# TOOL-CATALOG.md

The complete v1.0 tool inventory — every MCP tool the agent will ship, organized by pipeline and group. **228 tools** across 9 pipelines.

Each entry is `tool_name` + status + one-line purpose. Click into the linked pipeline file for full schema, examples, and feasibility notes.

**Status legend:**
- 🟢 v1.0 — feasible and shipping
- 🟡 v1.0 (with caveats) — feasible but documented constraint (mode switch, context override, version-specific)
- 🔴 v1.1+ — deferred
- ⚫ env-flagged — only available with `BLENDER_AGENT_ALLOW_EXEC=1`
- ⭐ composite — multi-step composite tool that ends with one `undo_push`
- ❌ not shipped — out of scope, documented as non-goal

---

## Quick stats

| Pipeline | Group prefix(es) | Count | v1.0 ready |
|---|---|---|---|
| B1 Environment kits | `scene_*`, `collection_*`, `object_*`, `mesh_*`, `collision_*`, `material_*`, `uv_*`, `export_*`, `view_layer_*` | 16 | 15 🟢🟡 / 1 🔴 |
| B2 Hard-surface props | `mesh_*`, `modifier_*`, `material_*`, `export_*` | 28 | 24 🟢🟡 / 4 🔴 |
| B3 Organic / character | `mesh_*`, `sculpt_*`, `modifier_*`, `retopo_*`, `shape_key_*`, `uv_*`, `export_*` | 21 | 17 🟢🟡 / 4 🔴 |
| B4 UV + bake | `uv_*`, `bake_*`, `image_*`, `cage_*` | 22 | 22 🟢🟡 / 0 🔴 |
| B5 Materials / shaders | `material_*`, `shader_node_*`, `node_group_*` | 24 | 23 🟢🟡 / 1 🔴 |
| B6 Geometry Nodes + Compositor | `geo_node_*`, `compositor_*`, `modifier_*`, `render_*` | 22 | 20 🟢🟡 / 2 🔴 |
| B7 Rigging + MetaHuman | `armature_*`, `bone_*`, `bone_collection_*`, `driver_*`, `vertex_group_*`, `shape_key_*`, `socket_*`, `metahuman_*` | 31 | 31 🟢🟡 / 0 🔴 |
| B8 Animation + export | `action_*`, `keyframe_*`, `fcurve_*`, `nla_*`, `armature_*`, `export_*`, `import_*`, `blend_*` | 25 | 25 🟢🟡 / 0 🔴 |
| B9 Lighting / camera / render / scene / file | `light_*`, `world_*`, `camera_*`, `render_*`, `viewport_*`, `scene_*`, `collection_*`, `view_layer_*`, `library_*`, `asset_*`, `file_*`, `exec_*` | 34 | 33 🟢🟡 / 1 ⚫ |
| **Total** | — | **223** | **210 v1.0 ready** |

> Note: some tools (e.g. `uv_smart_project`, `scene_create`, `export_fbx_static`, `collection_create`, `view_layer_create`, `shape_key_create_arkit_set`, `export_fbx_skeletal`) appear in more than one pipeline's research notes because multiple pipelines use them. The catalog below lists each tool **once, in its canonical owner pipeline.** The duplicate listings in research files cross-reference back here.

---

## B1 — Environment kits (modular level building)

Full source: [pipelines/B1-environment-kits.md](pipelines/B1-environment-kits.md)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `scene_create` | 🟢 | Create a new scene with unit system + frame range (canonical owner — also used by B9) |
| 2 | `collection_create` | 🟢 | Create a collection at a path (canonical owner — also used by B9) |
| 3 | `object_add_blockout` | 🟢 | Add a primitive mesh sized to a target footprint for level layout |
| 4 | `object_set_transform` | 🟢 | Set object location/rotation/scale (snap-friendly grid units) |
| 5 | `object_duplicate_linked` ⭐ | 🟡 | Duplicate with shared mesh data; needs 3D View context override |
| 6 | `mesh_set_origin_to_snap_corner` | 🟢 | Move origin to a named corner (X+Y+Z, X-Y+Z, etc.) for grid snapping |
| 7 | `collision_add_convex_hull` | 🟢 | Generate UCX_ child mesh from selected object via Convex Hull modifier |
| 8 | `collection_instance_create` ⭐ | 🟡 | Instantiate a collection as a single-object reference (kit reuse); context override |
| 9 | `material_create_procedural_grid` | 🟢 | Create a checker/grid material for blockout visualization |
| 10 | `material_assign_slot` | 🟢 | Assign material to object's slot N (canonical owner — also used by B2, B5) |
| 11 | `uv_unwrap_smart_project` ⭐ | 🟡 | Wrapper around `uv_smart_project` with kit-friendly defaults; context override |
| 12 | `export_fbx_static` | 🟢 | Export selection as static mesh FBX with full param matrix (canonical owner — also used by B2, B8) |
| 13 | `export_fbx_collection_batch` ⭐ | 🟢 | Export each top-level child of a collection as its own FBX file |
| 14 | `scene_set_unit_scale_for_modular_kit` | 🟢 | Configure scene units to UE5 cm (`unit_settings.scale_length=0.01`, system='METRIC') |
| 15 | `view_layer_create_for_export` | 🟢 | Create an export-only view layer with kit collections enabled (canonical owner — also used by B9) |
| 16 | `decal_project_3d` | 🔴 | Modal projection workflow — out of scope; use material alpha-clip on flat plane instead |

