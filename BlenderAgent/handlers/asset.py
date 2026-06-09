"""Asset browser handlers (B9)."""

from __future__ import annotations

from typing import Any

from ..helpers import InvalidInputError, composite_undo, get_object
from ..server import handler


@handler("POST", "/asset/mark")
def asset_mark(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    with composite_undo(f"asset_mark:{obj.name}"):
        if not obj.asset_data:
            obj.asset_mark()
        tags = body.get("tags") or []
        for tag in tags:
            if tag not in [t.name for t in obj.asset_data.tags]:
                obj.asset_data.tags.new(name=tag)
        if "catalogId" in body:
            obj.asset_data.catalog_id = body["catalogId"]
        if "description" in body:
            obj.asset_data.description = body["description"]
    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "tags": [t.name for t in obj.asset_data.tags] if obj.asset_data else [],
        },
        "refs": {"objectName": obj.name},
    }


@handler("POST", "/asset/clear")
def asset_clear(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    if not obj.asset_data:
        raise InvalidInputError(f"{obj.name!r} is not marked as an asset")
    with composite_undo(f"asset_clear:{obj.name}"):
        obj.asset_clear()
    return {"ok": True, "data": {"objectName": obj.name, "cleared": True}}
