# PROMPT-TEMPLATES.md

Copy any of these into your agent chat to kick off a common workflow.

---

## 1. Install (per harness)

Open your project in your IDE, then paste the matching prompt into your agent. The installer is the same — it lives at [install/AGENT-INSTALL.md](AGENT-INSTALL.md). The only thing that changes is the entry phrasing so each harness knows where to write config.

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

### GitHub Copilot

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

---

## 2. Uninstall

Same prompt for every harness — the installer keeps a delimited managed block so removal is precise.

```
Uninstall @pobruno/blender-agent from this workspace. Follow Phase 7 of
install/AGENT-INSTALL.md from https://github.com/PoBruno/mcp-blender-agent:
remove the managed block from my primary instruction file, delete the skill
files, and remove the `blender-agent` key from my MCP config (preserve every
other entry). Ask before clearing the npx cache. Tell me how to remove the
Blender addon manually since you can't reach into Blender.
```

---

## 3. Smoke test (after install)

```
Using the blender-agent tools, do this:
1. Call blender_launch.
2. Create a new scene called "Smoke" and set it active.
3. Create a 1 m cube called "Hello".
4. Take a vision_snapshot from the front and show me the PNG.
5. Save the file to ./smoke.blend.
6. Render a 256x256 PNG to ./smoke.png with EEVEE.
Show me the responses from each tool.
```

---

## 4. Workflow prompts

### UE5 modular kit (Recipe 4)

```
Using blender-agent, build me a UE5 modular kit:
- Scene unit scale 0.01, 1 unit = 1 cm.
- A collection "Kit_Walls".
- 3 blockout walls 4m x 0.2m x 3m named SM_Wall_A, SM_Wall_B, SM_Wall_C.
- A UCX convex hull collision for each.
- A procedural grid material applied to all three.
- Smart UV unwrap on each.
- Export the whole collection to ./export/ as one .fbx per object with UE5-correct axes.
```

### ARKit-52 face rig (Recipe 3)

```
Using blender-agent:
1. Create a plane called "Face".
2. Ensure all 52 ARKit blendshape keys exist on Face.
3. Set jawOpen=0.6 and eyeBlinkLeft=1.0.
4. Render a single frame to ./face.png.
```

### Character + animation + export (Recipes 1 + 8)

```
Using blender-agent, build me a UE5-compatible humanoid skeleton + idle anim:
1. armature_create_biped at 1.8 m height.
2. Skin a quick capsule body to it.
3. Create an "Idle" action, keyframe a 60-frame breathing loop on the spine.
4. Push the action to an NLA strip.
5. Export rig + action to ./Char_Idle.fbx with UE5 axes.
6. Render a 6-angle contact sheet so I can review.
```

### Procedural material from textures

```
Using blender-agent:
1. Create material "M_Brick" via material_create_pbr_from_textures with
   baseColor=./tex/brick_color.png, roughness=./tex/brick_rgh.png,
   normal=./tex/brick_nrm.png, normalSpace=OpenGL.
2. Assign it to a 4 m plane "Wall".
3. Smart UV unwrap and render.
```

### Geometry-Nodes scatter (Recipe 6)

```
Using blender-agent:
1. Create a 10 m plane "Ground".
2. Create a Geometry Nodes group "ScatterTrees".
3. Inside: DistributePointsOnFaces → InstanceOnPoints with a small cone primitive.
4. Apply the group as a modifier on "Ground".
5. Render the result.
```

### Self-inventory

```
Use server_handlers, then list every export-related tool grouped by file
format (FBX, glTF, OBJ, USD, Alembic). Describe each in one line.
```
