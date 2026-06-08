"""UE5 SOCKET_* empty handlers (B2)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_object,
    ue5_socket_name,
)
from ..server import handler


@handler("POST", "/socket/add")
def socket_add(body: dict[str, Any]) -> dict[str, Any]:
    """Add a SOCKET_<name> Empty as a child of parent object."""
    import bpy  # type: ignore

    parent = get_object(body.get("objectName"))
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    full_name = ue5_socket_name(name)
    location = tuple(body.get("location", (0.0, 0.0, 0.0)))
    rotation = tuple(body.get("rotation", (0.0, 0.0, 0.0)))

    with composite_undo(f"socket_add:{parent.name}/{full_name}"):
        empty = bpy.data.objects.new(name=full_name, object_data=None)
        empty.empty_display_type = "ARROWS"
        empty.empty_display_size = 0.25
        empty.parent = parent
        empty.location = location
        empty.rotation_euler = rotation
        bpy.context.scene.collection.objects.link(empty)

    return {
        "ok": True,
        "data": {
            "socketObjectName": empty.name,
            "parentName": parent.name,
            "location": list(empty.location),
        },
        "refs": {"objectName": empty.name, "parentObjectName": parent.name},
    }
