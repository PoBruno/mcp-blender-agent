"""Vision feedback handlers — the visual loop that powers AlphaFold-style recycling.

These endpoints exist so the agent can SEE what it built, score it against a
brief, and iterate. Without these, every modeling call is blind.

Endpoints
---------
- /vision/contact_sheet     — render N angles, compose into a single PNG grid
- /vision/turntable         — render a 360° rotation as a sequence of PNGs
- /vision/topology_inspect  — quad/tri/ngon counts, manifold flags, normals
- /vision/scale_report      — bbox + dimensions, optional comparison to spec
- /vision/screenshot_viewport — capture current viewport (when not background)
"""

from __future__ import annotations

import math
import os
import tempfile
from typing import Any, Iterable, List, Optional, Tuple

from ..helpers import (
    InvalidInputError,
    get_object,
    get_scene,
)
from ..server import handler


# ---------------------------------------------------------------------------
# camera placement helper
# ---------------------------------------------------------------------------

def _bbox_world_corners(objects: Iterable[Any]) -> List[Tuple[float, float, float]]:
    """All world-space bbox corners across the given objects."""
    corners: List[Tuple[float, float, float]] = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT", "ARMATURE", "EMPTY"}:
            continue
        try:
            mw = obj.matrix_world
            for c in obj.bound_box:
                v = mw @ _vec3(c)
                corners.append((v.x, v.y, v.z))
        except Exception:  # noqa: BLE001
            continue
    return corners


def _vec3(seq: Any) -> Any:
    from mathutils import Vector  # type: ignore
    return Vector((seq[0], seq[1], seq[2]))


def _aabb(corners: List[Tuple[float, float, float]]) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
    if not corners:
        return None
    xs = [c[0] for c in corners]; ys = [c[1] for c in corners]; zs = [c[2] for c in corners]
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


def _resolve_targets(body: dict[str, Any]) -> List[Any]:
    import bpy  # type: ignore
    names = body.get("objectNames")
    if names is None:
        return [o for o in bpy.context.scene.objects if not o.hide_render]
    if not isinstance(names, list):
        raise InvalidInputError("objectNames must be a list of strings")
    return [get_object(str(n)) for n in names]


