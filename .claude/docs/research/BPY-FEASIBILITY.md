# BPY-FEASIBILITY.md

The crosswalk between what an artist does in Blender and what an agent driving `bpy` can actually do deterministically.

Three verdicts:
- **🟢 Green** — deterministic, headless-friendly, no surprises. Ship in v1.0.
- **🟡 Yellow** — feasible but with a constraint (mode switch, context override, brittle API, performance, version-specific naming). Ship in v1.0 with the constraint documented.
- **🔴 Red** — fundamentally modal / interactive / out-of-scope. Either ship a setup-only tool, defer to v1.1, or document as an explicit non-goal.

Full per-step verdicts and notes live in each pipeline file's §3 (Feasibility Verdict Table). This file is the **cross-cutting summary** and the **single source of truth on what we can and cannot ship**.

---

## 1. The aggregate verdict

Synthesizing all nine pipeline reports:

| Domain | Tools proposed | 🟢 Green | 🟡 Yellow | 🔴 Red | Net v1.0 ready |
|---|---|---|---|---|---|
| B1 Environment kits | ~16 | 11 | 4 | 1 | ✅ Yes |
| B2 Hard-surface props | 28 | 20 | 5 | 3 | ✅ Yes |
| B3 Organic / character | 21 | 12 | 5 | 4 | ⚠️ Partial — sculpt boundary |
| B4 UV + bake | ~22 | 16 | 6 | 0 | ✅ Yes |
| B5 Materials / shaders | 24 | 18 | 5 | 1 | ✅ Yes |
| B6 Geometry Nodes + Compositor | ~22 | 16 | 4 | 2 | ✅ Yes (simulation zones → v1.1) |
| B7 Rigging + MetaHuman face | 37 | 22 | 12 | 3 | ✅ Yes (face DNA rig → v1.1) |
| B8 Animation + retarget + export | 25 | 22 | 3 | 0 | ✅ Yes |
| B9 Lighting / camera / render / scene | ~33 | 25 | 7 | 1 | ✅ Yes (`exec_python` opt-in) |
| **Totals** | **~228** | **~162** | **~51** | **~15** | **~213 of 228 ship in v1.0** |

Roughly **93%** of the proposed surface is shippable in v1.0. The remaining 7% is either deferred to v1.1 (simulation zones, full FACS face rig, advanced retopo) or shipped as setup-only with the modal step left to the human.

---

## 2. The 🔴 Red blockers — what the agent fundamentally cannot do

These are **modal-only Blender operators** that require live mouse/screen-space input and cannot be replayed deterministically. The agent's role is **setup + verify**, never **execute the modal step**.

| # | Operation | Pipeline | Root cause | Workaround the agent ships |
|---|---|---|---|---|
| 1 | Freehand sculpt brush strokes | B3 | `bpy.ops.sculpt.brush_stroke` requires live mouse events | Ship `sculpt_brush_stroke_deterministic` (replay a pre-recorded stroke list as `OperatorStrokeElement[]` — feasibility verify in 4.2). Ship all non-modal sculpt ops (`sculpt_remesh_voxel`, `sculpt_symmetrize`, `sculpt_filter_apply`, `sculpt_mask_create_from_cavity`). Sculpting "by feel" stays with the human. |
| 2 | Freehand weight paint brush strokes | B7 | Modal brush, live mouse | Ship `vertex_group.add(indices, weight, type='REPLACE')` for data-level weight assignment. Ship `vertex_group_auto_weight_from_armature` (calls `bpy.ops.object.parent_set(type='ARMATURE_AUTO')`). Human paints; agent assigns. |
| 3 | Texture painting | B5 | Modal brush, live mouse | Out of scope — agent doesn't paint. Use B4 bake to capture surface detail deterministically. |
| 4 | Polybuild (retopo) | B3 | Modal brush in Edit Mode | Out of scope as a primary path. Ship `shrinkwrap` + `bmesh` manual topo build as the agent path. Optional v1.1: external retopo addon subprocess (Instant Meshes / TopoGun). |
| 5 | Knife tool (interactive) | B2 | Modal — Ctrl+click face | Use `bpy.ops.mesh.bisect` (non-modal, takes plane params). Use `bmesh.ops.split_edges` for surgical cuts. |
| 6 | Modal Bevel / Loop Cut (drag to confirm) | B2 | Both have modal forms | Both also accept explicit numeric params: `bpy.ops.mesh.bevel(width=0.05, segments=2)` and `bpy.ops.mesh.loopcut_slide(MESH_OT_loopcut={'number_cuts': 1})`. **Verify in 4.2 — keyword vary by version.** |
| 7 | 3D Viewport gizmos / dragging | All | Live screen interaction | Replace with explicit `obj.matrix_world = ...` or `bpy.ops.transform.translate(value=(x,y,z))`. |
| 8 | Full FACS / DNA face rig (MetaHuman style) | B7 | ~400-joint rig + RBF solvers; tooling is Maya/Houdini only | v1.0 ships ARKit-52 shape-key path (`shape_key_create_arkit_set` + drivers). Full DNA rig deferred to v1.1, possibly via external subprocess. |
| 9 | GN Simulation Zones (4.0+) frame-loop | B6 | Frame-by-frame eval needs deep main-thread integration | Defer to v1.1. Ship static/single-frame GN tools first. |
| 10 | Bent Normal bake (full ray-march) | B4 | Not natively supported in Blender | Document as "UE-side post-process" via blending Normal × AO. Or optional `exec_python` ray-march (slow). |
| 11 | True trim-sheet UV pack with locked rows | B1 | `bpy.ops.uv.pack_islands` has limited locking | Ship `uv_align_island_to_trim_row` composite that places islands into known rows manually. Don't pretend pack does row-locking. |
| 12 | Library Asset Browser drag-drop | B9 | UI interaction | Ship `asset_mark` / `asset_unmark` data tools. Browser interaction is UI-only. |
| 13 | Interactive 3D decal projection | B1 | Modal projection workflow | Out of scope; use pre-authored GN decal templates with exposed parameters, or material alpha-clip on a flat plane. |
| 14 | `exec_python(code: str)` exposed by default | B9 | Trivial-but-dangerous arbitrary execution path | Ship **only behind `BLENDER_AGENT_ALLOW_EXEC=1`** env flag. Never default. See [DECISIONS.md ADR-008](../DECISIONS.md). |
| 15 | Real-time viewport playback (animation review) | B8/B9 | UI-only | Ship `render_animation` instead (produces frames the agent can inspect). |

