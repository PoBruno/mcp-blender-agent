"""Vertex group handlers (B7, B3)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    VertexGroupNotFoundError,
    composite_undo,
    get_object,
)
from ..server import handler


@handler("POST", "/vertex_group/create")
def vertex_group_create(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    if obj.type != "MESH":
        raise InvalidInputError(f"Object {obj.name!r} type is {obj.type}, expected MESH")
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    with composite_undo(f"vertex_group_create:{obj.name}/{name}"):
        if name in obj.vertex_groups:
            vg = obj.vertex_groups[name]
            return {
                "ok": True,
                "data": {"objectName": obj.name, "vertexGroupName": vg.name, "created": False},
                "refs": {"objectName": obj.name, "vertexGroupName": vg.name},
            }
        vg = obj.vertex_groups.new(name=name)
    return {
        "ok": True,
        "data": {"objectName": obj.name, "vertexGroupName": vg.name, "created": True},
        "refs": {"objectName": obj.name, "vertexGroupName": vg.name},
    }


@handler("POST", "/vertex_group/assign_vertices")
def vertex_group_assign_vertices(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    name = body.get("vertexGroupName")
    if not name:
        raise InvalidInputError("vertexGroupName is required")
    indices = body.get("vertexIndices", [])
    weight = float(body.get("weight", 1.0))
    if not isinstance(indices, list) or not indices:
        raise InvalidInputError("vertexIndices must be a non-empty list")
    vg = obj.vertex_groups.get(name)
    if vg is None:
        raise VertexGroupNotFoundError(f"{obj.name!r} has no vertex group {name!r}")
    with composite_undo(f"vertex_group_assign_vertices:{obj.name}/{name}"):
        vg.add(indices, weight, "REPLACE")
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "vertexGroupName": name,
            "assignedCount": len(indices),
            "weight": weight,
        },
        "refs": {"objectName": obj.name, "vertexGroupName": name},
    }


@handler("POST", "/vertex_group/delete")
def vertex_group_delete(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    name = body.get("vertexGroupName")
    if not name:
        raise InvalidInputError("vertexGroupName is required")
    vg = obj.vertex_groups.get(name)
    if vg is None:
        raise VertexGroupNotFoundError(f"{obj.name!r} has no vertex group {name!r}")
    with composite_undo(f"vertex_group_delete:{obj.name}/{name}"):
        obj.vertex_groups.remove(vg)
    return {"ok": True, "data": {"objectName": obj.name, "deletedVertexGroup": name}}
