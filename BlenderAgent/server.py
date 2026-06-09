"""HTTP server for BlenderAgent.

The HTTP server runs on a background thread (`ThreadingHTTPServer`). All
request handlers enqueue their work onto `_job_queue` and block on a
`threading.Event` until `_drain` runs them on the main thread. The drain is
registered via `bpy.app.timers.register(_drain, persistent=True)`.

`bpy` is NOT thread-safe — never call `bpy.*` from the HTTP thread directly.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional

logger = logging.getLogger("BlenderAgent.server")

# ----------------------------------------------------------------------------
# Module-level state
# ----------------------------------------------------------------------------

_DEFAULT_PORT = 9877
_DRAIN_INTERVAL_SECS = 0.016  # ~60 Hz

_job_queue: queue.Queue[tuple[Callable[[], Any], threading.Event, list[Any]]] = queue.Queue()
_server: Optional[ThreadingHTTPServer] = None
_server_thread: Optional[threading.Thread] = None
_shutdown_event = threading.Event()
_drain_registered = False

# Default main-thread timeout for a handler. Light ops finish in well under a
# second; heavy ones (render, bake, remesh) declare their own via the decorator
# so a slow-but-legitimate render does not get killed mid-flight and wedge the
# main thread for every request that follows it.
_DEFAULT_HANDLER_TIMEOUT = 30.0


# ----------------------------------------------------------------------------
# Handler registry
# ----------------------------------------------------------------------------

# Map of (method, path) → callable(body_dict) → response_dict
_handlers: dict[tuple[str, str], Callable[[dict[str, Any]], dict[str, Any]]] = {}
# Map of (method, path) → main-thread timeout in seconds.
_handler_timeouts: dict[tuple[str, str], float] = {}


def handler(method: str, path: str, *, timeout: float = _DEFAULT_HANDLER_TIMEOUT) -> Callable[
    [Callable[[dict[str, Any]], dict[str, Any]]],
    Callable[[dict[str, Any]], dict[str, Any]],
]:
    """Decorator: register an HTTP handler.

    The decorated function takes the parsed JSON body (or empty dict for GET)
    and returns the response dict. It is called on the **main thread** via the
    timer drain, so it may freely call `bpy.*`.

    `timeout` is the main-thread budget in seconds. Heavy operations (renders,
    bakes, remeshes) MUST raise it above the 30s default — otherwise the job is
    declared timed-out while it is still running synchronously on the main
    thread, blocking the drain for every subsequent request (cascading freeze).

    Exceptions are caught at the boundary and converted to
    `{"ok": False, "errorCode": "...", "message": "..."}`.
    """
    def decorator(fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        key = (method.upper(), path)
        if key in _handlers:
            raise RuntimeError(f"Duplicate handler registration for {method} {path}")
        _handlers[key] = fn
        _handler_timeouts[key] = timeout
        return fn
    return decorator


# ----------------------------------------------------------------------------
# Main-thread marshalling
# ----------------------------------------------------------------------------

def _run_on_main_thread(fn: Callable[[], Any], timeout: float = 30.0) -> Any:
    """Enqueue `fn` for the next timer drain. Block until it completes.

    Returns the function's return value, or re-raises its exception.
    """
    done = threading.Event()
    result: list[Any] = [None, None]  # [value, exception]

    def wrapped() -> None:
        try:
            result[0] = fn()
        except BaseException as exc:  # noqa: BLE001  (re-raised on calling thread)
            result[1] = exc
        finally:
            done.set()

    _job_queue.put((wrapped, done, result))

    if not done.wait(timeout=timeout):
        raise TimeoutError(f"main-thread job exceeded {timeout}s")

    if result[1] is not None:
        raise result[1]  # type: ignore[misc]
    return result[0]


def _drain() -> Optional[float]:
    """Timer callback — runs queued jobs on the main thread.

    Returns the next poll interval (seconds). Returning None deregisters.
    """
    # Drain everything that arrived; don't hog the main thread for too long.
    deadline_jobs = 16
    processed = 0
    while processed < deadline_jobs:
        try:
            fn, _done, _result = _job_queue.get_nowait()
        except queue.Empty:
            break
        try:
            fn()
        except BaseException:  # noqa: BLE001  (caught inside wrapped)
            logger.exception("drain: wrapped fn raised unexpectedly")
        processed += 1

    if _shutdown_event.is_set():
        return None  # deregister
    return _DRAIN_INTERVAL_SECS


def drain_once() -> None:
    """Manual drain for headless `serve_blocking` mode."""
    _drain()


def shutdown_requested() -> bool:
    return _shutdown_event.is_set()


# ----------------------------------------------------------------------------
# HTTP request handler
# ----------------------------------------------------------------------------

class _RequestHandler(BaseHTTPRequestHandler):
    server_version = "BlenderAgent/0.0.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        # Suppress default stderr access log — use our logger instead.
        logger.debug("HTTP %s - %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _dispatch(self, method: str) -> None:
        key = (method, self.path)
        fn = _handlers.get(key)
        if fn is None:
            self._send_json(404, {
                "ok": False,
                "errorCode": "HANDLER_NOT_FOUND",
                "message": f"No handler for {method} {self.path}",
            })
            return

        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length > 0 else b""
            body: dict[str, Any] = json.loads(raw) if raw else {}
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {
                "ok": False,
                "errorCode": "INVALID_JSON",
                "message": str(exc),
            })
            return

        try:
            timeout = _handler_timeouts.get(key, _DEFAULT_HANDLER_TIMEOUT)
            result = _run_on_main_thread(lambda: fn(body), timeout=timeout)
        except TimeoutError as exc:
            self._send_json(504, {
                "ok": False,
                "errorCode": "BLENDER_TIMEOUT",
                "message": str(exc),
            })
            return
        except BaseException as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            logger.error("handler %s %s raised: %s\n%s", method, self.path, exc, tb)
            error_code = getattr(exc, "error_code", "INTERNAL_ERROR")
            self._send_json(500, {
                "ok": False,
                "errorCode": error_code,
                "message": str(exc),
            })
            return

        # Success
        if not isinstance(result, dict):
            result = {"ok": True, "data": result}
        result.setdefault("ok", True)
        self._send_json(200, result)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")


# ----------------------------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------------------------

def _get_port() -> int:
    raw = os.environ.get("BLENDER_AGENT_PORT") or os.environ.get("BLENDER_PORT")
    if not raw:
        return _DEFAULT_PORT
    try:
        return int(raw)
    except ValueError:
        logger.warning("invalid BLENDER_AGENT_PORT %r — falling back to %d", raw, _DEFAULT_PORT)
        return _DEFAULT_PORT


def _register_drain() -> None:
    """Register the main-thread drain via bpy.app.timers.

    Skipped if `bpy` cannot be imported (e.g. unit tests that import server.py
    without Blender). In that case the caller is responsible for invoking
    `drain_once()` manually.
    """
    global _drain_registered
    if _drain_registered:
        return
    try:
        import bpy  # type: ignore
    except ImportError:
        logger.warning("bpy not available — drain must be pumped manually via drain_once()")
        return

    if not bpy.app.timers.is_registered(_drain):
        bpy.app.timers.register(_drain, first_interval=_DRAIN_INTERVAL_SECS, persistent=True)
    _drain_registered = True


def _unregister_drain() -> None:
    global _drain_registered
    try:
        import bpy  # type: ignore
    except ImportError:
        _drain_registered = False
        return
    if bpy.app.timers.is_registered(_drain):
        bpy.app.timers.unregister(_drain)
    _drain_registered = False


def _import_handlers() -> None:
    """Import all handler modules so their `@handler` decorators fire."""
    from . import handlers  # noqa: F401  (side-effect: registers handlers)


def start() -> None:
    global _server, _server_thread
    if _server is not None:
        logger.info("server already running")
        return

    _import_handlers()

    port = _get_port()
    _shutdown_event.clear()
    _server = ThreadingHTTPServer(("127.0.0.1", port), _RequestHandler)
    _server.daemon_threads = True
    _server_thread = threading.Thread(
        target=_server.serve_forever,
        name="BlenderAgent-HTTP",
        daemon=True,
    )
    _server_thread.start()
    _register_drain()
    logger.info("BlenderAgent listening on 127.0.0.1:%d", port)


def stop() -> None:
    global _server, _server_thread
    _shutdown_event.set()
    if _server is not None:
        try:
            _server.shutdown()
            _server.server_close()
        except Exception:  # noqa: BLE001
            logger.exception("error during server.shutdown")
        _server = None
    _server_thread = None
    _unregister_drain()
    logger.info("BlenderAgent stopped")


# ----------------------------------------------------------------------------
# Built-in handlers (server lifecycle)
# ----------------------------------------------------------------------------

@handler("GET", "/server/status")
def _server_status(_body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    return {
        "ok": True,
        "data": {
            "version": bpy.app.version_string,
            "versionTuple": list(bpy.app.version),
            "scene": bpy.context.scene.name if bpy.context.scene else None,
            "mode": "blender-agent",
            "addonVersion": "0.0.1",
            "execPythonAllowed": os.environ.get("BLENDER_AGENT_ALLOW_EXEC") == "1",
        },
        "refs": {
            "sceneName": bpy.context.scene.name if bpy.context.scene else "",
        },
    }


@handler("POST", "/server/shutdown")
def _server_shutdown(_body: dict[str, Any]) -> dict[str, Any]:
    _shutdown_event.set()
    return {"ok": True, "data": {"shuttingDown": True}}


@handler("POST", "/server/addon_restart")
def _server_addon_restart(body: dict[str, Any]) -> dict[str, Any]:
    """Disable + re-enable the BlenderAgent addon in the running Blender.

    Scheduled via `bpy.app.timers.register` with a small delay so the HTTP
    response is sent BEFORE the server gets torn down. The re-enable then
    spins a fresh server on the same port. Use this to fully re-register
    bl_info-level state (handler classes, operators, properties) — heavier
    than `/server/reload` which only re-imports handler submodules.

    Body: { delay?: float (default 0.5) }
    Returns: { restarting, addonModule, delay }
    """
    import bpy  # type: ignore

    delay = float(body.get("delay", 0.5))
    if delay < 0.1:
        delay = 0.1
    module_name = __package__ or "BlenderAgent"

    def _do_restart() -> None:
        try:
            bpy.ops.preferences.addon_disable(module=module_name)
        except Exception:  # noqa: BLE001
            logger.exception("addon_disable failed")
        try:
            bpy.ops.preferences.addon_enable(module=module_name)
        except Exception:  # noqa: BLE001
            logger.exception("addon_enable failed")
        return None  # do not repeat

    bpy.app.timers.register(_do_restart, first_interval=delay)

    return {
        "ok": True,
        "data": {
            "restarting": True,
            "addonModule": module_name,
            "delay": delay,
        },
    }


@handler("POST", "/server/blender_quit")
def _server_blender_quit(body: dict[str, Any]) -> dict[str, Any]:
    """Quit the host Blender process from inside the addon.

    Scheduled via timer so the HTTP response is sent first. After the call
    Blender exits — the orchestrator must re-spawn it externally
    (e.g. PowerShell Start-Process) to recover.

    Body: { delay?: float (default 0.5), saveAs?: str (optional .blend path) }
    Returns: { quitting, delay, saveAs }
    """
    import bpy  # type: ignore

    delay = float(body.get("delay", 0.5))
    if delay < 0.1:
        delay = 0.1
    save_as = body.get("saveAs")

    def _do_quit() -> None:
        try:
            if save_as:
                bpy.ops.wm.save_as_mainfile(filepath=str(save_as))
        except Exception:  # noqa: BLE001
            logger.exception("save_as_mainfile failed")
        try:
            bpy.ops.wm.quit_blender()
        except Exception:  # noqa: BLE001
            logger.exception("quit_blender failed")
        return None

    bpy.app.timers.register(_do_quit, first_interval=delay)
    return {
        "ok": True,
        "data": {"quitting": True, "delay": delay, "saveAs": save_as},
    }


@handler("POST", "/batch", timeout=900.0)
def _batch(body: dict[str, Any]) -> dict[str, Any]:
    """Run many tool calls in one request (S6-17).

    The whole batch executes inside a single main-thread drain job, so there is
    no per-op HTTP round-trip and the sequence is not interleaved with other
    requests. Each op = {path, method?='POST', body?={}}.

    Body: { ops: [ {path, method?, body?}, ... ], stopOnError?: bool=true }
    Returns { ok, data: { results: [{index, path, ok, ...}], count, failedAt? } }.
    """
    ops = body.get("ops")
    if not isinstance(ops, list) or not ops:
        return {"ok": False, "errorCode": "INVALID_INPUT", "message": "ops must be a non-empty list"}
    stop_on_error = bool(body.get("stopOnError", True))

    results: list[dict[str, Any]] = []
    ok_all = True
    failed_at: Optional[int] = None
    for i, op in enumerate(ops):
        if not isinstance(op, dict) or not op.get("path"):
            res = {"ok": False, "errorCode": "INVALID_INPUT", "message": "each op needs a 'path'"}
        else:
            method = str(op.get("method", "POST")).upper()
            path = op["path"]
            op_body = op.get("body") or {}
            fn = _handlers.get((method, path))
            if fn is None:
                res = {"ok": False, "errorCode": "HANDLER_NOT_FOUND",
                       "message": f"no handler for {method} {path}"}
            else:
                try:
                    res = fn(op_body)
                    if not isinstance(res, dict):
                        res = {"ok": True, "data": res}
                    res.setdefault("ok", True)
                except BaseException as exc:  # noqa: BLE001
                    res = {"ok": False,
                           "errorCode": getattr(exc, "error_code", "INTERNAL_ERROR"),
                           "message": str(exc)}
        results.append({"index": i, "path": op.get("path") if isinstance(op, dict) else None, **res})
        if not res.get("ok", True):
            ok_all = False
            failed_at = i
            if stop_on_error:
                break

    data: dict[str, Any] = {"results": results, "count": len(results)}
    if failed_at is not None:
        data["failedAt"] = failed_at
    return {"ok": ok_all, "data": data}


@handler("GET", "/server/handlers")
def _server_handlers(_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {
            "handlers": sorted(f"{m} {p}" for (m, p) in _handlers.keys()),
            "count": len(_handlers),
        },
    }


@handler("POST", "/server/reload")
def _server_reload(_body: dict[str, Any]) -> dict[str, Any]:
    """Re-import every BlenderAgent.handlers.* submodule and re-register handlers.

    Lets dev iterate on handler code without restarting Blender: edit a Python
    file in BlenderAgent/handlers/, sync it into the installed addon folder,
    then POST here. The next handler call sees the new code.

    Safe because we only reload modules whose name starts with
    'BlenderAgent.handlers.'. The registry is cleared and rebuilt; built-in
    /server/* handlers are re-added via the import of this very module.
    """
    import importlib
    import sys as _sys

    # Snapshot built-in /server/* handlers so we don't lose them when wiping.
    builtin = {k: v for k, v in _handlers.items() if k[1].startswith("/server/")}

    # Wipe so duplicate registration doesn't trip
    _handlers.clear()
    _handlers.update(builtin)

    reloaded: list[str] = []
    errors: list[dict[str, str]] = []

    # Reload the handlers package itself so __init__'s re-exports refresh
    pkg_name = "BlenderAgent.handlers"
    target_names = [n for n in list(_sys.modules.keys())
                    if n == pkg_name or n.startswith(pkg_name + ".")]
    # Also reload the library subpackages so parametric builders pick up edits.
    lib_pkg = "BlenderAgent.library"
    target_names.extend(n for n in list(_sys.modules.keys())
                        if n == lib_pkg or n.startswith(lib_pkg + "."))
    # Deterministic order: package first, then submodules alphabetically
    target_names.sort(key=lambda n: (0 if n == pkg_name else 1, n))

    for name in target_names:
        mod = _sys.modules.get(name)
        if mod is None:
            continue
        try:
            importlib.reload(mod)
            reloaded.append(name)
        except Exception as exc:  # noqa: BLE001
            errors.append({"module": name, "error": f"{type(exc).__name__}: {exc}"})

    return {
        "ok": len(errors) == 0,
        "data": {
            "reloadedCount": len(reloaded),
            "reloaded": reloaded,
            "handlerCount": len(_handlers),
            "errorCount": len(errors),
            "errors": errors,
        },
    }
