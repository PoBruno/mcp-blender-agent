---
applyTo: "BlenderAgent/**/*.py"
---

# Python (Blender addon) rules

For all files under `BlenderAgent/`. They run inside Blender's embedded Python interpreter (CPython 3.11+ on Blender 4.2 LTS).

Matching Claude Code version: [`.claude/rules/python-blender.md`](../../.claude/rules/python-blender.md) — keep both in sync.

## Threading — the most important rule

**`bpy` is not thread-safe.** Mutating Blender data from a background thread will corrupt state or crash the editor.

The addon's HTTP server runs on a `threading.Thread`. Every handler invocation **must** enqueue its work onto the main thread via `bpy.app.timers.register(drain, persistent=True)`, then block the HTTP thread on a `threading.Event` until the main thread sets the result.

Pattern:

```python
import bpy
import threading
import queue

_work_queue: "queue.Queue[tuple]" = queue.Queue()

def _drain():
    try:
        fn, args, kwargs, result_event, result_holder = _work_queue.get_nowait()
    except queue.Empty:
        return 0.016  # poll every frame
    try:
        result_holder["value"] = fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        result_holder["error"] = exc
    finally:
        result_event.set()
    return 0.016

def run_on_main(fn, *args, **kwargs):
    """Call from background thread. Blocks until main-thread executes fn."""
    event = threading.Event()
    holder = {}
    _work_queue.put((fn, args, kwargs, event, holder))
    event.wait(timeout=30.0)
    if "error" in holder:
        raise holder["error"]
    return holder.get("value")

def register():
    bpy.app.timers.register(_drain, persistent=True)
```

Every handler body runs **inside `fn` passed to `run_on_main`** — never directly in the HTTP handler.

## API choices

- **`bpy.data`** for navigating and mutating data-blocks: `bpy.data.objects`, `bpy.data.materials`, `bpy.data.armatures`, `bpy.data.actions`, `bpy.data.scenes`.
- **`bpy.ops`** for operators that have side effects beyond a single data-block (mode switches, selection, file IO, render). Always check `op.poll()` first.
- **`bmesh`** for non-trivial mesh edits. Open with `bmesh.from_edit_mesh(obj.data)` in Edit Mode or `bmesh.new()` + `bm.from_mesh(obj.data)` in Object Mode.
- **`mathutils`** for vectors, matrices, quaternions. Never mix with raw tuples in math.
- **`bpy.context.temp_override(...)`** for operators that depend on 3D View context (selection, area, region). Always.

**Never** use:
- Pre-2.8 `Blender.*` globals (don't exist anymore but tutorials online still reference them).
- Direct attribute mutation on read-only context (`bpy.context.active_object = obj` raises). Use `bpy.context.view_layer.objects.active = obj`.
- `print()` from a handler — the output goes nowhere visible. Use the addon's logger.

## Mode-aware mutations

```python
def with_mode(obj, mode, fn):
    prev_active = bpy.context.view_layer.objects.active
    prev_mode = obj.mode if obj == prev_active else "OBJECT"
    bpy.context.view_layer.objects.active = obj
    if obj.mode != mode:
        bpy.ops.object.mode_set(mode=mode)
    try:
        return fn()
    finally:
        if obj.mode != prev_mode:
            bpy.ops.object.mode_set(mode=prev_mode)
        bpy.context.view_layer.objects.active = prev_active
```

Every mesh edit, armature edit, pose edit wraps in `with_mode`. Idempotent — entering a mode you're already in is a no-op (mode_set checks).

## Undo policy

Composite mutations end with **one** undo push:

```python
# inside main-thread fn
do_step_1()
do_step_2()
do_step_3()
bpy.ops.ed.undo_push(message="Add socket and rename bone")
```

Ctrl+Z then reverses the entire composite. Never call `undo_push` per primitive inside a composite.

For pure-data mutations (no `bpy.ops`), call `undo_push` yourself. For operators (`bpy.ops.*`), Blender pushes automatically — but the composite still ends with **one** explicit `undo_push` so the label is meaningful.

## Context overrides

Operators tied to 3D View need an override:

```python
def with_view3d_override(fn):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                with bpy.context.temp_override(window=window, area=area, region=area.regions[-1]):
                    return fn()
    raise RuntimeError("No 3D Viewport available")
```

Headless Blender (`--background`) has no windows. Handlers that depend on 3D View must check and return `ERROR_NO_VIEWPORT` cleanly.

## Errors

Raise specific exceptions inside `fn`. The handler boundary catches and converts:

```python
class HandlerError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
```

The TS server maps `HandlerError.code` to `errorCode` in the tool response. Use codes from the registry in [`.claude/rules/mcp-tools.md`](../../.claude/rules/mcp-tools.md). Don't invent new codes without registering them.

## Logging

Use `print` only during local debug. Production logging:

```python
import logging
log = logging.getLogger("BlenderAgent")
log.info("…")
```

The addon configures the handler in `__init__.py`. Never write to stdout from handlers — VS Code's MCP transport reads stdout and gets confused.

## What not to do

- No `time.sleep()` on the main thread. Use `bpy.app.timers` with an interval.
- No GC manipulation. Blender owns its data lifecycle.
- No direct `.blend` writes. Always go through `bpy.ops.wm.save_mainfile` / `save_as_mainfile`.
- No `os.system` / `subprocess` for Blender ops — use `bpy.ops`.
- No `eval` / `exec` in handlers. The opt-in `exec_python` tool is the only sanctioned place.
