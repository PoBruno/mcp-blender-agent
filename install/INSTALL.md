# Install — `blender-agent` MCP

End-user install playbook. Pick the section for your harness.

> **Prereq for all paths:** Blender 4.2 LTS or newer (5.x recommended; tested on 5.1.2) installed and either on `PATH` or accessible via the `BLENDER_BIN` env var. Confirm with `blender --version`.
>
> **Port note:** the addon listens on `9877` by default to coexist with the well-known [`blender-mcp`](https://github.com/ahujasid/blender-mcp) plugin (port 9876). Override with the `BLENDER_AGENT_PORT` env var if needed.

---

## 1. Install the Blender addon (one-time)

The addon is the in-process Python plugin that listens on port `9877` and executes every operation.

1. Download `BlenderAgent.zip` from the latest [GitHub Release](https://github.com/PoBruno/mcp-blender-agent/releases) (or zip the `BlenderAgent/` folder from a checkout).
2. Open Blender → **Edit → Preferences → Add-ons → Install…** → pick the zip.
3. Search for **"BlenderAgent"** and tick the checkbox to enable.
4. Save preferences. The HTTP server starts immediately on `http://127.0.0.1:9877`.

Verify it's alive:

```powershell
curl http://127.0.0.1:9877/server/status
```

You should see JSON with `ok: true` and your Blender version.

> **Headless mode:** if you never plan to keep Blender open, skip the addon install — the MCP server will spawn `blender --background` on demand. The addon path is *strongly* preferred for interactive workflows.

---

## 2. Install the MCP server (`@pobruno/blender-agent`)

```powershell
npm install -g @pobruno/blender-agent
# or per-project:
npm install @pobruno/blender-agent
```

Verify the binary is on `PATH`:

```powershell
blender-agent --help
```

---

## 3. Wire into your agent harness

### 3.1 GitHub Copilot (VS Code)

Add to your user `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "blender-agent": {
        "command": "blender-agent",
        "env": { "BLENDER_PORT": "9877" }
      }
    }
  }
}
```

Reload VS Code. The tools appear under the Copilot Chat tool picker.

### 3.2 Claude Code

`~/.config/claude-code/claude_desktop_config.json` (or your platform-specific path):

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "blender-agent",
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

### 3.3 Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "blender-agent",
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

Restart Claude Desktop.

### 3.4 Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "blender-agent": {
      "command": "blender-agent",
      "env": { "BLENDER_PORT": "9877" }
    }
  }
}
```

---

## 4. Verify end-to-end

Ask your agent:

> Use `server_status` and tell me the Blender version.

If it returns `{ ok: true, data: { version: "5.x.x", ... } }`, you're done.

---

## 5. Optional environment variables

| Var | Default | Purpose |
|---|---|---|
| `BLENDER_PORT` | `9877` | HTTP port the addon binds to. |
| `BLENDER_HOST` | `127.0.0.1` | HTTP host the MCP server talks to. |
| `BLENDER_BIN` | autodetect | Path to the Blender executable for headless fallback. |
| `BLENDER_TIMEOUT_MS` | `60000` | Per-call HTTP timeout. |
| `BLENDER_AGENT_ALLOW_EXEC_PYTHON` | unset | Set to `1` to enable the `exec_python` tool. Disabled by default (ADR-008). |

---

## 6. Uninstall

- **Addon:** Edit → Preferences → Add-ons → search "BlenderAgent" → expand → **Remove**.
- **MCP server:** `npm uninstall -g @pobruno/blender-agent`.
- **Harness wiring:** delete the entry from your `settings.json` / `mcp.json`.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `BLENDER_UNREACHABLE` | Addon not enabled OR Blender not running | Enable addon, or set `BLENDER_BIN` for headless. |
| `BLENDER_NOT_FOUND` | Headless wanted but no `blender` binary | Install Blender 4.2 LTS or set `BLENDER_BIN`. |
| `EXEC_PYTHON_DISABLED` | Calling `exec_python` without the env flag | Set `BLENDER_AGENT_ALLOW_EXEC_PYTHON=1` before Blender starts. |
| `BLENDER_VERSION_UNSUPPORTED` | Blender < 4.2 | Upgrade to 4.2 LTS or newer. |
| `HANDLER_NOT_FOUND` | MCP server newer than addon | Reinstall the addon zip from the matching release. |

For anything else, run `server_handlers` to see every route the addon exposes, then [open an issue](https://github.com/PoBruno/mcp-blender-agent/issues).
