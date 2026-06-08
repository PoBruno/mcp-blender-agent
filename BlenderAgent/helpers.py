"""Shared helpers used by every handler.

This module is the central place for:
- Typed exception classes that map to error codes
- Main-thread-safe mode switch helper (`with_mode`)
- Context-override helper for operators that need a 3D View
- Undo-push helper for composite operations
- Common UE5 naming conventions
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional, TypeVar

logger = logging.getLogger("BlenderAgent.helpers")

T = TypeVar("T")


# ----------------------------------------------------------------------------
# Typed exceptions — each has an `error_code` consumed by server.py boundary
# ----------------------------------------------------------------------------

class BlenderAgentError(Exception):
    """Base class. Subclasses set `error_code` consumed by server.py."""

    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, error_code: Optional[str] = None) -> None:
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class ObjectNotFoundError(BlenderAgentError):
    error_code = "OBJECT_NOT_FOUND"


class CollectionNotFoundError(BlenderAgentError):
    error_code = "COLLECTION_NOT_FOUND"


class SceneNotFoundError(BlenderAgentError):
    error_code = "SCENE_NOT_FOUND"


class MaterialNotFoundError(BlenderAgentError):
    error_code = "MATERIAL_NOT_FOUND"


class ArmatureNotFoundError(BlenderAgentError):
    error_code = "ARMATURE_NOT_FOUND"


class BoneNotFoundError(BlenderAgentError):
    error_code = "BONE_NOT_FOUND"


class ActionNotFoundError(BlenderAgentError):
    error_code = "ACTION_NOT_FOUND"


class ModifierNotFoundError(BlenderAgentError):
    error_code = "MODIFIER_NOT_FOUND"


class NodeNotFoundError(BlenderAgentError):
    error_code = "NODE_NOT_FOUND"


class ImageNotFoundError(BlenderAgentError):
    error_code = "IMAGE_NOT_FOUND"


class ShapeKeyNotFoundError(BlenderAgentError):
    error_code = "SHAPE_KEY_NOT_FOUND"


class VertexGroupNotFoundError(BlenderAgentError):
    error_code = "VERTEX_GROUP_NOT_FOUND"


class InvalidInputError(BlenderAgentError):
    error_code = "INVALID_INPUT"


class ContextOverrideFailedError(BlenderAgentError):
    error_code = "CONTEXT_OVERRIDE_FAILED"


class OperatorFailedError(BlenderAgentError):
    error_code = "OPERATOR_FAILED"


class ExportFailedError(BlenderAgentError):
    error_code = "EXPORT_FAILED"


class ImportFailedError(BlenderAgentError):
    error_code = "IMPORT_FAILED"


class UnsupportedVersionError(BlenderAgentError):
    error_code = "BLENDER_VERSION_UNSUPPORTED"


class ExecDisabledError(BlenderAgentError):
    error_code = "EXEC_PYTHON_DISABLED"


# ----------------------------------------------------------------------------
# Object lookup helpers
# ----------------------------------------------------------------------------

def get_object(name: str) -> Any:
    """Lookup `bpy.data.objects[name]` or raise `ObjectNotFoundError`."""
    import bpy  # type: ignore
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ObjectNotFoundError(f"Object {name!r} not found in bpy.data.objects")
    return obj


def get_collection(name: str) -> Any:
    import bpy  # type: ignore
    col = bpy.data.collections.get(name)
    if col is None:
        raise CollectionNotFoundError(f"Collection {name!r} not found")
    return col


def get_scene(name: Optional[str] = None) -> Any:
    import bpy  # type: ignore
    if name is None:
        return bpy.context.scene
    sc = bpy.data.scenes.get(name)
    if sc is None:
        raise SceneNotFoundError(f"Scene {name!r} not found")
    return sc


def get_material(name: str) -> Any:
    import bpy  # type: ignore
    mat = bpy.data.materials.get(name)
    if mat is None:
        raise MaterialNotFoundError(f"Material {name!r} not found")
    return mat


def get_armature_object(name: str) -> Any:
    obj = get_object(name)
    if obj.type != "ARMATURE":
        raise ArmatureNotFoundError(f"Object {name!r} is type {obj.type}, expected ARMATURE")
    return obj


def get_image(name: str) -> Any:
    import bpy  # type: ignore
    img = bpy.data.images.get(name)
    if img is None:
        raise ImageNotFoundError(f"Image {name!r} not found")
    return img


def get_action(name: str) -> Any:
    import bpy  # type: ignore
    act = bpy.data.actions.get(name)
    if act is None:
        raise ActionNotFoundError(f"Action {name!r} not found")
    return act


# ----------------------------------------------------------------------------
# Mode switch helper — wraps an operator block in Edit/Pose/Sculpt mode
# ----------------------------------------------------------------------------

@contextmanager
def with_mode(obj: Any, target_mode: str) -> Iterator[None]:
    """Switch `obj` into `target_mode`, run body, restore previous mode.

    `target_mode` is one of:
    OBJECT, EDIT, POSE, SCULPT, VERTEX_PAINT, WEIGHT_PAINT, TEXTURE_PAINT.
    """
    import bpy  # type: ignore

    prev_active = bpy.context.view_layer.objects.active
    prev_mode = obj.mode if obj == prev_active else "OBJECT"

    if obj != prev_active:
        bpy.context.view_layer.objects.active = obj

    if obj.mode != target_mode:
        bpy.ops.object.mode_set(mode=target_mode)
    try:
        yield
    finally:
        if obj.mode != prev_mode:
            try:
                bpy.ops.object.mode_set(mode=prev_mode)
            except Exception:  # noqa: BLE001
                logger.warning("with_mode: failed to restore mode %r", prev_mode)
        if prev_active is not None and prev_active != obj:
            try:
                bpy.context.view_layer.objects.active = prev_active
            except Exception:  # noqa: BLE001
                pass


# ----------------------------------------------------------------------------
# Context override helper — for operators needing a 3D View
# ----------------------------------------------------------------------------

@contextmanager
def with_3dview_context() -> Iterator[dict[str, Any]]:
    """Yield a context override dict suitable for `bpy.context.temp_override`.

    Finds the first VIEW_3D area+region in the current window. In `--background`
    mode there may be no window; we fall back to creating a synthetic override.
    """
    import bpy  # type: ignore

    override: dict[str, Any] = {}
    found = False
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        override = {
                            "window": window,
                            "screen": window.screen,
                            "area": area,
                            "region": region,
                            "scene": bpy.context.scene,
                        }
                        found = True
                        break
            if found:
                break
        if found:
            break

    if not found:
        # Headless / no window — yield a minimal override. Some ops still work.
        override = {
            "scene": bpy.context.scene,
            "view_layer": bpy.context.view_layer,
        }
        yield override
        return

    with bpy.context.temp_override(**override):
        yield override


# ----------------------------------------------------------------------------
# Undo wrapper for composite operations
# ----------------------------------------------------------------------------

@contextmanager
def composite_undo(message: str) -> Iterator[None]:
    """Wrap a composite tool body so all mutations land as ONE undo entry.

    Pushes a single `bpy.ops.ed.undo_push(message=...)` on successful exit.
    On exception, the partial state is NOT rolled back — the handler must
    clean up before raising (per ADR-004).
    """
    import bpy  # type: ignore
    yield
    try:
        bpy.ops.ed.undo_push(message=message)
    except Exception:  # noqa: BLE001
        logger.warning("composite_undo: undo_push(%r) failed", message)


# ----------------------------------------------------------------------------
# Selection helpers
# ----------------------------------------------------------------------------

def set_active_and_selected(obj: Any, *, deselect_all: bool = True) -> None:
    """Make `obj` the active object and the only selected one."""
    import bpy  # type: ignore
    if deselect_all:
        for o in bpy.data.objects:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# ----------------------------------------------------------------------------
# UE5 naming helpers
# ----------------------------------------------------------------------------

def ue5_collision_name(mesh_name: str, prefix: str, index: int = 1) -> str:
    """Return UE5 collision name: e.g. `UCX_MyMesh_01`."""
    if prefix not in {"UCX", "UBX", "USP", "UCP"}:
        raise InvalidInputError(f"Invalid collision prefix {prefix!r}; expected UCX/UBX/USP/UCP")
    return f"{prefix}_{mesh_name}_{index:02d}"


def ue5_socket_name(name: str) -> str:
    return f"SOCKET_{name}" if not name.startswith("SOCKET_") else name


# ----------------------------------------------------------------------------
# Version check
# ----------------------------------------------------------------------------

def require_blender_version(major: int, minor: int) -> None:
    """Raise UnsupportedVersionError if Blender is older than `major.minor`."""
    import bpy  # type: ignore
    v = bpy.app.version
    if v[0] < major or (v[0] == major and v[1] < minor):
        raise UnsupportedVersionError(
            f"Blender {v[0]}.{v[1]}.{v[2]} is older than required {major}.{minor}"
        )