---

## 3. The 🟡 Yellow constraints — feasible but conditional

These tools ship in v1.0 but the constraint must be documented in the tool description and enforced in the test suite.

### 3.1 Context-override constraints (3D View or UV Editor required)

Many operators that "look" data-driven actually require a live 3D View or UV Editor area to execute (`bpy.ops.uv.smart_project`, `bpy.ops.uv.project_from_view`, `bpy.ops.object.duplicate(linked=True)`, `bpy.ops.object.collection_instance_add`, `bpy.ops.view3d.camera_to_view_selected`, etc.).

**Pattern:** the agent's handler must obtain a 3D View context via `bpy.context.temp_override(area=..., region=...)`. In headless mode (`blender --background`), the agent must synthesize a temporary window + screen + area. See [ARCHITECTURE.md §4](../ARCHITECTURE.md) for the marshalling pattern.

**Affected tools:** `uv_smart_project`, `uv_project_from_view`, `object_duplicate_linked`, `collection_instance_create`, `mesh_bridge_edge_loops`, `camera_to_view_selected`, `viewport_screenshot`, ~12 others. All flagged with `errorCode: CONTEXT_OVERRIDE_FAILED` in their entries.

### 3.2 Mode-switch constraints (Edit / Pose / Sculpt / Weight Paint)

Mesh editing requires Edit Mode on the mesh. Bone editing requires Edit Mode on the armature. Pose-mode constraints work in either Pose or Object mode (data API), but interactive verification requires Pose Mode.

**Pattern:** every mode-sensitive tool wraps in a `with_mode(obj, 'EDIT', lambda: ...)` helper that records previous mode, switches, mutates, restores. See [.claude/rules/python-blender.md](../../rules/python-blender.md).

**Affected tools:** `bone_add`, `bone_set_head_tail`, `bone_set_roll`, `bone_set_parent`, `armature_symmetrize`, all `mesh_*` Edit Mode primitives, `uv_mark_seams`, etc.

### 3.3 API surface changed in 4.0+ (bone collections, node interface)

| API | Pre-4.0 | 4.0+ | Affected tools |
|---|---|---|---|
| Bone layers | `bone.layers[32]` (bitmask) | `armature.collections.new(name)` + `collection.assign(bone)` | All B7 `bone_collection_*` tools |
| Node-tree inputs/outputs | `node_tree.inputs.new(...)` / `outputs.new(...)` | `node_tree.interface.new_socket(name, in_out='INPUT', socket_type='NodeSocketFloat')` | `node_group_create`, `node_group_add_interface_socket`, all GN group tools |
| Auto-smooth | `mesh.use_auto_smooth = True` + `auto_smooth_angle` | "Smooth by Angle" Geometry Nodes modifier (4.1+) | `mesh_smooth_by_angle_modifier_add` |
| Musgrave shader node | `ShaderNodeTexMusgrave` | Removed in 4.1; use Noise/Voronoi with feature param | `shader_node_add_noise_texture`, `shader_node_add_voronoi_texture` |
| EEVEE engine | `'BLENDER_EEVEE'` | `'BLENDER_EEVEE_NEXT'` (4.2+) | `render_set_engine`, `render_configure_eevee_next` |

The agent is **locked to Blender 4.2 LTS+** (see [DECISIONS.md ADR-002](../DECISIONS.md)). Pre-4.0 paths are out of scope and not tested.

### 3.4 Driver expressions (fragile; pre-fill templates)

Drivers are F-curves with a Python expression. Hand-authored expressions are error-prone (`ZeroDivisionError`, `NameError` for missing vars).

