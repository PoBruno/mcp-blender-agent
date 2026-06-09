---
name: blender-agent-control
description: Passive context — you control a live Blender session through the blender-agent MCP. Load this whenever the user asks to model, rig, animate, texture, light, render, or export anything in 3D, or mentions Blender. It tells you the operating loop, the tool map, and the gotchas that bite first-timers.
---

# You control Blender (via the blender-agent MCP)

When this skill is loaded, assume the user has the **blender-agent** MCP server connected. You can drive a real Blender session: modeling, rigging, animation, materials, shader/geometry nodes, lighting, rendering, and export. Tools are named `blender_*`, `object_*`, `mesh_*`, `material_*`, `shader_node_*`, `armature_*`, `bone_*`, `keyframe_*`, `vision_*`, `render_*`, `export_*`, etc.

This is not a "describe what you would do" tool. **Call the tools and do it.** Every tool returns `{ ok, data, refs, nextSteps, warnings, errorCode }`; pass `refs` (object/material/bone names) into the next call.

## The operating loop (always)

1. **Launch first.** Before any modeling call, run `blender_launch`. It reuses an open Blender or starts a GUI one from the default install path. Without it, calls fail with `BLENDER_UNREACHABLE`. `blender_quit` / `addon_restart` recover a wedged session.
2. **See what you build.** After any change, call `vision_snapshot` (fast viewport screenshot in GUI, fast EEVEE render in background) and *look at the image*. This is the feedback loop — never model blind. Use `vision_contact_sheet` for the final multi-angle gate.
3. **Critique → refine → repeat.** Compare the snapshot to the user's intent/reference. Fix one class of issue per iteration. Stop when it reads correctly.
4. **Validate before export.** `vision_topology_inspect` (tri/quad/ngon, manifold) and `vision_scale_report` (dimensions vs spec) are your quality gates.

For anything beyond a single primitive, load the **aaa-modeling** skill — it has the full brief→spec→strategy→refine→postprocess pipeline.

## Tool map (where to reach)

| Goal | Tools |
|---|---|
| Lifecycle | `blender_launch`, `blender_quit`, `addon_restart`, `server_status`, `server_handlers` |
| Primitives / transforms | `object_create`, `object_set_transform`, `object_delete`, `object_list`, `object_get_info` |
| Mesh edit | `mesh_extrude_region_move`, `mesh_bevel`, `mesh_loop_cut`, `mesh_subdivide`, `mesh_join`, `mesh_shade_smooth`, `mesh_merge_by_distance` |
| Modifiers | `modifier_add`, `modifier_set_property`, `modifier_apply` (SUBSURF, MIRROR, BEVEL, SOLIDIFY, ARRAY, …) |
| Materials / shading | `material_create`, `material_assign_slot`, `shader_node_add`, `shader_node_set_input_value`, `shader_node_connect_pins` |
| Rig | `armature_create`, `bone_add`, `bone_set_parent`, `bone_ik_setup`, `vertex_group_create`, `vertex_group_assign_vertices`, `armature_parent_with_auto_weights` |
| Animation | `action_create`, `action_assign_to_object`, `bone_set_pose_transform`, `keyframe_bone_pose`, `nla_track_add`, `nla_push_action_to_strip` |
| Lighting / world / render | `light_create`, `world_create`, `world_assign_to_scene`, `render_set_engine`, `render_set_resolution`, `render_render_still` |
| Vision / feedback | `vision_snapshot`, `vision_contact_sheet`, `vision_turntable`, `vision_topology_inspect`, `vision_scale_report` |
| Parametric library | `parametric_list`, `parametric_build` (chair_beach, stool_bar, table_dining, human_basic) |
| Post-process / export | `postproc_voxel_remesh`, `postproc_quad_remesh`, `postproc_decimate`, `uv_smart_project`, `bake_run`, `export_fbx_static`, `export_gltf` |

Run `server_handlers` to list every route the connected addon exposes.

## Gotchas (these bite first-timers)

- **Pose with euler → keyframe euler.** `bone_set_pose_transform(rotationEuler=…)` puts the bone in XYZ mode. When you `keyframe_bone_pose`, pass `channels: ["rotation_euler"]` — the default keys quaternion and your rotation will silently not animate.
- **Actions don't reset un-keyed bones.** Switching to an action leaves bones it doesn't key in their previous pose. Key every bone you want controlled, or reset them.
- **Persist actions.** A freshly created action has 0 users and is purged on save. Push it to an NLA strip (`nla_push_action_to_strip`) or it won't survive.
- **Apply scale before width-based ops.** Non-uniform object scale distorts Bevel/Solidify width. Bake transforms (or build at final size) first.
- **Object mode for operators.** Many operators (`mesh_shade_smooth`, joins) fail if the object is in Sculpt/Edit mode.
- **View transform mutes color.** Blender's default AgX desaturates. For vivid color either set the view transform to Standard or push base-color saturation.
- **Critique renders are EEVEE + low samples by default** — fast. Reserve Cycles / high samples for the final hero shot.

## When something fails

- `BLENDER_UNREACHABLE` → call `blender_launch`.
- `BLENDER_NOT_FOUND` → Blender isn't installed/where expected; set `BLENDER_BIN`.
- `HANDLER_NOT_FOUND` → addon older than the MCP server; reinstall the addon, or `addon_restart`.
- A render/bake "hangs" → it's heavy and on the main thread; the call has a long timeout, wait for it. Don't spam retries.
