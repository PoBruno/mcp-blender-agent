# CONTRIBUTING.md

Open to humans and AI agents. Same rules either way.

## 1. Read the entry point first

- Humans: start with [README.md](README.md), then [OBJECTIVES.md](OBJECTIVES.md), then [ROADMAP.md](ROADMAP.md).
- Agents (Claude Code, Copilot, Cursor): start with [CLAUDE.md](CLAUDE.md) or [AGENTS.md](AGENTS.md).

The bibles are in [.claude/docs/](.claude/docs/). `ARCHITECTURE.md` is the source of truth. Conflicts with it require a new ADR in [DECISIONS.md](.claude/docs/DECISIONS.md).

## 2. Scope

Work in scope = a task listed in [.claude/docs/SPRINTS.md](.claude/docs/SPRINTS.md). Anything else, open an issue first.

## 3. Branch + commit hygiene

- **Never commit to `main`.** All work goes to `dev` (or a topic branch off `dev`).
- **Never `git add -A`.** Stage specific files.
- Commit format: `type: short description` (max 72 chars). Types: `feat`, `fix`, `wip`, `refactor`, `chore`, `docs`, `test`.
- No AI attribution markers. No "Generated with Claude" trailers. Write commits as a developer.

## 4. Build + test before declaring done

- **Python addon change:** reload the addon in Blender (or restart `blender --background` in tests). Run the relevant Vitest integration test.
- **TypeScript change:** `cd Tools && npm run build && npm test`.

Failed build = not done.

## 5. Tool contract is non-negotiable

Every MCP tool returns `{ ok, data, refs, nextSteps, warnings, errorCode }`. Read [.claude/rules/mcp-tools.md](.claude/rules/mcp-tools.md). New error codes go in the registry there + in [.github/instructions/mcp-tools.instructions.md](.github/instructions/mcp-tools.instructions.md).

## 6. Threading is non-negotiable

`bpy` is not thread-safe. All mutations go through the main-thread `bpy.app.timers` drain. Calling `bpy.*` from the HTTP background thread is a bug, even if it works "most of the time".

## 7. Tests are mandatory

Every new tool ships with an integration test in `Tools/test/tools/`. CI runs against Blender 4.2 LTS on Windows + macOS + Linux. Red CI = not merged.

## 8. PRs

- Open against `dev`. Never against `main`.
- One concern per PR. If you find yourself touching multiple unrelated files, split.
- PR body summarizes: what changed, why (link the SPRINTS task), how you tested.

## 9. Reference repositories

`ref/` is gitignored. It holds prior-art Blender MCPs for study (`ahujasid/blender-mcp`, `PatrykIti/blender-ai-mcp`). **Never copy code verbatim.** Read, learn, write your own.

## 10. Code of conduct

Be direct. Be technical. Skip the small talk in PR descriptions. Treat AI contributions with the same review standard as human contributions.
