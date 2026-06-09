---
applyTo: '**'
description: Passive context — you control a live Blender session through the blender-agent MCP. Auto-applied to every interaction so the agent always knows the operating loop, the tool map, and the gotchas.
---

# You control Blender (via the blender-agent MCP)

When this instruction is loaded, assume the **blender-agent** MCP server is connected. You can drive a real Blender session: modeling, rigging, animation, materials, shader/geometry nodes, lighting, rendering, and export. Tools are named `blender_*`, `object_*`, `mesh_*`, `material_*`, `shader_node_*`, `armature_*`, `bone_*`, `keyframe_*`, `vision_*`, `render_*`, `export_*`, etc.

This is not a "describe what you would do" tool. **Call the tools and do it.** Every tool returns `{ ok, data, refs, nextSteps, warnings, errorCode }`; pass `refs` (object/material/bone names) into the next call.

## The operating loop (always)

1. **Launch first.** Before any modeling call, run `blender_launch`. It reuses an open Blender or starts a GUI one. Without it, calls fail with `BLENDER_UNREACHABLE`.
2. **See what you build.** After any change call `vision_snapshot` and *look at the image*. Never model blind. Use `vision_contact_sheet` for multi-angle review.
3. **Critique → refine → repeat.** Compare the snapshot to the user's intent. Fix one class of issue per iteration. Stop when it reads correctly.
4. **Validate before export.** `vision_topology_inspect` + `vision_scale_report` are your quality gates.

## Tool map (where to reach)

| Goal | Tools |
|---|---|
| Lifecycle | `blender_launch`, `blender_quit`, `addon_restart`, `server_status`, `server_handlers` |
| Primitives / transforms | `object_create`, `object_set_transform`, `object_apply_transform`, `object_delete`, `object_list`, `object_get_info` |
| Mesh edit | `mesh_extrude_region_move`, `mesh_bevel`, `mesh_loop_cut`, `mesh_subdivide`, `mesh_join`, `mesh_shade_smooth`, `mesh_merge_by_distance` |
| Modifiers | `modifier_add`, `modifier_set_property`, `modifier_apply` (SUBSURF, MIRROR, BEVEL, SOLIDIFY, ARRAY, …) |
| Materials / shading | `material_create`, `material_set_principled`, `material_create_pbr_from_textures`, `material_assign_slot`, `shader_node_add`, `shader_node_set_input_value`, `shader_node_connect_pins` |
| Geo nodes | `geo_node_group_create`, `geo_node_add_node`, `geo_node_connect`, `geo_node_apply_to_object` |
| UV | `uv_smart_project`, `uv_unwrap`, `uv_pack_islands`, `uv_validate_for_baking` |
| Rig | `armature_create`, `armature_create_biped`, `bone_add`, `bone_set_parent`, `bone_ik_setup`, `armature_parent_with_auto_weights` |
| Animation | `action_create`, `action_assign_to_object`, `bone_set_pose_transform`, `keyframe_bone_pose`, `pose_set`, `nla_track_add`, `nla_push_action_to_strip` |
| Lighting / world / render | `light_create`, `world_create`, `world_assign_to_scene`, `render_set_engine`, `render_set_resolution`, `render_render_still`, `render_render_animation` |
| Vision / feedback | `vision_snapshot`, `vision_contact_sheet`, `vision_turntable`, `vision_topology_inspect`, `vision_scale_report`, `vision_silhouette_compare` |
| Parametric library | `parametric_list`, `parametric_build` |
| Post-process | `postproc_voxel_remesh`, `postproc_quad_remesh`, `postproc_decimate`, `postproc_smart_uv_project`, `bake_run` |
| Export | `export_fbx_static`, `export_fbx_skeletal`, `export_fbx_animation`, `export_fbx_collection_batch`, `export_gltf` |

Run `server_handlers` to list every route the connected addon exposes. See [`blender-agent/TOOLS.md`](blender-agent/TOOLS.md) for the full reference and [`blender-agent/FLOWS.md`](blender-agent/FLOWS.md) for concrete recipes.

## Gotchas (these bite first-timers)

- **Pose with euler → keyframe euler.** `bone_set_pose_transform(rotationEuler=…)` puts the bone in XYZ mode. When you `keyframe_bone_pose`, pass `channels: ["rotation_euler"]` — the default keys quaternion and your rotation will silently not animate.
- **Actions don't reset un-keyed bones.** Switching to an action leaves bones it doesn't key in their previous pose. Key every bone you want controlled, or reset them.
- **Persist actions.** A freshly created action has 0 users and is purged on save. Set `useFakeUser: true` on creation or push to an NLA strip — otherwise it won't survive a save/load.
- **Apply scale before width-based ops.** Non-uniform object scale distorts Bevel/Solidify width. Bake transforms first.
- **Object mode for operators.** Many operators (`mesh_shade_smooth`, joins) fail if the object is in Sculpt/Edit mode.
- **View transform mutes color.** Default AgX desaturates. For vivid color set view transform to Standard or push base-color saturation.
- **Critique renders are EEVEE + low samples by default** — fast. Reserve Cycles / high samples for the hero shot.
- **`exec_python` is disabled by default.** Check `server_handlers` for a typed tool before reaching for raw Python. Enable only by launching Blender with `BLENDER_AGENT_ALLOW_EXEC_PYTHON=1`.

## When something fails

- `BLENDER_UNREACHABLE` → call `blender_launch`.
- `BLENDER_NOT_FOUND` → Blender isn't installed/where expected; set `BLENDER_BIN`.
- `HANDLER_NOT_FOUND` → addon older than the MCP server; reinstall the addon, or `addon_restart`.
- A render/bake "hangs" → it's heavy and on the main thread; the call has a long timeout, wait for it. Don't spam retries.
