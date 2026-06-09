# WORKFLOW-RECIPES.md

End-to-end recipes — concrete sequences of tool calls that take an agent from "empty `.blend`" to "asset usable in UE5". Each recipe is a chained, deterministic flow.

These recipes are what `nextSteps[]` hints from individual tools should point toward. They are also the basis for the v1.0 integration test suite — every recipe gets at least one happy-path test.

**Conventions:**
- `[]` = tool call boundaries
- `→ refs.X="Y"` = produced reference value the next call consumes
- `# comment` = inline guidance
- Each recipe ends with a single export call + a UE5-side verification checklist

Recipes:
1. [character_export_ue5_skeletal](#recipe-1-character_export_ue5_skeletal) — sculpt → retopo → rig → skin → export FBX skeletal
2. [character_retarget_to_ue5_mannequin](#recipe-2-character_retarget_to_ue5_mannequin) — import third-party mocap → retarget to UE5 SK_Mannequin → bake → export
3. [metahuman_face_blendshapes_setup](#recipe-3-metahuman_face_blendshapes_setup) — full ARKit-52 blendshape rig on a head mesh with driver bones
4. [level_modular_kit_bake_export](#recipe-4-level_modular_kit_bake_export) — modular wall/floor/corner kit with grid snapping + collision + batch export
5. [prop_high_to_low_bake_export](#recipe-5-prop_high_to_low_bake_export) — high-poly → low-poly → cage → bake PBR set → export with collision
6. [procedural_foliage_scatter_export](#recipe-6-procedural_foliage_scatter_export) — GN scatter forest → realize instances → static mesh export
7. [cinematic_render_sequence](#recipe-7-cinematic_render_sequence) — multi-camera cinematic with DOF + light groups + compositor + EXR sequence
8. [animation_bake_export_gltf](#recipe-8-animation_bake_export_gltf) — multi-clip animation library → bake NLA → export glTF with multiple animations

---

## Recipe 1: `character_export_ue5_skeletal`

**Goal:** ship a sculpted character as a skeletal mesh fully compatible with the UE5 SK_Mannequin skeleton, A-pose, A-side weights, ARKit-52 face blendshapes optional.

**Pre-conditions:** none (starts from empty scene).

**Inputs from agent:** target file path, character name, optional ARKit face flag.

```
# 1. Scene setup
[scene_set_unit_scale_for_modular_kit(scale=1.0)]   # 1 BU = 1 m = UE5's GlobalScale=1.0
[collection_create(parentPath="Scene Collection", name="Character")]
  → refs.collectionName="Character"

# 2. Base mesh from box → sculpt
[mesh_create_box_subdivided(size=2.0, subdivisions=4)]
  → refs.objectName="Cube"
[object_set_transform(objectName="Cube", location=(0,0,1))]
[modifier_add_multires(objectName="Cube", subdivisions=4)]
[sculpt_mode_toggle(objectName="Cube", enter=true)]
# ... agent invokes sculpt_filter_apply / sculpt_remesh_voxel / sculpt_symmetrize
# ... freehand sculpting stays with the human; agent does deterministic filters
[sculpt_remesh_voxel(objectName="Cube", voxelSize=0.02)]
[sculpt_symmetrize(objectName="Cube", axis="+X")]
[sculpt_mode_toggle(objectName="Cube", enter=false)]

# 3. Retopo (manual base cage path — modal Polybuild stays with human)
[retopo_create_base_cage(sourceObjectName="Cube", targetTriCount=15000)]
  → refs.objectName="Cube_Retopo"

# 4. UV unwrap
[uv_smart_project(objectName="Cube_Retopo", angleLimit=66.0, islandMargin=0.02)]
  → refs.uvLayerName="UVMap"
[uv_pack_islands(objectName="Cube_Retopo", margin=0.005)]
[uv_average_islands_scale(objectName="Cube_Retopo")]
[uv_validate_for_baking(objectName="Cube_Retopo")]
  → refs.ok=true

# 5. Rig with UE5 Mannequin skeleton
[armature_create_ue5_mannequin(name="SK_Hero", scale=1.0)]
  → refs.armatureName="SK_Hero"
  → refs.boneNames=["root","pelvis","spine_01",...,"ik_foot_root","ik_hand_root","ik_hand_gun"]

# 6. Optional MetaHuman face blendshapes (if face flag set)
# (see Recipe 3 for the standalone face setup)
[shape_key_create_basis(objectName="Cube_Retopo")]
[shape_key_create_arkit_set(objectName="Cube_Retopo")]
  → refs.shapeKeyNames=["eyeBlinkLeft",...,"tongueOut"]  # 52 items
[metahuman_face_validate(objectName="Cube_Retopo")]
  → refs.missingShapeKeys=[]

# 7. Skin mesh to armature
[mesh_parent_to_armature(meshObjectName="Cube_Retopo", armatureObjectName="SK_Hero")]
[vertex_group_create_from_armature(meshObjectName="Cube_Retopo", armatureObjectName="SK_Hero")]
  → refs.vertexGroupNames=[...64 names...]
[vertex_group_auto_weight_from_armature(meshObjectName="Cube_Retopo", armatureObjectName="SK_Hero")]
[vertex_group_normalize_weights(meshObjectName="Cube_Retopo")]
# Manual weight cleanup is the human's job (weight_paint is modal — out of scope)

# 8. Sockets (e.g. for attaching weapons)
[socket_add(armatureName="SK_Hero", boneName="hand_r", socketName="WeaponSocket_R", location=(0,0,0))]
  → refs.objectName="SOCKET_WeaponSocket_R"

# 9. Final validation + export
[mesh_validate_for_export_ue5(objectName="Cube_Retopo")]
[export_fbx_skeletal(
    armatureName="SK_Hero",
    meshObjectNames=["Cube_Retopo"],
    filepath="export/SK_Hero.fbx",
    globalScale=1.0,
    applyUnitScale=true,
    axisForward="-Z",
    axisUp="Y",
    useArmatureDeformOnly=true,
    addLeafBones=false,
    bakeAnim=false,
    useMeshModifiers=true,
    objectTypes=["ARMATURE","MESH"]
)]
  → refs.filepath="export/SK_Hero.fbx"
```

**UE5-side verify:** import as Skeletal Mesh, target SK_Mannequin skeleton; bones auto-merge; ARKit-52 morph targets visible in Skeletal Mesh editor; A-pose intact.

**Tested in:** `Tools/test/recipes/character-export.test.ts`

---

## Recipe 2: `character_retarget_to_ue5_mannequin`

**Goal:** take a Mixamo / third-party rigged character or animation and produce a clean Action retargeted to the UE5 SK_Mannequin skeleton.

```
# 1. Import source rig + animation
[file_open(filepath="source/mixamo_walk.fbx")]
# Or:
[import_fbx_skeletal(filepath="source/mixamo_character.fbx")]
  → refs.armatureName="Armature"
  → refs.actionName="Armature|mixamo.com|Layer0"

# 2. Standardize the source skeleton orientation (Mixamo → UE5)
[armature_apply_scale(armatureName="Armature")]   # often Mixamo imports at 0.01 scale
[bone_rename_convention(armatureName="Armature", from="MIXAMO", to="UE5_MANNEQUIN")]
# Tool internally maps "mixamorig:Hips" → "pelvis", "mixamorig:Spine" → "spine_01", etc.

# 3. Build a fresh UE5 Mannequin skeleton as the retarget target
[armature_create_ue5_mannequin(name="SK_Mannequin_Target")]
  → refs.armatureName="SK_Mannequin_Target"

# 4. Composite retarget (the big one)
[armature_retarget_to_ue5_mannequin(
    sourceArmatureName="Armature",
    sourceActionName="Armature|mixamo.com|Layer0",
    targetArmatureName="SK_Mannequin_Target",
    boneMap={"mixamorig:Hips":"pelvis", "mixamorig:Spine":"spine_01", ...},
    visualKeying=true,
    clearConstraints=true,
    bakeSimulation=true)]
  → refs.actionName="SK_Mannequin_Target|Walk_Retargeted"

# 5. Export animation only
[export_fbx_animation(
    armatureName="SK_Mannequin_Target",
    actionName="SK_Mannequin_Target|Walk_Retargeted",
    filepath="export/Walk_Retargeted.fbx",
    bakeAnim=true,
    bakeAnimUseAllActions=false,
    bakeAnimForceStartendKeying=true,
    addLeafBones=false)]
  → refs.filepath="export/Walk_Retargeted.fbx"
```

**UE5-side verify:** import animation against existing SK_Mannequin skeleton — no bone count mismatch warnings, root motion preserved, no scale drift.

---

## Recipe 3: `metahuman_face_blendshapes_setup`

**Goal:** install the 52-blendshape ARKit face rig on an existing head mesh, with optional driver bones for Live Link / control rig.

```
# 1. Verify head mesh exists and is the active object
[shape_key_create_basis(objectName="HeadMesh")]
  → refs.shapeKeyName="Basis"

# 2. Generate all 52 ARKit shape keys (deterministic; default value=0)
[shape_key_create_arkit_set(objectName="HeadMesh")]
  → refs.shapeKeyNames=[
      "eyeBlinkLeft","eyeLookDownLeft","eyeLookInLeft","eyeLookOutLeft","eyeLookUpLeft","eyeSquintLeft","eyeWideLeft",
      "eyeBlinkRight","eyeLookDownRight","eyeLookInRight","eyeLookOutRight","eyeLookUpRight","eyeSquintRight","eyeWideRight",
      "jawForward","jawLeft","jawRight","jawOpen",
      "mouthClose","mouthFunnel","mouthPucker","mouthLeft","mouthRight",
      "mouthSmileLeft","mouthSmileRight","mouthFrownLeft","mouthFrownRight",
      "mouthDimpleLeft","mouthDimpleRight","mouthStretchLeft","mouthStretchRight",
      "mouthRollLower","mouthRollUpper","mouthShrugLower","mouthShrugUpper",
      "mouthPressLeft","mouthPressRight","mouthLowerDownLeft","mouthLowerDownRight",
      "mouthUpperUpLeft","mouthUpperUpRight",
      "browDownLeft","browDownRight","browInnerUp","browOuterUpLeft","browOuterUpRight",
      "cheekPuff","cheekSquintLeft","cheekSquintRight",
      "noseSneerLeft","noseSneerRight",
      "tongueOut"]

# 3. Validate (sanity)
[metahuman_face_validate(objectName="HeadMesh")]
  → refs.missingShapeKeys=[]
  → refs.ok=true

# 4. (Optional) Driver bones — let the rigger drive shape keys from a face control armature
[armature_create(name="FaceRig")]
  → refs.armatureName="FaceRig"
[bone_add(armatureName="FaceRig", boneName="jaw_ctrl", head=(0,0,1.6), tail=(0,0,1.65))]
  → refs.boneName="jaw_ctrl"
[bone_set_constraint_limit_rotation(armatureName="FaceRig", boneName="jaw_ctrl",
    minX=0, maxX=0.7, minY=-0.2, maxY=0.2, minZ=-0.2, maxZ=0.2)]
[driver_add_from_bone_rotation(
    sourceArmatureName="FaceRig",
    sourceBoneName="jaw_ctrl",
    sourceTransformType="ROT_X",
    targetObjectName="HeadMesh",
    targetDataPath='key_blocks["jawOpen"].value',
    multiplier=1.43)]   # jaw_ctrl rotates 0..0.7 rad → jawOpen 0..1

# Repeat per shape-key family. Or skip — drivers are optional; agent could ship Live Link path instead.

# 5. Export (face is part of skeletal export — see Recipe 1 §9)
```

**UE5-side verify:** import as Skeletal Mesh; in the Skeletal Mesh editor, all 52 morph targets are visible by ARKit name; Live Link Face app drives them in PIE.

---

## Recipe 4: `level_modular_kit_bake_export`

**Goal:** ship a modular wall/floor/corner kit (UE5 cm scale, grid-snapped origins, collision auto-generated, batch-exported as one FBX per piece).

```
# 1. Scene + units
[scene_create(name="Kit_Castle", unitSystem="METRIC", scaleLength=0.01, frameStart=1, frameEnd=1)]
  → refs.sceneName="Kit_Castle"
[scene_set_active(sceneName="Kit_Castle")]
[scene_set_unit_scale_for_modular_kit(scale=0.01)]    # 1 BU = 1 cm

# 2. Collection per piece type
[collection_create(parentPath="Scene Collection", name="Walls")]
[collection_create(parentPath="Scene Collection", name="Floors")]
[collection_create(parentPath="Scene Collection", name="Corners")]

# 3. Blockout each piece — example: Wall_Straight_400x300
[object_add_blockout(name="Wall_Straight_400", footprint=(400,30,300), collectionName="Walls")]
  → refs.objectName="Wall_Straight_400"
[mesh_set_origin_to_snap_corner(objectName="Wall_Straight_400", corner="MIN_X_MIN_Y_MIN_Z")]
[material_create_procedural_grid(name="Grid_BlockOut", squareSize=0.5)]
  → refs.materialName="Grid_BlockOut"
[material_assign_slot(objectName="Wall_Straight_400", materialName="Grid_BlockOut", slotIndex=0)]
[uv_unwrap_smart_project(objectName="Wall_Straight_400", angleLimit=66)]
[collision_add_convex_hull(objectName="Wall_Straight_400")]
  → refs.collisionObjectName="UCX_Wall_Straight_400_01"

# 4. (Repeat blockout for every piece in the kit)
[object_add_blockout(name="Floor_400x400", footprint=(400,400,20), collectionName="Floors")]
  → refs.objectName="Floor_400x400"
[mesh_set_origin_to_snap_corner(objectName="Floor_400x400", corner="MIN_X_MIN_Y_MIN_Z")]
[material_assign_slot(objectName="Floor_400x400", materialName="Grid_BlockOut", slotIndex=0)]
[uv_unwrap_smart_project(objectName="Floor_400x400")]
[collision_add_convex_hull(objectName="Floor_400x400")]
# ... repeat for Corner_L, Corner_R, etc.

# 5. Export each top-level child of each collection as its own FBX
[view_layer_create_for_export(name="Export_Kit", collectionNames=["Walls","Floors","Corners"])]
  → refs.viewLayerName="Export_Kit"
[export_fbx_collection_batch(
    collectionName="Walls",
    outputDirectory="export/kit/walls/",
    filenameTemplate="SM_{ObjectName}.fbx",
    globalScale=1.0,
    applyUnitScale=true,
    axisForward="-Z", axisUp="Y",
    includeCollisionChildren=true)]
  → refs.filepaths=["export/kit/walls/SM_Wall_Straight_400.fbx", ...]
[export_fbx_collection_batch(collectionName="Floors", outputDirectory="export/kit/floors/", ...)]
[export_fbx_collection_batch(collectionName="Corners", outputDirectory="export/kit/corners/", ...)]
```

**UE5-side verify:** import as static meshes; UCX_ children become collision primitives automatically; origins snap to grid; modular pieces fit edge-to-edge at 400-unit increments.

---

## Recipe 5: `prop_high_to_low_bake_export`

**Goal:** sculpted prop → game-ready low-poly with full PBR texture set baked from high-poly.

```
# 1. Assume high-poly is the active object (from sculpt or import)
[mesh_validate_topology(objectName="Sculpt_HighPoly")]
  → refs.triCount=1850000   # too high for game

# 2. Generate low-poly (manual + decimate composite)
[mesh_duplicate_for_lod(sourceObjectName="Sculpt_HighPoly", decimateRatio=0.01)]
  → refs.objectName="Sculpt_LowPoly"
[mesh_validate_topology(objectName="Sculpt_LowPoly")]
  → refs.triCount=18500     # ~1% target

# 3. Manual hand-retopo would happen here for hero props; for this recipe we accept decimate.

# 4. UV unwrap the low-poly
[uv_smart_project(objectName="Sculpt_LowPoly", angleLimit=66, islandMargin=0.02)]
  → refs.uvLayerName="UVMap"
[uv_pack_islands(objectName="Sculpt_LowPoly", margin=0.005)]
[uv_average_islands_scale(objectName="Sculpt_LowPoly")]

# 5. Cage object for clean normal bake
[cage_object_create(sourceObjectName="Sculpt_LowPoly", thickness=0.05)]
  → refs.cageObjectName="Sculpt_LowPoly_Cage"

# 6. Bake PBR set in one composite (normal, roughness, metallic, AO)
[bake_pbr_set(
    targetObjectName="Sculpt_LowPoly",
    sourceObjectName="Sculpt_HighPoly",
    cageObjectName="Sculpt_LowPoly_Cage",
    resolution=2048,
    outputDirectory="textures/",
    namingPrefix="T_Sword",
    normalFormat="DIRECTX")]
  → refs.imagePaths={
      "Normal": "textures/T_Sword_Normal.png",
      "Roughness": "textures/T_Sword_Roughness.png",
      "Metallic": "textures/T_Sword_Metallic.png",
      "AO": "textures/T_Sword_AO.png",
      "BaseColor": "textures/T_Sword_BaseColor.png"}

# 7. Build UE5-ready material
[material_create_pbr_for_ue(
    name="M_Sword",
    baseColorPath="textures/T_Sword_BaseColor.png",
    normalPath="textures/T_Sword_Normal.png",
    roughnessPath="textures/T_Sword_Roughness.png",
    metallicPath="textures/T_Sword_Metallic.png",
    aoPath="textures/T_Sword_AO.png")]
  → refs.materialName="M_Sword"
[material_assign_to_object(objectName="Sculpt_LowPoly", materialName="M_Sword")]
[material_validate_for_ue_export(materialName="M_Sword")]

# 8. Collision
[mesh_create_collision_convex(sourceObjectName="Sculpt_LowPoly", collisionName="UCX_Sword_01")]
  → refs.objectName="UCX_Sword_01"

# 9. Final export
[mesh_validate_for_export_ue5(objectName="Sculpt_LowPoly")]
[export_fbx_static(
    objectNames=["Sculpt_LowPoly","UCX_Sword_01"],
    filepath="export/SM_Sword.fbx",
    globalScale=1.0, applyUnitScale=true,
    axisForward="-Z", axisUp="Y",
    useMeshModifiers=true,
    bakeSpaceTransform=false)]
  → refs.filepath="export/SM_Sword.fbx"
```

**UE5-side verify:** import as Static Mesh; UCX_Sword_01 becomes collision; material instance from M_Sword displays normal map without inversion (DirectX format auto-detected).

---

## Recipe 6: `procedural_foliage_scatter_export`

**Goal:** scatter forest of trees over a terrain mesh via Geometry Nodes, realize instances, export as static mesh for UE5 (or alternatively for UE5 PCG / Foliage Instanced Static Mesh).

```
# 1. Terrain and tree collection
[mesh_add_primitive(type="PLANE", size=100, subdivisions=64)]
  → refs.objectName="Terrain"
# ... noise displacement on Terrain (via shader or sculpt; skipped here)

[collection_create(parentPath="Scene Collection", name="Trees_Source")]
[file_append_data(filepath="assets/tree_pine.blend", datablockType="Object", names=["Tree_Pine_01","Tree_Pine_02","Tree_Pine_03"])]
[collection_move_objects(collectionName="Trees_Source", objectNames=["Tree_Pine_01","Tree_Pine_02","Tree_Pine_03"])]

# 2. Build scatter via composite
[geo_node_instance_on_points_setup(
    targetObjectName="Terrain",
    sourceCollectionName="Trees_Source",
    density=0.5,
    seed=42,
    rotateRandom=true,
    scaleMin=0.8, scaleMax=1.2)]
  → refs.modifierName="GeometryNodes"
  → refs.nodeTreeName="Forest_Scatter_AutoGen"

# 3. Tweak distribution by vertex color / weight (variable density)
[geo_node_distribute_points_density_attribute(
    nodeTreeName="Forest_Scatter_AutoGen",
    attributeName="Density",
    attributeDomain="POINT")]
# ... agent or human paints vertex color "Density" on terrain

# 4. Realize the instances (turn them into actual mesh data) — required for UE static-mesh export
[geo_node_realize_instances(nodeTreeName="Forest_Scatter_AutoGen")]

# 5. Apply the modifier (bake to mesh)
[modifier_apply(objectName="Terrain", modifierName="GeometryNodes")]
[mesh_validate_topology(objectName="Terrain")]

# 6. Export — choose one path:
# Path A: export as one big static mesh (simpler; loses instancing benefit in UE)
[export_fbx_static(objectNames=["Terrain"], filepath="export/SM_Forest.fbx")]

# Path B (preferred for UE5): keep trees as separate objects (don't realize); export Trees_Source collection
# and let UE5 PCG / Foliage Instanced Static Mesh handle scatter on the engine side
[export_fbx_collection_batch(
    collectionName="Trees_Source",
    outputDirectory="export/foliage/",
    filenameTemplate="SM_{ObjectName}.fbx")]
  → refs.filepaths=["export/foliage/SM_Tree_Pine_01.fbx", ...]
```

**UE5-side verify (Path A):** large static mesh imports with Nanite enabled; LOD0 retains all scatter geometry.
**UE5-side verify (Path B):** three tree SMs import; PCG graph in level uses them as scatter sources.

---

## Recipe 7: `cinematic_render_sequence`

**Goal:** multi-camera cinematic with DOF, light groups, EEVEE-Next/Cycles render, compositor color grade, EXR sequence output for Sequencer ingest.

```
# 1. Scene + render engine
[scene_create(name="Cinematic_Opening", unitSystem="METRIC", scaleLength=1.0, frameStart=1, frameEnd=240)]
  → refs.sceneName="Cinematic_Opening"
[scene_set_active(sceneName="Cinematic_Opening")]
[render_set_engine(engine="CYCLES")]
[render_configure_cycles(samples=256, denoiser="OPENIMAGEDENOISE", device="GPU",
    maxBounces=12, transparentMaxBounces=8, useAdaptiveSampling=true)]
[render_set_output(
    filepath="//render/opening_####",
    resolutionX=3840, resolutionY=2160,
    fileFormat="OPEN_EXR_MULTILAYER",
    colorMode="RGBA",
    colorDepth="32",
    frameStart=1, frameEnd=240, fps=24)]

# 2. World HDRI
[world_set_hdri(filepath="hdri/studio_4k.exr", rotation=0.0, strength=1.0)]

# 3. Lights with groups (compositor color-grade per group)
[light_create(name="KeyLight", type="AREA", energy=500, color=(1.0,0.95,0.85))]
  → refs.objectName="KeyLight"
[light_set_area_shape(objectName="KeyLight", shape="RECTANGLE", sizeX=2.0, sizeY=1.0)]
[object_set_transform(objectName="KeyLight", location=(3,-3,4), rotation=(60,0,40))]
[light_create_group(groupName="Group_Key")]
[light_configure_linking(objectName="KeyLight", lightGroup="Group_Key")]

[light_create(name="FillLight", type="AREA", energy=120, color=(0.8,0.85,1.0))]
[light_create_group(groupName="Group_Fill")]
[light_configure_linking(objectName="FillLight", lightGroup="Group_Fill")]

[light_create(name="RimLight", type="SPOT", energy=300, color=(1.0,0.9,0.8))]
[light_create_group(groupName="Group_Rim")]
[light_configure_linking(objectName="RimLight", lightGroup="Group_Rim")]

# 4. Cameras
[camera_create(name="Cam_Wide", focalLength=35, sensorWidth=36)]
[object_set_transform(objectName="Cam_Wide", location=(0,-8,1.7), rotation=(85,0,0))]
[camera_set_dof(objectName="Cam_Wide", focusDistance=8.0, fStop=2.8)]
[camera_set_clipping(objectName="Cam_Wide", clipStart=0.1, clipEnd=1000)]

[camera_create(name="Cam_Close", focalLength=85, sensorWidth=36)]
[object_set_transform(objectName="Cam_Close", location=(0.3,-2,1.7), rotation=(88,0,5))]
[camera_set_dof(objectName="Cam_Close", focusDistance=2.0, fStop=1.4)]

[camera_set_active(cameraObjectName="Cam_Wide")]   # start with wide

# 5. Compositor — light group color grade + film grain
[compositor_enable(sceneName="Cinematic_Opening")]
[compositor_node_add(sceneName="Cinematic_Opening", nodeType="CompositorNodeRLayers", name="RenderLayers")]
[compositor_node_add(sceneName="Cinematic_Opening", nodeType="CompositorNodeHueSat", name="KeyGrade")]
[compositor_node_set(sceneName="Cinematic_Opening", nodeName="KeyGrade", paramName="color_saturation", paramValue=0.9)]
[compositor_node_add(sceneName="Cinematic_Opening", nodeType="CompositorNodeOutputFile", name="OutputEXR")]
[compositor_node_set(sceneName="Cinematic_Opening", nodeName="OutputEXR", paramName="base_path", paramValue="//render/passes/")]
[compositor_link_create(sceneName="Cinematic_Opening",
    fromNode="RenderLayers", fromSocket="Group_Key",
    toNode="KeyGrade", toSocket="Image")]
[compositor_link_create(sceneName="Cinematic_Opening",
    fromNode="KeyGrade", fromSocket="Image",
    toNode="OutputEXR", toSocket="Image")]

# 6. Render
[render_animation(frameStart=1, frameEnd=240, useStepFrames=false)]
  → refs.filepaths=["render/opening_0001.exr",...,"render/opening_0240.exr"]
```

**Downstream:** EXRs go into UE5 Sequencer as Image Plate, or DaVinci Resolve for grading.

---

## Recipe 8: `animation_bake_export_gltf`

**Goal:** library of multiple animation clips on one armature → bake NLA stack → export as a single glTF file with N animation tracks.

```
# 1. Open file with rig + multiple clips
[file_open(filepath="character.blend")]
  → refs.armatureName="SK_Hero"
  → refs.actionNames=["Walk","Run","Jump_Start","Jump_Loop","Jump_Land","Idle"]

# 2. For each clip, push to NLA + bake (composite per clip)
# (animation library workflow: clips are stored as separate Actions linked to the armature)

# 2a. Walk
[nla_track_create_and_push_action(
    armatureName="SK_Hero",
    trackName="NLA_Walk",
    actionName="Walk",
    startFrame=1)]
[nla_bake_to_action(
    armatureName="SK_Hero",
    actionName="Walk_Baked",
    visualKeying=true,
    clearConstraints=false,
    bakeSimulation=true,
    onlySelectedBones=false)]
  → refs.actionName="Walk_Baked"

# 2b. Run
[nla_track_create_and_push_action(armatureName="SK_Hero", trackName="NLA_Run", actionName="Run", startFrame=1)]
[nla_bake_to_action(armatureName="SK_Hero", actionName="Run_Baked", visualKeying=true)]

# 2c. Jump trio (separate Actions; UE5 will composite into one Animation Sequence)
[nla_bake_to_action(armatureName="SK_Hero", actionName="Jump_Start_Baked", visualKeying=true)]
[nla_bake_to_action(armatureName="SK_Hero", actionName="Jump_Loop_Baked", visualKeying=true)]
[nla_bake_to_action(armatureName="SK_Hero", actionName="Jump_Land_Baked", visualKeying=true)]

# 2d. Idle
[nla_bake_to_action(armatureName="SK_Hero", actionName="Idle_Baked", visualKeying=true)]

# 3. Export single glTF with all baked actions as separate animations
[export_gltf_skeletal(
    armatureName="SK_Hero",
    meshObjectNames=["Hero_Body"],
    actionNames=["Walk_Baked","Run_Baked","Jump_Start_Baked","Jump_Loop_Baked","Jump_Land_Baked","Idle_Baked"],
    filepath="export/SK_Hero.glb",
    exportAnimations=true,
    exportAnimationMode="ACTIONS",
    exportNlaStrips=false,
    exportApply=true)]
  → refs.filepath="export/SK_Hero.glb"
```

**UE5-side verify:** import .glb as Skeletal Mesh + 6 Animation Sequences. Each retains keyframes; UE Animation Blueprint references them by name.

---

## Recipe-test mapping (Sprint 1)

Every recipe gets at least one integration test under `Tools/test/recipes/`:

| Recipe | Test file | Tools exercised |
|---|---|---|
| 1 | `character-export-ue5-skeletal.test.ts` | armature, vertex_group, shape_key, export_fbx_skeletal, validation |
| 2 | `character-retarget-to-ue5-mannequin.test.ts` | import_fbx, retarget composite, export_fbx_animation |
| 3 | `metahuman-face-blendshapes-setup.test.ts` | shape_key_create_arkit_set, metahuman_face_validate, driver_add_from_bone_rotation |
| 4 | `level-modular-kit-bake-export.test.ts` | scene+units, object_add_blockout, collision, batch export |
| 5 | `prop-high-to-low-bake-export.test.ts` | mesh_duplicate_for_lod, cage, bake_pbr_set, material_create_pbr_for_ue, export |
| 6 | `procedural-foliage-scatter-export.test.ts` | geo_node_instance_on_points_setup, realize, modifier_apply, batch export |
| 7 | `cinematic-render-sequence.test.ts` | light groups, dof, render_configure_cycles, compositor, render_animation (short frame range) |
| 8 | `animation-bake-export-gltf.test.ts` | nla_track_create_and_push_action, nla_bake_to_action, export_gltf_skeletal |

These recipe tests are **end-to-end** — they exercise every linkage between primitives. Individual primitive tests live alongside their tool files (`Tools/test/tools/<tool>.test.ts`).
