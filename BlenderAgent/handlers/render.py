"""Render handlers (B9)."""

from __future__ import annotations

import os
from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_scene,
)
from ..server import handler


@handler("POST", "/render/set_engine")
def render_set_engine(body: dict[str, Any]) -> dict[str, Any]:
    scene = get_scene(body.get("sceneName"))
    requested = body.get("engine", "CYCLES")
    # Blender 4.2 has BLENDER_EEVEE_NEXT; Blender 5.x renamed it back to BLENDER_EEVEE
    # and removed BLENDER_EEVEE_NEXT. Provide bidirectional fallback so the same
    # tool call works on both versions.
    aliases = {
        "BLENDER_EEVEE_NEXT": "BLENDER_EEVEE",
        "BLENDER_EEVEE": "BLENDER_EEVEE_NEXT",
    }
    attempts = [requested]
    if requested in aliases:
        attempts.append(aliases[requested])

    last_exc: Exception | None = None
    with composite_undo(f"render_set_engine:{scene.name}/{requested}"):
        for candidate in attempts:
            try:
                scene.render.engine = candidate
                last_exc = None
                break
            except (TypeError, ValueError) as exc:
                last_exc = exc
    if last_exc is not None:
        raise InvalidInputError(
            f"Unknown render engine {requested!r} (aliases tried: {attempts}); {last_exc}"
        )
    return {"ok": True, "data": {"sceneName": scene.name, "engine": scene.render.engine},
            "refs": {"sceneName": scene.name}}


@handler("POST", "/render/set_resolution")
def render_set_resolution(body: dict[str, Any]) -> dict[str, Any]:
    scene = get_scene(body.get("sceneName"))
    w = int(body.get("width", 1920))
    h = int(body.get("height", 1080))
    pct = int(body.get("percentage", 100))
    with composite_undo(f"render_set_resolution:{scene.name}/{w}x{h}"):
        scene.render.resolution_x = w
        scene.render.resolution_y = h
        scene.render.resolution_percentage = pct
    return {
        "ok": True,
        "data": {
            "sceneName": scene.name, "width": w, "height": h, "percentage": pct,
        },
        "refs": {"sceneName": scene.name},
    }


@handler("POST", "/render/render_still")
def render_render_still(body: dict[str, Any]) -> dict[str, Any]:
    """Render a single frame and save to filepath."""
    import bpy  # type: ignore
    scene = get_scene(body.get("sceneName"))
    filepath = body.get("filepath")
    if not filepath:
        raise InvalidInputError("filepath is required")
    d = os.path.dirname(filepath)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    scene.render.filepath = filepath
    scene.render.image_settings.file_format = body.get("fileFormat", "PNG")
    bpy.ops.render.render(write_still=True)
    return {
        "ok": True,
        "data": {"sceneName": scene.name, "filepath": scene.render.filepath},
        "refs": {"sceneName": scene.name, "filepath": scene.render.filepath},
    }


@handler("POST", "/render/render_animation")
def render_render_animation(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    scene = get_scene(body.get("sceneName"))
    filepath = body.get("filepathPrefix")
    if not filepath:
        raise InvalidInputError("filepathPrefix is required")
    d = os.path.dirname(filepath)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    scene.render.filepath = filepath
    scene.render.image_settings.file_format = body.get("fileFormat", "PNG")
    bpy.ops.render.render(animation=True)
    return {
        "ok": True,
        "data": {
            "sceneName": scene.name,
            "filepathPrefix": scene.render.filepath,
            "frameStart": scene.frame_start,
            "frameEnd": scene.frame_end,
        },
        "refs": {"sceneName": scene.name},
    }
