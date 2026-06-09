"""Parametric human base mesh — proportionally correct primitive composition.

The point is *correctness of proportions*, not detail. The output is a clean
named-parts mannequin that:
  - matches the chosen canon's head-counts on every landmark,
  - is composed of single-mesh-per-part primitives (sphere head, capsule torso,
    cylinders for limbs, ellipsoids for hands/feet),
  - has consistent collection naming and material slots,
  - is ready to be unified via /postproc/voxel_remesh + /postproc/quad_remesh
    if the user wants a single watertight mesh.

Parts produced (T-pose, facing +Y):
  human_head
  human_torso_upper        (chest + ribs, sphere-stretched)
  human_torso_lower        (abdomen + pelvis)
  human_neck
  human_upper_arm_L / _R
  human_forearm_L / _R
  human_hand_L / _R
  human_thigh_L / _R
  human_shin_L / _R
  human_foot_L / _R
"""

from __future__ import annotations

from typing import Any, Dict

import bpy  # type: ignore
import bmesh  # type: ignore
from mathutils import Matrix, Vector  # type: ignore

from ..anatomy.proportions import resolve_human, material_recipe


# ---------------------------------------------------------------------------
# primitive helpers
# ---------------------------------------------------------------------------

def _uv_sphere(name: str, radius: float, segments: int = 24, rings: int = 16) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _ellipsoid(name: str, rx: float, ry: float, rz: float, segments: int = 24, rings: int = 16) -> bpy.types.Mesh:
    """UV sphere of unit radius then non-uniform scaled to an ellipsoid."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    bmesh.ops.scale(bm, vec=(rx, ry, rz), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _capsule_z(name: str, radius: float, length: float, segments: int = 16) -> bpy.types.Mesh:
    """Capsule of given length oriented along +Z, centered at origin.

    Built as a cylinder + two hemispherical caps.
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    cyl_h = max(length - 2.0 * radius, 0.0)
    # cylinder body
    bmesh.ops.create_cone(
        bm,
        cap_ends=False, cap_tris=False,
        segments=segments,
        radius1=radius, radius2=radius,
        depth=cyl_h,
        matrix=Matrix.Identity(4),
    )
    # top hemisphere — full sphere then delete bottom half via select-by-Z
    bm_top = bmesh.new()
    bmesh.ops.create_uvsphere(bm_top, u_segments=segments, v_segments=max(8, segments // 2), radius=radius)
    # delete verts with z < 0
    verts_to_remove = [v for v in bm_top.verts if v.co.z < -1e-5]
    bmesh.ops.delete(bm_top, geom=verts_to_remove, context="VERTS")
    # translate top dome up to top of cylinder
    bmesh.ops.translate(bm_top, vec=(0.0, 0.0, cyl_h / 2.0), verts=bm_top.verts)
    # merge into main bm
    _merge_bmesh(bm, bm_top)
    bm_top.free()

    # bottom hemisphere — same trick mirrored
    bm_bot = bmesh.new()
    bmesh.ops.create_uvsphere(bm_bot, u_segments=segments, v_segments=max(8, segments // 2), radius=radius)
    verts_to_remove = [v for v in bm_bot.verts if v.co.z > 1e-5]
    bmesh.ops.delete(bm_bot, geom=verts_to_remove, context="VERTS")
    bmesh.ops.translate(bm_bot, vec=(0.0, 0.0, -cyl_h / 2.0), verts=bm_bot.verts)
    _merge_bmesh(bm, bm_bot)
    bm_bot.free()

    # heal seams between cylinder and caps
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _merge_bmesh(target: "bmesh.types.BMesh", source: "bmesh.types.BMesh") -> None:
    """Copy verts/faces from `source` into `target`. Manual implementation since
    bmesh has no public merge op — we read coords + face indices and re-create."""
    src_verts = list(source.verts)
    new_verts = [target.verts.new(v.co) for v in src_verts]
    target.verts.ensure_lookup_table()
    for face in source.faces:
        try:
            target.faces.new([new_verts[v.index] for v in face.verts])
        except ValueError:
            # duplicate face — skip
            continue


def _ensure_material(name: str, recipe_name: str) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    rec = material_recipe(recipe_name)
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (
            rec["base_color_r"], rec["base_color_g"], rec["base_color_b"], 1.0,
        )
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = rec["roughness"]
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = rec["metallic"]
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = rec.get("specular", 0.5)
        elif "Specular" in bsdf.inputs:
            bsdf.inputs["Specular"].default_value = rec.get("specular", 0.5)
    return mat


def _link(obj: bpy.types.Object, coll: bpy.types.Collection) -> None:
    coll.objects.link(obj)


def _assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat


# ---------------------------------------------------------------------------
# public builder
# ---------------------------------------------------------------------------

def build(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build a parametric human base mesh.

    Params:
        canon: str          — canon name (default 'heroic_male'). See
                              /parametric/anatomy/human listCanons=true.
        height: float (m)   — total body height, default 1.80
        material_recipe: str— skin material recipe name, default 'skin_caucasian'
        location: [x,y,z]   — origin (feet at z=0 + location.z), default [0,0,0]
        collection_name: str— default 'Human'
        with_arms_t_pose: bool — arms horizontal (T) vs slightly down (A).
                                 default True.
        head_scale: float   — extra scale multiplier on the head sphere, default 1.0
    """
    canon = str((params or {}).get("canon", "heroic_male"))
    height = float((params or {}).get("height", 1.80))
    mat_recipe = str((params or {}).get("material_recipe", "skin_caucasian"))
    origin = Vector((params or {}).get("location", [0.0, 0.0, 0.0]))
    coll_name = str((params or {}).get("collection_name", "Human"))
    t_pose = bool((params or {}).get("with_arms_t_pose", True))
    head_scale = float((params or {}).get("head_scale", 1.0))

    dims = resolve_human(canon, height)

    # collection
    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)

    mat_skin = _ensure_material(f"mat_{mat_recipe}", mat_recipe)

    parts: Dict[str, str] = {}

    # ---- HEAD ----
    head_h = dims["head_height_m"] * head_scale
    head_w = dims["head_width_m"] * head_scale
    head_d = head_w * 1.15  # heads are deeper than wide
    head_center_z = height - head_h / 2.0  # top of head at z=height
    head_mesh = _ellipsoid("mesh_human_head", head_w / 2.0, head_d / 2.0, head_h / 2.0)
    head_obj = bpy.data.objects.new("human_head", head_mesh)
    head_obj.location = origin + Vector((0.0, 0.0, head_center_z))
    _link(head_obj, coll)
    _assign_material(head_obj, mat_skin)
    parts["head"] = head_obj.name

    # ---- NECK ----
    neck_h = head_h * 0.45
    neck_r = head_w * 0.22
    neck_center_z = dims["shoulder_height_m"] + neck_h / 2.0
    neck_mesh = _capsule_z("mesh_human_neck", neck_r, neck_h + 2 * neck_r)
    neck_obj = bpy.data.objects.new("human_neck", neck_mesh)
    neck_obj.location = origin + Vector((0.0, 0.0, neck_center_z))
    _link(neck_obj, coll)
    _assign_material(neck_obj, mat_skin)
    parts["neck"] = neck_obj.name

    # ---- UPPER TORSO (chest) ----
    shoulder_z = dims["shoulder_height_m"]
    nipple_z = dims["nipple_height_m"]
    navel_z = dims["navel_height_m"]
    crotch_z = dims["crotch_height_m"]
    chest_w = dims["chest_width_m"]
    shoulder_w = dims["shoulder_width_m"]

    upper_torso_h = shoulder_z - navel_z
    upper_torso_center_z = (shoulder_z + navel_z) / 2.0
    upper_torso_mesh = _ellipsoid(
        "mesh_human_torso_upper",
        rx=shoulder_w / 2.2,                   # rib-cage X half-width
        ry=chest_w / 3.5,                      # front-back depth
        rz=upper_torso_h / 2.0,
    )
    upper_torso_obj = bpy.data.objects.new("human_torso_upper", upper_torso_mesh)
    upper_torso_obj.location = origin + Vector((0.0, 0.0, upper_torso_center_z))
    _link(upper_torso_obj, coll)
    _assign_material(upper_torso_obj, mat_skin)
    parts["torso_upper"] = upper_torso_obj.name

    # ---- LOWER TORSO (abdomen + pelvis) ----
    lower_torso_h = navel_z - crotch_z + dims["head_height_m"] * 0.10
    lower_torso_center_z = (navel_z + crotch_z) / 2.0
    hip_w = dims["hip_width_m"]
    waist_w = dims["waist_width_m"]
    avg_w = (hip_w + waist_w) / 2.0
    lower_torso_mesh = _ellipsoid(
        "mesh_human_torso_lower",
        rx=avg_w / 2.2,
        ry=avg_w / 3.5,
        rz=lower_torso_h / 2.0,
    )
    lower_torso_obj = bpy.data.objects.new("human_torso_lower", lower_torso_mesh)
    lower_torso_obj.location = origin + Vector((0.0, 0.0, lower_torso_center_z))
    _link(lower_torso_obj, coll)
    _assign_material(lower_torso_obj, mat_skin)
    parts["torso_lower"] = lower_torso_obj.name

    # ---- ARMS ----
    upper_arm_len = dims["upper_arm_length_m"]
    forearm_len = dims["forearm_length_m"]
    hand_len = dims["hand_length_m"]
    arm_r_upper = dims["head_width_m"] * 0.20
    arm_r_fore = dims["head_width_m"] * 0.17
    # T-pose: arms point along ±X; A-pose: 30° down from horizontal
    import math
    if t_pose:
        arm_down_angle = 0.0
    else:
        arm_down_angle = math.radians(30.0)

    for sign, tag in [(-1, "L"), (1, "R")]:
        # shoulder pivot
        shoulder_pivot = Vector((sign * shoulder_w / 2.0, 0.0, shoulder_z))
        arm_dir = Vector((
            sign * math.cos(arm_down_angle),
            0.0,
            -math.sin(arm_down_angle),
        ))

        # upper arm — capsule along Z, then rotated to align with arm_dir
        ua_center = shoulder_pivot + arm_dir * (upper_arm_len / 2.0)
        ua_mesh = _capsule_z(f"mesh_human_upper_arm_{tag}", arm_r_upper, upper_arm_len)
        ua_obj = bpy.data.objects.new(f"human_upper_arm_{tag}", ua_mesh)
        ua_obj.location = origin + ua_center
        # rotation: from +Z to arm_dir
        ua_obj.rotation_mode = "QUATERNION"
        ua_obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(arm_dir)
        ua_obj.rotation_mode = "XYZ"
        _link(ua_obj, coll)
        _assign_material(ua_obj, mat_skin)
        parts[f"upper_arm_{tag}"] = ua_obj.name

        # elbow
        elbow = shoulder_pivot + arm_dir * upper_arm_len
        # forearm
        fa_center = elbow + arm_dir * (forearm_len / 2.0)
        fa_mesh = _capsule_z(f"mesh_human_forearm_{tag}", arm_r_fore, forearm_len)
        fa_obj = bpy.data.objects.new(f"human_forearm_{tag}", fa_mesh)
        fa_obj.location = origin + fa_center
        fa_obj.rotation_mode = "QUATERNION"
        fa_obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(arm_dir)
        fa_obj.rotation_mode = "XYZ"
        _link(fa_obj, coll)
        _assign_material(fa_obj, mat_skin)
        parts[f"forearm_{tag}"] = fa_obj.name

        # hand — ellipsoid
        wrist = elbow + arm_dir * forearm_len
        hand_center = wrist + arm_dir * (hand_len / 2.0)
        hand_mesh = _ellipsoid(
            f"mesh_human_hand_{tag}",
            rx=arm_r_fore * 1.05,
            ry=arm_r_fore * 0.45,
            rz=hand_len / 2.0,
        )
        hand_obj = bpy.data.objects.new(f"human_hand_{tag}", hand_mesh)
        hand_obj.location = origin + hand_center
        hand_obj.rotation_mode = "QUATERNION"
        hand_obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(arm_dir)
        hand_obj.rotation_mode = "XYZ"
        _link(hand_obj, coll)
        _assign_material(hand_obj, mat_skin)
        parts[f"hand_{tag}"] = hand_obj.name

    # ---- LEGS ----
    thigh_len = dims["thigh_length_m"]
    shin_len = dims["shin_length_m"]
    foot_len = dims["foot_length_m"]
    leg_r_upper = dims["head_width_m"] * 0.28
    leg_r_lower = dims["head_width_m"] * 0.22

    for sign, tag in [(-1, "L"), (1, "R")]:
        hip_pivot = Vector((sign * hip_w / 4.0, 0.0, crotch_z))
        # thigh — capsule straight down
        thigh_center = hip_pivot + Vector((0.0, 0.0, -thigh_len / 2.0))
        thigh_mesh = _capsule_z(f"mesh_human_thigh_{tag}", leg_r_upper, thigh_len)
        thigh_obj = bpy.data.objects.new(f"human_thigh_{tag}", thigh_mesh)
        thigh_obj.location = origin + thigh_center
        _link(thigh_obj, coll)
        _assign_material(thigh_obj, mat_skin)
        parts[f"thigh_{tag}"] = thigh_obj.name

        knee = hip_pivot + Vector((0.0, 0.0, -thigh_len))
        # shin
        shin_center = knee + Vector((0.0, 0.0, -shin_len / 2.0))
        shin_mesh = _capsule_z(f"mesh_human_shin_{tag}", leg_r_lower, shin_len)
        shin_obj = bpy.data.objects.new(f"human_shin_{tag}", shin_mesh)
        shin_obj.location = origin + shin_center
        _link(shin_obj, coll)
        _assign_material(shin_obj, mat_skin)
        parts[f"shin_{tag}"] = shin_obj.name

        # foot — ellipsoid lying horizontally, pointing +Y
        ankle = knee + Vector((0.0, 0.0, -shin_len))
        foot_h = foot_len * 0.20
        foot_center = ankle + Vector((0.0, foot_len * 0.3, foot_h / 2.0 - leg_r_lower * 0.4))
        foot_mesh = _ellipsoid(
            f"mesh_human_foot_{tag}",
            rx=leg_r_lower * 1.1,
            ry=foot_len / 2.0,
            rz=foot_h / 2.0,
        )
        foot_obj = bpy.data.objects.new(f"human_foot_{tag}", foot_mesh)
        foot_obj.location = origin + foot_center
        _link(foot_obj, coll)
        _assign_material(foot_obj, mat_skin)
        parts[f"foot_{tag}"] = foot_obj.name

    return {
        "parts": parts,
        "dimensions": dims,
        "materials": [mat_skin.name],
        "collection": coll.name,
        "params": {
            "canon": canon,
            "height": height,
            "material_recipe": mat_recipe,
            "location": list(origin),
            "collection_name": coll_name,
            "with_arms_t_pose": t_pose,
            "head_scale": head_scale,
        },
    }
