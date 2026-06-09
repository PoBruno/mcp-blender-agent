"""Generative bridges (S6-15) — image-to-3D via external backends.

The realistic path for organic / photoreal content ("model this character from a
photo") is a learned image-to-3D model. Generation runs OUTSIDE Blender; this
handler is the dispatch + import point. Backends are pluggable:

  BLENDER_AGENT_IMG23D_BACKEND = 'hunyuan3d' | 'tripo' | 'meshy' | 'rodin'
  BLENDER_AGENT_IMG23D_ENDPOINT, BLENDER_AGENT_IMG23D_KEY  (for HTTP APIs)

No backend ships in v1.0 — wiring one is a follow-up. Until then the handler
returns a structured, actionable errorCode instead of pretending. When a backend
is added, it produces a mesh file and this handler imports it via import_obj /
import_gltf and returns the new object names in refs.
"""

from __future__ import annotations

import os
from typing import Any

from ..helpers import InvalidInputError
from ..server import handler

_SUPPORTED = ["hunyuan3d (local, open-source)", "tripo", "meshy", "rodin"]


@handler("POST", "/generate/image_to_3d", timeout=900.0)
def generate_image_to_3d(body: dict[str, Any]) -> dict[str, Any]:
    """Generate a mesh from a reference image via the configured backend (S6-15).

    Body: {imagePath: str, name?: str, targetPolycount?: int,
           removeBackground?: bool, importInto?: str (collection)}

    Returns the imported object names in refs when a backend is wired. With no
    backend configured returns errorCode BACKEND_NOT_CONFIGURED + how to enable.
    """
    image_path = body.get("imagePath")
    if not image_path or not os.path.isfile(str(image_path)):
        raise InvalidInputError("imagePath must be an existing image file")

    backend = os.environ.get("BLENDER_AGENT_IMG23D_BACKEND")
    if not backend:
        return {
            "ok": False,
            "errorCode": "BACKEND_NOT_CONFIGURED",
            "data": {
                "message": "No image-to-3D backend configured.",
                "supported": _SUPPORTED,
                "howToEnable": [
                    "Set BLENDER_AGENT_IMG23D_BACKEND to one of the supported backends.",
                    "For HTTP APIs also set BLENDER_AGENT_IMG23D_ENDPOINT and BLENDER_AGENT_IMG23D_KEY.",
                    "For hunyuan3d, install it locally (16GB VRAM) and expose its inference endpoint.",
                    "Fallback for now: use the parametric library / primitive blockout path.",
                ],
            },
        }

    # A backend is named but none is bundled in this build. This is where a
    # concrete integration calls the model, downloads the mesh, then imports it
    # (import_obj / import_gltf) and returns refs.objectNames.
    return {
        "ok": False,
        "errorCode": "BACKEND_NOT_IMPLEMENTED",
        "data": {
            "backend": backend,
            "message": (
                f"backend {backend!r} is selected but not bundled in this build; "
                "wire the generation+import step in handlers/generate.py"
            ),
        },
    }
