"""World / environment handlers (B9)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_scene,
)
from ..server import handler


@handler("POST", "/world/create")
def world_create(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    name = body.get("name", "World")
    with composite_undo(f"world_create:{name}"):
        if name in bpy.data.worlds:
            w = bpy.data.worlds[name]
            return {"ok": True, "data": {"worldName": w.name, "created": False},
                    "refs": {"worldName": w.name}}
        w = bpy.data.worlds.new(name=name)
        w.use_nodes = True
    return {"ok": True, "data": {"worldName": w.name, "created": True},
            "refs": {"worldName": w.name}}


@handler("POST", "/world/assign_to_scene")
def world_assign_to_scene(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    scene = get_scene(body.get("sceneName"))
    name = body.get("worldName")
    if not name:
        raise InvalidInputError("worldName is required")
    w = bpy.data.worlds.get(name)
    if w is None:
        raise InvalidInputError(f"world {name!r} not found")
    with composite_undo(f"world_assign_to_scene:{scene.name}/{name}"):
        scene.world = w
    return {"ok": True, "data": {"sceneName": scene.name, "worldName": w.name},
            "refs": {"sceneName": scene.name, "worldName": w.name}}
