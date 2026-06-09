# FLOWS — common Blender workflows via blender-agent

Concrete recipes the agent should follow when the user describes one of these tasks. Each is a deterministic call sequence — no improvisation. Names are MCP tool names exactly as registered.

If the user's task doesn't match a recipe here, fall back to the **see-and-refine loop** from [SKILL.md](SKILL.md).

---

## A — First call of any session

```
1. blender_launch                                  # reuse open Blender or start GUI
2. server_status                                   # confirm version, scene, addon online
3. (optional) object_list                          # see what's in the scene
```

Skip this only if you JUST called `blender_launch` in the same chat turn.

---

## B — Build a primitive blockout

For "make me a cube/sphere/cylinder/etc." style requests.

```
1. object_create { type: <TYPE>, name, location?, size? }
2. object_set_transform { objectName, scale?, rotationEuler? }     # if non-default
3. vision_snapshot { objectNames: [name], angle: "front_top" }
```

Show the snapshot. If the user asked for more than a primitive, switch to flow C or G.

---

## C — Parametric build (chairs, tables, humans)

If the user's intent matches a parametric builder, skip primitive composition and use the library.

```
1. parametric_list                                 # discover available builders
2. parametric_build { builder: <NAME>, params: {...} }
3. vision_contact_sheet { objectNames: [...] }     # 6-angle review
```

Builders shipped at v1.0: `chair_beach`, `table_dining`, `stool_bar`, `human_basic`.

---

## D — Mesh editing pass

When the user wants to modify an existing mesh (add bevel, subdivide, extrude).

```
1. object_set_mode { objectName, mode: "OBJECT" }  # safety — many ops fail in Sculpt/Edit
2. modifier_add or mesh_extrude_region_move or mesh_bevel or mesh_loop_cut
3. (if non-uniform scale present) object_apply_transform { scale: true }
4. vision_snapshot                                  # see the change
```

`mesh_*` ops mutate geometry directly. `modifier_*` is non-destructive — prefer for any "make it smoother / mirror / array" intent.

---

## E — Material authoring

### E.1 — Quick principled

```
1. material_create { name }
2. material_set_principled { materialName, baseColor, roughness?, metallic?, emission? }
3. material_assign_slot { objectName, materialName, slotIndex: 0 }
```

### E.2 — Textured PBR (with image maps)

```
1. material_create_pbr_from_textures {
     name, baseColor: <path>, roughness?, metallic?, normal?, normalSpace: "OpenGL"
   }
2. material_assign_slot { objectName, materialName, slotIndex: 0 }
3. uv_smart_project { objectName }                 # if no UVs yet
```

### E.3 — Procedural via shader nodes

```
1. material_create { name }
2. shader_node_add { materialName, type: "ShaderNodeTexNoise" } → returns nodeName
3. shader_node_add { materialName, type: "ShaderNodeColorRamp" }
4. shader_node_connect_pins { fromNodeName, fromSocket: "Fac", toNodeName, toSocket: "Fac" }
5. shader_node_set_input_value { ... }             # tune
```

---

## F — Rigging a humanoid

```
1. armature_create_biped { name, height: 1.8 }    # 19-bone preset
2. armature_parent_with_auto_weights { armatureObjectName, meshObjectName }
3. armature_validate_ue5_convention                # if shipping to UE5
```

For non-humanoid rigs:

```
1. armature_create { name }
2. bone_add { armatureObjectName, name, head, tail, parent? }   # repeat
3. bone_set_parent { ... }                                       # if hierarchy needed
4. bone_ik_setup                                                  # for IK chains
5. mesh_parent_to_armature { meshObjectName, armatureObjectName }
6. vertex_group_create / vertex_group_assign_vertices             # for manual weights
```

---

## G — Animation pass (idle loop, walk cycle)

```
1. action_create { name: "Idle", useFakeUser: true }          # fake user critical — see Gotchas
2. action_assign_to_object { objectName: <Armature>, actionName: "Idle" }
3. For each pose moment:
   a. bone_set_pose_transform { armatureObjectName, boneName, rotationEuler? OR rotationQuaternion? }
   b. keyframe_bone_pose { armatureObjectName, boneName, frame, channels: ["rotation_euler" or "rotation_quaternion"] }
4. (alternative — batch many bones at once) pose_set { armatureObjectName, frame, pose: {bone1: {...}, bone2: {...}} }
5. nla_track_add { objectName, trackName: "IdleTrack" }
6. nla_push_action_to_strip { objectName, actionName: "Idle", trackName: "IdleTrack", frameStart: 1 }
7. vision_render_action { armatureObjectName, actionName: "Idle", frameStart: 1, frameEnd: 60, step: 5 }
```

**Critical:** the `channels` argument for `keyframe_bone_pose` must match the bone's `rotation_mode`. If you set euler, key euler. Default picks quaternion and your animation silently does nothing.

---

## H — Vision feedback (the see-and-refine loop)

After ANY mutation that affects how the scene looks, snapshot and look.

```
1. vision_snapshot { angle: "front" | "front_top" | "left" | ..., resolution: 512, samples: 4 }
2. (every N iterations) vision_contact_sheet { objectNames: [...], angles: 6 }
3. (final gate before export) vision_topology_inspect + vision_scale_report
```

For animations: `vision_render_action` writes a sprite-strip PNG you can see.

For "is this close to my reference?": `vision_silhouette_compare { referenceImage, outputPath }` returns IoU + a diff heatmap.

---

## I — Export to UE5 / glTF / OBJ

### I.1 — Static mesh to UE5

```
1. object_apply_transform { objectName, scale: true, rotation: true }   # bake transforms
2. mesh_shade_smooth or mesh_shade_flat                                  # explicit choice
3. uv_smart_project                                                       # if no UVs
4. collision_add_convex_hull { objectName }                              # UCX_<name>
5. export_fbx_static { objectNames: [name], filepath, axisForward: "X", axisUp: "Z" }
```

### I.2 — Skeletal mesh + animation to UE5

```
1. armature_validate_ue5_convention { armatureObjectName }
2. export_fbx_skeletal { armatureObjectName, meshObjectNames, filepath }
3. export_fbx_animation { armatureObjectName, actionName, filepath }
```

### I.3 — glTF for the web

```
1. export_gltf { objectNames, filepath, format: "GLB", exportImages: true }
```

---

## J — Render

```
1. render_set_engine { engine: "CYCLES" | "BLENDER_EEVEE_NEXT" }
2. render_set_resolution { width, height, percentage: 100 }
3. render_set_view_transform { viewTransform: "Standard" | "AgX" | "Filmic" }
4. render_set_output { filepath, fileFormat: "PNG", colorMode: "RGBA" }
5. render_render_still
```

For an animation:

```
… same setup …
4. scene_set_frame_range { start, end, fps }
5. render_render_animation
```

---

## K — Batch / atomic multi-op

If you're doing 5+ small ops in a row with no need to inspect between them, the `batch` tool cuts round-trips:

```
batch {
  ops: [
    { path: "/object/create", body: {...} },
    { path: "/object/create", body: {...} },
    { path: "/object/rename", body: {...} },
    ...
  ]
}
```

Stops at the first failure and reports `failedAt`. Don't use this when you need a snapshot between steps.

---

## When you don't know what tool to reach for

```
server_handlers                                    # lists every registered route
```

Then pick the one whose name matches your intent. If still unsure, ask the user before mutating.
