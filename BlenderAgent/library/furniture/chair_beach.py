"""Beach chair (recliner) parametric builder.

Parts produced
--------------
- chair_beach_frame_leg_FL / FR / BL / BR
- chair_beach_frame_rail_L / R                 (long horizontal side rails)
- chair_beach_frame_crossbar_front / back
- chair_beach_frame_arm_L / R
- chair_beach_frame_back_post_L / R            (inclined back posts)
- chair_beach_seat_slat_<i>                    (i = 1..slat_count, on seat)
- chair_beach_back_slat_<i>                    (i = 1..back_slat_count, on back)

Materials (created if missing)
------------------------------
- mat_weathered_teak (frame)
- mat_faded_canvas_<accentColor>  (slats; accentColor in params, default 'orange')
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import bpy  # type: ignore
import bmesh  # type: ignore
from mathutils import Matrix, Vector  # type: ignore

from ..anatomy.proportions import (
    furniture_defaults,
    material_recipe,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _cube_mesh(name: str, size: Tuple[float, float, float], origin: str = "center") -> bpy.types.Mesh:
    """Create a fresh mesh datablock shaped as an axis-aligned box.

    origin == 'center' centers on (0,0,0); 'bottom' places the +Z face at +size.z/2,
    bottom face at 0 (useful for legs).
    """
    sx, sy, sz = size
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if origin == "bottom":
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.0, 0.0, 0.5)))
    else:
        bmesh.ops.create_cube(bm, size=1.0)
    # scale verts to (sx, sy, sz)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _link(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    collection.objects.link(obj)


def _ensure_material(name: str, recipe_name: str) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    rec = material_recipe(recipe_name)
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (
            rec["base_color_r"], rec["base_color_g"], rec["base_color_b"], 1.0,
        )
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = rec["roughness"]
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = rec["metallic"]
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = rec.get("specular", 0.5)
        elif "Specular" in bsdf.inputs:
            bsdf.inputs["Specular"].default_value = rec.get("specular", 0.5)
    return mat


def _assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat


# ---------------------------------------------------------------------------
# public builder
# ---------------------------------------------------------------------------

def build(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build a beach chair. Accepted params (all optional, fall back to defaults):

        length: float (m)              — overall length, default 1.70
        width: float (m)               — overall width, default 0.60
        seat_height: float (m)         — default 0.35
        back_angle_deg: float          — default 28
        leg_thickness: float           — default 0.04
        rail_thickness: float          — default 0.05
        slat_count: int                — seat slats, default 7
        back_slat_count: int           — default 5
        slat_thickness: float          — default 0.012
        slat_gap: float                — default 0.015
        accent_color: str              — material recipe name for slats,
                                         default 'faded_canvas_orange'
        location: [x,y,z]              — origin, default [0,0,0]
        collection_name: str           — target collection, default 'ChairBeach'
        with_arms: bool                — default True
    """
    defaults = furniture_defaults("chair_beach")
    p = dict(defaults)
    p.update(params or {})

    length = float(p["length"])
    width = float(p["width"])
    seat_h = float(p["seat_height"])
    back_angle = math.radians(float(p["back_angle_deg"]))
    leg_t = float(p["leg_thickness"])
    rail_t = float(p["rail_thickness"])
    slat_count = int(p["slat_count"])
    back_slat_count = int(p.get("back_slat_count", 5))
    slat_t = float(p["slat_thickness"])
    slat_gap = float(p["slat_gap"])
    accent_recipe = str(p.get("accent_color", "faded_canvas_orange"))
    with_arms = bool(p.get("with_arms", True))
    origin = Vector(p.get("location", [0.0, 0.0, 0.0]))
    coll_name = str(p.get("collection_name", "ChairBeach"))

    # target collection
    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)

    # materials
    mat_frame = _ensure_material("mat_weathered_teak", "weathered_teak")
    mat_slat = _ensure_material(f"mat_canvas_{accent_recipe}", accent_recipe)

    parts: Dict[str, str] = {}

    # Frame: 4 legs at corners (length axis = Y, width axis = X)
    half_l = length / 2.0
    half_w = width / 2.0 - rail_t / 2.0
    leg_positions = {
        "FL": (-half_w,  half_l - 0.05, 0.0),
        "FR": ( half_w,  half_l - 0.05, 0.0),
        "BL": (-half_w, -half_l + 0.05, 0.0),
        "BR": ( half_w, -half_l + 0.05, 0.0),
    }
    leg_height = seat_h
    for tag, (x, y, _z) in leg_positions.items():
        mesh = _cube_mesh(f"mesh_leg_{tag}", (leg_t, leg_t, leg_height), origin="bottom")
        obj = bpy.data.objects.new(f"chair_beach_frame_leg_{tag}", mesh)
        obj.location = origin + Vector((x, y, 0.0))
        _link(obj, coll)
        _assign_material(obj, mat_frame)
        parts[f"leg_{tag}"] = obj.name

    # Side rails — long, run along Y
    rail_height = rail_t
    rail_z = seat_h
    for sign, tag in [(-1, "L"), (1, "R")]:
        mesh = _cube_mesh(f"mesh_rail_{tag}", (rail_t, length, rail_height))
        obj = bpy.data.objects.new(f"chair_beach_frame_rail_{tag}", mesh)
        obj.location = origin + Vector((sign * half_w, 0.0, rail_z))
        _link(obj, coll)
        _assign_material(obj, mat_frame)
        parts[f"rail_{tag}"] = obj.name

    # Crossbars at front and back (under the seat plane, between the legs)
    inner_w = (2 * half_w) - leg_t
    for side, tag in [(1, "front"), (-1, "back")]:
        mesh = _cube_mesh(f"mesh_crossbar_{tag}", (inner_w, rail_t, rail_height))
        obj = bpy.data.objects.new(f"chair_beach_frame_crossbar_{tag}", mesh)
        obj.location = origin + Vector((0.0, side * (half_l - 0.05), rail_z))
        _link(obj, coll)
        _assign_material(obj, mat_frame)
        parts[f"crossbar_{tag}"] = obj.name

    # Seat slats: span across X, distributed along the front 60% of length
    seat_zone_start = -half_l + 0.1           # back of seat (toward foot end? convention: front = +Y)
    seat_zone_end = half_l * 0.10             # leave back 40% for the inclined backrest
    seat_zone_len = seat_zone_end - seat_zone_start
    slat_pitch = seat_zone_len / max(slat_count, 1)
    slat_width = max(slat_pitch - slat_gap, 0.01)
    slat_z = seat_h + rail_height / 2.0 + slat_t / 2.0
    slat_length_x = (2 * half_w) - 0.01
    for i in range(slat_count):
        y_center = seat_zone_start + slat_pitch * (i + 0.5)
        mesh = _cube_mesh(f"mesh_seat_slat_{i+1}", (slat_length_x, slat_width, slat_t))
        obj = bpy.data.objects.new(f"chair_beach_seat_slat_{i+1}", mesh)
        obj.location = origin + Vector((0.0, y_center, slat_z))
        _link(obj, coll)
        _assign_material(obj, mat_slat)
        parts[f"seat_slat_{i+1}"] = obj.name

    # Back posts: from the back of the seat, inclined upward by back_angle
    back_start_y = seat_zone_end + slat_gap
    back_length = (half_l - back_start_y) / math.cos(back_angle)
    # post center: a bit above the rail, halfway along the back length
    post_t = rail_t
    for sign, tag in [(-1, "L"), (1, "R")]:
        mesh = _cube_mesh(f"mesh_back_post_{tag}", (post_t, post_t, back_length))
        obj = bpy.data.objects.new(f"chair_beach_frame_back_post_{tag}", mesh)
        # midpoint between bottom (at rail) and top
        bottom = Vector((sign * half_w, back_start_y, seat_h))
        # rotate around X axis by -back_angle (tilting away)
        # Compute the post's axis direction
        axis_dir = Vector((0.0, -math.sin(back_angle), math.cos(back_angle)))
        center = bottom + axis_dir * (back_length / 2.0)
        obj.location = origin + center
        obj.rotation_euler = (-back_angle, 0.0, 0.0)
        _link(obj, coll)
        _assign_material(obj, mat_frame)
        parts[f"back_post_{tag}"] = obj.name

    # Back slats — run X across the back, parented to back-post centerline
    back_slat_zone = back_length * 0.85
    back_slat_pitch = back_slat_zone / max(back_slat_count, 1)
    back_slat_width = max(back_slat_pitch - slat_gap, 0.01)
    for i in range(back_slat_count):
        # local-space offset along the back axis (from bottom of posts)
        t_local = back_slat_pitch * (i + 0.5)  # along post local Z
        # world placement = bottom + axis_dir * t_local, with width-axis at X
        bottom = Vector((0.0, back_start_y, seat_h))
        axis_dir = Vector((0.0, -math.sin(back_angle), math.cos(back_angle)))
        center = bottom + axis_dir * t_local
        mesh = _cube_mesh(f"mesh_back_slat_{i+1}", (slat_length_x, back_slat_width, slat_t))
        obj = bpy.data.objects.new(f"chair_beach_back_slat_{i+1}", mesh)
        obj.location = origin + center
        # rotate so slat normal aligns with back plane normal
        obj.rotation_euler = (-back_angle, 0.0, 0.0)
        _link(obj, coll)
        _assign_material(obj, mat_slat)
        parts[f"back_slat_{i+1}"] = obj.name

    # Arms
    if with_arms:
        arm_length = length * 0.35
        arm_thickness = 0.04
        arm_height = 0.15  # above seat
        arm_z = seat_h + arm_height + arm_thickness / 2.0
        for sign, tag in [(-1, "L"), (1, "R")]:
            # vertical support post
            sp_h = arm_height
            sp_mesh = _cube_mesh(f"mesh_arm_support_{tag}", (arm_thickness, arm_thickness, sp_h), origin="bottom")
            sp_obj = bpy.data.objects.new(f"chair_beach_frame_arm_support_{tag}", sp_mesh)
            sp_obj.location = origin + Vector((sign * half_w, arm_length * 0.5, seat_h))
            _link(sp_obj, coll)
            _assign_material(sp_obj, mat_frame)
            parts[f"arm_support_{tag}"] = sp_obj.name

            # horizontal arm rail
            arm_mesh = _cube_mesh(f"mesh_arm_{tag}", (arm_thickness, arm_length, arm_thickness))
            arm_obj = bpy.data.objects.new(f"chair_beach_frame_arm_{tag}", arm_mesh)
            arm_obj.location = origin + Vector((sign * half_w, arm_length * 0.25, arm_z))
            _link(arm_obj, coll)
            _assign_material(arm_obj, mat_frame)
            parts[f"arm_{tag}"] = arm_obj.name

    dims = {
        "length": length,
        "width": 2 * half_w + leg_t,
        "height": seat_h + back_length * math.cos(back_angle) + 0.05,
    }
    return {
        "parts": parts,
        "dimensions": dims,
        "materials": [mat_frame.name, mat_slat.name],
        "collection": coll.name,
        "params": p,
    }
