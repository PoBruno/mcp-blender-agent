"""Animation handlers (B6) — actions, NLA strips, keyframes."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    ActionNotFoundError,
    BoneNotFoundError,
    InvalidInputError,
    composite_undo,
    get_action,
    get_armature_object,
    get_object,
    with_mode,
)
from ..server import handler


@handler("POST", "/action/create")
def action_create(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    with composite_undo(f"action_create:{name}"):
        if name in bpy.data.actions:
            act = bpy.data.actions[name]
            return {
                "ok": True,
                "data": {"actionName": act.name, "created": False},
                "refs": {"actionName": act.name},
            }
        act = bpy.data.actions.new(name=name)
    return {"ok": True, "data": {"actionName": act.name, "created": True},
            "refs": {"actionName": act.name}}


def _action_fcurve_count(act: Any) -> int:
    """Count fcurves on an action across both legacy and Blender 4.4+ layered APIs.

    Legacy actions: act.fcurves (flat list).
    Layered actions: act.slots[*].channelbags(layer)[*].fcurves (nested).
    """
    # Legacy path — Blender < 4.4 or actions still in legacy mode.
    fc = getattr(act, "fcurves", None)
    if fc is not None:
        try:
            return len(fc)
        except TypeError:
            pass

    # Layered path — Blender 4.4+
    layers = getattr(act, "layers", None)
    slots = getattr(act, "slots", None)
    if layers is None or slots is None:
        return 0
    total = 0
    for layer in layers:
        for strip in getattr(layer, "strips", []):
            for slot in slots:
                cb = None
                if hasattr(strip, "channelbag"):
                    try:
                        cb = strip.channelbag(slot)
                    except (RuntimeError, TypeError):
                        cb = None
                if cb is not None and hasattr(cb, "fcurves"):
                    try:
                        total += len(cb.fcurves)
                    except TypeError:
                        pass
    return total


@handler("POST", "/action/list")
def action_list(body: dict[str, Any]) -> dict[str, Any]:
    """List every action in bpy.data.actions with frame range + fcurve count.

    Body: {namePattern?: str (substring filter)}

    Pure read; never mutates. Used to discover existing animations in a loaded
    .blend (e.g. before exporting each action to its own FBX). Handles both the
    legacy and Blender 4.4+ layered action APIs.
    """
    import bpy  # type: ignore

    pattern = body.get("namePattern")
    items: list[dict[str, Any]] = []
    for act in bpy.data.actions:
        if pattern and pattern not in act.name:
            continue
        fr = act.frame_range
        items.append(
            {
                "name": act.name,
                "frameStart": float(fr[0]),
                "frameEnd": float(fr[1]),
                "frameCount": int(fr[1] - fr[0]) + 1,
                "fcurveCount": _action_fcurve_count(act),
                "slotCount": len(getattr(act, "slots", []) or []),
                "useFakeUser": bool(act.use_fake_user),
                "users": int(act.users),
                "isLegacy": bool(getattr(act, "is_action_legacy", False)),
                "isLayered": bool(getattr(act, "is_action_layered", False)),
            }
        )
    return {"ok": True, "data": {"count": len(items), "actions": items}}


def _iter_fcurves(act: Any):
    """Yield every fcurve on an action, across legacy and layered APIs.

    Each yield is a tuple (data_path: str, array_index: int, keyframe_count: int).
    """
    # Legacy path
    fc = getattr(act, "fcurves", None)
    if fc is not None:
        try:
            for cu in fc:
                yield (cu.data_path or "", int(cu.array_index), len(cu.keyframe_points))
            return
        except TypeError:
            pass

    # Layered path
    layers = getattr(act, "layers", None)
    slots = getattr(act, "slots", None)
    if layers is None or slots is None:
        return
    for layer in layers:
        for strip in getattr(layer, "strips", []):
            for slot in slots:
                cb = None
                if hasattr(strip, "channelbag"):
                    try:
                        cb = strip.channelbag(slot)
                    except (RuntimeError, TypeError):
                        cb = None
                if cb is None or not hasattr(cb, "fcurves"):
                    continue
                try:
                    for cu in cb.fcurves:
                        yield (cu.data_path or "", int(cu.array_index), len(cu.keyframe_points))
                except TypeError:
                    pass


def _classify_data_path(dp: str) -> str:
    """Return 'bone' | 'shape_key' | 'object' | 'other' for an fcurve data_path."""
    if dp.startswith("pose.bones["):
        return "bone"
    if dp.startswith("key_blocks["):
        return "shape_key"
    if dp in ("location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle",
              "scale", "delta_location", "delta_rotation_euler", "delta_scale"):
        return "object"
    return "other"


def _bone_name_from_data_path(dp: str) -> str:
    """Extract the bone name from a pose.bones["X"]... data_path. '' if not bone."""
    if not dp.startswith('pose.bones["'):
        return ""
    end = dp.find('"]', 12)
    if end < 0:
        return ""
    return dp[12:end]


def _clear_action_fcurves(act: Any) -> int:
    """Remove every fcurve from an action across legacy and layered APIs.

    Returns the number of fcurves removed. Used by bake handlers that own an
    action entirely and must guarantee no stale keyframes from a previous run.
    """
    removed = 0
    fc = getattr(act, "fcurves", None)
    if fc is not None:
        try:
            for cu in list(fc):
                fc.remove(cu)
                removed += 1
            return removed
        except TypeError:
            pass

    layers = getattr(act, "layers", None)
    slots = getattr(act, "slots", None)
    if layers is None or slots is None:
        return removed
    for layer in layers:
        for strip in getattr(layer, "strips", []):
            for slot in slots:
                cb = None
                if hasattr(strip, "channelbag"):
                    try:
                        cb = strip.channelbag(slot)
                    except (RuntimeError, TypeError):
                        cb = None
                if cb is None or not hasattr(cb, "fcurves"):
                    continue
                try:
                    for cu in list(cb.fcurves):
                        cb.fcurves.remove(cu)
                        removed += 1
                except TypeError:
                    pass
    return removed


@handler("POST", "/action/inspect")
def action_inspect(body: dict[str, Any]) -> dict[str, Any]:
    """Deep-inspect an action: fcurve categories, touched bones, and a content
    hash usable for dedup.

    Body: {actionName: str}

    Returns:
        actionName, frameStart, frameEnd, frameCount,
        fcurveCount, boneFcurveCount, shapeKeyFcurveCount, objectFcurveCount,
        otherFcurveCount, hasBoneFcurves, hasShapeKeyFcurves, hasObjectFcurves,
        bones: [str] (sorted, unique bones touched),
        contentHash: str (sha1 of sorted (path, idx, kfCount) tuples — animations
                          with identical structure produce identical hashes; useful
                          for dedup of NLA push-down clones).
    """
    import hashlib

    act = get_action(body.get("actionName"))
    fr = act.frame_range

    bone_cnt = sk_cnt = obj_cnt = other_cnt = 0
    bones: set[str] = set()
    sig: list[tuple[str, int, int]] = []
    for dp, idx, kfn in _iter_fcurves(act):
        sig.append((dp, idx, kfn))
        cat = _classify_data_path(dp)
        if cat == "bone":
            bone_cnt += 1
            bn = _bone_name_from_data_path(dp)
            if bn:
                bones.add(bn)
        elif cat == "shape_key":
            sk_cnt += 1
        elif cat == "object":
            obj_cnt += 1
        else:
            other_cnt += 1

    sig.sort()
    h = hashlib.sha1()
    for dp, idx, kfn in sig:
        h.update(f"{dp}|{idx}|{kfn}\n".encode("utf-8"))

    total = bone_cnt + sk_cnt + obj_cnt + other_cnt
    return {
        "ok": True,
        "data": {
            "actionName": act.name,
            "frameStart": float(fr[0]),
            "frameEnd": float(fr[1]),
            "frameCount": int(fr[1] - fr[0]) + 1,
            "fcurveCount": total,
            "boneFcurveCount": bone_cnt,
            "shapeKeyFcurveCount": sk_cnt,
            "objectFcurveCount": obj_cnt,
            "otherFcurveCount": other_cnt,
            "hasBoneFcurves": bone_cnt > 0,
            "hasShapeKeyFcurves": sk_cnt > 0,
            "hasObjectFcurves": obj_cnt > 0,
            "bones": sorted(bones),
            "contentHash": h.hexdigest(),
        },
        "refs": {"actionName": act.name},
    }


@handler("POST", "/action/rename")
def action_rename(body: dict[str, Any]) -> dict[str, Any]:
    """Rename an action.

    Body: {actionName: str, newName: str}

    Idempotent: if actionName==newName, returns ok without touching the action.
    Refuses if newName already exists on a different action (returns
    INVALID_INPUT). Preserves use_fake_user and existing animation_data refs
    (Blender's name-key rename keeps refs intact).
    """
    import bpy  # type: ignore

    act = get_action(body.get("actionName"))
    new_name = body.get("newName")
    if not new_name or not isinstance(new_name, str):
        raise InvalidInputError("newName is required (non-empty string)")

    if act.name == new_name:
        return {
            "ok": True,
            "data": {"actionName": act.name, "renamed": False, "previousName": act.name},
            "refs": {"actionName": act.name},
        }

    existing = bpy.data.actions.get(new_name)
    if existing is not None and existing != act:
        raise InvalidInputError(
            f"action {new_name!r} already exists; rename would collide"
        )

    previous = act.name
    with composite_undo(f"action_rename:{previous}->{new_name}"):
        act.name = new_name

    return {
        "ok": True,
        "data": {
            "actionName": act.name,
            "renamed": True,
            "previousName": previous,
        },
        "refs": {"actionName": act.name},
    }


@handler("POST", "/action/assign_to_object")
def action_assign_to_object(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    action_name = body.get("actionName")
    if not action_name:
        raise InvalidInputError("actionName is required")
    act = get_action(action_name)
    with composite_undo(f"action_assign_to_object:{obj.name}/{act.name}"):
        if obj.animation_data is None:
            obj.animation_data_create()
        obj.animation_data.action = act
    return {
        "ok": True,
        "data": {"objectName": obj.name, "actionName": act.name},
        "refs": {"objectName": obj.name, "actionName": act.name},
    }


@handler("POST", "/action/unassign_from_object")
def action_unassign_from_object(body: dict[str, Any]) -> dict[str, Any]:
    """Clear the active action on an object. Used before bind-pose render so the
    armature evaluates at rest, not at whatever frame the last action drives.

    Idempotent: returns ok with `wasAssigned=false` when nothing was assigned.
    """
    obj = get_object(body.get("objectName"))
    prev = None
    if obj.animation_data is not None and obj.animation_data.action is not None:
        prev = obj.animation_data.action.name
        with composite_undo(f"action_unassign_from_object:{obj.name}"):
            obj.animation_data.action = None
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "wasAssigned": prev is not None,
            "previousActionName": prev or "",
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/keyframe/add")
def keyframe_add(body: dict[str, Any]) -> dict[str, Any]:
    """Add a keyframe.

    Body: {objectName: str, dataPath: str, frame: int, arrayIndex?: int}
    """
    obj = get_object(body.get("objectName"))
    data_path = body.get("dataPath")
    frame = body.get("frame")
    if not data_path or frame is None:
        raise InvalidInputError("dataPath and frame are required")
    array_index = body.get("arrayIndex", -1)
    with composite_undo(f"keyframe_add:{obj.name}/{data_path}@{frame}"):
        ok = obj.keyframe_insert(data_path=data_path, frame=int(frame), index=array_index)
    if not ok:
        raise InvalidInputError(
            f"keyframe_insert({obj.name!r}, {data_path!r}, frame={frame}) returned False"
        )
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "dataPath": data_path,
            "frame": int(frame),
            "arrayIndex": array_index,
        },
        "refs": {"objectName": obj.name, "actionName": obj.animation_data.action.name
                 if obj.animation_data and obj.animation_data.action else ""},
    }


@handler("POST", "/keyframe/bone_pose")
def keyframe_bone_pose(body: dict[str, Any]) -> dict[str, Any]:
    """Keyframe pose-bone location/rotation/scale.

    Body: {armatureObjectName: str, boneName: str, frame: int,
           channels?: ['location','rotation_quaternion','scale'] (default all)}
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    bone_name = body.get("boneName")
    frame = body.get("frame")
    if not bone_name or frame is None:
        raise InvalidInputError("boneName and frame are required")
    channels = body.get("channels") or ["location", "rotation_quaternion", "scale"]

    inserted: list[str] = []
    with composite_undo(f"keyframe_bone_pose:{arm.name}/{bone_name}@{frame}"):
        for ch in channels:
            path = f'pose.bones["{bone_name}"].{ch}'
            ok = arm.keyframe_insert(data_path=path, frame=int(frame))
            if ok:
                inserted.append(ch)
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneName": bone_name,
            "frame": int(frame),
            "insertedChannels": inserted,
        },
        "refs": {
            "armatureName": arm.name,
            "boneName": bone_name,
            "actionName": arm.animation_data.action.name
            if arm.animation_data and arm.animation_data.action else "",
        },
    }


