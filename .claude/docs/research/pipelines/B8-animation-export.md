I have sufficient foundation material. Now I'll compile a comprehensive research report on B8 — Animation authoring, retargeting, and import/export operators for Blender 4.2 LTS targeting UE5.

---

# B8 Research Report — Animation Authoring, Retargeting, and Import/Export

## Part A: Canonical Workflow

### The UE5 Animation Export Workflow

**Context:** Per UE-TARGETS.md §1.3, UE5 **requires one Action per FBX file** for skeletal animation. Mannequin animations are stored per-clip. Blender source → export composite tool must respect this constraint.

**Workflow Steps:**

1. **Source Authoring**
   - Author animation on rigged character (armature with bones, mesh skinned to bones).
   - Frame range: set `scene.frame_start/frame_end` to match animation playback range.
   - Frame rate: set `scene.render.fps` to match target (typically 30 or 60 fps).
   - Action: create/assign via `bpy.data.actions.new()` → `obj.animation_data.action`.

2. **Keyframing**
   - Insert keyframes on armature bones via `pose_bone.keyframe_insert(data_path='rotation_quaternion', frame=N)`.
   - Insert on object root motion via `obj.keyframe_insert(data_path='location', frame=N)` on root bone.
   - Apply constraints (IK, Copy Rotation, etc.) pre-bake, then bake result onto bones.

3. **NLA Stack (Optional Multi-Clip)**
   - Push Actions to NLA tracks via `nla_track.strips.new(name, frame_start, action)`.
   - Per-strip: set `strip.use_animated_time_cyclic` for looping, `strip.scale` for time warping.
   - Bake NLA stack: `bpy.ops.nla.bake(frame_start=X, frame_end=Y, ...)` → converts strips back to Action.

4. **Bake Step (Critical for UE)**
   - If constraints used: bake via `bpy.ops.nla.bake(...)` or direct F-curve mutation to produce clean location/rotation keys.
   - Bake into **new Action** (or current if `use_current_action=True`).
   - Remove all constraints pre-export (UE only wants bone transforms, not constraint deformation).

5. **Export**
   - Select armature + mesh.
   - Call `export_fbx_animation` composite: 
     - Per-Action loop, export one FBX per Action.
     - Set FBX params: `bake_anim=True`, `use_selection=True`, `bake_anim_step=1.0` (every frame).
     - Frame range = Action's start/end or scene frame range.
     - Save as `${action_name}.fbx`.

---

### The UE5 Mannequin Retargeting Workflow

**Context:** UE5 Mannequin (`SK_Mannequin`) is the canonical skeleton. Custom character rigs must retarget animations to it. Blender has no native "retarget" operator — this must be a composite tool.

**Workflow Steps:**

1. **Import Source Animation**
   - Source rig + animation imported (or created in Blender).
   - Source skeleton named (e.g., `Armature.source`).
   - UE Mannequin skeleton imported or created (named `Armature.mannequin`).

2. **Bone Mapping**
   - Manual or programmatic: build a dict `{source_bone: mannequin_bone}` for all bones to retarget.
   - Example: `{"LeftShoulder": "clavicle_l", "LeftArm": "upperarm_l", ...}`.

3. **Constraint Setup**
   - For each mapped bone pair:
     - Select Mannequin bone.
     - Add constraint: `Copy Rotation` (from source bone).
     - Optional: `Copy Location` if root motion or position-driven animation.
     - Set influence to 1.0, target armature = source rig.

4. **Bake Retargeted Animation**
   - Select Mannequin armature.
   - Call `bpy.ops.nla.bake(bake_types={'POSE'}, visual_keying=True, clear_constraints=True)`.
   - This evaluates all constraints on the main thread and bakes result into keyframes.
   - Remove constraints (auto-cleared by `clear_constraints=True`).

5. **Export Retargeted Action**
   - Call `export_fbx_animation` on the Mannequin rig with the baked action.
   - Save as `${action_name}_retargeted.fbx`.

---

## Part B: Proposed Tools — Full Catalog

### Core Animation Authoring

#### 1. `action_create`
```
Signature: action_create(
  actionName: str,
  objectName: str
) -> { ok: bool, refs: { actionName }, data: { actionName, framesCount } }

Description:
Create a new Action and assign it to the animation_data of the given object.
If animation_data does not exist, create it. Returns the Action name.
Useful for setting up a blank animation slot before keyframing.

errorCodes:
  OBJECT_NOT_FOUND: object does not exist
  OBJECT_NOT_ANIMATABLE: object type cannot have animation_data (e.g., Light in some cases, or read-only assets)
  ACTION_EXISTS: actionName already exists (if strict mode)

Zod Sketch:
  z.object({
    objectName: z.string().describe("Object name (e.g., 'Armature')"),
    actionName: z.string().describe("Desired Action name")
  })

https://docs.blender.org/api/current/bpy.types.AnimationData.html
```

#### 2. `keyframe_insert_bone`
```
Signature: keyframe_insert_bone(
  objectName: str,
  boneName: str,
  frame: int,
  dataPath: enum('location' | 'rotation_quaternion' | 'rotation_euler' | 'scale'),
  useVisualKeying: bool = false
) -> { ok: bool, refs: { boneName }, data: { keysInserted: int } }

Description:
Insert a keyframe on a bone's transform (location, rotation, or scale).
dataPath supports per-channel control ('location.x', 'rotation_quaternion', etc.).
useVisualKeying = true evaluates constraints before keying (bakes constraint effect into keyframe).
Returns number of keys inserted (1 for single channel, 3 for location/euler, 4 for quaternion).

errorCodes:
  OBJECT_NOT_FOUND: object does not exist
  NOT_AN_ARMATURE: object is not an Armature
  BONE_NOT_FOUND: boneName does not exist in armature
  ACTION_NOT_ASSIGNED: object has no active Action

Zod Sketch:
  z.object({
    objectName: z.string(),
    boneName: z.string(),
    frame: z.number().int().min(0),
    dataPath: z.enum(['location', 'rotation_quaternion', 'rotation_euler', 'scale']),
    useVisualKeying: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.types.Keyable.html#bpy.types.Keyable.keyframe_insert
```

