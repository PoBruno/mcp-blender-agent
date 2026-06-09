"""MetaHuman / ARKit-52 helpers (B7) — Recipe 6 underpinning."""

from __future__ import annotations

from typing import Any

from ..helpers import (
    InvalidInputError,
    composite_undo,
    get_object,
)
from ..server import handler


# ARKit 52 blendshape names — canonical per DECISIONS ADR-009 / 010.
ARKIT_52_BLENDSHAPES = (
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthFunnel", "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthPressLeft", "mouthPressRight", "mouthPucker", "mouthRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight",
    "tongueOut",
)


@handler("POST", "/metahuman/arkit52_list")
def metahuman_arkit52_list(_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {
            "blendshapes": list(ARKIT_52_BLENDSHAPES),
            "count": len(ARKIT_52_BLENDSHAPES),
            "version": "1.0",
        },
    }


@handler("POST", "/metahuman/ensure_arkit52_shape_keys")
def metahuman_ensure_arkit52_shape_keys(body: dict[str, Any]) -> dict[str, Any]:
    """Ensure all 52 ARKit shape keys exist on the head mesh."""
    obj = get_object(body.get("objectName"))
    if obj.type != "MESH":
        raise InvalidInputError(f"Object {obj.name!r} type is {obj.type}, expected MESH")

    created: list[str] = []
    existing: list[str] = []
    with composite_undo(f"metahuman_ensure_arkit52_shape_keys:{obj.name}"):
        if obj.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
        keys = obj.data.shape_keys.key_blocks
        for name in ARKIT_52_BLENDSHAPES:
            if name in keys:
                existing.append(name)
            else:
                obj.shape_key_add(name=name, from_mix=False)
                created.append(name)

    return {
        "ok": True,
        "data": {
            "objectName": obj.name,
            "createdCount": len(created),
            "existingCount": len(existing),
            "createdShapes": created,
        },
        "refs": {"objectName": obj.name},
    }
