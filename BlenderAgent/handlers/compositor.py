"""Compositor handlers (B5 §15) — minimal, used for output-passes only."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    NodeNotFoundError,
    composite_undo,
    get_scene,
)
from ..server import handler


def _ensure_compositor(scene: Any) -> Any:
    """Enable compositor nodes on a scene and return the node tree.

    In Blender 4.2 LTS `scene.use_nodes = True` auto-creates `scene.node_tree`.
    In Blender 5.x the compositor moved to `scene.compositing_node_group`
    (a NodeGroup datablock); `scene.node_tree` is no longer attached at all.
    Probe both and return whichever exists.
    """
    import bpy  # type: ignore
    scene.use_nodes = True
    # Blender 4.x path
    tree = getattr(scene, "node_tree", None)
    if tree is not None:
        return tree
    # Blender 5.x path: scene.compositing_node_group is a NodeGroup datablock.
    existing = getattr(scene, "compositing_node_group", None)
    if existing is not None:
        return existing
    ng = bpy.data.node_groups.new(name=f"{scene.name}_Compositor", type="CompositorNodeTree")
    scene.compositing_node_group = ng
    return ng


@handler("POST", "/compositor/enable")
def compositor_enable(body: dict[str, Any]) -> dict[str, Any]:
    scene = get_scene(body.get("sceneName"))
    with composite_undo(f"compositor_enable:{scene.name}"):
        _ensure_compositor(scene)
    return {
        "ok": True,
        "data": {"sceneName": scene.name, "useNodes": scene.use_nodes},
        "refs": {"sceneName": scene.name},
    }


@handler("POST", "/compositor/add_node")
def compositor_add_node(body: dict[str, Any]) -> dict[str, Any]:
    scene = get_scene(body.get("sceneName"))
    tree = _ensure_compositor(scene)
    node_type = body.get("type")
    if not node_type:
        raise InvalidInputError("type is required")
    name = body.get("name")
    location = body.get("location")
    with composite_undo(f"compositor_add_node:{scene.name}/{node_type}"):
        try:
            node = tree.nodes.new(node_type)
        except (RuntimeError, TypeError) as exc:
            raise InvalidInputError(f"Unknown compositor node {node_type!r}: {exc}") from exc
        if name:
            node.name = name
        if location:
            node.location = tuple(location)
    return {
        "ok": True,
        "data": {"sceneName": scene.name, "nodeName": node.name, "type": node.bl_idname},
        "refs": {"sceneName": scene.name, "nodeName": node.name},
    }


@handler("POST", "/compositor/connect")
def compositor_connect(body: dict[str, Any]) -> dict[str, Any]:
    scene = get_scene(body.get("sceneName"))
    tree = _ensure_compositor(scene)
    f_n = tree.nodes.get(body.get("fromNodeName"))
    t_n = tree.nodes.get(body.get("toNodeName"))
    if f_n is None or t_n is None:
        raise NodeNotFoundError("from or to compositor node not found")
    f_s = f_n.outputs.get(body.get("fromSocketName"))
    t_s = t_n.inputs.get(body.get("toSocketName"))
    if f_s is None or t_s is None:
        raise InvalidInputError("from or to socket not found")
    with composite_undo(f"compositor_connect:{f_n.name}->{t_n.name}"):
        tree.links.new(f_s, t_s)
    return {"ok": True, "data": {"sceneName": scene.name, "from": f_n.name, "to": t_n.name},
            "refs": {"sceneName": scene.name}}


@handler("POST", "/compositor/set_node_property")
def compositor_set_node_property(body: dict[str, Any]) -> dict[str, Any]:
    """Set a top-level property on a compositor node (e.g. base_path, blend_type).

    Body: {sceneName?: str, nodeName: str, propertyName: str, propertyValue: any}

    Use for primitive node attributes that are RNA properties of the node itself.
    Examples: `base_path` on CompositorNodeOutputFile; `blend_type` on
    CompositorNodeMixRGB; `mute` on any node; `label` on any node.
    """
    scene = get_scene(body.get("sceneName"))
    tree = _ensure_compositor(scene)
    node_name = body.get("nodeName")
    prop_name = body.get("propertyName")
    if not node_name or not prop_name:
        raise InvalidInputError("nodeName and propertyName are required")
    if "propertyValue" not in body:
        raise InvalidInputError("propertyValue is required")
    node = tree.nodes.get(node_name)
    if node is None:
        raise NodeNotFoundError(f"compositor node {node_name!r} not found")
    if not hasattr(node, prop_name):
        raise InvalidInputError(
            f"node {node_name!r} ({node.bl_idname}) has no property {prop_name!r}"
        )
    value = body["propertyValue"]
    with composite_undo(f"compositor_set_node_property:{node.name}.{prop_name}"):
        try:
            setattr(node, prop_name, value)
        except (TypeError, ValueError) as exc:
            raise InvalidInputError(
                f"cannot set {prop_name!r} on {node.name!r}: {exc}"
            ) from exc
    return {
        "ok": True,
        "data": {
            "sceneName": scene.name,
            "nodeName": node.name,
            "propertyName": prop_name,
            "propertyValue": getattr(node, prop_name),
        },
        "refs": {"sceneName": scene.name, "nodeName": node.name},
    }


@handler("POST", "/compositor/set_node_input")
def compositor_set_node_input(body: dict[str, Any]) -> dict[str, Any]:
    """Set the default_value of a compositor node's input socket.

    Body: {sceneName?: str, nodeName: str, inputName: str, value: any}

    Example: set `Hue`/`Saturation`/`Value` on CompositorNodeHueSat without linking.
    """
    scene = get_scene(body.get("sceneName"))
    tree = _ensure_compositor(scene)
    node_name = body.get("nodeName")
    input_name = body.get("inputName")
    if not node_name or not input_name:
        raise InvalidInputError("nodeName and inputName are required")
    if "value" not in body:
        raise InvalidInputError("value is required")
    node = tree.nodes.get(node_name)
    if node is None:
        raise NodeNotFoundError(f"compositor node {node_name!r} not found")
    sock = node.inputs.get(input_name)
    if sock is None:
        raise InvalidInputError(
            f"node {node_name!r} has no input socket {input_name!r}"
        )
    value = body["value"]
    with composite_undo(f"compositor_set_node_input:{node.name}.{input_name}"):
        try:
            sock.default_value = value
        except (TypeError, ValueError) as exc:
            raise InvalidInputError(
                f"cannot set input {input_name!r} on {node.name!r}: {exc}"
            ) from exc
    return {
        "ok": True,
        "data": {
            "sceneName": scene.name,
            "nodeName": node.name,
            "inputName": input_name,
        },
        "refs": {"sceneName": scene.name, "nodeName": node.name},
    }
