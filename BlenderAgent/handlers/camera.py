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


@handler("POST", "/camera/frame_object")
def camera_frame_object(body: dict[str, Any]) -> dict[str, Any]:
    """Position a camera to frame a target object, looking at it from a chosen
    direction. Computes a comfortable distance based on the target's bounding
    box and the camera's field of view.

    Body:
      cameraObjectName: str   — existing CAMERA object (created via /camera/create)
      targetObjectName: str   — object to frame (ARMATURE or MESH)
      direction?: 'front'|'back'|'left'|'right'|'top'|'bottom'|'front_top'   (default 'front')
      paddingFactor?: float   — multiplier on computed distance (default 1.4)
      heightOffset?: float    — vertical offset added to target center (default 0)
      setActive?: bool        — also set as scene.camera (default true)
      includeChildren?: bool  — include child mesh bounds (default true; needed for
                                rigs where Armature itself has no geometry)
      sceneName?: str

    Returns the final camera location, the look-at target, and the distance.
    """
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
    import math

    cam = get_object(body.get("cameraObjectName") or body.get("cameraName"))
    if cam.type != "CAMERA":
        raise InvalidInputError(f"{cam.name!r} is not a CAMERA (got {cam.type})")
    target = get_object(body.get("targetObjectName"))
    direction = (body.get("direction") or "front").lower()
    padding = float(body.get("paddingFactor", 1.4))
    height_offset = float(body.get("heightOffset", 0.0))
    set_active = bool(body.get("setActive", True))
    include_children = bool(body.get("includeChildren", True))
    scene = get_scene(body.get("sceneName"))

    if padding <= 0:
        raise InvalidInputError("paddingFactor must be > 0")

    # Compute world-space AABB of target (+ children if requested)
    def aabb_of(obj: Any) -> tuple[Vector, Vector] | None:
        # MESH: 8 bbox corners; ARMATURE: pose-bone heads/tails world-space
        pts: list[Vector] = []
        if obj.type == "MESH" and obj.data is not None:
            mw = obj.matrix_world
            for corner in obj.bound_box:
                pts.append(mw @ Vector(corner))
        elif obj.type == "ARMATURE":
            mw = obj.matrix_world
            for pb in obj.pose.bones:
                pts.append(mw @ pb.head)
                pts.append(mw @ pb.tail)
        else:
            # Other types: just the origin
            pts.append(obj.matrix_world.translation.copy())
        if not pts:
            return None
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        return (lo, hi)

    all_pts: list[Vector] = []
    queue = [target]
    seen: set[str] = set()
    while queue:
        o = queue.pop()
        if o.name in seen:
            continue
        seen.add(o.name)
        b = aabb_of(o)
        if b is not None:
            all_pts.append(b[0])
            all_pts.append(b[1])
        if include_children:
            queue.extend(o.children)

    if not all_pts:
        raise InvalidInputError(f"could not compute bounds for {target.name!r}")

    lo = Vector((min(p.x for p in all_pts), min(p.y for p in all_pts), min(p.z for p in all_pts)))
    hi = Vector((max(p.x for p in all_pts), max(p.y for p in all_pts), max(p.z for p in all_pts)))
    center = (lo + hi) * 0.5
    center.z += height_offset
    size = hi - lo
    radius = max(size.x, size.y, size.z) * 0.5
    if radius <= 0:
        radius = 1.0

    # Distance from a horizontal FOV that fits the radius * padding
    fov = float(cam.data.angle)  # full horizontal angle in radians
    distance = (radius * padding) / math.tan(fov * 0.5)

    # Direction vectors (camera looks at -Z; we position camera, then rotate to look at center)
    dir_map = {
        "front":     Vector(( 0.0, -1.0,  0.0)),
        "back":      Vector(( 0.0,  1.0,  0.0)),
        "left":      Vector((-1.0,  0.0,  0.0)),
        "right":     Vector(( 1.0,  0.0,  0.0)),
        "top":       Vector(( 0.0,  0.0,  1.0)),
        "bottom":    Vector(( 0.0,  0.0, -1.0)),
        "front_top": Vector(( 0.0, -1.0,  0.6)).normalized(),
    }
    if direction not in dir_map:
        raise InvalidInputError(
            f"direction must be one of {sorted(dir_map.keys())}, got {direction!r}"
        )
    v = dir_map[direction]
    cam_loc = center + v * distance

    # Aim camera at center: track_quat returns rotation that maps -Z forward to (center - cam_loc)
    forward = (center - cam_loc).normalized()
    quat = forward.to_track_quat("-Z", "Y")

    with composite_undo(f"camera_frame_object:{cam.name}->{target.name}"):
        cam.location = cam_loc
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = quat
        if set_active:
            scene.camera = cam

    return {
        "ok": True,
        "data": {
            "cameraName": cam.name,
            "targetName": target.name,
            "direction": direction,
            "location": [cam_loc.x, cam_loc.y, cam_loc.z],
            "lookAt": [center.x, center.y, center.z],
            "distance": float(distance),
            "boundsRadius": float(radius),
            "boundsSize": [size.x, size.y, size.z],
            "isActive": set_active,
        },
        "refs": {
            "cameraName": cam.name,
            "objectName": cam.name,
            "targetName": target.name,
        },
    }
