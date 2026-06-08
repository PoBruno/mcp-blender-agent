"""Shape key handlers (B3, B7 — MetaHuman ARKit blendshapes)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    ShapeKeyNotFoundError,
    composite_undo,
    get_object,
    set_active_and_selected,
    with_3dview_context,
)
from ..server import handler


def _ensure_mesh(obj: Any) -> None:
    if obj.type != "MESH":
        raise InvalidInputError(f"Object {obj.name!r} type is {obj.type}, expected MESH")


@handler("POST", "/shape_key/add")
def shape_key_add(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    name = body.get("name", "Key")
    from_mix = bool(body.get("fromMix", False))
    with composite_undo(f"shape_key_add:{obj.name}/{name}"):
        if obj.data.shape_keys is None:
            set_active_and_selected(obj)
            with with_3dview_context():
                bpy.ops.object.shape_key_add(from_mix=False)
            # First call creates Basis. Add the named key next.
            sk = obj.shape_key_add(name=name, from_mix=from_mix)
        else:
            sk = obj.shape_key_add(name=name, from_mix=from_mix)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "shapeKeyName": sk.name, "value": sk.value},
        "refs": {"objectName": obj.name, "shapeKeyName": sk.name},
    }


@handler("POST", "/shape_key/set_value")
def shape_key_set_value(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    name = body.get("shapeKeyName")
    if not name:
        raise InvalidInputError("shapeKeyName is required")
    if obj.data.shape_keys is None:
        raise ShapeKeyNotFoundError(f"{obj.name!r} has no shape keys")
    sk = obj.data.shape_keys.key_blocks.get(name)
    if sk is None:
        raise ShapeKeyNotFoundError(f"{obj.name!r} has no shape key {name!r}")
    with composite_undo(f"shape_key_set_value:{obj.name}/{name}"):
        sk.value = float(body.get("value", 1.0))
    return {
        "ok": True,
        "data": {"objectName": obj.name, "shapeKeyName": name, "value": sk.value},
        "refs": {"objectName": obj.name, "shapeKeyName": name},
    }


@handler("POST", "/shape_key/rename")
def shape_key_rename(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    old = body.get("oldName")
    new = body.get("newName")
    if not old or not new:
        raise InvalidInputError("oldName and newName are required")
    if obj.data.shape_keys is None:
        raise ShapeKeyNotFoundError(f"{obj.name!r} has no shape keys")
    sk = obj.data.shape_keys.key_blocks.get(old)
    if sk is None:
        raise ShapeKeyNotFoundError(f"{obj.name!r} has no shape key {old!r}")
    with composite_undo(f"shape_key_rename:{obj.name}/{old}->{new}"):
        sk.name = new
    return {
        "ok": True,
        "data": {"objectName": obj.name, "shapeKeyName": sk.name},
        "refs": {"objectName": obj.name, "shapeKeyName": sk.name},
    }