#### 3. `keyframe_insert_object`
```
Signature: keyframe_insert_object(
  objectName: str,
  frame: int,
  dataPath: enum('location' | 'rotation_quaternion' | 'rotation_euler' | 'scale'),
  useVisualKeying: bool = false
) -> { ok: bool, refs: { objectName }, data: { keysInserted: int } }

Description:
Insert a keyframe on an object's transform (root motion for characters).
Complements bone keying; used for animating the root bone's world position.

errorCodes:
  OBJECT_NOT_FOUND
  ACTION_NOT_ASSIGNED

Zod Sketch:
  z.object({
    objectName: z.string(),
    frame: z.number().int().min(0),
    dataPath: z.enum(['location', 'rotation_quaternion', 'rotation_euler', 'scale']),
    useVisualKeying: z.boolean().optional()
  })
```

#### 4. `fcurve_set_keyframe_values`
```
Signature: fcurve_set_keyframe_values(
  objectName: str,
  actionName: str,
  dataPath: str,
  frameValuePairs: [ { frame: int, value: float, handleType?: 'AUTO' | 'VECTOR' | 'ALIGNED' | 'FREE' } ]
) -> { ok: bool, data: { keysSet: int } }

Description:
Directly mutate F-curve keyframe values post-hoc. Surgical edits: change keyframe positions, values, or handle types.
dataPath examples: 'pose.bones["Armature.001"]["rotation_quaternion"]', 'location.x'.
Useful for fine-tuning after bake or constraint evaluation.

errorCodes:
  OBJECT_NOT_FOUND
  ACTION_NOT_FOUND
  FCURVE_NOT_FOUND: dataPath does not map to an existing F-curve

Zod Sketch:
  z.object({
    objectName: z.string(),
    actionName: z.string(),
    dataPath: z.string().describe("F-curve data_path, e.g. 'rotation_quaternion'"),
    frameValuePairs: z.array(z.object({
      frame: z.number().int(),
      value: z.number(),
      handleType: z.enum(['AUTO', 'VECTOR', 'ALIGNED', 'FREE']).optional()
    }))
  })

https://docs.blender.org/api/current/bpy.types.FCurve.html#bpy.types.FCurve.keyframe_points
```

#### 5. `fcurve_add_modifier`
```
Signature: fcurve_add_modifier(
  objectName: str,
  actionName: str,
  dataPath: str,
  modifierType: enum('CYCLES' | 'NOISE' | 'LIMITS' | 'STEPPED' | 'GENERATOR'),
  modifierParams: { ...type-specific params }
) -> { ok: bool, data: { modifierName: str } }

Description:
Add an F-curve modifier (Cycles, Noise, etc.) to animate/process a curve.
Cycles: loop animation (useful for walk/run cycles).
Noise: add procedural jitter.
Limits: clamp values within range.
Stepped: convert smooth curve to stepped keyframes.
Generator: generate polynomial or custom function.

Zod Sketch (simplified; type-specific params expand per modifierType):
  z.object({
    objectName: z.string(),
    actionName: z.string(),
    dataPath: z.string(),
    modifierType: z.enum(['CYCLES', 'NOISE', 'LIMITS', 'STEPPED', 'GENERATOR']),
    cyclesMode: z.enum(['REPEAT', 'REPEAT_OFFSET', 'MIRROR']).optional().describe("For CYCLES"),
    cyclesBefore: z.number().int().min(0).optional(),
    cyclesAfter: z.number().int().min(0).optional(),
    noiseScale: z.number().optional().describe("For NOISE"),
    noiseStrength: z.number().optional()
  })

https://docs.blender.org/api/current/bpy.types.FModifier.html
```

#### 6. `nla_track_create_and_push_action`
```
Signature: nla_track_create_and_push_action(
  objectName: str,
  actionName: str,
  trackName: str = "NLA_Track",
  frameStart: int = 1,
  blendMode: enum('REPLACE' | 'ADD' | 'SUBTRACT' | 'MULTIPLY') = 'REPLACE',
  timeScale: float = 1.0
) -> { ok: bool, data: { trackName, stripName, frameEnd } }

Description:
Create an NLA track and push an Action onto it as a strip.
Multiple tracks can hold multiple actions for complex animation blends.
timeScale warps the animation timeline (e.g., 0.5 = half speed, 2.0 = double speed).
blendMode controls how the strip combines with other tracks.

errorCodes:
  OBJECT_NOT_FOUND
  ACTION_NOT_FOUND
  TRACK_EXISTS: trackName already used (if strict)

Zod Sketch:
  z.object({
    objectName: z.string(),
    actionName: z.string(),
    trackName: z.string().optional(),
    frameStart: z.number().int().min(1).optional(),
    blendMode: z.enum(['REPLACE', 'ADD', 'SUBTRACT', 'MULTIPLY']).optional(),
    timeScale: z.number().positive().optional()
  })

https://docs.blender.org/api/current/bpy.types.NlaTrack.html
https://docs.blender.org/api/current/bpy.types.NlaStrip.html
```

### NLA Baking & Compositing

#### 7. `nla_bake_to_action` ⭐ **CRITICAL FOR UE**
```
Signature: nla_bake_to_action(
  objectName: str,
  frameStart: int,
  frameEnd: int,
  frameStep: int = 1,
  visualKeying: bool = true,
  clearConstraints: bool = true,
  clearParents: bool = false,
  useCurrentAction: bool = false,
  cleanCurves: bool = true,
  bakeTypes: set('POSE' | 'OBJECT') = {'POSE'},
  channelTypes: set('LOCATION' | 'ROTATION' | 'SCALE') = {'LOCATION', 'ROTATION', 'SCALE'}
) -> { ok: bool, refs: { actionName }, data: { keysCreated: int, keysPerFrame: int } }

Description:
Bake NLA strips, constraints, drivers, and visual deformation into a flat Action keyframe set.
**This is the prerequisite step before UE FBX export.** Evaluates all deformation per-frame on the main thread.
visualKeying=true captures final pose (with constraints applied).
clearConstraints=true removes all constraints post-bake (required for UE export).
cleanCurves=true removes redundant keyframes post-bake (optimization).

UE-TARGETS Contract: "bake action to convert constraints/drivers into keyframes. Critical pre-export step."

errorCodes:
  OBJECT_NOT_FOUND
  NOT_AN_ARMATURE
  FRAME_RANGE_INVALID: frame_start >= frame_end

Zod Sketch:
  z.object({
    objectName: z.string().describe("Armature object name"),
    frameStart: z.number().int().min(0).describe("First frame to bake"),
    frameEnd: z.number().int().min(1).describe("Last frame to bake (inclusive)"),
    frameStep: z.number().int().min(1).optional().describe("Every N frames"),
    visualKeying: z.boolean().optional().describe("Bake with constraints applied"),
    clearConstraints: z.boolean().optional().describe("Remove constraints post-bake"),
    clearParents: z.boolean().optional(),
    useCurrentAction: z.boolean().optional().describe("Bake into current action instead of new"),
    cleanCurves: z.boolean().optional().describe("Remove redundant keys"),
    bakeTypes: z.set(z.enum(['POSE', 'OBJECT'])).optional(),
    channelTypes: z.set(z.enum(['LOCATION', 'ROTATION', 'SCALE'])).optional()
  })

https://docs.blender.org/api/current/bpy.ops.nla.html#bpy.ops.nla.bake
```

