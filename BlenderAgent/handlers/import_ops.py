"""Import handlers (B9.E)."""

from __future__ import annotations

import os
from typing import Any

from ..helpers import ImportFailedError, InvalidInputError
from ..server import handler


@handler("POST", "/import/fbx")
def import_fbx(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    if not os.path.isfile(filepath):
        raise InvalidInputError(f"file not found: {filepath}")
    before = set(o.name for o in bpy.data.objects)
    try:
        bpy.ops.import_scene.fbx(filepath=filepath)
    except Exception as exc:  # noqa: BLE001
        raise ImportFailedError(f"FBX import failed: {exc}") from exc
    after = set(o.name for o in bpy.data.objects)
    new_objects = sorted(after - before)
    return {
        "ok": True,
        "data": {"filepath": filepath, "importedObjects": new_objects},
        "refs": {"objectNames": new_objects, "filepath": filepath},
    }


@handler("POST", "/import/obj")
def import_obj(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    filepath = body.get("filepath")
    if not filepath or not os.path.isfile(filepath):
        raise InvalidInputError(f"filepath missing or file not found")
    before = set(o.name for o in bpy.data.objects)
    try:
        bpy.ops.wm.obj_import(filepath=filepath)
    except Exception as exc:  # noqa: BLE001
        raise ImportFailedError(f"OBJ import failed: {exc}") from exc
    after = set(o.name for o in bpy.data.objects)
    new_objects = sorted(after - before)
    return {
        "ok": True,
        "data": {"filepath": filepath, "importedObjects": new_objects},
        "refs": {"objectNames": new_objects},
    }


@handler("POST", "/import/gltf")
def import_gltf(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    filepath = body.get("filepath")
    if not filepath or not os.path.isfile(filepath):
        raise InvalidInputError(f"filepath missing or file not found")
    before = set(o.name for o in bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=filepath)
    except Exception as exc:  # noqa: BLE001
        raise ImportFailedError(f"glTF import failed: {exc}") from exc
    after = set(o.name for o in bpy.data.objects)
    new_objects = sorted(after - before)
    return {
        "ok": True,
        "data": {"filepath": filepath, "importedObjects": new_objects},
        "refs": {"objectNames": new_objects},
    }
