<div align="center">

# mcp-blender-agent

**Deterministic Blender control for AI agents — typed tools, not improvised Python.**

[![npm](https://img.shields.io/npm/v/@pobruno/blender-agent)](https://www.npmjs.com/package/@pobruno/blender-agent)
[![Blender 4.2+](https://img.shields.io/badge/Blender-4.2%20LTS%2B-orange)](https://www.blender.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

The point nobody discusses in Blender MCP demos: the problem isn't the AI. Most MCPs just delegate Python scripts to Blender — each run generates different code, no grouped undo, no output schema. When it fails you don't know if it was the model, the script, or the scene state.

You solve this outside the addon. Each operation becomes a **typed tool**: input validated, output structured as `{ ok, data, refs, nextSteps }` with IDs that chain into the next call. Composite mutations end with a single undo push. The agent stops improvising Python. Same input, same result. Ctrl+Z undoes the entire operation.

~216 tools across 12 domains — a separate tool for each Blender operation: modeling, rigging, animation, materials, shader/geometry nodes, rendering, FBX/glTF/USD/Alembic export with every exporter parameter exposed. Runs on Blender 4.2 LTS+ (5.x recommended).

→ Architecture: [.claude/docs/ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md)

---

## Install

You install the MCP by running **one prompt in whatever agent you use** — Claude Code, GitHub Copilot, Cursor, Codex, opencode, Claude Desktop. The agent detects which harness it's running in, configures itself, and walks you through the one manual step (installing `BlenderAgent.zip` in Blender's Add-ons UI). **No clone, no build** — the server runs via `npx` (prereq: Node 18+).

Paste this into your agent chat:

```
Install @pobruno/blender-agent into this workspace. Fetch and read
https://raw.githubusercontent.com/PoBruno/mcp-blender-agent/main/install/AGENT-INSTALL.md
and run every phase. Detect which agent harness you are running as (Claude Code,
GitHub Copilot, Cursor, Codex, opencode, or Claude Desktop) and follow the
config-target and skill-placement tables for that harness: merge the
`npx -y @pobruno/blender-agent@latest` server entry into my MCP config, copy the
bundled context skill (`npx -y @pobruno/blender-agent --print-skill-dir`) into my
harness, and inject the managed block from MANAGED-BLOCK.md into my primary
instruction file. Ask before anything destructive or global. Print the path from
`--print-addon-zip` so I can install it in Blender's Add-ons UI.
```

Per-harness prompts and workflow recipes: [install/PROMPT-TEMPLATES.md](install/PROMPT-TEMPLATES.md) · Manual reference: [install/INSTALL.md](install/INSTALL.md)

---

## Manual install (contributors)

```powershell
git clone https://github.com/PoBruno/mcp-blender-agent.git
cd mcp-blender-agent/Tools
npm install && npm run build
npm test   # requires Blender on PATH or BLENDER_BIN
```

---

## License

MIT. Not affiliated with the Blender Foundation.
