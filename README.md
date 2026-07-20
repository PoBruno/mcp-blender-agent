# mcp-blender-agent

The problem with most Blender MCPs: they just delegate Python scripts. Each run generates different code, no grouped undo, no output schema — when it fails you don't know if it was the model, the script, or the scene state.

Here every operation is a **typed tool**: input validated by Zod schema, output structured as `{ ok, data, refs, nextSteps }` with IDs that chain into the next call. Composite mutations end with a single undo push. Same input, same result. Ctrl+Z undoes the whole operation, not five micro-steps.

~216 tools across 12 domains — modeling, rigging, animation, materials, shader/geometry nodes, rendering, FBX/glTF/USD/Alembic export with every exporter parameter exposed. Runs on Blender 4.2 LTS+ (5.x recommended).

→ Architecture deep-dive: [.claude/docs/ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md)

---

## Install

Paste the prompt for your agent into chat. **No clone, no build** — the server runs via `npx`. The agent will print the path to `BlenderAgent.zip`; you install it once via **Blender → Edit → Preferences → Add-ons → Install…** (prereq: Node 18+).

### Claude Code

```
Install @pobruno/blender-agent into this workspace. Read install/AGENT-INSTALL.md
from https://github.com/PoBruno/mcp-blender-agent and run every phase. Merge
{ "command": "npx", "args": ["-y", "@pobruno/blender-agent@latest"] } into
.mcp.json, then run `npx -y @pobruno/blender-agent --print-skill-dir` and copy
the bundled SKILL/FLOWS/TOOLS markdown into .claude/skills/blender-agent/.
Inject the managed block from MANAGED-BLOCK.md into CLAUDE.md. Use
AskUserQuestion before anything destructive. Print the path from
`--print-addon-zip` so I can install it in Blender's Add-ons UI.
```

### GitHub Copilot (VS Code)

```
Install @pobruno/blender-agent into this workspace. Read install/AGENT-INSTALL.md
from https://github.com/PoBruno/mcp-blender-agent and run every phase. Merge
{ "command": "npx", "args": ["-y", "@pobruno/blender-agent@latest"] } into
.vscode/mcp.json, then run `npx -y @pobruno/blender-agent --print-skill-dir`
and copy the bundled instructions.md to .github/instructions/blender-agent.instructions.md
plus FLOWS/TOOLS to .github/instructions/blender-agent/. Inject the managed
block from MANAGED-BLOCK.md into .github/copilot-instructions.md. Use
AskUserQuestion before anything destructive. Print the path from
`--print-addon-zip` so I can install it in Blender's Add-ons UI.
```

### Cursor

```
Install @pobruno/blender-agent into this workspace. Read install/AGENT-INSTALL.md
from https://github.com/PoBruno/mcp-blender-agent and run every phase. Merge
{ "command": "npx", "args": ["-y", "@pobruno/blender-agent@latest"] } into
.mcp.json, then run `npx -y @pobruno/blender-agent --print-skill-dir` and copy
the bundled SKILL/FLOWS/TOOLS markdown into ./blender-agent/. Inject the
managed block from MANAGED-BLOCK.md into AGENTS.md. Ask before anything
destructive. Print the path from `--print-addon-zip` so I can install it in
Blender's Add-ons UI.
```

### Codex

```
Install @pobruno/blender-agent into this workspace. Read install/AGENT-INSTALL.md
from https://github.com/PoBruno/mcp-blender-agent and run every phase. Add
{ "command": "npx", "args": ["-y", "@pobruno/blender-agent@latest"] } to the
mcpServers block in ~/.codex/config.toml (create it if absent), then run
`npx -y @pobruno/blender-agent --print-skill-dir` and copy the bundled
SKILL/FLOWS/TOOLS markdown into ./blender-agent/. Inject the managed block
from MANAGED-BLOCK.md into AGENTS.md. Ask before anything destructive. Print
the path from `--print-addon-zip` so I can install it in Blender's Add-ons UI.
```

### Claude Desktop

```
Install @pobruno/blender-agent for me. Read install/AGENT-INSTALL.md from
https://github.com/PoBruno/mcp-blender-agent and run every phase. Merge
{ "command": "npx", "args": ["-y", "@pobruno/blender-agent@latest"] } into
%APPDATA%\Claude\claude_desktop_config.json. Tell me when I need to restart
Claude Desktop. Ask before anything destructive. Print the path from
`npx -y @pobruno/blender-agent --print-addon-zip` so I can install it in
Blender's Add-ons UI.
```

More prompts (smoke test, workflow recipes): [install/PROMPT-TEMPLATES.md](install/PROMPT-TEMPLATES.md)

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
