"""Collection handlers (B1, B9.D3–D4)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    CollectionNotFoundError,
    InvalidInputError,
    composite_undo,
    get_collection,
    get_object,
    get_scene,
)
from ..server import handler


@handler("POST", "/collection/create")
def collection_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a collection.

    Body: {name: str, parentPath?: str ('Scene Collection' default), sceneName?: str}
    """
    import bpy  # type: ignore

    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")

    parent_name = body.get("parentPath") or body.get("parentName")
    scene = get_scene(body.get("sceneName"))

    if name in bpy.data.collections:
        # Idempotent — return existing
        col = bpy.data.collections[name]
        return {
            "ok": True,
            "data": {"collectionName": col.name, "created": False},
            "refs": {"collectionName": col.name},
        }

    with composite_undo(f"collection_create:{name}"):
        new_col = bpy.data.collections.new(name=name)
        if parent_name and parent_name != "Scene Collection":
            parent = get_collection(parent_name)
            parent.children.link(new_col)
        else:
            scene.collection.children.link(new_col)

    return {
        "ok": True,
        "data": {"collectionName": new_col.name, "created": True},
        "refs": {"collectionName": new_col.name},
    }


@handler("POST", "/collection/move_objects")
def collection_move_objects(body: dict[str, Any]) -> dict[str, Any]:
    """Move objects from their current collection(s) into `collectionName`."""
    target = get_collection(body.get("collectionName") or body.get("targetCollectionName"))
    object_names = body.get("objectNames", [])
    if not isinstance(object_names, list) or not object_names:
        raise InvalidInputError("objectNames must be a non-empty list")

    with composite_undo(f"collection_move_objects:{target.name}"):
        moved: list[str] = []
        for n in object_names:
            obj = get_object(n)
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            target.objects.link(obj)
            moved.append(obj.name)

    return {
        "ok": True,
        "data": {"collectionName": target.name, "movedObjects": moved},
        "refs": {"collectionName": target.name, "objectNames": moved},
    }


@handler("GET", "/collection/list")
def collection_list(_body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    return {
        "ok": True,
        "data": {
            "collections": [
                {"name": c.name, "objectCount": len(c.objects)} for c in bpy.data.collections
            ],
        },
    }


@handler("POST", "/collection/delete")
def collection_delete(body: dict[str, Any]) -> dict[str, Any]:
    import bpy  # type: ignore
    name = body.get("collectionName") or body.get("name")
    if not name:
        raise CollectionNotFoundError("collectionName is required")
    col = get_collection(name)
    with composite_undo(f"collection_delete:{name}"):
        bpy.data.collections.remove(col)
    return {"ok": True, "data": {"deleted": name}}
