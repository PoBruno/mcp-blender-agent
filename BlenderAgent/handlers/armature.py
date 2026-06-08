"""Armature handlers (B7)."""

from __future__ import annotations

import re
from typing import Any

from ..helpers import (
    BoneNotFoundError,
    InvalidInputError,
    composite_undo,
    get_armature_object,
    get_collection,
    get_object,
    set_active_and_selected,
    with_3dview_context,
    with_mode,
)
from ..server import handler


@handler("POST", "/armature/create")
def armature_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new armature object."""
    import bpy  # type: ignore

    name = body.get("name", "Armature")
    location = tuple(body.get("location", (0.0, 0.0, 0.0)))
    collection_name = body.get("collectionName")

    with composite_undo(f"armature_create:{name}"):
        arm_data = bpy.data.armatures.new(name=f"{name}_data")
        arm_obj = bpy.data.objects.new(name=name, object_data=arm_data)
        arm_obj.location = location
        if collection_name:
            target = get_collection(collection_name)
            target.objects.link(arm_obj)
        else:
            bpy.context.scene.collection.objects.link(arm_obj)

    return {
        "ok": True,
        "data": {"armatureObjectName": arm_obj.name, "armatureDataName": arm_data.name},
        "refs": {"armatureName": arm_obj.name, "objectName": arm_obj.name},
    }


@handler("POST", "/armature/show_in_front")
def armature_show_in_front(body: dict[str, Any]) -> dict[str, Any]:
    arm = get_armature_object(body.get("armatureObjectName") or body.get("name"))
    show = bool(body.get("show", True))
    with composite_undo(f"armature_show_in_front:{arm.name}"):
        arm.show_in_front = show
    return {"ok": True, "data": {"armatureObjectName": arm.name, "showInFront": show},
            "refs": {"armatureName": arm.name}}


@handler("POST", "/armature/set_pose_position")
def armature_set_pose_position(body: dict[str, Any]) -> dict[str, Any]:
    """Switch an armature between POSE (animations evaluated) and REST (bind pose).

    REST ignores active action AND every NLA strip AND every pose-bone transform
    — it's the only reliable way to render the imported bind pose after the
    rig already has pushed strips. Restore with mode='POSE' after.

    Body: { armatureObjectName: str, mode: 'POSE' | 'REST' }
    """
    arm = get_armature_object(body.get("armatureObjectName") or body.get("name"))
    mode = (body.get("mode") or "POSE").upper()
    if mode not in ("POSE", "REST"):
        raise InvalidInputError(f"mode must be 'POSE' or 'REST', got {mode!r}")
    prev = arm.data.pose_position
    with composite_undo(f"armature_set_pose_position:{arm.name}/{mode}"):
        arm.data.pose_position = mode
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "mode": mode,
            "previousMode": prev,
        },
        "refs": {"armatureName": arm.name},
    }


# UE5 SK_Mannequin convention IK bones. Sibling-of-root layout (NOT children of pelvis).
# Heights/positions are in METERS at globalScale=1.0 (1 BU = 1 m). The artist
# adjusts foot_l/foot_r/hand_l/hand_r references after the rig is in place.
_UE5_IK_BONES: list[dict[str, Any]] = [
    {"name": "ik_foot_root", "head": [0.0, 0.0, 0.0], "tail": [0.0, 0.0, 0.1], "parent": None},
    {"name": "ik_foot_l", "head": [0.1, 0.0, 0.0], "tail": [0.1, 0.0, 0.1], "parent": "ik_foot_root"},
    {"name": "ik_foot_r", "head": [-0.1, 0.0, 0.0], "tail": [-0.1, 0.0, 0.1], "parent": "ik_foot_root"},
    {"name": "ik_hand_root", "head": [0.0, 0.0, 1.0], "tail": [0.0, 0.0, 1.1], "parent": None},
    {"name": "ik_hand_gun", "head": [0.0, 0.2, 1.2], "tail": [0.0, 0.2, 1.3], "parent": "ik_hand_root"},
    {"name": "ik_hand_l", "head": [0.2, 0.2, 1.2], "tail": [0.2, 0.2, 1.3], "parent": "ik_hand_gun"},
    {"name": "ik_hand_r", "head": [-0.2, 0.2, 1.2], "tail": [-0.2, 0.2, 1.3], "parent": "ik_hand_gun"},
]


@handler("POST", "/armature/add_ue5_ik_bones")
def armature_add_ue5_ik_bones(body: dict[str, Any]) -> dict[str, Any]:
    """Add the UE5 SK_Mannequin IK control bones to an armature.

    Body: {armatureObjectName: str, useDeform?: bool (default false),
           skipExisting?: bool (default true)}

    Adds 7 bones (sibling-of-root layout, not children of pelvis):
        ik_foot_root, ik_foot_l, ik_foot_r,
        ik_hand_root, ik_hand_gun, ik_hand_l, ik_hand_r

    All are non-deforming by default — they exist only as IK targets that UE5
    auto-detects during skeletal mesh import.
    """
    from mathutils import Vector  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    use_deform = bool(body.get("useDeform", False))
    skip_existing = bool(body.get("skipExisting", True))

    created: list[str] = []
    existed: list[str] = []
    with composite_undo(f"armature_add_ue5_ik_bones:{arm.name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            for spec in _UE5_IK_BONES:
                name = spec["name"]
                if name in eb:
                    if skip_existing:
                        existed.append(name)
                        continue
                    raise InvalidInputError(
                        f"bone {name!r} already exists (skipExisting=false)"
                    )
                b = eb.new(name=name)
                b.head = Vector(tuple(spec["head"]))
                b.tail = Vector(tuple(spec["tail"]))
                b.use_deform = use_deform
                created.append(name)
            # Re-link parents (need to do this after all bones exist so siblings
            # can reference each other).
            for spec in _UE5_IK_BONES:
                name = spec["name"]
                parent = spec["parent"]
                if name not in eb:
                    continue
                if parent and parent in eb:
                    eb[name].parent = eb[parent]
                    eb[name].use_connect = False

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "createdCount": len(created),
            "existingCount": len(existed),
            "createdBones": created,
            "existingBones": existed,
        },
        "refs": {"armatureName": arm.name, "boneNames": created + existed},
    }


_UE5_NAMING_FORBIDDEN_RE = re.compile(r"[A-Z]")
_UE5_DOT_SUFFIX_RE = re.compile(r"\.(L|R)$")


@handler("POST", "/armature/validate_ue5_convention")
def armature_validate_ue5_convention(body: dict[str, Any]) -> dict[str, Any]:
    """Validate an armature against UE5 SK_Mannequin conventions.

    Body: {armatureObjectName: str,
           zeroRollBones?: [str, ...] (bones that MUST have |roll| < tolerance),
           rollToleranceRad?: float (default 0.01 rad ~= 0.57°),
           requireLowercase?: bool (default true),
           requireUnderscoreLR?: bool (default true — fail .L/.R suffix),
           requiredBones?: [str, ...] (bones that MUST exist)}

    Returns ok=true if all checks pass. ok=false + warnings[] otherwise. This
    is a pure read; it never mutates the armature.
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    zero_roll_bones = body.get("zeroRollBones") or []
    roll_tol = float(body.get("rollToleranceRad", 0.01))
    require_lowercase = bool(body.get("requireLowercase", True))
    require_underscore_lr = bool(body.get("requireUnderscoreLR", True))
    required_bones = body.get("requiredBones") or []

    failures: list[dict[str, Any]] = []
    warnings: list[str] = []

    set_active_and_selected(arm)
    with with_mode(arm, "EDIT"):
        eb = arm.data.edit_bones
        names = {b.name for b in eb}

        # 1. Required bones present
        for req in required_bones:
            if req not in names:
                failures.append({"check": "required_bones", "boneName": req,
                                 "reason": "missing"})

        # 2. Naming conventions
        for b in eb:
            if require_lowercase and _UE5_NAMING_FORBIDDEN_RE.search(b.name):
                failures.append({"check": "lowercase", "boneName": b.name,
                                 "reason": "contains uppercase character"})
            if require_underscore_lr and _UE5_DOT_SUFFIX_RE.search(b.name):
                failures.append({"check": "underscore_lr", "boneName": b.name,
                                 "reason": "uses .L/.R; UE5 expects _l/_r"})

        # 3. Zero-roll bones
        for name in zero_roll_bones:
            if name not in eb:
                failures.append({"check": "zero_roll", "boneName": name,
                                 "reason": "bone missing — cannot verify roll"})
                continue
            r = float(eb[name].roll)
            if abs(r) > roll_tol:
                failures.append({
                    "check": "zero_roll",
                    "boneName": name,
                    "reason": f"roll {r:.4f} rad exceeds tolerance {roll_tol:.4f}",
                    "rollRad": r,
                    "rollDeg": r * 180.0 / 3.141592653589793,
                })

        bone_count = len(eb)

    ok = len(failures) == 0
    if not ok:
        warnings.append(
            f"{len(failures)} UE5 convention violation(s) detected on {arm.name!r}"
        )

    payload: dict[str, Any] = {
        "ok": ok,
        "data": {
            "armatureObjectName": arm.name,
            "boneCount": bone_count,
            "passed": ok,
            "failureCount": len(failures),
            "failures": failures,
        },
        "refs": {"armatureName": arm.name},
        "warnings": warnings,
    }
    if not ok:
        payload["errorCode"] = "VALIDATION_FAILED"
    return payload


