"""Scene handlers (B1, B9.D1–D2)."""

from __future__ import annotations

from typing import Any

from ..helpers import SceneNotFoundError, composite_undo, get_scene
from ..server import handler


@handler("POST", "/scene/create")
def scene_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new scene.

    Body: {name: str, unitSystem?: 'METRIC'|'IMPERIAL'|'NONE', scaleLength?: float,
           frameStart?: int, frameEnd?: int}
    """
    import bpy  # type: ignore

    name = body.get("name", "Scene")
    unit_system = body.get("unitSystem", "METRIC")
    scale_length = float(body.get("scaleLength", 1.0))
    frame_start = int(body.get("frameStart", 1))
    frame_end = int(body.get("frameEnd", 250))

    with composite_undo(f"scene_create:{name}"):
        new_scene = bpy.data.scenes.new(name=name)
        new_scene.unit_settings.system = unit_system
        new_scene.unit_settings.scale_length = scale_length
        new_scene.frame_start = frame_start
        new_scene.frame_end = frame_end

    return {
        "ok": True,
        "data": {
            "sceneName": new_scene.name,
            "unitSystem": new_scene.unit_settings.system,
            "scaleLength": new_scene.unit_settings.scale_length,
        },
        "refs": {"sceneName": new_scene.name},
        "nextSteps": [
            "Call /scene/set_active to make this the active scene.",
            "Call /collection/create to add collections under it.",
        ],
    }


@handler("POST", "/scene/set_active")
def scene_set_active(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    name = body.get("sceneName") or body.get("name")
    if not name:
        raise SceneNotFoundError("sceneName is required")
    scene = get_scene(name)
    bpy.context.window.scene = scene
    return {
        "ok": True,
        "data": {"sceneName": scene.name},
        "refs": {"sceneName": scene.name},
    }


@handler("POST", "/scene/set_unit_scale_for_modular_kit")
def scene_set_unit_scale_for_modular_kit(body: dict[str, Any]) -> dict[str, Any]:
    """Set scene units to UE5 cm convention (1 BU = 1 cm by default)."""
    scene = get_scene(body.get("sceneName"))
    scale = float(body.get("scale", 0.01))
    with composite_undo(f"scene_set_unit_scale_for_modular_kit:{scene.name}"):
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = scale
    return {
        "ok": True,
        "data": {"sceneName": scene.name, "scaleLength": scale},
        "refs": {"sceneName": scene.name},
    }


@handler("GET", "/scene/list")
def scene_list(_body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    return {
        "ok": True,
        "data": {
            "scenes": [s.name for s in bpy.data.scenes],
            "active": bpy.context.scene.name if bpy.context.scene else None,
        },
    }