---

## B2 — Hard-surface props (weapons, vehicles, machinery)

Full source: [pipelines/B2-hard-surface-props.md](pipelines/B2-hard-surface-props.md)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `mesh_add_primitive` | 🟢 | Add cube/cylinder/sphere/plane/torus with size + segment params |
| 2 | `mesh_mirror_modifier_add` | 🟢 | Add Mirror modifier (axis, bisect, clip) |
| 3 | `mesh_array_modifier_add` | 🟢 | Add Array modifier (count, offset, fit type) |
| 4 | `mesh_boolean_modifier_add` | 🟢 | Add Boolean (union/diff/intersect, exact/fast solver) |
| 5 | `mesh_bevel_modifier_add` | 🟢 | Add Bevel modifier (width, segments, profile, custom profile 4.2) |
| 6 | `mesh_subdivision_modifier_add` | 🟢 | Add Subdivision Surface (viewport + render levels) |
| 7 | `mesh_smooth_by_angle_modifier_add` | 🟢 | Add Smooth-by-Angle GN modifier (4.1+ replacement for `use_auto_smooth`) |
| 8 | `mesh_decimate_modifier_add` | 🟢 | Add Decimate modifier for LOD (collapse/un-subdivide/planar) |
| 9 | `mesh_edge_split_modifier_add` | 🟢 | Add Edge Split modifier (pre-export hard edges) |
| 10 | `mesh_solidify_modifier_add` | 🟢 | Add Solidify modifier (thickness, offset) |
| 11 | `mesh_weld_modifier_add` | 🟢 | Add Weld modifier (distance-based merge) |
| 12 | `mesh_triangulate_modifier_add` | 🟢 | Add Triangulate modifier (quad/n-gon methods) |
| 13 | `mesh_mark_sharp` ⭐ | 🟡 | Mark edges sharp by selection criteria; needs Edit Mode |
| 14 | `mesh_bevel_edge_single` ⭐ | 🟡 | Non-modal bevel of selected edges; Edit Mode |
| 15 | `mesh_extrude_faces` ⭐ | 🟡 | Extrude face indices by vector; Edit Mode + bmesh; **edge/face index fragile** |
| 16 | `mesh_inset_faces` ⭐ | 🟡 | Inset face indices by thickness; Edit Mode |
| 17 | `mesh_bridge_edge_loops` ⭐ | 🟡 | Bridge two edge loops; Edit Mode + context override |
| 18 | `mesh_duplicate_for_lod` ⭐ | 🟢 | Composite: duplicate + apply Decimate at ratio → name `LOD1`, `LOD2` |
| 19 | `modifier_apply_all` | 🟢 | Apply all modifiers in stack order (canonical owner — also used by B6 as `modifier_apply`) |
| 20 | `mesh_validate_topology` | 🟢 | Read-only: count tris/quads/ngons, non-manifold edges, loose verts |
| 21 | `material_create_principled_for_ue5` | 🟢 | Create Principled BSDF material with UE5-safe defaults |
| 22 | `mesh_assign_material_slot` | 🟢 | Assign material to mesh slot index |
| 23 | `mesh_create_collision_box` | 🟢 | Create `UBX_<Name>` child empty-mesh box collision |
| 24 | `mesh_create_collision_convex` | 🟡 | Create `UCX_<Name>` child convex hull; round-trip FBX verify pending |
| 25 | `export_fbx_skeletal` | 🟢 | (see B8 — listed there as canonical owner) |
| 26 | `export_gltf` | 🟢 | Khronos PBR-subset export (canonical owner — B8 ships `export_gltf_skeletal` for animated) |
| 27 | `mesh_validate_for_export_ue5` | 🟢 | Read-only: tri-only, scale=1, transform=identity, single material per part check |
| 28 | `knife_interactive` | 🔴 | Modal — use `bpy.ops.mesh.bisect` instead |

