"""Post-processing pipeline handlers — retopology, UV, decimate, LOD.

These are the canonical "Phase 7" tools from the aaa-modeling skill: after
silhouette is approved, run these to produce engine-ready meshes.

Endpoints
---------
- /postproc/voxel_remesh         — bpy.ops.object.voxel_remesh
- /postproc/quad_remesh          — bpy.ops.object.quadriflow_remesh
- /postproc/smart_uv_project     — bpy.ops.uv.smart_project on every selected face
- /postproc/decimate             — DECIMATE modifier (collapse/un-subdiv/planar)
- /postproc/lod_generate         — N levels via decimate at decreasing ratios
- /postproc/auto_smooth_normals  — smooth shading + auto-smooth angle
"""

from __future__ import annotations

from typing import Any, List

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_object,
    set_active_and_selected,
    with_3dview_context,
    with_mode,
)
from ..server import handler


def _ensure_mesh(obj: Any) -> None:
    if obj.type != "MESH":
        raise InvalidInputError(f"Object {obj.name!r} type is {obj.type}, expected MESH")


# ---------------------------------------------------------------------------
# voxel_remesh
# ---------------------------------------------------------------------------

@handler("POST", "/postproc/voxel_remesh", timeout=300.0)
def postproc_voxel_remesh(body: dict[str, Any]) -> dict[str, Any]:
    """Voxel-remesh an object to uniform topology. Heals intersections.

    Body:
        objectName: str
        voxelSize: float            — default 0.02 (smaller = denser mesh)
        adaptivity?: float          — 0..1, default 0.0
        useSmoothShade?: bool       — default True
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    voxel_size = float(body.get("voxelSize", 0.02))
    if voxel_size <= 0:
        raise InvalidInputError("voxelSize must be > 0")
    adaptivity = float(body.get("adaptivity", 0.0))
    use_smooth = bool(body.get("useSmoothShade", True))

    with composite_undo(f"postproc_voxel_remesh:{obj.name}"):
        obj.data.remesh_voxel_size = voxel_size
        obj.data.remesh_voxel_adaptivity = adaptivity
        if hasattr(obj.data, "use_remesh_smooth_normals"):
            obj.data.use_remesh_smooth_normals = use_smooth
        set_active_and_selected(obj)
        with with_3dview_context():
            bpy.ops.object.voxel_remesh()

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "voxelSize": voxel_size,
            "newVertexCount": len(obj.data.vertices),
            "newFaceCount": len(obj.data.polygons),
        },
        "refs": {"objectName": obj.name},
    }


# ---------------------------------------------------------------------------
# quad_remesh (QuadriFlow)
# ---------------------------------------------------------------------------

@handler("POST", "/postproc/quad_remesh", timeout=300.0)
def postproc_quad_remesh(body: dict[str, Any]) -> dict[str, Any]:
    """Quad-remesh (QuadriFlow) for clean quad-dominant topology.

    Body:
        objectName: str
        targetFaces?: int          — default 2000
        useMeshSymmetry?: bool     — default False
        useSharpEdges?: bool       — default True
        useSmoothNormals?: bool    — default True
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    target_faces = int(body.get("targetFaces", 2000))
    if target_faces < 16:
        raise InvalidInputError("targetFaces must be >= 16")
    use_sym = bool(body.get("useMeshSymmetry", False))
    use_sharp = bool(body.get("useSharpEdges", True))
    use_smooth = bool(body.get("useSmoothNormals", True))

    with composite_undo(f"postproc_quad_remesh:{obj.name}"):
        set_active_and_selected(obj)
        with with_3dview_context():
            bpy.ops.object.quadriflow_remesh(
                target_faces=target_faces,
                use_mesh_symmetry=use_sym,
                use_preserve_sharp=use_sharp,
                use_preserve_boundary=True,
                smooth_normals=use_smooth,
                mode="FACES",
            )

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "requestedFaces": target_faces,
            "actualFaceCount": len(obj.data.polygons),
            "vertexCount": len(obj.data.vertices),
        },
        "refs": {"objectName": obj.name},
    }


# ---------------------------------------------------------------------------
# smart_uv_project
# ---------------------------------------------------------------------------

