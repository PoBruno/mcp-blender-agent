"""Collision handlers (B1 §7, B2 §23–24)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_object,
    set_active_and_selected,
    ue5_collision_name,
    with_3dview_context,
    with_mode,
)
from ..server import handler


def _next_collision_index(parent_obj: Any, prefix: str) -> int:
    import bpy  # type: ignore
    name_prefix = f"{prefix}_{parent_obj.name}_"
    existing = [o.name for o in bpy.data.objects if o.name.startswith(name_prefix)]
    return len(existing) + 1


@handler("POST", "/collision/add_box")
def collision_add_box(body: dict[str, Any]) -> dict[str, Any]:
    """Generate a `UBX_<Name>_NN` axis-aligned bounding box collision child."""
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    parent = get_object(body.get("objectName"))
    idx = _next_collision_index(parent, "UBX")
    name = ue5_collision_name(parent.name, "UBX", idx)

    with composite_undo(f"collision_add_box:{parent.name}"):
        # Compute bbox in local space
        bbox = [Vector(c) for c in parent.bound_box]
        min_v = Vector((min(c.x for c in bbox), min(c.y for c in bbox), min(c.z for c in bbox)))
        max_v = Vector((max(c.x for c in bbox), max(c.y for c in bbox), max(c.z for c in bbox)))
        center = (min_v + max_v) / 2.0
        size = (max_v - min_v)

        with with_3dview_context():
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=parent.matrix_world @ center)
        col_obj = bpy.context.active_object
        col_obj.name = name
        col_obj.scale = (size.x, size.y, size.z)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        col_obj.display_type = "WIRE"
        col_obj.parent = parent

    return {
        "ok": True,
        "data": {"collisionObjectName": col_obj.name, "parentName": parent.name},
        "refs": {"objectName": col_obj.name, "collisionObjectName": col_obj.name},
    }


@handler("POST", "/collision/add_convex_hull")
def collision_add_convex_hull(body: dict[str, Any]) -> dict[str, Any]:
    """Generate a `UCX_<Name>_NN` convex-hull collision child via Convex Hull bmesh op."""
    import bpy  # type: ignore
    import bmesh  # type: ignore

    parent = get_object(body.get("objectName"))
    if parent.type != "MESH":
        raise InvalidInputError(f"Object {parent.name!r} is type {parent.type}, expected MESH")

    idx = _next_collision_index(parent, "UCX")
    name = ue5_collision_name(parent.name, "UCX", idx)

    with composite_undo(f"collision_add_convex_hull:{parent.name}"):
        # Duplicate parent mesh data so the hull is independent
        new_mesh = parent.data.copy()
        col_obj = bpy.data.objects.new(name=name, object_data=new_mesh)
        col_obj.matrix_world = parent.matrix_world.copy()
        col_obj.display_type = "WIRE"
        col_obj.parent = parent
        bpy.context.scene.collection.objects.link(col_obj)

        # Compute convex hull via bmesh
        set_active_and_selected(col_obj)
        with with_mode(col_obj, "EDIT"):
            bm = bmesh.from_edit_mesh(col_obj.data)
            bmesh.ops.convex_hull(bm, input=bm.verts)
            bmesh.update_edit_mesh(col_obj.data)

    return {
        "ok": True,
        "data": {"collisionObjectName": col_obj.name, "parentName": parent.name},
        "refs": {"objectName": col_obj.name, "collisionObjectName": col_obj.name},
    }