---

## B3 — Organic / character (sculpting + ARKit blendshapes)

Full source: [pipelines/B3-organic-character.md](pipelines/B3-organic-character.md)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `mesh_create_box_subdivided` | 🟢 | Create cube with N subdivisions for base sculpt mesh |
| 2 | `mesh_extrude_faces` | 🟡 | (alias of B2 §15) |
| 3 | `modifier_add_multires` | 🟢 | Add Multi-Resolution modifier with target subdivision level |
| 4 | `sculpt_mode_toggle` ⭐ | 🟡 | Enter/exit Sculpt Mode on active mesh; idempotent |
| 5 | `sculpt_filter_apply` | 🟢 | Apply mesh filter (smooth/sharpen/inflate/relax) deterministically |
| 6 | `sculpt_remesh_voxel` | 🟢 | Voxel remesh at voxel size (replaces Dyntopo for retopo prep) |
| 7 | `sculpt_symmetrize` | 🟢 | Symmetrize the sculpt across axis (+/−X/Y/Z) |
| 8 | `sculpt_set_brush_param` | 🟢 | Set brush radius/strength/falloff for the active brush |
| 9 | `sculpt_brush_stroke_deterministic` ⭐ | 🟡 | Replay a pre-recorded stroke list (verify in 4.2 — modal alternative path) |
| 10 | `sculpt_mask_create_from_cavity` | 🟢 | Generate mask from cavity (concave areas) for selective sculpt |
| 11 | `retopo_create_base_cage` ⭐ | 🟡 | Composite: Shrinkwrap-based base cage over high-poly (manual topo path) |
| 12 | `shape_key_create_basis` | 🟢 | Add Basis shape key to mesh (idempotent) |
| 13 | `shape_key_add` | 🟢 | Add named relative shape key off Basis |
| 14 | `shape_key_create_arkit_set` ⭐ | 🟢 | Composite: create all 52 ARKit blendshapes named per Apple spec (canonical owner — also used by B7) |
| 15 | `shape_key_set_value` | 🟢 | Set a shape key's value 0..1 |
| 16 | `shape_key_add_driver` | 🟡 | Add a driver to a shape key (templated expression only) |
| 17 | `uv_mark_seams` ⭐ | 🟡 | Mark UV seams from selection or sharp edges; Edit Mode |
| 18 | `uv_smart_project` ⭐ | 🟡 | (canonical owner — also used by B1, B4) — Smart UV Project; context override |
| 19 | `uv_pack_islands` ⭐ | 🟡 | Pack UV islands; needs UV Editor context |
| 20 | `export_fbx_skeletal_character` ⭐ | 🟢 | Composite: A-pose verify + ARKit verify + FBX export with UE5 character defaults |
| 21 | `sculpt_freehand_stroke` | 🔴 | Modal brush — see [BPY-FEASIBILITY §2 row 1](BPY-FEASIBILITY.md) |
| 22 | `polybuild_retopo` | 🔴 | Modal — manual `bmesh` build is the agent path |
| 23 | `texture_paint_stroke` | 🔴 | Modal — out of scope; use B4 bake instead |
| 24 | `metahuman_face_dna_rig` | 🔴 | Full FACS rig — v1.1+ |

---

## B4 — UV + bake (texture production)