### Retargeting (Composite)

#### 8. `armature_retarget_to_ue5_mannequin` ⭐ **COMPOSITE — Large Tool**
```
Signature: armature_retarget_to_ue5_mannequin(
  sourceArmatureName: str,
  targetArmatureName: str = "Armature.mannequin",
  boneMapping: object = {}, // { source_bone: mannequin_bone, ... }
  actionName: str = "",  // if empty, retarget current action
  frameStart: int = 1,
  frameEnd: int = 250,
  useVisualKeying: bool = true,
  outputActionSuffix: str = "_retargeted"
) -> { ok: bool, refs: { targetArmatureName, actionName }, data: { keysCreated, retargetedBones } }

Description:
**Composite multi-step retargeting tool for UE5 Mannequin skeleton.**

Steps:
1. Validate both armatures exist and have animation_data.
2. Build bone mapping (manual or inferred from bone name similarity).
3. For each mapped pair: add Copy Rotation constraint on target bone → source bone.
4. Bake constraints: `nla_bake_to_action(target, frameStart, frameEnd, ..., clearConstraints=true)`.
5. Create new Action named `${actionName}${outputActionSuffix}`.
6. Remove constraints.
7. Return retargeted action name and bone count.

errorCodes:
  OBJECT_NOT_FOUND: either armature missing
  NOT_AN_ARMATURE: one or both objects not armatures
  MAPPING_INCOMPLETE: unmapped bones (if strict validation)
  ACTION_NOT_FOUND: actionName does not exist on source
  RETARGET_FAILED: constraint or bake step failed

Zod Sketch:
  z.object({
    sourceArmatureName: z.string().describe("Source rig armature"),
    targetArmatureName: z.string().optional().describe("Target (UE Mannequin) armature"),
    boneMapping: z.record(z.string(), z.string()).optional().describe("{ sourceBone: mannequinBone, ... }"),
    actionName: z.string().optional().describe("Action to retarget; if empty, use active"),
    frameStart: z.number().int().min(1).optional(),
    frameEnd: z.number().int().min(1).optional(),
    useVisualKeying: z.boolean().optional(),
    outputActionSuffix: z.string().optional().describe("Suffix for output action name")
  })

Related:
  upstream: action_create, keyframe_insert_bone, nla_bake_to_action
  downstream: export_fbx_animation (to export the retargeted action)

Design Question: Ship in v1.0 as a full composite, or defer to v1.1 after primitives stabilize?
(Answer in DECISIONS.md ADR-006: defer to v1.1, ship bone_add_copy_rotation_constraint primitive in v1.0)
```

---

### Import/Export Operator Matrix

#### FBX Export — Animation + Skeletal Mesh

#### 9. `export_fbx_skeletal` ⭐ **PRIMARY EXPORT TOOL**
```
Signature: export_fbx_skeletal(
  filePath: str,
  objectName: str = "Armature",
  meshObjectNames: string[] = [],
  selectedOnly: bool = true,
  globalScale: float = 1.0,
  applyUnitScale: bool = true,
  axisForward: enum('-Z' | 'X' | 'Y' | '-X' | '-Y') = '-Z',
  axisUp: enum('Y' | 'X' | 'Z' | '-X' | '-Y' | '-Z') = 'Y',
  useSelection: bool = true,
  useMeshModifiers: bool = true,
  meshSmoothType: enum('OFF' | 'FACE' | 'EDGE' | 'SMOOTH_GROUP') = 'FACE',
  useTriangles: bool = true,
  bakeAnim: bool = true,
  bakeAnimUseAllBones: bool = true,
  bakeAnimStep: float = 1.0,
  bakeAnimSimplify: float = 0.0,
  addLeafBones: bool = false,  // **CRITICAL: false for UE**
  primaryBoneAxis: enum('Y' | 'X') = 'Y',
  secondaryBoneAxis: enum('X' | '-X') = 'X',
  useArmatureDeformOnly: bool = true,
  armatureNodeType: enum('NULL' | 'ROOT' | 'LIMBNODE') = 'NULL',
  useTspace: bool = true,
  useCustomProps: bool = true,
  pathMode: enum('AUTO' | 'COPY') = 'COPY',
  embedTextures: bool = false,
  checkExisting: bool = true
) -> { 
  ok: bool, 
  data: { 
    filePath, 
    skeletalMeshCount: int, 
    animationClip: str,
    triangleCount: int,
    naniteRecommended: bool,
    fbxVersion: str,
    warnings: string[]
  },
  refs: { objectName, meshObjectNames[] },
  nextSteps: [ "import_fbx_to_unreal_engine" ],
  warnings: [ "add_leaf_bones=false required for UE", ... ]
}

Description:
Export an armature + meshes as a skeletal mesh FBX for UE5.
**Every parameter is typed and maps to a Blender FBX exporter parameter (see UE-TARGETS §7).**

Key constraints for UE compatibility:
  - addLeafBones=false: UE adds its own leaf bones; Blender must not duplicate.
  - useArmatureDeformOnly=true: skip IK control bones.
  - bakeAnim=true: bake all animation into FBX.
  - bakeAnimUseAllBones=true: UE requires keyframes on all bones (even if unchanged).
  - useSelection=true: only export selected objects (agent controls scope).
  - globalScale=1.0 + applyUnitScale=true: correct cm conversion for UE.
  - axisForward='-Z', axisUp='Y': matches UE axis convention (see UE-TARGETS §0).
  - useTriangles=true: UE FBX pipeline requires triangles.

Output payload:
  - naniteRecommended: bool. Infer from tri count + LOD count. If tri > 100k && no LODs, recommend Nanite on UE side.
  - fbxVersion: report "BIN7400" (FBX 2014+) as exported.
  - warnings: e.g., "bone X has no deform weights", "mesh Y has N-gons (may cause import errors)".

errorCodes:
  OBJECT_NOT_FOUND
  NOT_AN_ARMATURE
  MESH_NOT_SKINNED: mesh has no armature modifier
  FILE_WRITE_FAILED
  FBX_EXPORT_FAILED
  INVALID_PARAMS: bakeAnimStep out of range, etc.

Zod Sketch (excerpt):
  z.object({
    filePath: z.string().describe("Output FBX file path"),
    objectName: z.string().describe("Armature object name"),
    meshObjectNames: z.array(z.string()).optional().describe("Mesh objects to export with armature"),
    selectedOnly: z.boolean().optional(),
    globalScale: z.number().min(0.001).max(1000).default(1.0),
    applyUnitScale: z.boolean().default(true),
    axisForward: z.enum(['-Z', 'X', 'Y', '-X', '-Y']).default('-Z').describe("For UE, always '-Z'"),
    axisUp: z.enum(['Y', 'X', 'Z', '-X', '-Y', '-Z']).default('Y').describe("For UE, always 'Y'"),
    useSelection: z.boolean().default(true),
    useMeshModifiers: z.boolean().default(true),
    meshSmoothType: z.enum(['OFF', 'FACE', 'EDGE', 'SMOOTH_GROUP']).default('FACE'),
    useTriangles: z.boolean().default(true).describe("UE requires triangles"),
    bakeAnim: z.boolean().default(true).describe("Bake animation into FBX"),
    bakeAnimUseAllBones: z.boolean().default(true).describe("UE requires keys on all bones"),
    bakeAnimStep: z.number().min(0.01).max(100).default(1.0).describe("Every N frames"),
    bakeAnimSimplify: z.number().min(0).max(100).default(0).describe("No simplification for UE"),
    addLeafBones: z.boolean().default(false).describe("CRITICAL: false for UE. UE adds leaf bones; Blender must not."),
    primaryBoneAxis: z.enum(['Y', 'X']).default('Y'),
    secondaryBoneAxis: z.enum(['X', '-X']).default('X'),
    useArmatureDeformOnly: z.boolean().default(true).describe("Skip IK control bones"),
    armatureNodeType: z.enum(['NULL', 'ROOT', 'LIMBNODE']).default('NULL'),
    useTspace: z.boolean().default(true).describe("Add tangent/binormal vectors"),
    useCustomProps: z.boolean().default(true),
    pathMode: z.enum(['AUTO', 'COPY']).default('COPY'),
    embedTextures: z.boolean().default(false).describe("UE expects external textures"),
    checkExisting: z.boolean().default(true)
  })

https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.fbx
https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine
```

