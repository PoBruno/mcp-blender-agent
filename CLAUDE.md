# mcp-blender-agent

Complete Blender agent runtime — MCP server giving AI coding agents (Claude Code, GitHub Copilot, Cursor, anything that speaks MCP) full control of a Blender session: modeling, rigging, animation, materials, shader / geometry nodes, rendering, and granular import/export.

This file is the **agent entry point**. GitHub Copilot reads it via [.github/copilot-instructions.md](.github/copilot-instructions.md) (which delegates here). Cursor and other agents read it via [AGENTS.md](AGENTS.md).

Sister project: [PoBruno/mcp-unreal-agent](https://github.com/PoBruno/mcp-unreal-agent). Same architecture, same contracts, same harness — the Blender twin.

---

## What this project does

Two processes:

- **`BlenderAgent` Python addon** — runs inside Blender (or as headless `blender --background`). Hosts an HTTP server on port `9876`. Calls `bpy.data`, `bpy.ops`, `bmesh`, `mathutils` directly. **No build step** — distributed as a zipped folder you install through Blender's Add-ons preferences.
- **`blender-agent` TypeScript MCP server** — translates MCP tool calls from agents into HTTP calls to the addon. Ships ~140 tools across 12 domains at v1.0.

Two serving modes:

- **Addon (preferred):** auto-starts when Blender opens. Zero overhead.
- **Headless:** spawned by the TS server when no Blender instance is detected. Used for CI, batch ops, headless render.

Agents call tools like `object_create`, `bone_add`, `material_assign_slot`, `shader_node_connect_pins`, `keyframe_add`, `export_fbx`. Every response includes IDs that chain into the next call.

---

## Tech stack

| Layer | Tech |
|---|---|
| Blender | 4.2 LTS or newer (no 3.x support) |
| Addon language | Python 3.11+ (Blender's embedded interpreter) — `bpy`, `bmesh`, `mathutils` |
| HTTP server | `http.server` in a background `threading.Thread`, drained on the main thread via `bpy.app.timers.register(drain, persistent=True)` |
| MCP server | TypeScript on Node.js 18+, `@modelcontextprotocol/sdk` v1.12+ |
| Schema validation | Zod |
| Tests | Vitest with a self-bootstrapping `blender --background` harness |
| Bridge | HTTP localhost:9876 (JSON in, JSON out) |
| Distribution | TS server via npm; addon as `BlenderAgent.zip` from GitHub Releases |

---

## Architecture principles

1. **Subsystem-equivalent APIs only.** Use `bpy.data` and `bpy.ops` directly. Never reach for deprecated 2.7x-style globals like `Blender.*`. When an operator requires context, wrap in `bpy.context.temp_override(...)` and restore on exit.
2. **Composite atomic flows.** A single high-level tool drains its mutations on the main thread and ends with a single `bpy.ops.ed.undo_push(message=...)`. Agents shouldn't have to orchestrate undo manually. See [.claude/skills/tool-chains/SKILL.md](.claude/skills/tool-chains/SKILL.md).
3. **Structured output contract.** Every tool returns `{ ok, data, refs, nextSteps, warnings, errorCode }`. `refs` are IDs the agent passes to the next tool. `nextSteps` are hints, never commands. See [.claude/rules/mcp-tools.md](.claude/rules/mcp-tools.md).
4. **Main-thread marshalling.** `bpy` is **not thread-safe**. The HTTP server runs on a background thread, enqueues a callable, then blocks on a `threading.Event` until the `bpy.app.timers` drain on the main thread executes it and posts the result. **Never call `bpy.*` from the HTTP thread directly.**
5. **Mode-aware mutations.** Mesh edits switch to Edit Mode, armature edits to Edit/Pose Mode, restore on exit. Idempotent — entering a mode you're already in is a no-op.
6. **Snapshots, not binary diffs.** `.blend` is binary; never try to diff it. Use structured JSON snapshots for graphs and scenes.
7. **Headless is the fallback, not the default.** If Blender is open, the TS server detects it (probe `GET /server/status` on port `9876`) and never spawns a duplicate.
8. **Dual harness, single source of truth.** All conventions live in `CLAUDE.md` and `.claude/`. The `.github/copilot-instructions.md` is a thin bridge that re-exports them. No drift allowed.

---

## Project documentation

All living docs are in [.claude/docs/](.claude/docs/). **`ARCHITECTURE.md` is the bible** — read it before touching any domain. [OBJECTIVES.md](OBJECTIVES.md) is the product brief; if you ever feel a conflict between the two, OBJECTIVES wins until ARCHITECTURE is updated.

| File | Purpose |
|---|---|
| [OBJECTIVES.md](OBJECTIVES.md) | Product brief — what we're building and why, success criteria, non-goals |
| [ROADMAP.md](ROADMAP.md) | 5-phase plan with milestones |
| [.claude/docs/ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md) | System design bible — components, threading, IPC, tool contract, install flow |
| [.claude/docs/DECISIONS.md](.claude/docs/DECISIONS.md) | ADRs — why we chose X over Y |
| [.claude/docs/SPRINTS.md](.claude/docs/SPRINTS.md) | Active sprint tasks — source of truth for what to work on |
| [.claude/docs/HISTORY.md](.claude/docs/HISTORY.md) | Session snapshots |

Domain rules in [.claude/rules/](.claude/rules/) (loaded per-file by `applyTo` glob):

| File | applyTo |
|---|---|
| [.claude/rules/python-blender.md](.claude/rules/python-blender.md) | `BlenderAgent/**/*.py` |
| [.claude/rules/typescript.md](.claude/rules/typescript.md) | `Tools/**/*.ts` |
| [.claude/rules/mcp-tools.md](.claude/rules/mcp-tools.md) | `Tools/src/tools/**/*.ts` |

Skills in [.claude/skills/](.claude/skills/) — domain knowledge packaged for the agent to load on demand:

| Skill | When to load |
|---|---|
| `blender-api-cheat` | Need the right `bpy` module / operator / class for an operation |
| `tool-chains` | Designing a new composite tool, or chaining existing tools |
| `mcp-tool-schema` | Defining a new MCP tool's input/output shape |
| `install` | Working on or executing the end-user install playbook |

---

## Passive behaviors (always active)

These apply in every conversation without invoking a command.

**Before implementing any feature:**
- Check [.claude/docs/SPRINTS.md](.claude/docs/SPRINTS.md) — confirm the task is in the active sprint. If not, ask before starting.
- Check [.claude/docs/DECISIONS.md](.claude/docs/DECISIONS.md) — your design might already have an ADR.

**Before any architecture or tech decision:**
- Read [.claude/docs/ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md). It is the source of truth.
- If your idea conflicts with an existing ADR, surface the conflict before writing code. Add a new ADR (problem / decision / rationale / alternatives) if a genuinely new call is being made.

**When touching the Python addon:**
- `bpy` is **not thread-safe** — every mutation runs on the main thread via the timer drain.
- Operators that need 3D-View context wrap in `bpy.context.temp_override(...)`.
- Mode switches are bracketed (enter, mutate, restore).
- Composite mutations end with **one** `bpy.ops.ed.undo_push(message=...)`.
- Never use deprecated 2.7x-style APIs. Lock on Blender 4.2 LTS+.
- Errors propagate as Python exceptions — caught at the handler boundary and converted to `{ ok: false, errorCode: ... }`.

**When touching TypeScript MCP server code:**
- Every tool returns the structured contract (see [.claude/rules/mcp-tools.md](.claude/rules/mcp-tools.md)).
- Zod schema for every input — no `any`.
- Integration test required: add to `Tools/test/tools/<your-tool>.test.ts`.
- After ANY TS change run `npm run build`. The parent agent does the build; sub-agents do not.

**When writing MCP tool descriptions:**
- They are read by the LLM consuming them. Write for that audience: what it does, when to use it, inputs, outputs.
- Under 200 chars for simple tools; structured multiline for complex ones (especially `export_*` with dozens of parameters).

**When writing anything external (commits, PRs, README, docs outside `.claude/`):**
- Write as a developer, not as an AI — short, direct, lowercase after the prefix.
- Banned words: "ensure", "leverage", "facilitate", "utilize", "implement", "comprehensive", "robust", "seamless", "straightforward".
- No AI attribution markers, no "Generated with Claude", no co-author trailers.
- Commit format: `type: short description` (max 72 chars). Types: `feat`, `fix`, `wip`, `refactor`, `chore`, `docs`, `test`.

---

## Reference repositories (read-only)

`ref/` is **gitignored**. It holds shallow clones of prior-art Blender MCPs so you can study patterns:

- `ref/blender-mcp/` — [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp), the dominant "creative" Blender MCP. Reference for the socket addon pattern.
- `ref/blender-ai-mcp/` — [PatrykIti/blender-ai-mcp](https://github.com/PatrykIti/blender-ai-mcp), goal-first routing and curated tools.

**Never copy code verbatim from `ref/`.** Read, learn, write our own to our contract.

---

## Git workflow

Permanent `dev` integration branch. `main` is release-only.

- **`dev` is permanent.** All day-to-day work commits to `dev` (or a topic branch off `dev`).
- **`main` is release-only.** Advances only via a long-lived PR from `dev` → `main`. Never commit directly to `main`.
- **Never** use `git add -A` — always stage specific files.
- Commit format: `type: short description` (max 72 chars).

---

## Repository structure

```
mcp-blender-agent/
├── CLAUDE.md                       # this file — agent entry point
├── AGENTS.md                       # universal bridge for Cursor / others
├── OBJECTIVES.md                   # product brief
├── ROADMAP.md                      # 5-phase delivery plan
├── README.md                       # human entry point
├── LICENSE                         # MIT
├── CONTRIBUTING.md                 # open to humans and AI agents
│
├── BlenderAgent/                   # Python addon (the plugin)
│   ├── __init__.py                 # addon registration (bl_info)
│   ├── server.py                   # HTTP listener + main-thread drain
│   └── handlers/                   # one file per domain
│
├── Tools/                          # TypeScript MCP server
│   ├── package.json
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── index.ts                # MCP server entry
│   │   ├── blender-bridge.ts       # HTTP client + headless lifecycle
│   │   ├── types.ts                # ToolResult contract type
│   │   └── tools/                  # one file per tool group
│   └── test/                       # vitest integration tests
│
├── install/                        # install harness for end users
│   ├── INSTALL.md                  # human-readable install steps
│   ├── AGENT-INSTALL.md            # adaptive installer brain (added Phase 5)
│   ├── context-skill/              # passive context pack (added Phase 5)
│   └── PROMPT-TEMPLATES.md         # copy-paste prompts for Claude / Copilot / Cursor
│
├── ref/                            # GITIGNORED — reference repos for study
│   ├── blender-mcp/                # ahujasid/blender-mcp
│   └── blender-ai-mcp/             # PatrykIti/blender-ai-mcp
│
├── .claude/                        # dev harness — Claude + Copilot read this
│   ├── docs/                       # living architecture / roadmap / sprint
│   ├── rules/                      # domain rules (applyTo globs)
│   └── skills/                     # domain knowledge skills
│
└── .github/
    ├── copilot-instructions.md     # bridge: delegates to CLAUDE.md
    └── instructions/               # applyTo-scoped instructions for Copilot
```

---

## Coding conventions

- **No comments unless the WHY is non-obvious.** Names should explain the what.
- **One responsibility per file.** Addon handler files split by domain. TS tool files split by feature group.
- **Always `await` in TS.** No `.then(...)` chains in tool code.
- **Zod schemas at the boundary.** No `any`, no untyped responses.
- **Snake_case for Python, camelCase for TS public APIs, kebab-case for tool names** (`object_create`, `material_assign_slot`).
- **JSON in / JSON out** at the HTTP boundary. The TS server is the only place that translates between Zod camelCase and Python snake_case.

---

## Running the project

Phase 0 is the only phase scaffolded right now. As phases land, this block grows.

```powershell
# TypeScript MCP server — build
cd Tools
npm install
npm run build

# Run the integration test suite (spawns headless Blender)
npm test
```

Headless Blender requirement: `blender` on `PATH` or `BLENDER_BIN` env var pointing at the executable.

---

## Claude Code config (after Phase 0)

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "node",
      "args": ["./node_modules/@pobruno/blender-agent/dist/index.js"],
      "env": { "BLENDER_PORT": "9876" }
    }
  }
}
```

## GitHub Copilot / VS Code config (after Phase 0)

```json
{
  "mcp": {
    "servers": {
      "blender-agent": {
        "command": "node",
        "args": ["./node_modules/@pobruno/blender-agent/dist/index.js"],
        "env": { "BLENDER_PORT": "9876" }
      }
    }
  }
}
```

---

## Sprint task format

Every task in SPRINTS.md follows this exact format.

### Task ID
```
SN-XX   where N = sprint number, XX = zero-padded task number (01, 02, …)
```

### Task line
```markdown
- [ ] **SN-XX** One-line description — include done criteria inline
  _(requires SN-YY)_
  ⚠️ Note: one-line warning about a non-obvious constraint
  🔍 Research first: one-line of what to verify before writing code
```

### Marking done
```markdown
- [x] **SN-XX** Description <!-- done: YYYY-MM-DD -->
```

---

## Tool output contract — quick reference

Every MCP tool must return:

```ts
type ToolResult<T> = {
  ok: boolean;
  data?: T;                                   // shape varies per tool
  refs?: Record<string, string | string[]>;   // IDs other tools can consume
  nextSteps?: string[];                       // hints, not commands
  warnings?: string[];
  errorCode?: string;                         // when ok=false
};
```

See [.claude/rules/mcp-tools.md](.claude/rules/mcp-tools.md) for the full contract, error code table, and ID-chain conventions.

---

## When in doubt

1. Read [OBJECTIVES.md](OBJECTIVES.md) — does what you're about to do serve the single objective?
2. Search [.claude/docs/ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md) and [.claude/docs/DECISIONS.md](.claude/docs/DECISIONS.md).
3. Check the active sprint in [.claude/docs/SPRINTS.md](.claude/docs/SPRINTS.md).
4. Read the relevant skill in [.claude/skills/](.claude/skills/).
5. Then ask.