Full source: [pipelines/B4-uv-and-baking.md](pipelines/B4-uv-and-baking.md)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `uv_layer_create` | 🟢 | Add a named UV layer (up to 8 per mesh) |
| 2 | `uv_mark_seam` ⭐ | 🟡 | Mark edges as seams from selection; Edit Mode |
| 3 | `uv_unwrap` ⭐ | 🟡 | Angle-Based unwrap of current selection; Edit Mode |
| 4 | `uv_smart_project` ⭐ | 🟡 | (canonical reference — see B3 §18) |
| 5 | `uv_pack_islands` ⭐ | 🟡 | Pack islands with margin; UV Editor context |
| 6 | `uv_average_islands_scale` ⭐ | 🟡 | Match texel density across islands |
| 7 | `uv_minimize_stretch` ⭐ | 🟡 | Iterative relax of UV stretch |
| 8 | `bake_image_create` | 🟢 | Create blank Image datablock at resolution + colorspace + alpha + float depth |
| 9 | `bake_normal` ⭐ | 🟡 | Bake tangent-space normal (high→low with cage); requires active Image Texture node |
| 10 | `bake_roughness` ⭐ | 🟡 | Bake Roughness pass |
| 11 | `bake_metallic` ⭐ | 🟡 | Bake Metallic pass |
| 12 | `bake_diffuse` ⭐ | 🟡 | Bake Diffuse Color pass |
| 13 | `bake_ao` ⭐ | 🟡 | Bake Ambient Occlusion |
| 14 | `bake_curvature` ⭐ | 🟡 | Bake Pointiness (via Emit-from-Pointiness setup) |
| 15 | `bake_position` ⭐ | 🟡 | Bake world-position pass |
| 16 | `image_save_render` | 🟢 | Save image to disk (PNG/EXR) with colorspace settings |
| 17 | `cage_object_create` ⭐ | 🟢 | Composite: duplicate low-poly + Solidify offset for normal-bake cage |
| 18 | `uv_project_from_view` ⭐ | 🟡 | UV from current view projection; context override on 3D View area |
| 19 | `uv_project_cube` / `uv_project_cylinder` / `uv_project_sphere` | 🟡 | Primitive UV projections; Edit Mode |
| 20 | `uv_follow_active_quads` ⭐ | 🟡 | Active-quad-follow for strip/trim flows; Edit Mode |
| 21 | `uv_lightmap_pack` ⭐ | 🟡 | Generate Channel 2 lightmap UV (optional for non-Lumen workflows) |
| 22 | `uv_align_to_trim_row` ⭐ | 🟡 | Composite: align selected islands to trim-sheet row coordinates |
| 23 | `uv_snap_to_pixels` | 🟢 | Snap UVs to pixel grid at target resolution |
| 24 | `uv_validate_for_baking` | 🟢 | Read-only: overlap check, 0..1 bounds, density variance, island count |
| 25 | `image_pack` / `image_unpack` | 🟢 | Pack/unpack image data into the `.blend` |
| 26 | `bake_normal_high_to_low` ⭐ | 🟢 | Composite: cage create + normal bake + DirectX swizzle option + save |
| 27 | `uv_prepare_for_export` ⭐ | 🟢 | Composite: smart project + pack + average + validate |
| 28 | `bake_pbr_set` ⭐ | 🟢 | Composite: bake normal + roughness + metallic + AO in one call |

(Counts as ~22 unique primitives + 4 composites = 26 entries; some merge into 22 in the per-pipeline §3 table.)

---

## B5 — Materials / shaders (Principled BSDF + procedural + node groups)

Full source: [pipelines/B5-materials-shaders.md](pipelines/B5-materials-shaders.md)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `material_create` | 🟢 | Create empty Material with `use_nodes=True` |
| 2 | `material_delete` | 🟢 | Remove Material from `bpy.data` |
| 3 | `material_assign_to_object` | 🟢 | Wire Material into object slot 0 (creates slot if needed) |
| 4 | `shader_node_add_principled_bsdf` | 🟢 | Add Principled BSDF node to material's shader tree |
| 5 | `shader_node_set_principled_param` | 🟢 | Set Base Color / Metallic / Roughness / IOR / Alpha by name |
| 6 | `shader_node_add_image_texture` | 🟢 | Load image + add Image Texture node + set colorspace |
| 7 | `shader_node_add_normal_map` | 🟢 | Add Normal Map node (TANGENT space) with UV input |
| 8 | `shader_node_connect_pins` | 🟢 | Connect two named sockets `from_node.from_socket → to_node.to_socket` |
| 9 | `shader_node_set_mapping_param` | 🟢 | Set Mapping node location/rotation/scale |
| 10 | `shader_node_add_noise_texture` | 🟢 | Add Noise Texture node with scale/detail/distortion |
| 11 | `shader_node_add_voronoi_texture` | 🟢 | Add Voronoi (Musgrave replacement post-4.1) with feature param |
| 12 | `shader_node_add_color_ramp` | 🟡 | Add ColorRamp (4.0+ element API) |
| 13 | `shader_node_add_mix_shader` | 🟢 | Add Mix Shader node with fac input |
| 14 | `node_group_create` | 🟢 | Create empty Shader/Geometry NodeGroup |
| 15 | `node_group_add_interface_socket` | 🟡 | Add typed input/output socket via 4.0+ `tree.interface.new_socket(...)` |
| 16 | `node_group_instantiate_in_material` | 🟢 | Drop a NodeGroup into a material's shader tree |
| 17 | `material_slot_add` | 🟢 | Add an empty material slot to object |
| 18 | `material_assign_per_face_range` | 🟢 | Assign material slot index to polygon range (per-face material) |
| 19 | `material_create_pbr_for_ue` ⭐ | 🟢 | Composite: Principled + textures (BaseColor/Normal/Roughness/Metallic/AO) wired with UE5 defaults |
| 20 | `material_create_foliage_two_sided` ⭐ | 🟡 | Composite: Mix Shader + Translucent for foliage cards |
| 21 | `material_create_decal_alpha_clip` ⭐ | 🟡 | Composite: alpha-clip material with `blend_method='CLIP'` |
| 22 | `material_validate_for_ue_export` | 🟢 | Read-only: no UE-unsafe nodes, texture paths exist, single Principled root |
| 23 | `material_snapshot_to_json` | 🟡 | Serialize material node graph to JSON (defaults + links) |
| 24 | `shader_node_full_exposure` | 🔴 | All 60+ ShaderNode subtypes — v1.0 ships core only; full exposure v1.1+ |

