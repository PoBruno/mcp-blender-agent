"""Modifier handlers (B2)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    ModifierNotFoundError,
    composite_undo,
    get_object,
    set_active_and_selected,
    with_3dview_context,
)
from ..server import handler


@handler("POST", "/modifier/add")
def modifier_add(body: dict[str, Any]) -> dict[str, Any]:
    """Add a modifier to an object.

    Body: {objectName: str, type: str (e.g. 'SUBSURF', 'MIRROR', 'BEVEL', ...),
           name?: str, params?: dict}
    """
    obj = get_object(body.get("objectName"))
    mod_type = body.get("type")
    if not mod_type:
        raise InvalidInputError("type is required")
    name = body.get("name") or mod_type.title()
    params = body.get("params") or {}

    with composite_undo(f"modifier_add:{obj.name}/{mod_type}"):
        try:
            mod = obj.modifiers.new(name=name, type=mod_type)
        except TypeError as exc:
            raise InvalidInputError(f"Unknown modifier type {mod_type!r}: {exc}") from exc
        if mod is None:
            raise InvalidInputError(f"Failed to add modifier {mod_type!r} to {obj.name!r}")
        for k, v in params.items():
            if hasattr(mod, k):
                setattr(mod, k, v)

    return {
        "ok": True,
        "data": {"objectName": obj.name, "modifierName": mod.name, "type": mod.type},
        "refs": {"objectName": obj.name, "modifierName": mod.name},
    }


@handler("POST", "/modifier/set_property")
def modifier_set_property(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    name = body.get("modifierName")
    if not name:
        raise InvalidInputError("modifierName is required")
    mod = obj.modifiers.get(name)
    if mod is None:
        raise ModifierNotFoundError(f"{obj.name!r} has no modifier {name!r}")
    props = body.get("properties") or {}
    with composite_undo(f"modifier_set_property:{obj.name}/{name}"):
        for k, v in props.items():
            if not hasattr(mod, k):
                raise InvalidInputError(f"Modifier {mod.type!r} has no property {k!r}")
            setattr(mod, k, v)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "modifierName": mod.name, "updated": list(props.keys())},
        "refs": {"objectName": obj.name, "modifierName": mod.name},
    }


@handler("POST", "/modifier/apply")
def modifier_apply(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    name = body.get("modifierName")
    if not name:
        raise InvalidInputError("modifierName is required")
    if obj.modifiers.get(name) is None:
        raise ModifierNotFoundError(f"{obj.name!r} has no modifier {name!r}")
    with composite_undo(f"modifier_apply:{obj.name}/{name}"):
        set_active_and_selected(obj)
        with with_3dview_context():
            bpy.ops.object.modifier_apply(modifier=name)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "appliedModifier": name},
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/modifier/remove")
def modifier_remove(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    name = body.get("modifierName")
    if not name:
        raise InvalidInputError("modifierName is required")
    mod = obj.modifiers.get(name)
    if mod is None:
        raise ModifierNotFoundError(f"{obj.name!r} has no modifier {name!r}")
    with composite_undo(f"modifier_remove:{obj.name}/{name}"):
        obj.modifiers.remove(mod)
    return {"ok": True, "data": {"objectName": obj.name, "removedModifier": name}}


@handler("POST", "/modifier/list")
def modifier_list(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers],
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/modifier/reorder")
def modifier_reorder(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    name = body.get("modifierName")
    direction = body.get("direction", "UP").upper()
    if not name:
        raise InvalidInputError("modifierName is required")
    if direction not in {"UP", "DOWN"}:
        raise InvalidInputError("direction must be UP or DOWN")
    with composite_undo(f"modifier_reorder:{obj.name}/{name}/{direction}"):
        set_active_and_selected(obj)
        with with_3dview_context():
            if direction == "UP":
                bpy.ops.object.modifier_move_up(modifier=name)
            else:
                bpy.ops.object.modifier_move_down(modifier=name)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "modifierName": name, "direction": direction},
        "refs": {"objectName": obj.name, "modifierName": name},
    }
