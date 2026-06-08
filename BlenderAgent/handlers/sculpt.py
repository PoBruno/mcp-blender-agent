"""Sculpt handlers (B3) — stub. Mostly modal; verify each op in 4.2.

Per BPY-FEASIBILITY.md §B3, dyntopo + remesh are scriptable but most
brush strokes are modal-only. We expose the deterministic operations only.
"""

from __future__ import annotations

from typing import Any

from ..helpers import (
    composite_undo,
    get_object,
    set_active_and_selected,
    with_3dview_context,
    with_mode,
)
from ..server import handler


@handler("POST", "/sculpt/enable_dyntopo")
def sculpt_enable_dyntopo(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    detail_size = float(body.get("detailSize", 12.0))
    with composite_undo(f"sculpt_enable_dyntopo:{obj.name}"):
        set_active_and_selected(obj)
        with with_mode(obj, "SCULPT"):
            scene = bpy.context.scene
            scene.tool_settings.sculpt.detail_size = detail_size
            with with_3dview_context():
                if not scene.tool_settings.sculpt.use_dyntopo if hasattr(scene.tool_settings.sculpt, "use_dyntopo") else True:
                    bpy.ops.sculpt.dynamic_topology_toggle()
    return {"ok": True, "data": {"objectName": obj.name, "detailSize": detail_size},
            "refs": {"objectName": obj.name}}


@handler("POST", "/sculpt/voxel_remesh")
def sculpt_voxel_remesh(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    voxel_size = float(body.get("voxelSize", 0.05))
    with composite_undo(f"sculpt_voxel_remesh:{obj.name}"):
        set_active_and_selected(obj)
        obj.data.remesh_voxel_size = voxel_size
        with with_mode(obj, "SCULPT"):
            with with_3dview_context():
                bpy.ops.object.voxel_remesh()
    return {"ok": True, "data": {"objectName": obj.name, "voxelSize": voxel_size},
            "refs": {"objectName": obj.name}}