def _place_camera_around(scene: Any, targets: List[Any], angle: str, padding: float = 1.4) -> Tuple[Any, bool]:
    """Position a temporary camera looking at the centroid of the targets.

    Returns (camera_object, created_flag). Caller is responsible for cleanup
    when created_flag is True.
    """
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    corners = _bbox_world_corners(targets)
    aabb = _aabb(corners)
    if aabb is None:
        raise InvalidInputError("targets have no renderable geometry")
    (mn, mx) = aabb
    centroid = Vector((((mn[0] + mx[0]) / 2.0), ((mn[1] + mx[1]) / 2.0), ((mn[2] + mx[2]) / 2.0)))
    size = max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2], 0.1)
    distance = size * padding * 1.6  # comfortable framing

    # offset by angle keyword
    offsets = {
        "front":          Vector(( 0.0, -1.0,  0.20)),
        "back":           Vector(( 0.0,  1.0,  0.20)),
        "left":           Vector((-1.0,  0.0,  0.20)),
        "right":          Vector(( 1.0,  0.0,  0.20)),
        "top":            Vector(( 0.0,  0.0,  1.0)),
        "bottom":         Vector(( 0.0,  0.0, -1.0)),
        "three_quarter":  Vector(( 0.85, -0.85, 0.55)),
        "three_quarter_back": Vector((-0.85, 0.85, 0.55)),
    }
    if angle not in offsets:
        raise InvalidInputError(
            f"unknown angle {angle!r}; valid: {sorted(offsets)}"
        )
    direction = offsets[angle].normalized()
    cam_loc = centroid + direction * distance

    cam_data = bpy.data.cameras.new("_vision_tmp_cam")
    cam_obj = bpy.data.objects.new("_vision_tmp_cam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = cam_loc
    # aim at centroid
    direction_to_target = (centroid - cam_loc).normalized()
    # blender camera looks down -Z; build rotation to align -Z with direction_to_target
    rot_quat = direction_to_target.to_track_quat("-Z", "Y")
    cam_obj.rotation_mode = "QUATERNION"
    cam_obj.rotation_quaternion = rot_quat
    cam_obj.rotation_mode = "XYZ"
    return cam_obj, True


def _place_turntable_camera(scene: Any, targets: List[Any], azimuth_deg: float, elevation_deg: float = 12.0, padding: float = 1.4) -> Any:
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    corners = _bbox_world_corners(targets)
    aabb = _aabb(corners)
    if aabb is None:
        raise InvalidInputError("targets have no renderable geometry")
    (mn, mx) = aabb
    centroid = Vector(((mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0, (mn[2] + mx[2]) / 2.0))
    size = max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2], 0.1)
    distance = size * padding * 1.7

    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    x = distance * math.cos(el) * math.sin(az)
    y = -distance * math.cos(el) * math.cos(az)
    z = distance * math.sin(el)
    cam_loc = centroid + Vector((x, y, z))

    cam_data = bpy.data.cameras.new("_vision_tt_cam")
    cam_obj = bpy.data.objects.new("_vision_tt_cam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = cam_loc
    direction_to_target = (centroid - cam_loc).normalized()
    rot_quat = direction_to_target.to_track_quat("-Z", "Y")
    cam_obj.rotation_mode = "QUATERNION"
    cam_obj.rotation_quaternion = rot_quat
    cam_obj.rotation_mode = "XYZ"
    return cam_obj


# ---------------------------------------------------------------------------
# contact_sheet
# ---------------------------------------------------------------------------

@handler("POST", "/vision/contact_sheet")
def vision_contact_sheet(body: dict[str, Any]) -> dict[str, Any]:
    """Render N angles of the targets, compose a single PNG grid.

    Body:
        objectNames?: list[str]  — None ⇒ all visible render objects
        angles?: list[str]       — default ['front','side','top','three_quarter']
                                   valid: front,back,left,right,top,bottom,
                                   three_quarter,three_quarter_back
                                   (alias: 'side' ⇒ 'left')
        resolution?: int         — per-thumbnail square pixels, default 384
        padding?: float          — camera framing padding, default 1.4
        outputPath: str          — final PNG path (the grid)
        engine?: str             — 'BLENDER_EEVEE'|'BLENDER_EEVEE_NEXT'|'CYCLES'
        keepTiles?: bool         — also keep individual tile PNGs, default False

    Returns the grid path under refs.contactSheet and per-tile paths under
    data.tiles.
    """
    import bpy  # type: ignore

    scene = get_scene(body.get("sceneName"))
    targets = _resolve_targets(body)
    if not targets:
        raise InvalidInputError("no renderable objects to capture")

    angles_in = body.get("angles") or ["front", "side", "top", "three_quarter"]
    if not isinstance(angles_in, list) or not angles_in:
        raise InvalidInputError("angles must be a non-empty list of strings")
    # 'side' is an alias for 'left'
    angles = [("left" if a == "side" else a) for a in angles_in]

    tile_res = int(body.get("resolution", 384))
    if tile_res < 64 or tile_res > 4096:
        raise InvalidInputError("resolution must be in [64,4096]")
    padding = float(body.get("padding", 1.4))

    output_path = body.get("outputPath")
    if not output_path:
        raise InvalidInputError("outputPath is required")
    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    keep_tiles = bool(body.get("keepTiles", False))
    engine_override = body.get("engine")

    # save/restore camera + render settings
    prev_camera = scene.camera
    prev_engine = scene.render.engine
    prev_res_x = scene.render.resolution_x
    prev_res_y = scene.render.resolution_y
    prev_filepath = scene.render.filepath
    prev_file_format = scene.render.image_settings.file_format

    tile_paths: List[str] = []
    cams_created: List[Any] = []

    try:
        scene.render.resolution_x = tile_res
        scene.render.resolution_y = tile_res
        scene.render.image_settings.file_format = "PNG"
        if engine_override:
            try:
                scene.render.engine = engine_override
            except (TypeError, ValueError):
                pass  # keep current

        for idx, angle in enumerate(angles):
            cam_obj, _created = _place_camera_around(scene, targets, angle, padding=padding)
            cams_created.append(cam_obj)
            scene.camera = cam_obj

            tile_path = os.path.join(
                tempfile.gettempdir() if not keep_tiles else out_dir,
                f"_vision_tile_{idx:02d}_{angle}.png",
            )
            scene.render.filepath = tile_path
            bpy.ops.render.render(write_still=True)
            tile_paths.append(tile_path)
    finally:
        # restore
        scene.camera = prev_camera
        scene.render.engine = prev_engine
        scene.render.resolution_x = prev_res_x
        scene.render.resolution_y = prev_res_y
        scene.render.filepath = prev_filepath
        scene.render.image_settings.file_format = prev_file_format
        for cam in cams_created:
            try:
                bpy.data.objects.remove(cam, do_unlink=True)
            except Exception:  # noqa: BLE001
                pass

    # compose grid using bpy.data.images pixel ops (no PIL dependency)
    grid_path = _compose_grid(tile_paths, output_path, tile_res)

    # optionally delete the temp tiles
    if not keep_tiles:
        for p in tile_paths:
            try:
                os.remove(p)
            except OSError:
                pass
        tile_paths = []

    return {
        "ok": True,
        "data": {
            "contactSheet": grid_path,
            "tiles": tile_paths,
            "angles": angles,
            "resolution": tile_res,
            "objectCount": len(targets),
        },
        "refs": {"contactSheet": grid_path},
        "nextSteps": [
            "open the contactSheet PNG and self-critique on the 6-axis rubric",
            "if any axis < 4, refine one class of issue and re-run",
        ],
    }


def _compose_grid(tile_paths: List[str], output_path: str, tile_res: int) -> str:
    """Compose tiles into a 2-column grid. Uses numpy (ships with Blender)."""
    import bpy  # type: ignore
    import numpy as np  # type: ignore

    n = len(tile_paths)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    grid_w = cols * tile_res
    grid_h = rows * tile_res

    grid = np.zeros((grid_h, grid_w, 4), dtype=np.float32)
    grid[..., 3] = 1.0  # opaque alpha by default

    for idx, tp in enumerate(tile_paths):
        try:
            tile_img = bpy.data.images.load(tp, check_existing=False)
        except RuntimeError:
            continue
        try:
            tw = tile_img.size[0]
            th = tile_img.size[1]
            if tw <= 0 or th <= 0:
                continue
            arr = np.empty(tw * th * 4, dtype=np.float32)
            tile_img.pixels.foreach_get(arr)
            arr = arr.reshape((th, tw, 4))
            # blender image origin is bottom-left, our np 'grid' uses same convention
            r = idx // cols
            c = idx % cols
            x0 = c * tile_res
            y0_top = grid_h - tile_res - r * tile_res  # bottom-left of this tile
            ch = min(th, tile_res)
            cw = min(tw, tile_res)
            grid[y0_top:y0_top + ch, x0:x0 + cw] = arr[:ch, :cw]
        finally:
            try:
                bpy.data.images.remove(tile_img)
            except Exception:  # noqa: BLE001
                pass

    grid_name = f"_vision_grid_{os.path.basename(output_path)}"
    if grid_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[grid_name])
    grid_img = bpy.data.images.new(grid_name, width=grid_w, height=grid_h, alpha=True)
    flat = grid.reshape(-1).astype(np.float32)
    grid_img.pixels.foreach_set(flat)
    grid_img.filepath_raw = output_path
    grid_img.file_format = "PNG"
    grid_img.save()
    bpy.data.images.remove(grid_img)
    return output_path


