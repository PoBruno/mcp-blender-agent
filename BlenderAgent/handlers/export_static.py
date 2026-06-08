"""FBX static / glTF / collection-batch export handlers (B1 + B2)."""

from __future__ import annotations

import os
from typing import Any

from ..helpers import (
    ExportFailedError,
    InvalidInputError,
    composite_undo,
    get_collection,
    get_object,
    set_active_and_selected,
)
from ..server import handler


def _ensure_dir(filepath: str) -> None:
    d = os.path.dirname(filepath)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def _select_objects(names: list[str]) -> list[Any]:
    import bpy  # type: ignore
    for o in bpy.data.objects:
        o.select_set(False)
    selected: list[Any] = []
    for n in names:
        obj = get_object(n)
        obj.select_set(True)
        selected.append(obj)
    if selected:
        bpy.context.view_layer.objects.active = selected[0]
    return selected


@handler("POST", "/export/fbx_static")
def export_fbx_static(body: dict[str, Any]) -> dict[str, Any]:
    """Export selected objects as a static-mesh FBX with full UE5-compatible defaults.

    Per UE-TARGETS.md §7 — axis_forward='-Z', axis_up='Y', global_scale=1.0,
    apply_unit_scale=True, use_armature_deform_only=True, add_leaf_bones=False.
    """
    import bpy  # type: ignore

    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    object_names = body.get("objectNames", [])
    if not isinstance(object_names, list) or not object_names:
        raise InvalidInputError("objectNames must be a non-empty list")

    _ensure_dir(filepath)

    selected = _select_objects(object_names)
    if not selected:
        raise ExportFailedError("No objects resolved for export")

    params = {
        "filepath": filepath,
        "use_selection": True,
        "global_scale": float(body.get("globalScale", 1.0)),
        "apply_unit_scale": bool(body.get("applyUnitScale", True)),
        "apply_scale_options": body.get("applyScaleOptions", "FBX_SCALE_NONE"),
        "axis_forward": body.get("axisForward", "-Z"),
        "axis_up": body.get("axisUp", "Y"),
        "object_types": set(body.get("objectTypes", ["MESH", "EMPTY"])),
        "use_mesh_modifiers": bool(body.get("useMeshModifiers", True)),
        "mesh_smooth_type": body.get("meshSmoothType", "FACE"),
        "use_subsurf": bool(body.get("useSubsurf", False)),
        "use_mesh_edges": bool(body.get("useMeshEdges", False)),
        "use_tspace": bool(body.get("useTspace", True)),
        "use_triangles": bool(body.get("useTriangles", False)),
        "use_custom_props": bool(body.get("useCustomProps", False)),
        "add_leaf_bones": bool(body.get("addLeafBones", False)),
        "primary_bone_axis": body.get("primaryBoneAxis", "Y"),
        "secondary_bone_axis": body.get("secondaryBoneAxis", "X"),
        "use_armature_deform_only": bool(body.get("useArmatureDeformOnly", True)),
        "bake_anim": bool(body.get("bakeAnim", False)),
        "path_mode": body.get("pathMode", "AUTO"),
        "embed_textures": bool(body.get("embedTextures", False)),
        "batch_mode": body.get("batchMode", "OFF"),
        "bake_space_transform": bool(body.get("bakeSpaceTransform", False)),
    }

    try:
        bpy.ops.export_scene.fbx(**params)
    except Exception as exc:  # noqa: BLE001
        raise ExportFailedError(f"FBX export failed: {exc}") from exc

    return {
        "ok": True,
        "data": {
            "filepath": os.path.abspath(filepath),
            "exportedObjects": [o.name for o in selected],
            "objectCount": len(selected),
        },
        "refs": {"filepath": os.path.abspath(filepath)},
        "nextSteps": [
            "Import the FBX into UE5 as Static Mesh.",
            "Verify UCX_*/UBX_* children become collision primitives.",
        ],
    }


@handler("POST", "/export/fbx_collection_batch")
def export_fbx_collection_batch(body: dict[str, Any]) -> dict[str, Any]:
    """Export each top-level child of a collection as its own FBX file.

    Body: {collectionName: str, outputDirectory: str,
           filenameTemplate?: str (default 'SM_{ObjectName}.fbx'),
           includeCollisionChildren?: bool (default true),
           ...standard FBX params...}
    """
    import bpy  # type: ignore

    col = get_collection(body.get("collectionName"))
    out_dir = body.get("outputDirectory")
    if not out_dir:
        raise InvalidInputError("outputDirectory is required")
    template = body.get("filenameTemplate", "SM_{ObjectName}.fbx")
    include_collision = bool(body.get("includeCollisionChildren", True))

    os.makedirs(out_dir, exist_ok=True)

    exported: list[str] = []
    failures: list[dict[str, str]] = []

    base_params = dict(body)
    base_params.pop("collectionName", None)
    base_params.pop("outputDirectory", None)
    base_params.pop("filenameTemplate", None)
    base_params.pop("includeCollisionChildren", None)

    with composite_undo(f"export_fbx_collection_batch:{col.name}"):
        for obj in list(col.objects):
            if obj.parent is not None:
                # Skip children — they're exported as part of their parent
                continue
            filename = template.replace("{ObjectName}", obj.name)
            filepath = os.path.join(out_dir, filename)
            names = [obj.name]
            if include_collision:
                for child in obj.children:
                    if child.name.startswith(("UCX_", "UBX_", "USP_", "UCP_", "SOCKET_", "LOD_")):
                        names.append(child.name)
            try:
                export_fbx_static({**base_params, "filepath": filepath, "objectNames": names})
                exported.append(filepath)
            except Exception as exc:  # noqa: BLE001
                failures.append({"object": obj.name, "error": str(exc)})

    return {
        "ok": True,
        "data": {
            "collectionName": col.name,
            "outputDirectory": os.path.abspath(out_dir),
            "exportedCount": len(exported),
            "failureCount": len(failures),
            "failures": failures,
        },
        "refs": {"filepaths": exported},
    }


@handler("POST", "/export/gltf")
def export_gltf(body: dict[str, Any]) -> dict[str, Any]:
    """Export selection as glTF 2.0 (.glb or .gltf)."""
    import bpy  # type: ignore

    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    object_names = body.get("objectNames", [])
    if not isinstance(object_names, list) or not object_names:
        raise InvalidInputError("objectNames must be a non-empty list")
    _ensure_dir(filepath)
    _select_objects(object_names)

    params = {
        "filepath": filepath,
        "use_selection": True,
        "export_format": body.get("exportFormat", "GLB"),
        "export_apply": bool(body.get("exportApply", True)),
        "export_animations": bool(body.get("exportAnimations", False)),
        "export_yup": bool(body.get("exportYup", True)),
        "export_extras": bool(body.get("exportExtras", False)),
    }
    try:
        bpy.ops.export_scene.gltf(**params)
    except Exception as exc:  # noqa: BLE001
        raise ExportFailedError(f"glTF export failed: {exc}") from exc

    return {
        "ok": True,
        "data": {"filepath": os.path.abspath(filepath), "objectCount": len(object_names)},
        "refs": {"filepath": os.path.abspath(filepath)},
    }
