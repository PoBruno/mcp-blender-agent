# AGENTS.md

Universal entry point for AI coding agents (Cursor, Aider, Continue, Cline, Windsurf, anything that reads `AGENTS.md`).

**The full instruction set lives in [CLAUDE.md](CLAUDE.md). Read it.**

This file exists so that agents which look for `AGENTS.md` by convention land at the same harness used by Claude Code and GitHub Copilot.

## What this project is

`mcp-blender-agent` — an MCP server giving AI agents complete, deterministic, undoable control of Blender: modeling, rigging, animation, materials, shader / geometry nodes, rendering, granular import / export.

Sister project: [PoBruno/mcp-unreal-agent](https://github.com/PoBruno/mcp-unreal-agent). Same architecture, same contracts, same harness — the Blender twin.

Two parts:
- **`BlenderAgent` Python addon** at [BlenderAgent/](BlenderAgent/) — runs an HTTP server inside Blender on port `9876`. No build step.
- **`blender-agent` MCP server** at [Tools/](Tools/) — TypeScript bridge from MCP protocol to addon HTTP.

## What you need to know to start work

1. Read [OBJECTIVES.md](OBJECTIVES.md) — the product brief.
2. Read [CLAUDE.md](CLAUDE.md) — full conventions, tech stack, doc index.
3. Read [.claude/docs/ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md) — system bible.
4. Check [.claude/docs/SPRINTS.md](.claude/docs/SPRINTS.md) — current task list.
5. Domain rules in [.claude/rules/](.claude/rules/) load per-file by glob.
6. Skills (loadable domain knowledge) in [.claude/skills/](.claude/skills/).

## Hard rules

- Never commit directly to `main`. Work goes on `dev` or a topic branch off `dev`.
- After Python addon changes: reload the addon in Blender (or restart `blender --background` in tests), then run the relevant Vitest integration test.
- After TS changes: `cd Tools && npm run build`, then run tests.
- Every new MCP tool needs an integration test in `Tools/test/tools/`.
- Tool outputs must follow the structured contract in [.claude/rules/mcp-tools.md](.claude/rules/mcp-tools.md).
- `bpy` is **not thread-safe.** All mutations run on the main thread via the timer drain — never call `bpy.*` from the HTTP background thread.

## Reference repositories

`ref/` (gitignored) contains shallow clones of prior-art Blender MCPs for study. Never copy verbatim.
