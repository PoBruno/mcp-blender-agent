# Research INDEX

The complete v1.0 design study for `mcp-blender-agent` — what we will build, why each tool is feasible, how tools chain, and what end-to-end recipes look like.

This package is **authoritative for tool design**. Sprint planning, ADRs, and ROADMAP counts all derive from these docs. When in doubt about scope or feasibility, read here first.

---

## Read in this order

1. **[UE-TARGETS.md](UE-TARGETS.md)** — what UE5 needs from us. Axes, units, SK_Mannequin hierarchy, A-pose, collision prefixes, ARKit-52, LOD groups, Nanite/Lumen caps, full FBX exporter param matrix, per-export-class verify checklist. **Start here.** Everything downstream serves these contracts.

2. **[WORKFLOWS.md](WORKFLOWS.md)** — how the 9 pipelines depend on each other. Single Mermaid dependency diagram, canonical orderings per pipeline, cross-domain seams (B3→B7, B7→B8, B4→B5, etc.), 8 end-to-end recipe names, universal constraints, modal blockers table.

3. **[BPY-FEASIBILITY.md](BPY-FEASIBILITY.md)** — the cross-cutting feasibility crosswalk. Aggregate verdict (162 🟢 / 51 🟡 / 15 🔴), the 15 red blockers with workarounds, the yellow constraints (context overrides, mode switches, 4.0+ API changes, fragile drivers, bake quirks, library override fragility, USD stability), the green core.

4. **[TYPE-GRAPH.md](TYPE-GRAPH.md)** — the entity dependency map. 25 entity types organized by domain (Scene infra, Object/geometry, Armature/rigging, Materials/shader nodes, GN/Compositor, Animation, Resources), Mermaid graph of ownership and reference edges, ID-chain examples for the 5 most common end-to-end flows, producer↔consumer matrix per entity type, UE/Blender naming conventions, scoping rules.

5. **[TOOL-CATALOG.md](TOOL-CATALOG.md)** — the complete 228-tool inventory. Stats table, per-pipeline list (every tool with status + one-line purpose + canonical owner), cross-pipeline alias map, "how to add a new tool" procedure.

6. **[WORKFLOW-RECIPES.md](WORKFLOW-RECIPES.md)** — 8 hand-authored end-to-end recipes. Each is a chained sequence of tool calls from "empty .blend" to "UE5-usable asset" with UE5-side verification checklist. These become the v1.0 integration test suite.

7. **[pipelines/](pipelines/)** — the 9 per-pipeline research reports. Each has §1 workflow + §2 API details + §3 feasibility verdict table + §4 entity types + §5 open questions + §6 tool catalog with full schemas.

---

## The 9 pipelines

