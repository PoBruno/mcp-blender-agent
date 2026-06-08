---
name: install
description: Step-by-step playbook for installing mcp-blender-agent into an end user's agent harness (Claude Code / Copilot / Cursor / Claude Desktop). Read when the user asks to install the MCP or follow the install prompt.
---

# Install playbook (skill placeholder)

The full installer brain lives at [`install/AGENT-INSTALL.md`](../../../install/AGENT-INSTALL.md). It is **not finalized yet** — it lands in Phase 5 of the roadmap.

When the user asks you to install `blender-agent` into their setup, follow [`install/AGENT-INSTALL.md`](../../../install/AGENT-INSTALL.md) end to end. Until that file exists in full form, use the temporary skeleton at [`install/INSTALL.md`](../../../install/INSTALL.md) which lists manual steps.

## Why this skill exists now (before Phase 5)

So that the installer surface area is reserved and the agent has somewhere to land when asked. The full content (detect → plan → ask → execute → inject → verify → uninstall) mirrors `mcp-unreal-agent`'s `install/AGENT-INSTALL.md`.

## High-level shape (preview)

1. **Detect** — OS, Blender version, agent harness, conflicts.
2. **Plan** — primary harness, addon install path, MCP config entry, managed instruction block.
3. **Ask** — confirm with user.
4. **Execute** — install addon, install TS server, merge MCP config.
5. **Inject** — copy passive context skill into the harness, add managed block.
6. **Verify** — call `server_status` end-to-end.
7. **Uninstall** — strip managed block, remove skill files, remove MCP entry, disable addon. Leaves `.blend` files alone.

For Blender specifically (vs UE):
- No build step. The addon is a folder + `bl_info` dict.
- Install via `blender --background --python-expr "bpy.ops.preferences.addon_install(filepath='...'); bpy.ops.preferences.addon_enable(module='BlenderAgent')"`.
- No source-control complications (no `.uproject` to edit).
- Headless verification is trivial — same `--background` invocation we use in CI.
