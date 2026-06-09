"""Material handlers — Sprint 1 subset (B1 + B5 §1–3, §17).

Full B5 (shader nodes, node groups, composites) is in handlers/shader_node.py
and handlers/node_group.py.
"""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    coerce_value,
    composite_undo,
    get_material,
    get_object,
)
from ..server import handler


def _principled_node(mat: Any) -> Any:
    if not mat.use_nodes or mat.node_tree is None:
        raise InvalidInputError(f"material {mat.name!r} has no node tree")
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            return n
    raise InvalidInputError(f"material {mat.name!r} has no Principled BSDF node")


def _set_socket(node: Any, names: list[str], value: Any) -> bool:
    """Set the first input socket that matches any of `names` (version-tolerant)."""
    for nm in names:
        sock = node.inputs.get(nm)
        if sock is not None:
            try:
                sock.default_value = coerce_value(value)
                return True
            except (TypeError, ValueError):
                return False
    return False


@handler("POST", "/material/set_principled")
def material_set_principled(body: dict[str, Any]) -> dict[str, Any]:
    """Set common Principled BSDF inputs in one call (S6-09).

    Body: {materialName, baseColor?: [r,g,b,a], roughness?, metallic?,
           emissionColor?: [r,g,b,a], emissionStrength?, alpha?, ior?,
           specular?}  — only provided keys are applied. Socket names are
    resolved version-tolerantly (4.x/5.x).
    """
    mat = get_material(body.get("materialName"))
    node = _principled_node(mat)
    applied: list[str] = []
    spec = [
        ("baseColor", ["Base Color"]),
        ("roughness", ["Roughness"]),
        ("metallic", ["Metallic"]),
        ("emissionColor", ["Emission Color", "Emission"]),
        ("emissionStrength", ["Emission Strength"]),
        ("alpha", ["Alpha"]),
        ("ior", ["IOR"]),
        ("specular", ["Specular IOR Level", "Specular"]),
    ]
    with composite_undo(f"material_set_principled:{mat.name}"):
        for key, sockets in spec:
            if key in body and body[key] is not None:
                if _set_socket(node, sockets, body[key]):
                    applied.append(key)
    return {
        "ok": True,
        "data": {"materialName": mat.name, "applied": applied},
        "refs": {"materialName": mat.name},
    }


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


@handler("POST", "/material/create_pbr_from_textures")
def material_create_pbr_from_textures(body: dict[str, Any]) -> dict[str, Any]:
    """Create a Principled BSDF material wired to up to 4 PBR texture maps.

    Body: {
      name: str,
      baseColor?: str (filepath to color texture, sRGB),
      normal?: str (filepath, Non-Color, plugged through ShaderNodeNormalMap),
      metallic?: str (filepath, Non-Color),
      roughness?: str (filepath, Non-Color),
      normalSpace?: 'OpenGL' | 'DirectX' (default 'OpenGL'),
      uvMap?: str (uv map name, default active),
      replaceExisting?: bool (default true — wipes existing node tree)
    }

    Each provided texture is loaded as a packed image (or linked, see packImages)
    into an Image Texture node. Color spaces are set correctly (sRGB for
    baseColor, Non-Color for the rest). For DirectX normal maps the green
    channel is inverted via a Separate/Combine Color pair. The output is wired
    to a single Material Output node.

    Returns the list of (slot, nodeName, image, colorspace) for traceability.
    """
    import bpy  # type: ignore

    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")

    base_color = body.get("baseColor")
    normal = body.get("normal")
    metallic = body.get("metallic")
    roughness = body.get("roughness")
    normal_space = body.get("normalSpace", "OpenGL")
    uv_map = body.get("uvMap")
    replace = bool(body.get("replaceExisting", True))

    if normal_space not in ("OpenGL", "DirectX"):
        raise InvalidInputError("normalSpace must be 'OpenGL' or 'DirectX'")

    # Validate every provided file exists up-front
    import os
    for label, path in (("baseColor", base_color), ("normal", normal),
                        ("metallic", metallic), ("roughness", roughness)):
        if path and not os.path.isfile(path):
            raise InvalidInputError(f"{label} texture not found: {path}")

    created: list[dict[str, Any]] = []

    with composite_undo(f"material_create_pbr_from_textures:{name}"):
        if name in bpy.data.materials:
            mat = bpy.data.materials[name]
        else:
            mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True

        tree = mat.node_tree
        if replace:
            for n in list(tree.nodes):
                tree.nodes.remove(n)

        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        out = tree.nodes.new("ShaderNodeOutputMaterial")
        out.location = (400, 0)
        tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

        def _add_image(path: str, slot: str, y: int, colorspace: str) -> Any:
            img = bpy.data.images.load(path, check_existing=True)
            try:
                img.colorspace_settings.name = colorspace
            except Exception:  # noqa: BLE001
                pass
            tex = tree.nodes.new("ShaderNodeTexImage")
            tex.image = img
            tex.location = (-600, y)
            tex.name = f"Tex_{slot}"
            if uv_map:
                uv = tree.nodes.new("ShaderNodeUVMap")
                uv.uv_map = uv_map
                uv.location = (-900, y)
                tree.links.new(uv.outputs["UV"], tex.inputs["Vector"])
            created.append({
                "slot": slot, "nodeName": tex.name,
                "image": img.name, "filepath": path, "colorspace": colorspace,
            })
            return tex

        if base_color:
            tex = _add_image(base_color, "baseColor", 300, "sRGB")
            tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

        if metallic:
            tex = _add_image(metallic, "metallic", 0, "Non-Color")
            tree.links.new(tex.outputs["Color"], bsdf.inputs["Metallic"])

        if roughness:
            tex = _add_image(roughness, "roughness", -300, "Non-Color")
            tree.links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])

        if normal:
            tex = _add_image(normal, "normal", -600, "Non-Color")
            nmap = tree.nodes.new("ShaderNodeNormalMap")
            nmap.location = (-200, -600)
            if normal_space == "DirectX":
                # Invert green channel: Separate Color → Invert G → Combine Color
                sep = tree.nodes.new("ShaderNodeSeparateColor")
                sep.location = (-450, -600)
                inv = tree.nodes.new("ShaderNodeInvert")
                inv.location = (-350, -680)
                comb = tree.nodes.new("ShaderNodeCombineColor")
                comb.location = (-280, -600)
                tree.links.new(tex.outputs["Color"], sep.inputs["Color"])
                tree.links.new(sep.outputs["Red"], comb.inputs["Red"])
                tree.links.new(sep.outputs["Green"], inv.inputs["Color"])
                tree.links.new(inv.outputs["Color"], comb.inputs["Green"])
                tree.links.new(sep.outputs["Blue"], comb.inputs["Blue"])
                tree.links.new(comb.outputs["Color"], nmap.inputs["Color"])
            else:
                tree.links.new(tex.outputs["Color"], nmap.inputs["Color"])
            tree.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return {
        "ok": True,
        "data": {
            "materialName": mat.name,
            "normalSpace": normal_space,
            "textures": created,
            "textureCount": len(created),
        },
        "refs": {"materialName": mat.name, "nodeTreeName": mat.node_tree.name},
    }

