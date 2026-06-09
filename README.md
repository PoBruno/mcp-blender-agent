# mcp-blender-agent

> Complete Blender control plane for AI coding agents — MCP server giving Claude Code, GitHub Copilot, Cursor, and any MCP-speaking agent full control of a Blender session: modeling, rigging, animation, materials, shader/geometry nodes, rendering, and granular export to FBX / glTF / USD / Alembic.

Sister project to [PoBruno/mcp-unreal-agent](https://github.com/PoBruno/mcp-unreal-agent). Same architecture, same contracts, same harness — the Blender twin.

---

## ⚡ Install in one prompt

Open your project in your editor, then paste the matching prompt into your agent chat. The MCP server runs straight from npm via `npx` — **no clone, no build**. The Blender addon zip is bundled inside the npm package; the agent will print its path so you can drop it into Blender's Add-ons UI. Prereqs: **Blender 4.2 LTS+ (5.x recommended)**, **Node 18+**.

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

One manual step you'll do yourself: install `BlenderAgent.zip` (path printed by `--print-addon-zip`) via Blender → Edit → Preferences → Add-ons → Install... — the agent can't reach into a separate Blender process to enable a plugin.

After install, the agent reads the bundled `SKILL.md` on every 3D request — so it always knows it drives Blender, launches first, and runs the see-and-refine loop. Manual install reference: [install/INSTALL.md](install/INSTALL.md). More copy-paste workflow prompts: [install/PROMPT-TEMPLATES.md](install/PROMPT-TEMPLATES.md).

---

## Why this exists

The Blender MCP space today is dominated by **creative toys**: "make a dungeon scene", "apply a red metallic material". Those exist (see [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp), 22k+ stars) and they're great for ideation.

`blender-agent` is different. It is a **production control plane**:

- Every Blender operator and `bpy.data` mutation surfaces as a typed MCP tool with a Zod input schema and a structured `{ok, data, refs, nextSteps, warnings, errorCode}` output.
- Composite atomic flows wrap multi-step mutations in a single undo push.
- ID-chaining makes multi-tool workflows feel like dataflow — no string parsing on the agent side.
- Granular export — every parameter of `bpy.ops.export_scene.fbx` / `export_scene.gltf` / `wm.usd_export` / `wm.alembic_export` is a tool input, not a black box.
- Install brain detects the user's agent harness (Claude / Copilot / Cursor / Claude Desktop) and configures itself.
- Passive context skill — always-on guidance the agent reads before touching Blender, so it picks the right tool the first time.

The agent should be able to describe a low-poly character — bones, weights, sockets, idle animation, vertex naming, dimensions, texture layout, export target — and have it built end-to-end.

---

## What you get

Two parts, mirroring `mcp-unreal-agent`:

- **`BlenderAgent/` — Python addon** that lives inside Blender (or runs headless via `blender --background`). Hosts an HTTP server on port `9877` (different from the dominant `blender-mcp` plugin on 9876 — they coexist). Calls `bpy.data`, `bpy.ops`, `bmesh`, `mathutils` directly. No build step.
- **`Tools/` — TypeScript MCP server.** Translates MCP tool calls from the agent into HTTP calls to the addon. Ships the structured tool contract, ID-chain, error registry, install brain, and passive context skill.

Two serving modes:

- **Addon (preferred):** auto-starts when Blender opens. Zero overhead.
- **Headless:** spawned by the TS server when no Blender instance is detected. Used for CI, batch ops, and first-time install verification.

---

## Status

**Sprints 0–6 shipped. v1.0 candidate on Blender 5.1.2.** Addon (41 handler modules, 212 routes), TS server (20 tool files, ~216 MCP tools), full integration suite — **211 cases passing** on real Blender 5.1.2 (Steam install, port 9877 coexisting with ahujasid `blender-mcp` on 9876). Distributed as the `@pobruno/blender-agent` npm package (server + bundled Blender addon zip + passive context skill); GitHub Actions publishes on tag push to `main`. One-prompt install via `npx -y @pobruno/blender-agent@latest`. See [.claude/docs/SPRINTS.md](.claude/docs/SPRINTS.md) for the per-task done log.

---

## Quick start (manual — for contributors)

```powershell
git clone https://github.com/PoBruno/mcp-blender-agent.git
cd mcp-blender-agent/Tools
npm install
npm run build
npm run build:addon-zip
# Need Blender 4.2 LTS or newer (5.x recommended) on PATH (or BLENDER_BIN) to run the integration tests:
npm test
```

End users: use the one-prompt install above — `npx` fetches the published package, no clone needed.

End-user install reference: [install/INSTALL.md](install/INSTALL.md). Agent-driven install playbook: [install/AGENT-INSTALL.md](install/AGENT-INSTALL.md). Copy-paste prompts: [install/PROMPT-TEMPLATES.md](install/PROMPT-TEMPLATES.md).

---

## Documentation

- **[OBJECTIVES.md](OBJECTIVES.md)** — what we are building and why, success criteria, non-goals.
- **[ROADMAP.md](ROADMAP.md)** — 5-phase delivery plan with milestones.
- **[CLAUDE.md](CLAUDE.md)** — agent entry point. Tech stack, conventions, commands, doc index. Read first.
- **[AGENTS.md](AGENTS.md)** — universal bridge for Cursor and other agents.
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — GitHub Copilot harness (delegates to CLAUDE.md).
- **[.claude/docs/ARCHITECTURE.md](.claude/docs/ARCHITECTURE.md)** — system bible.
- **[.claude/docs/DECISIONS.md](.claude/docs/DECISIONS.md)** — ADRs.

---

## Reference repositories

Read-only clones live under `ref/` (gitignored). They exist so the agent and developers can study prior art:

- `ref/blender-mcp/` — [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp), the dominant Blender MCP. Reference for the addon socket pattern and Claude Desktop integration.
- `ref/blender-ai-mcp/` — [PatrykIti/blender-ai-mcp](https://github.com/PatrykIti/blender-ai-mcp), goal-first routing and curated tools. Reference for production-shaped tool design.

To refresh:

```powershell
cd ref
git -C blender-mcp pull
git -C blender-ai-mcp pull
```

We **never** copy code verbatim from these. We study, take inspiration, build our own to our contract.

---

## License

MIT. See [LICENSE](LICENSE).

Not affiliated with the Blender Foundation. "Blender" is a trademark of the Blender Foundation.
