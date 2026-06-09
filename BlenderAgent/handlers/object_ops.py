"""Object primitive handlers (B1, B7 mesh→armature parenting)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    ObjectNotFoundError,
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
    elif prim_type in {"CUBE", "PLANE"}:
        kwargs["size"] = size
    elif prim_type == "CONE":
        # primitive_cone_add takes radius1 (base) and radius2 (top); not "radius".
        kwargs["radius1"] = size / 2
    elif prim_type == "TORUS":
        # primitive_torus_add uses major_radius / minor_radius; map size -> major.
        kwargs["major_radius"] = size / 2
        kwargs["minor_radius"] = max(size / 8, 0.01)
    else:
        # SPHERE, CYLINDER, ICOSPHERE all accept "radius".
        kwargs["radius"] = size / 2

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


@handler("POST", "/object/delete")
def object_delete(body: dict[str, Any]) -> dict[str, Any]:
    """Remove one or more objects from the .blend (data + scene unlink).

    Body: {objectNames: [str, ...]} or {objectName: str}

    Children are recursively detached but NOT deleted unless explicitly listed
    (caller decides). Missing names are silently skipped — pass strict=true to
    raise ObjectNotFoundError on the first missing one. Idempotent.
    """
    import bpy  # type: ignore

    names = body.get("objectNames")
    if names is None and "objectName" in body:
        names = [body["objectName"]]
    if not names:
        raise InvalidInputError("objectNames or objectName required")
    if isinstance(names, str):
        names = [names]
    strict = bool(body.get("strict", False))

    deleted: list[str] = []
    skipped: list[str] = []
    with composite_undo(f"object_delete:{len(names)}"):
        for n in names:
            obj = bpy.data.objects.get(n)
            if obj is None:
                if strict:
                    raise ObjectNotFoundError(f"object {n!r} not found")
                skipped.append(n)
                continue
            bpy.data.objects.remove(obj, do_unlink=True)
            deleted.append(n)

    return {
        "ok": True,
        "data": {
            "deletedCount": len(deleted),
            "deleted": deleted,
            "skippedCount": len(skipped),
            "skipped": skipped,
        },
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


@handler("POST", "/object/apply_transform")
def object_apply_transform(body: dict[str, Any]) -> dict[str, Any]:
    """Bake object location/rotation/scale into the mesh data (S6-06).

    Body: {objectName, location?: bool, rotation?: bool, scale?: bool (default scale only)}
    Non-uniform object scale distorts width-based ops (Bevel/Solidify); apply
    scale before those. Resets the applied channels to identity.
    """
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    do_loc = bool(body.get("location", False))
    do_rot = bool(body.get("rotation", False))
    do_scale = bool(body.get("scale", True))
    with composite_undo(f"object_apply_transform:{obj.name}"):
        set_active_and_selected(obj)
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        with with_3dview_context():
            bpy.ops.object.transform_apply(location=do_loc, rotation=do_rot, scale=do_scale)
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "applied": {"location": do_loc, "rotation": do_rot, "scale": do_scale},
            "scale": list(obj.scale),
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/object/set_mode")
def object_set_mode(body: dict[str, Any]) -> dict[str, Any]:
    """Switch an object into a mode (S6-07).

    Body: {objectName, mode: OBJECT|EDIT|POSE|SCULPT|VERTEX_PAINT|WEIGHT_PAINT|TEXTURE_PAINT}
    Use to recover from a stuck Sculpt/Edit mode that breaks operators.
    """
    import bpy  # type: ignore
    obj = get_object(body.get("objectName"))
    mode = body.get("mode")
    if not mode:
        raise InvalidInputError("mode is required")
    with composite_undo(f"object_set_mode:{obj.name}/{mode}"):
        set_active_and_selected(obj)
        try:
            bpy.ops.object.mode_set(mode=str(mode))
        except (RuntimeError, TypeError) as exc:
            raise InvalidInputError(f"cannot set mode {mode!r} on {obj.name!r}: {exc}") from exc
    return {
        "ok": True,
        "data": {"objectName": obj.name, "mode": obj.mode},
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/object/rename")
def object_rename(body: dict[str, Any]) -> dict[str, Any]:
    """Rename an object (S6-10). Body: {objectName, newName}."""
    obj = get_object(body.get("objectName"))
    new_name = body.get("newName")
    if not new_name:
        raise InvalidInputError("newName is required")
    with composite_undo(f"object_rename:{obj.name}->{new_name}"):
        obj.name = str(new_name)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "requestedName": new_name},
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


@handler("POST", "/object/list")
def object_list(body: dict[str, Any]) -> dict[str, Any]:
    """List every object in bpy.data.objects with type/location/parent/collection.

    Body: {typeFilter?: str | [str, ...] (e.g. "ARMATURE" or ["MESH","ARMATURE"]),
           namePattern?: str (substring filter, case-sensitive),
           collectionName?: str (only objects in this collection)}

    Pure read; never mutates. Use to discover armatures, meshes, lights, sockets
    in a loaded .blend before chaining other tools.
    """
    import bpy  # type: ignore

    type_filter = body.get("typeFilter")
    if isinstance(type_filter, str):
        type_filter = [type_filter]
    if type_filter:
        type_filter = {t.upper() for t in type_filter}

    name_pat = body.get("namePattern")
    coll_name = body.get("collectionName")
    coll_obj_names: set[str] | None = None
    if coll_name:
        if coll_name not in bpy.data.collections:
            raise InvalidInputError(f"collection {coll_name!r} not found")
        coll_obj_names = {o.name for o in bpy.data.collections[coll_name].objects}

    items: list[dict[str, Any]] = []
    for o in bpy.data.objects:
        if type_filter and o.type not in type_filter:
            continue
        if name_pat and name_pat not in o.name:
            continue
        if coll_obj_names is not None and o.name not in coll_obj_names:
            continue
        items.append(
            {
                "name": o.name,
                "type": o.type,
                "location": list(o.location),
                "rotationEuler": list(o.rotation_euler),
                "scale": list(o.scale),
                "parent": o.parent.name if o.parent else None,
                "childrenCount": len(o.children),
                "modifierCount": len(o.modifiers) if hasattr(o, "modifiers") else 0,
                "collections": [c.name for c in o.users_collection],
                "hide": bool(o.hide_get()),
            }
        )

    return {
        "ok": True,
        "data": {"count": len(items), "objects": items},
    }


@handler("POST", "/object/get_info")
def object_get_info(body: dict[str, Any]) -> dict[str, Any]:
    """Deep introspection of a single object — children, modifiers, animation,
    data block summary.

    Body: {objectName: str}

    Returns parent/children/modifiers, plus type-specific summary:
      - MESH: vertex/edge/face count, vertex_group names, material slots
      - ARMATURE: bone count, action name, sockets (SOCKET_ prefixed children)
      - EMPTY: empty_display_type, size
    """
    obj = get_object(body.get("objectName"))

    info: dict[str, Any] = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotationEuler": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "parent": obj.parent.name if obj.parent else None,
        "parentType": obj.parent_type if obj.parent else None,
        "parentBone": obj.parent_bone if obj.parent else "",
        "children": [c.name for c in obj.children],
        "collections": [c.name for c in obj.users_collection],
        "modifiers": [
            {"name": m.name, "type": m.type} for m in (obj.modifiers or [])
        ] if hasattr(obj, "modifiers") else [],
        "animation": {
            "hasAnimData": obj.animation_data is not None,
            "actionName": obj.animation_data.action.name
            if obj.animation_data and obj.animation_data.action else None,
            "nlaTrackCount": len(obj.animation_data.nla_tracks)
            if obj.animation_data else 0,
        },
    }

    if obj.type == "MESH":
        me = obj.data
        info["mesh"] = {
            "vertices": len(me.vertices),
            "edges": len(me.edges),
            "polygons": len(me.polygons),
            "uvLayers": [u.name for u in me.uv_layers],
            "vertexGroups": [vg.name for vg in obj.vertex_groups],
            "materialSlots": [
                {"slot": i, "materialName": s.material.name if s.material else None}
                for i, s in enumerate(obj.material_slots)
            ],
            "shapeKeys": [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
        }
    elif obj.type == "ARMATURE":
        arm = obj.data
        sockets = [c.name for c in obj.children if c.name.startswith("SOCKET_")]
        info["armature"] = {
            "boneCount": len(arm.bones),
            "boneNames": [b.name for b in arm.bones],
            "sockets": sockets,
            "showInFront": bool(obj.show_in_front),
        }
    elif obj.type == "EMPTY":
        info["empty"] = {
            "displayType": obj.empty_display_type,
            "displaySize": float(obj.empty_display_size),
        }

    return {"ok": True, "data": info, "refs": {"objectName": obj.name}}

