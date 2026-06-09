"""Bar stool parametric builder — round seat + footrest + 4 angled legs."""

from __future__ import annotations

import math
from typing import Any, Dict

import bpy  # type: ignore
import bmesh  # type: ignore
from mathutils import Matrix, Vector  # type: ignore

from ..anatomy.proportions import furniture_defaults
from .chair_beach import _ensure_material, _link, _assign_material


def _cylinder_mesh(name: str, radius: float, height: float, segments: int = 32) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=height,
        matrix=Matrix.Translation((0.0, 0.0, height / 2.0)),
    )
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def build(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build a bar stool.

    Params:
        seat_height: float (m)     — default 0.75
        seat_diameter: float (m)   — default 0.32
        seat_thickness: float (m)  — default 0.04
        footrest_height: float (m) — default 0.30
        leg_thickness: float (m)   — default 0.03
        material_recipe: str       — default 'brushed_aluminum'
        location: [x,y,z]
        collection_name: str       — default 'StoolBar'
    """
    defaults = furniture_defaults("stool_bar")
    p = dict(defaults)
    p.update(params or {})

    seat_h = float(p["seat_height"])
    seat_d = float(p["seat_diameter"])
    seat_t = float(p.get("seat_thickness", 0.04))
    foot_h = float(p["footrest_height"])
    leg_t = float(p["leg_thickness"])
    mat_name = str(p.get("material_recipe", "brushed_aluminum"))
    origin = Vector(p.get("location", [0.0, 0.0, 0.0]))
    coll_name = str(p.get("collection_name", "StoolBar"))

    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)

    mat = _ensure_material(f"mat_{mat_name}", mat_name)
    parts: Dict[str, str] = {}

    # seat (cylinder)
    seat_mesh = _cylinder_mesh("mesh_stool_seat", seat_d / 2.0, seat_t, segments=48)
    seat_obj = bpy.data.objects.new("stool_bar_seat", seat_mesh)
    seat_obj.location = origin + Vector((0.0, 0.0, seat_h - seat_t / 2.0))
    _link(seat_obj, coll)
    _assign_material(seat_obj, mat)
    parts["seat"] = seat_obj.name

    # 4 legs, splayed outward by ~5°
    splay = math.radians(5.0)
    leg_h = seat_h
    base_offset = seat_d * 0.4
    top_offset = seat_d * 0.45
    for ang_deg, tag in [(45, "FR"), (135, "FL"), (225, "BL"), (315, "BR")]:
        ang = math.radians(ang_deg)
        # build leg cylinder centered then translate/rotate
        leg_mesh = _cylinder_mesh(f"mesh_stool_leg_{tag}", leg_t / 2.0, leg_h, segments=12)
        leg_obj = bpy.data.objects.new(f"stool_bar_leg_{tag}", leg_mesh)
        # place foot at outer ring, top under seat at inner ring
        foot_pos = Vector((math.cos(ang) * top_offset, math.sin(ang) * top_offset, 0.0))
        leg_obj.location = origin + foot_pos
        # tilt outward — rotate around the perpendicular horizontal axis
        # axis = direction-from-origin rotated 90° in XY
        # We rotate so the leg leans away from center
        # rotation = compose Euler from look-at: simpler to tilt by splay around tangent
        tangent = Vector((-math.sin(ang), math.cos(ang), 0.0))
        # rotation_axis-angle equivalent → just set rotation_euler approximations
        # Use rotation_quaternion for precision
        from mathutils import Quaternion  # type: ignore
        q = Quaternion(tangent, splay) if foot_pos.length > 0 else Quaternion()
        leg_obj.rotation_mode = "QUATERNION"
        leg_obj.rotation_quaternion = q
        leg_obj.rotation_mode = "XYZ"
        _link(leg_obj, coll)
        _assign_material(leg_obj, mat)
        parts[f"leg_{tag}"] = leg_obj.name

    # footrest ring — torus-ish, modelled as cylinder of large radius small thickness
    footrest_radius = seat_d * 0.42
    fr_mesh = _cylinder_mesh("mesh_stool_footrest", footrest_radius, 0.008, segments=48)
    fr_obj = bpy.data.objects.new("stool_bar_footrest", fr_mesh)
    fr_obj.location = origin + Vector((0.0, 0.0, foot_h))
    _link(fr_obj, coll)
    _assign_material(fr_obj, mat)
    parts["footrest"] = fr_obj.name

    return {
        "parts": parts,
        "dimensions": {"diameter": seat_d, "height": seat_h},
        "materials": [mat.name],
        "collection": coll.name,
        "params": p,
    }
