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
    """Add a SOCKET_<name> Empty as a child of a parent object or specific bone.

    Body: {
      objectName: str,          # parent object (typically the Armature)
      name: str,                # socket short name; auto-prefixed SOCKET_
      boneName?: str,           # if set AND parent is an ARMATURE, the empty
                                # is parented to this bone via parent_type='BONE'
                                # (UE5 detects this as a per-bone socket)
      location?: [x,y,z],       # local offset relative to the parent (or bone tail)
      rotation?: [x,y,z],       # Euler radians
    }

    For an Armature parent, omitting boneName parents the empty to the object's
    origin — that's almost never what you want for UE5 sockets. The handler
    raises InvalidInputError when boneName is provided but the bone doesn't
    exist in the armature.
    """
    import bpy  # type: ignore

    parent = get_object(body.get("objectName"))
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    bone_name = body.get("boneName")
    full_name = ue5_socket_name(name)
    location = tuple(body.get("location", (0.0, 0.0, 0.0)))
    rotation = tuple(body.get("rotation", (0.0, 0.0, 0.0)))

    if bone_name:
        if parent.type != "ARMATURE":
            raise InvalidInputError(
                f"boneName given but parent {parent.name!r} is {parent.type}, not ARMATURE"
            )
        if bone_name not in parent.data.bones:
            raise InvalidInputError(
                f"bone {bone_name!r} not found in armature {parent.name!r}"
            )

    with composite_undo(f"socket_add:{parent.name}/{full_name}"):
        # Reuse if already present (idempotent)
        empty = bpy.data.objects.get(full_name)
        if empty is None:
            empty = bpy.data.objects.new(name=full_name, object_data=None)
            bpy.context.scene.collection.objects.link(empty)
        empty.empty_display_type = "ARROWS"
        empty.empty_display_size = 0.05
        empty.parent = parent
        if bone_name:
            empty.parent_type = "BONE"
            empty.parent_bone = bone_name
        else:
            empty.parent_type = "OBJECT"
        empty.location = location
        empty.rotation_euler = rotation

    return {
        "ok": True,
        "data": {
            "socketObjectName": empty.name,
            "parentName": parent.name,
            "parentBone": bone_name or "",
            "parentType": empty.parent_type,
            "location": list(empty.location),
        },
        "refs": {
            "objectName": empty.name,
            "parentObjectName": parent.name,
            **({"boneName": bone_name} if bone_name else {}),
        },
    }
