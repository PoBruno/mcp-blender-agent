# PROMPT-TEMPLATES.md

Copy any of these into your agent chat to kick off a common workflow.

---

## 1. Install (per harness)

Open your project in your IDE, then paste the matching prompt into your agent. The installer is the same — it lives at [install/AGENT-INSTALL.md](AGENT-INSTALL.md). The only thing that changes is the entry phrasing so each harness knows where to write config.

### Claude Code

```
Install https://github.com/PoBruno/mcp-blender-agent into this workspace.
Follow install/AGENT-INSTALL.md from that repo end to end. Clone into
.mcp/blender-agent, build the TS server, package the addon zip, merge MCP
config into .mcp.json, inject the passive context skill into
.claude/skills/blender-agent/ and reference it via a delimited managed block
in CLAUDE.md. Use AskUserQuestion before anything destructive. Tell me the
exact path to BlenderAgent.zip so I can install it in Blender's Add-ons UI.
```

### GitHub Copilot

```
Install https://github.com/PoBruno/mcp-blender-agent into this workspace.
Read install/AGENT-INSTALL.md from that repo and run every phase. Clone into
.mcp/blender-agent, build the TS server, package the addon zip, write the
MCP config to .vscode/mcp.json, inject the passive context skill into
.github/instructions/blender-agent/ and reference it via a delimited managed
block in .github/copilot-instructions.md. Use AskUserQuestion before anything
destructive. Tell me the exact path to BlenderAgent.zip so I can install it
in Blender's Add-ons UI.
```

### Cursor

```
Install https://github.com/PoBruno/mcp-blender-agent into this workspace.
Follow install/AGENT-INSTALL.md from that repo end to end. Clone into
.mcp/blender-agent, build the TS server, package the addon zip, merge MCP
config into .mcp.json, inject the passive context skill into ./blender-agent/
and reference it via a delimited managed block in AGENTS.md. Ask before
anything destructive. Tell me the exact path to BlenderAgent.zip so I can
install it in Blender's Add-ons UI.
```

### Claude Desktop

```
Install https://github.com/PoBruno/mcp-blender-agent into the folder I'll
tell you. Follow install/AGENT-INSTALL.md from that repo end to end. Clone
into <FOLDER>/.mcp/blender-agent, build the TS server, package the addon zip,
add the MCP entry to %APPDATA%\Claude\claude_desktop_config.json with
absolute paths, inject the passive context skill, and tell me when I need to
restart Claude Desktop. Ask before anything destructive. Tell me the exact
path to BlenderAgent.zip so I can install it in Blender's Add-ons UI.

Workspace folder: <PASTE ABSOLUTE PATH HERE>
```

---

## 2. Uninstall

Same prompt for every harness — the installer keeps a delimited managed block so removal is precise.

```
Uninstall the blender-agent MCP from this workspace. Follow Phase 7 of
install/AGENT-INSTALL.md inside .mcp/blender-agent: remove the managed block
from my primary instruction file, delete the skill files, remove the
blender-agent key from my MCP config (preserve every other entry), and ask
me before deleting the clone itself. Tell me how to remove the Blender addon
manually since you can't reach into Blender.
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
