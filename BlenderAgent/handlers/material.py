"""Material handlers — Sprint 1 subset (B1 + B5 §1–3, §17).

Full B5 (shader nodes, node groups, composites) is in handlers/shader_node.py
and handlers/node_group.py.
"""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_material,
    get_object,
)
from ..server import handler


@handler("POST", "/material/create")
def material_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a Material with use_nodes=True."""
    import bpy  # type: ignore
    name = body.get("name", "Material")
    use_nodes = bool(body.get("useNodes", True))
    with composite_undo(f"material_create:{name}"):
        if name in bpy.data.materials:
            mat = bpy.data.materials[name]
            return {
                "ok": True,
                "data": {"materialName": mat.name, "created": False},
                "refs": {"materialName": mat.name},
            }
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = use_nodes
    return {
        "ok": True,
        "data": {"materialName": mat.name, "created": True},
        "refs": {"materialName": mat.name},
    }


@handler("POST", "/material/delete")
def material_delete(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    mat = get_material(body.get("materialName") or body.get("name"))
    name = mat.name
    with composite_undo(f"material_delete:{name}"):
        bpy.data.materials.remove(mat)
    return {"ok": True, "data": {"deleted": name}}


@handler("POST", "/material/assign_to_object")
def material_assign_to_object(body: dict[str, Any]) -> dict[str, Any]:
    """Assign material to an object's slot."""
    obj = get_object(body.get("objectName"))
    mat = get_material(body.get("materialName"))
    slot_index = body.get("slotIndex")

    with composite_undo(f"material_assign_to_object:{obj.name}/{mat.name}"):
        if slot_index is None:
            if not obj.data.materials:
                obj.data.materials.append(mat)
                idx = 0
            else:
                obj.data.materials[0] = mat
                idx = 0
        else:
            idx = int(slot_index)
            while len(obj.data.materials) <= idx:
                obj.data.materials.append(None)
            obj.data.materials[idx] = mat

    return {
        "ok": True,
        "data": {"objectName": obj.name, "materialName": mat.name, "slotIndex": idx},
        "refs": {"objectName": obj.name, "materialName": mat.name},
    }


@handler("POST", "/material/assign_slot")
def material_assign_slot(body: dict[str, Any]) -> dict[str, Any]:
    """Alias of material_assign_to_object kept for legacy callers (B1 docs)."""
    return material_assign_to_object(body)


@handler("POST", "/material/slot_add")
def material_slot_add(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    if obj.type != "MESH":
        raise InvalidInputError(f"Object {obj.name!r} type is {obj.type}, expected MESH")
    with composite_undo(f"material_slot_add:{obj.name}"):
        obj.data.materials.append(None)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "slotIndex": len(obj.data.materials) - 1},
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/material/create_procedural_grid")
def material_create_procedural_grid(body: dict[str, Any]) -> dict[str, Any]:
    """Create a Checker/Grid procedural material for blockout visualization."""
    import bpy  # type: ignore

    name = body.get("name", "Grid_BlockOut")
    square_size = float(body.get("squareSize", 0.5))

    with composite_undo(f"material_create_procedural_grid:{name}"):
        if name in bpy.data.materials:
            mat = bpy.data.materials[name]
        else:
            mat = bpy.data.materials.new(name=name)
            mat.use_nodes = True
        tree = mat.node_tree
        # Clear existing nodes
        for n in list(tree.nodes):
            tree.nodes.remove(n)

        coord = tree.nodes.new("ShaderNodeTexCoord")
        coord.location = (-600, 0)

        mapping = tree.nodes.new("ShaderNodeMapping")
        mapping.location = (-400, 0)
        mapping.inputs["Scale"].default_value = (1.0 / square_size, 1.0 / square_size, 1.0 / square_size)

        checker = tree.nodes.new("ShaderNodeTexChecker")
        checker.location = (-200, 0)
        checker.inputs["Color1"].default_value = (0.85, 0.85, 0.85, 1.0)
        checker.inputs["Color2"].default_value = (0.15, 0.15, 0.15, 1.0)
        checker.inputs["Scale"].default_value = 1.0

        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (100, 0)

        out = tree.nodes.new("ShaderNodeOutputMaterial")
        out.location = (400, 0)

        tree.links.new(coord.outputs["UV"], mapping.inputs["Vector"])
        tree.links.new(mapping.outputs["Vector"], checker.inputs["Vector"])
        tree.links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
        tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    return {
        "ok": True,
        "data": {"materialName": mat.name, "squareSize": square_size},
        "refs": {"materialName": mat.name, "nodeTreeName": mat.node_tree.name},
    }
