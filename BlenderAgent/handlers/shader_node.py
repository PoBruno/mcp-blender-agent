"""Shader node graph handlers (B5)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    NodeNotFoundError,
    composite_undo,
    get_material,
)
from ..server import handler


def _resolve_tree(body: dict[str, Any]) -> Any:
    """Resolve a node tree by material name or world name."""
    import bpy  # type: ignore
    if "materialName" in body:
        return get_material(body["materialName"]).node_tree
    if "worldName" in body:
        world = bpy.data.worlds.get(body["worldName"])
        if world is None:
            raise InvalidInputError(f"world {body['worldName']!r} not found")
        return world.node_tree
    if "nodeGroupName" in body:
        ng = bpy.data.node_groups.get(body["nodeGroupName"])
        if ng is None:
            raise InvalidInputError(f"node group {body['nodeGroupName']!r} not found")
        return ng
    raise InvalidInputError("materialName, worldName or nodeGroupName required")


@handler("POST", "/shader_node/add")
def shader_node_add(body: dict[str, Any]) -> dict[str, Any]:
    """Add a shader node to a material's node tree.

    Body: {materialName: str, type: str (bl_idname like 'ShaderNodeBsdfPrincipled'),
           name?: str, location?: [x,y]}
    """
    tree = _resolve_tree(body)
    node_type = body.get("type")
    if not node_type:
        raise InvalidInputError("type is required")
    name = body.get("name")
    location = body.get("location")
    with composite_undo(f"shader_node_add:{node_type}"):
        try:
            node = tree.nodes.new(node_type)
        except (RuntimeError, TypeError) as exc:
            raise InvalidInputError(f"Unknown node type {node_type!r}: {exc}") from exc
        if name:
            node.name = name
        if location:
            node.location = tuple(location)
    return {
        "ok": True,
        "data": {"nodeName": node.name, "type": node.bl_idname, "location": list(node.location)},
        "refs": {"nodeName": node.name},
    }


@handler("POST", "/shader_node/set_input_value")
def shader_node_set_input_value(body: dict[str, Any]) -> dict[str, Any]:
    """Set a default_value on a node socket."""
    tree = _resolve_tree(body)
    node_name = body.get("nodeName")
    socket = body.get("socketName") or body.get("socket")
    value = body.get("value")
    if not node_name or socket is None or value is None:
        raise InvalidInputError("nodeName, socketName and value are required")
    # Some MCP clients stringify untyped (z.unknown) values — a color arrives as
    # "[0.85, 0.02, 0.02, 1.0]" and a float as "0.16". Recover JSON scalars and
    # sequences so numeric/color/vector sockets accept them.
    if isinstance(value, str):
        import json
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            pass
    node = tree.nodes.get(node_name)
    if node is None:
        raise NodeNotFoundError(f"node {node_name!r} not found")
    inp = node.inputs.get(socket) if isinstance(socket, str) else node.inputs[int(socket)]
    if inp is None:
        raise InvalidInputError(f"socket {socket!r} not found on {node.name!r}")
    with composite_undo(f"shader_node_set_input_value:{node.name}/{socket}"):
        if isinstance(value, (list, tuple)):
            inp.default_value = tuple(value)
        else:
            inp.default_value = value
    return {
        "ok": True,
        "data": {"nodeName": node.name, "socketName": str(socket), "value": value},
        "refs": {"nodeName": node.name},
    }


@handler("POST", "/shader_node/connect")
def shader_node_connect(body: dict[str, Any]) -> dict[str, Any]:
    """Connect two sockets in a node tree."""
    tree = _resolve_tree(body)
    from_node = body.get("fromNodeName")
    from_socket = body.get("fromSocketName")
    to_node = body.get("toNodeName")
    to_socket = body.get("toSocketName")
    if not all([from_node, from_socket, to_node, to_socket]):
        raise InvalidInputError("fromNodeName, fromSocketName, toNodeName, toSocketName required")
    n_from = tree.nodes.get(from_node)
    n_to = tree.nodes.get(to_node)
    if n_from is None or n_to is None:
        raise NodeNotFoundError(f"nodes not found: {from_node!r} or {to_node!r}")
    out = n_from.outputs.get(from_socket)
    inp = n_to.inputs.get(to_socket)
    if out is None or inp is None:
        raise InvalidInputError(f"socket(s) not found: {from_socket!r} -> {to_socket!r}")
    with composite_undo(f"shader_node_connect:{from_node}->{to_node}"):
        link = tree.links.new(out, inp)
    return {
        "ok": True,
        "data": {
            "fromNode": n_from.name, "fromSocket": from_socket,
            "toNode": n_to.name, "toSocket": to_socket,
        },
        "refs": {"linkFrom": n_from.name, "linkTo": n_to.name},
    }


@handler("POST", "/shader_node/connect_pins")
def shader_node_connect_pins(body: dict[str, Any]) -> dict[str, Any]:
    """Alias for shader_node_connect — preferred name in docs."""
    return shader_node_connect(body)


@handler("POST", "/shader_node/remove")
def shader_node_remove(body: dict[str, Any]) -> dict[str, Any]:
    tree = _resolve_tree(body)
    name = body.get("nodeName")
    if not name:
        raise InvalidInputError("nodeName is required")
    node = tree.nodes.get(name)
    if node is None:
        raise NodeNotFoundError(f"node {name!r} not found")
    with composite_undo(f"shader_node_remove:{name}"):
        tree.nodes.remove(node)
    return {"ok": True, "data": {"removed": name}}


@handler("POST", "/shader_node/list")
def shader_node_list(body: dict[str, Any]) -> dict[str, Any]:
    tree = _resolve_tree(body)
    return {
        "ok": True,
        "data": {
            "nodes": [{"name": n.name, "type": n.bl_idname, "location": list(n.location)}
                      for n in tree.nodes],
            "links": [{
                "from": l.from_node.name, "fromSocket": l.from_socket.name,
                "to": l.to_node.name, "toSocket": l.to_socket.name,
            } for l in tree.links],
        },
    }
