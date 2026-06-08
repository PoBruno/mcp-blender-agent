"""Bone (Edit + Pose) handlers (B7)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    BoneNotFoundError,
    InvalidInputError,
    composite_undo,
    get_armature_object,
    set_active_and_selected,
    with_3dview_context,
    with_mode,
)
from ..server import handler


@handler("POST", "/bone/add")
def bone_add(body: dict[str, Any]) -> dict[str, Any]:
    """Add an edit bone to an armature.

    Body: {armatureObjectName: str, name: str, head: [x,y,z], tail: [x,y,z],
           parentName?: str, useConnect?: bool, roll?: float}
    """
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("name")
    head = body.get("head")
    tail = body.get("tail")
    if not name or head is None or tail is None:
        raise InvalidInputError("name, head and tail are required")
    parent_name = body.get("parentName")
    use_connect = bool(body.get("useConnect", False))
    roll = float(body.get("roll", 0.0))

    with composite_undo(f"bone_add:{arm.name}/{name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            edit_bones = arm.data.edit_bones
            if name in edit_bones:
                raise InvalidInputError(f"Bone {name!r} already exists in {arm.name!r}")
            b = edit_bones.new(name=name)
            b.head = Vector(tuple(head))
            b.tail = Vector(tuple(tail))
            b.roll = roll
            if parent_name:
                if parent_name not in edit_bones:
                    raise BoneNotFoundError(f"parent {parent_name!r} not in armature {arm.name!r}")
                b.parent = edit_bones[parent_name]
                b.use_connect = use_connect

    return {
        "ok": True,
        "data": {"armatureObjectName": arm.name, "boneName": name, "parent": parent_name},
        "refs": {"armatureName": arm.name, "boneName": name},
    }


@handler("POST", "/bone/set_parent")
def bone_set_parent(body: dict[str, Any]) -> dict[str, Any]:
    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("boneName")
    parent_name = body.get("parentName")
    if not name:
        raise InvalidInputError("boneName is required")
    use_connect = bool(body.get("useConnect", False))

    with composite_undo(f"bone_set_parent:{arm.name}/{name}->{parent_name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            if name not in eb:
                raise BoneNotFoundError(f"{name!r} not in armature")
            b = eb[name]
            if parent_name:
                if parent_name not in eb:
                    raise BoneNotFoundError(f"parent {parent_name!r} not in armature")
                b.parent = eb[parent_name]
                b.use_connect = use_connect
            else:
                b.parent = None
                b.use_connect = False

    return {
        "ok": True,
        "data": {"armatureObjectName": arm.name, "boneName": name, "parent": parent_name},
        "refs": {"armatureName": arm.name, "boneName": name},
    }


@handler("POST", "/bone/rename")
def bone_rename(body: dict[str, Any]) -> dict[str, Any]:
    arm = get_armature_object(body.get("armatureObjectName"))
    old = body.get("oldName")
    new = body.get("newName")
    if not old or not new:
        raise InvalidInputError("oldName and newName are required")
    with composite_undo(f"bone_rename:{arm.name}/{old}->{new}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            if old not in eb:
                raise BoneNotFoundError(f"{old!r} not in armature")
            eb[old].name = new
            final = eb[new].name
    return {
        "ok": True,
        "data": {"armatureObjectName": arm.name, "oldName": old, "boneName": final},
        "refs": {"armatureName": arm.name, "boneName": final},
    }


@handler("POST", "/bone/set_pose_transform")
def bone_set_pose_transform(body: dict[str, Any]) -> dict[str, Any]:
    """Set the pose-bone transform (location/rotation_quaternion/scale)."""
    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("boneName")
    if not name:
        raise InvalidInputError("boneName is required")
    with composite_undo(f"bone_set_pose_transform:{arm.name}/{name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "POSE"):
            pb = arm.pose.bones.get(name)
            if pb is None:
                raise BoneNotFoundError(f"pose bone {name!r} not found in {arm.name!r}")
            if "location" in body:
                pb.location = tuple(body["location"])
            if "rotationQuaternion" in body:
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = tuple(body["rotationQuaternion"])
            elif "rotationEuler" in body:
                pb.rotation_mode = "XYZ"
                pb.rotation_euler = tuple(body["rotationEuler"])
            if "scale" in body:
                pb.scale = tuple(body["scale"])
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneName": name,
            "location": list(arm.pose.bones[name].location),
        },
        "refs": {"armatureName": arm.name, "boneName": name},
    }


@handler("POST", "/bone/delete")
def bone_delete(body: dict[str, Any]) -> dict[str, Any]:
    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("boneName")
    if not name:
        raise InvalidInputError("boneName is required")
    with composite_undo(f"bone_delete:{arm.name}/{name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            if name not in eb:
                raise BoneNotFoundError(f"{name!r} not in armature")
            eb.remove(eb[name])
    return {"ok": True, "data": {"armatureObjectName": arm.name, "deletedBone": name}}
