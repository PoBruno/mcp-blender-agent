"""Mesh edit (bmesh) handlers (B3).

These edit topology via bmesh inside `with_mode(obj, 'EDIT')`.
"""

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
        raise InvalidInputError(f"Object {obj.name!r} type is {obj.type}, expected MESH")


@handler("POST", "/mesh/extrude_region_move")
def mesh_extrude_region_move(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    offset = body.get("offset", [0.0, 0.0, 1.0])
    with composite_undo(f"mesh_extrude_region_move:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            with with_3dview_context():
                bpy.ops.mesh.extrude_region_move(
                    TRANSFORM_OT_translate={"value": tuple(offset)}
                )
    return {"ok": True, "data": {"objectName": obj.name, "offset": list(offset)},
            "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/bevel")
def mesh_bevel(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    offset = float(body.get("offset", 0.1))
    segments = int(body.get("segments", 2))
    profile = float(body.get("profile", 0.5))
    with composite_undo(f"mesh_bevel:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            with with_3dview_context():
                bpy.ops.mesh.bevel(
                    offset=offset, segments=segments, profile=profile
                )
    return {"ok": True, "data": {"objectName": obj.name, "offset": offset, "segments": segments},
            "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/loop_cut")
def mesh_loop_cut(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    number_cuts = int(body.get("numberCuts", 1))
    with composite_undo(f"mesh_loop_cut:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            with with_3dview_context():
                bpy.ops.mesh.loopcut_slide(
                    MESH_OT_loopcut={"number_cuts": number_cuts}
                )
    return {"ok": True, "data": {"objectName": obj.name, "numberCuts": number_cuts},
            "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/subdivide")
def mesh_subdivide(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    number_cuts = int(body.get("numberCuts", 1))
    smoothness = float(body.get("smoothness", 0.0))
    with composite_undo(f"mesh_subdivide:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.mesh.subdivide(number_cuts=number_cuts, smoothness=smoothness)
    return {"ok": True, "data": {"objectName": obj.name, "numberCuts": number_cuts},
            "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/merge_by_distance")
def mesh_merge_by_distance(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    threshold = float(body.get("threshold", 0.0001))
    with composite_undo(f"mesh_merge_by_distance:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.mesh.remove_doubles(threshold=threshold)
    return {"ok": True, "data": {"objectName": obj.name, "threshold": threshold},
            "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/shade_smooth")
def mesh_shade_smooth(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    with composite_undo(f"mesh_shade_smooth:{obj.name}"):
        set_active_and_selected(obj)
        with with_3dview_context():
            bpy.ops.object.shade_smooth()
    return {"ok": True, "data": {"objectName": obj.name}, "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/shade_flat")
def mesh_shade_flat(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    with composite_undo(f"mesh_shade_flat:{obj.name}"):
        set_active_and_selected(obj)
        with with_3dview_context():
            bpy.ops.object.shade_flat()
    return {"ok": True, "data": {"objectName": obj.name}, "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/recalc_normals")
def mesh_recalc_normals(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    inside = bool(body.get("inside", False))
    with composite_undo(f"mesh_recalc_normals:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.mesh.normals_make_consistent(inside=inside)
    return {"ok": True, "data": {"objectName": obj.name, "inside": inside},
            "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/triangulate")
def mesh_triangulate(body: dict[str, Any]) -> dict[str, Any]:
    """Apply Triangulate modifier-style operation in edit mode."""
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    with composite_undo(f"mesh_triangulate:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.mesh.quads_convert_to_tris()
    return {"ok": True, "data": {"objectName": obj.name}, "refs": {"objectName": obj.name}}


@handler("POST", "/mesh/join")
def mesh_join(body: dict[str, Any]) -> dict[str, Any]:
    """Join multiple meshes into one (active is target)."""
    import bpy  # type: ignore
    target = get_object(body.get("targetObjectName"))
    source_names = body.get("sourceObjectNames", [])
    if not isinstance(source_names, list) or not source_names:
        raise InvalidInputError("sourceObjectNames must be a non-empty list")
    with composite_undo(f"mesh_join:{target.name}"):
        for o in bpy.data.objects:
            o.select_set(False)
        for n in source_names:
            get_object(n).select_set(True)
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        with with_3dview_context():
            bpy.ops.object.join()
    return {
        "ok": True,
        "data": {"objectName": target.name, "joined": source_names},
        "refs": {"objectName": target.name},
    }


@handler("POST", "/mesh/separate_by_loose_parts")
def mesh_separate_by_loose_parts(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    _ensure_mesh(obj)
    before = set(o.name for o in bpy.data.objects)
    with composite_undo(f"mesh_separate_by_loose_parts:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "EDIT"):
            bpy.ops.mesh.select_all(action="SELECT")
            with with_3dview_context():
                bpy.ops.mesh.separate(type="LOOSE")
    after = set(o.name for o in bpy.data.objects)
    new_objects = sorted(after - before)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "newObjects": new_objects},
        "refs": {"objectNames": [obj.name, *new_objects]},
    }
