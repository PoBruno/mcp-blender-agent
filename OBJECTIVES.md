# OBJECTIVES.md

The product brief for `mcp-blender-agent`. If any decision conflicts with this file, the file wins until it is amended.

---

## 1. The single objective

> Give an AI coding agent **complete, deterministic, undoable control** of a Blender session through MCP, with the same contract guarantees as `mcp-unreal-agent`.

"Complete" = anything a technical artist could do through Blender's UI, the agent can do through a typed tool. "Deterministic" = the agent never has to parse free text or guess; every tool returns structured JSON with IDs that chain into the next call. "Undoable" = every mutation lands in Blender's undo stack with a meaningful label, and composite flows are a single undo step.

---

## 2. Concrete capability targets

The agent must be able to:

### Scene & object control
- Enumerate scenes, collections, objects, modifiers, constraints — with every property visible.
- Create, duplicate, rename, parent, transform, delete any object type (mesh, armature, empty, camera, light, curve, GPencil).
- Mutate every property of every modifier and constraint with the exact same fidelity as the N-panel.

### Modeling
- Inspect and mutate mesh data (vertices, edges, faces, vertex groups, UV maps, shape keys) via `bmesh`.
- Add and configure modifiers (subdivision, mirror, array, boolean, decimate, solidify, etc.) end-to-end without leaving the chat.
- Apply, reorder, remove modifiers.

### Rigging
- Author armatures: add bones, set roll, set head/tail/parent, name vertex groups.
- Add "sockets" — empties parented to bones — with the same UX as UE sockets.
- Copy / mirror bones between armatures.
- Inspect and edit pose mode constraints (IK, copy rotation, limit location, etc.).

### Animation
- List and edit actions, F-curves, keyframes, interpolation, NLA tracks.
- Insert / remove / move keyframes by frame and value.
- Bake actions, retarget, mute / solo strips.
- Add and configure drivers.

### Materials & nodes
- Read every shader node graph as structured JSON.
- Add, connect, disconnect, delete shader nodes with typed inputs.
- Mutate every Principled BSDF parameter, every image texture, every node group input.
- Snapshot + diff material graphs (text-diffable JSON snapshots, no binary `.blend` diff needed).
- Same for Geometry Nodes and Compositor.

### Camera, light, viewport, render
- Create and configure cameras (focal, sensor, DoF, clip).
- Create and configure lights (type, energy, color, shadow).
- Drive the viewport (camera, view, shading mode, screenshot).
- Set render engine (Cycles / Eevee / Workbench), settings, frame range.
- Render image, render animation, take viewport screenshot, take final render.

### Import & export — the killer feature
- Import FBX / glTF / OBJ / USD / Alembic / `.blend` library link/append, with every operator parameter typed.
- Export the same formats with **every single operator parameter exposed as a Zod-validated input** — axis remap, scale, embed textures, smoothing groups, animation export modes, NLA strip handling, leaf bones, USD instancing, Alembic visibility, etc.
- A single composite tool can: "rename armature root, bake actions, fix scale, export FBX with UE-compatible settings to path X" — atomically.

### File & session
- Save, save-as, open, revert, list dependencies, pack / make-local external files.
- Inspect Python console output and `print()` results.
- Escape hatch: `exec_python` (off by default, opt-in per session).

---

## 3. Architectural guarantees (non-negotiable)

These mirror `mcp-unreal-agent`. They are why this project is different from existing Blender MCPs.