@handler("POST", "/postproc/smart_uv_project")
def postproc_smart_uv_project(body: dict[str, Any]) -> dict[str, Any]:
    """Smart UV project across the whole mesh.

    Body:
        objectName: str
        angleLimit?: float (deg)   — default 66
        islandMargin?: float       — default 0.02
        areaWeight?: float         — 0..1, default 0.0
        correctAspect?: bool       — default True
        scaleToBounds?: bool       — default True
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    angle_limit = float(body.get("angleLimit", 66.0))
    island_margin = float(body.get("islandMargin", 0.02))
    area_weight = float(body.get("areaWeight", 0.0))
    correct_aspect = bool(body.get("correctAspect", True))
    scale_to_bounds = bool(body.get("scaleToBounds", True))

    import math
    with composite_undo(f"postproc_smart_uv_project:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            with with_3dview_context():
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.uv.smart_project(
                    angle_limit=math.radians(angle_limit),
                    island_margin=island_margin,
                    area_weight=area_weight,
                    correct_aspect=correct_aspect,
                    scale_to_bounds=scale_to_bounds,
                )

    me = obj.data
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "uvLayerCount": len(me.uv_layers),
            "activeUVLayer": (me.uv_layers.active.name if me.uv_layers.active else None),
        },
        "refs": {"objectName": obj.name},
    }


# ---------------------------------------------------------------------------
# decimate
# ---------------------------------------------------------------------------

@handler("POST", "/postproc/decimate")
def postproc_decimate(body: dict[str, Any]) -> dict[str, Any]:
    """Add (and optionally apply) a DECIMATE modifier.

    Body:
        objectName: str
        decimateType?: 'COLLAPSE'|'UNSUBDIV'|'DISSOLVE'   — default COLLAPSE
        ratio?: float                  — for COLLAPSE, default 0.5
        iterations?: int               — for UNSUBDIV, default 2
        angleLimit?: float (deg)       — for DISSOLVE, default 5.0
        apply?: bool                   — default False (keep as live modifier)
        modifierName?: str             — default 'Decimate'
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    dtype = str(body.get("decimateType", "COLLAPSE")).upper()
    if dtype not in {"COLLAPSE", "UNSUBDIV", "DISSOLVE"}:
        raise InvalidInputError(f"decimateType must be COLLAPSE|UNSUBDIV|DISSOLVE, got {dtype!r}")
    modifier_name = body.get("modifierName", "Decimate")
    apply_flag = bool(body.get("apply", False))

    with composite_undo(f"postproc_decimate:{obj.name}"):
        mod = obj.modifiers.new(name=modifier_name, type="DECIMATE")
        mod.decimate_type = dtype
        if dtype == "COLLAPSE":
            mod.ratio = float(body.get("ratio", 0.5))
        elif dtype == "UNSUBDIV":
            mod.iterations = int(body.get("iterations", 2))
        elif dtype == "DISSOLVE":
            import math
            mod.angle_limit = math.radians(float(body.get("angleLimit", 5.0)))
        if apply_flag:
            set_active_and_selected(obj)
            with with_3dview_context():
                bpy.ops.object.modifier_apply(modifier=modifier_name)

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "decimateType": dtype,
            "applied": apply_flag,
            "currentFaceCount": len(obj.data.polygons),
        },
        "refs": {"objectName": obj.name},
    }


# ---------------------------------------------------------------------------
# lod_generate
# ---------------------------------------------------------------------------

@handler("POST", "/postproc/lod_generate", timeout=300.0)
def postproc_lod_generate(body: dict[str, Any]) -> dict[str, Any]:
    """Generate N decimated LOD copies. Each copy is independent and named
    `<base>_LOD<i>`. The base object is preserved unchanged as LOD0.

    Body:
        objectName: str
        levels?: int        — default 3 (creates LOD1..LOD3)
        ratios?: list[float]— per-level collapse ratios. Default [0.5, 0.25, 0.10]
                              length must equal `levels` if given.
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    levels = int(body.get("levels", 3))
    if levels < 1 or levels > 8:
        raise InvalidInputError("levels must be in [1,8]")
    ratios = body.get("ratios")
    if ratios is None:
        defaults = [0.5, 0.25, 0.10, 0.05, 0.025, 0.0125, 0.006, 0.003]
        ratios = defaults[:levels]
    else:
        if not isinstance(ratios, list) or len(ratios) != levels:
            raise InvalidInputError(f"ratios must be a list of length {levels}")
        ratios = [float(r) for r in ratios]

    created: List[dict[str, Any]] = []
    with composite_undo(f"postproc_lod_generate:{obj.name}/{levels}"):
        for idx, ratio in enumerate(ratios, start=1):
            if ratio <= 0 or ratio >= 1:
                raise InvalidInputError(f"ratio at index {idx-1} must be in (0,1)")
            # duplicate object data so each LOD is independent
            new_mesh = obj.data.copy()
            new_obj = obj.copy()
            new_obj.data = new_mesh
            new_obj.name = f"{obj.name}_LOD{idx}"
            # link to same collection as source
            for c in obj.users_collection:
                c.objects.link(new_obj)

            mod = new_obj.modifiers.new(name=f"_lod_decimate_{idx}", type="DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = ratio

            set_active_and_selected(new_obj)
            with with_3dview_context():
                bpy.ops.object.modifier_apply(modifier=mod.name)

            created.append({
                "name": new_obj.name,
                "ratio": ratio,
                "faceCount": len(new_obj.data.polygons),
            })

    return {
        "ok": True,
        "data": {"baseObject": obj.name, "levels": levels, "lods": created},
        "refs": {"objectNames": [c["name"] for c in created]},
    }


# ---------------------------------------------------------------------------
# auto_smooth_normals
# ---------------------------------------------------------------------------

@handler("POST", "/postproc/auto_smooth_normals")
def postproc_auto_smooth_normals(body: dict[str, Any]) -> dict[str, Any]:
    """Smooth shading + auto-smooth at angle. Blender 4.1+ uses the modifier
    geometry-node based auto-smooth (the legacy `mesh.use_auto_smooth` bool was
    removed). We add a `Smooth by Angle` modifier if not present.

    Body:
        objectName: str
        angle?: float (deg)        — default 30
    """
    import bpy  # type: ignore
    import math

    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    angle = float(body.get("angle", 30.0))

    with composite_undo(f"postproc_auto_smooth_normals:{obj.name}"):
        set_active_and_selected(obj)
        # mark all polys smooth
        for poly in obj.data.polygons:
            poly.use_smooth = True

        # Blender 4.1+: use the "Smooth by Angle" geo-node modifier through
        # the operator that adds it under-the-hood.
        added_via_op = False
        with with_3dview_context():
            try:
                bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
                added_via_op = True
            except Exception:  # noqa: BLE001
                # fallback: legacy bool (3.x / 4.0)
                if hasattr(obj.data, "use_auto_smooth"):
                    obj.data.use_auto_smooth = True
                    obj.data.auto_smooth_angle = math.radians(angle)

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "angleDeg": angle,
            "method": ("modifier" if added_via_op else "legacy_mesh_data"),
        },
        "refs": {"objectName": obj.name},
    }
