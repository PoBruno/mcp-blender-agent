"""Raw Python execution — environment-flag gated (ADR-008).

Disabled by default. To enable, set env var BLENDER_AGENT_ALLOW_EXEC_PYTHON=1
BEFORE Blender starts the addon (or before serve_blocking()).
"""

from __future__ import annotations

import io
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from ..helpers import ExecDisabledError, InvalidInputError
from ..server import handler


def _exec_allowed() -> bool:
    return os.environ.get("BLENDER_AGENT_ALLOW_EXEC_PYTHON", "").lower() in {"1", "true", "yes", "on"}


@handler("POST", "/exec/python")
def exec_python(body: dict[str, Any]) -> dict[str, Any]:
    """Execute an arbitrary Python snippet inside Blender.

    Per ADR-008, requires BLENDER_AGENT_ALLOW_EXEC_PYTHON=1 in the addon env.
    """
    if not _exec_allowed():
        raise ExecDisabledError(
            "exec_python is disabled. Set BLENDER_AGENT_ALLOW_EXEC_PYTHON=1 to enable."
        )
    code = body.get("code")
    if not isinstance(code, str) or not code.strip():
        raise InvalidInputError("code (non-empty string) is required")

    import bpy  # type: ignore

    stdout = io.StringIO()
    stderr = io.StringIO()
    local_ns: dict[str, Any] = {"bpy": bpy, "_result": None}
    success = True
    error_msg = ""
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(compile(code, "<exec_python>", "exec"), local_ns)  # noqa: S102
    except Exception:
        success = False
        error_msg = traceback.format_exc()

    return {
        "ok": success,
        "data": {
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
            "result": repr(local_ns.get("_result")),
        },
        "errorCode": "EXEC_FAILED" if not success else None,
        "warnings": [error_msg] if not success else [],
    }


@handler("POST", "/exec/status")
def exec_status(_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {
            "execPythonAllowed": _exec_allowed(),
            "pythonVersion": sys.version,
        },
    }
