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


@handler("POST", "/render/set_output")
def render_set_output(body: dict[str, Any]) -> dict[str, Any]:
    """Configure render output filepath, file format, color depth, frames, fps.

    Body: {sceneName?: str, filepath?: str, fileFormat?: str, colorMode?: 'BW'|'RGB'|'RGBA',
           colorDepth?: '8'|'16'|'32', frameStart?: int, frameEnd?: int, frameStep?: int,
           fps?: int, fpsBase?: float, compression?: int (0-100 for PNG)}

    file_format values supported by Blender: PNG, JPEG, BMP, IRIS, OPEN_EXR,
    OPEN_EXR_MULTILAYER, HDR, TIFF, TARGA, TARGA_RAW, CINEON, DPX, WEBP, AVI_JPEG,
    AVI_RAW, FFMPEG.
    """
    scene = get_scene(body.get("sceneName"))
    rs = scene.render
    isettings = rs.image_settings

    filepath = body.get("filepath")
    file_format = body.get("fileFormat")
    color_mode = body.get("colorMode")
    color_depth = body.get("colorDepth")
    frame_start = body.get("frameStart")
    frame_end = body.get("frameEnd")
    frame_step = body.get("frameStep")
    fps = body.get("fps")
    fps_base = body.get("fpsBase")
    compression = body.get("compression")

    with composite_undo(f"render_set_output:{scene.name}"):
        if filepath is not None:
            rs.filepath = str(filepath)
        if file_format is not None:
            try:
                isettings.file_format = str(file_format)
            except (TypeError, ValueError) as exc:
                raise InvalidInputError(
                    f"Unknown fileFormat {file_format!r}: {exc}"
                ) from exc
        if color_mode is not None:
            try:
                isettings.color_mode = str(color_mode)
            except (TypeError, ValueError) as exc:
                raise InvalidInputError(
                    f"Unknown colorMode {color_mode!r}: {exc}"
                ) from exc
        if color_depth is not None:
            try:
                isettings.color_depth = str(color_depth)
            except (TypeError, ValueError) as exc:
                raise InvalidInputError(
                    f"Unknown colorDepth {color_depth!r}: {exc}"
                ) from exc
        if compression is not None:
            try:
                isettings.compression = int(compression)
            except (TypeError, ValueError, AttributeError):
                pass
        if frame_start is not None:
            scene.frame_start = int(frame_start)
        if frame_end is not None:
            scene.frame_end = int(frame_end)
        if frame_step is not None:
            scene.frame_step = int(frame_step)
        if fps is not None:
            rs.fps = int(fps)
        if fps_base is not None:
            rs.fps_base = float(fps_base)

    return {
        "ok": True,
        "data": {
            "sceneName": scene.name,
            "filepath": rs.filepath,
            "fileFormat": isettings.file_format,
            "colorMode": isettings.color_mode,
            "colorDepth": isettings.color_depth,
            "frameStart": scene.frame_start,
            "frameEnd": scene.frame_end,
            "frameStep": scene.frame_step,
            "fps": rs.fps,
            "fpsBase": rs.fps_base,
        },
        "refs": {"sceneName": scene.name},
    }