_UE5_LR_SUFFIX_RE = re.compile(r"\.([LR])(_end)?$")


def _to_ue5_name(name: str, *, lowercase: bool, suffix_lr: bool) -> str:
    """Apply ARTIS UE5 naming rules to a single bone name.

    - .L  → _l       .R  → _r
    - .L_end → _l_end       .R_end → _r_end
    - then optional lowercase pass.
    Bones starting with 'SOCKET_' or 'ik_' are returned unchanged (already
    canonical) — the SOCKET_ prefix is intentionally uppercase per UE5 import
    detection, and ik_* bones we created are already lowercase.
    """
    if name.startswith("SOCKET_") or name.startswith("ik_"):
        return name
    out = name
    if suffix_lr:
        out = _UE5_LR_SUFFIX_RE.sub(
            lambda m: ("_" + m.group(1).lower()) + (m.group(2) or ""),
            out,
        )
    if lowercase:
        out = out.lower()
    return out


@handler("POST", "/armature/rename_to_ue5_convention")
def armature_rename_to_ue5_convention(body: dict[str, Any]) -> dict[str, Any]:
    """Rename every bone in an armature to match UE5 naming conventions.

    Body: {
      armatureObjectName: str,
      lowercase?: bool (default true),       # Bone.015 → bone.015
      suffixLR?: bool (default true),        # .L/.R → _l/_r, .L_end → _l_end
      dryRun?: bool (default false),         # if true, only report what would change
      exclude?: [str, ...] (optional)        # bones to leave untouched
    }

    Vertex groups bound to renamed bones are auto-updated by Blender. Bones
    prefixed with 'SOCKET_' or 'ik_' are skipped (already canonical).

    The whole batch runs inside a single Edit-Mode session + one undo step,
    so re-running is safe and Ctrl+Z reverts the entire batch.
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    lowercase = bool(body.get("lowercase", True))
    suffix_lr = bool(body.get("suffixLR", True))
    dry_run = bool(body.get("dryRun", False))
    exclude = set(body.get("exclude") or [])

    if not (lowercase or suffix_lr):
        raise InvalidInputError("at least one of lowercase or suffixLR must be true")

    # Plan first (no mutation) to detect collisions before we touch anything
    set_active_and_selected(arm)
    plan: list[tuple[str, str]] = []
    collisions: list[dict[str, Any]] = []
    with with_mode(arm, "EDIT"):
        eb = arm.data.edit_bones
        existing_names = {b.name for b in eb}
        new_names: dict[str, str] = {}
        for b in eb:
            if b.name in exclude:
                continue
            target = _to_ue5_name(b.name, lowercase=lowercase, suffix_lr=suffix_lr)
            if target == b.name:
                continue
            if target in existing_names and target != b.name:
                collisions.append({"from": b.name, "to": target,
                                   "reason": "target name already exists in armature"})
                continue
            if target in new_names.values():
                collisions.append({"from": b.name, "to": target,
                                   "reason": "target name collides with another planned rename"})
                continue
            new_names[b.name] = target
            plan.append((b.name, target))

        if dry_run or collisions:
            return {
                "ok": len(collisions) == 0,
                "data": {
                    "armatureObjectName": arm.name,
                    "dryRun": dry_run,
                    "planCount": len(plan),
                    "plan": [{"from": o, "to": n} for o, n in plan],
                    "collisionCount": len(collisions),
                    "collisions": collisions,
                },
                "refs": {"armatureName": arm.name},
                "errorCode": "NAME_COLLISION" if collisions else None,
            }

    # Apply for real — wrapped in undo
    renamed: list[dict[str, str]] = []
    with composite_undo(f"armature_rename_to_ue5:{arm.name}/{len(plan)}"):
        set_active_and_selected(arm)
        with with_mode(arm, "EDIT"):
            eb = arm.data.edit_bones
            # Two-pass rename to dodge transient collisions (a→b while b→c):
            #   pass 1: rename all to a tmp name with a $ prefix
            #   pass 2: rename tmp → final
            tmp_map: dict[str, str] = {}
            for old, new in plan:
                if old not in eb:
                    continue
                tmp = f"${old}#tmp"
                eb[old].name = tmp
                tmp_map[tmp] = new
            for tmp, final in tmp_map.items():
                if tmp not in eb:
                    continue
                eb[tmp].name = final
                actual = eb[final].name  # Blender may suffix .001 on collision
                renamed.append({"from": tmp.removeprefix("$").removesuffix("#tmp"),
                                "to": actual})

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "renamedCount": len(renamed),
            "renames": renamed,
        },
        "refs": {"armatureName": arm.name},
    }


# ----------------------------------------------------------------------------
# Skinning / pose composite tools
# ----------------------------------------------------------------------------


@handler("POST", "/armature/parent_with_auto_weights")
def armature_parent_with_auto_weights(body: dict[str, Any]) -> dict[str, Any]:
    """Parent meshes to an armature with automatic envelope/bone-heat weights.

    Composite of `bpy.ops.object.parent_set(type=...)`. The armature becomes
    parent, every mesh in `meshObjectNames` becomes a child with a generated
    Armature modifier and per-bone vertex groups.

    Body: {
      armatureObjectName: str,
      meshObjectNames: [str, ...],
      type?: 'ARMATURE_AUTO' | 'ARMATURE_NAME' | 'ARMATURE_ENVELOPE'
              | 'ARMATURE' (default 'ARMATURE_AUTO'),
      keepTransform?: bool   // default true; preserves world position
    }

    Returns: { childObjectNames: [str], modifierName: str | null }
    """
    import bpy  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    mesh_names = body.get("meshObjectNames") or []
    if not mesh_names:
        raise InvalidInputError("meshObjectNames is required (non-empty list)")
    parent_type = body.get("type", "ARMATURE_AUTO")
    if parent_type not in {"ARMATURE_AUTO", "ARMATURE_NAME", "ARMATURE_ENVELOPE", "ARMATURE"}:
        raise InvalidInputError(
            f"type {parent_type!r} not in ARMATURE_AUTO/NAME/ENVELOPE/ARMATURE"
        )
    keep_transform = bool(body.get("keepTransform", True))

    meshes = []
    for n in mesh_names:
        o = get_object(n)
        if o.type != "MESH":
            raise InvalidInputError(f"{n!r} is not a MESH (type={o.type})")
        meshes.append(o)

    children: list[str] = []
    with composite_undo(f"armature_parent_with_auto_weights:{arm.name}"):
        for o in bpy.data.objects:
            o.select_set(False)
        for m in meshes:
            m.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm  # armature MUST be active

        with with_3dview_context():
            try:
                bpy.ops.object.parent_set(
                    type=parent_type,
                    keep_transform=keep_transform,
                )
            except (RuntimeError, TypeError) as exc:
                raise InvalidInputError(
                    f"parent_set(type={parent_type!r}) failed: {exc}"
                ) from exc

        for m in meshes:
            children.append(m.name)

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "childObjectNames": children,
            "type": parent_type,
        },
        "refs": {"armatureName": arm.name, "childObjectNames": children},
    }


# Default mirror suffix pairs — covers UE5 (.l/.r), Blender (_L/_R), legacy.
_MIRROR_SUFFIX_PAIRS = (
    (".l", ".r"),
    (".L", ".R"),
    ("_l", "_r"),
    ("_L", "_R"),
    (".left", ".right"),
)


def _mirror_bone_name(name: str) -> str:
    """Return the L↔R mirror of a bone name. Returns name unchanged if no
    suffix match."""
    for a, b in _MIRROR_SUFFIX_PAIRS:
        if name.endswith(a):
            return name[: -len(a)] + b
        if name.endswith(b):
            return name[: -len(b)] + a
    return name


@handler("POST", "/armature/pose_mirror")
def armature_pose_mirror(body: dict[str, Any]) -> dict[str, Any]:
    """Mirror the current pose across the rig's local YZ plane (X-axis flip).

    Wraps `bpy.ops.pose.copy` + `bpy.ops.pose.paste(flipped=True)`. Bone
    naming must follow the standard L/R suffix convention; otherwise the paste
    silently no-ops on unmatched bones.

    Body: {
      armatureObjectName: str,
      boneNames?: [str, ...]  // restrict to a subset; default = all pose bones
    }

    Returns: { mirroredCount, bones: [{from, to}] }
    """
    import bpy  # type: ignore

    arm = get_armature_object(body.get("armatureObjectName"))
    only = body.get("boneNames")
    if only is not None and not isinstance(only, list):
        raise InvalidInputError("boneNames must be a list")

    pose_bones = arm.pose.bones
    targets = (
        [pose_bones[n] for n in only if n in pose_bones]
        if only is not None
        else list(pose_bones)
    )
    if only is not None:
        missing = [n for n in only if n not in pose_bones]
        if missing:
            raise BoneNotFoundError(f"bones not in armature: {missing}")

    mirrored: list[dict[str, str]] = []
    with composite_undo(f"armature_pose_mirror:{arm.name}"):
        set_active_and_selected(arm)
        with with_mode(arm, "POSE"):
            for pb in pose_bones:
                pb.bone.select = False
            for pb in targets:
                pb.bone.select = True

            with with_3dview_context():
                try:
                    bpy.ops.pose.copy()
                    bpy.ops.pose.paste(flipped=True)
                except (RuntimeError, TypeError) as exc:
                    raise InvalidInputError(f"pose mirror failed: {exc}") from exc

            for pb in targets:
                mirrored.append({"from": pb.name, "to": _mirror_bone_name(pb.name)})

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "mirroredCount": len(mirrored),
            "bones": mirrored,
        },
        "refs": {"armatureName": arm.name},
    }


def _snapshot_pose(arm: Any) -> dict[str, dict[str, list[float]]]:
    """Capture every pose bone's location/rotation_quaternion/scale."""
    snap: dict[str, dict[str, list[float]]] = {}
    for pb in arm.pose.bones:
        snap[pb.name] = {
            "location": list(pb.location),
            "rotation_quaternion": list(pb.rotation_quaternion),
            "rotation_euler": list(pb.rotation_euler),
            "rotation_mode": pb.rotation_mode,
            "scale": list(pb.scale),
        }
    return snap


