"""Dining table parametric builder."""

from __future__ import annotations

from typing import Any, Dict

import bpy  # type: ignore
import bmesh  # type: ignore
from mathutils import Matrix, Vector  # type: ignore

from ..anatomy.proportions import furniture_defaults
from .chair_beach import _cube_mesh, _ensure_material, _link, _assign_material


def build(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build a rectangular dining table.

    Params:
        top_length: float (m)        — default 1.80
        top_width: float (m)         — default 0.90
        top_height: float (m)        — default 0.75
        top_thickness: float (m)     — default 0.04
        leg_thickness: float (m)     — default 0.06
        leg_inset: float (m)         — default 0.10 from each corner
        material_recipe: str         — default 'polished_oak'
        location: [x,y,z]            — default [0,0,0]
        collection_name: str         — default 'TableDining'
    """
    defaults = furniture_defaults("table_dining")
    p = dict(defaults)
    p.update(params or {})

    L = float(p["top_length"])
    W = float(p["top_width"])
    H = float(p["top_height"])
    T = float(p["top_thickness"])
    leg_t = float(p["leg_thickness"])
    inset = float(p.get("leg_inset", 0.10))
    mat_name = str(p.get("material_recipe", "polished_oak"))
    origin = Vector(p.get("location", [0.0, 0.0, 0.0]))
    coll_name = str(p.get("collection_name", "TableDining"))

    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)

    mat = _ensure_material(f"mat_{mat_name}", mat_name)

    parts: Dict[str, str] = {}

    # top
    top_mesh = _cube_mesh("mesh_table_top", (L, W, T))
    top_obj = bpy.data.objects.new("table_dining_top", top_mesh)
    top_obj.location = origin + Vector((0.0, 0.0, H - T / 2.0))
    _link(top_obj, coll)
    _assign_material(top_obj, mat)
    parts["top"] = top_obj.name

    leg_h = H - T
    leg_positions = [
        ( (L / 2 - inset),  (W / 2 - inset), "FR"),
        (-(L / 2 - inset),  (W / 2 - inset), "FL"),
        ( (L / 2 - inset), -(W / 2 - inset), "BR"),
        (-(L / 2 - inset), -(W / 2 - inset), "BL"),
    ]
    for x, y, tag in leg_positions:
        leg_mesh = _cube_mesh(f"mesh_table_leg_{tag}", (leg_t, leg_t, leg_h), origin="bottom")
        leg_obj = bpy.data.objects.new(f"table_dining_leg_{tag}", leg_mesh)
        leg_obj.location = origin + Vector((x, y, 0.0))
        _link(leg_obj, coll)
        _assign_material(leg_obj, mat)
        parts[f"leg_{tag}"] = leg_obj.name

    return {
        "parts": parts,
        "dimensions": {"length": L, "width": W, "height": H},
        "materials": [mat.name],
        "collection": coll.name,
        "params": p,
    }
