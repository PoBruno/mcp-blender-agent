# TOOLS — reference by domain

Every MCP tool the `blender-agent` server exposes, grouped by domain. ~216 tools across 20 groups at v1.0. Always-up-to-date source of truth is `server_handlers` at runtime — this file is the at-a-glance map you reach for when picking.

Every tool returns the structured contract:
```ts
{ ok: boolean, data?, refs?, nextSteps?, warnings?, errorCode? }
```

`refs` are the IDs you chain to the next call.

---

## Server / lifecycle

`blender_launch`, `blender_quit`, `server_status`, `server_handlers`, `server_shutdown`, `addon_restart`, `batch`.

Use `blender_launch` once per session. `server_handlers` is your self-discovery tool — call it whenever you're unsure a capability exists.

---

## File I/O

`file_new`, `file_open`, `file_save`, `file_save_as`, `file_append_data`, `file_pack_all`, `file_unpack_all`, `image_save_as`.

---

## Scene / collection / view layer

`scene_create`, `scene_list`, `scene_set_active`, `scene_set_frame_range`, `scene_set_unit_scale_for_modular_kit`, `collection_create`, `collection_delete`, `collection_list`, `collection_move_objects`, `collection_instance_create`, `view_layer_create`, `view_layer_create_for_export`, `view_layer_list`.

---

## Object — base CRUD + transforms

`object_create`, `object_delete`, `object_list`, `object_get_info`, `object_rename`, `object_duplicate_linked`, `object_set_mode`, `object_set_transform`, `object_apply_transform`, `object_add_blockout`, `object_add_constraint`, `object_list_constraints`, `object_remove_constraint`, `object_update_constraint`.

`object_set_mode` is mandatory before mesh-edit / sculpt / pose operations that require their mode. The composite tools handle this for you.

---

## Mesh editing

`mesh_extrude_region_move`, `mesh_bevel`, `mesh_loop_cut`, `mesh_subdivide`, `mesh_merge_by_distance`, `mesh_separate_by_loose_parts`, `mesh_join`, `mesh_triangulate`, `mesh_recalc_normals`, `mesh_shade_smooth`, `mesh_shade_flat`, `mesh_set_origin_to_snap_corner`, `mesh_parent_to_armature`.

`bmesh`-backed. All run on the main thread inside Edit Mode, restore Object Mode on exit.

---

## Modifiers

`modifier_add`, `modifier_apply`, `modifier_remove`, `modifier_list`, `modifier_reorder`, `modifier_set_property`.

Non-destructive. Prefer over `mesh_*` for any "make it smoother / mirror / array / lattice" intent.

---

## Material + shader graph

`material_create`, `material_delete`, `material_set_principled`, `material_create_pbr_from_textures`, `material_create_procedural_grid`, `material_assign_slot`, `material_slot_add`, `shader_node_add`, `shader_node_remove`, `shader_node_list`, `shader_node_connect_pins`, `shader_node_set_input_value`, `node_group_create`, `node_group_instance_in_material`.

For texture-driven PBR, `material_create_pbr_from_textures` builds the full graph in one call. For procedural, compose nodes manually.

---

## Geometry nodes

`geo_node_group_create`, `geo_node_add_node`, `geo_node_connect`, `geo_node_set_node_input`, `geo_node_apply_to_object`.

---

## UV

`uv_unwrap`, `uv_smart_project`, `uv_unwrap_smart_project`, `uv_layer_create`, `uv_mark_seams`, `uv_pack_islands`, `uv_average_islands_scale`, `uv_minimize_stretch`, `uv_validate_for_baking`.

---

## Armature / rigging

`armature_create`, `armature_create_biped`, `armature_pose_apply`, `armature_pose_snapshot`, `armature_pose_mirror`, `armature_pose_library_list`, `armature_show_in_front`, `armature_set_pose_position`, `armature_parent_with_auto_weights`, `armature_validate_ue5_convention`, `armature_rename_to_ue5_convention`, `armature_add_ue5_ik_bones`.

### Bones

`bone_add`, `bone_delete`, `bone_delete_by_pattern`, `bone_rename`, `bone_list`, `bone_set_parent`, `bone_set_edit_transform`, `bone_set_pose_transform`, `bone_set_roll`, `bone_recalculate_roll`, `bone_set_custom_shape`, `bone_ik_setup`, `bone_add_constraint`, `bone_remove_constraint`, `bone_update_constraint`, `bone_list_constraints`, `bone_collection_create`, `bone_collection_assign_bone`.

### Vertex groups

