"""Armature handlers (B7)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_armature_object,
    get_collection,
    with_3dview_context,
)
from ..server import handler


@handler("POST", "/armature/create")
def armature_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new armature object."""
    import bpy  # type: ignore

    name = body.get("name", "Armature")
    location = tuple(body.get("location", (0.0, 0.0, 0.0)))
    collection_name = body.get("collectionName")

    with composite_undo(f"armature_create:{name}"):
        arm_data = bpy.data.armatures.new(name=f"{name}_data")
        arm_obj = bpy.data.objects.new(name=name, object_data=arm_data)
        arm_obj.location = location
        if collection_name:
            target = get_collection(collection_name)
            target.objects.link(arm_obj)
        else:
            bpy.context.scene.collection.objects.link(arm_obj)

    return {
        "ok": True,
        "data": {"armatureObjectName": arm_obj.name, "armatureDataName": arm_data.name},
        "refs": {"armatureName": arm_obj.name, "objectName": arm_obj.name},
    }


@handler("POST", "/armature/show_in_front")
def armature_show_in_front(body: dict[str, Any]) -> dict[str, Any]:
    arm = get_armature_object(body.get("armatureObjectName") or body.get("name"))
    show = bool(body.get("show", True))
    with composite_undo(f"armature_show_in_front:{arm.name}"):
        arm.show_in_front = show
    return {"ok": True, "data": {"armatureObjectName": arm.name, "showInFront": show},
            "refs": {"armatureName": arm.name}}
