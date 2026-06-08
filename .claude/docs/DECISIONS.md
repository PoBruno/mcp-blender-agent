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