#### 10. `export_fbx_animation` ⭐ **ANIMATION-ONLY EXPORT**
```
Signature: export_fbx_animation(
  filePath: str,
  objectName: str = "Armature",
  actionName: str = "",  // if empty, use active action
  frameStart: int = 1,
  frameEnd: int = 250,
  globalScale: float = 1.0,
  applyUnitScale: bool = true,
  bakeAnimStep: float = 1.0,
  bakeAnimSimplify: float = 0.0,
  axisForward: enum('-Z' | 'X' | 'Y' | '-X' | '-Y') = '-Z',
  axisUp: enum('Y' | 'X' | 'Z' | '-X' | '-Y' | '-Z') = 'Y'
) -> {
  ok: bool,
  data: {
    filePath,
    actionName,
    frameCount: int,
    fbxVersion: str
  },
  refs: { objectName, actionName },
  nextSteps: [ "import_fbx_animation_to_unreal_engine" ],
  warnings: []
}

Description:
Export a single Action as an animation-only FBX (no mesh).
**UE-TARGETS §1.3: "one Action per FBX". Use this for per-clip export.**

Composite wrapper around `export_fbx_skeletal` with `bakeAnim=true, bakeAnimUseAllBones=true, object_types={'ARMATURE'}`.

errorCodes:
  OBJECT_NOT_FOUND
  NOT_AN_ARMATURE
  ACTION_NOT_FOUND
  FILE_WRITE_FAILED

Zod Sketch:
  z.object({
    filePath: z.string(),
    objectName: z.string(),
    actionName: z.string().optional().describe("Action to export; if empty, use active"),
    frameStart: z.number().int().min(1),
    frameEnd: z.number().int().min(1),
    globalScale: z.number().default(1.0),
    applyUnitScale: z.boolean().default(true),
    bakeAnimStep: z.number().default(1.0),
    bakeAnimSimplify: z.number().default(0.0),
    axisForward: z.enum(['-Z', 'X', 'Y', '-X', '-Y']).default('-Z'),
    axisUp: z.enum(['Y', 'X', 'Z', '-X', '-Y', '-Z']).default('Y')
  })

Design Question: Should `export_fbx_animations_all` auto-generate a folder of individual FBX files (one per Action)?
(Answer in DECISIONS.md ADR-007: yes, ship as composite in v1.1; v1.0 exports one Action at a time)
```

#### glTF Export — Multi-Animation

#### 11. `export_gltf_skeletal`
```
Signature: export_gltf_skeletal(
  filePath: str,
  objectName: str = "Armature",
  meshObjectNames: string[] = [],
  animationMode: enum('ACTIONS' | 'NLA_TRACKS' | 'SCENE') = 'ACTIONS',
  selectedOnly: bool = true,
  globalScale: float = 1.0,
  useSelection: bool = true,
  exportMaterials: bool = true,
  exportAnimations: bool = true,
  exportNormals: bool = true,
  exportTexcoords: bool = true,
  exportTangents: bool = true,
  exportSkins: bool = true,
  exportMorph: bool = true,
  exportDef Bones: bool = false,
  exportForceSampling: bool = true,
  exportFrameStep: int = 1,
  draco MeshCompressionEnable: bool = false
) -> {
  ok: bool,
  data: {
    filePath,
    meshCount: int,
    animationCount: int,
    materialCount: int,
    fileSize: int
  },
  nextSteps: [ "import_gltf_to_unreal_engine_or_unity" ]
}

Description:
Export skeletal mesh + animations as glTF 2.0 (multi-animation per file, unlike FBX's one-per-file).
animationMode='ACTIONS': each Action becomes one glTF animation.
animationMode='NLA_TRACKS': each NLA track becomes one glTF animation.
animationMode='SCENE': baked scene animation as single clip.

**Key difference from FBX:** glTF **supports multiple animations in one file**, so agent can export all clips at once.

errorCodes:
  OBJECT_NOT_FOUND
  NOT_AN_ARMATURE
  FILE_WRITE_FAILED
  GLTF_EXPORT_FAILED

Zod Sketch (excerpt):
  z.object({
    filePath: z.string().describe("Output glTF file path"),
    objectName: z.string(),
    meshObjectNames: z.array(z.string()).optional(),
    animationMode: z.enum(['ACTIONS', 'NLA_TRACKS', 'SCENE']).default('ACTIONS').describe("glTF can pack multiple animations unlike FBX"),
    selectedOnly: z.boolean().optional(),
    globalScale: z.number().default(1.0),
    exportAnimations: z.boolean().default(true),
    exportSkins: z.boolean().default(true),
    exportMorph: z.boolean().default(true).describe("Export shape keys as morph targets"),
    exportForceSampling: z.boolean().default(true),
    exportFrameStep: z.number().int().min(1).optional(),
    dracoMeshCompressionEnable: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.gltf
https://dev.epicgames.com/documentation/en-us/unreal-engine/datasmith-overview
```

