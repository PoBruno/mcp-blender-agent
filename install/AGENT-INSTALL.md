# AGENT-INSTALL — adaptive installer brain

You are installing `@pobruno/blender-agent` for the user. Follow this playbook end-to-end. Do not skip the verify step.

## Phase 1 — Detect

Detect the user's environment in parallel:

1. **OS:** Windows / macOS / Linux.
2. **Blender:** run `blender --version`. Require **4.2 LTS or newer (5.x recommended)**. If missing on `PATH`, check well-known paths:
   - Windows: `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe` (any 5.x), then `4.2`/`4.3`/`4.4`, then `C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe`.
   - macOS: `/Applications/Blender.app/Contents/MacOS/Blender`.
   - Linux: `/usr/bin/blender`, `/usr/local/bin/blender`, `/opt/blender/blender`, `which blender`.
3. **Node:** run `node --version`. Require ≥ 18.
4. **Harness:** look at the user's editor / chat. One of: GitHub Copilot (VS Code), Claude Code, Claude Desktop, Cursor.
5. **Existing install:** check `npm ls -g @pobruno/blender-agent` and probe `http://127.0.0.1:9877/server/status`.

## Phase 2 — Plan

Build a concrete checklist of steps based on Phase 1. Possible items:

- [ ] Install Blender 4.2 LTS or newer (5.x recommended; pick the latest stable) if missing or too old
- [ ] Install the BlenderAgent addon (if not enabled in any detected Blender)
- [ ] `npm install -g @pobruno/blender-agent` (if not installed or outdated)
- [ ] Inject MCP config into the detected harness's config file
- [ ] Restart the harness (if config file was changed)

## Phase 3 — Ask

Present the plan to the user. Ask exactly one consolidated question:

> I'll do the following: \<bulleted plan\>. May I proceed?

Wait for explicit consent before executing anything that mutates the system.

## Phase 4 — Execute

Run each plan item. Do **not** parallelize package installs and config edits — order matters.

For the addon install: prefer scripting via Blender's preferences API. From a terminal:

```bash
blender --background --python-expr "import bpy, os; bpy.ops.preferences.addon_install(filepath='/path/to/BlenderAgent.zip'); bpy.ops.preferences.addon_enable(module='BlenderAgent'); bpy.ops.wm.save_userpref()"
```

For per-harness config: see [INSTALL.md §3](INSTALL.md#3-wire-into-your-agent-harness) for the exact JSON snippets. Merge into the existing file — do not overwrite.

## Phase 5 — Inject the passive context skill

Copy `install/context-skill/SKILL.md` into the harness skill directory so the agent always loads "I control Blender" context on any 3D request. Drop location per harness:

- **Claude Code:** `<project>/.claude/skills/blender-agent-control/SKILL.md` (project) or `~/.claude/skills/blender-agent-control/SKILL.md` (global).
- **Cursor / Cline / Windsurf:** append the skill body into the project rules file the harness reads (e.g. `.cursor/rules/` or `AGENTS.md`), since they have no skill folder.
- **GitHub Copilot:** add a one-line pointer in `.github/copilot-instructions.md` — "On any 3D/Blender request, read `install/context-skill/SKILL.md` first." Copilot has no skill loader; the instructions file is the passive hook.
- **Claude Desktop:** paste the skill body into the conversation's project instructions / a pinned message.

This is what makes the chat *always* know it drives Blender, launches first, and runs the see-and-refine loop — not just "has some tools".

## Phase 6 — Verify

Run, in sequence:

1. Through the harness, invoke **`blender_launch`** — expect `ok: true` (reuses an open Blender or starts a GUI one).
2. Invoke `server_status` — expect `version` matching `^(4|5)\.`.
3. Invoke `server_handlers` — expect a list including `POST /object/create`, `POST /vision/snapshot`, `POST /export/fbx_static`.
4. Optional smoke: `object_create` a cube, then `vision_snapshot` — confirm a PNG is written.

If any step fails, surface the exact error and the matching row from [INSTALL.md §7](INSTALL.md#7-troubleshooting).

## Phase 7 — Report

Tell the user:

- What was installed and where.
- The harness restart status.
- The verification result (the version string Blender returned).
- The first 3 example prompts to try (from [PROMPT-TEMPLATES.md](PROMPT-TEMPLATES.md)).
