"""Camera handlers (B9)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_collection,
    get_object,
    get_scene,
)
from ..server import handler


@handler("POST", "/camera/create")
def camera_create(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    name = body.get("name", "Camera")
    location = tuple(body.get("location", (0.0, -7.0, 5.0)))
    rotation = tuple(body.get("rotation", (1.1, 0.0, 0.0)))
    lens = float(body.get("lens", 50.0))
    collection_name = body.get("collectionName")

    with composite_undo(f"camera_create:{name}"):
        cam_data = bpy.data.cameras.new(name=f"{name}_data")
        cam_data.lens = lens
        cam_obj = bpy.data.objects.new(name=name, object_data=cam_data)
        cam_obj.location = location
        cam_obj.rotation_euler = rotation
        if collection_name:
            get_collection(collection_name).objects.link(cam_obj)
        else:
            bpy.context.scene.collection.objects.link(cam_obj)
    return {
        "ok": True,
        "data": {
            "cameraObjectName": cam_obj.name,
            "cameraDataName": cam_data.name,
            "lens": lens,
        },
        "refs": {"objectName": cam_obj.name, "cameraName": cam_obj.name},
    }


@handler("POST", "/camera/set_active")
def camera_set_active(body: dict[str, Any]) -> dict[str, Any]:
    cam = get_object(body.get("objectName") or body.get("cameraName"))
    if cam.type != "CAMERA":
        raise InvalidInputError(f"{cam.name!r} is not a CAMERA (got {cam.type})")
    scene = get_scene(body.get("sceneName"))
    with composite_undo(f"camera_set_active:{scene.name}/{cam.name}"):
        scene.camera = cam
    return {"ok": True, "data": {"sceneName": scene.name, "cameraName": cam.name},
            "refs": {"sceneName": scene.name, "cameraName": cam.name}}


@handler("POST", "/camera/set_dof")
def camera_set_dof(body: dict[str, Any]) -> dict[str, Any]:
    """Configure depth-of-field on a camera.

    Body: {objectName: str, focusDistance?: float, fStop?: float,
           focusObjectName?: str (overrides focusDistance), useDof?: bool}
    """
    cam = get_object(body.get("objectName") or body.get("cameraName"))
    if cam.type != "CAMERA":
        raise InvalidInputError(f"{cam.name!r} is not a CAMERA (got {cam.type})")
    dof = cam.data.dof
    use_dof = body.get("useDof")
    focus_distance = body.get("focusDistance")
    f_stop = body.get("fStop")
    focus_obj_name = body.get("focusObjectName")
    focus_obj = get_object(focus_obj_name) if focus_obj_name else None

    with composite_undo(f"camera_set_dof:{cam.name}"):
        if use_dof is not None:
            dof.use_dof = bool(use_dof)
        else:
            dof.use_dof = True
        if focus_obj is not None:
            dof.focus_object = focus_obj
        if focus_distance is not None:
            dof.focus_distance = float(focus_distance)
        if f_stop is not None:
            dof.aperture_fstop = float(f_stop)

    return {
        "ok": True,
        "data": {
            "cameraName": cam.name,
            "useDof": dof.use_dof,
            "focusDistance": dof.focus_distance,
            "fStop": dof.aperture_fstop,
            "focusObjectName": dof.focus_object.name if dof.focus_object else None,
        },
        "refs": {"objectName": cam.name, "cameraName": cam.name},
    }


@handler("POST", "/camera/set_clipping")
def camera_set_clipping(body: dict[str, Any]) -> dict[str, Any]:
    """Set near/far clip planes on a camera.

    Body: {objectName: str, clipStart?: float, clipEnd?: float}
    """
    cam = get_object(body.get("objectName") or body.get("cameraName"))
    if cam.type != "CAMERA":
        raise InvalidInputError(f"{cam.name!r} is not a CAMERA (got {cam.type})")
    clip_start = body.get("clipStart")
    clip_end = body.get("clipEnd")
    if clip_start is None and clip_end is None:
        raise InvalidInputError("at least one of clipStart or clipEnd is required")
    with composite_undo(f"camera_set_clipping:{cam.name}"):
        if clip_start is not None:
            cs = float(clip_start)
            if cs <= 0:
                raise InvalidInputError("clipStart must be > 0")
            cam.data.clip_start = cs
        if clip_end is not None:
            ce = float(clip_end)
            if ce <= cam.data.clip_start:
                raise InvalidInputError("clipEnd must be > clipStart")
            cam.data.clip_end = ce
    return {
        "ok": True,
        "data": {
            "cameraName": cam.name,
            "clipStart": cam.data.clip_start,
            "clipEnd": cam.data.clip_end,
        },
        "refs": {"objectName": cam.name, "cameraName": cam.name},
    }
