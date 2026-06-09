# AGENT-INSTALL.md — the brain

You are an AI coding agent (Claude Code, GitHub Copilot agent mode, Cursor, anything that speaks MCP + has shell + filesystem tools). The user asked you to install `mcp-blender-agent` into the workspace they have open. **You are the installer.** Follow this playbook end to end. Don't skip phases.

This file is the single source of truth for the install. For a human-only manual reference, see [`INSTALL.md`](INSTALL.md). For copy-paste entry prompts, see [`PROMPT-TEMPLATES.md`](PROMPT-TEMPLATES.md). For what gets injected into the user's harness, see [`context-skill/`](context-skill/).

Repo: https://github.com/PoBruno/mcp-blender-agent.

---

## Phases

0. **CONFIRM SCOPE** — describe what you're about to do and wait for "go".
1. **DETECT** — read-only sweep of the workspace, the user's harness, conflicting MCP servers, the local Blender install, and existing instruction files.
2. **PLAN** — adaptive placement of the clone, the skill, the MCP config; conflict proposal.
3. **ASK** — surface picture + plan in one structured batch via `AskUserQuestion` (or harness equivalent). Skip any question with only one reasonable answer.
4. **EXECUTE** — clone repo into the workspace, build the TS server, package the addon zip, merge MCP config.
5. **INJECT** — install the passive context skill into the user's harness and add the delimited managed block to their primary instruction file.
6. **VERIFY** — restart prompt, addon install instructions, health check (`server_status`), sample prompt.
7. **UNINSTALL / REPAIR** — documented reverse path. Same delimiters → clean removal.

Each phase has gates. **Stop at a gate** if information is missing or anything looked unexpected. Don't improvise.

---

## Phase 0 — Confirm scope

Say (adapt to the harness, English or pt-BR depending on the user):

> I'll install `mcp-blender-agent` into the workspace you have open. I'll do this in 6 phases:
>
> 1. **Detect** what you already have (workspace, agent harness, MCP servers, Blender install, instructions) — read-only.
> 2. **Plan** the install adaptively based on what I find.
> 3. **Ask** you to confirm any decisions that aren't obvious.
> 4. **Execute** — clone the repo into `.mcp/blender-agent/`, build the TypeScript server, package the addon as a zip.
> 5. **Inject** the passive Blender context skill into your harness so your agent has Blender know-how in every interaction.
> 6. **Verify** with a health check and sample prompts.
>
> One manual step: you install the addon zip in Blender's Add-ons preferences yourself — I can't reach into a separate Blender process to enable a plugin.
>
> Total time: 2–5 minutes plus the Blender addon install (~30s). Proceed?

Wait for confirmation.

---

## Phase 1 — DETECT (read-only)

Do all of this without modifying anything. Collect a JSON-shaped picture you'll use in Phase 2.

### 1.1 — Workspace root

