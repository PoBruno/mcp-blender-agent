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


@handler("POST", "/bone/delete_by_pattern")
def bone_delete_by_pattern(body: dict[str, Any]) -> dict[str, Any]:
    """Bulk-delete edit bones whose name matches a regex pattern.

    Used to strip leaf/_end artifact bones the FBX exporter would otherwise
    carry into UE5. Children of a deleted bone are reparented to the deleted
    bone's parent so the chain stays intact.

    Body: {
      armatureObjectName: str,
      pattern: str,            # Python regex (re.search semantics)
      dryRun?: bool,           # default false — when true, just lists matches
      excludeRoots?: bool,     # default true — never delete a bone with no parent
    }

    Returns: {deletedBones: [str], skippedRoots: [str], matchedCount: int}
    """
    import re
    arm = get_armature_object(body.get("armatureObjectName"))
    pattern = body.get("pattern")
    if not pattern:
        raise InvalidInputError("pattern is required")
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise InvalidInputError(f"invalid regex {pattern!r}: {exc}") from exc
    dry_run = bool(body.get("dryRun", False))
    exclude_roots = bool(body.get("excludeRoots", True))

    deleted: list[str] = []
    skipped_roots: list[str] = []

    with composite_undo(f"bone_delete_by_pattern:{arm.name}/{pattern}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            # Snapshot names first — mutating eb while iterating breaks the loop.
            candidates = [b.name for b in eb if rx.search(b.name)]
            if dry_run:
                return {
                    "ok": True,
                    "data": {
                        "armatureObjectName": arm.name,
                        "pattern": pattern,
                        "dryRun": True,
                        "matchedCount": len(candidates),
                        "wouldDelete": candidates,
                    },
                    "refs": {"armatureName": arm.name},
                }
            # Sort by depth descending so children disappear before parents
            # (avoids reparenting work).
            def depth(b_name: str) -> int:
                b = eb.get(b_name)
                d = 0
                while b is not None and b.parent is not None:
                    d += 1
                    b = b.parent
                return d
            candidates.sort(key=depth, reverse=True)

            for name in candidates:
                if name not in eb:
                    continue
                b = eb[name]
                if exclude_roots and b.parent is None:
                    skipped_roots.append(name)
                    continue
                # Reparent any (still-existing) children up one level.
                new_parent = b.parent
                for child in list(b.children):
                    child.parent = new_parent
                eb.remove(b)
                deleted.append(name)

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "pattern": pattern,
            "dryRun": False,
            "matchedCount": len(candidates),
            "deletedBones": deleted,
            "skippedRoots": skipped_roots,
        },
        "refs": {"armatureName": arm.name},
    }


