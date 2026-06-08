# ROADMAP.md

Five phases to v1.0. Each phase ends with a green CI build, a tagged release on `dev`, and an updated demo. Phases are sequenced for **vertical slices** — each phase delivers a usable subset, not a layer.

The matching [SPRINTS.md](.claude/docs/SPRINTS.md) breaks each phase into actionable tasks (SN-XX format). When you start work, read SPRINTS.md, not this file.

**Research foundation:** the per-pipeline feasibility study lives in [`.claude/docs/research/`](.claude/docs/research/) — start with [INDEX.md](.claude/docs/research/INDEX.md). The 228-tool catalog, type graph, BPY feasibility matrix, end-to-end workflow recipes, and UE5 target spec are all there and are authoritative for sprint planning.

---

## Phase 0 — Bootstrap

**Outcome:** A round-trip "hello world". TS MCP server calls `server_status`, addon responds with Blender version + scene name.

- Repo scaffold (this commit).
- `Tools/` skeleton: `package.json`, `tsconfig.json`, `vitest.config.ts`, `src/index.ts`, `src/blender-bridge.ts`, `src/types.ts`, `src/tools/server-status.ts`.
- `BlenderAgent/` skeleton: `__init__.py` (addon registration), `server.py` (HTTP listener on `9877` with background thread + `bpy.app.timers` drain — `9876` is reserved for ahujasid's `blender-mcp`), `handlers/server_status.py`.
- One Vitest integration test: spawn `blender --background --addons BlenderAgent`, hit `/server/status`, assert version.
- CI: GitHub Actions matrix Windows + macOS + Linux against Blender 4.2 LTS.
- Install brain skeleton — detect Blender version only, no real installation yet.

**Done when:** `npm run build && npm test` passes locally and in CI.

---

## Phase 1 — Core scene & object control (~30 tools)

**Outcome:** The agent can inspect and manipulate the scene graph end-to-end.

- **Scene group** (`scene_*`, ~10 tools): list/create/delete scenes and collections, link objects to collections, get/set world background.
- **Object group** (`object_*`, ~12 tools): list, create (mesh/empty/camera/light/curve/armature), delete, duplicate, rename, transform, parent, visibility, apply transform, select.
- **Mesh inspect** (`mesh_*` read-only, ~8 tools): get info, list vertices/edges/faces, list vertex groups, list UV maps, list shape keys.
- Main-thread marshalling policy locked.
- Context-override helper finalized.
- Composite-flow undo pattern locked: data mutation + single `undo_push` at end.

**Done when:** demo "create cube, parent to empty, transform, list scene" works in Copilot chat.

---

## Phase 2 — Modeling, rigging & animation (~40 tools)

**Outcome:** The agent can build and rig a low-poly character.

- **Mesh edit** (`mesh_*` mutations, ~8 tools): extrude, delete geometry, subdivide, select-by-index, vertex/edge/face mutations via `bmesh`.
- **Modifier group** (`modifier_*`, ~8 tools): add, list, get, set property, reorder, apply, remove. Cover subdivision, mirror, array, solidify, boolean, decimate, bevel.
- **Constraint group** (`constraint_*`, ~6 tools): add, list, set target, set property, remove.
- **Armature group** (`armature_*`, `bone_*`, `socket_*`, ~14 tools): list armatures, add/remove/rename bones, set roll/transform/parent, add empty-socket parented to bone, copy bones/sockets between armatures.
- **Animation group** (`action_*`, `keyframe_*`, `nla_*`, `driver_*`, ~14 tools): list actions, assign action, add/remove/move keyframes, set interpolation, add NLA strips, bake, add drivers.

**Done when:** demo "build a stick-figure character with idle animation" works in one chat.

---

## Phase 3 — Materials, shader & geometry nodes (~30 tools)

**Outcome:** The agent can author procedural materials and geometry node graphs.

- **Material group** (`material_*`, ~10 tools): list, create, assign to slot, list slots, set Principled params, validate, snapshot, diff.
- **Shader node group** (`shader_node_*`, ~10 tools): get graph, add node, connect/disconnect pins, set input value, move node, delete node, create image texture + assign image.
- **Geometry Nodes group** (`geo_node_*`, ~10 tools): list node trees, get graph, add/connect/disconnect nodes, set inputs, create node group, validate.

**Done when:** demo "make a procedural moss material with noise + Principled" works in one chat.

---

## Phase 4 — Render & granular export (~30 tools)

**Outcome:** The agent has full control of every render and export parameter — the project's killer feature.

- **Camera group** (`camera_*`, ~5 tools): list, create, set focal/sensor/DoF, set active.
- **Light group** (`light_*`, ~5 tools): list, create, set type/energy/color/shadow.
- **Viewport group** (`viewport_*`, ~5 tools): get/set view, set shading mode, screenshot, view-frame-selected.
- **Render group** (`render_*`, ~5 tools): set engine, set settings (samples, resolution, frame range), render image, render animation.
- **Import group** (`import_*`, ~5 tools): FBX, glTF, OBJ, USD, Alembic — **every operator parameter typed**.
- **Export group** (`export_*`, ~6 tools): FBX, glTF, OBJ, USD, Alembic, STL — **every operator parameter typed**. This is the project's signature surface.

**Done when:** demo "build character → bake animation → export FBX with UE5-compatible settings → import into UE5 via `mcp-unreal-agent`" works end-to-end.

---

## Phase 5 — Polish, install, ship

**Outcome:** v1.0. End users install with one prompt.

- **File / session group** (`file_*`, ~6 tools): save, save-as, open, revert, list dependencies, pack/unpack external.
- **Python escape** (`exec_python`, opt-in, gated) + `get_python_console_output`.
- **Install brain finalised** — 7-phase adaptive installer mirroring `mcp-unreal-agent`'s `install/AGENT-INSTALL.md`. Detects Claude Code / Copilot / Cursor / Claude Desktop. Handles conflicts. Manages a delimited block in the user's primary instruction file.
- **Passive context skill** — `install/context-skill/{SKILL.md, instructions.md, FLOWS.md, TOOLS.md, MANAGED-BLOCK.md}`, generated `TOOLS.md` from a digest script.
- **Demo videos**: "Build a character", "Export to Unreal".
- **README + OBJECTIVES + ROADMAP** polished, cross-linked with `mcp-unreal-agent`.
- **Tag `v1.0.0` from `main`.**

---

## Milestones / dates

This is a one-developer + one-agent project. No date commitments. Phases land when the smoke demo for the phase passes. Aim is one phase every couple of weeks; if a phase takes longer it takes longer.

| Phase | Tools delivered (cumulative) | Smoke demo |
|---|---|---|
| 0 | 1 | `server_status` round-trip |
| 1 | ~30 | Create cube, parent, transform |
| 2 | ~120 | Build stick-figure with idle anim; UE5 Mannequin rig; ARKit-52 face setup |
| 3 | ~190 | Procedural moss material; node group reuse; GN forest scatter |
| 4 | ~225 | Build character, export FBX, import to UE5; bake PBR set; cinematic render |
| 5 | ~228 | One-prompt install + full demo videos; `exec_python` env-flagged opt-in |

Counts updated from the [research catalog](.claude/docs/research/TOOL-CATALOG.md) (228 tools verified across 9 pipelines). See [ADR-013](.claude/docs/DECISIONS.md) for the count revision.

---

## Beyond v1.0

Re-evaluate based on usage:

- Render farm orchestration.
- Multi-agent co-op on a shared Blender session.
- Read user-installed addon Python source (Blender twin of UE's C++ context bridge).
- Asset library integration (Poly Haven, Sketchfab) — only if not better handled by composing with `ahujasid/blender-mcp`.
- Bridge tools that chain `blender-agent → unreal-agent` and `blender-agent → unity-agent` (if a `unity-agent` exists by then).
