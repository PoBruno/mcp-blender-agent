# Prompt templates

Copy any of these into your agent chat to kick off common workflows.

---

## Install

```
Install the @pobruno/blender-agent MCP server for me. Detect my OS, check that Blender 4.2 LTS or newer (5.x recommended) is available, install the BlenderAgent Blender addon, install the npm package, wire it into my agent harness on port 9877 (to coexist with the existing blender-mcp on 9876), and verify it works end-to-end by calling server_status. Follow the install/AGENT-INSTALL.md playbook in the repo.
```

---

## Smoke test (no Blender experience needed)

```
Using the blender-agent tools, do this:
1. Create a new scene called "Smoke" and set it active.
2. Create a 1m cube called "Hello".
3. Save the file to ./smoke.blend.
4. Render a 256x256 PNG to ./smoke.png with EEVEE.
Show me the responses from each tool.
```

---

## UE5 modular kit (Recipe 4)

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

---

## ARKit-52 face rig (Recipe 6)

```
Using blender-agent:
1. Create a plane called "Face".
2. Ensure all 52 ARKit blendshape keys exist on Face.
3. Set jawOpen=0.6 and eyeBlinkLeft=1.0.
4. Render a single frame to ./face.png.
```

---

## Animation export

```
Using blender-agent:
1. Create an armature called "TestRig" with a Root bone.
2. Create a "Wave" action and assign it to TestRig.
3. Keyframe the Root pose rotation at frames 1, 15, 30.
4. Push the action to an NLA strip called "WaveTrack".
5. Export the rig + animation as ./TestRig_Wave.fbx, UE5-compatible.
```

---

## Geometry-Nodes scatter

```
Using blender-agent:
1. Create a 10m plane "Ground".
2. Create a Geometry Nodes group "ScatterTrees".
3. Inside it add DistributePointsOnFaces, then InstanceOnPoints with a small cone primitive.
4. Apply the group as a modifier on "Ground".
5. Render the result.
```

---

## Composite undo check

```
Use the blender-agent server_handlers tool, then list the names of every export-related tool. After that, describe what each one does in one line.
```
