"""Object primitive handlers (B1, B7 mesh→armature parenting)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_armature_object,
    get_collection,
    get_object,
    set_active_and_selected,
    with_3dview_context,
)
from ..server import handler


_PRIMITIVE_OPS = {
    "CUBE": ("mesh", "primitive_cube_add", {"size": "size"}),
    "PLANE": ("mesh", "primitive_plane_add", {"size": "size"}),
    "SPHERE": ("mesh", "primitive_uv_sphere_add", {"radius": "size"}),
    "CYLINDER": ("mesh", "primitive_cylinder_add", {"radius": "size"}),
    "CONE": ("mesh", "primitive_cone_add", {"radius1": "size"}),
    "TORUS": ("mesh", "primitive_torus_add", {}),
    "ICOSPHERE": ("mesh", "primitive_ico_sphere_add", {"radius": "size"}),
    "EMPTY": ("object", "empty_add", {}),
}


def _call_primitive(namespace: str, op_name: str, **kwargs: Any) -> None:
    import bpy  # type: ignore
    ns = getattr(bpy.ops, namespace)
    op = getattr(ns, op_name)
    op(**kwargs)


@handler("POST", "/object/create")
def object_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a primitive object.

    Body: {type: 'CUBE'|'PLANE'|'SPHERE'|'CYLINDER'|'CONE'|'TORUS'|'ICOSPHERE'|'EMPTY',
           name?: str, size?: float, location?: [x,y,z],
           rotation?: [x,y,z] (radians), scale?: [x,y,z],
           collectionName?: str}
    """
    import bpy  # type: ignore

    prim_type = (body.get("type") or "CUBE").upper()
    if prim_type not in _PRIMITIVE_OPS:
        raise InvalidInputError(f"Unsupported type {prim_type!r}; allowed: {sorted(_PRIMITIVE_OPS)}")

    namespace, op_name, _param_map = _PRIMITIVE_OPS[prim_type]
    size = float(body.get("size", 2.0))
    location = tuple(body.get("location", (0.0, 0.0, 0.0)))
    rotation = tuple(body.get("rotation", (0.0, 0.0, 0.0)))
    scale = tuple(body.get("scale", (1.0, 1.0, 1.0)))
    name = body.get("name")
    collection_name = body.get("collectionName")

    kwargs: dict[str, Any] = {"location": location, "rotation": rotation, "scale": scale}
    if prim_type == "EMPTY":
        # bpy.ops.object.empty_add takes location/rotation but not scale; pass type for display.
        kwargs = {"location": location, "rotation": rotation, "type": body.get("emptyType", "PLAIN_AXES")}
    elif prim_type in {"CUBE", "PLANE", "SPHERE", "CYLINDER", "CONE", "ICOSPHERE"}:
        kwargs["size" if prim_type in {"CUBE", "PLANE"} else "radius"] = size if prim_type in {"CUBE", "PLANE"} else size / 2

    with composite_undo(f"object_create:{prim_type}"):
        with with_3dview_context():
            _call_primitive(namespace, op_name, **kwargs)
        obj = bpy.context.active_object
        if obj is None:
            raise InvalidInputError(f"Failed to create primitive {prim_type}")
        if name:
            obj.name = name
        if collection_name:
            target = get_collection(collection_name)
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            target.objects.link(obj)

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "type": obj.type,
            "location": list(obj.location),
        },
        "refs": {"objectName": obj.name},
        "nextSteps": [
            "Call /object/set_transform to position the object.",
            "Call /material/assign_slot to add a material.",
        ],
    }


@handler("POST", "/object/add_blockout")
def object_add_blockout(body: dict[str, Any]) -> dict[str, Any]:
    """Add a cube sized to a target footprint for level blockout.

    Body: {name: str, footprint: [w, d, h] (BU), collectionName?: str, location?: [x,y,z]}
    """
    import bpy  # type: ignore

    name = body.get("name", "Blockout")
    footprint = body.get("footprint")
    if not isinstance(footprint, list) or len(footprint) != 3:
        raise InvalidInputError("footprint must be [w, d, h]")
    location = tuple(body.get("location", (0.0, 0.0, 0.0)))
    collection_name = body.get("collectionName")

    with composite_undo(f"object_add_blockout:{name}"):
        with with_3dview_context():
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (footprint[0], footprint[1], footprint[2])
        # Apply scale so dimensions = footprint
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        if collection_name:
            target = get_collection(collection_name)
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            target.objects.link(obj)

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "dimensions": list(obj.dimensions),
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/object/set_transform")
def object_set_transform(body: dict[str, Any]) -> dict[str, Any]:
    """Set object location/rotation/scale."""
    obj = get_object(body.get("objectName"))
    with composite_undo(f"object_set_transform:{obj.name}"):
        if "location" in body:
            obj.location = tuple(body["location"])
        if "rotation" in body:
            obj.rotation_euler = tuple(body["rotation"])
        if "scale" in body:
            obj.scale = tuple(body["scale"])
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/object/duplicate_linked")
def object_duplicate_linked(body: dict[str, Any]) -> dict[str, Any]:
    """Duplicate an object with linked (shared) data."""
    import bpy  # type: ignore
    src = get_object(body.get("objectName"))
    new_name = body.get("newName")
    with composite_undo(f"object_duplicate_linked:{src.name}"):
        set_active_and_selected(src)
        with with_3dview_context():
            bpy.ops.object.duplicate(linked=True)
        new_obj = bpy.context.active_object
        if new_name:
            new_obj.name = new_name
    return {
        "ok": True,
        "data": {"sourceName": src.name, "objectName": new_obj.name},
        "refs": {"objectName": new_obj.name},
    }