#### Static Mesh Export

#### 12. `export_fbx_static`
```
Signature: export_fbx_static(
  filePath: str,
  meshObjectNames: string[] = [],
  lodCount: int = 1,
  selectedOnly: bool = true,
  globalScale: float = 1.0,
  applyUnitScale: bool = true,
  useTriangles: bool = true,
  useMeshModifiers: bool = true,
  [... FBX-common params from export_fbx_skeletal ...]
) -> {
  ok: bool,
  data: { filePath, meshCount, triangleCount, naniteRecommended: bool },
  nextSteps: [ "import_fbx_static_to_unreal_engine" ]
}

Zod Sketch (excerpt):
  z.object({
    filePath: z.string(),
    meshObjectNames: z.array(z.string()).describe("Static meshes to export"),
    lodCount: z.number().int().min(1).default(1),
    selectedOnly: z.boolean().default(true),
    globalScale: z.number().default(1.0),
    useTriangles: z.boolean().default(true),
    [... ]
  })

https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.fbx
https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine
```

#### Alembic Export (Hair / Groom)

#### 13. `export_alembic_hair`
```
Signature: export_alembic_hair(
  filePath: str,
  particleSystemName: str,
  frameStart: int = 1,
  frameEnd: int = 250,
  samplingRate: int = 1,
  globalScale: float = 1.0,
  useInstancing: bool = true
) -> {
  ok: bool,
  data: { filePath, particleCount, frameCount },
  nextSteps: [ "import_alembic_to_unreal_groom" ]
}

Description:
Export hair particle systems or curves as Alembic (.abc) for UE Groom system.
samplingRate: number of substeps per frame (higher = more detail, larger file).
UE can import Alembic curves directly into a Groom asset.

errorCodes:
  OBJECT_NOT_FOUND
  NO_PARTICLE_SYSTEMS
  FILE_WRITE_FAILED

Zod Sketch:
  z.object({
    filePath: z.string(),
    particleSystemName: z.string().describe("Name of particle system or hair object"),
    frameStart: z.number().int().min(1).optional(),
    frameEnd: z.number().int().optional(),
    samplingRate: z.number().int().min(1).optional(),
    globalScale: z.number().optional(),
    useInstancing: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.alembic_export
https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-hair-strands-grooming
```

#### USD Export

#### 14. `export_usd_skeletal`
```
Signature: export_usd_skeletal(
  filePath: str,
  objectName: str = "Armature",
  meshObjectNames: string[] = [],
  exportAnimation: bool = true,
  exportArmatures: bool = true,
  exportShapekeys: bool = true,
  globalScale: float = 1.0,
  convertOrientation: bool = true,
  exportGlobalForward: enum('X' | 'Y' | 'Z' | '-X' | '-Y' | '-Z') = '-Z',
  exportGlobalUp: enum('X' | 'Y' | 'Z' | '-X' | '-Y' | '-Z') = 'Y'
) -> {
  ok: bool,
  data: { filePath, usdVersion: str },
  nextSteps: [ "import_usd_to_unreal_engine" ]
}

Description:
Export skeletal mesh to USD format. USD is more modern than FBX but less universally supported.
Blender 4.2+ has stable USD export (see UE-TARGETS note on USD stability).

errorCodes:
  OBJECT_NOT_FOUND
  NOT_AN_ARMATURE
  FILE_WRITE_FAILED
  USD_EXPORT_FAILED

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.usd$/),
    objectName: z.string(),
    meshObjectNames: z.array(z.string()).optional(),
    exportAnimation: z.boolean().optional(),
    exportArmatures: z.boolean().optional(),
    exportShapekeys: z.boolean().optional(),
    globalScale: z.number().optional(),
    convertOrientation: z.boolean().optional(),
    exportGlobalForward: z.enum(['X', 'Y', 'Z', '-X', '-Y', '-Z']).optional(),
    exportGlobalUp: z.enum(['X', 'Y', 'Z', '-X', '-Y', '-Z']).optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.usd_export
https://dev.epicgames.com/documentation/en-us/unreal-engine/universal-scene-description-usd
```

#### OBJ Export

#### 15. `export_obj_static`
```
Signature: export_obj_static(
  filePath: str,
  meshObjectNames: string[] = [],
  selectedOnly: bool = true,
  globalScale: float = 1.0,
  applyTransform: bool = true,
  exportUvs: bool = true,
  exportNormals: bool = true,
  exportColors: bool = false,
  exportMaterials: bool = true
) -> {
  ok: bool,
  data: { filePath }
}

Description:
Export static meshes as Wavefront OBJ (simple, widely supported, no animation).
OBJ does not support skeletal animation; use for static props only.

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.obj$/),
    meshObjectNames: z.array(z.string()),
    [... ]
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.obj_export
```

#### BVH Motion Capture Export

#### 16. `export_bvh_animation`
```
Signature: export_bvh_animation(
  filePath: str,
  objectName: str = "Armature",
  frameStart: int = 1,
  frameEnd: int = 250,
  globalScale: float = 1.0,
  rotateMode: enum('NATIVE' | 'XYZ' | 'XZY' | 'YXZ' | 'YZX' | 'ZXY' | 'ZYX') = 'NATIVE'
) -> {
  ok: bool,
  data: { filePath, frameCount }
}

Description:
Export armature animation as BVH (Biovision Hierarchical) motion capture format.
Used for mocap data interchange, can be imported back into Blender or other tools.

errorCodes:
  OBJECT_NOT_FOUND
  NOT_AN_ARMATURE
  FILE_WRITE_FAILED

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.bvh$/),
    objectName: z.string(),
    frameStart: z.number().int().min(1).optional(),
    frameEnd: z.number().int().optional(),
    globalScale: z.number().optional(),
    rotateMode: z.enum(['NATIVE', 'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX']).optional()
  })

https://docs.blender.org/api/current/bpy.ops.export_anim.html#bpy.ops.export_anim.bvh
```

