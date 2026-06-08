# Install — placeholder

The end-user install playbook ships with **Phase 5** of the roadmap. Until then this folder holds placeholders.

When Phase 5 lands, this folder will contain:

| File | Purpose |
|---|---|
| `INSTALL.md` | Human-readable step-by-step install for technical users who don't want to use an agent. |
| `AGENT-INSTALL.md` | Adaptive installer brain — the agent reads this and performs detect → plan → ask → execute → inject → verify. |
| `PROMPT-TEMPLATES.md` | Copy-paste prompts for Claude Code, Copilot, Cursor, Claude Desktop. |
| `context-skill/` | Passive context skill injected into the user harness. |
| `claude-mcp-config.json` | MCP config snippet template. |

For now: there is nothing to install. The repo is in Phase 0 (bootstrap). See [ROADMAP.md](../ROADMAP.md) and [.claude/docs/SPRINTS.md](../.claude/docs/SPRINTS.md).

## Sister project reference

The full install brain pattern is in [`mcp-unreal-agent/install/AGENT-INSTALL.md`](https://github.com/PoBruno/mcp-unreal-agent/blob/main/install/AGENT-INSTALL.md). This project will mirror it in Phase 5, simplified where Blender's lack of a build step makes things easier.