The clone lives **inside the workspace the user has open** (matches `mcp-unreal-agent`'s pattern). Resolve the workspace root from your harness:

- VS Code / Copilot: the open folder (`${workspaceFolder}`).
- Claude Code: the directory `claude` was launched in (CWD of the agent process).
- Cursor: same as VS Code.
- Claude Desktop: no workspace concept — ask the user for an absolute path to a folder where the clone should live.

If you cannot resolve a workspace, **stop and ask** for an absolute path.

Note whether `.mcp/blender-agent/` already exists at the workspace root (re-install path).

### 1.2 — Harness type

Look for these markers (read, never write):

| Harness | Markers |
|---|---|
| **Claude Code** | `.claude/` directory and/or `CLAUDE.md` at project root, `.mcp.json` |
| **GitHub Copilot** | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.vscode/mcp.json`, `.vscode/settings.json` with `mcp` key |
| **Cursor** | `AGENTS.md`, `.cursor/`, `.cursor/rules/` |
| **Claude Desktop** | none in-workspace — flag as a candidate; ask the user |

A workspace may have several. **Record all that are present** — the user might use more than one.

### 1.3 — Existing MCP servers

Read every MCP config file found in 1.2 and list each registered server. Flag any whose `command` / `args` look Blender-related (substring match on `blender`, `blender-mcp`, `bpy`) or any binding port `9877`. These are **candidates to centralize** in Phase 3.

The popular `ahujasid/blender-mcp` on port **9876** is NOT a conflict — we deliberately use 9877 to coexist. Leave it alone.

### 1.4 — Existing instructions / rules / skills

Walk these read-only and record paths only (not contents):

- `CLAUDE.md`, `.claude/rules/**`, `.claude/skills/**`, `.claude/commands/**`
- `.github/copilot-instructions.md`, `.github/instructions/**`, `.github/prompts/**`
- `AGENTS.md`, `.cursor/rules/**`

This tells you **where the passive skill should go** so it doesn't collide with the user's content and so its reference can be added to the right primary instruction file.

### 1.5 — Blender install

```powershell
# Windows — check well-known locations + PATH
$blender = (Get-Command blender -ErrorAction SilentlyContinue).Path
if (-not $blender) {
    $candidates = @(
        "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
    )
    $blender = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if ($blender) { & $blender --version }
```

Linux / macOS equivalents: `which blender`, `/Applications/Blender.app/Contents/MacOS/Blender --version`, `/usr/bin/blender --version`.

Require **Blender 4.2 LTS or newer (5.x recommended)**. If older or missing, surface it — don't try to install Blender for the user.

### 1.6 — Blender addons directory

Record the path where the user's Blender looks for addons. The standard locations:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\` |
| macOS | `~/Library/Application Support/Blender/<version>/scripts/addons/` |
| Linux | `~/.config/blender/<version>/scripts/addons/` |

`<version>` matches the Blender major.minor (e.g. `5.1`, `4.2`). This is informational for Phase 6 — the user installs the zip via the GUI; you don't write into this folder.

### 1.7 — Prereqs

```powershell
node --version       # need 18+
git --version
```

If Node is missing or < 18, surface and stop — don't try to install Node for the user.

### 1.8 — Build the picture

End of Phase 1, you should have something like:

```json
{
  "workspace": { "root": "C:/Users/me/my-project", "cloneAlreadyExists": false },
  "harness": ["claude-code", "copilot"],
  "mcpConfigs": {
    "claude": { "path": ".mcp.json", "servers": ["my-other-mcp"] },
    "copilot": { "path": ".vscode/mcp.json", "servers": ["blender-mcp"] }
  },
  "conflicts": [],
  "instructions": {
    "claude": ["CLAUDE.md", ".claude/rules/python.md"],
    "copilot": [".github/copilot-instructions.md"]
  },
  "blender": { "binary": "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe", "version": "5.1.2", "addonsDir": "C:/Users/me/AppData/Roaming/Blender Foundation/Blender/5.1/scripts/addons" },
  "prereqs": { "node": "20.10.0", "git": "2.43" }
}
```

Hold this picture in working memory for Phase 2.

---

## Phase 2 — PLAN (adaptive placement)

Derive the proposal from the detected picture. Don't ask anything yet.

### 2.1 — Pick a primary harness

If multiple harnesses were detected, default order: **Claude Code → Copilot → Cursor → Claude Desktop**. If only one, that's the primary. The user will confirm in Phase 3.

### 2.2 — Decide clone location

Default: `<workspace>/.mcp/blender-agent/`. Hidden directory at the workspace root, consistent with `.vscode`, `.github`, `.claude`. The user can override in Phase 3 if they prefer a different location (e.g. `tools/blender-agent/` for visibility).

### 2.3 — Decide skill placement

| Primary harness | Skill files go to | Managed block goes into |
|---|---|---|
| Claude Code | `.claude/skills/blender-agent/{SKILL,FLOWS,TOOLS}.md` | `CLAUDE.md` |
| Copilot | `.github/instructions/blender-agent.instructions.md` + `.github/instructions/blender-agent/{FLOWS,TOOLS}.md` | `.github/copilot-instructions.md` |
| Cursor / generic | `blender-agent/{SKILL,FLOWS,TOOLS}.md` at workspace root | `AGENTS.md` |

If a primary instruction file doesn't exist, the plan **creates a minimal one** whose body is the managed block (so the skill is reachable). The user will confirm.

### 2.4 — Decide MCP config target

- Claude Code → `.mcp.json` at workspace root (`mcpServers.blender-agent`).
- Copilot → `.vscode/mcp.json` (`servers.blender-agent`).
- Cursor → `.mcp.json` like Claude Code.
- Claude Desktop → `%APPDATA%\Claude\claude_desktop_config.json` (Windows) / `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) with **absolute paths**. **Always ask** before touching this one (global).

### 2.5 — Conflict proposal

For each conflict from 1.3, decide a default recommendation:

- **Another `mcp-blender-agent` already configured** (different path) → recommend `replace with this install`.
- **Port 9877 bound by another server** → recommend `disable that one OR change its port` (we can't move ours at runtime currently).
- **`ahujasid/blender-mcp` on port 9876** → **not a conflict**, leave it alone. Document the coexistence.
- **Unrelated MCP** (`tavily`, `github`, etc.) → recommend `keep both`.

### 2.6 — Build / re-install step

- `cloneAlreadyExists == true` and `Tools/dist/index.js` exists → recommend `update via git pull + npm install + npm run build`.
- Fresh → recommend `clone + build`.
- For the addon, you ALWAYS produce a fresh zip from the cloned `BlenderAgent/` folder so the version matches what the TS server expects.

End of Phase 2: you have a proposal you can show.

---

## Phase 3 — ASK (structured)

Surface the picture + proposal in one batch with `AskUserQuestion` (or your harness's equivalent). Ask each question only if it has more than one reasonable answer. If only one harness was detected, no MCPs conflict, and no instruction file collisions exist, you can skip straight to confirming the whole plan as a single question.

Recommended questions:

1. **Confirm harness.** "I detected `<list>`. Which is your primary?" *(options: each detected + "all of them"; recommended = first in order)*
2. **Clone location.** "I'll clone into `<workspace>/.mcp/blender-agent/`. OK?" *(options: `OK (recommended)`, `Use a different path — let me specify`)*
3. **Conflicting MCPs.** *(only if `conflicts.length > 0`)* "I found `<server-name>` in `<config-path>` — it overlaps with `blender-agent`. What do you want to do?" *(options: `Replace it (recommended)`, `Keep both — let me pick later`, `Remove that one`)*
4. **Context skill placement.** "I'll install the passive Blender context skill at `<path>` and reference it from `<primary instruction file>` via a delimited managed block. OK?" *(options: `OK`, `Place skill elsewhere — let me specify`)*
5. **Claude Desktop?** *(only if Claude Desktop is a candidate but not the primary in-workspace harness)* "I won't touch `%APPDATA%\Claude\claude_desktop_config.json` unless you say so. Want me to add the entry there too?" *(options: `No`, `Yes, with absolute paths`)*

For every "yes" option that involves a destructive action (replace a server, overwrite a file), preview the diff before applying in Phase 4.

---

## Phase 4 — EXECUTE

Each substep is idempotent. If something fails, **stop** and tell the user — don't try to "fix" the workspace.

### 4.1 — Clone or update the repo

```powershell
$cloneDir = Join-Path $workspace.root ".mcp/blender-agent"
New-Item -ItemType Directory -Force -Path (Split-Path $cloneDir) | Out-Null

if (Test-Path $cloneDir) {
    Push-Location $cloneDir
    git pull --ff-only
    Pop-Location
} else {
    git clone https://github.com/PoBruno/mcp-blender-agent.git $cloneDir
}
```

If `git pull` fails because the user has local changes, surface and stop.

### 4.2 — Build the TS server

```powershell
Push-Location (Join-Path $cloneDir "Tools")
npm install
npm run build
Pop-Location
```

Verify `Tools/dist/index.js`. If `npm install` fails because Node is < 18, surface and stop — don't try to upgrade Node for the user.

### 4.3 — Package the addon as a zip

The addon is a single Python package at `<clone>/BlenderAgent/`. Zip it so the user can install via Blender's GUI in Phase 6.

```powershell
$addonSource = Join-Path $cloneDir "BlenderAgent"
$addonZip    = Join-Path $cloneDir "BlenderAgent.zip"
if (Test-Path $addonZip) { Remove-Item $addonZip }
Compress-Archive -Path $addonSource -DestinationPath $addonZip
```

On macOS / Linux:

```bash
cd "$cloneDir" && zip -r BlenderAgent.zip BlenderAgent -x '*/__pycache__/*'
```

Verify the zip contains `BlenderAgent/__init__.py` at the top (Blender expects the addon folder, not its contents, at the root).

### 4.4 — Disable / replace conflicting MCP servers (if approved in Phase 3)

For each `replace` decision, **remove the conflicting server's entry** from its MCP config file. Preserve every other entry. If the user said `Keep both`, leave them alone.

### 4.5 — Merge our MCP config

Per primary harness (and any extra approved in Phase 3). Use **relative paths** for in-workspace harnesses, **absolute paths** for Claude Desktop.

**Claude Code — `.mcp.json` (workspace root)**
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

**Copilot — `.vscode/mcp.json`**
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

**Cursor — same as Claude Code (`.mcp.json` at workspace root).**

**Claude Desktop** — `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS). Use **absolute paths**:

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

Always **merge — never overwrite**. If `blender-agent` already exists, replace its entry only. Preserve every other server entry.

---

## Phase 5 — INJECT (the passive context skill)

This phase is the headline. It's why the user gets value in every subsequent interaction, not just when they explicitly ask the agent to "use blender-agent".

### 5.1 — Copy the skill files

From the clone's `install/context-skill/` directory **into the user's harness location** picked in Phase 2:

**Claude Code:**
- `install/context-skill/SKILL.md` → `.claude/skills/blender-agent/SKILL.md`
- `install/context-skill/FLOWS.md` → `.claude/skills/blender-agent/FLOWS.md`
- `install/context-skill/TOOLS.md` → `.claude/skills/blender-agent/TOOLS.md`

**Copilot:**
- `install/context-skill/instructions.md` → `.github/instructions/blender-agent.instructions.md`
- `install/context-skill/FLOWS.md` → `.github/instructions/blender-agent/FLOWS.md`
- `install/context-skill/TOOLS.md` → `.github/instructions/blender-agent/TOOLS.md`

**Cursor / generic:**
- `install/context-skill/SKILL.md` + `FLOWS.md` + `TOOLS.md` → `blender-agent/` at workspace root

Files are copied **as-is**. Don't edit them — they're the canonical source.

### 5.2 — Inject the managed block

Open the primary instruction file (`CLAUDE.md` / `.github/copilot-instructions.md` / `AGENTS.md`).

- If a managed block already exists (look for the delimiters `<!-- BEGIN blender-agent` / `<!-- END blender-agent -->`), **replace the region between (and including) them** with the new block.
- If no managed block exists, **append** the new block to the end of the file (with a leading blank line).

Use the exact block from [`context-skill/MANAGED-BLOCK.md`](context-skill/MANAGED-BLOCK.md) for the user's primary harness. **Do not modify content outside the delimiters.**

If the primary instruction file doesn't exist, create a minimal one whose only content is the managed block (with a one-line preface like `# Project instructions`).

### 5.3 — Verify injection

Re-read the file. Confirm both delimiters are present exactly once. If you see two `BEGIN`s, you have a bug — surface to the user.

---

## Phase 6 — VERIFY + first run

### 6.1 — Install the Blender addon (manual user step)

Display these exact instructions, with the real absolute path to the zip:

> ⚠️ **Manual step (~30s).** I can't reach into Blender to enable an addon for you. Please:
>
> 1. Open Blender.
> 2. **Edit → Preferences → Add-ons → Install...**
> 3. Navigate to `<absolute path to BlenderAgent.zip>` and click **Install Add-on**.
> 4. In the add-on list, search **"BlenderAgent"** and tick the checkbox to enable it.
> 5. Click the disclosure triangle on the add-on entry — the panel should say `HTTP server started on port 9877`.
> 6. (Optional) **Edit → Preferences → Save Preferences** so it auto-loads next time.
>
> Tell me when it's enabled.

Wait.

### 6.2 — Restart prompt

Once the user confirms the addon is enabled, say:

> Now please restart your coding agent so it picks up the new MCP config:
>
> - **Claude Code:** close and re-open the session.
> - **VS Code (Copilot):** **Developer: Reload Window** (Ctrl+Shift+P).
> - **Cursor:** **Developer: Reload Window**.
> - **Claude Desktop:** quit and re-open the app.
>
> Tell me when it's restarted — I'll run the health check.

Wait.

### 6.3 — Health check

Once the user confirms the restart, call the `server_status` MCP tool. Expected:

```json
{ "ok": true, "data": { "version": "5.1.2", "scene": "Scene", "mode": "blender-agent", "addonVersion": "0.0.1", "execPythonAllowed": false } }
```

If `ok == true` and `version` starts with `4.` or `5.` → install succeeded.

Diagnostics:

- `BLENDER_UNREACHABLE` → addon not enabled or Blender not running. Re-check Phase 6.1.
- Tool isn't available in the agent at all → the MCP config wasn't reloaded. Have them restart the agent / reload the window again.
- Wrong Blender version returned → user enabled the addon in a different Blender install than what was detected in Phase 1.5. Ask which Blender they want to drive.

### 6.4 — Confirm the skill loaded

Ask the agent (in the user's chat, not via MCP):

- Claude Code: *"What does the blender-agent skill say I should call before any modeling?"*
- Copilot: *"What does my `blender-agent.instructions.md` say about the operating loop?"*

A correct answer mentions `blender_launch` and the see-and-refine loop. A blank / "I don't know" answer means the managed block isn't in the right file or the harness didn't reload.

### 6.5 — Sample prompts

Suggest 2–3 concrete prompts:

> Try one of these to confirm full control:
>
> 1. *"Launch Blender, create a 1 m cube called Hello, then take a viewport snapshot."*
> 2. *"Build a beach chair using the parametric library and render a contact sheet."*
> 3. *"List every export tool you have, grouped by file format."*

Install complete.

---

## Phase 7 — UNINSTALL / REPAIR

The whole install is reversible. Use this when the user asks to remove or when something corrupted partway and they want a clean slate.

### 7.1 — Remove the managed block

For each harness the install touched, open the primary instruction file and **remove the region between (and including) the `<!-- BEGIN blender-agent` / `<!-- END blender-agent -->` delimiters**. If the only thing left in a file the installer created is whitespace, remove that file too. **Never touch content outside the delimiters.**

### 7.2 — Remove the skill files

```powershell
# Claude Code
Remove-Item -Recurse -Force "$workspace/.claude/skills/blender-agent" -ErrorAction SilentlyContinue
# Copilot
Remove-Item -Force "$workspace/.github/instructions/blender-agent.instructions.md" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$workspace/.github/instructions/blender-agent" -ErrorAction SilentlyContinue
# Cursor / generic
Remove-Item -Recurse -Force "$workspace/blender-agent" -ErrorAction SilentlyContinue
```

### 7.3 — Remove the MCP config entry

Open each MCP config the installer wrote and **remove only the `blender-agent` key**. Preserve everything else.

### 7.4 — Remove the clone (ask first)

```powershell
Remove-Item -Recurse -Force "$workspace/.mcp/blender-agent"
```

Ask before doing this — the user may have local edits. If `.mcp/` is now empty, remove it too.

### 7.5 — Disable / remove the Blender addon (manual)

Tell the user:

> The Blender addon stays installed in your Blender preferences. To remove:
>
> 1. Open Blender → **Edit → Preferences → Add-ons**.
> 2. Search **"BlenderAgent"**, expand the entry, click **Remove**.
> 3. **Save Preferences**.

You can't do this for them from outside Blender.

### 7.6 — Report

Tell the user exactly what was removed and what wasn't, and remind them to restart their agent so the MCP config reload sticks.

### Repair (partial install)

If a previous install failed mid-flow: run Phase 7 first to clear stale state, then Phase 1 → 6 fresh.

---

## Hard rules across all phases

- **Never** delete or rewrite a file the installer didn't create unless removing exactly the delimited managed block.
- **Never** use `git add -A` or any wildcard write outside of paths under `.mcp/blender-agent/`, the user's MCP config files, the user's primary instruction file, and the skill output paths.
- **Never** silently change a setting that already exists with a different value — surface to the user.
- **Never** install Blender or Node for the user. Surface a missing prereq and stop.
- **Never** reach into Blender to enable an addon. That's the user's manual step in Phase 6.1.
- **If you don't know, ask.** Use `AskUserQuestion` — never guess at a workspace root, a Blender version, an agent type, or a path to a global config file.
- **Stop on first hard failure.** Surface exact output. Don't auto-retry a non-transient error.