**Pattern:** the agent ships templated expressions only (e.g., `var * 0.5`, `clamp(var, 0, 1)`). Tools like `shape_key_add_driver`, `driver_add_from_bone_rotation` expose a `multiplier` numeric param, not a free-text expression. Free-text drivers are gated behind `BLENDER_AGENT_ALLOW_EXEC=1` (same flag as `exec_python`).

### 3.5 Cycles + bake quirks

- `bpy.ops.object.bake(type=...)` reads the **selected and active Image Texture node** in the object's material. Tools must set the node selection + active state internally before calling. Missing this → silent bake failure or `NO_IMAGE_NODE_ACTIVE` error.
- Cage object for normal baking **must have identical topology** to the low-poly. The `cage_object_create` composite duplicates the low-poly + applies a Solidify modifier with small thickness.
- Bake can be slow (10s–10min). The handler must run on the main thread with no timeout, or stream progress.

### 3.6 Library Override fragility

- Library Override lets a linked datablock be edited locally. But: upstream changes to the linked file can break the override — Blender's resync logic helps but isn't perfect.
- The agent ships `library_link` / `library_make_override` / `library_resync` / `library_make_local` as primitives. The override-edit step is the user's responsibility; the agent doesn't try to auto-resolve override conflicts. See [DECISIONS.md ADR-009](../DECISIONS.md).

### 3.7 USD export stability

Blender's USD support is stable in 4.2 LTS but historically had bugs in 3.x. Tools are flagged 🟡 with the note "Blender 4.2+ required". Older Blenders will fail with `USD_VERSION_UNSUPPORTED`.

### 3.8 Composite render in headless

`bpy.ops.render.render(write_still=True)` works in headless but may need a `bpy.context.temp_override()` for some EEVEE-Next operations. `compositor_render_frame` flagged 🟡 — verify in test harness.

---

## 4. The 🟢 Green core — what ships effortlessly

The bulk of the v1.0 surface (~162 tools). The pattern is consistent: **data-block CRUD** via `bpy.data.*` plus **type-stable operators** (`bpy.ops.mesh.primitive_cube_add`, `bpy.ops.export_scene.fbx`, `bpy.ops.object.modifier_apply`, etc.).

What goes green effortlessly:
- All scene / collection / view-layer CRUD.
- All material / shader-node CRUD (Principled BSDF, Image Texture, Mapping, Normal Map, ColorRamp, Mix Shader, Noise/Voronoi).
- All armature data API (create armature, add bones, set head/tail/roll/parent, mirror).
- All pose-mode constraint API (IK, Copy Rotation/Location, Limit Rotation, Track To, etc.).
- All animation API (Action create, keyframe insert per data_path, F-curve modifiers, NLA push, bake action).
- All export operators with full parameter coverage (FBX, glTF, USD, Alembic, OBJ, BVH).
- All shape-key API (add, set value, drivers, ARKit-52 set generation).
- All vertex-group data-level API (group.add(indices, weight)).
- All Geometry Node tree CRUD (create tree, attach modifier, add nodes, link nodes, set interface sockets).
- All Compositor tree CRUD.
- File IO (save, save-as, open, append, pack/unpack).
- Render still / animation / viewport screenshot (with context override).

The agent is in good shape on `bpy`. The risks are concentrated in the 🟡 column.

---

## 5. Threading + main-thread constraints (apply to everything)

`bpy` is not thread-safe. Every tool, regardless of feasibility verdict, runs on the main thread via the `bpy.app.timers.register(drain, persistent=True)` pattern. The HTTP handler thread enqueues a callable + blocks on a `threading.Event` until the main-thread drain executes it. See [ARCHITECTURE.md §3](../ARCHITECTURE.md).

This means:

- **No tool can parallelize internally.** Within a tool, all `bpy.*` calls are sequential on the main thread.
- **Tools can be called concurrently** by the agent — the addon serializes them via the drain queue.
- **Long-running tools** (sculpt remesh, large bakes, render animation) **block the queue** until they finish. The handler must signal progress where possible.

---

## 6. Per-domain feasibility tables (canonical)

The detailed step-level verdicts live in each pipeline file. Click through for the full breakdown:

- [B1 Environment kits — §3](pipelines/B1-environment-kits.md)
- [B2 Hard-surface props — §3](pipelines/B2-hard-surface-props.md)
- [B3 Organic / character — §3](pipelines/B3-organic-character.md)
- [B4 UV + bake — §3](pipelines/B4-uv-and-baking.md)
- [B5 Materials / shaders — §3](pipelines/B5-materials-shaders.md)
- [B6 Geometry Nodes + Compositor — §3](pipelines/B6-geometry-nodes-compositor.md)
- [B7 Rigging + MetaHuman face — §3](pipelines/B7-rigging-metahuman.md)
- [B8 Animation + retarget + export — §3](pipelines/B8-animation-export.md)
- [B9 Lighting / camera / render / scene — §3](pipelines/B9-lighting-camera-render-scene.md)