@handler("POST", "/mesh/set_origin_to_snap_corner")
def mesh_set_origin_to_snap_corner(body: dict[str, Any]) -> dict[str, Any]:
    """Move the object origin to a named corner of its bounding box.

    Body: {objectName: str, corner: 'MIN_X_MIN_Y_MIN_Z' | ... 8 variants}
    """
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    obj = get_object(body.get("objectName"))
    corner = body.get("corner", "MIN_X_MIN_Y_MIN_Z").upper()

    parts = corner.split("_")
    if len(parts) != 6:
        raise InvalidInputError(
            f"corner must be e.g. 'MIN_X_MIN_Y_MIN_Z' (got {corner!r})"
        )
    # parts = ['MIN', 'X', 'MIN', 'Y', 'MIN', 'Z']
    sides = (parts[0], parts[2], parts[4])
    axes = (parts[1], parts[3], parts[5])
    if axes != ("X", "Y", "Z"):
        raise InvalidInputError("axes must be X, Y, Z in order")

    bbox = [Vector(corner) for corner in obj.bound_box]
    target = Vector((0.0, 0.0, 0.0))
    for i, side in enumerate(sides):
        values = [c[i] for c in bbox]
        target[i] = min(values) if side == "MIN" else max(values)

    target_world = obj.matrix_world @ target

    with composite_undo(f"mesh_set_origin_to_snap_corner:{obj.name}"):
        cursor_prev = bpy.context.scene.cursor.location.copy()
        try:
            bpy.context.scene.cursor.location = target_world
            set_active_and_selected(obj)
            with with_3dview_context():
                bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        finally:
            bpy.context.scene.cursor.location = cursor_prev

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "newOriginWorld": list(target_world),
            "corner": corner,
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/collection/instance_create")
def collection_instance_create(body: dict[str, Any]) -> dict[str, Any]:
    """Instantiate a collection as a single Empty (collection instance)."""
    import bpy  # type: ignore
    col = get_collection(body.get("collectionName"))
    location = tuple(body.get("location", (0.0, 0.0, 0.0)))
    name = body.get("name") or f"Inst_{col.name}"

    with composite_undo(f"collection_instance_create:{col.name}"):
        empty = bpy.data.objects.new(name=name, object_data=None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = col
        empty.location = location
        bpy.context.scene.collection.objects.link(empty)

    return {
        "ok": True,
        "data": {"objectName": empty.name, "instanceOf": col.name},
        "refs": {"objectName": empty.name, "collectionName": col.name},
    }


@handler("POST", "/mesh/parent_to_armature")
def mesh_parent_to_armature(body: dict[str, Any]) -> dict[str, Any]:
    """Parent a mesh to an armature object with an Armature modifier."""
    import bpy  # type: ignore
    mesh_obj = get_object(body.get("meshObjectName") or body.get("meshName"))
    arm_obj = get_armature_object(body.get("armatureObjectName") or body.get("armatureName"))

    with composite_undo(f"mesh_parent_to_armature:{mesh_obj.name}"):
        mesh_obj.parent = arm_obj
        mesh_obj.parent_type = "OBJECT"
        # Ensure Armature modifier exists
        mod = next((m for m in mesh_obj.modifiers if m.type == "ARMATURE"), None)
        if mod is None:
            mod = mesh_obj.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = arm_obj
        mod.use_vertex_groups = True

    return {
        "ok": True,
        "data": {
            "meshObjectName": mesh_obj.name,
            "armatureObjectName": arm_obj.name,
            "modifierName": mod.name,
        },
        "refs": {
            "objectName": mesh_obj.name,
            "armatureName": arm_obj.name,
            "modifierName": mod.name,
        },
    }
