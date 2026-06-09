"""Parametric furniture builders.

Each builder is a function `build(params: dict) -> dict` that:
  1. validates + completes params (falls back to FURNITURE_DEFAULTS),
  2. creates named, scaled, parented objects directly via bpy.data + bmesh,
  3. returns {parts: {name: objectName}, dimensions: {...}, materials: [...]}

The dispatcher in `BlenderAgent/handlers/parametric.py` wraps each build call
in `composite_undo(...)` so the agent gets one-shot undo.

Convention: each builder names its parts `<asset>_<part>` (singular) or
`<asset>_<part>_<i>` (1-indexed) so the agent can predict the names.
"""
