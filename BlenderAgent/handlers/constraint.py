"""Bone constraint handlers (B7)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    BoneNotFoundError,
    InvalidInputError,
    composite_undo,
    get_armature_object,
    get_object,
    set_active_and_selected,
    with_mode,
)
from ..server import handler


@handler("POST", "/bone/add_constraint")
def bone_add_constraint(body: dict[str, Any]) -> dict[str, Any]:
    """Add a constraint to a pose bone.

    Body: {armatureObjectName: str, boneName: str, type: str,
           name?: str, params?: dict, targetObjectName?: str, targetBoneName?: str}
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    bone_name = body.get("boneName")
    c_type = body.get("type")
    if not bone_name or not c_type:
        raise InvalidInputError("boneName and type are required")
    name = body.get("name") or c_type.title()
    params = body.get("params") or {}
    target_obj_name = body.get("targetObjectName")
    target_bone_name = body.get("targetBoneName")

    with composite_undo(f"bone_add_constraint:{arm.name}/{bone_name}/{c_type}"):
        set_active_and_selected(arm)
        with with_mode(arm, "POSE"):
            pb = arm.pose.bones.get(bone_name)
            if pb is None:
                raise BoneNotFoundError(f"pose bone {bone_name!r} not found")
            try:
                c = pb.constraints.new(type=c_type)
            except RuntimeError as exc:
                raise InvalidInputError(f"Unknown constraint type {c_type!r}: {exc}") from exc
            c.name = name
            if target_obj_name:
                c.target = get_object(target_obj_name)
                if target_bone_name and hasattr(c, "subtarget"):
                    c.subtarget = target_bone_name
            for k, v in params.items():
                if hasattr(c, k):
                    setattr(c, k, v)
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneName": bone_name,
            "constraintName": c.name,
            "type": c.type,
        },
        "refs": {"armatureName": arm.name, "boneName": bone_name, "constraintName": c.name},
    }


@handler("POST", "/object/add_constraint")
def object_add_constraint(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    c_type = body.get("type")
    if not c_type:
        raise InvalidInputError("type is required")
    name = body.get("name") or c_type.title()
    params = body.get("params") or {}
    target_obj_name = body.get("targetObjectName")
    with composite_undo(f"object_add_constraint:{obj.name}/{c_type}"):
        try:
            c = obj.constraints.new(type=c_type)
        except RuntimeError as exc:
            raise InvalidInputError(f"Unknown constraint type {c_type!r}: {exc}") from exc
        c.name = name
        if target_obj_name:
            c.target = get_object(target_obj_name)
        for k, v in params.items():
            if hasattr(c, k):
                setattr(c, k, v)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "constraintName": c.name, "type": c.type},
        "refs": {"objectName": obj.name, "constraintName": c.name},
    }
