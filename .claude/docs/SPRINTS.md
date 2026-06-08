# SPRINTS.md

Active sprint tasks. **This file is the source of truth for what to work on.** [ROADMAP.md](../../ROADMAP.md) is the phase-level plan; this is the actionable breakdown of the current sprint.

## Task format

```markdown
- [ ] **SN-XX** One-line description — include done criteria inline
  _(requires SN-YY)_
  ⚠️ Note: one-line warning about a non-obvious constraint
  🔍 Research first: one-line of what to verify before writing code
```

`N` = sprint number, `XX` = zero-padded task number. Mark done with `[x]` and `<!-- done: YYYY-MM-DD -->` at the end of the line.

---

## Sprint 0 — Bootstrap (done)

Goal: a green Vitest test that spawns headless Blender, calls `server_status`, asserts the version. Everything required to make that pass — nothing more.

### Addon

- [x] **S0-01** Create `BlenderAgent/__init__.py` with `bl_info` dict (name, version `(0, 0, 1)`, blender `(4, 2, 0)`, category `"Development"`) and `register()` / `unregister()` calling into `server.start()` / `server.stop()`. <!-- done: 2026-06-08 -->

- [x] **S0-02** Create `BlenderAgent/server.py` with the threading + drain pattern: `ThreadingHTTPServer` on a background thread, `queue.Queue` of jobs, `bpy.app.timers.register(_drain, persistent=True)`. <!-- done: 2026-06-08 -->

- [x] **S0-03** Create `BlenderAgent/handlers/__init__.py` + server status handler returning version/scene/mode. <!-- done: 2026-06-08 -->

### TypeScript bridge

- [x] **S0-04** `Tools/package.json` with `"type": "module"`, scripts, deps. <!-- done: 2026-06-08 -->

- [x] **S0-05** `Tools/tsconfig.json` with `strict: true`, `module: "NodeNext"`, `target: "ES2022"`. <!-- done: 2026-06-08 -->

- [x] **S0-06** `Tools/src/types.ts` with `ToolResult<T>` exported. <!-- done: 2026-06-08 -->

- [x] **S0-07** `Tools/src/blender-bridge.ts` with `blenderGet` / `blenderPost`, headless spawn, binary autodetect. <!-- done: 2026-06-08 -->

- [x] **S0-08** `Tools/src/tools/server.ts` registering `server_status`, `server_handlers`, `server_shutdown`. <!-- done: 2026-06-08 -->

- [x] **S0-09** `Tools/src/index.ts` boots `McpServer` over stdio. <!-- done: 2026-06-08 -->

### Tests

- [x] **S0-10** `Tools/vitest.config.ts` with 120s testTimeout, single-fork pool. <!-- done: 2026-06-08 -->

- [x] **S0-11** `Tools/test/bootstrap.ts` spawning headless Blender via `serve_blocking()`. <!-- done: 2026-06-08 -->

- [x] **S0-12** `Tools/test/tools/server-status.test.ts` asserting version starts "4." and core handlers are registered. <!-- done: 2026-06-08 -->

### CI + repo polish

- [x] **S0-13** `.github/workflows/ci.yml` matrix (ubuntu/windows/macos) installing Blender 4.2 LTS, running build + tests. <!-- done: 2026-06-08 -->

- [x] **S0-14** `CONTRIBUTING.md` short — link to CLAUDE.md, explain dual harness, explain `dev`-only workflow. <!-- done: 2026-06-08 -->

- [ ] **S0-15** First green CI tag `v0.0.1-bootstrap` on `dev`.

---

## Sprint 1 — Scene & object control

Planned after S0 lands. Will be expanded then. Outline (re-derived from the [research catalog](research/TOOL-CATALOG.md) — see [ADR-012](DECISIONS.md) for tool layering):

Scope = **B1 + part of B9** (~22 tools):
- Scene/collection/view-layer CRUD (B1 §1–2, §15; B9.D1–D5): `scene_create`, `scene_set_active`, `collection_create`, `collection_move_objects`, `view_layer_create`, `scene_set_unit_scale_for_modular_kit`, `view_layer_create_for_export`.
- Object primitives (B1 §3–6): `object_add_blockout`, `object_set_transform`, `object_duplicate_linked`, `mesh_set_origin_to_snap_corner`.
- Material + UV smoke pass (B1 §9–11): `material_create_procedural_grid`, `material_assign_slot`, `uv_unwrap_smart_project`.
- File IO (B9.E1–E6): `file_save`, `file_save_as`, `file_open`, `file_append_data`, `file_pack_all`, `file_unpack_all`.
- Collision + export smoke (B1 §7, §12–14): `collision_add_convex_hull`, `export_fbx_static`, `export_fbx_collection_batch`.

