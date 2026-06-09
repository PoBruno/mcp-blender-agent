# INSTALL.md — manual install reference

Human-readable, step-by-step install. The agent-driven path in [`AGENT-INSTALL.md`](AGENT-INSTALL.md) automates everything below; this file exists as a reference when you want to know exactly what the installer does, or to do it by hand.

> **Prereqs:**
> - Blender **4.2 LTS or newer** (5.x recommended; tested on 5.1.2). On `PATH` or in a default install location.
> - **Node.js 18+** (ships with `npx`).
>
> **Port:** the addon listens on **`9877`** so it coexists with the popular [`ahujasid/blender-mcp`](https://github.com/ahujasid/blender-mcp) on 9876.
>
> **No clone, no build.** The MCP server runs straight from npm via `npx`. The Blender addon zip is bundled inside the npm package.

---

## 1. Wire `blender-agent` into your agent harness

Pick the section that matches your agent. All paths are workspace-relative unless noted.

### 1.1 GitHub Copilot (VS Code)

Create or merge into `.vscode/mcp.json`:

```json
{
  "servers": {
    "blender-agent": {
      "command": "npx",
      "args": ["-y", "@pobruno/blender-agent@latest"],
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

Run **Developer: Reload Window** (Ctrl+Shift+P). The tools appear under the Copilot Chat tool picker. The first call will be slower while `npx` fetches the package.

### 1.2 Claude Code

Create or merge into `.mcp.json` at the workspace root:

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "npx",
      "args": ["-y", "@pobruno/blender-agent@latest"],
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

Close and re-open the Claude Code session.

### 1.3 Cursor

`.mcp.json` at the workspace root (same shape as Claude Code), then **Developer: Reload Window**.

### 1.4 Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "npx",
      "args": ["-y", "@pobruno/blender-agent@latest"],
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

Quit and re-open Claude Desktop.

### 1.5 Windows: `npx` not on PATH

If your harness can't find `npx`, point at the absolute path Node ships:

```json
{
  "command": "C:\\Program Files\\nodejs\\npx.cmd",
  "args": ["-y", "@pobruno/blender-agent@latest"]
}
```

### 1.6 Version pinning (optional, recommended for teams)

Replace `@latest` with a specific version (e.g. `@0.1.0`) so the whole team runs the same code:

```json
"args": ["-y", "@pobruno/blender-agent@0.1.0"]
```

Find the latest version:

```powershell
npm view @pobruno/blender-agent version
```

---

## 2. Install the Blender addon

The npm package bundles `BlenderAgent.zip`. Print its absolute path:

```powershell
npx -y @pobruno/blender-agent@latest --print-addon-zip
```

Output:

```
C:\Users\me\AppData\Local\npm-cache\_npx\<hash>\node_modules\@pobruno\blender-agent\assets\BlenderAgent.zip
```

Then in Blender (the **one manual step** — from outside Blender you can't enable an addon in another running Blender process):

1. Open Blender (any 4.2+ install).
2. **Edit → Preferences → Add-ons → Install...**
3. Paste / navigate to the path above and click **Install Add-on**.
4. In the add-on list search **"BlenderAgent"** and tick the checkbox to enable it.
5. Click the disclosure triangle on the entry. The info panel should say `HTTP server started on port 9877`.
6. (Optional) **Edit → Preferences → Save Preferences** so the addon auto-loads next time you open Blender.

Verify from another terminal:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:9877/server/status -UseBasicParsing | Select-Object -ExpandProperty Content
```

You should see `{"ok": true, "data": { "version": "5.x.x", ... }}`.

---

## 3. Install the passive context skill

The skill makes your agent always know it controls Blender, so it picks the right tools on the first try and runs the see-and-refine loop instead of describing what it would do.

Print the bundled skill directory:

```powershell
npx -y @pobruno/blender-agent@latest --print-skill-dir
```

Then copy the markdown files into your harness:

| Harness | Source filename (under `<skill-dir>`) | Destination |
|---|---|---|
| Claude Code | `SKILL.md`, `FLOWS.md`, `TOOLS.md` | `.claude/skills/blender-agent/<filename>` |
| Copilot | `instructions.md` | `.github/instructions/blender-agent.instructions.md` |
| Copilot | `FLOWS.md`, `TOOLS.md` | `.github/instructions/blender-agent/<filename>` |
| Cursor / generic | `SKILL.md`, `FLOWS.md`, `TOOLS.md` | `blender-agent/<filename>` at workspace root |

Then add the **managed block** from `<skill-dir>/MANAGED-BLOCK.md` (pick the section matching your harness) to your primary instruction file:

- Claude Code → `CLAUDE.md` (or create one)
- Copilot → `.github/copilot-instructions.md` (or create one)
- Cursor → `AGENTS.md` (or create one)

The block has delimiters (`<!-- BEGIN blender-agent ... <!-- END blender-agent -->`). Uninstall removes only the delimited region — never anything outside it.

---

## 4. Verify end-to-end

Ask your agent:

> Use the `server_status` tool and tell me the Blender version.

Expected: `{ ok: true, data: { version: "5.x.x", ... } }`. Then try:

> Launch Blender, create a 1 m cube called `Hello`, then take a viewport snapshot.

The agent should call `blender_launch` → `object_create` → `vision_snapshot` and show you the PNG. If yes, you're done.

---

## 5. Optional environment variables

| Var | Default | Purpose |
|---|---|---|
| `BLENDER_PORT` | `9877` | HTTP port the addon binds to. |
| `BLENDER_HOST` | `127.0.0.1` | HTTP host the MCP server talks to. |
| `BLENDER_BIN` | autodetect | Path to the Blender executable for headless fallback. |
| `BLENDER_TIMEOUT_MS` | `60000` | Per-call HTTP timeout. |
| `BLENDER_AGENT_ALLOW_EXEC_PYTHON` | unset | Set to `1` before launching Blender to enable the `exec_python` tool. Disabled by default ([ADR-008](../.claude/docs/DECISIONS.md)). |

---

## 6. Uninstall

Reverse order:

1. **Managed block** — open your primary instruction file and delete the region between (and including) the `<!-- BEGIN blender-agent` / `<!-- END blender-agent -->` delimiters. Nothing else.
2. **Skill files** — delete the per-harness paths from §3.
3. **MCP config** — open `.mcp.json` / `.vscode/mcp.json` and remove the `blender-agent` key only. Preserve every other server.
4. **npx cache** *(optional)* — `Remove-Item -Recurse -Force "$env:LOCALAPPDATA\npm-cache\_npx\*\node_modules\@pobruno\blender-agent"` (Windows). Frees ~1 MB. Skip if you use the package elsewhere.
5. **Blender addon** — Blender → Edit → Preferences → Add-ons → search "BlenderAgent" → expand → **Remove** → Save Preferences.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `BLENDER_UNREACHABLE` | Addon not enabled OR Blender not running | Enable the addon (§2), or set `BLENDER_BIN` for headless. |
| `BLENDER_NOT_FOUND` | Headless wanted but no `blender` binary | Install Blender 4.2 LTS or set `BLENDER_BIN`. |
| `EXEC_PYTHON_DISABLED` | Calling `exec_python` without the env flag | Set `BLENDER_AGENT_ALLOW_EXEC_PYTHON=1` before Blender starts. |
| `BLENDER_VERSION_UNSUPPORTED` | Blender < 4.2 | Upgrade to 4.2 LTS or newer. |
| `HANDLER_NOT_FOUND` | TS server newer than installed addon | Re-print `--print-addon-zip` and re-install the addon in Blender. |
| Tools don't show up in the agent | MCP config not reloaded, OR npx couldn't fetch | Reload the editor window / restart the agent. Run `npx -y @pobruno/blender-agent --version` in a terminal to confirm. |
| First call hangs for ~30s | Cold `npx` fetch | Expected on first run. Subsequent calls are instant. |
| Two `blender-agent` entries appear | Stale config | Open the relevant MCP config and keep only one entry. |

For anything else, ask your agent to run `server_handlers` and surface every route the addon exposes, then [open an issue](https://github.com/PoBruno/mcp-blender-agent/issues).

---

## 8. Contributor / source install

Want to hack on the MCP server? Don't use npm — work from source:

```powershell
git clone https://github.com/PoBruno/mcp-blender-agent.git
cd mcp-blender-agent/Tools
npm install
npm run build
npm run build:addon-zip
npm test    # needs Blender 4.2 LTS on PATH or BLENDER_BIN
```

Then point your MCP config at the local `dist/index.js` instead of npx:

```json
{
  "command": "node",
  "args": ["D:/path/to/mcp-blender-agent/Tools/dist/index.js"]
}
```

The Blender addon source lives at `BlenderAgent/`. Install the freshly built `Tools/assets/BlenderAgent.zip` in Blender (same GUI steps as §2).

Release flow: tag `v*.*.*` on `main` → GitHub Actions publishes to npm and creates a GitHub Release with the addon zip attached. See [`.github/workflows/publish.yml`](../.github/workflows/publish.yml).