### Import Operator Matrix

#### 17. `import_fbx_animation`
```
Signature: import_fbx_animation(
  filePath: str,
  targetArmatureName: str = "Armature",
  globalScale: float = 1.0,
  useAnim: bool = true,
  ignoreLeafBones: bool = false,
  automaticBoneOrientation: bool = false
) -> {
  ok: bool,
  data: { actionName, frameCount },
  refs: { actionName }
}

Description:
Import FBX animation clip into an existing armature.
Target armature must already exist and have matching skeleton.

errorCodes:
  FILE_NOT_FOUND
  OBJECT_NOT_FOUND: target armature
  NOT_AN_ARMATURE
  SKELETON_MISMATCH: bone names do not align

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.fbx$/),
    targetArmatureName: z.string(),
    globalScale: z.number().optional(),
    useAnim: z.boolean().default(true),
    ignoreLeafBones: z.boolean().optional(),
    automaticBoneOrientation: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.import_scene.html#bpy.ops.import_scene.fbx
```

#### 18. `import_fbx_skeletal`
```
Signature: import_fbx_skeletal(
  filePath: str,
  globalScale: float = 1.0,
  useAnim: bool = true,
  useCustomNormals: bool = true,
  importSubsurfaces: bool = false
) -> {
  ok: bool,
  data: { armatureName, meshNames[], animationName? },
  refs: { armatureName, meshNames[] }
}

Description:
Import FBX skeletal mesh + armature + animation.

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.fbx$/),
    globalScale: z.number().optional(),
    useAnim: z.boolean().optional(),
    useCustomNormals: z.boolean().optional(),
    importSubsurfaces: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.fbx_import
```

#### 19. `import_gltf_skeletal`
```
Signature: import_gltf_skeletal(
  filePath: str,
  globalScale: float = 1.0,
  importAnimations: bool = true,
  importSkeletons: bool = true,
  importBlendshapes: bool = true,
  createCollection: bool = false
) -> {
  ok: bool,
  data: { armatureName, meshNames[], animationNames[] },
  refs: { armatureName }
}

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.(gltf|glb)$/),
    globalScale: z.number().optional(),
    importAnimations: z.boolean().optional(),
    importSkeletons: z.boolean().optional(),
    importBlendshapes: z.boolean().optional(),
    createCollection: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.import_scene.html#bpy.ops.import_scene.gltf
```

#### 20. `import_alembic`
```
Signature: import_alembic(
  filePath: str,
  globalScale: float = 1.0,
  setFrameRange: bool = true,
  validateMeshes: bool = true
) -> {
  ok: bool,
  data: { objectNames[], frameCount }
}

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.abc$/),
    globalScale: z.number().optional(),
    setFrameRange: z.boolean().optional(),
    validateMeshes: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.alembic_import
```

#### 21. `import_usd_skeletal`
```
Signature: import_usd_skeletal(
  filePath: str,
  globalScale: float = 1.0,
  setFrameRange: bool = true,
  importAnimations: bool = true,
  importSkeletons: bool = true,
  importShapeKeys: bool = true
) -> {
  ok: bool,
  data: { armatureName?, meshNames[], animationNames[] }
}

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.usd(a)?$/),
    globalScale: z.number().optional(),
    setFrameRange: z.boolean().optional(),
    importAnimations: z.boolean().optional(),
    importSkeletons: z.boolean().optional(),
    importShapeKeys: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.usd_import
```

#### 22. `import_obj_static`
```
Signature: import_obj_static(
  filePath: str,
  globalScale: float = 1.0,
  useImageSearch: bool = false,
  mergeMeshes: bool = false
) -> {
  ok: bool,
  data: { meshNames[], materialNames[] }
}

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.obj$/),
    globalScale: z.number().optional(),
    useImageSearch: z.boolean().optional(),
    mergeMeshes: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.obj_import
```

#### 23. `import_bvh_animation`
```
Signature: import_bvh_animation(
  filePath: str,
  globalScale: float = 1.0,
  rotationMode: enum('NATIVE' | 'XYZ' | 'XZY' | 'YXZ' | 'YZX' | 'ZXY' | 'ZYX') = 'NATIVE'
) -> {
  ok: bool,
  data: { armatureName, actionName, frameCount }
}

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.bvh$/),
    globalScale: z.number().optional(),
    rotationMode: z.enum(['NATIVE', 'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX']).optional()
  })

https://docs.blender.org/api/current/bpy.ops.import_anim.html
```

### File I/O

#### 24. `blend_open`
```
Signature: blend_open(
  filePath: str,
  loadUi: bool = true,
  useScripts: bool = false
) -> {
  ok: bool,
  data: { filePath, sceneCount: int }
}

Description:
Open a .blend file in the current Blender session.

errorCodes:
  FILE_NOT_FOUND
  BLEND_LOAD_FAILED
  INVALID_BLEND_FILE

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.blend$/),
    loadUi: z.boolean().optional(),
    useScripts: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.open_mainfile
```

#### 25. `blend_save`
```
Signature: blend_save(
  filePath: str = "",  // if empty, save over current file
  compress: bool = false
) -> {
  ok: bool,
  data: { filePath }
}

Zod Sketch:
  z.object({
    filePath: z.string().regex(/\.blend$/).optional(),
    compress: z.boolean().optional()
  })

https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.save_mainfile
```

---

## Part C: Feasibility Verdict Table

