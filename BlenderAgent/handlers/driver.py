"""Driver handlers (B7 §22, B6 §16) — VERIFY in 4.2 (see BPY-FEASIBILITY)."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    BlenderAgentError,
    InvalidInputError,
    composite_undo,
    get_object,
)
from ..server import handler


@handler("POST", "/driver/add")
def driver_add(body: dict[str, Any]) -> dict[str, Any]:
    """Add a driver to a data path on an object.

    Body: {objectName: str, dataPath: str, arrayIndex?: int,
           expression?: str, variables?: list[{name, type, target_id_type,
           target_object_name, data_path}]}
    """
    obj = get_object(body.get("objectName"))
    data_path = body.get("dataPath")
    if not data_path:
        raise InvalidInputError("dataPath is required")
    array_index = body.get("arrayIndex", -1)
    expression = body.get("expression", "var")
    variables = body.get("variables") or []

    with composite_undo(f"driver_add:{obj.name}/{data_path}"):
        try:
            fcurve = obj.driver_add(data_path, array_index)
        except (TypeError, RuntimeError) as exc:
            raise InvalidInputError(f"driver_add({data_path!r}) failed: {exc}") from exc
        drv = fcurve.driver
        drv.type = "SCRIPTED"
        drv.expression = expression
        for v in variables:
            var = drv.variables.new()
            var.name = v["name"]
            var.type = v.get("type", "TRANSFORMS")
            tgt = var.targets[0]
            if "targetObjectName" in v:
                tgt.id = get_object(v["targetObjectName"])
            if "dataPath" in v:
                tgt.data_path = v["dataPath"]
            if "transformType" in v:
                tgt.transform_type = v["transformType"]
            if "transformSpace" in v:
                tgt.transform_space = v["transformSpace"]

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "dataPath": data_path,
            "expression": expression,
            "variableCount": len(variables),
        },
        "refs": {"objectName": obj.name, "driverDataPath": data_path},
    }


@handler("POST", "/driver/remove")
def driver_remove(body: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(body.get("objectName"))
    data_path = body.get("dataPath")
    array_index = body.get("arrayIndex", -1)
    if not data_path:
        raise InvalidInputError("dataPath is required")
    with composite_undo(f"driver_remove:{obj.name}/{data_path}"):
        ok = obj.driver_remove(data_path, array_index)
    if not ok:
        raise BlenderAgentError(
            f"No driver to remove at {obj.name!r}/{data_path}",
            error_code="DRIVER_NOT_FOUND",
        )
    return {"ok": True, "data": {"objectName": obj.name, "dataPath": data_path}}
