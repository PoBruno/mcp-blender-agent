"""View layer handlers (B1, B9.D5)."""

from __future__ import annotations

from typing import Any

from ..helpers import InvalidInputError, composite_undo, get_collection, get_scene
from ..server import handler


@handler("POST", "/view_layer/create")
def view_layer_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new view layer on a scene."""
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    scene = get_scene(body.get("sceneName"))
    with composite_undo(f"view_layer_create:{name}"):
        if name in scene.view_layers:
            vl = scene.view_layers[name]
        else:
            vl = scene.view_layers.new(name=name)
    return {
        "ok": True,
        "data": {"viewLayerName": vl.name, "sceneName": scene.name},
        "refs": {"viewLayerName": vl.name, "sceneName": scene.name},
    }


@handler("POST", "/view_layer/create_for_export")
def view_layer_create_for_export(body: dict[str, Any]) -> dict[str, Any]:
    """Create an export-only view layer with only the named collections enabled.

    Body: {name: str, collectionNames: list[str], sceneName?: str}
    """
    name = body.get("name", "Export")
    collection_names = body.get("collectionNames", [])
    if not collection_names:
        raise InvalidInputError("collectionNames must be a non-empty list")
    scene = get_scene(body.get("sceneName"))

    with composite_undo(f"view_layer_create_for_export:{name}"):
        if name in scene.view_layers:
            vl = scene.view_layers[name]
        else:
            vl = scene.view_layers.new(name=name)

        # Resolve target collection names to validate they exist
        for cn in collection_names:
            get_collection(cn)

        # Walk layer-collections in this view layer; exclude everything not in our list
        def walk(lc: Any) -> None:
            lc.exclude = lc.collection.name not in collection_names and lc.collection.name != "Scene Collection"
            for child in lc.children:
                walk(child)

        walk(vl.layer_collection)

    return {
        "ok": True,
        "data": {
            "viewLayerName": vl.name,
            "sceneName": scene.name,
            "enabledCollections": collection_names,
        },
        "refs": {"viewLayerName": vl.name},
    }


@handler("GET", "/view_layer/list")
def view_layer_list(body: dict[str, Any]) -> dict[str, Any]:
    scene = get_scene(body.get("sceneName"))
    return {
        "ok": True,
        "data": {
            "sceneName": scene.name,
            "viewLayers": [vl.name for vl in scene.view_layers],
            "active": scene.view_layers.active.name if scene.view_layers.active else None,
        },
    }