| Operation | Operator(s) Used | Feasible? | Partial Notes | Blocked Notes |
|-----------|------------------|-----------|----------------|---------------|
| **Animation Authoring** |
| Create Action | `bpy.data.actions.new()` → `obj.animation_data.action` | ✅ GREEN | — | — |
| Insert keyframes (bone transform) | `pose_bone.keyframe_insert('location', frame=N)` | ✅ GREEN | Per-channel via `data_path` arg | — |
| Insert keyframes (object) | `obj.keyframe_insert('location', frame=N)` | ✅ GREEN | Root motion support | — |
| Edit F-curve values | `fcurve.keyframe_points[i].co / handle_* attrs` | ✅ GREEN | Surgical edits post-hoc | — |
| Add F-curve modifiers | `fcurve.modifiers.new(type='CYCLES', ...)` | ✅ GREEN | Cycles, Noise, Limits, Stepped, Generator | — |
| **NLA / Multi-Clip** |
| Create NLA track | `obj.animation_data.nla_tracks.new()` | ✅ GREEN | — | — |
| Push action to NLA strip | `track.strips.new(name, frame, action)` | ✅ GREEN | — | — |
| Bake NLA → Action | `bpy.ops.nla.bake(...)` | ✅ GREEN | Constraints, drivers, NLA stack | **Main-thread only** (handled by async drain) |
| **Retargeting** |
| Add Copy Rotation constraint | `bone.constraints.new('COPY_ROTATION')` | ✅ GREEN | Per-bone, configurable | — |
| Bake constraints into keys | `nla.bake(..., visual_keying=True, clear_constraints=True)` | ✅ GREEN | — | — |
| Bone mapping inference | Script-side (no native op) | 🟡 YELLOW | Manual dict or name-similarity heuristic | Full auto-rig like Rigify requires paid addon |
| **Export** |
| FBX skeletal (animation + mesh) | `bpy.ops.export_scene.fbx(...)` | ✅ GREEN | ~40 typed params per UE-TARGETS §7 | — |
| FBX animation-only | `bpy.ops.export_scene.fbx(..., object_types={'ARMATURE'}, ...)` | ✅ GREEN | Wrapper, per-Action loop | — |
| glTF skeletal (multi-anim per file) | `bpy.ops.export_scene.gltf(...)` | ✅ GREEN | ~60 params; supports multiple animations | — |
| USD skeletal | `bpy.ops.wm.usd_export(...)` | ✅ GREEN | Blender 4.2+ stable | **USD older versions unstable; 4.2+ required** |
| Alembic (hair/groom) | `bpy.ops.wm.alembic_export(...)` | ✅ GREEN | Curve export for UE Groom | — |
| OBJ (static) | `bpy.ops.wm.obj_export(...)` | ✅ GREEN | No animation support | OBJ cannot carry skeletal rigs |
| BVH motion capture | `bpy.ops.export_anim.bvh(...)` | ✅ GREEN | Rotation mode selection | — |
| **Import** |
| FBX (skeletal + animation) | `bpy.ops.import_scene.fbx(...)` | ✅ GREEN | — | — |
| FBX (animation into existing rig) | `bpy.ops.import_scene.fbx(...) ` + manual target binding | 🟡 YELLOW | Manual skeleton matching required; no auto-remap | Would require agent-side name mapping + constraint setup |
| glTF (skeletal + animation) | `bpy.ops.import_scene.gltf(...)` | ✅ GREEN | — | — |
| USD | `bpy.ops.wm.usd_import(...)` | ✅ GREEN | Blender 4.2+ required | — |
| Alembic | `bpy.ops.wm.alembic_import(...)` | ✅ GREEN | — | — |
| OBJ | `bpy.ops.wm.obj_import(...)` | ✅ GREEN | Static meshes only | — |
| BVH | `bpy.ops.import_anim.bvh(...)` | ✅ GREEN | Creates new armature from BVH | — |
| **File I/O** |
| Open .blend | `bpy.ops.wm.open_mainfile(...)` | ✅ GREEN | — | — |
| Save .blend | `bpy.ops.wm.save_mainfile(...)` | ✅ GREEN | — | — |

---

## Part D: Entity Types Touched (Type Graph Entries)

Entities produced/consumed in B8:

| Entity Type | Producer Tools | Consumer Tools | Example Chain |
|-------------|-----------------|------------------|---------------|
| **Action** | `action_create`, `nla_bake_to_action` | `export_fbx_animation`, `nla_track_create_and_push_action`, `armature_retarget_to_ue5_mannequin` | `action_create("Walk") → keyframe_insert_bone(...) → export_fbx_animation(actionName="Walk")` |
| **FCurve** | `keyframe_insert_*` (implicit), `fcurve_set_keyframe_values` | `fcurve_add_modifier`, `nla_bake_to_action` | `keyframe_insert_bone(...) → fcurve_add_modifier(..., type='CYCLES')` |
| **NLATrack** | `nla_track_create_and_push_action` | `nla_bake_to_action`, `export_gltf_skeletal(..., animationMode='NLA_TRACKS')` | `nla_track_create_and_push_action(...) → nla_bake_to_action(...)` |
| **NLAStrip** | `nla_track_create_and_push_action` | (read-only in retargeting context) | — |
| **AnimationData** | `action_create` | `keyframe_insert_bone`, `nla_track_create_and_push_action` | — |
| **Bone** | (rigging layer, B7) | `keyframe_insert_bone`, `armature_retarget_to_ue5_mannequin` (reads bones) | — |
| **Constraint** | (rigging layer, B7) | `armature_retarget_to_ue5_mannequin` (adds constraints), `nla_bake_to_action` (bakes + clears) | `armature_retarget_to_ue5_mannequin(...) → nla_bake_to_action(..., clearConstraints=True)` |

---

## Part E: Open Issues / Design Questions

### Issue 1: Retargeting Complexity — v1.0 vs v1.1

**Question:** `armature_retarget_to_ue5_mannequin` is a large composite tool (~7 steps, many error modes). Should it ship in v1.0 or defer to v1.1 after animation primitives stabilize?

**Recommendation:** **Defer to v1.1.** Ship primitives in v1.0:
- `bone_add_copy_rotation_constraint`
- `nla_bake_to_action` (already listed above)
- `constraint_set_target`

Agent can compose multi-step retargeting workflows. v1.1 ships `armature_retarget_to_ue5_mannequin` as a high-level convenience.

**ADR:** Write ADR-006: "Composite tools — when to ship vs defer."

---

### Issue 2: Batch Animation Export — Single vs Batch Mode

**Question:** `export_fbx_animation` exports one Action per file (UE requirement). Should the tool catalog also include `export_fbx_animations_all` that auto-loops and produces a folder of FBX files?

**Recommendation:** **v1.0 ships `export_fbx_animation` only.** Agent can loop. v1.1 adds `export_fbx_animations_all` composite for convenience. Benefits: v1.0 keeps tool count tight; agent learns explicit composition.

**ADR:** Write ADR-007: "Batch export — agent-side loop vs composite tool."

---

### Issue 3: glTF Multi-Animation Divergence from FBX

**Question:** glTF supports multiple animations per file, unlike FBX's one-per-file. Should `export_gltf_skeletal` default to `animationMode='ACTIONS'` (one glTF animation per Blender Action, all in one file)?

**Recommendation:** **Yes, default to 'ACTIONS'.** This is glTF's strength over FBX. Agent can control via param.

---

### Issue 4: USD Export Stability

**Question:** Blender 4.2 has USD export, but was USD stable in 4.2 or is 4.3+ required?

