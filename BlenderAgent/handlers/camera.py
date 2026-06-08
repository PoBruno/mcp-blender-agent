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