Each tool gets `Tools/test/tools/<tool>.test.ts` per the contract. End-of-sprint demo recreates [Recipe 4: level_modular_kit_bake_export](research/WORKFLOW-RECIPES.md#recipe-4-level_modular_kit_bake_export) in one chat.

---

## Sprint 2 — Modeling, rigging, animation (~80 tools)

Outline (B2 + B3 + B7 + B8):
- Hard-surface modifier stack (B2): all `mesh_*_modifier_add`, `mesh_validate_topology`, `mesh_validate_for_export_ue5`, `modifier_apply_all`.
- Mesh-edit primitives (B2 §13–17): `mesh_mark_sharp`, `mesh_bevel_edge_single`, `mesh_extrude_faces`, `mesh_inset_faces`, `mesh_bridge_edge_loops`, `mesh_duplicate_for_lod`.
- Collision composites (B2 §23–24): `mesh_create_collision_box`, `mesh_create_collision_convex`.
- Sculpt deterministic ops (B3 §3–10): `modifier_add_multires`, `sculpt_mode_toggle`, `sculpt_remesh_voxel`, `sculpt_symmetrize`, `sculpt_filter_apply`, `sculpt_set_brush_param`, `sculpt_brush_stroke_deterministic`, `sculpt_mask_create_from_cavity`.
- Retopo + shape keys (B3 §11–16): `retopo_create_base_cage`, `shape_key_create_basis`, `shape_key_add`, `shape_key_create_arkit_set`, `shape_key_set_value`, `shape_key_add_driver`.
- Full rigging suite (B7.A–B7.I): all 30 tools — armature, bone, constraints, drivers, vertex groups, bone collections, sockets, MetaHuman face validate, mesh→armature parenting.
- Animation authoring + NLA + retarget (B8.A–B8.C): `action_create`, `keyframe_insert_bone`, `keyframe_insert_object`, `fcurve_set_keyframe_values`, `fcurve_add_modifier`, `nla_track_create_and_push_action`, `nla_bake_to_action` ⭐, `armature_retarget_to_ue5_mannequin` ⭐.

End-of-sprint demo: [Recipe 1: character_export_ue5_skeletal](research/WORKFLOW-RECIPES.md#recipe-1-character_export_ue5_skeletal) + [Recipe 2: character_retarget_to_ue5_mannequin](research/WORKFLOW-RECIPES.md#recipe-2-character_retarget_to_ue5_mannequin).

---

## Sprint 3 — Materials, shaders, geometry nodes, UV/bake (~70 tools)

Outline (B4 + B5 + B6):
- UV pipeline (B4 §1–7, §17–25): all UV ops + validation.
- Bake pipeline (B4 §8–16, §26–28): `bake_image_create`, `bake_normal`/`bake_roughness`/`bake_metallic`/`bake_diffuse`/`bake_ao`/`bake_curvature`/`bake_position`, `image_save_render`, `cage_object_create`, `bake_pbr_set` ⭐, `bake_normal_high_to_low` ⭐.
- Material + shader (B5): all 23 tools — Principled, Image Texture, Normal Map, Mapping, Noise, Voronoi, ColorRamp, Mix Shader, Node Group create/instantiate, per-face material, `material_create_pbr_for_ue` ⭐, `material_create_foliage_two_sided` ⭐, `material_create_decal_alpha_clip` ⭐, validation, snapshot.
- Geometry Nodes (B6 §1–11, §17–22): tree CRUD, modifier attach, node create/link/input, `geo_node_instance_on_points_setup` ⭐, `geo_node_distribute_points_density_attribute`, `geo_node_capture_attribute`, `geo_node_store_named_attribute`, `geo_node_realize_instances`, `modifier_apply`, `modifier_list_get`, `geo_node_mesh_primitive_create` ⭐, `geo_node_attribute_mix`.
- Compositor (B6 §12–16): `compositor_enable`, `compositor_node_add`, `compositor_node_set`, `compositor_link_create`, `compositor_render_frame`.

End-of-sprint demo: [Recipe 5: prop_high_to_low_bake_export](research/WORKFLOW-RECIPES.md#recipe-5-prop_high_to_low_bake_export) + [Recipe 6: procedural_foliage_scatter_export](research/WORKFLOW-RECIPES.md#recipe-6-procedural_foliage_scatter_export).

---

## Sprint 4 — Lighting / camera / render / export (~50 tools)

Outline (B8.D–B8.F + B9.A–B9.D + remaining exports):
- Lights + world (B9.A): `light_create`, `light_set_area_shape`, `light_configure_linking`, `light_create_group`, `world_set_hdri`.
- Cameras (B9.B): `camera_create`, `camera_set_dof`, `camera_set_clipping`, `camera_set_active`.
- Render (B9.C): `render_set_engine`, `render_configure_cycles`, `render_configure_eevee_next`, `render_set_output`, `render_still_image`, `render_animation`, `viewport_screenshot`.
- Library + asset (B9.D6–D11): `library_link`, `library_make_override`, `library_resync`, `library_make_local`, `asset_mark`, `asset_unmark`.
- Export remainder (B8.D–B8.E): `export_fbx_skeletal` ⭐, `export_fbx_animation` ⭐, `export_gltf_skeletal`, `export_alembic_hair`, `export_usd_skeletal`, `export_obj_static`, `export_bvh_animation`, all `import_*` counterparts, `blend_open`, `blend_save`.
- Final B6 composites: `geo_node_simulation_zone_setup` is deferred to v1.1 per [ADR-013](DECISIONS.md).

End-of-sprint demo: [Recipe 7: cinematic_render_sequence](research/WORKFLOW-RECIPES.md#recipe-7-cinematic_render_sequence) + [Recipe 8: animation_bake_export_gltf](research/WORKFLOW-RECIPES.md#recipe-8-animation_bake_export_gltf) + UE5 ingestion smoke test via `mcp-unreal-agent`.

---

## Sprint 5 — Polish + install + ship

Outline:
- `exec_python` + `get_python_console_output` behind `BLENDER_AGENT_ALLOW_EXEC=1` per [ADR-008](DECISIONS.md).
- Install brain finalized (`install/AGENT-INSTALL.md` and `install/context-skill/`).
- All 8 recipes from [WORKFLOW-RECIPES.md](research/WORKFLOW-RECIPES.md) covered by `Tools/test/recipes/*.test.ts`.
- Demo videos.
- v1.0.0 tag.

---

## Done log

### 2026-06-08 — bulk delivery (S0–S5 scaffold)

All structural work for Sprints 0–5 landed in a single push. Per-tool tests follow incrementally.

**Sprint 0** — S0-01 through S0-13 done. CONTRIBUTING (S0-14) and `v0.0.1-bootstrap` tag (S0-15) still pending.

**Sprint 1** — scene/collection/view-layer/file-IO CRUD, object primitives + collision + UV smart-project, procedural grid material + slot assign, `export_fbx_static` + `export_fbx_collection_batch`. Integration tests: `scene-blockout.test.ts`, `export-fbx.test.ts`, `file-io.test.ts`.

**Sprint 2** — modifier add/set/apply/remove/list/reorder, mesh-edit primitives (extrude/bevel/loop-cut/subdivide/merge/shade/normals/triangulate/join/separate), armature + bone + bone-collection + constraint + driver + vertex-group + shape-key suites, MetaHuman ARKit-52 ensure (idempotent), animation + NLA push. Integration tests: `modifier-mesh.test.ts`, `armature-bone.test.ts`, `metahuman.test.ts`, `animation.test.ts`.

**Sprint 3** — UV pipeline (unwrap/smart-project/pack-islands/seams/validate), bake setup + run + image save, shader-node add/connect/set, node-group create/instance, Geometry Nodes group + node + connect + apply-to-object, Compositor enable + node + connect. Integration tests: `material-shader.test.ts`, `geo-node-compositor.test.ts`.

**Sprint 4** — light + world + camera + render (engine/resolution/still/animation), library link/override/reload, asset mark/clear, full export remainder (gltf, fbx_skeletal, fbx_animation), import_fbx/obj/gltf. Integration test: `render.test.ts`.

**Sprint 5 (partial)** — `exec_python` env-flagged with `EXEC_PYTHON_DISABLED` default, install harness (`install/INSTALL.md`, `install/AGENT-INSTALL.md`, `install/PROMPT-TEMPLATES.md`), recipe tests landed: `recipe-03-metahuman-face.test.ts`, `recipe-04-level-modular-kit.test.ts`, `recipe-08-animation-bake-export.test.ts`. Recipes 1, 2, 5, 6, 7 remain.

**Build status:** `cd Tools && npm run build` exits 0. **Real-world validation: 39/39 tool tests + 3/3 recipe tests passing on Blender 5.1.2 (Steam install, port 9877 coexisting with ahujasid blender-mcp on 9876).** CI matrix (ubuntu/windows/macos) installs Blender 4.2 LTS for upstream parity.
