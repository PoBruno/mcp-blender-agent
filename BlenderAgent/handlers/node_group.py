"""Shader node group handlers (B5)."""

from __future__ import annotations

from typing import Any

from ..helpers import InvalidInputError, composite_undo
from ..server import handler


@handler("POST", "/node_group/create")
def node_group_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new ShaderNodeTree (the underlying data of a node group)."""
    import bpy  # type: ignore
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    tree_type = body.get("treeType", "ShaderNodeTree")
    with composite_undo(f"node_group_create:{name}"):
        if name in bpy.data.node_groups:
            ng = bpy.data.node_groups[name]
            return {"ok": True,
                    "data": {"nodeGroupName": ng.name, "created": False, "treeType": ng.bl_idname},
                    "refs": {"nodeGroupName": ng.name}}
        ng = bpy.data.node_groups.new(name=name, type=tree_type)
    return {"ok": True,
            "data": {"nodeGroupName": ng.name, "created": True, "treeType": ng.bl_idname},
            "refs": {"nodeGroupName": ng.name}}


@handler("POST", "/node_group/instance_in_material")
def node_group_instance_in_material(body: dict[str, Any]) -> dict[str, Any]:
    """Add a ShaderNodeGroup pointing at an existing node group inside a material."""
    import bpy  # type: ignore
    material_name = body.get("materialName")
    ng_name = body.get("nodeGroupName")
    if not material_name or not ng_name:
        raise InvalidInputError("materialName and nodeGroupName required")
    mat = bpy.data.materials.get(material_name)
    if mat is None or mat.node_tree is None:
        raise InvalidInputError(f"material {material_name!r} not found or has no node tree")
    ng = bpy.data.node_groups.get(ng_name)
    if ng is None:
        raise InvalidInputError(f"node group {ng_name!r} not found")
    location = body.get("location", (0, 0))
    with composite_undo(f"node_group_instance_in_material:{material_name}/{ng_name}"):
        gnode = mat.node_tree.nodes.new("ShaderNodeGroup")
        gnode.node_tree = ng
        gnode.location = tuple(location)
    return {
        "ok": True,
        "data": {"materialName": mat.name, "nodeName": gnode.name, "nodeGroupName": ng.name},
        "refs": {"materialName": mat.name, "nodeName": gnode.name, "nodeGroupName": ng.name},
    }