| File | Domain | Tool count | v1.0 ready | Smoke recipe |
|---|---|---|---|---|
| [B1-environment-kits.md](pipelines/B1-environment-kits.md) | Modular level kits (UE5 cm units, grid origins, batch export) | 16 | 15 | [Recipe 4](WORKFLOW-RECIPES.md#recipe-4-level_modular_kit_bake_export) |
| [B2-hard-surface-props.md](pipelines/B2-hard-surface-props.md) | Hard-surface props (modifier stack, LOD, collision, PBR) | 28 | 24 | [Recipe 5](WORKFLOW-RECIPES.md#recipe-5-prop_high_to_low_bake_export) |
| [B3-organic-character.md](pipelines/B3-organic-character.md) | Organic / character (sculpt deterministic ops, retopo, ARKit shape keys) | 21 | 17 | part of [Recipe 1](WORKFLOW-RECIPES.md#recipe-1-character_export_ue5_skeletal) |
| [B4-uv-and-baking.md](pipelines/B4-uv-and-baking.md) | UV + bake (texture production, cage, PBR set bake) | 22 | 22 | part of [Recipe 5](WORKFLOW-RECIPES.md#recipe-5-prop_high_to_low_bake_export) |
| [B5-materials-shaders.md](pipelines/B5-materials-shaders.md) | Materials / shader nodes (Principled BSDF, procedural, node groups) | 24 | 23 | part of [Recipe 5](WORKFLOW-RECIPES.md#recipe-5-prop_high_to_low_bake_export) |
| [B6-geometry-nodes-compositor.md](pipelines/B6-geometry-nodes-compositor.md) | Geometry Nodes + Compositor (scatter, realize, render passes) | 22 | 20 | [Recipe 6](WORKFLOW-RECIPES.md#recipe-6-procedural_foliage_scatter_export) |
| [B7-rigging-metahuman.md](pipelines/B7-rigging-metahuman.md) | Rigging + MetaHuman face (UE5 Mannequin, ARKit-52, drivers, sockets) | 31 | 31 | part of [Recipe 1](WORKFLOW-RECIPES.md#recipe-1-character_export_ue5_skeletal) + [Recipe 3](WORKFLOW-RECIPES.md#recipe-3-metahuman_face_blendshapes_setup) |
| [B8-animation-export.md](pipelines/B8-animation-export.md) | Animation + retarget + granular export (FBX/glTF/USD/Alembic/OBJ/BVH) | 25 | 25 | [Recipe 2](WORKFLOW-RECIPES.md#recipe-2-character_retarget_to_ue5_mannequin) + [Recipe 8](WORKFLOW-RECIPES.md#recipe-8-animation_bake_export_gltf) |
| [B9-lighting-camera-render-scene.md](pipelines/B9-lighting-camera-render-scene.md) | Lighting / camera / render / scene / library / file IO | 34 | 33 (+ 1 env-flagged) | [Recipe 7](WORKFLOW-RECIPES.md#recipe-7-cinematic_render_sequence) |
| **Totals** | | **228** | **210 + 5 deferred + 15 RED out-of-scope** | 8 recipes |

---

## Key research-driven decisions

These ADRs in [DECISIONS.md](../DECISIONS.md) were added as a direct result of this research:

- **[ADR-008](../DECISIONS.md)** — `exec_python` opt-in behind `BLENDER_AGENT_ALLOW_EXEC=1`.
- **[ADR-009](../DECISIONS.md)** — MetaHuman face = ARKit-52 in v1.0; full DNA rig deferred to v1.1+.
- **[ADR-010](../DECISIONS.md)** — Sculpt boundary: ship deterministic ops + setup; freehand strokes stay human.
- **[ADR-011](../DECISIONS.md)** — Library Override: ship 4 primitives; conflict resolution stays human.
- **[ADR-012](../DECISIONS.md)** — Tool layering: canonical owner pipeline per tool + cross-references.
- **[ADR-013](../DECISIONS.md)** — Tool count target = 228 (was estimated as ~140); supersedes implicit count in ROADMAP.

---

## What's not in this package

- **No code.** This is design research. Implementation begins in Sprint 1.
- **No `bpy` API verification logs.** We assume 4.2 LTS API surface based on Blender Foundation docs + cross-referencing `ref/blender-mcp` and `ref/blender-ai-mcp` patterns. Verification happens in integration tests as each tool ships.
- **No performance benchmarks.** Will be measured as tools ship; recorded in HISTORY.md.
- **No installer / packaging plan.** That's Phase 5 work and lives in [`install/`](../../../install/).

---

## How to consume this package

- **Agent doing sprint planning:** read [SPRINTS.md](../SPRINTS.md) (already references this package) + [ROADMAP.md](../../../ROADMAP.md). The per-sprint scope is derived from the catalog.
- **Agent implementing a tool:** TOOL-CATALOG → find canonical owner → read that pipeline's §6 entry → check BPY-FEASIBILITY → trace TYPE-GRAPH → write Zod schema + Python handler + integration test.
- **Agent writing an end-to-end test:** WORKFLOW-RECIPES → pick a recipe → translate to vitest steps + UE5 verification checks.
- **Human reviewing scope:** UE-TARGETS (what we owe UE5) → WORKFLOWS (how it all fits) → BPY-FEASIBILITY (what's risky).
