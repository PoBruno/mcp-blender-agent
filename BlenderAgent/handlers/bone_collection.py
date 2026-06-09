"""Bone collection handlers (B7 — Blender 4.2 deform/control separation)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    BoneNotFoundError,
    InvalidInputError,
    composite_undo,
    get_armature_object,
)
from ..server import handler


@handler("POST", "/bone_collection/create")
def bone_collection_create(body: dict[str, Any]) -> dict[str, Any]:
    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    with composite_undo(f"bone_collection_create:{arm.name}/{name}"):
        existing = arm.data.collections.get(name)
        if existing is not None:
            return {
                "ok": True,
                "data": {"armatureObjectName": arm.name, "boneCollectionName": existing.name,
                         "created": False},
                "refs": {"armatureName": arm.name, "boneCollectionName": existing.name},
            }
        bc = arm.data.collections.new(name=name)
    return {
        "ok": True,
        "data": {"armatureObjectName": arm.name, "boneCollectionName": bc.name, "created": True},
        "refs": {"armatureName": arm.name, "boneCollectionName": bc.name},
    }


@handler("POST", "/bone_collection/assign_bone")
def bone_collection_assign_bone(body: dict[str, Any]) -> dict[str, Any]:
    arm = get_armature_object(body.get("armatureObjectName"))
    collection_name = body.get("boneCollectionName")
    bone_name = body.get("boneName")
    if not collection_name or not bone_name:
        raise InvalidInputError("boneCollectionName and boneName are required")
    bc = arm.data.collections.get(collection_name)
    if bc is None:
        raise InvalidInputError(f"bone collection {collection_name!r} not found")
    with composite_undo(f"bone_collection_assign_bone:{arm.name}/{collection_name}/{bone_name}"):
        bone = arm.data.bones.get(bone_name)
        if bone is None:
            raise BoneNotFoundError(f"bone {bone_name!r} not found")
        bc.assign(bone)
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "boneCollectionName": collection_name,
            "boneName": bone_name,
        },
        "refs": {"armatureName": arm.name, "boneCollectionName": collection_name,
                 "boneName": bone_name},
    }