# ---------------------------------------------------------------------------
# turntable
# ---------------------------------------------------------------------------

@handler("POST", "/vision/turntable")
def vision_turntable(body: dict[str, Any]) -> dict[str, Any]:
    """Render a 360° rotation as a sequence of PNGs.

    Body:
        objectNames?: list[str]   — default all visible
        frames?: int              — default 12 (every 30°)
        elevation?: float (deg)   — default 12
        resolution?: int          — square pixels, default 512
        padding?: float           — default 1.4
        outputDir: str            — directory for the N frames
        filenamePrefix?: str      — default 'turntable_'
        engine?: str
    """
    import bpy  # type: ignore

    scene = get_scene(body.get("sceneName"))
    targets = _resolve_targets(body)
    if not targets:
        raise InvalidInputError("no renderable objects to capture")

    frames = int(body.get("frames", 12))
    if frames < 2 or frames > 360:
        raise InvalidInputError("frames must be in [2,360]")
    elevation = float(body.get("elevation", 12.0))
    res = int(body.get("resolution", 512))
    if res < 64 or res > 4096:
        raise InvalidInputError("resolution must be in [64,4096]")
    padding = float(body.get("padding", 1.4))

    output_dir = body.get("outputDir")
    if not output_dir:
        raise InvalidInputError("outputDir is required")
    os.makedirs(output_dir, exist_ok=True)
    prefix = body.get("filenamePrefix", "turntable_")
    engine_override = body.get("engine")

    prev_camera = scene.camera
    prev_engine = scene.render.engine
    prev_res_x = scene.render.resolution_x
    prev_res_y = scene.render.resolution_y
    prev_filepath = scene.render.filepath
    prev_file_format = scene.render.image_settings.file_format

    rendered: List[str] = []
    cams_created: List[Any] = []
    try:
        scene.render.resolution_x = res
        scene.render.resolution_y = res
        scene.render.image_settings.file_format = "PNG"
        if engine_override:
            try:
                scene.render.engine = engine_override
            except (TypeError, ValueError):
                pass

        for i in range(frames):
            az = (360.0 / frames) * i
            cam = _place_turntable_camera(scene, targets, az, elevation, padding)
            cams_created.append(cam)
            scene.camera = cam
            fpath = os.path.join(output_dir, f"{prefix}{i:03d}.png")
            scene.render.filepath = fpath
            bpy.ops.render.render(write_still=True)
            rendered.append(fpath)
            # remove cam immediately to keep scene clean
            bpy.data.objects.remove(cam, do_unlink=True)
            cams_created.pop()
    finally:
        scene.camera = prev_camera
        scene.render.engine = prev_engine
        scene.render.resolution_x = prev_res_x
        scene.render.resolution_y = prev_res_y
        scene.render.filepath = prev_filepath
        scene.render.image_settings.file_format = prev_file_format
        for cam in cams_created:
            try:
                bpy.data.objects.remove(cam, do_unlink=True)
            except Exception:  # noqa: BLE001
                pass

    return {
        "ok": True,
        "data": {
            "frames": rendered,
            "count": len(rendered),
            "elevationDeg": elevation,
            "resolution": res,
        },
        "refs": {"frames": rendered},
    }