@handler("POST", "/armature/pose_snapshot")
def armature_pose_snapshot(body: dict[str, Any]) -> dict[str, Any]:
    """Capture the current pose and store it under a name on the armature.

    Poses live in `arm['_pose_library']` (custom property) keyed by name.
    Body: { armatureObjectName: str, poseName: str }
    Returns: { poseName, boneCount }
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("poseName")
    if not name:
        raise InvalidInputError("poseName is required")

    with composite_undo(f"armature_pose_snapshot:{arm.name}/{name}"):
        snap = _snapshot_pose(arm)
        lib = arm.get("_pose_library") or {}
        # Bone IDProperty values aren't all natively serializable — Blender's
        # IDProperty supports dict / list / primitive nesting; this works.
        lib_dict = dict(lib) if hasattr(lib, "keys") else {}
        lib_dict[name] = snap
        arm["_pose_library"] = lib_dict

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "poseName": name,
            "boneCount": len(snap),
        },
        "refs": {"armatureName": arm.name, "poseName": name},
    }


@handler("POST", "/armature/pose_apply")
def armature_pose_apply(body: dict[str, Any]) -> dict[str, Any]:
    """Apply a previously snapshotted pose to the armature.

    Body: {
      armatureObjectName: str,
      poseName: str,
      boneNames?: [str, ...]   // restrict to subset
    }
    Returns: { appliedCount, missingBones }
    """
    arm = get_armature_object(body.get("armatureObjectName"))
    name = body.get("poseName")
    if not name:
        raise InvalidInputError("poseName is required")
    only = body.get("boneNames")
    only_set = set(only) if isinstance(only, list) else None

    lib = arm.get("_pose_library")
    if lib is None or name not in (lib.keys() if hasattr(lib, "keys") else dict(lib)):
        raise InvalidInputError(
            f"pose {name!r} not found in armature {arm.name!r} pose library"
        )
    snap = lib[name]

    applied = 0
    missing: list[str] = []
    with composite_undo(f"armature_pose_apply:{arm.name}/{name}"):
        with with_mode(arm, "POSE"):
            for bname, ch in dict(snap).items():
                if only_set is not None and bname not in only_set:
                    continue
                pb = arm.pose.bones.get(bname)
                if pb is None:
                    missing.append(bname)
                    continue
                ch = dict(ch)
                if "rotation_mode" in ch:
                    pb.rotation_mode = str(ch["rotation_mode"])
                if "location" in ch:
                    pb.location = tuple(ch["location"])
                if "rotation_quaternion" in ch:
                    pb.rotation_quaternion = tuple(ch["rotation_quaternion"])
                if "rotation_euler" in ch:
                    pb.rotation_euler = tuple(ch["rotation_euler"])
                if "scale" in ch:
                    pb.scale = tuple(ch["scale"])
                applied += 1

    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "poseName": name,
            "appliedCount": applied,
            "missingBones": missing,
        },
        "refs": {"armatureName": arm.name, "poseName": name},
    }


@handler("POST", "/armature/pose_library_list")
def armature_pose_library_list(body: dict[str, Any]) -> dict[str, Any]:
    """List every named pose stored on the armature."""
    arm = get_armature_object(body.get("armatureObjectName"))
    lib = arm.get("_pose_library")
    names: list[str] = []
    if lib is not None:
        try:
            names = sorted(lib.keys() if hasattr(lib, "keys") else dict(lib).keys())
        except (TypeError, AttributeError):
            names = []
    return {
        "ok": True,
        "data": {
            "armatureObjectName": arm.name,
            "count": len(names),
            "poseNames": names,
        },
        "refs": {"armatureName": arm.name},
    }

