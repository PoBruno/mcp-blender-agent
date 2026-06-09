"""Parametric library dispatcher + proportion-matrix introspection.

Endpoints
---------
- /parametric/list                    — registered builders
- /parametric/build                   — invoke builder by name with params
- /parametric/anatomy/human           — resolve human canon to dims
- /parametric/anatomy/furniture       — defaults for known furniture kind
- /parametric/animation/timing        — frame timing for a known cycle
- /parametric/material/recipe         — PBR values for a material archetype
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, Dict

from ..helpers import InvalidInputError, composite_undo
from ..library.anatomy import proportions as _props
from ..server import handler


# ---------------------------------------------------------------------------
# registry — each entry maps tool name → import path of the builder module
# ---------------------------------------------------------------------------

_BUILDERS: Dict[str, str] = {
    "chair_beach":   "BlenderAgent.library.furniture.chair_beach",
    "table_dining":  "BlenderAgent.library.furniture.table_dining",
    "stool_bar":     "BlenderAgent.library.furniture.stool_bar",
    "human_basic":   "BlenderAgent.library.character.human_basic",
}


def _resolve_builder(name: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    path = _BUILDERS.get(name)
    if path is None:
        raise InvalidInputError(
            f"unknown parametric builder {name!r}; valid: {sorted(_BUILDERS)}"
        )
    mod = importlib.import_module(path)
    build_fn = getattr(mod, "build", None)
    if not callable(build_fn):
        raise InvalidInputError(f"builder {name!r} has no `build` function")
    return build_fn


# ---------------------------------------------------------------------------
# /parametric/list
# ---------------------------------------------------------------------------

@handler("POST", "/parametric/list")
def parametric_list(_body: dict[str, Any]) -> dict[str, Any]:
    items = []
    for name in sorted(_BUILDERS):
        mod = importlib.import_module(_BUILDERS[name])
        doc = (getattr(mod, "build", None).__doc__ or "").strip()
        items.append({"name": name, "description": doc.splitlines()[0] if doc else ""})
    return {"ok": True, "data": {"builders": items, "count": len(items)}}


# ---------------------------------------------------------------------------
# /parametric/build
# ---------------------------------------------------------------------------

@handler("POST", "/parametric/build")
def parametric_build(body: dict[str, Any]) -> dict[str, Any]:
    """Body: {name: str, params?: dict}."""
    name = body.get("name")
    if not name:
        raise InvalidInputError("name is required")
    params = body.get("params") or {}
    if not isinstance(params, dict):
        raise InvalidInputError("params must be an object")

    build_fn = _resolve_builder(str(name))

    with composite_undo(f"parametric_build:{name}"):
        result = build_fn(params)

    parts = result.get("parts", {}) if isinstance(result, dict) else {}
    object_names = list(parts.values())
    return {
        "ok": True,
        "data": result,
        "refs": {"objectNames": object_names, "collectionName": result.get("collection")},
        "nextSteps": [
            "render a contact sheet via /vision/contact_sheet to verify silhouette",
            "run /vision/topology_inspect for quality gates",
        ],
    }


# ---------------------------------------------------------------------------
# anatomy / proportions introspection
# ---------------------------------------------------------------------------

@handler("POST", "/parametric/anatomy/human")
def parametric_anatomy_human(body: dict[str, Any]) -> dict[str, Any]:
    """Body: {canon?: str, height?: float, listCanons?: bool}.

    If listCanons is true, return the available canon names.
    Otherwise canon + height are required; returns derived dimensions.
    """
    if body.get("listCanons"):
        return {"ok": True, "data": {"canons": sorted(_props.HUMAN_CANONS.keys())}}
    canon = body.get("canon")
    height = body.get("height")
    if not canon or height is None:
        raise InvalidInputError("canon and height required (or listCanons=true)")
    try:
        dims = _props.resolve_human(str(canon), float(height))
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    return {"ok": True, "data": dims}


@handler("POST", "/parametric/anatomy/furniture")
def parametric_anatomy_furniture(body: dict[str, Any]) -> dict[str, Any]:
    """Body: {kind?: str, list?: bool}."""
    if body.get("list"):
        return {"ok": True, "data": {"kinds": sorted(_props.FURNITURE_DEFAULTS.keys())}}
    kind = body.get("kind")
    if not kind:
        raise InvalidInputError("kind required (or list=true)")
    try:
        return {"ok": True, "data": _props.furniture_defaults(str(kind))}
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc


@handler("POST", "/parametric/animation/timing")
def parametric_animation_timing(body: dict[str, Any]) -> dict[str, Any]:
    """Body: {kind?: str, fps?: float, list?: bool}."""
    if body.get("list"):
        return {"ok": True, "data": {"kinds": sorted(_props.ANIMATION_TIMINGS.keys())}}
    kind = body.get("kind")
    if not kind:
        raise InvalidInputError("kind required (or list=true)")
    fps = body.get("fps")
    try:
        return {"ok": True, "data": _props.animation_timing(str(kind), float(fps) if fps else None)}
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc


@handler("POST", "/parametric/material/recipe")
def parametric_material_recipe(body: dict[str, Any]) -> dict[str, Any]:
    """Body: {name?: str, list?: bool}."""
    if body.get("list"):
        return {"ok": True, "data": {"recipes": sorted(_props.MATERIAL_RECIPES.keys())}}
    name = body.get("name")
    if not name:
        raise InvalidInputError("name required (or list=true)")
    try:
        return {"ok": True, "data": _props.material_recipe(str(name))}
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