# ---------------------------------------------------------------------------
# topology_inspect
# ---------------------------------------------------------------------------

@handler("POST", "/vision/topology_inspect")
def vision_topology_inspect(body: dict[str, Any]) -> dict[str, Any]:
    """Per-object topology metrics: tri/quad/ngon counts, manifold, normals.

    Body:
        objectNames?: list[str]   — default: all MESH objects in scene
    """
    import bpy  # type: ignore
    import bmesh  # type: ignore

    names = body.get("objectNames")
    if names is None:
        objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    else:
        if not isinstance(names, list):
            raise InvalidInputError("objectNames must be a list of strings")
        objects = [get_object(str(n)) for n in names]
        for o in objects:
            if o.type != "MESH":
                raise InvalidInputError(f"object {o.name!r} is type {o.type}, not MESH")

    reports: List[dict[str, Any]] = []
    total = {"vertices": 0, "edges": 0, "faces": 0, "tris": 0, "quads": 0, "ngons": 0,
             "nonManifoldEdges": 0, "loose": 0}

    for obj in objects:
        me = obj.data
        bm = bmesh.new()
        try:
            bm.from_mesh(me)
            tris = sum(1 for f in bm.faces if len(f.verts) == 3)
            quads = sum(1 for f in bm.faces if len(f.verts) == 4)
            ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
            nonmanifold_edges = sum(1 for e in bm.edges if not e.is_manifold)
            loose_verts = sum(1 for v in bm.verts if not v.link_edges)
            # bbox
            if bm.verts:
                xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
                dim = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
            else:
                dim = (0.0, 0.0, 0.0)
            face_count = len(bm.faces)
            quad_ratio = (quads / face_count) if face_count else 0.0
            report = {
                "objectName": obj.name,
                "vertices": len(bm.verts),
                "edges": len(bm.edges),
                "faces": face_count,
                "tris": tris,
                "quads": quads,
                "ngons": ngons,
                "quadRatio": quad_ratio,
                "nonManifoldEdges": nonmanifold_edges,
                "looseVertices": loose_verts,
                "dimensionsLocal": list(dim),
                "hasUV": bool(me.uv_layers),
                "uvLayerCount": len(me.uv_layers),
                "materialSlotCount": len(obj.material_slots),
                # estimated render-tri count (each ngon ≈ N-2 tris)
                "estimatedRenderTris": tris + 2 * quads + sum(
                    max(0, len(f.verts) - 2) for f in bm.faces if len(f.verts) > 4
                ),
            }
            reports.append(report)
            total["vertices"] += report["vertices"]
            total["edges"] += report["edges"]
            total["faces"] += report["faces"]
            total["tris"] += report["tris"]
            total["quads"] += report["quads"]
            total["ngons"] += report["ngons"]
            total["nonManifoldEdges"] += report["nonManifoldEdges"]
            total["loose"] += report["looseVertices"]
        finally:
            bm.free()

    warnings: List[str] = []
    if total["ngons"] > 0:
        warnings.append(f"{total['ngons']} n-gon(s) present — consider triangulate or quad_remesh")
    if total["nonManifoldEdges"] > 0:
        warnings.append(
            f"{total['nonManifoldEdges']} non-manifold edge(s) — voxel_remesh recommended"
        )
    if total["loose"] > 0:
        warnings.append(f"{total['loose']} loose vert(s) — merge_by_distance suggested")

    return {
        "ok": True,
        "data": {
            "perObject": reports,
            "totals": total,
            "objectCount": len(objects),
        },
        "warnings": warnings,
        "refs": {"objectNames": [r["objectName"] for r in reports]},
    }