@handler("POST", "/aim_offset/bake_9_pose_matrix")
def aim_offset_bake_9_pose_matrix(body: dict[str, Any]) -> dict[str, Any]:
    """Bake a 9-pose AimOffset (3x3 yaw/pitch grid) by distributing rotation
    across spine + neck + head bones (ARTIS §3.3).

    Rotations are computed in WORLD space (yaw around world Z, pitch around
    world X by default) and converted to each bone's rest-local frame via
    conjugation: q_local = R_rest^-1 @ q_world @ R_rest. This makes the bake
    correct regardless of bone roll or whether the bone's local Y axis points
    up (typical humanoid) or somewhere else.

    Body: {
      armatureObjectName: str,
      actionName?: str (default 'AimOffset'),
      spineBoneName: str,            # e.g. 'spine_02'
      neckBoneName: str,             # e.g. 'neck_01'
      headBoneName: str,             # e.g. 'head_01'
      yawWeights?: [spine, neck, head],   # default [0.17, 0.22, 0.61] (39% body / 61% head)
      pitchWeights?: [spine, neck, head], # default [0.05, 0.15, 0.80] (pitch concentrated on head)
      yawDegMax?: float,             # default 90
      pitchDegMax?: float,           # default 45
      frameStart?: int,              # default 1 (frames 1..9)
      yawAxisWorld?: [x,y,z],        # default [0,0,1] — character "up" in world
      pitchAxisWorld?: [x,y,z],      # default [1,0,0] — character "right" in world
    }

    Frame layout (matches §3.3 table):
       1: yaw -max, pitch +max     2: yaw  0,    pitch +max     3: yaw +max, pitch +max
       4: yaw -max, pitch  0       5: yaw  0,    pitch  0       6: yaw +max, pitch  0
       7: yaw -max, pitch -max     8: yaw  0,    pitch -max     9: yaw +max, pitch -max

    Each bone gets its share (weight * angle) keyframed on the corresponding
    frame. Center pose (frame 5) is the neutral rest pose. Bones not present
    in the armature raise BONE_NOT_FOUND.
    """
    import math
    import bpy  # type: ignore
    from mathutils import Quaternion, Vector  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    action_name = body.get("actionName") or "AimOffset"
    spine_name = body.get("spineBoneName")
    neck_name = body.get("neckBoneName")
    head_name = body.get("headBoneName")
    if not (spine_name and neck_name and head_name):
        raise InvalidInputError(
            "spineBoneName, neckBoneName, headBoneName are all required"
        )

    yaw_weights = body.get("yawWeights") or [0.17, 0.22, 0.61]
    pitch_weights = body.get("pitchWeights") or [0.05, 0.15, 0.80]
    yaw_max_deg = float(body.get("yawDegMax", 90.0))
    pitch_max_deg = float(body.get("pitchDegMax", 45.0))
    frame_start = int(body.get("frameStart", 1))
    yaw_axis_world = Vector(tuple(body.get("yawAxisWorld") or (0.0, 0.0, 1.0))).normalized()
    pitch_axis_world = Vector(tuple(body.get("pitchAxisWorld") or (1.0, 0.0, 0.0))).normalized()

    if len(yaw_weights) != 3 or len(pitch_weights) != 3:
        raise InvalidInputError("yawWeights and pitchWeights must each be 3 floats (spine, neck, head)")

    # Validate bones exist
    pose_bones = arm.pose.bones
    for n in (spine_name, neck_name, head_name):
        if n not in pose_bones:
            raise BoneNotFoundError(f"{n!r} not in armature {arm.name!r}")

    bones = [
        (spine_name, yaw_weights[0], pitch_weights[0]),
        (neck_name, yaw_weights[1], pitch_weights[1]),
        (head_name, yaw_weights[2], pitch_weights[2]),
    ]

    # 9-pose layout: (frame_offset, yaw_factor, pitch_factor) where factors ∈ {-1, 0, +1}
    poses = [
        (0, -1, +1), (1, 0, +1), (2, +1, +1),
        (3, -1, 0),  (4, 0, 0),  (5, +1, 0),
        (6, -1, -1), (7, 0, -1), (8, +1, -1),
    ]

    with composite_undo(f"aim_offset_bake:{arm.name}/{action_name}"):
        # Ensure action exists and is assigned
        if action_name in bpy.data.actions:
            act = bpy.data.actions[action_name]
            # Clear any stale fcurves so re-baking after a config change doesn't
            # leave old bone keyframes alongside the new ones. We clear EVERY
            # fcurve in the action — this handler owns the action entirely.
            _clear_action_fcurves(act)
        else:
            act = bpy.data.actions.new(name=action_name)
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act

        # Switch to pose mode for keyframing
        with with_mode(arm, "POSE"):
            # Pre-compute per-bone rest-orientation in world space; we conjugate
            # the desired world rotation into the bone's local frame so the bake
            # is independent of bone roll / local axis convention.
            arm_world = arm.matrix_world
            rest_world_rots = {}
            for bname, _yw, _pw in bones:
                rest_world_rots[bname] = (arm_world @ arm.pose.bones[bname].bone.matrix_local).to_quaternion()

            for f_off, yaw_f, pitch_f in poses:
                frame = frame_start + f_off
                for bname, yaw_w, pitch_w in bones:
                    pb = arm.pose.bones[bname]
                    yaw_rad = math.radians(yaw_max_deg * yaw_f * yaw_w)
                    pitch_rad = math.radians(pitch_max_deg * pitch_f * pitch_w)
                    # Desired rotation share in WORLD space:
                    q_world = (
                        Quaternion(yaw_axis_world, yaw_rad)
                        @ Quaternion(pitch_axis_world, pitch_rad)
                    )
                    # Convert to bone-local: q_local = R_rest^-1 @ q_world @ R_rest
                    rest_rot = rest_world_rots[bname]
                    q_local = rest_rot.inverted() @ q_world @ rest_rot
                    pb.rotation_mode = "QUATERNION"
                    pb.rotation_quaternion = q_local
                    arm.keyframe_insert(
                        data_path=f'pose.bones["{bname}"].rotation_quaternion',
                        frame=frame,
                    )
            # Set scene frame range
            scn = bpy.context.scene
            scn.frame_start = frame_start
            scn.frame_end = frame_start + 8

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "actionName": act.name,
            "frameStart": frame_start,
            "frameEnd": frame_start + 8,
            "poseCount": 9,
            "bones": [
                {"name": spine_name, "yawShare": yaw_weights[0], "pitchShare": pitch_weights[0]},
                {"name": neck_name, "yawShare": yaw_weights[1], "pitchShare": pitch_weights[1]},
                {"name": head_name, "yawShare": yaw_weights[2], "pitchShare": pitch_weights[2]},
            ],
        },
        "refs": {
            "armatureName": arm.name,
            "actionName": act.name,
        },
    }


