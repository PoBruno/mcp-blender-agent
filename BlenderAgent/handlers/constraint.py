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
            except (RuntimeError, TypeError) as exc:
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
        except (RuntimeError, TypeError) as exc:
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


# ----------------------------------------------------------------------------
# Inspection / removal / update — both bone and object scope
# ----------------------------------------------------------------------------

# Constraint attributes that are safe to serialize across every constraint
# type. Type-specific extras land in `params` as a dict.
_CONSTRAINT_BASE_ATTRS = (
    "name", "type", "enabled", "mute", "influence",
    "owner_space", "target_space",
)
# Generic per-type attributes worth surfacing if they exist on the constraint.
_CONSTRAINT_PARAM_ATTRS = (
    "subtarget", "head_tail", "use_bbone_shape",
    "chain_count", "pole_subtarget", "pole_angle",
    "use_x", "use_y", "use_z",
    "invert_x", "invert_y", "invert_z",
    "use_offset", "use_limit_x", "use_limit_y", "use_limit_z",
    "min_x", "max_x", "min_y", "max_y", "min_z", "max_z",
    "min_z", "max_z", "use_min_x", "use_max_x",
    "from_min_x", "from_max_x", "to_min_x", "to_max_x",
    "mix_mode", "mix_mode_rot", "mix_mode_scale",
    "use_world_space",
    "track_axis", "up_axis", "lock_axis", "rotation_range",
)


def _serialize_constraint(c: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for a in _CONSTRAINT_BASE_ATTRS:
        if hasattr(c, a):
            v = getattr(c, a)
            out[a] = v
    target = getattr(c, "target", None)
    out["targetObjectName"] = target.name if target is not None else None
    params: dict[str, Any] = {}
    for a in _CONSTRAINT_PARAM_ATTRS:
        if hasattr(c, a):
            v = getattr(c, a)
            # Only emit if not a default zero/empty — keep payload terse
            if isinstance(v, (int, float, bool, str)):
                params[a] = v
    out["params"] = params
    return out


@handler("POST", "/bone/list_constraints")
def bone_list_constraints(body: dict[str, Any]) -> dict[str, Any]:
    """List every constraint on a pose bone.

    Body: {armatureObjectName: str, boneName: str}
    Returns: {constraints: [{name,type,enabled,mute,influence,targetObjectName,params}]}
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    bone_name = body.get("boneName")
    if not bone_name:
        raise InvalidInputError("boneName is required")
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        raise BoneNotFoundError(f"pose bone {bone_name!r} not found")
    items = [_serialize_constraint(c) for c in pb.constraints]
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneName": bone_name,
            "count": len(items),
            "constraints": items,
        },
        "refs": {"armatureName": arm.name, "boneName": bone_name},
    }


@handler("POST", "/bone/remove_constraint")
def bone_remove_constraint(body: dict[str, Any]) -> dict[str, Any]:
    """Remove a constraint from a pose bone by name. Idempotent on absence."""
    arm = get_armature_object(body.get("armatureObjectName"))
    bone_name = body.get("boneName")
    c_name = body.get("constraintName")
    if not (bone_name and c_name):
        raise InvalidInputError("boneName and constraintName are required")
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        raise BoneNotFoundError(f"pose bone {bone_name!r} not found")
    c = pb.constraints.get(c_name)
    removed = False
    if c is not None:
        with composite_undo(f"bone_remove_constraint:{arm.name}/{bone_name}/{c_name}"):
            pb.constraints.remove(c)
            removed = True
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneName": bone_name,
            "constraintName": c_name,
            "removed": removed,
        },
    }


@handler("POST", "/bone/update_constraint")
def bone_update_constraint(body: dict[str, Any]) -> dict[str, Any]:
    """Update a bone constraint in place: enable/mute/influence + params dict.

    Body: {armatureObjectName, boneName, constraintName, params?: dict,
           targetObjectName?: str, targetBoneName?: str, enabled?: bool,
           mute?: bool, influence?: float}
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    bone_name = body.get("boneName")
    c_name = body.get("constraintName")
    if not (bone_name and c_name):
        raise InvalidInputError("boneName and constraintName are required")
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        raise BoneNotFoundError(f"pose bone {bone_name!r} not found")
    c = pb.constraints.get(c_name)
    if c is None:
        raise InvalidInputError(f"constraint {c_name!r} not found on bone {bone_name!r}")

    params = body.get("params") or {}
    with composite_undo(f"bone_update_constraint:{arm.name}/{bone_name}/{c_name}"):
        for key, attr in (("enabled", "enabled"), ("mute", "mute"), ("influence", "influence")):
            if key in body and hasattr(c, attr):
                setattr(c, attr, body[key])
        if "targetObjectName" in body:
            tgt = body["targetObjectName"]
            c.target = get_object(tgt) if tgt else None
        if "targetBoneName" in body and hasattr(c, "subtarget"):
            c.subtarget = body["targetBoneName"] or ""
        for k, v in params.items():
            if hasattr(c, k):
                try:
                    setattr(c, k, v)
                except (TypeError, AttributeError):
                    pass
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneName": bone_name,
            "constraint": _serialize_constraint(c),
        },
        "refs": {"armatureName": arm.name, "boneName": bone_name, "constraintName": c.name},
    }


@handler("POST", "/object/list_constraints")
def object_list_constraints(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    items = [_serialize_constraint(c) for c in obj.constraints]
    return {
        "ok": True,
        "data": {"objectName": obj.name, "count": len(items), "constraints": items},
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/object/remove_constraint")
def object_remove_constraint(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    c_name = body.get("constraintName")
    if not c_name:
        raise InvalidInputError("constraintName is required")
    c = obj.constraints.get(c_name)
    removed = False
    if c is not None:
        with composite_undo(f"object_remove_constraint:{obj.name}/{c_name}"):
            obj.constraints.remove(c)
            removed = True
    return {
        "ok": True,
        "data": {"objectName": obj.name, "constraintName": c_name, "removed": removed},
    }


@handler("POST", "/object/update_constraint")
def object_update_constraint(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    c_name = body.get("constraintName")
    if not c_name:
        raise InvalidInputError("constraintName is required")
    c = obj.constraints.get(c_name)
    if c is None:
        raise InvalidInputError(f"constraint {c_name!r} not found on object {obj.name!r}")
    params = body.get("params") or {}
    with composite_undo(f"object_update_constraint:{obj.name}/{c_name}"):
        for key, attr in (("enabled", "enabled"), ("mute", "mute"), ("influence", "influence")):
            if key in body and hasattr(c, attr):
                setattr(c, attr, body[key])
        if "targetObjectName" in body:
            tgt = body["targetObjectName"]
            c.target = get_object(tgt) if tgt else None
        for k, v in params.items():
            if hasattr(c, k):
                try:
                    setattr(c, k, v)
                except (TypeError, AttributeError):
                    pass
    return {
        "ok": True,
        "data": {"objectName": obj.name, "constraint": _serialize_constraint(c)},
        "refs": {"objectName": obj.name, "constraintName": c.name},
    }
