# DECISIONS.md

ADRs (Architecture Decision Records) for `mcp-blender-agent`. Append-only — once decided, an ADR stays. If a decision changes, add a new ADR that supersedes the old one (mark the old one with `Status: superseded by ADR-NNN`).

Format per ADR:
- **Context** — what problem are we solving and why now.
- **Decision** — what we chose.
- **Rationale** — why we chose it.
- **Alternatives considered** — what we rejected and why.
- **Consequences** — what becomes easier / harder.

---

## ADR-001: Main-thread marshalling via `bpy.app.timers`, not modal operators

**Status:** Accepted.

**Context:** `bpy` is not thread-safe. The addon's HTTP server runs on a background thread. Some mechanism must run handler bodies on the main thread.

**Decision:** Use `bpy.app.timers.register(drain, persistent=True)` polling a `queue.Queue` every ~16 ms. Handlers block on a `threading.Event` until the drain processes their job.

**Rationale:**
- Timers run regardless of UI state. Works identically in interactive editor and `--background`.
- Simpler lifecycle than modal operators (no `invoke` / `execute` / `modal` / `cancel`).
- No dependency on a focused window or specific area.
- ahujasid/blender-mcp uses the same approach (`server.execute_in_main_thread`); production-validated.

**Alternatives considered:**
- **Modal operator** — added complexity for no benefit; depends on UI events.
- **`bpy.app.handlers.depsgraph_update_post`** — only fires on data changes; useless for read-only handlers.
- **`bpy.app.handlers.frame_change_post`** — only fires during playback.

**Consequences:**
- Worst-case latency ≈ 16 ms per call (one timer tick). Acceptable for an interactive tool; assertable in tests.
- A long-running modal (sculpt brush, modal transform) can stall the drain. Handlers must return `BLENDER_TIMEOUT` after 30 s.

---

## ADR-002: Lock on Blender 4.2 LTS or newer; no 3.x support

**Status:** Accepted.

**Context:** Several core APIs changed between 3.x and 4.x: `bpy.context.temp_override` (the only sane way to override 3D View context) is 4.x+. Animation channelbags (4.4+ Action system) replace older F-curve constructions. Supporting both pre-4 and post-4 means twice the API matrix.

**Decision:** Hard-require Blender 4.2 LTS or newer. The addon's `bl_info["blender"]` is `(4, 2, 0)`. The TS server probes `bpy.app.version` on first contact and refuses to operate if older.

**Rationale:**
- 4.2 LTS is the long-term support version, supported by the Blender Foundation through 2026.
- 4.x's `temp_override` is required for any context-sensitive operator. Re-implementing the pre-4 `override` dict per operator is fragile.
- We're a new project; we don't owe backwards compatibility.

**Alternatives considered:**
- **Support 3.6 LTS too** — doubles the test matrix, blocks use of cleaner 4.x APIs.
- **Lock on latest only (4.5+)** — too restrictive for a tool meant to be installed broadly.

**Consequences:**
- We can use modern APIs everywhere.
- Users on older Blender get a clear `BLENDER_VERSION_UNSUPPORTED` error and instructions to upgrade.

---

## ADR-003: HTTP over `http.server`, not raw TCP sockets

**Status:** Accepted.

**Context:** ahujasid/blender-mcp uses a raw TCP socket with a JSON-over-newline protocol. We need to choose between that pattern and HTTP.

**Decision:** Use Python's stdlib `http.server.ThreadingHTTPServer`. JSON request body in, JSON response body out. Paths like `/object/create`, `/material/get_graph`, `/server/status`.

**Rationale:**
- HTTP has status codes (200 / 4xx / 5xx) that map cleanly to `ok` / `errorCode`.
- `curl http://localhost:9876/server/status` is the trivial debug story.
- Standard library — no extra Python deps inside the addon.
- Matches `mcp-unreal-agent`'s bridge — one mental model for both projects.

**Alternatives considered:**
- **Raw TCP socket** (ahujasid style) — works but every error is a manual parse; harder to debug.
- **WebSocket** — overkill for synchronous request/response.
- **gRPC** — needs `grpcio`, painful to bundle in a Blender addon.

**Consequences:**
- One open port (9876). Conflict possible — install brain detects and reports.
- Each request is a new TCP connection. Negligible overhead at developer scale.

---

## ADR-004: Compositions are one undo push at the end, not nested

**Status:** Accepted.

**Context:** Blender's undo stack is flat — there's no nesting. Multiple `bpy.ops.ed.undo_push` calls produce multiple Ctrl+Z entries.

**Decision:** Composite tools emit **one** `bpy.ops.ed.undo_push(message=...)` at the end of the main-thread `fn`, with a descriptive message that names the composite operation.

