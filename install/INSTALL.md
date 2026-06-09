# INSTALL.md — manual install reference

Human-readable, step-by-step install. The agent-driven path in [`AGENT-INSTALL.md`](AGENT-INSTALL.md) automates everything below; this file exists as a reference when you want to know exactly what the installer does, or to do it by hand.

> **Prereqs:**
> - Blender **4.2 LTS or newer** (5.x recommended; tested on 5.1.2). On `PATH` or in a default install location.
> - **Node.js 18+** for the MCP server.
> - **git** for the clone.
>
> **Port:** the addon listens on **`9877`** so it coexists with the popular [`ahujasid/blender-mcp`](https://github.com/ahujasid/blender-mcp) on 9876.

---

## 1. Clone the repo

Open your project in your editor (VS Code, Cursor, Claude Code, whatever) so the workspace root is well-defined, then:

```powershell
git clone https://github.com/PoBruno/mcp-blender-agent.git .mcp/blender-agent
```

`.mcp/blender-agent/` is the convention used by the installer. You can put the clone anywhere — just adjust the paths below.

---

## 2. Build the TypeScript MCP server

```powershell
cd .mcp/blender-agent/Tools
npm install
npm run build
cd ../../..
```

This produces `.mcp/blender-agent/Tools/dist/index.js` — the entry point your agent will invoke.

---

## 3. Package the Blender addon

The addon is the Python package at `.mcp/blender-agent/BlenderAgent/`. Zip it so Blender's GUI can install it:

```powershell
Compress-Archive `
  -Path .mcp/blender-agent/BlenderAgent `
  -DestinationPath .mcp/blender-agent/BlenderAgent.zip `
  -Force
```

macOS / Linux:

```bash
cd .mcp/blender-agent && \
  zip -r BlenderAgent.zip BlenderAgent -x '*/__pycache__/*' && \
  cd ../..
```

Verify the zip contains `BlenderAgent/__init__.py` at the **top level** — Blender expects the addon folder, not its contents, at the zip root.

---

## 4. Install the addon in Blender

This is the **one manual step**. From outside Blender you can't enable an addon in another running Blender process.

1. Open Blender (any 4.2+ install).
2. **Edit → Preferences → Add-ons → Install...**
3. Navigate to `.mcp/blender-agent/BlenderAgent.zip` and click **Install Add-on**.
4. In the add-on list search **"BlenderAgent"** and tick the checkbox to enable it.
5. Click the disclosure triangle on the entry. The info panel should say `HTTP server started on port 9877`.
6. (Optional) **Edit → Preferences → Save Preferences** so the addon auto-loads next time you open Blender.

Verify from another terminal:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:9877/server/status -UseBasicParsing | Select-Object -ExpandProperty Content
```

You should see `{"ok": true, "data": { "version": "5.x.x", ... }}`.

---

## 5. Wire into your agent harness

Pick the section that matches your agent. All paths are **relative to the workspace root** unless noted.

### 5.1 GitHub Copilot (VS Code)

Create or merge into `.vscode/mcp.json`:

```json
{
  "servers": {
    "blender-agent": {
      "command": "node",
      "args": [".mcp/blender-agent/Tools/dist/index.js"],
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

**Developer: Reload Window** (Ctrl+Shift+P) and the tools appear under the Copilot Chat tool picker.

### 5.2 Claude Code

Create or merge into `.mcp.json` at the workspace root:

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "node",
      "args": [".mcp/blender-agent/Tools/dist/index.js"],
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

Close and re-open the Claude Code session.

### 5.3 Cursor

`.mcp.json` at the workspace root (same shape as Claude Code), then **Developer: Reload Window**.

### 5.4 Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS). Use **absolute paths** — Claude Desktop has no workspace concept:

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "node",
      "args": ["C:/Users/me/my-project/.mcp/blender-agent/Tools/dist/index.js"],
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

Quit and re-open Claude Desktop.

---

## 6. Install the passive context skill

The skill makes your agent always know it controls Blender, so it picks the right tools on the first try and runs the see-and-refine loop instead of describing what it would do.

Copy these files from `.mcp/blender-agent/install/context-skill/` into your harness:

| Harness | Destination |
|---|---|
| Claude Code | `.claude/skills/blender-agent/SKILL.md`, `FLOWS.md`, `TOOLS.md` |
| Copilot | `.github/instructions/blender-agent.instructions.md` (renamed from `instructions.md`), `.github/instructions/blender-agent/FLOWS.md`, `TOOLS.md` |
| Cursor / generic | `blender-agent/SKILL.md`, `FLOWS.md`, `TOOLS.md` at workspace root |

Then add the **managed block** from `.mcp/blender-agent/install/context-skill/MANAGED-BLOCK.md` (pick the section matching your harness) to your primary instruction file:

- Claude Code → `CLAUDE.md` (or create one)
- Copilot → `.github/copilot-instructions.md` (or create one)
- Cursor → `AGENTS.md` (or create one)

The block has delimiters (`<!-- BEGIN blender-agent ... <!-- END blender-agent -->`). Uninstall removes only the delimited region — never anything outside it.

---

## 7. Verify end-to-end

Ask your agent:

> Use the `server_status` tool and tell me the Blender version.

Expected: `{ ok: true, data: { version: "5.x.x", ... } }`. Then try:

> Launch Blender, create a 1 m cube called `Hello`, then take a viewport snapshot.

The agent should call `blender_launch` → `object_create` → `vision_snapshot` and show you the PNG. If yes, you're done.

---

## 8. Optional environment variables

| Var | Default | Purpose |
|---|---|---|
| `BLENDER_PORT` | `9877` | HTTP port the addon binds to. |
| `BLENDER_HOST` | `127.0.0.1` | HTTP host the MCP server talks to. |
| `BLENDER_BIN` | autodetect | Path to the Blender executable for headless fallback. |
| `BLENDER_TIMEOUT_MS` | `60000` | Per-call HTTP timeout. |
| `BLENDER_AGENT_ALLOW_EXEC_PYTHON` | unset | Set to `1` before launching Blender to enable the `exec_python` tool. Disabled by default ([ADR-008](../.claude/docs/DECISIONS.md)). |

---

## 9. Uninstall

Reverse order:

1. **Managed block** — open your primary instruction file and delete the region between (and including) the `<!-- BEGIN blender-agent` / `<!-- END blender-agent -->` delimiters. Nothing else.
2. **Skill files** — delete the per-harness paths from §6.
3. **MCP config** — open `.mcp.json` / `.vscode/mcp.json` and remove the `blender-agent` key only.
4. **Clone** — `Remove-Item -Recurse -Force .mcp/blender-agent` (only if you don't want it around for other workspaces — the clone is workspace-local, so other workspaces have their own).
5. **Blender addon** — Blender → Edit → Preferences → Add-ons → search "BlenderAgent" → expand → **Remove** → Save Preferences.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `BLENDER_UNREACHABLE` | Addon not enabled OR Blender not running | Enable the addon (§4), or set `BLENDER_BIN` for headless. |
| `BLENDER_NOT_FOUND` | Headless wanted but no `blender` binary | Install Blender 4.2 LTS or set `BLENDER_BIN`. |
| `EXEC_PYTHON_DISABLED` | Calling `exec_python` without the env flag | Set `BLENDER_AGENT_ALLOW_EXEC_PYTHON=1` before Blender starts. |
| `BLENDER_VERSION_UNSUPPORTED` | Blender < 4.2 | Upgrade to 4.2 LTS or newer. |
| `HANDLER_NOT_FOUND` | TS server newer than installed addon | Re-zip and re-install the addon from `.mcp/blender-agent/BlenderAgent/` (§3–4). |
| Tools don't show up in the agent | MCP config not reloaded | Reload the editor window / restart the agent. |
| Two `blender-agent` entries appear | Stale config | Open the relevant MCP config and keep only one entry. |

For anything else, ask your agent to run `server_handlers` and surface every route the addon exposes, then [open an issue](https://github.com/PoBruno/mcp-blender-agent/issues).
