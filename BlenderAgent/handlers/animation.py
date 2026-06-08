"""Animation handlers (B6) — actions, NLA strips, keyframes."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    ActionNotFoundError,
    InvalidInputError,
    composite_undo,
    get_action,
    get_armature_object,
    get_object,
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
    import bpy  # type: ignore
    scene_name = body.get("sceneName")
    scene = bpy.data.scenes[scene_name] if scene_name else bpy.context.scene
    start = int(body.get("frameStart", 1))
    end = int(body.get("frameEnd", 250))
    with composite_undo(f"scene_set_frame_range:{scene.name}"):
        scene.frame_start = start
        scene.frame_end = end
    return {
        "ok": True,
        "data": {"sceneName": scene.name, "frameStart": start, "frameEnd": end},
        "refs": {"sceneName": scene.name},
    }