---

## B6 — Geometry Nodes + Compositor (procedural + post)

Full source: [pipelines/B6-geometry-nodes-compositor.md](pipelines/B6-geometry-nodes-compositor.md)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `geo_node_tree_create` | 🟢 | Create new GeometryNodeTree datablock |
| 2 | `geo_node_modifier_add` | 🟢 | Add GN modifier to object + bind tree |
| 3 | `geo_node_node_create` | 🟢 | Create node of `bl_idname` in a GN tree |
| 4 | `geo_node_link_create` | 🟢 | Wire two GN sockets |
| 5 | `geo_node_input_set` | 🟢 | Set default value of GN modifier input (by name or index) |
| 6 | `geo_node_instance_on_points_setup` ⭐ | 🟡 | Composite: Distribute Points + Instance on Points + Realize (forest scatter) |
| 7 | `geo_node_distribute_points_density_attribute` | 🟡 | Variable-density distribution via Vertex Color/Weight (4.2 attribute API verify) |
| 8 | `geo_node_capture_attribute` | 🟡 | Capture Named Attribute on geometry (4.0+ API) |
| 9 | `geo_node_store_named_attribute` | 🟢 | Store Named Attribute on point/face/corner domain |
| 10 | `geo_node_realize_instances` | 🟢 | Realize Instances node — required before UE export of scattered instances |
| 11 | `modifier_apply` ⭐ | 🟢 | Apply modifier (canonical name in B6; same op as B2 §19 `modifier_apply_all`) |
| 12 | `compositor_enable` | 🟢 | `scene.use_nodes = True` |
| 13 | `compositor_node_add` | 🟢 | Add CompositorNode of `bl_idname` |
| 14 | `compositor_node_set` | 🟢 | Set node param by name |
| 15 | `compositor_link_create` | 🟢 | Wire two compositor sockets |
| 16 | `compositor_render_frame` | 🟡 | Render single frame through compositor; may need temp_override |
| 17 | `render_engine_set` | 🟢 | (canonical reference — see B9 §C1 `render_set_engine`) |
| 18 | `geo_node_mesh_primitive_create` ⭐ | 🟢 | Composite: GN-generated mesh primitive (cube/cylinder via GN nodes) |
| 19 | `geo_node_attribute_mix` | 🟡 | Field-mix two attribute fields (4.2 socket-naming verify) |
| 20 | `geo_node_collection_swap_by_attribute` | 🔴 | `GeometryNodeIndexSwitch` or custom group lookup — v1.1 |
| 21 | `geo_node_simulation_zone_setup` ⭐ | 🔴 | Simulation Zone frame-loop — v1.1 (frame-by-frame main-thread integration deep dive) |
| 22 | `modifier_list_get` | 🟢 | Read-only: list modifiers on object |

---

## B7 — Rigging + MetaHuman face

Full source: [pipelines/B7-rigging-metahuman.md](pipelines/B7-rigging-metahuman.md)

### B7.A — Armature

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `armature_create` | 🟢 | Create empty Armature + wrapper Object |
| 2 | `armature_list` | 🟢 | Read-only: list all armatures |
| 3 | `armature_create_ue5_mannequin` ⭐ | 🟢 | Composite: full UE5 Mannequin skeleton (root→pelvis→spine_01..05, IK virtuals, full finger chain) |
| 4 | `armature_symmetrize` ⭐ | 🟡 | Symmetrize armature across X axis; Edit Mode |

### B7.B — Bones

