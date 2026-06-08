"""Library (link/append/override) handlers (B9)."""

from __future__ import annotations

import os
from typing import Any

from ..helpers import InvalidInputError, composite_undo
from ..server import handler


@handler("POST", "/library/link")
def library_link(body: dict[str, Any]) -> dict[str, Any]:
    """Link datablocks from another .blend (keeps them library-linked, not appended)."""
    import bpy  # type: ignore
    filepath = body.get("filepath")
    datablock_type = body.get("datablockType", "Object")
    names = body.get("names", [])
    if not filepath or not names:
        raise InvalidInputError("filepath and names are required")
    if not os.path.isfile(filepath):
        raise InvalidInputError(f"file not found: {filepath}")

    linked: list[str] = []
    with composite_undo(f"library_link:{datablock_type}"):
        with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
            attr_from = getattr(data_from, datablock_type.lower() + "s", None)
            attr_to = getattr(data_to, datablock_type.lower() + "s", None)
            if attr_from is None or attr_to is None:
                raise InvalidInputError(f"unknown datablock type {datablock_type!r}")
            avail = list(attr_from)
            wanted = [n for n in names if n in avail]
            setattr(data_to, datablock_type.lower() + "s", wanted)
            linked = wanted

    return {
        "ok": True,
        "data": {"filepath": filepath, "datablockType": datablock_type, "linked": linked},
        "refs": {"objectNames": linked} if datablock_type.lower() == "object" else {},
    }


@handler("POST", "/library/make_override")
def library_make_override(body: dict[str, Any]) -> dict[str, Any]:
    """Make a library override on the linked datablock (Blender 4.x flow)."""
    import bpy  # type: ignore
    object_name = body.get("objectName")
    if not object_name:
        raise InvalidInputError("objectName is required")
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        raise InvalidInputError(f"object {object_name!r} not found")
    if obj.library is None:
        raise InvalidInputError(f"object {object_name!r} is not linked from a library")
    with composite_undo(f"library_make_override:{object_name}"):
        try:
            override = obj.override_create(remap_local_usages=True)
        except RuntimeError as exc:
            raise InvalidInputError(f"override_create failed: {exc}") from exc
    return {
        "ok": True,
        "data": {"objectName": object_name, "overrideObjectName": override.name},
        "refs": {"objectName": override.name},
    }


@handler("POST", "/library/reload")
def library_reload(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    lib = bpy.data.libraries.get(filepath)
    if lib is None:
        # try basename match
        lib = next((l for l in bpy.data.libraries if l.filepath == filepath), None)
    if lib is None:
        raise InvalidInputError(f"library {filepath!r} not found in bpy.data.libraries")
    lib.reload()
    return {"ok": True, "data": {"filepath": filepath, "reloaded": True}}