# 3×3 grid cell names in source-frame order (frame 1..9).
# Matches the bake layout in /aim_offset/bake_9_pose_matrix:
#   1:LU  2:CU  3:RU
#   4:LC  5:CC  6:RC
#   7:LD  8:CD  9:RD
# Two-letter code: <Horizontal (L/C/R)><Vertical (U/C/D)> — UE5
# BlendSpace2D convention. The 9 cells become 9 standalone AnimSequences.
_AIM_CELL_NAMES = ["LU", "CU", "RU", "LC", "CC", "RC", "LD", "CD", "RD"]


@handler("POST", "/aim_offset/split_to_9_single_frame_actions")
def aim_offset_split_to_9_single_frame_actions(body: dict[str, Any]) -> dict[str, Any]:
    """Split a baked 9-pose AimOffset action into 9 single-frame actions, one
    per grid cell, so UE5's BlendSpace2D can ingest each pose as its own
    AnimSequence.

    Source action must have keyframes at frames `frameStart .. frameStart+8`
    on bone channels (the layout produced by /aim_offset/bake_9_pose_matrix).

    For each cell i ∈ 0..8 we:
      - Assign the source action to the armature and `scene.frame_set` to the
        source frame so the depsgraph evaluates the pose.
      - Snapshot every touched pose bone's transform channels (whatever the
        source action keyframes — typically rotation_quaternion).
      - Create (or overwrite) a new action named `<targetPrefix><cellName>`
        where cellName ∈ {LU, CU, RU, LC, CC, RC, LD, CD, RD}.
      - Assign the new action and write a single keyframe at frame 1 on every
        snapshotted channel via `armature.keyframe_insert` — this is layered-
        API safe (Blender 4.4+ channelbags handled transparently).

    Returns: { actionNames: [9], createdCount, overwrittenCount, cellNames }
    """
    import bpy  # type: ignore

    arm_name = body.get("armatureObjectName")
    if not arm_name:
        raise InvalidInputError("armatureObjectName is required")
    arm = get_armature_object(arm_name)

    src_name = body.get("sourceActionName")
    if not src_name:
        raise InvalidInputError("sourceActionName is required")
    src = bpy.data.actions.get(src_name)
    if src is None:
        raise InvalidInputError(f"action {src_name!r} not found")

    frame_start = int(body.get("frameStart", 1))
    target_prefix = body.get("targetPrefix") or f"{src_name}_"

    # Discover which bones + which channels the source action keyframes.
    # We use the layered-API-safe _iter_fcurves helper to enumerate data_paths.
    bone_channels: dict[str, set[str]] = {}  # bone_name → {"rotation_quaternion", "location", ...}
    for data_path, _array_index, _kp_count in _iter_fcurves(src):
        bname = _bone_name_from_data_path(data_path)
        if not bname:
            continue
        # data_path is e.g. pose.bones["spine_02"].rotation_quaternion
        suffix = data_path.rsplit("].", 1)[-1] if "]." in data_path else ""
        if not suffix:
            continue
        bone_channels.setdefault(bname, set()).add(suffix)

    if not bone_channels:
        raise InvalidInputError(
            f"source action {src_name!r} has no pose-bone fcurves to split"
        )

    pose_bones = arm.pose.bones
    missing = [b for b in bone_channels if b not in pose_bones]
    if missing:
        raise BoneNotFoundError(
            f"source action touches bones not in armature {arm.name!r}: {missing}"
        )

    created: list[str] = []
    overwritten: list[str] = []
    out_names: list[str] = []

    scene = bpy.context.scene
    saved_frame = scene.frame_current
    saved_action = arm.animation_data.action if arm.animation_data else None

    try:
        with composite_undo(f"aim_offset_split:{src_name}"):
            with with_mode(arm, "POSE"):
                for i, cell in enumerate(_AIM_CELL_NAMES):
                    # 1. Evaluate source pose at the source frame
                    if arm.animation_data is None:
                        arm.animation_data_create()
                    arm.animation_data.action = src
                    scene.frame_set(frame_start + i)

                    # 2. Snapshot every touched channel
                    snapshot: dict[tuple[str, str], Any] = {}
                    for bname, channels in bone_channels.items():
                        pb = pose_bones[bname]
                        for ch in channels:
                            val = getattr(pb, ch, None)
                            if val is None:
                                continue
                            # Copy mutable vector / quaternion values
                            snapshot[(bname, ch)] = (
                                tuple(val) if hasattr(val, "__iter__") else val
                            )

                    # 3. Create / overwrite target action
                    tgt_name = f"{target_prefix}{cell}"
                    out_names.append(tgt_name)
                    tgt = bpy.data.actions.get(tgt_name)
                    if tgt is None:
                        tgt = bpy.data.actions.new(name=tgt_name)
                        created.append(tgt_name)
                    else:
                        _clear_action_fcurves(tgt)
                        overwritten.append(tgt_name)

                    # 4. Assign target action and key the snapshot at frame 1
                    arm.animation_data.action = tgt
                    scene.frame_set(1)
                    for (bname, ch), val in snapshot.items():
                        pb = pose_bones[bname]
                        # Restore the channel value, then keyframe it
                        if isinstance(val, tuple):
                            setattr(pb, ch, val)
                        else:
                            setattr(pb, ch, val)
                        arm.keyframe_insert(
                            data_path=f'pose.bones["{bname}"].{ch}',
                            frame=1,
                        )
    finally:
        # Restore scene state
        if arm.animation_data is not None:
            arm.animation_data.action = saved_action
        scene.frame_set(saved_frame)

    return {
        "ok": True,
        "data": {
            "sourceActionName": src_name,
            "actionNames": out_names,
            "createdCount": len(created),
            "overwrittenCount": len(overwritten),
            "cellNames": _AIM_CELL_NAMES,
            "bonesTouched": sorted(bone_channels.keys()),
        },
        "refs": {"actionNames": out_names},
    }