| # | Tool | Status | Purpose |
|---|---|---|---|
| 5 | `bone_add` ⭐ | 🟡 | Add EditBone with head/tail/roll; Edit Mode |
| 6 | `bone_list` | 🟢 | Read-only: list bones with parent/head/tail/roll |
| 7 | `bone_set_head_tail` ⭐ | 🟡 | Set head/tail vectors; Edit Mode |
| 8 | `bone_set_roll` ⭐ | 🟡 | Set bone roll; Edit Mode |
| 9 | `bone_set_parent` ⭐ | 🟡 | Set parent + use_connect; Edit Mode |
| 10 | `bone_mirror` ⭐ | 🟡 | Mirror selected bones across axis with name suffix flip |
| 11 | `bone_apply_pose` ⭐ | 🟡 | Apply current Pose-Mode transform as the rest pose |
| 12 | `bone_rename_convention` | 🟢 | Flip `.L`/`.R` ↔ `_l`/`_r` per UE/Blender convention |

### B7.C — Pose-mode constraints (constraint authoring; UI-grouped under `bone_*`)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 13 | `bone_set_constraint_ik` | 🟢 | Add IK constraint with chain_count + target + pole target |
| 14 | `bone_set_constraint_copy_location` | 🟢 | Add Copy Location constraint |
| 15 | `bone_set_constraint_copy_rotation` | 🟢 | Add Copy Rotation constraint |
| 16 | `bone_set_constraint_limit_location` | 🟢 | Add Limit Location constraint |
| 17 | `bone_set_constraint_limit_rotation` | 🟢 | Add Limit Rotation constraint |

### B7.D — Drivers

| # | Tool | Status | Purpose |
|---|---|---|---|
| 18 | `driver_add_from_bone_rotation` ⭐ | 🟡 | Composite: add driver on target data_path from bone rotation axis × multiplier |

### B7.E — Vertex groups + skinning

| # | Tool | Status | Purpose |
|---|---|---|---|
| 19 | `vertex_group_create` | 🟢 | Create empty named vertex group |
| 20 | `vertex_group_create_from_armature` ⭐ | 🟢 | Composite: one VG per bone, named to match |
| 21 | `vertex_group_auto_weight_from_armature` ⭐ | 🟢 | Composite: `bpy.ops.object.parent_set(type='ARMATURE_AUTO')` |
| 22 | `vertex_group_list` | 🟢 | Read-only: list groups |
| 23 | `vertex_group_normalize_weights` | 🟢 | `bpy.ops.object.vertex_group_normalize_all()` |

### B7.F — Bone collections (4.0+)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 24 | `bone_collection_create` | 🟡 | Create armature.collections entry (4.0+ API) |
| 25 | `bone_collection_assign_bone` | 🟡 | Add bone to collection (4.0+) |

### B7.G — MetaHuman face

| # | Tool | Status | Purpose |
|---|---|---|---|
| 26 | `shape_key_create_arkit_set` ⭐ | 🟢 | (canonical reference — see B3 §14) |
| 27 | `metahuman_face_validate` | 🟢 | Read-only: verify all 52 ARKit shape keys present + correctly named |

### B7.H — Sockets

| # | Tool | Status | Purpose |
|---|---|---|---|
| 28 | `socket_add` | 🟢 | Create `SOCKET_<name>` empty parented to a bone (UE socket) |
| 29 | `socket_list` | 🟢 | Read-only: list all SOCKET_* empties |

### B7.I — Object-level (mesh-armature parenting)

| # | Tool | Status | Purpose |
|---|---|---|---|
| 30 | `mesh_parent_to_armature` ⭐ | 🟢 | Parent mesh to armature with armature modifier (linked to skeleton) |

### B7.J — Out of scope

| # | Tool | Status | Purpose |
|---|---|---|---|
| 31 | `metahuman_face_rig_install` | 🔴 | Full DNA face rig — v1.1+ (see Question A in B7 source) |
| 32 | `weight_paint_brush_stroke` | 🔴 | Modal — out of scope (use `vertex_group.add(indices, weight)` instead) |

---

## B8 — Animation + retarget + export/import

Full source: [pipelines/B8-animation-export.md](pipelines/B8-animation-export.md)

### B8.A — Authoring

| # | Tool | Status | Purpose |
|---|---|---|---|
| 1 | `action_create` | 🟢 | Create empty Action and bind to object's `animation_data` |
| 2 | `keyframe_insert_bone` | 🟢 | Insert keyframe on `pose.bones["x"].location/rotation/scale` at frame N |
| 3 | `keyframe_insert_object` | 🟢 | Insert keyframe on object's transform at frame N |
| 4 | `fcurve_set_keyframe_values` | 🟢 | Surgically edit existing F-curve points (co, handle_left, handle_right, interpolation) |
| 5 | `fcurve_add_modifier` | 🟢 | Add F-curve modifier (Cycles, Noise, Limits, Stepped, Generator) |