`vertex_group_create`, `vertex_group_assign_vertices`, `vertex_group_delete`.

---

## Animation

`action_create`, `action_assign_to_object`, `action_unassign_from_object`, `action_rename`, `action_list`, `action_inspect`, `action_duplicate`, `action_mirror`.

`keyframe_add`, `keyframe_bone_pose`, `keyframe_set_interpolation`, `pose_set`.

`fcurve_list`, `fcurve_evaluate`, `fcurve_add_modifier`.

`nla_track_add`, `nla_push_action_to_strip`, `nla_list`, `nla_strip_update`, `nla_strip_remove`.

`anim_bake_action`, `driver_add`, `driver_remove`.

Always set `useFakeUser: true` when creating an Action you'll later push to NLA — otherwise it can be garbage-collected.

### Aim Offset (UE5 9-pose matrix)

`aim_offset_bake_9_pose_matrix`, `aim_offset_split_to_9_single_frame_actions`, `aim_offset_validate_9_pose_matrix`.

---

## Shape keys + MetaHuman

`shape_key_add`, `shape_key_rename`, `shape_key_set_value`.
`metahuman_ensure_arkit52_shape_keys`, `metahuman_arkit52_list`.

---

## Sculpting + collision + sockets

`sculpt_enable_dyntopo`, `sculpt_voxel_remesh`.
`collision_add_box`, `collision_add_convex_hull`.
`socket_add` (UE5-style socket bones).

---

## Post-processing

`postproc_decimate`, `postproc_voxel_remesh`, `postproc_quad_remesh`, `postproc_lod_generate`, `postproc_smart_uv_project`, `postproc_auto_smooth_normals`.

---

## Constraints (object-level)

`object_add_constraint`, `object_update_constraint`, `object_remove_constraint`, `object_list_constraints`. Bone-level constraints are under the Bones section above.

---

## Cameras + lights + world

`camera_create`, `camera_set_active`, `camera_set_clipping`, `camera_set_dof`, `camera_frame_object`.
`light_create`, `light_set_property`.
`world_create`, `world_assign_to_scene`.

---

## Render + compositor + bake

`render_set_engine`, `render_set_resolution`, `render_set_output`, `render_set_view_transform`, `render_render_still`, `render_render_animation`.
`compositor_enable`, `compositor_add_node`, `compositor_connect`, `compositor_set_node_input`, `compositor_set_node_property`.
`bake_setup_target_image`, `bake_run`.

---

## Import + export

### Import
`import_fbx`, `import_gltf`, `import_obj`.

### Export
`export_fbx_static` — static mesh + collision.
`export_fbx_skeletal` — rig + mesh.
`export_fbx_animation` — action(s) on a rig.
`export_fbx_collection_batch` — one .fbx per object in a collection.
`export_gltf` — glTF / GLB.

Every export tool's parameters mirror Blender's operator panel 1:1, with tooltips quoted in `.describe()`.

---

## Parametric library

`parametric_list`, `parametric_build`, `parametric_anatomy_furniture`, `parametric_anatomy_human`, `parametric_animation_timing`, `parametric_material_recipe`.

Builders shipped at v1.0: `chair_beach`, `table_dining`, `stool_bar`, `human_basic`. Use `parametric_list` to discover what else has been added.

---

## Asset library + linked data

`asset_mark`, `asset_clear`.
`library_link`, `library_make_override`, `library_reload`.

---

## Generative (image-to-3D)

`generate_image_to_3d` — wraps a configurable external generator (provider chosen at addon-load via env). Returns an imported mesh, slotted into the scene like any other object.

---

## Vision (the agent's eyes)

`vision_snapshot` — single render from an angle.
`vision_contact_sheet` — 6-angle grid for review.
`vision_turntable` — N-frame rotation render (sprite strip).
`vision_silhouette_compare` — IoU + diff heatmap against a reference image.
`vision_render_action` — sprite strip of an action over a frame range.
`vision_topology_inspect` — vertex/edge/face stats + non-manifold edges.
`vision_scale_report` — bounding box vs unit scale (catches the 100x scale bug).
`vision_screenshot_viewport` — raw viewport grab when you need WYSIWYG instead of a fresh render.

Use these aggressively. The agent has no eyes otherwise.

---

## Escape hatch

`exec_python` — arbitrary Python in Blender. **Disabled by default.** Enable by launching Blender with `BLENDER_AGENT_ALLOW_EXEC_PYTHON=1`. Treat as last resort; every "do X with Python" temptation should first be checked against `server_handlers` for an existing typed tool.

`exec_status` — reports whether `exec_python` is enabled and why.