@handler("POST", "/aim_offset/validate_9_pose_matrix")
def aim_offset_validate_9_pose_matrix(body: dict[str, Any]) -> dict[str, Any]:
    """Validate a baked 9-pose AimOffset by measuring the WORLD-space rotation
    delta of a probe bone (typically the head) at each pose frame and comparing
    against the expected yaw/pitch.

    Per-pose metric is the QUATERNION GEODESIC DISTANCE between the actual
    delta and the expected `Q_yaw @ Q_pitch`. This is the correct invariant
    for composed rotations — Euler decomposition fails on corners because the
    chain (spine→neck→head) doesn't commute.

    For reporting we also emit the actual yaw/pitch as decomposed in 'ZXY'
    order (which IS clean for pure-axis poses 2, 4, 5, 6, 8) so artists can
    eyeball single-axis bones easily.

    Body: {
      armatureObjectName: str,
      actionName?: str (default 'AimOffset'),
      probeBoneName: str,            # bone whose world rotation is measured (typically head)
      yawDegMax?: float,             # default 90
      pitchDegMax?: float,           # default 45
      frameStart?: int,              # default 1
      toleranceDeg?: float,          # default 5.0 (on quaternion angle)
      yawAxisWorld?: [x,y,z],        # default [0,0,1]
      pitchAxisWorld?: [x,y,z],      # default [1,0,0]
    }
    """
    import math
    import bpy  # type: ignore
    from mathutils import Quaternion, Vector  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    action_name = body.get("actionName") or "AimOffset"
    probe_name = body.get("probeBoneName")
    if not probe_name:
        raise InvalidInputError("probeBoneName is required (typically the head bone)")
    yaw_max_deg = float(body.get("yawDegMax", 90.0))
    pitch_max_deg = float(body.get("pitchDegMax", 45.0))
    frame_start = int(body.get("frameStart", 1))
    tolerance = float(body.get("toleranceDeg", 5.0))
    yaw_axis = Vector(tuple(body.get("yawAxisWorld") or (0.0, 0.0, 1.0))).normalized()
    pitch_axis = Vector(tuple(body.get("pitchAxisWorld") or (1.0, 0.0, 0.0))).normalized()

    if action_name not in bpy.data.actions:
        raise InvalidInputError(f"action {action_name!r} not found")
    if probe_name not in arm.pose.bones:
        raise BoneNotFoundError(f"{probe_name!r} not in armature {arm.name!r}")

    # Make sure the action is the one being evaluated
    if arm.animation_data is None:
        arm.animation_data_create()
    prev_action = arm.animation_data.action
    arm.animation_data.action = bpy.data.actions[action_name]

    poses = [
        (0, -1, +1), (1, 0, +1), (2, +1, +1),
        (3, -1, 0),  (4, 0, 0),  (5, +1, 0),
        (6, -1, -1), (7, 0, -1), (8, +1, -1),
    ]

    scn = bpy.context.scene
    saved_frame = scn.frame_current

    pb = arm.pose.bones[probe_name]
    rest_world_rot = (arm.matrix_world @ pb.bone.matrix_local).to_quaternion()

    results = []
    max_err = 0.0
    try:
        for f_off, yaw_f, pitch_f in poses:
            frame = frame_start + f_off
            scn.frame_set(frame)
            pose_world_mat = arm.matrix_world @ pb.matrix
            pose_world_rot = pose_world_mat.to_quaternion()
            delta = pose_world_rot @ rest_world_rot.inverted()

            # Expected world rotation = same composition the bake applies
            expected_yaw_rad = math.radians(yaw_max_deg * yaw_f)
            expected_pitch_rad = math.radians(pitch_max_deg * pitch_f)
            expected = (
                Quaternion(yaw_axis, expected_yaw_rad)
                @ Quaternion(pitch_axis, expected_pitch_rad)
            )

            # Geodesic distance: angle of (delta @ expected^-1). Use abs(w) to
            # collapse the q ≡ -q double-cover.
            diff = delta @ expected.inverted()
            w = max(-1.0, min(1.0, abs(diff.w)))
            angle_err_deg = math.degrees(2.0 * math.acos(w))
            max_err = max(max_err, angle_err_deg)

            # Decompose-for-reporting (clean only on single-axis poses).
            eul = delta.to_euler("ZXY")
            results.append({
                "frame": frame,
                "expectedYawDeg": round(math.degrees(expected_yaw_rad), 3),
                "actualYawDeg": round(math.degrees(eul.z), 3),
                "expectedPitchDeg": round(math.degrees(expected_pitch_rad), 3),
                "actualPitchDeg": round(math.degrees(eul.x), 3),
                "angleErrorDeg": round(angle_err_deg, 3),
                "pass": angle_err_deg <= tolerance,
            })
    finally:
        scn.frame_set(saved_frame)
        if prev_action is not None:
            arm.animation_data.action = prev_action

    all_pass = all(p["pass"] for p in results)
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "actionName": action_name,
            "probeBoneName": probe_name,
            "toleranceDeg": tolerance,
            "maxErrorDeg": round(max_err, 3),
            "allPass": all_pass,
            "poses": results,
        },
        "refs": {
            "armatureName": arm.name,
            "actionName": action_name,
            "boneName": probe_name,
        },
    }