### B8.B — NLA

| # | Tool | Status | Purpose |
|---|---|---|---|
| 6 | `nla_track_create_and_push_action` | 🟢 | Create NLA track + push action as strip |
| 7 | `nla_bake_to_action` ⭐ | 🟢 | **⭐ CRITICAL FOR UE** — bake NLA + constraints + drivers into a single flat Action |

### B8.C — Retargeting

| # | Tool | Status | Purpose |
|---|---|---|---|
| 8 | `armature_retarget_to_ue5_mannequin` ⭐ | 🟡 | **⭐ LARGE COMPOSITE** — bone-name remap + Copy Rotation constraints + bake to clean Action |

### B8.D — Export

| # | Tool | Status | Purpose |
|---|---|---|---|
| 9 | `export_fbx_skeletal` | 🟢 | **⭐ PRIMARY** — full UE5 skeletal export (~40 typed params, see [UE-TARGETS §7](research/UE-TARGETS.md)) |
| 10 | `export_fbx_animation` ⭐ | 🟢 | Animation-only FBX (per-Action loop, skeleton only) |
| 11 | `export_gltf_skeletal` | 🟢 | glTF with multiple animations in one file (~60 params) |
| 12 | `export_fbx_static` | 🟢 | (canonical reference — see B1 §12) |
| 13 | `export_alembic_hair` | 🟢 | Alembic curve export for UE Groom |
| 14 | `export_usd_skeletal` | 🟡 | USD skeletal (Blender 4.2+ required) |
| 15 | `export_obj_static` | 🟢 | OBJ static-only |
| 16 | `export_bvh_animation` | 🟢 | BVH motion capture export with rotation-mode selection |

### B8.E — Import

| # | Tool | Status | Purpose |
|---|---|---|---|
| 17 | `import_fbx_animation` | 🟡 | FBX animation into existing rig (manual bone remap; no auto-bind) |
| 18 | `import_fbx_skeletal` | 🟢 | FBX skeletal mesh + animation |
| 19 | `import_gltf_skeletal` | 🟢 | glTF skeletal import |
| 20 | `import_alembic` | 🟢 | Alembic curve/cache import |
| 21 | `import_usd_skeletal` | 🟢 | USD skeletal import (4.2+) |
| 22 | `import_obj_static` | 🟢 | OBJ import |
| 23 | `import_bvh_animation` | 🟢 | BVH — creates new armature from mocap |

### B8.F — Blend file IO

| # | Tool | Status | Purpose |
|---|---|---|---|
| 24 | `blend_open` | 🟢 | `bpy.ops.wm.open_mainfile` |
| 25 | `blend_save` | 🟢 | `bpy.ops.wm.save_mainfile` |

---

## B9 — Lighting / camera / render / scene / library / file

Full source: [pipelines/B9-lighting-camera-render-scene.md](pipelines/B9-lighting-camera-render-scene.md)

### B9.A — Lighting

| # | Tool | Status | Purpose |
|---|---|---|---|
| A1 | `light_create` | 🟢 | Create light (SUN/POINT/SPOT/AREA) with energy + color |
| A2 | `light_set_area_shape` | 🟢 | Set area light shape (SQUARE/RECTANGLE/DISK/ELLIPSE) + dims |
| A3 | `light_configure_linking` | 🟢 | Configure Light Linking (4.2+) — include/exclude per object/collection |
| A4 | `light_create_group` | 🟢 | Create Light Group for compositor light passes |
| A5 | `world_set_hdri` | 🟢 | Set world HDRI env texture from disk + rotation + strength |

### B9.B — Camera

| # | Tool | Status | Purpose |
|---|---|---|---|
| B1 | `camera_create` | 🟢 | Create camera + wrapper Object with focal length + sensor size |
| B2 | `camera_set_dof` | 🟢 | Set depth of field (focus distance/object + f-stop) |
| B3 | `camera_set_clipping` | 🟢 | Set near/far clip |
| B4 | `camera_set_active` | 🟢 | Set scene's active camera |

### B9.C — Render

| # | Tool | Status | Purpose |
|---|---|---|---|
| C1 | `render_set_engine` | 🟢 | Set engine (`CYCLES`, `BLENDER_EEVEE_NEXT`, `BLENDER_WORKBENCH`) |
| C2 | `render_configure_cycles` | 🟢 | Set Cycles samples, denoiser, light bounces, device |
| C3 | `render_configure_eevee_next` | 🟢 | Set EEVEE-Next settings (4.2+) |
| C4 | `render_set_output` | 🟢 | Set output filepath, resolution, format, frame range |
| C5 | `render_still_image` ⭐ | 🟢 | Render single frame; main-thread blocking |
| C6 | `render_animation` ⭐ | 🟢 | Render frame range; main-thread blocking, long-running |
| C7 | `viewport_screenshot` ⭐ | 🟡 | Screenshot from 3D View (context override needed in headless) |