# ---------------------------------------------------------------------------
# scale_report
# ---------------------------------------------------------------------------

@handler("POST", "/vision/scale_report")
def vision_scale_report(body: dict[str, Any]) -> dict[str, Any]:
    """World-space AABB of the targets, optional comparison to a spec.

    Body:
        objectNames?: list[str]                 — default all visible
        expected?: {x?: float, y?: float, z?: float}  — meters, optional
        tolerance?: float                       — default 0.10 (10%)
    """
    targets = _resolve_targets(body)
    if not targets:
        raise InvalidInputError("no renderable objects to measure")

    aabb = _aabb(_bbox_world_corners(targets))
    if aabb is None:
        raise InvalidInputError("targets have no geometry")
    (mn, mx) = aabb
    dims = (mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2])
    centroid = ((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2)

    expected = body.get("expected") or {}
    tol = float(body.get("tolerance", 0.10))
    deltas: dict[str, dict[str, float]] = {}
    spec_ok = True
    if isinstance(expected, dict):
        for axis_idx, axis in enumerate("xyz"):
            if axis in expected:
                want = float(expected[axis])
                got = dims[axis_idx]
                pct = abs(got - want) / max(want, 1e-6)
                deltas[axis] = {"expected": want, "actual": got, "pctDelta": pct}
                if pct > tol:
                    spec_ok = False

    return {
        "ok": True,
        "data": {
            "objectCount": len(targets),
            "min": list(mn),
            "max": list(mx),
            "dimensions": list(dims),
            "centroid": list(centroid),
            "expected": expected,
            "tolerance": tol,
            "deltas": deltas,
            "withinSpec": spec_ok,
        },
        "refs": {"objectNames": [o.name for o in targets]},
    }


# ---------------------------------------------------------------------------
# screenshot_viewport (best-effort — only works in GUI mode)
# ---------------------------------------------------------------------------

@handler("POST", "/vision/screenshot_viewport")
def vision_screenshot_viewport(body: dict[str, Any]) -> dict[str, Any]:
    """Capture the current 3D viewport to PNG. Only works in GUI mode.

    Body:
        outputPath: str
    """
    import bpy  # type: ignore

    output_path = body.get("outputPath")
    if not output_path:
        raise InvalidInputError("outputPath is required")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # find a 3D viewport
    area_found = None
    region_found = None
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area_found = area
                for region in area.regions:
                    if region.type == "WINDOW":
                        region_found = region
                        break
                break
        if area_found:
            break
    if area_found is None or region_found is None:
        return {
            "ok": False,
            "errorCode": "NO_VIEWPORT",
            "data": {"message": "no 3D viewport available (background mode?)"},
        }
    with bpy.context.temp_override(window=window, area=area_found, region=region_found):
        bpy.ops.screen.screenshot_area(filepath=output_path)
    return {"ok": True, "data": {"filepath": output_path}, "refs": {"filepath": output_path}}