@handler("POST", "/nla/push_action_to_strip")
def nla_push_action_to_strip(body: dict[str, Any]) -> dict[str, Any]:
    """Push the active action onto a new NLA strip for the object."""
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    if obj.animation_data is None or obj.animation_data.action is None:
        raise InvalidInputError(f"{obj.name!r} has no active action to push")
    track_name = body.get("trackName") or "NlaTrack"

    with composite_undo(f"nla_push_action_to_strip:{obj.name}"):
        act = obj.animation_data.action
        track = obj.animation_data.nla_tracks.new()
        track.name = track_name
        track.strips.new(name=act.name, start=int(act.frame_range[0]), action=act)
        obj.animation_data.action = None

    return {
        "ok": True,
        "data": {"objectName": obj.name, "trackName": track.name, "actionName": act.name},
        "refs": {"objectName": obj.name, "actionName": act.name},
    }


@handler("POST", "/scene/set_frame_range")
def scene_set_frame_range(body: dict[str, Any]) -> dict[str, Any]:
    """Set the scene's animation range and/or current frame.

    Body: {sceneName?: str, frameStart?: int, frameEnd?: int, frameCurrent?: int}

    All fields are optional. When only frameCurrent is provided, the start/end
    range is left untouched — handy for stepping through poses while rendering
    validation stills. Defaults preserve current values when a field is omitted.
    """
    import bpy  # type: ignore
    scene_name = body.get("sceneName")
    scene = bpy.data.scenes[scene_name] if scene_name else bpy.context.scene
    start = body.get("frameStart")
    end = body.get("frameEnd")
    cur = body.get("frameCurrent")
    if start is None and end is None and cur is None:
        # Back-compat default behaviour
        start = 1
        end = 250
    with composite_undo(f"scene_set_frame_range:{scene.name}"):
        if start is not None:
            scene.frame_start = int(start)
        if end is not None:
            scene.frame_end = int(end)
        if cur is not None:
            scene.frame_set(int(cur))
    return {
        "ok": True,
        "data": {
            "sceneName": scene.name,
            "frameStart": scene.frame_start,
            "frameEnd": scene.frame_end,
            "frameCurrent": scene.frame_current,
        },
        "refs": {"sceneName": scene.name},
    }
