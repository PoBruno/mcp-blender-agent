"""UV handlers (B1 §11, B3 §17–19, B4)."""

from __future__ import annotations

from typing import Any

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
        raise InvalidInputError(f"Object {obj.name!r} is type {obj.type}, expected MESH")


@handler("POST", "/uv/layer_create")
def uv_layer_create(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    name = body.get("name", "UVMap")
    with composite_undo(f"uv_layer_create:{obj.name}/{name}"):
        if name not in obj.data.uv_layers:
            obj.data.uv_layers.new(name=name)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "uvLayerName": name},
        "refs": {"objectName": obj.name, "uvLayerName": name},
    }


@handler("POST", "/uv/smart_project")
def uv_smart_project(body: dict[str, Any]) -> dict[str, Any]:
    """Run Smart UV Project on the mesh.

    Body: {objectName: str, angleLimit?: float (deg, default 66),
           islandMargin?: float (default 0.02), areaWeight?: float,
           correctAspect?: bool, scaleToBounds?: bool}
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    angle_limit = float(body.get("angleLimit", 66.0))
    island_margin = float(body.get("islandMargin", 0.02))
    area_weight = float(body.get("areaWeight", 0.0))
    correct_aspect = bool(body.get("correctAspect", True))
    scale_to_bounds = bool(body.get("scaleToBounds", False))

    with composite_undo(f"uv_smart_project:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.uv.smart_project(
                    angle_limit=angle_limit * (3.141592653589793 / 180.0),
                    island_margin=island_margin,
                    area_weight=area_weight,
                    correct_aspect=correct_aspect,
                    scale_to_bounds=scale_to_bounds,
                )

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "uvLayerName": obj.data.uv_layers.active.name if obj.data.uv_layers.active else "UVMap",
        },
        "refs": {
            "objectName": obj.name,
            "uvLayerName": obj.data.uv_layers.active.name if obj.data.uv_layers.active else "UVMap",
        },
    }


@handler("POST", "/uv/unwrap_smart_project")
def uv_unwrap_smart_project(body: dict[str, Any]) -> dict[str, Any]:
    """Alias for uv_smart_project — kit-friendly default."""
    return uv_smart_project(body)


@handler("POST", "/uv/pack_islands")
def uv_pack_islands(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    margin = float(body.get("margin", 0.005))

    with composite_undo(f"uv_pack_islands:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.uv.pack_islands(margin=margin)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "margin": margin},
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/uv/average_islands_scale")
def uv_average_islands_scale(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    with composite_undo(f"uv_average_islands_scale:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.uv.average_islands_scale()
    return {"ok": True, "data": {"objectName": obj.name}, "refs": {"objectName": obj.name}}


@handler("POST", "/uv/mark_seams")
def uv_mark_seams(body: dict[str, Any]) -> dict[str, Any]:
    """Mark seams from current edge selection, or auto-mark from sharp edges."""
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    from_sharp = bool(body.get("fromSharp", False))

    with composite_undo(f"uv_mark_seams:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            if from_sharp:
                bpy.ops.mesh.select_all(action="DESELECT")
                # Select sharp edges
                bpy.ops.mesh.select_mode(type="EDGE")
                for edge in obj.data.edges:
                    edge.select = edge.use_edge_sharp
            with with_3dview_context():
                bpy.ops.mesh.mark_seam(clear=False)
    return {"ok": True, "data": {"objectName": obj.name}, "refs": {"objectName": obj.name}}


@handler("POST", "/uv/minimize_stretch")
def uv_minimize_stretch(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    iterations = int(body.get("iterations", 32))
    with composite_undo(f"uv_minimize_stretch:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.uv.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.uv.minimize_stretch(iterations=iterations)
    return {"ok": True, "data": {"objectName": obj.name}, "refs": {"objectName": obj.name}}


@handler("POST", "/uv/unwrap")
def uv_unwrap(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    method = body.get("method", "ANGLE_BASED").upper()
    margin = float(body.get("margin", 0.001))
    with composite_undo(f"uv_unwrap:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.uv.unwrap(method=method, margin=margin)
    return {"ok": True, "data": {"objectName": obj.name, "method": method}, "refs": {"objectName": obj.name}}


@handler("POST", "/uv/validate_for_baking")
def uv_validate_for_baking(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    if not obj.data.uv_layers:
        return {
            "ok": False,
            "errorCode": "NO_UV_LAYER",
            "message": f"{obj.name!r} has no UV layer",
        }

    uv = obj.data.uv_layers.active
    out_of_bounds = 0
    for loop in obj.data.loops:
        uv_co = uv.data[loop.index].uv
        if uv_co.x < 0 or uv_co.x > 1 or uv_co.y < 0 or uv_co.y > 1:
            out_of_bounds += 1

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "uvLayerName": uv.name,
            "loopCount": len(obj.data.loops),
            "outOfBoundsLoops": out_of_bounds,
        },
        "refs": {"objectName": obj.name, "uvLayerName": uv.name},
    }