@handler("POST", "/bone/list")
def bone_list(body: dict[str, Any]) -> dict[str, Any]:
    """List all edit bones with head/tail/roll/parent/length.

    Body: {armatureObjectName: str, namePattern?: str (substring filter)}

    Used by agents to audit armatures (verify UE5 roll convention, find bones
    with rolled axes, build a name-set for renaming).
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    pattern = body.get("namePattern")
    bones_data: list[dict[str, Any]] = []
    with composite_undo(f"bone_list:{arm.name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            for b in arm.data.edit_bones:
                if pattern and pattern not in b.name:
                    continue
                bones_data.append(
                    {
                        "name": b.name,
                        "head": list(b.head),
                        "tail": list(b.tail),
                        "roll": float(b.roll),
                        "length": float(b.length),
                        "parent": b.parent.name if b.parent else None,
                        "useConnect": bool(b.use_connect),
                        "useDeform": bool(b.use_deform),
                    }
                )
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneCount": len(bones_data),
            "bones": bones_data,
        },
        "refs": {"armatureName": arm.name},
    }


@handler("POST", "/bone/set_edit_transform")
def bone_set_edit_transform(body: dict[str, Any]) -> dict[str, Any]:
    """Set head/tail/roll on an existing edit bone.

    Body: {armatureObjectName: str, boneName: str,
           head?: [x,y,z], tail?: [x,y,z], roll?: float,
           useDeform?: bool, useConnect?: bool}

    Pass only the keys you want to change.
    """
    from mathutils import Vector  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("boneName")
    if not name:
        raise InvalidInputError("boneName is required")

    head = body.get("head")
    tail = body.get("tail")
    roll = body.get("roll")
    use_deform = body.get("useDeform")
    use_connect = body.get("useConnect")

    with composite_undo(f"bone_set_edit_transform:{arm.name}/{name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            if name not in eb:
                raise BoneNotFoundError(f"{name!r} not in armature")
            b = eb[name]
            if head is not None:
                b.head = Vector(tuple(head))
            if tail is not None:
                b.tail = Vector(tuple(tail))
            if roll is not None:
                b.roll = float(roll)
            if use_deform is not None:
                b.use_deform = bool(use_deform)
            if use_connect is not None:
                b.use_connect = bool(use_connect)
            final_head = list(b.head)
            final_tail = list(b.tail)
            final_roll = float(b.roll)

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneName": name,
            "head": final_head,
            "tail": final_tail,
            "roll": final_roll,
        },
        "refs": {"armatureName": arm.name, "boneName": name},
    }


@handler("POST", "/bone/set_roll")
def bone_set_roll(body: dict[str, Any]) -> dict[str, Any]:
    """Set roll (rotation around the bone's Y-axis) on one or more edit bones.

    Body: {armatureObjectName: str, boneNames: [str, ...], roll: float (radians)}

    Use 0.0 to "clear" roll. Use bone/recalculate_roll for orientation-based
    auto-fix (e.g. align Z to global +Z).
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    bone_names = body.get("boneNames")
    if not bone_names:
        raise InvalidInputError("boneNames is required (list of str)")
    if isinstance(bone_names, str):
        bone_names = [bone_names]
    if "roll" not in body:
        raise InvalidInputError("roll is required (radians)")
    roll = float(body["roll"])

    updated: list[dict[str, Any]] = []
    with composite_undo(f"bone_set_roll:{arm.name}/{roll}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            for name in bone_names:
                if name not in eb:
                    raise BoneNotFoundError(f"{name!r} not in armature {arm.name!r}")
                eb[name].roll = roll
                updated.append({"name": name, "roll": float(eb[name].roll)})
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "updatedCount": len(updated),
            "bones": updated,
        },
        "refs": {"armatureName": arm.name},
    }


_RECALC_ROLL_TYPES = {
    "POS_X", "POS_Y", "POS_Z", "NEG_X", "NEG_Y", "NEG_Z",
    "GLOBAL_POS_X", "GLOBAL_POS_Y", "GLOBAL_POS_Z",
    "GLOBAL_NEG_X", "GLOBAL_NEG_Y", "GLOBAL_NEG_Z",
    "ACTIVE", "VIEW", "CURSOR",
}


@handler("POST", "/bone/recalculate_roll")
def bone_recalculate_roll(body: dict[str, Any]) -> dict[str, Any]:
    """Auto-recalculate roll on a set of bones using a reference orientation.

    Body: {armatureObjectName: str, boneNames: [str, ...],
           type?: str (default 'GLOBAL_POS_Z')}

    Wraps `bpy.ops.armature.calculate_roll`. Use 'GLOBAL_POS_Z' for UE5-style
    spine/neck/head bones (their Z local should point up). Use 'GLOBAL_NEG_Z'
    if the chain inverts.
    """
    import bpy  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    bone_names = body.get("boneNames")
    if not bone_names:
        raise InvalidInputError("boneNames is required (list of str)")
    if isinstance(bone_names, str):
        bone_names = [bone_names]
    roll_type = (body.get("type") or "GLOBAL_POS_Z").upper()
    if roll_type not in _RECALC_ROLL_TYPES:
        raise InvalidInputError(
            f"type {roll_type!r} not in {sorted(_RECALC_ROLL_TYPES)}"
        )

    rolls_after: list[dict[str, Any]] = []
    with composite_undo(f"bone_recalculate_roll:{arm.name}/{roll_type}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            for b in eb:
                b.select = False
                b.select_head = False
                b.select_tail = False
            for name in bone_names:
                if name not in eb:
                    raise BoneNotFoundError(f"{name!r} not in armature {arm.name!r}")
                eb[name].select = True
                eb[name].select_head = True
                eb[name].select_tail = True
            with with_3dview_context():
                try:
                    bpy.ops.armature.calculate_roll(type=roll_type)
                except (RuntimeError, TypeError) as exc:
                    raise InvalidInputError(
                        f"calculate_roll(type={roll_type!r}) failed: {exc}"
                    ) from exc
            for name in bone_names:
                rolls_after.append({"name": name, "roll": float(eb[name].roll)})

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "type": roll_type,
            "bones": rolls_after,
        },
        "refs": {"armatureName": arm.name},
    }
