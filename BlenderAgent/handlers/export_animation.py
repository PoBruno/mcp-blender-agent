"""FBX skeletal + animation export (B6, B7)."""

from __future__ import annotations

import os
from typing import Any

from ..helpers import (
    ExportFailedError,
    InvalidInputError,
    get_object,
)
from ..server import handler


def _ensure_dir(filepath: str) -> None:
    d = os.path.dirname(filepath)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


@handler("POST", "/export/fbx_skeletal")
def export_fbx_skeletal(body: dict[str, Any]) -> dict[str, Any]:
    """Export Armature + skinned meshes as FBX skeletal mesh."""
    import bpy  # type: ignore

    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    arm_name = body.get("armatureObjectName")
    if not arm_name:
        raise InvalidInputError("armatureObjectName is required")
    arm = get_object(arm_name)
    if arm.type != "ARMATURE":
        raise InvalidInputError(f"{arm_name!r} is not an ARMATURE")

    _ensure_dir(filepath)

    # Select armature + every mesh child
    for o in bpy.data.objects:
        o.select_set(False)
    arm.select_set(True)
    for child in arm.children:
        if child.type == "MESH":
            child.select_set(True)
    bpy.context.view_layer.objects.active = arm

    params = {
        "filepath": filepath,
        "use_selection": True,
        "global_scale": float(body.get("globalScale", 1.0)),
        "apply_unit_scale": bool(body.get("applyUnitScale", True)),
        "axis_forward": body.get("axisForward", "-Z"),
        "axis_up": body.get("axisUp", "Y"),
        "object_types": {"ARMATURE", "MESH", "EMPTY"},
        "use_mesh_modifiers": bool(body.get("useMeshModifiers", True)),
        "mesh_smooth_type": body.get("meshSmoothType", "FACE"),
        "use_tspace": bool(body.get("useTspace", True)),
        "add_leaf_bones": bool(body.get("addLeafBones", False)),
        "primary_bone_axis": body.get("primaryBoneAxis", "Y"),
        "secondary_bone_axis": body.get("secondaryBoneAxis", "X"),
        "use_armature_deform_only": bool(body.get("useArmatureDeformOnly", True)),
        "bake_space_transform": bool(body.get("bakeSpaceTransform", False)),
        "bake_anim": bool(body.get("bakeAnim", False)),
        "path_mode": body.get("pathMode", "AUTO"),
    }

    try:
        bpy.ops.export_scene.fbx(**params)
    except Exception as exc:  # noqa: BLE001
        raise ExportFailedError(f"FBX skeletal export failed: {exc}") from exc

    return {
        "ok": True,
        "data": {
            "filepath": os.path.abspath(filepath),
            "armatureObjectName": arm.name,
        },
        "refs": {"filepath": os.path.abspath(filepath), "armatureName": arm.name},
    }


@handler("POST", "/export/fbx_animation")
def export_fbx_animation(body: dict[str, Any]) -> dict[str, Any]:
    """Export an animation-only FBX (armature + baked actions)."""
    import bpy  # type: ignore

    filepath = body.get("filepath")
    arm_name = body.get("armatureObjectName")
    if not filepath or not arm_name:
        raise InvalidInputError("filepath and armatureObjectName required")
    arm = get_object(arm_name)
    if arm.type != "ARMATURE":
        raise InvalidInputError(f"{arm_name!r} is not an ARMATURE")
    _ensure_dir(filepath)

    for o in bpy.data.objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm

    params = {
        "filepath": filepath,
        "use_selection": True,
        "global_scale": float(body.get("globalScale", 1.0)),
        "apply_unit_scale": bool(body.get("applyUnitScale", True)),
        "axis_forward": body.get("axisForward", "-Z"),
        "axis_up": body.get("axisUp", "Y"),
        "object_types": {"ARMATURE"},
        "add_leaf_bones": bool(body.get("addLeafBones", False)),
        "primary_bone_axis": body.get("primaryBoneAxis", "Y"),
        "secondary_bone_axis": body.get("secondaryBoneAxis", "X"),
        "bake_space_transform": bool(body.get("bakeSpaceTransform", False)),
        "bake_anim": True,
        "bake_anim_use_all_bones": True,
        "bake_anim_use_nla_strips": bool(body.get("useNlaStrips", True)),
        "bake_anim_use_all_actions": bool(body.get("useAllActions", False)),
        "bake_anim_force_startend_keying": True,
        "bake_anim_step": float(body.get("bakeAnimStep", 1.0)),
        "bake_anim_simplify_factor": float(body.get("bakeAnimSimplifyFactor", 1.0)),
        "path_mode": body.get("pathMode", "AUTO"),
    }

    try:
        bpy.ops.export_scene.fbx(**params)
    except Exception as exc:  # noqa: BLE001
        raise ExportFailedError(f"FBX animation export failed: {exc}") from exc

    return {
        "ok": True,
        "data": {
            "filepath": os.path.abspath(filepath),
            "armatureObjectName": arm.name,
        },
        "refs": {"filepath": os.path.abspath(filepath), "armatureName": arm.name},
    }
