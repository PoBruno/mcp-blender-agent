"""Bake handlers (B4) — Cycles bake to texture."""

from __future__ import annotations

import os
from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_object,
    set_active_and_selected,
    with_3dview_context,
)
from ..server import handler


_BAKE_TYPES = {
    "COMBINED", "AO", "SHADOW", "NORMAL", "UV", "ROUGHNESS",
    "EMIT", "ENVIRONMENT", "DIFFUSE", "GLOSSY", "TRANSMISSION", "POSITION",
}


@handler("POST", "/bake/setup_target_image")
def bake_setup_target_image(body: dict[str, Any]) -> dict[str, Any]:
    """Create an Image datablock and an Image Texture node selected on the
    material, ready for bake to land on it.
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    image_name = body.get("imageName", f"Bake_{obj.name}")
    width = int(body.get("width", 1024))
    height = int(body.get("height", 1024))
    material_name = body.get("materialName")
    if not material_name:
        raise InvalidInputError("materialName is required")
    if material_name not in {s.material.name for s in obj.material_slots if s.material}:
        raise InvalidInputError(f"{obj.name!r} has no slot with material {material_name!r}")

    with composite_undo(f"bake_setup_target_image:{obj.name}/{image_name}"):
        img = bpy.data.images.get(image_name)
        if img is None:
            img = bpy.data.images.new(name=image_name, width=width, height=height, alpha=False)

        mat = bpy.data.materials[material_name]
        tree = mat.node_tree
        # Add image texture node and select+activate it
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        for n in tree.nodes:
            n.select = False
        tex.select = True
        tree.nodes.active = tex

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "imageName": img.name,
            "materialName": material_name,
            "imageNodeName": tex.name,
        },
        "refs": {
            "objectName": obj.name,
            "imageName": img.name,
            "nodeName": tex.name,
        },
    }


@handler("POST", "/bake/run")
def bake_run(body: dict[str, Any]) -> dict[str, Any]:
    """Run `bpy.ops.object.bake` with full parameter passthrough.

    Body: {objectName: str, type: str (one of _BAKE_TYPES), samples?: int,
           useSelectedToActive?: bool, marginType?: 'EXTEND'|'ADJACENT_FACES',
           margin?: int, useClear?: bool}
    """
    import bpy  # type: ignore

    obj = get_object(body.get("objectName"))
    bake_type = (body.get("type") or "COMBINED").upper()
    if bake_type not in _BAKE_TYPES:
        raise InvalidInputError(f"bake type {bake_type!r} not in {sorted(_BAKE_TYPES)}")
    use_sel_to_active = bool(body.get("useSelectedToActive", False))
    margin = int(body.get("margin", 16))
    margin_type = body.get("marginType", "EXTEND")
    use_clear = bool(body.get("useClear", True))
    samples = body.get("samples")

    scene = bpy.context.scene
    with composite_undo(f"bake_run:{obj.name}/{bake_type}"):
        if scene.render.engine != "CYCLES":
            scene.render.engine = "CYCLES"
        if samples is not None:
            scene.cycles.samples = int(samples)
        set_active_and_selected(obj)
        with with_3dview_context():
            bpy.ops.object.bake(
                type=bake_type,
                use_selected_to_active=use_sel_to_active,
                margin=margin,
                margin_type=margin_type,
                use_clear=use_clear,
            )

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "bakeType": bake_type,
            "samples": scene.cycles.samples,
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/image/save_as")
def image_save_as(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    name = body.get("imageName")
    filepath = body.get("filepath")
    if not name or not filepath:
        raise InvalidInputError("imageName and filepath are required")
    img = bpy.data.images.get(name)
    if img is None:
        raise InvalidInputError(f"image {name!r} not found")
    d = os.path.dirname(filepath)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    img.filepath_raw = filepath
    img.file_format = body.get("fileFormat", "PNG")
    img.save()
    return {
        "ok": True,
        "data": {"imageName": img.name, "filepath": filepath},
        "refs": {"imageName": img.name, "filepath": filepath},
    }
