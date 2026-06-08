"""Geometry Node graph handlers (B8) — applies/edits GeometryNodeTree.

Per ADR-013, geometry-node graph editing is owned here. Modifier addition
of a Geometry Nodes modifier is in handlers/modifier.py.
"""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    NodeNotFoundError,
    composite_undo,
    get_object,
)
from ..server import handler


def _get_geo_tree(body: dict[str, Any]) -> Any:
    import bpy  # type: ignore
    ng_name = body.get("nodeGroupName")
    if not ng_name:
        raise InvalidInputError("nodeGroupName required")
    ng = bpy.data.node_groups.get(ng_name)
    if ng is None:
        raise InvalidInputError(f"node group {ng_name!r} not found")
    if not ng.bl_idname.endswith("GeometryNodeTree"):
        raise InvalidInputError(f"{ng_name!r} is not a GeometryNodeTree (got {ng.bl_idname!r})")
    return ng


@handler("POST", "/geo_node/group_create")
def geo_node_group_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a GeometryNodeTree with a Group Input + Group Output."""
    import bpy  # type: ignore
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    with composite_undo(f"geo_node_group_create:{name}"):
        if name in bpy.data.node_groups:
            ng = bpy.data.node_groups[name]
            return {"ok": True,
                    "data": {"nodeGroupName": ng.name, "created": False},
                    "refs": {"nodeGroupName": ng.name}}
        ng = bpy.data.node_groups.new(name=name, type="GeometryNodeTree")
        # Add a Group Input/Output and the Geometry socket
        ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        n_in = ng.nodes.new("NodeGroupInput")
        n_out = ng.nodes.new("NodeGroupOutput")
        n_in.location = (-200, 0)
        n_out.location = (200, 0)
        ng.links.new(n_in.outputs[0], n_out.inputs[0])
    return {"ok": True,
            "data": {"nodeGroupName": ng.name, "created": True},
            "refs": {"nodeGroupName": ng.name}}


@handler("POST", "/geo_node/add_node")
def geo_node_add_node(body: dict[str, Any]) -> dict[str, Any]:
    tree = _get_geo_tree(body)
    node_type = body.get("type")
    if not node_type:
        raise InvalidInputError("type is required")
    name = body.get("name")
    location = body.get("location")
    with composite_undo(f"geo_node_add_node:{tree.name}/{node_type}"):
        try:
            node = tree.nodes.new(node_type)
        except RuntimeError as exc:
            raise InvalidInputError(f"Unknown node type {node_type!r}: {exc}") from exc
        if name:
            node.name = name
        if location:
            node.location = tuple(location)
    return {
        "ok": True,
        "data": {"nodeGroupName": tree.name, "nodeName": node.name, "type": node.bl_idname},
        "refs": {"nodeGroupName": tree.name, "nodeName": node.name},
    }


@handler("POST", "/geo_node/connect")
def geo_node_connect(body: dict[str, Any]) -> dict[str, Any]:
    tree = _get_geo_tree(body)
    f_n = tree.nodes.get(body.get("fromNodeName"))
    t_n = tree.nodes.get(body.get("toNodeName"))
    if f_n is None or t_n is None:
        raise NodeNotFoundError("from or to node not found")
    f_s = f_n.outputs.get(body.get("fromSocketName"))
    t_s = t_n.inputs.get(body.get("toSocketName"))
    if f_s is None or t_s is None:
        raise InvalidInputError("from or to socket not found")
    with composite_undo(f"geo_node_connect:{f_n.name}->{t_n.name}"):
        tree.links.new(f_s, t_s)
    return {
        "ok": True,
        "data": {"nodeGroupName": tree.name, "from": f_n.name, "to": t_n.name},
        "refs": {"nodeGroupName": tree.name},
    }


@handler("POST", "/geo_node/apply_to_object")
def geo_node_apply_to_object(body: dict[str, Any]) -> dict[str, Any]:
    """Add a Geometry Nodes modifier to an object and set its node group."""
    obj = get_object(body.get("objectName"))
    ng_name = body.get("nodeGroupName")
    if not ng_name:
        raise InvalidInputError("nodeGroupName required")
    import bpy  # type: ignore
    ng = bpy.data.node_groups.get(ng_name)
    if ng is None:
        raise InvalidInputError(f"node group {ng_name!r} not found")
    mod_name = body.get("modifierName", "GeometryNodes")
    with composite_undo(f"geo_node_apply_to_object:{obj.name}/{ng_name}"):
        mod = obj.modifiers.get(mod_name)
        if mod is None:
            mod = obj.modifiers.new(name=mod_name, type="NODES")
        mod.node_group = ng
    return {
        "ok": True,
        "data": {"objectName": obj.name, "modifierName": mod.name, "nodeGroupName": ng.name},
        "refs": {"objectName": obj.name, "modifierName": mod.name, "nodeGroupName": ng.name},
    }
