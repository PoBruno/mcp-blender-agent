# MANAGED-BLOCK.md

Per-harness templates of the **managed block** the installer injects into the user's primary instruction file. The block carries delimiters so uninstall removes exactly the inserted region — never anything else.

**Hard rule:** the installer never modifies content outside the delimiters. If a block already exists in the file, replace the region between (and including) the delimiters and leave everything else untouched.

---

## Claude Code → `CLAUDE.md`

```markdown
<!-- BEGIN blender-agent v1 (managed by install/AGENT-INSTALL.md — do not edit by hand) -->
## blender-agent — passive Blender context

The `blender-agent` MCP server is configured for this workspace. It gives you complete, deterministic, undoable control of a live Blender session: modeling, rigging, animation, materials, shader/geometry nodes, lighting, rendering, granular import/export.

Whenever the user asks you to model, rig, animate, texture, light, render, or export anything in 3D — or mentions Blender — **load the skill at [.claude/skills/blender-agent/SKILL.md](.claude/skills/blender-agent/SKILL.md) first.** It carries the operating loop, the tool map, the gotchas, and the failure recovery paths.

For workflow recipes: [.claude/skills/blender-agent/FLOWS.md](.claude/skills/blender-agent/FLOWS.md).
For the full tool reference: [.claude/skills/blender-agent/TOOLS.md](.claude/skills/blender-agent/TOOLS.md).

Always start a session with `blender_launch`, then use the see-and-refine loop (`vision_snapshot` after every mutation). Don't describe — execute.
<!-- END blender-agent -->
```

---

## GitHub Copilot → `.github/copilot-instructions.md`

```markdown
<!-- BEGIN blender-agent v1 (managed by install/AGENT-INSTALL.md — do not edit by hand) -->
## blender-agent — passive Blender context

The `blender-agent` MCP server is configured in [`.vscode/mcp.json`](../.vscode/mcp.json). It gives you complete, deterministic, undoable control of a live Blender session: modeling, rigging, animation, materials, shader/geometry nodes, lighting, rendering, granular import/export.

Per-file rules live in [`.github/instructions/blender-agent.instructions.md`](instructions/blender-agent.instructions.md) and auto-load on every interaction (`applyTo: '**'`). That file carries the operating loop, the tool map, the gotchas, and the failure recovery paths.

For workflow recipes: [`.github/instructions/blender-agent/FLOWS.md`](instructions/blender-agent/FLOWS.md).
For the full tool reference: [`.github/instructions/blender-agent/TOOLS.md`](instructions/blender-agent/TOOLS.md).

Whenever the user asks for anything in 3D, always start with `blender_launch`, then use the see-and-refine loop (`vision_snapshot` after every mutation). Don't describe — execute.
<!-- END blender-agent -->
```

---

## Cursor → `AGENTS.md`

```markdown
<!-- BEGIN blender-agent v1 (managed by install/AGENT-INSTALL.md — do not edit by hand) -->
## blender-agent — passive Blender context

The `blender-agent` MCP server is configured for this workspace (`.mcp.json`). It gives you complete, deterministic, undoable control of a live Blender session: modeling, rigging, animation, materials, shader/geometry nodes, lighting, rendering, granular import/export.

Whenever the user asks you to model, rig, animate, texture, light, render, or export anything in 3D — or mentions Blender — **load [`./blender-agent/SKILL.md`](./blender-agent/SKILL.md) first.** It carries the operating loop, the tool map, the gotchas, and the failure recovery paths.

For workflow recipes: [`./blender-agent/FLOWS.md`](./blender-agent/FLOWS.md).
For the full tool reference: [`./blender-agent/TOOLS.md`](./blender-agent/TOOLS.md).

Always start a session with `blender_launch`, then use the see-and-refine loop (`vision_snapshot` after every mutation). Don't describe — execute.
<!-- END blender-agent -->
```

---

## Claude Desktop

Claude Desktop has no project instruction file equivalent. The MCP entry alone is enough — Claude Desktop will surface the tools globally. If the user wants passive context inside Claude Desktop, suggest they paste the contents of [SKILL.md](SKILL.md) into their "Personal preferences" (Settings → Profile).

The installer does **not** edit any Claude Desktop preferences file beyond `claude_desktop_config.json`.

---

## Delimiter contract

- Open delimiter: `<!-- BEGIN blender-agent v1 ... -->`
- Close delimiter: `<!-- END blender-agent -->`
- The `v1` token bumps when the block schema changes. Re-running the installer with a newer schema will replace older versions.
- Anything outside the delimiters belongs to the user. Don't touch it.