**Rationale:**
- Ctrl+Z behaves the way the user expects ("undo the thing the agent just did", not "undo five primitives one by one").
- Reduces visual noise in the Undo History panel.
- Matches `mcp-unreal-agent`'s `FScopedTransaction` semantics conceptually.

**Alternatives considered:**
- **One push per primitive** — pollutes undo history, breaks the agent UX.
- **No push at all** — relies on operators auto-pushing, which is inconsistent (data-block mutations don't push).

**Consequences:**
- If a composite fails mid-way, the partial state is *not* rolled back automatically. Handlers must wrap risky steps in try/except and clean up before raising. (Documented in [.claude/skills/tool-chains/SKILL.md](../skills/tool-chains/SKILL.md).)

---

## ADR-005: Name-keyed IDs, not synthetic UUIDs

**Status:** Accepted.

**Context:** `mcp-unreal-agent` uses asset paths like `/Game/Blueprints/BP_MyChar` as IDs. Blender's data model is keyed by name (`bpy.data.objects["Cube"]`).

**Decision:** Use the Blender name as the ID. `refs.objectName`, `refs.materialName`, `refs.boneName`. Never generate synthetic UUIDs.

**Rationale:**
- Blender's own scripting uses names. Matching the convention reduces cognitive friction for users who occasionally read addon source or run Python in the console.
- Names are stable as long as the user doesn't rename. Renames are explicit (`object_rename`) and update `refs` on the response.
- Tooltips and error messages are self-explanatory ("object 'Cube' not found").

**Alternatives considered:**
- **Synthetic UUIDs** — stable across rename but require a side-table mapping. Extra failure mode.
- **`bpy.data.objects[i]` integer indices** — change on add/remove. Useless as IDs.

**Consequences:**
- If two scenes have an object with the same name (rare; Blender appends `.001` automatically), the ID is still unique within a scene. Multi-scene tools accept `sceneName + objectName`.
- A rename mid-flow invalidates a held ref. The agent must call the rename tool, which returns the new ref.

---

## ADR-006: TypeScript MCP server, not Python

**Status:** Accepted.

**Context:** ahujasid/blender-mcp has the MCP server in Python (uvx-installed). We could do the same.

**Decision:** TypeScript MCP server in `Tools/`, identical pattern to `mcp-unreal-agent`.

**Rationale:**
- Reuses ~50% of `mcp-unreal-agent`'s code verbatim (bridge, contract, install brain, context skill, digest generator, vitest harness).
- Node-based MCP servers are the most common form in the ecosystem (better client support).
- Zod is the cleanest schema layer in the MCP ecosystem.
- Keeps the addon minimal — pure Python with stdlib only.

**Alternatives considered:**
- **Python MCP server** (uvx pattern) — would force two Python processes (server + addon) like ahujasid's setup. No real simplification.
- **Both** — twice the maintenance for no benefit.

**Consequences:**
- Two languages in the codebase. Acceptable — they have clear domain boundaries (TS = contract & transport; Python = Blender).
- snake_case ↔ camelCase translation lives in one place (`blender-bridge.ts`).

---

## ADR-007: `ref/` is gitignored prior-art, never copied verbatim

**Status:** Accepted.

**Context:** ahujasid/blender-mcp and PatrykIti/blender-ai-mcp are valuable references. They're MIT and Apache-licensed respectively, so copying would be legal, but mixing licenses and giving up the chance to design our own contract would hurt.

**Decision:** Clone both into `ref/` (gitignored). Read for patterns; never copy code into our tree.

**Rationale:**
- Our contract (`{ok, data, refs, nextSteps, warnings, errorCode}`) is the differentiator. Verbatim code loses it.
- Keeps license attribution simple — we ship our own code, MIT.
- The act of rewriting forces us to understand each pattern before adopting it.

**Alternatives considered:**
- **Submodule** — pulls history we don't want.
- **Fork** — implies derivative relationship; we're not deriving, we're starting from scratch.

**Consequences:**
- Some good ideas in `ref/` need explicit re-implementation. Worth it.

---

## ADR-008: `exec_python` is opt-in behind `BLENDER_AGENT_ALLOW_EXEC=1`

**Status:** Accepted (research phase).

**Context:** A `exec_python(code: str)` tool is trivial to ship and pseudo-solves "what if my tool list doesn't cover this?" It also opens an arbitrary code-execution path that a compromised or hallucinating model can abuse — wiping `bpy.data`, exfiltrating files, modifying `~/.config`, etc.

**Decision:** Ship `exec_python` and `get_python_console_output` **only when** the addon process sees `BLENDER_AGENT_ALLOW_EXEC=1`. By default the tools refuse to register, returning `errorCode: EXEC_PYTHON_DISABLED` if called. Same gate covers free-text driver expressions in `shape_key_add_driver` / `driver_add_*` (otherwise restricted to templated expressions like `var * 0.5`).

**Rationale:**
- Default-safe. A fresh install can't run arbitrary code.
- Power user opt-in for one-off scripts or research workflows.
- The flag is visible in `server_status` output so the agent can detect and adapt.

**Alternatives considered:**
- **Always-on** — unacceptable for an MCP server meant to be installed broadly.
- **Always-off** — too restrictive; some workflows genuinely need it.
- **Capability list in env** (`BLENDER_AGENT_ALLOW=exec_python,free_drivers`) — over-engineered for two related capabilities.

**Consequences:**
- The 228-tool catalog has one tool (`exec_python`) that v1.0 ships behind a flag. Documented in [TOOL-CATALOG.md §B9.E](research/TOOL-CATALOG.md) and [BPY-FEASIBILITY.md §2 row 14](research/BPY-FEASIBILITY.md).

---

## ADR-009: MetaHuman face — ARKit-52 in v1.0, full FACS DNA rig deferred to v1.1+

**Status:** Accepted (research phase).

**Context:** "MetaHuman face support" can mean two very different things:
1. The 52 ARKit blendshapes (Apple's spec) on a mesh, driven by drivers or Live Link Face. Trivially doable in `bpy`.
2. The full ~400-joint DNA face rig with RBF solvers, lip sync, and skin sliding. Authored in Maya/Houdini via Epic's `MetaHuman for Maya` plugin; no native Blender path exists.

**Decision:** v1.0 ships **ARKit-52 only** via `shape_key_create_arkit_set` + `shape_key_add_driver` + `metahuman_face_validate`. Full DNA rig is a v1.1+ investigation, possibly via external subprocess (`MetaHumanCreator` or DCC plugin bridge).

**Rationale:**
- Apple's ARKit-52 is the cross-platform face standard. UE5 Live Link Face writes to ARKit names. MetaHuman Animator accepts ARKit input.
- ARKit-52 covers 90% of game-character facial animation needs.
- Full DNA is research-grade work that would consume an entire sprint with uncertain feasibility.

**Alternatives considered:**
- **Ship nothing for v1.0** — leaves a glaring gap for the character pipeline.
- **Ship a half-built DNA rig** — would set false expectations.

**Consequences:**
- Marketing copy for v1.0 says "MetaHuman-compatible (ARKit-52)", not "full MetaHuman rig".
- `metahuman_face_validate` exists to prevent users from shipping incomplete face meshes.

---

## ADR-010: Sculpt boundary — agent ships deterministic ops + setup, not freehand strokes

**Status:** Accepted (research phase).

**Context:** Sculpting in Blender mixes deterministic ops (voxel remesh, symmetrize, masks, filters) with inherently modal ones (the brush stroke itself — needs live mouse events). The agent can't realistically replay a freehand sculpt session.

**Decision:** Ship the deterministic sculpt subset (`sculpt_remesh_voxel`, `sculpt_symmetrize`, `sculpt_filter_apply`, `sculpt_mask_create_from_cavity`, `sculpt_set_brush_param`, `sculpt_mode_toggle`, `sculpt_brush_stroke_deterministic` — the last replays a recorded stroke list, feasibility verified in 4.2). Do **not** ship a freehand "draw a stroke" tool. Polybuild retopo also stays modal — ship `retopo_create_base_cage` (Shrinkwrap-based) and `bmesh`-driven manual topo build.

**Rationale:**
- Determinism is non-negotiable for an agent tool. Modal brush strokes are not deterministic.
- The split aligns with what an artist actually does: "set up the scene + bake deterministic ops" is agent work; "express creative intent through brush strokes" is human work.
- Texture painting is the same pattern: agent sets up materials and bakes (B4); painting strokes stay human.

**Alternatives considered:**
- **Ship a `sculpt_freehand_stroke` taking screenshots and predicted mouse coords** — fragile, slow, non-deterministic.
- **Ship nothing for sculpt** — would block the character pipeline.

**Consequences:**
- v1.0 supports a "sculpt + verify" flow but not a "sculpt from scratch via agent" flow.
- Documented in [BPY-FEASIBILITY.md §2 rows 1, 3, 4](research/BPY-FEASIBILITY.md).

---

## ADR-011: Library Override — primitives only; conflict resolution stays human

**Status:** Accepted (research phase).

**Context:** Blender's Library Override system lets a linked datablock be locally edited. Upstream changes can break the override — Blender's resync logic helps but is imperfect, and conflict resolution genuinely needs the user's judgement.

**Decision:** Ship `library_link`, `library_make_override`, `library_resync`, `library_make_local` as primitives. **Do not** ship a composite that tries to auto-resolve override conflicts. The agent's role is to set up overrides and surface resync results; conflict resolution is the user's.

**Rationale:**
- Override conflicts are semantic. Asking an LLM to resolve "your animation says elbow_l should be at 30°, but upstream rig says 45°" is asking for hallucinated decisions.
- The 4 primitives cover ~95% of override workflows (cinematic ingest, character lib reuse).
- Asset Browser publishing is also UI-driven; v1.0 ships `asset_mark` / `asset_unmark` data tools but no browser interaction.

**Alternatives considered:**
- **Skip override entirely** — blocks cinematic and library-reuse workflows.
- **Ship auto-resolver** — would silently corrupt user data.

**Consequences:**
- Cinematic pipelines that need library overrides work; complex conflicts surface to the user.
- Documented in [BPY-FEASIBILITY.md §3.6](research/BPY-FEASIBILITY.md).

---

## ADR-012: Tool layering — pipeline-organized + canonical owner + cross-references

**Status:** Accepted (research phase).

**Context:** ~228 tools across 9 pipelines, with some tools (`export_fbx_static`, `uv_smart_project`, `shape_key_create_arkit_set`, `scene_create`, `collection_create`, `view_layer_create`) appearing in multiple pipelines' research notes. We need one place each tool lives.

**Decision:** Each tool has exactly one **canonical owner pipeline** — the file that defines its handler under `BlenderAgent/handlers/<domain>.py` and registration under `Tools/src/tools/<domain>.ts`. Other pipelines that use it cross-reference back via the alias map in [TOOL-CATALOG.md §"Cross-pipeline alias map"](research/TOOL-CATALOG.md).

The 9 pipelines (B1..B9) map to the 12-domain phase structure of [ROADMAP.md](../../ROADMAP.md) as follows:

| Pipeline | Phase | Notes |
|---|---|---|
| B1 Environment kits | P1 + P4 | Scene/object/collection (P1) + export (P4) |
| B2 Hard-surface props | P2 + P4 | Modifier/mesh edit (P2) + export (P4) |
| B3 Organic / character | P2 | Sculpt + rig prep |
| B4 UV + bake | P3 | UV + texture pipeline |
| B5 Materials / shaders | P3 | Material + shader node |
| B6 Geometry Nodes + Compositor | P3 | GN + compositor |
| B7 Rigging + MetaHuman face | P2 | Armature + bone + shape keys |
| B8 Animation + export | P2 + P4 | Animation auth (P2) + export (P4) |
| B9 Lighting / camera / render / scene / file | P4 + P5 | Render (P4) + file IO (P5) |

**Rationale:**
- Avoids duplicate handler registration (each `@handler("POST", "/object/create")` must be unique).
- Single source of truth per tool. The research files are organized by *artist workflow*; the codebase is organized by *Blender data domain*. The alias map bridges the two.

**Alternatives considered:**
- **One tool file per pipeline** — would lead to duplicate handler registrations.
- **Flat single-file registration** — unreadable at 228 tools.

**Consequences:**
- New-tool authoring procedure: find canonical owner per [TOOL-CATALOG.md](research/TOOL-CATALOG.md) → register there → cross-reference in the consuming pipeline's research file.

---

## ADR-013: Tool count target is ~228, not "~140"

**Status:** Accepted (research phase, supersedes implicit count in ROADMAP.md).

**Context:** [ROADMAP.md](../../ROADMAP.md) and [CLAUDE.md](../../CLAUDE.md) cited "~140 tools at v1.0" as an estimate. The 9-pipeline research surfaced 228 distinct tools — 162 🟢 + 51 🟡 + 15 🔴 (deferred or out-of-scope).

**Decision:** The verified v1.0 target is **~210 tools shipped** (162 green + 48 yellow w/ caveats), with 15 explicitly deferred to v1.1+. The "~140" figure in older docs is superseded — see [TOOL-CATALOG.md](research/TOOL-CATALOG.md) for the canonical count.

**Rationale:**
- The original 140 estimate predated the pipeline-by-pipeline study. The research surfaced ~88 more tools (mostly composites and per-pipeline export wrappers).
- Verified count is more useful than an estimate for sprint planning.

**Consequences:**
- ROADMAP.md "Tools delivered" column updated.
- Per-sprint task counts re-derive from this.
- The catalog is the source of truth, not the roadmap.
