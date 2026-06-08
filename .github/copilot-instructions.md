# GitHub Copilot instructions

This repo is dual-harness: Claude Code and GitHub Copilot work from the same conventions. The source of truth is [`CLAUDE.md`](../CLAUDE.md) and [`.claude/`](../.claude/). This file is a thin bridge so Copilot lands at the same place.

## Read these first

1. [`OBJECTIVES.md`](../OBJECTIVES.md) — product brief. The single objective and concrete capability targets.
2. [`CLAUDE.md`](../CLAUDE.md) — project entry point: tech stack, architecture principles, doc index, commands, conventions. Read it in full before any non-trivial change.
3. [`.claude/docs/ARCHITECTURE.md`](../.claude/docs/ARCHITECTURE.md) — system bible. Read before touching any domain.
4. [`.claude/docs/SPRINTS.md`](../.claude/docs/SPRINTS.md) — active sprint tasks. Confirm your work is in scope.
5. [`.claude/docs/DECISIONS.md`](../.claude/docs/DECISIONS.md) — ADRs. Your design might already exist here.

## File-scoped rules

Copilot loads per-file rules from [`.github/instructions/`](instructions/) automatically when their `applyTo` glob matches. They mirror the rules in [`.claude/rules/`](../.claude/rules/) — same content, different harness location.

| Glob | Rule file |
|---|---|
| `BlenderAgent/**/*.py` | [`instructions/python-blender.instructions.md`](instructions/python-blender.instructions.md) |
| `Tools/**/*.ts` | [`instructions/typescript.instructions.md`](instructions/typescript.instructions.md) |
| `Tools/src/tools/**/*.ts` | [`instructions/mcp-tools.instructions.md`](instructions/mcp-tools.instructions.md) |

## Skills

Skills are domain knowledge packs in [`.claude/skills/`](../.claude/skills/). Each has a `SKILL.md` you load when relevant:

- `tool-chains/SKILL.md` — designing composite tools and chaining existing ones
- `blender-api-cheat/SKILL.md` — `bpy` module map, operator vs data access, threading
- `mcp-tool-schema/SKILL.md` — input/output shape for new tools
- `install/SKILL.md` — install playbook execution

When the user's request matches a skill's topic, read the corresponding `SKILL.md` before writing code.

## Hard rules (Copilot-relevant subset)

- **Build after every change.** TS: `cd Tools && npm run build`. Python: reload the addon in Blender (or restart `blender --background` in tests). Do not declare done before the build passes.
- **Integration test per new tool.** New TS tool → new file in `Tools/test/tools/`. New addon handler → covered by the TS tool's test.
- **`bpy` is not thread-safe.** Every mutation goes through the main-thread timer drain. Never call `bpy.*` from the HTTP background thread.
- **Wrap mutations in undo.** Composite tools end with a single `bpy.ops.ed.undo_push(message=...)`.
- **Structured output contract.** Every tool returns `{ ok, data, refs, nextSteps, warnings, errorCode }`. See [`.claude/rules/mcp-tools.md`](../.claude/rules/mcp-tools.md).
- **No commits to `main`.** Work goes on `dev` or a topic branch off `dev`.
- **No AI attribution in commits / PRs.** Write as a developer.
- **`ref/` is read-only.** Never modify, never copy verbatim. Study and write our own to our contract.

## When proposing tool calls

Copilot agent mode: prefer using the MCP tools this project itself exposes (`blender-agent` server) when the work is about manipulating a Blender project. Don't shell out to `blender --python` when a typed MCP tool already exists.

When unsure whether a tool exists, list available `blender-agent` tools first.