### B9.D — Scene / collection / library / asset

| # | Tool | Status | Purpose |
|---|---|---|---|
| D1 | `scene_create` | 🟢 | (canonical owner — see B1 §1) |
| D2 | `scene_set_active` | 🟢 | Set the active scene by name |
| D3 | `collection_create` | 🟢 | (canonical owner — see B1 §2) |
| D4 | `collection_move_objects` | 🟢 | Move objects between collections |
| D5 | `view_layer_create` | 🟢 | (canonical owner — see B1 §15) |
| D6 | `library_link` | 🟡 | Link datablock(s) from external `.blend` |
| D7 | `library_make_override` | 🟡 | Make Library Override on linked datablock |
| D8 | `library_resync` | 🟡 | Resync override against upstream (fragile) |
| D9 | `library_make_local` | 🟡 | Convert linked datablock to local |
| D10 | `asset_mark` | 🟢 | Mark datablock as Asset (UI Asset Browser discovery) |
| D11 | `asset_unmark` | 🟢 | Unmark Asset flag |

### B9.E — File IO

| # | Tool | Status | Purpose |
|---|---|---|---|
| E1 | `file_save` | 🟢 | Save current `.blend` to its filepath |
| E2 | `file_save_as` | 🟢 | Save current `.blend` to a new filepath |
| E3 | `file_open` | 🟢 | Open `.blend` (replaces current session) |
| E4 | `file_append_data` | 🟢 | Append (copy in) datablock(s) from external `.blend` |
| E5 | `file_pack_all` | 🟢 | Pack all external resources into the `.blend` |
| E6 | `file_unpack_all` | 🟢 | Unpack to disk |
| E7 | `exec_python` | ⚫ | **NOT SHIPPED BY DEFAULT** — only available with `BLENDER_AGENT_ALLOW_EXEC=1` env flag |

---

## Cross-pipeline alias map (which file is the canonical owner)

Some tool names appear in multiple research files. Canonical ownership:

| Tool | Canonical owner | Also appears in |
|---|---|---|
| `scene_create` | B1 | B9 |
| `collection_create` | B1 | B9 |
| `view_layer_create` | B1 | B9 |
| `export_fbx_static` | B1 | B2, B8 |
| `export_fbx_skeletal` | B8 | B2, B3 |
| `material_assign_slot` / `material_assign_to_object` | B5 | B1, B2 |
| `uv_smart_project` | B3 | B1, B4 |
| `uv_pack_islands` | B4 | B3 |
| `uv_mark_seams` / `uv_mark_seam` | B4 | B3 |
| `shape_key_create_arkit_set` | B3 | B7 |
| `modifier_apply` / `modifier_apply_all` | B2 (`apply_all`) + B6 (`apply` single) | both names ship |
| `render_set_engine` | B9 | B6 alias `render_engine_set` |

When adding a tool, write its handler under the **canonical owner** group; cross-reference from other pipeline docs.

---

## How to add a new tool

1. Identify the canonical owner pipeline (B1..B9).
2. Read the relevant skills: [tool-chains/SKILL.md](../../skills/tool-chains/SKILL.md), [mcp-tool-schema/SKILL.md](../../skills/mcp-tool-schema/SKILL.md), [blender-api-cheat/SKILL.md](../../skills/blender-api-cheat/SKILL.md).
3. Find inputs in [TYPE-GRAPH.md §4](TYPE-GRAPH.md) (producers of your input types).
4. Find consumers in [TYPE-GRAPH.md §4](TYPE-GRAPH.md) (consumers of your output types) — these become `relatedTools.downstream[]`.
5. Verify feasibility in [BPY-FEASIBILITY.md §2–3](BPY-FEASIBILITY.md). If 🔴, stop and discuss.
6. Implement Python handler in `BlenderAgent/handlers/<domain>.py` with `@handler("POST", "/<domain>/<verb>")`.
7. Implement TS tool registration in `Tools/src/tools/<domain>.ts` with Zod schema and `relatedTools` populated.
8. Write integration test in `Tools/test/tools/<tool>.test.ts` covering happy path + every `errorCode` + idempotency + cleanup.
9. Run `cd Tools && npm run build && npm test`.
10. Append to this catalog under the right pipeline section.
