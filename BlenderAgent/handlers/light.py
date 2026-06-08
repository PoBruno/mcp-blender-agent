"""Light handlers (B9)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_collection,
    get_object,
)
from ..server import handler


_LIGHT_TYPES = {"POINT", "SUN", "SPOT", "AREA"}


@handler("POST", "/light/create")
def light_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a light object.

    Body: {name?: str, type: 'POINT'|'SUN'|'SPOT'|'AREA',
           energy?: float, color?: [r,g,b], location?: [x,y,z],
           collectionName?: str}
    """
    import bpy  # type: ignore

    light_type = (body.get("type") or "POINT").upper()
    if light_type not in _LIGHT_TYPES:
        raise InvalidInputError(f"type {light_type!r} not in {sorted(_LIGHT_TYPES)}")
    name = body.get("name", light_type.title())
    energy = float(body.get("energy", 1000.0))
    color = tuple(body.get("color", (1.0, 1.0, 1.0)))
    location = tuple(body.get("location", (0.0, 0.0, 3.0)))
    collection_name = body.get("collectionName")

    with composite_undo(f"light_create:{name}/{light_type}"):
        light_data = bpy.data.lights.new(name=f"{name}_data", type=light_type)
        light_data.energy = energy
        light_data.color = color
        light_obj = bpy.data.objects.new(name=name, object_data=light_data)
        light_obj.location = location
        if collection_name:
            get_collection(collection_name).objects.link(light_obj)
        else:
            bpy.context.scene.collection.objects.link(light_obj)

    return {
        "ok": True,
        "data": {
            "lightObjectName": light_obj.name,
            "lightDataName": light_data.name,
            "type": light_type,
            "energy": energy,
        },
        "refs": {"objectName": light_obj.name, "lightName": light_obj.name},
    }


@handler("POST", "/light/set_property")
def light_set_property(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    if obj.type != "LIGHT":
        raise InvalidInputError(f"{obj.name!r} type is {obj.type}, expected LIGHT")
    props = body.get("properties") or {}
    with composite_undo(f"light_set_property:{obj.name}"):
        for k, v in props.items():
            if hasattr(obj.data, k):
                setattr(obj.data, k, v)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "updated": list(props.keys())},
        "refs": {"objectName": obj.name},
    }