1. **Structured contract.** Every tool returns `{ ok, data, refs, nextSteps, warnings, errorCode }`. No free-text status, no implicit success.
2. **ID-chain.** `refs.objectName`, `refs.materialName`, `refs.actionName`, etc., feed the next tool's input parameter verbatim.
3. **Composite atomic flows.** Multi-step mutations wrap in a single `bpy.ops.ed.undo_push(message=...)`. The agent calls one tool, gets one undo entry.
4. **Main-thread marshalling.** `bpy` is not thread-safe. The addon's HTTP server lives on a background thread; every handler enqueues work into a `bpy.app.timers` drain that runs on the main thread.
5. **Context-override safety.** Operators that require a 3D-Viewport context wrap in `bpy.context.temp_override(...)` with restore on exit.
6. **Mode-aware mutations.** Mesh edits switch to Edit Mode, armature edits switch to Edit/Pose Mode, restore on exit. Idempotent.
7. **Snapshots, not binary diffs.** `.blend` is binary; structured JSON snapshots are the unit of "what changed".
8. **Anti-drift docs.** A `generate-tools-digest.mjs` produces `install/context-skill/TOOLS.md` so the agent's passive context always matches the registered tools.
9. **Dual harness.** Claude Code (`CLAUDE.md` + `.claude/`) and GitHub Copilot (`.github/copilot-instructions.md` + `.github/instructions/`) share one source of truth. Cursor and others land via `AGENTS.md`.

---

## 4. Success criteria

| # | Criterion | How we measure |
|---|---|---|
| S1 | The agent can build a low-poly character from a text description — mesh + armature + weights + idle anim + materials + export — in one chat session, with one Ctrl+Z reverting each composite step. | Smoke test script under `Tools/test/` runs the full flow against a headless Blender and asserts the produced `.fbx` opens in UE5 with the expected bones and animation. |
| S2 | Every Blender export operator parameter is reachable as a Zod-typed tool input — no "fall back to `exec_python`". | Coverage check in CI parses `addon.py` against the operator definitions and fails if a parameter is missing. |
| S3 | An end-user can install the MCP into any of (Claude Code, Copilot, Cursor, Claude Desktop) by pasting one prompt and answering 1–3 questions. | Manual smoke test on a clean Windows + clean macOS environment per release. |
| S4 | First-call latency from agent → addon → Blender → response is ≤ 200 ms for read tools, ≤ 1 s for typical mutations. | Vitest perf assertions in CI. |
| S5 | The passive context skill is never stale. | CI fails if `npm run digest` produces a diff against the committed `TOOLS.md`. |

---

## 5. Non-goals

We will explicitly **not**:

- Generate 3D assets via external services (Hyper3D, Sketchfab, Poly Haven). That's [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)'s niche. We compose with that MCP rather than duplicate it.
- Bundle a renderer or proprietary node groups. We expose Blender's own engines.
- Ship a chat UI, web dashboard, or visual editor. The agent is the UI.
- Implement a C++ Blender plugin. Python addon is the right boundary for Blender; C++ here would be cost without benefit.
- Support Blender 3.x. Lock on **Blender 4.2 LTS or newer** (see [DECISIONS.md](.claude/docs/DECISIONS.md)).
- Provide telemetry. Zero data exfiltration. Differs from `ahujasid/blender-mcp`'s anonymous telemetry by design.

---

## 6. Audience

Two distinct users:

- **The end user** — a technical artist, indie dev, or pipeline TA who runs Blender daily and uses an AI agent to drive it. They never read this repo's source. They paste an install prompt and start working.
- **The contributor** — another developer or agent extending the toolset. They read [CLAUDE.md](CLAUDE.md), [ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md), [DECISIONS.md](.claude/docs/DECISIONS.md), the rules in [.claude/rules/](.claude/rules/), and the skills in [.claude/skills/](.claude/skills/), then add tools.

The end user must never need to know that "tools are in `Tools/src/tools/`". The contributor must never need to ask "where do I put a new tool".

---

## 7. Out-of-scope until later

Deferred to post-1.0:

- Render farm / distributed render orchestration.
- Real-time co-op (multi-agent on one Blender).
- Plugin marketplace for community tools.
- Equivalent of UE's "C++ context bridge" — Blender's `bpy` reference is already first-class; only revisit if user demand emerges for reading user-installed addon source.

---

## 8. What "done" looks like for v1.0

- ~140 typed tools across 12 groups (see [ROADMAP.md](ROADMAP.md)).
- Install brain + passive context skill production-ready for all four harnesses.
- Two demo videos: "build a character" and "export a level for UE5".
- Sister-repo cross-link from `mcp-unreal-agent` documenting the chain `blender-agent → export FBX → unreal-agent → import to UE5`.
- 100% green CI on Windows + macOS + Linux against Blender 4.2 LTS.
