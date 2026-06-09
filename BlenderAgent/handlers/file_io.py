"""File IO handlers (B9.E)."""

from __future__ import annotations

import os
from typing import Any

from ..helpers import InvalidInputError, composite_undo
from ..server import handler


@handler("POST", "/file/new")
def file_new(body: dict[str, Any]) -> dict[str, Any]:
    """Reset the current Blender session to a fresh empty .blend file.

    Body: {empty?: bool}
      empty=true (default false): start with no default cube/camera/light.

    Calls bpy.ops.wm.read_homefile(use_empty=...) to load the user's startup
    or a fully empty scene. After this the active .blend has no filepath until
    /file/save_as is called.
    """
    import bpy  # type: ignore
    empty = bool(body.get("empty", False))
    bpy.ops.wm.read_homefile(use_empty=empty)
    return {
        "ok": True,
        "data": {"filepath": bpy.data.filepath, "empty": empty,
                 "sceneName": bpy.context.scene.name},
        "refs": {"sceneName": bpy.context.scene.name},
    }


@handler("POST", "/file/save")
def file_save(_body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    if not bpy.data.filepath:
        raise InvalidInputError("File has no filepath; use /file/save_as")
    bpy.ops.wm.save_mainfile()
    return {"ok": True, "data": {"filepath": bpy.data.filepath}}


@handler("POST", "/file/save_as")
def file_save_as(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
    return {"ok": True, "data": {"filepath": filepath}, "refs": {"filepath": filepath}}


@handler("POST", "/file/open")
def file_open(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    if not os.path.isfile(filepath):
        raise InvalidInputError(f"file does not exist: {filepath}")
    bpy.ops.wm.open_mainfile(filepath=filepath)
    return {"ok": True, "data": {"filepath": filepath}, "refs": {"filepath": filepath}}


@handler("POST", "/file/append_data")
def file_append_data(body: dict[str, Any]) -> dict[str, Any]:
    """Append one or more datablocks from another .blend file.

    Body: {filepath: str, datablockType: 'Object'|'Material'|'Action'|...,
           names: list[str]}
    """
    import bpy  # type: ignore
    filepath = body.get("filepath")
    datablock_type = body.get("datablockType", "Object")
    names = body.get("names", [])
    if not filepath or not names:
        raise InvalidInputError("filepath and names are required")
    if not os.path.isfile(filepath):
        raise InvalidInputError(f"file does not exist: {filepath}")

    appended: list[str] = []
    with composite_undo(f"file_append_data:{datablock_type}"):
        try:
            ctx = bpy.data.libraries.load(filepath, link=False)
        except (ValueError, RuntimeError) as exc:
            raise InvalidInputError(f"cannot load {filepath!r}: {exc}") from exc
        with ctx as (data_from, data_to):
            attr_from = getattr(data_from, datablock_type.lower() + "s", None)
            attr_to = getattr(data_to, datablock_type.lower() + "s", None)
            if attr_from is None or attr_to is None:
                raise InvalidInputError(f"unknown datablock type {datablock_type!r}")
            available = list(attr_from)
            wanted = [n for n in names if n in available]
            setattr(data_to, datablock_type.lower() + "s", wanted)
            appended = wanted

    # Link appended Objects into the active scene
    if datablock_type.lower() == "object":
        for obj in bpy.data.objects:
            if obj.name in appended and obj not in list(bpy.context.scene.collection.objects):
                try:
                    bpy.context.scene.collection.objects.link(obj)
                except RuntimeError:
                    pass

    return {
        "ok": True,
        "data": {
            "filepath": filepath,
            "datablockType": datablock_type,
            "appended": appended,
        },
        "refs": {"objectNames": appended} if datablock_type.lower() == "object" else {},
    }


@handler("POST", "/file/pack_all")
def file_pack_all(_body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    bpy.ops.file.pack_all()
    return {"ok": True, "data": {"packed": True}}


@handler("POST", "/file/unpack_all")
def file_unpack_all(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    method = body.get("method", "USE_LOCAL")
    bpy.ops.file.unpack_all(method=method)
    return {"ok": True, "data": {"unpacked": True, "method": method}}