**Recommendation:** **Verify with Blender 4.2 LTS release notes.** If stable, ship. If provisional, mark as "4.3+ recommended" in tool warnings.

---

### Issue 5: Animation Retargeting Without Rigify

**Question:** Full Rigify auto-rigging is out of scope (requires paid addon, modal UI). How does the agent set up bone mapping for `armature_retarget_to_ue5_mannequin`?

**Options:**
1. Manual dict: agent supplies `{ source_bone: mannequin_bone, ... }` (tedious, requires domain knowledge).
2. Name-similarity heuristic: script infers mapping from bone name overlap (fuzzy match).
3. Both: try heuristic first, allow manual override.

**Recommendation:** **Option 3.** v1.0: agent supplies manual dict. v1.1: add `bone_map_infer_from_names()` helper using difflib ratio.

---

### Issue 6: Constraint Baking Overhead

**Question:** `nla_bake_to_action(..., visual_keying=True)` evaluates all constraints every frame on the main thread. For long animations (60 fps × 600 frames = 36k evaluations), this can be slow. Should the tool offer a "fast bake" mode (skip constraints)?

**Recommendation:** **Yes, add `skipConstraints: bool = false` parameter.** If true, bake without constraint evaluation (faster, but loses constraint effects). Document trade-off.

---

## Part F: High-Level Workflow Examples

### Example 1: Simple Animation Export (No Retargeting)

```
1. action_create(objectName="Armature", actionName="Walk_Cycle")
   → refs: { actionName: "Walk_Cycle" }

2. keyframe_insert_bone(
     objectName="Armature", boneName="pelvis", 
     frame=[1, 5, 10, ...], dataPath="location",
     useVisualKeying=false
   )
   → Repeat for all bones, all frames

3. export_fbx_animation(
     filePath="Walk_Cycle.fbx",
     objectName="Armature",
     actionName="Walk_Cycle",
     frameStart=1, frameEnd=120,
     globalScale=1.0, applyUnitScale=true
   )
   → { ok: true, filePath: "...", frameCount: 120, fbxVersion: "BIN7400" }

   Result: "Walk_Cycle.fbx" ready for UE import.
```

### Example 2: Constraint-Based Animation (Requires Bake)

```
1. action_create(objectName="Armature", actionName="IK_Walk")

2. [Add IK constraints to feet]
   constraint_add(...) [not yet in schema; use existing bone constraint primitives from B7]

3. [Keyframe root/body, IK solves feet]
   keyframe_insert_bone(..., dataPath="location", useVisualKeying=true)

4. nla_bake_to_action(
     objectName="Armature",
     frameStart=1, frameEnd=120,
     visualKeying=true, clearConstraints=true
   )
   → refs: { actionName: "IK_Walk" }, data: { keysCreated: 9000 }
   → All constraints baked into clean rotation/location keys.

5. export_fbx_animation(actionName="IK_Walk", ...)
   → UE receives clean FK-only animation.
```

### Example 3: Character Retargeting (Deferred to v1.1)

```
[In v1.0, agent manually composes]:

1. import_fbx_skeletal(filePath="source_character.fbx")
   → refs: { armatureName: "source_rig" }

2. import_fbx_skeletal(filePath="ue5_mannequin.fbx")
   → refs: { armatureName: "Armature.mannequin" }

3. [Agent loops through bone mapping]:
   boneMapping = {
       "shoulder_l": "clavicle_l",
       "arm_l": "upperarm_l",
       ...
   }
   for (source, target) in boneMapping:
       bone_add_copy_rotation_constraint(
           armatureName="Armature.mannequin",
           boneName=target,
           targetArmatureName="source_rig",
           targetBoneName=source
       )

4. nla_bake_to_action(
     objectName="Armature.mannequin",
     frameStart=1, frameEnd=120,
     clearConstraints=true
   )

5. export_fbx_animation(
     objectName="Armature.mannequin",
     actionName="source_action_retargeted",
     ...
   )

[In v1.1]:
   armature_retarget_to_ue5_mannequin(
       sourceArmatureName="source_rig",
       targetArmatureName="Armature.mannequin",
       boneMapping={...},
       actionName="source_action",
       outputActionSuffix="_retargeted"
   )
   → One call replaces steps 1-4 above.
```

---

## Part G: Summary

### Tool Count Target: ~25 for B8

- **Authoring primitives:** 6 (`action_create`, `keyframe_insert_bone`, `keyframe_insert_object`, `fcurve_set_keyframe_values`, `fcurve_add_modifier`, `nla_track_create_and_push_action`)
- **Baking:** 1 (`nla_bake_to_action`)
- **Retargeting (composite):** 1 (deferred to v1.1; v1.0 relies on primitives)
- **Export ops:** 7 (`export_fbx_skeletal`, `export_fbx_animation`, `export_gltf_skeletal`, `export_usd_skeletal`, `export_alembic_hair`, `export_obj_static`, `export_bvh_animation`)
- **Import ops:** 7 (`import_fbx_animation`, `import_fbx_skeletal`, `import_gltf_skeletal`, `import_usd_skeletal`, `import_alembic`, `import_obj_static`, `import_bvh_animation`)
- **File I/O:** 2 (`blend_open`, `blend_save`)

**Total: ~24 for v1.0; +1 (`armature_retarget_to_ue5_mannequin`) for v1.1.**

### Critical URLs Cited

- **Blender 4.2 API:**
  - [bpy.ops.export_scene.fbx](https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.fbx)
  - [bpy.ops.export_scene.gltf](https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.gltf)
  - [bpy.ops.nla.bake](https://docs.blender.org/api/current/bpy.ops.nla.html#bpy.ops.nla.bake)
  - [bpy.types.FCurve](https://docs.blender.org/api/current/bpy.types.FCurve.html)
  - [bpy.types.NlaTrack](https://docs.blender.org/api/current/bpy.types.NlaTrack.html)
  - [bpy.ops.wm.usd_export](https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.usd_export)
  - [bpy.ops.wm.alembic_export](https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.alembic_export)
  - [bpy.ops.export_anim.bvh](https://docs.blender.org/api/current/bpy.ops.export_anim.html#bpy.ops.export_anim.bvh)

- **UE5 Docs:**
  - [FBX Skeletal Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine)
  - [Third Person Template](https://dev.epicgames.com/documentation/en-us/unreal-engine/third-person-template-in-unreal-engine)
  - [MetaHuman Documentation](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-documentation-in-unreal-engine)
  - [Lumen Global Illumination and Reflections](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine)
  - [Nanite Virtualized Geometry](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine)

---

**End of B8 Research Report**