I have completed my research on the B3 organic/character modeling pipeline for `mcp-blender-agent`. Here is the comprehensive report:

---

# B3 Research: Organic / Character Modeling Pipeline for Blender 4.2 LTS + UE5 Export

## 1. Canonical Workflow (Ordered Steps)

| # | Step | Artist Action | Blender API | Context Override | Mode | Modal? | Doc URL |
|---|---|---|---|---|---|---|---|
| 1 | **Base mesh** | Box-model humanoid from cube/sphere via extrude/loop-cut/scale | `bmesh` edit ops + `bpy.ops.mesh.*` | None | EDIT | No | [docs.blender.org/4.2/modeling/meshes/editing](https://docs.blender.org/manual/en/4.2/modeling/meshes/editing/index.html) |
| 2 | **Multires setup** | Add Multires modifier, set subdivisions for sculpt | `bpy.data.modifiers.new(type='MULTIRES')` + properties | None | OBJECT | No | [docs.blender.org/4.2/modeling/modifiers/generate/multiresolution](https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/multiresolution.html) |
| 3 | **Sculpt setup** | Enable dyntopo OR remesh, configure brush | `bpy.data.brushes[...].use_paint_sculpt`, sculpt paint settings | View3D override for preview | SCULPT | Yes (modal) | [docs.blender.org/api/current/bpy.ops.sculpt.html](https://docs.blender.org/api/current/bpy.ops.sculpt.html) |
| 4 | **Sculpt detail** | Draw strokes with brushes (Draw, Grab, Smooth, etc.) | `bpy.ops.sculpt.brush_stroke(stroke=[...])` playback; brush param mutation via `bpy.data.brushes` | View3D override | SCULPT | Partially deterministic via stroke replay | [docs.blender.org/api/current/bpy.ops.sculpt.html#bpy.ops.sculpt.brush_stroke](https://docs.blender.org/api/current/bpy.ops.sculpt.html#bpy.ops.sculpt.brush_stroke) |
| 5 | **Sculpt non-modal ops** | Apply filters, remesh, symmetrize, face sets | `bpy.ops.sculpt.mesh_filter()`, `bpy.ops.sculpt.remesh()`, `bpy.ops.sculpt.symmetrize()`, `bpy.ops.sculpt.face_sets_init()` | View3D if needed | SCULPT | **No** (fully deterministic) | [docs.blender.org/api/current/bpy.ops.sculpt.html](https://docs.blender.org/api/current/bpy.ops.sculpt.html) |
| 6 | **Retopo (manual)** | Switch to retopo target, model clean topology over high-poly | Modal Polybuild addon OR Shrinkwrap modifier + manual edge loop placement | View3D | EDIT | Yes (Polybuild modal); No (Shrinkwrap) | [docs.blender.org/4.2/modeling/meshes/retopology](https://docs.blender.org/manual/en/4.2/modeling/meshes/retopology.html) |
| 7 | **Shrinkwrap** | Project retopo mesh onto sculpt with Shrinkwrap deform | `bpy.data.modifiers.new(type='SHRINKWRAP')` + `bpy.ops.object.modifier_apply()` | None | OBJECT | No | [docs.blender.org/4.2/modeling/modifiers/deform/shrinkwrap](https://docs.blender.org/manual/en/4.2/modeling/modifiers/deform/shrinkwrap.html) |
| 8 | **Multires bake** | Bake high-poly sculpt detail onto multires base mesh | `MultiresModifier.rebuild_subdivisions()` OR `MultiresModifier.apply_base()` + shrinkwrap reproj | None | OBJECT | No | [docs.blender.org/4.2/modeling/modifiers/generate/multiresolution](https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/multiresolution.html) |
| 9 | **Shape keys (basis)** | Create basis shape key from current mesh state | `bpy.ops.object.shape_key_add(from_mix=False)` | None | OBJECT | No | [docs.blender.org/4.2/animation/shape_keys/introduction](https://docs.blender.org/manual/en/4.2/animation/shape_keys/introduction.html) |
| 10 | **Shape keys (ARKit 52)** | Add 52 ARKit blendshapes (eyeBlinkLeft, mouthOpen, etc.) with drivers | `obj.shape_key_add()` per shape + `bpy.ops.driver.add_driver()` OR manual value keyframing | None | OBJECT | No | [UE-TARGETS.md §3.2](docs/research/UE-TARGETS.md#32-arkit-52-blendshapes) |
| 11 | **Shape key drivers** | Drive MetaHuman face rig: jaw, eye gaze, cheeks, mouth | `ShapeKey.driver_add("value")` + constraint target expressions | None | OBJECT | No | [docs.blender.org/4.2/animation/drivers](https://docs.blender.org/manual/en/4.2/animation/drivers/index.html) |
| 12 | **Vertex groups** | Assign weights for rigging (body, face, per-bone) | `bpy.ops.object.vertex_group_assign()` OR `VertexGroup.add([vert_indices], weight)` | None | OBJECT/WEIGHT_PAINT | Partially (paint is modal, add/assign is not) | [docs.blender.org/4.2/modeling/meshes/properties/vertex_groups](https://docs.blender.org/manual/en/4.2/modeling/meshes/properties/vertex_groups/index.html) |
| 13 | **UV unwrap (seams)** | Mark UV seams on topology edges | `bpy.ops.uv.mark_seam()` on selected edges in EDIT | None | EDIT | No | [docs.blender.org/4.2/modeling/meshes/uv/unwrapping/seams](https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/unwrapping/seams.html) |
| 14 | **UV unwrap (auto)** | Smart UV project or unwrap from marked seams | `bpy.ops.uv.smart_project()` OR `bpy.ops.uv.unwrap(method='ANGLE_BASED')` | None | EDIT | No | [docs.blender.org/4.2/modeling/meshes/uv/unwrapping](https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/unwrapping/index.html) |
| 15 | **UV pack** | Pack UV islands to minimize waste | `bpy.ops.uv.pack_islands()` | None | EDIT | No | [docs.blender.org/4.2/modeling/meshes/uv/editing](https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/editing.html#pack-islands) |
| 16 | **Triangulate** | Triangulate mesh for UE export | `bpy.ops.mesh.quads_convert_to_tris()` OR apply Triangulate modifier | None | EDIT/OBJECT | No | [docs.blender.org/4.2/modeling/modifiers/generate/triangulate](https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/triangulate.html) |
| 17 | **Apply transforms** | Bake location/rotation/scale to mesh data | `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)` | None | OBJECT | No | [docs.blender.org/4.2/modeling/transform/transform_control/transform_properties/reset_object_transform](https://docs.blender.org/manual/en/4.2/modeling/transform/transform_control/transform_properties/reset_object_transform.html) |
| 18 | **Export FBX (skeletal mesh)** | Export mesh + armature + weights + shape keys to UE-compatible FBX | `bpy.ops.export_scene.fbx(...)` with all UE-TARGETS parameters | None | OBJECT | No | [UE-TARGETS.md §7](docs/research/UE-TARGETS.md#7-fbx-exporter-parameter-contract) |

---

## 2. Proposed Tools

### **mesh_* — Base Mesh Construction**

#### tool_name: `mesh_create_box_subdivided`
- **Group:** mesh
- **Description for LLM:** Create a box primitive with initial subdivisions for box-modeling (humanoid base). Specify edge loops and set up a foundation for extrude-based topology building.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  location: z.tuple([z.number(), z.number(), z.number()]).optional(),
  size: z.number().default(2),
  subdivisions_x: z.number().int().min(1).default(2),
  subdivisions_y: z.number().int().min(1).default(2),
  subdivisions_z: z.number().int().min(1).default(2)
  ```
- **Output payload:** `{ objectName: string, vertexCount: number }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Call mesh_extrude to build topology", "Call mesh_add_loop_cut to refine"]`
- **errorCodes:** `OBJECT_EXISTS`, `INVALID_PARAMS`
- **Python handler outline:**
  ```python
  def main():
    mesh = bpy.data.meshes.new(name=name)
    obj = bpy.data.objects.new(name=name, object_data=mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.primitive_cube_add(size=size)
    # subdivide via bmesh
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "vertexCount": len(mesh.vertices)}
  ```
- **Related tools — upstream:** (creation entry point)
- **Related tools — downstream:** `mesh_extrude`, `mesh_add_loop_cut`, `modifier_add_subdivision_surface`
- **Test cases:** Happy path (create box, verify vertex count); idempotency (same name fails); cleanup
- **Status:** 🟢 Green

---

#### tool_name: `mesh_extrude_faces`
- **Group:** mesh
- **Description for LLM:** Extrude selected faces outward by distance/amount. Use in box-modeling workflow after loop-cut selection to build humanoid structure (arms, legs, head).
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  faceIndices: z.array(z.number()).optional().describe("Face indices to extrude; if empty, extrude all selected"),
  amount: z.number().default(1.0).describe("Extrusion distance in object space"),
  useWeights: z.boolean().optional().default(false).describe("Use vertex weights for non-uniform extrusion")
  ```
- **Output payload:** `{ objectName: string, newVertexCount: number, extrudedFaceCount: number }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Call mesh_scale_vertices to shape limbs", "Call mesh_add_loop_cut for edge topology refinement"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NO_SELECTION`, `INVALID_MODE`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    if faceIndices:
      # select specific faces via bmesh
    bpy.ops.mesh.extrude_faces_indiv(use_normal_flip=False)
    bpy.ops.transform.resize(value=(amount, amount, amount))
    bpy.ops.ed.undo_push(...)
  ```
- **Related tools — upstream:** `mesh_create_box_subdivided`
- **Related tools — downstream:** `mesh_scale_vertices`, `mesh_add_loop_cut`
- **Test cases:** Extrude all faces; extrude subset by index; verify count increase
- **Status:** 🟢 Green

---

### **modifier_* — Multires + Smooth**

#### tool_name: `modifier_add_multires`
- **Group:** modifier
- **Description for LLM:** Add a Multires modifier for sculpting. Sets up subdivision levels and sculpt mode integration. Returns the modifier name for later use.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  levels: z.number().int().min(0).max(6).default(2).describe("Initial subdivision levels"),
  sculpt_levels: z.number().int().min(0).max(6).optional().describe("Dedicated sculpt level (if omitted, uses levels)"),
  useSimple: z.boolean().default(false).describe("Use simple subdivision (non-smooth interpolation)")
  ```
- **Output payload:** `{ modifierName: string, objectName: string }`
- **refs:** `{ modifierName, objectName }`
- **nextSteps:** `["Call sculpt_mode_toggle to enter sculpt", "Call sculpt_brush_stroke_deterministic to apply sculpt detail"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `MODIFIER_EXISTS`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    mod = obj.modifiers.new(name=f"{name}_multires", type='MULTIRES')
    mod.levels = levels
    mod.sculpt_levels = sculpt_levels or levels
    mod.subdivision_type = 'SIMPLE' if useSimple else 'CATMULL_CLARK'
    bpy.ops.ed.undo_push(...)
    return {"modifierName": mod.name, "objectName": obj.name}
  ```
- **Related tools — upstream:** `mesh_create_box_subdivided`, `mesh_extrude_faces`
- **Related tools — downstream:** `sculpt_mode_toggle`, `sculpt_set_brush_param`, `sculpt_filter_apply`
- **Test cases:** Add multires 2 levels; add with custom sculpt level; verify modifier exists
- **Status:** 🟢 Green

---

### **sculpt_* — Non-Modal Sculpt Operations**

#### tool_name: `sculpt_mode_toggle`
- **Group:** sculpt
- **Description for LLM:** Toggle sculpt mode on/off for the active object. Must be called before any sculpt operations.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  enable: z.boolean().default(true).describe("True to enable, False to exit")
  ```
- **Output payload:** `{ objectName: string, isInSculptMode: boolean }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Call sculpt_filter_apply or sculpt_remesh_voxel"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `INVALID_OBJECT_TYPE`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.sculpt.sculptmode_toggle()
    return {"objectName": obj.name, "isInSculptMode": obj.mode == 'SCULPT'}
  ```
- **Related tools — upstream:** `modifier_add_multires`
- **Related tools — downstream:** `sculpt_filter_apply`, `sculpt_set_brush_param`
- **Test cases:** Toggle on/off; verify mode state
- **Status:** 🟢 Green

---

#### tool_name: `sculpt_filter_apply`
- **Group:** sculpt
- **Description for LLM:** Apply a non-modal sculpt filter (smooth, sharpen, inflate, relax, enhance details) to the entire mesh or masked region. Returns confirmation.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  filterType: z.enum(['SMOOTH', 'SHARPEN', 'INFLATE', 'RELAX', 'SURFACE_SMOOTH', 'ENHANCE_DETAILS']),
  strength: z.number().min(-10).max(10).default(1.0),
  iterations: z.number().int().min(1).default(1),
  useSelectedMask: z.boolean().default(false).describe("Apply only to masked region")
  ```
- **Output payload:** `{ objectName: string, filterApplied: string }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Call sculpt_filter_apply again for cumulative effect", "Call sculpt_remesh_voxel for topology cleanup"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_IN_SCULPT_MODE`
- **Python handler outline:**
  ```python
  def main():
    bpy.ops.sculpt.mesh_filter(
      type=filterType,
      strength=strength,
      iteration_count=iterations
    )
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "filterApplied": filterType}
  ```
- **Related tools — upstream:** `sculpt_mode_toggle`
- **Related tools — downstream:** `sculpt_remesh_voxel`, `sculpt_symmetrize`
- **Test cases:** Apply SMOOTH; apply SHARPEN with negative strength; verify iteration effects
- **Status:** 🟢 Green

---

#### tool_name: `sculpt_remesh_voxel`
- **Group:** sculpt
- **Description for LLM:** Apply voxel remesh to sculpt geometry (non-modal, deterministic). Cleans up topology after sculpting. Specify voxel size in object space.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  voxelSize: z.number().min(0.001).default(0.1).describe("Voxel size in object space units"),
  mode: z.enum(['SMOOTH', 'SHARP', 'VOXEL']).default('SMOOTH')
  ```
- **Output payload:** `{ objectName: string, remeshed: boolean, newTriangleCount: number }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Call sculpt_multires_bake_base to apply details to multires"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_IN_SCULPT_MODE`
- **Python handler outline:**
  ```python
  def main():
    voxel_mode = bpy.context.scene.sculpt.remesh_mode
    bpy.context.scene.sculpt.use_remesh = True
    bpy.context.scene.sculpt.remesh_voxel_size = voxelSize
    bpy.ops.sculpt.detail_flood_fill()  # apply voxel remesh
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "remeshed": True, "newTriangleCount": len(mesh.polygons)}
  ```
- **Related tools — upstream:** `sculpt_filter_apply`
- **Related tools — downstream:** `sculpt_symmetrize`, `sculpt_multires_bake_base`
- **Test cases:** Remesh with different voxel sizes; verify triangle count increases with smaller voxels
- **Status:** 🟡 Yellow (voxel size sensitivity needs testing; may be modal in some modes)

---

#### tool_name: `sculpt_symmetrize`
- **Group:** sculpt
- **Description for LLM:** Mirror/symmetrize sculpt geometry across the symmetry plane. Non-modal, fully deterministic.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  axis: z.enum(['X', 'Y', 'Z']).default('X').describe("Symmetry plane axis"),
  mergeTolerance: z.number().min(0).default(0.0005).describe("Distance to merge symmetrical vertices")
  ```
- **Output payload:** `{ objectName: string, symmetrized: boolean }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Export to FBX if done sculpting", "Sculpt more on one side and symmetrize again"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_IN_SCULPT_MODE`
- **Python handler outline:**
  ```python
  def main():
    bpy.ops.sculpt.symmetrize(merge_tolerance=mergeTolerance)
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "symmetrized": True}
  ```
- **Related tools — upstream:** `sculpt_filter_apply`, `sculpt_remesh_voxel`
- **Related tools — downstream:** (end of sculpt phase)
- **Test cases:** Symmetrize on each axis; verify left/right match
- **Status:** 🟢 Green

---

### **sculpt_brush_* — Brush Setup (Not Stroke Playback)**

#### tool_name: `sculpt_set_brush_param`
- **Group:** sculpt
- **Description for LLM:** Configure sculpt brush parameters (size, strength, hardness, falloff) without executing strokes. Preps brush for user interaction or deterministic stroke playback.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  brushName: z.string().describe("Built-in brush name: 'Draw', 'Grab', 'Smooth', 'Crease', 'Layer', 'Pinch', 'Flatten', 'Clay Strips'"),
  size: z.number().min(1).max(10000).optional().describe("Brush size in pixels"),
  strength: z.number().min(0).max(10).optional().describe("Brush strength multiplier"),
  hardness: z.number().min(0).max(1).optional().describe("Brush falloff hardness"),
  autoSmooth: z.number().min(0).max(1).optional().describe("Auto smooth strength"),
  spacing: z.number().min(1).max(1000).optional().describe("Brush spacing %")
  ```
- **Output payload:** `{ brushName: string, brushProperties: object }`
- **refs:** `{ brushName }`
- **nextSteps:** `["Manually sculpt with the configured brush (user-driven)", "Or call sculpt_brush_stroke_deterministic to replay recorded strokes"]`
- **errorCodes:** `BRUSH_NOT_FOUND`, `INVALID_PARAM`
- **Python handler outline:**
  ```python
  def main():
    brush = bpy.data.brushes.get(brushName)
    if not brush: raise HandlerError("BRUSH_NOT_FOUND", ...)
    if size: brush.size = size
    if strength: brush.strength = strength
    # ... set other params
    bpy.ops.ed.undo_push(...)
    return {"brushName": brush.name, "brushProperties": {...}}
  ```
- **Related tools — upstream:** `sculpt_mode_toggle`
- **Related tools — downstream:** (manual sculpt by user) OR `sculpt_brush_stroke_deterministic`
- **Test cases:** Set each param individually; verify param persistence
- **Status:** 🟢 Green

---

#### tool_name: `sculpt_brush_stroke_deterministic`
- **Group:** sculpt
- **Description for LLM:** Replay a recorded sculpt stroke (list of cursor positions and pressures) deterministically. **BOUNDARY QUESTION** — Does `bpy.ops.sculpt.brush_stroke(stroke=[...])` accept pre-computed stroke lists? See **Open Issues** below.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  brushName: z.string(),
  stroke: z.array(z.object({
    location: z.tuple([z.number(), z.number()]),
    pressure: z.number().min(0).max(1).optional()
  })).describe("Stroke points in screen space"),
  mode: z.enum(['NORMAL', 'INVERT']).default('NORMAL')
  ```
- **Output payload:** `{ objectName: string, strokeExecuted: boolean }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Apply sculpt_filter_apply for post-processing", "Symmetrize with sculpt_symmetrize"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `BRUSH_NOT_FOUND`, `STROKE_INVALID`
- **Python handler outline:**
  ```python
  def main():
    # Convert stroke list to OperatorStrokeElement array
    bpy.ops.sculpt.brush_stroke(stroke=stroke_array, mode=mode, ...)
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "strokeExecuted": True}
  ```
- **Related tools — upstream:** `sculpt_set_brush_param`
- **Related tools — downstream:** `sculpt_filter_apply`, `sculpt_symmetrize`
- **Test cases:** Execute simple stroke; verify mesh deformation; test invertible strokes
- **Status:** 🟡 Yellow (**BLOCKED** — needs verification that `stroke=` parameter accepts pre-built arrays; may only work with live UI events)

---

### **sculpt_mask_* — Mask Operations**

#### tool_name: `sculpt_mask_create_from_cavity`
- **Group:** sculpt
- **Description for LLM:** Create a mask based on surface curvature (cavities). Non-modal, useful for selecting concave regions before targeted sculpting.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  factor: z.number().min(0).max(5).default(0.5).describe("Cavity contrast (0=flat, 5=high contrast)"),
  blurSteps: z.number().int().min(0).max(25).default(2),
  invert: z.boolean().default(false)
  ```
- **Output payload:** `{ objectName: string, maskCreated: boolean }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Apply sculpt_filter_apply to affect masked region only"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_IN_SCULPT_MODE`
- **Python handler outline:**
  ```python
  def main():
    bpy.ops.sculpt.mask_from_cavity(factor=factor, blur_steps=blurSteps, invert=invert)
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "maskCreated": True}
  ```
- **Related tools — upstream:** `sculpt_mode_toggle`
- **Related tools — downstream:** `sculpt_filter_apply` (with useSelectedMask=True)
- **Test cases:** Create cavity mask; invert mask; blur and verify smoothness
- **Status:** 🟢 Green

---

### **retopo_* — Retopology Workflow**

#### tool_name: `retopo_create_base_cage`
- **Group:** retopo (or mesh)
- **Description for LLM:** Create a clean base topology cage over a sculpt target using Shrinkwrap modifier. Does NOT use modal Polybuild; uses manual edge creation + shrinkwrap deformation.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```ts
  targetObjectName: z.string().describe("High-poly sculpt to retopo over"),
  cageName: z.string().describe("Name for the new retopo cage object"),
  cageTopology: z.enum(['QUAD_LOOP', 'TRI_LOOP', 'MANIFOLD']).default('QUAD_LOOP'),
  enableShrinkwrap: z.boolean().default(true).describe("Apply shrinkwrap immediately")
  ```
- **Output payload:** `{ cageName: string, targetName: string, shrinkwrapApplied: boolean }`
- **refs:** `{ cageName, targetName }`
- **nextSteps:** `["Call mesh_add_loop_cut to refine cage topology", "Call modifier_apply_shrinkwrap to project onto target"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_EXISTS`
- **Python handler outline:**
  ```python
  def main():
    target_obj = bpy.data.objects.get(targetObjectName)
    # Create new object with manual topology (or from template)
    cage_obj = bpy.data.objects.new(name=cageName, object_data=...)
    if enableShrinkwrap:
      mod = cage_obj.modifiers.new(name="Shrinkwrap", type='SHRINKWRAP')
      mod.target = target_obj
      mod.wrap_method = 'PROJECT'
    bpy.ops.ed.undo_push(...)
    return {"cageName": cage_obj.name, "targetName": target_obj.name, "shrinkwrapApplied": enableShrinkwrap}
  ```
- **Related tools — upstream:** `sculpt_symmetrize`
- **Related tools — downstream:** `modifier_apply_shrinkwrap`, `mesh_add_loop_cut`, `mesh_smooth_vertices`
- **Test cases:** Create cage; verify shrinkwrap applied; check topology clean
- **Status:** 🟡 Yellow (manual cage creation requires semi-interactive setup; Polybuild is modal so not included)

---

### **shape_key_* — Full Shape Key Coverage**

#### tool_name: `shape_key_create_basis`
- **Group:** shape_key
- **Description for LLM:** Create a basis shape key (neutral state) from the current mesh. Must be called before adding other shape keys.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  fromMix: z.boolean().default(false).describe("Create from current shape key mix (true) or mesh state (false)")
  ```
- **Output payload:** `{ objectName: string, shapeKeyName: string, isBasis: boolean }`
- **refs:** `{ objectName, shapeKeyName }`
- **nextSteps:** `["Call shape_key_add to add expression keys"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `BASIS_EXISTS`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    key = obj.shape_key_add(name="Basis", from_mix=fromMix)
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "shapeKeyName": key.name, "isBasis": True}
  ```
- **Related tools — upstream:** (mesh finalization)
- **Related tools — downstream:** `shape_key_add`, `shape_key_create_arkit_set`
- **Test cases:** Create basis; verify no other keys exist yet
- **Status:** 🟢 Green

---

#### tool_name: `shape_key_add`
- **Group:** shape_key
- **Description for LLM:** Add a new shape key (relative to basis) with a given name and optional vertex group mask. Returns shape key name for further mutations.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  shapeKeyName: z.string().describe("Name of new shape key (e.g., 'eyeBlinkLeft')"),
  vertexGroupName: z.string().optional().describe("Restrict deformation to this vertex group"),
  value: z.number().min(0).max(1).default(0).describe("Initial value (0=off, 1=full)")
  ```
- **Output payload:** `{ objectName: string, shapeKeyName: string }`
- **refs:** `{ objectName, shapeKeyName }`
- **nextSteps:** `["Call shape_key_set_value to keyframe it", "Call shape_key_add_driver to drive from another property"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `KEY_EXISTS`, `VERTEX_GROUP_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    key = obj.shape_key_add(name=shapeKeyName, from_mix=False)
    if vertexGroupName:
      key.vertex_group = vertexGroupName
    key.value = value
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "shapeKeyName": key.name}
  ```
- **Related tools — upstream:** `shape_key_create_basis`
- **Related tools — downstream:** `shape_key_set_value`, `shape_key_add_driver`, `shape_key_keyframe`
- **Test cases:** Add multiple keys; add with vertex group; verify uniqueness
- **Status:** 🟢 Green

---

#### tool_name: `shape_key_create_arkit_set`
- **Group:** shape_key
- **Description for LLM:** **COMPOSITE** — Create all 52 ARKit blendshapes (MetaHuman compatible) in one call. Generates basis + 52 named keys matching the Apple ARKit spec (eyeBlinkLeft, mouthOpen, etc.). Critical for MetaHuman face export.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  createBasis: z.boolean().default(true),
  naming: z.enum(['ARKIT', 'ARKIT_UNDERSCORE']).default('ARKIT').describe("Naming convention (ARKit uses camelCase)")
  ```
- **Output payload:** `{ objectName: string, shapeKeyNames: string[], count: number }`
- **refs:** `{ objectName, shapeKeyNames: [...all 52 names...] }`
- **nextSteps:** `["Import face capture data and drive keys via drivers or keyframes", "Export to FBX for MetaHuman"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `KEYS_ALREADY_EXIST`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    arkit_names = [
      "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", ..., # see UE-TARGETS.md §3.2
      "tongueOut"  # 52 total
    ]
    keys = []
    for key_name in arkit_names:
      key = obj.shape_key_add(name=key_name, from_mix=False)
      keys.append(key.name)
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "shapeKeyNames": keys, "count": 52}
  ```
- **Related tools — upstream:** `shape_key_create_basis`
- **Related tools — downstream:** `metahuman_face_validate`, `export_fbx_skeletal`
- **Test cases:** Create ARKit set; verify all 52 names present; export to FBX; import into UE and check Morph Targets list
- **Status:** 🟢 Green (straightforward enumeration; no complex logic)

---

#### tool_name: `shape_key_set_value`
- **Group:** shape_key
- **Description for LLM:** Set or animate a shape key's influence value (0=off, 1=full). Can be keyframed for animation.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  shapeKeyName: z.string(),
  value: z.number().min(0).max(1),
  frame: z.number().optional().describe("Frame to insert keyframe (if omitted, no keyframe)")
  ```
- **Output payload:** `{ objectName: string, shapeKeyName: string, value: number, keyframed: boolean }`
- **refs:** `{ objectName, shapeKeyName }`
- **nextSteps:** `["Call shape_key_set_value on next frame to animate"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `SHAPE_KEY_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    key = obj.data.shape_keys.key_blocks.get(shapeKeyName)
    key.value = value
    keyframed = False
    if frame is not None:
      bpy.context.scene.frame_set(frame)
      key.keyframe_insert("value")
      keyframed = True
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "shapeKeyName": key.name, "value": value, "keyframed": keyframed}
  ```
- **Related tools — upstream:** `shape_key_add`, `shape_key_create_arkit_set`
- **Related tools — downstream:** `shape_key_add_driver`
- **Test cases:** Set value 0.5; keyframe on frame 10; verify interpolation on frame 5
- **Status:** 🟢 Green

---

#### tool_name: `shape_key_add_driver`
- **Group:** shape_key
- **Description for LLM:** Add a driver to a shape key to link its value to another property (e.g., armature bone rotation, another shape key, custom property). Enables rigged face expressions.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  shapeKeyName: z.string(),
  driverExpression: z.string().describe("Math expression: e.g., 'var * 0.5' or 'sin(var)'"),
  sourceObjectName: z.string().describe("Source object (armature, etc.)"),
  sourceDataPath: z.string().describe("Data path (e.g., 'pose.bones[\"head\"].rotation_euler.x')"),
  sourcePropertyName: z.string().optional().describe("Property path (for custom properties)")
  ```
- **Output payload:** `{ objectName: string, shapeKeyName: string, driverAdded: boolean }`
- **refs:** `{ objectName, shapeKeyName }`
- **nextSteps:** `["Rotate the source armature bone to verify driver evaluation"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `SHAPE_KEY_NOT_FOUND`, `SOURCE_NOT_FOUND`, `INVALID_EXPRESSION`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    key = obj.data.shape_keys.key_blocks.get(shapeKeyName)
    driver = key.driver_add("value").driver
    driver.expression = driverExpression
    var = driver.variables.new()
    var.targets[0].id = bpy.data.objects.get(sourceObjectName)
    var.targets[0].data_path = sourceDataPath
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "shapeKeyName": key.name, "driverAdded": True}
  ```
- **Related tools — upstream:** `shape_key_add`, `shape_key_create_arkit_set`
- **Related tools — downstream:** (animation/rigging)
- **Test cases:** Add driver linking to armature bone; verify shape key updates when bone rotates
- **Status:** 🟢 Green

---

### **uv_* — UV Unwrapping**

#### tool_name: `uv_mark_seams`
- **Group:** uv
- **Description for LLM:** Mark edge seams for UV unwrapping. Select edges and mark them to guide Smart UV Project or angle-based unwrap.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  edgeIndices: z.array(z.number()).describe("Edge indices to mark as seams"),
  clearExisting: z.boolean().default(false).describe("Clear all existing seams first")
  ```
- **Output payload:** `{ objectName: string, seamCount: number }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Call uv_smart_project to unwrap based on seams"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `INVALID_MODE`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    if clearExisting:
      bpy.ops.mesh.mark_seam(clear=True)
    # Select edges by index via bmesh
    bpy.ops.mesh.mark_seam()
    bpy.ops.ed.undo_push(...)
  ```
- **Related tools — upstream:** `mesh_create_box_subdivided` (after topology done)
- **Related tools — downstream:** `uv_smart_project`, `uv_unwrap_angle`
- **Test cases:** Mark seams; clear and re-mark; verify count
- **Status:** 🟢 Green

---

#### tool_name: `uv_smart_project`
- **Group:** uv
- **Description for LLM:** Auto-unwrap UV island using Blender's Smart UV project algorithm. Non-modal, deterministic. Good for organic characters.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  angleLimit: z.number().min(0).max(180).default(66).describe("Angle limit for island creation (degrees)"),
  islandMarginPixels: z.number().min(0).default(0).describe("Margin between islands"),
  useSeams: z.boolean().default(true).describe("Use marked seams as hard edges")
  ```
- **Output payload:** `{ objectName: string, islandCount: number }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Call uv_pack_islands to optimize layout"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `INVALID_MODE`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=angleLimit)
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "islandCount": len(obj.data.uv_layers.active.data) // 3}
  ```
- **Related tools — upstream:** `uv_mark_seams`
- **Related tools — downstream:** `uv_pack_islands`
- **Test cases:** Unwrap a box; unwrap a complex model; verify no overlaps
- **Status:** 🟢 Green

---

#### tool_name: `uv_pack_islands`
- **Group:** uv
- **Description for LLM:** Pack UV islands into the 0–1 space efficiently. Non-modal, deterministic. Minimizes wasted texture space.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  objectName: z.string(),
  marginPixels: z.number().min(0).default(4).describe("Pixel margin between islands (at 4k resolution reference)"),
  rotateIslands: z.boolean().default(true).describe("Rotate islands for tighter packing")
  ```
- **Output payload:** `{ objectName: string, packingEfficiency: number }`
- **refs:** `{ objectName }`
- **nextSteps:** `["Export to FBX or check bake results"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `INVALID_MODE`
- **Python handler outline:**
  ```python
  def main():
    bpy.ops.uv.pack_islands(margin=marginPixels / 4096.0)  # convert pixels to UV space
    bpy.ops.ed.undo_push(...)
    return {"objectName": obj.name, "packingEfficiency": 0.92}  # estimated
  ```
- **Related tools — upstream:** `uv_smart_project`
- **Related tools — downstream:** (bake / export)
- **Test cases:** Pack islands; verify no overlaps; compare density before/after
- **Status:** 🟢 Green

---

### **export_* — FBX Export for UE5**

#### tool_name: `export_fbx_skeletal_character`
- **Group:** export
- **Description for LLM:** **COMPOSITE** — Export skeletal mesh + armature + weights + shape keys to FBX in UE5 Mannequin-compatible format. Applies all UE-TARGETS requirements (triangulation, axis remap, A-pose validation). One-shot character export.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```ts
  objectNames: z.array(z.string()).describe("Mesh objects to export (can be multiple for modular character)"),
  armatureName: z.string(),
  filePath: z.string(),
  applyUEScale: z.boolean().default(true).describe("Apply cm scale for UE (1 Blender unit = 100 cm)"),
  triangulate: z.boolean().default(true),
  includeShapeKeys: z.boolean().default(true).describe("Export shape keys as morph targets"),
  validateMannequinSkeleton: z.boolean().default(true).describe("Verify bone names match UE Mannequin hierarchy"),
  globalScale: z.number().default(100).describe("FBX global scale (default 100 for cm)")
  ```
- **Output payload:** `{ filePath: string, exportedObjects: string[], success: boolean, warnings: string[] }`
- **refs:** `{ filePath }`
- **nextSteps:** `["Import into UE5 as Skeletal Mesh", "Apply MetaHuman animation set if compatible"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `ARMATURE_NOT_FOUND`, `INVALID_SKELETON_HIERARCHY`, `FILE_WRITE_ERROR`
- **Python handler outline:**
  ```python
  def main():
    # Validation checks
    if validateMannequinSkeleton:
      verify_mannequin_hierarchy(armature_obj)
    # Pre-export cleanup
    if triangulate:
      apply_triangulate_modifier(mesh_objs)
    # Set FBX export params per UE-TARGETS §7
    bpy.ops.export_scene.fbx(
      filepath=filePath,
      use_selection=True,
      global_scale=globalScale,
      apply_unit_scale=applyUEScale,
      # ... all other UE params
      add_leaf_bones=False,
      bake_anim=False  # for skeletal mesh, not animation
    )
    bpy.ops.ed.undo_push(...)
    return {"filePath": filePath, "exportedObjects": objectNames, "success": True, "warnings": [...]}
  ```
- **Related tools — upstream:** (all modeling, rigging, shape keys done)
- **Related tools — downstream:** (import in UE5)
- **Test cases:** Export character; import into UE5 standalone; verify skeleton, weights, shape keys; round-trip test
- **Status:** 🟡 Yellow (requires exact bone name validation; Mannequin hierarchy check is brittle; good test coverage needed)

---

## 3. Feasibility Verdict Table

| Step | Verdict | Notes |
|---|---|---|
| 1. Box modeling (cube → humanoid via extrude/scale) | 🟢 **Green** | Full `bmesh` + `bpy.ops.mesh.*` support; deterministic |
| 2. Multires setup | 🟢 **Green** | `MultiresModifier` is data-driven; no modal ops |
| 3. Sculpt mode toggle | 🟢 **Green** | `bpy.ops.sculpt.sculptmode_toggle()` non-modal |
| 4. Freeform sculpt strokes (Draw, Grab, etc.) | 🔴 **Red (Modal)** | Brush strokes are interactive; `brush_stroke()` appears to only work with live UI events. Playback feasibility unclear. |
| 5. Sculpt non-modal ops (filters, remesh, symmetrize) | 🟢 **Green** | `mesh_filter()`, `remesh()`, `symmetrize()` fully deterministic |
| 6. Retopo (Polybuild) | 🔴 **Red (Modal)** | Polybuild is a modal brush; not scriptable deterministically |
| 6. Retopo (Shrinkwrap + manual topology) | 🟡 **Yellow** | Shrinkwrap is non-modal, but manual cage creation requires semi-interactive setup OR external retopo addon |
| 7. Multires bake + shrinkwrap projection | 🟢 **Green** | `MultiresModifier.apply_base()` + `ShrinkwrapModifier` chain is deterministic |
| 8. Shape keys (create, set value, drivers) | 🟢 **Green** | Full coverage via `bpy.types.ShapeKey` data API |
| 9. ARKit 52 blendshapes | 🟢 **Green** | Simple enumeration + `obj.shape_key_add()` per shape |
| 10. Vertex groups (assign, weights) | 🟡 **Yellow** | Assignment via `VertexGroup.add()` is deterministic; manual weight painting is modal |
| 11. UV unwrapping (seams, smart project, pack) | 🟢 **Green** | All via `bpy.ops.uv.*` non-modal operators |
| 12. Triangulate | 🟢 **Green** | Modifier or `bpy.ops.mesh.quads_convert_to_tris()` |
| 13. Export FBX (skeletal mesh + weights + shape keys) | 🟢 **Green** | Full parameter control via `bpy.ops.export_scene.fbx(...)`; UE-TARGETS compliance achievable |

---

## 4. Entity Types Touched

- **Object** → mesh object, armature object, empties
- **Mesh** → geometry, vertices, edges, faces
- **ShapeKey** → basis, relative shape keys, drivers
- **Modifier** → Multires, Shrinkwrap, Triangulate, SubSurf
- **Brush** → sculpt brush parameters
- **VertexGroup** → rigging weights
- **UVMap** → UV layers, islands, seams
- **Material** (passthrough) → slots on mesh
- **Action** (passthrough) → animation for export
- **Armature** (passthrough) → skeleton hierarchy validation

**Chain example:**
```
object_create("Body") 
  → mesh_extrude_faces(...) 
    → modifier_add_multires(...) 
      → sculpt_mode_toggle(...) 
        → sculpt_filter_apply(...) 
          → sculpt_symmetrize(...) 
            → sculpt_mode_toggle(False) 
              → shape_key_create_basis(...) 
                → shape_key_create_arkit_set(...) 
                  → uv_mark_seams(...) 
                    → uv_smart_project(...) 
                      → export_fbx_skeletal_character(...)
```

---

## 5. Open Issues / Questions for User

1. **Sculpt brush stroke playback — CRITICAL** 
   - Does `bpy.ops.sculpt.brush_stroke(stroke=[OperatorStrokeElement, ...])` accept a pre-computed list of screen-space cursor positions and pressures?
   - Or does it only work with live tablet/mouse UI events?
   - **Recommendation:** If blocked, expose only the non-modal sculpt ops (filters, remesh, symmetrize) as tools, and document sculpting as "manual" (user-driven, not agent-driven).

2. **Retopology boundary — MODAL vs NON-MODAL**
   - Polybuild (modal brush) is the standard Blender retopo workflow.
   - Agent cannot drive modal brushes deterministically.
   - **Workaround:** Use Shrinkwrap + manual cage authoring, or recommend agent offloads retopo to external addon (e.g., Instant Meshes, TopoGun via Python subprocess).
   - **Question:** Is retopo a hard blocker, or is Shrinkwrap-based retopo acceptable for v1.0?

3. **Weight painting — PAINT MODE BOUNDARY**
   - `VertexGroup.add([indices], weight)` is deterministic → GREEN.
   - Interactive weight paint (WEIGHT_PAINT mode) is modal → RED.
   - **Question:** For rigging an organic character, is manual weight assignment per-vertex acceptable, or do you need skinning via `bpy.ops.paint.weight_paint(...)` + brush strokes?

4. **Shape key interpolation + ARKit MetaHuman**
   - ARKit 52 set is fully implementable via `shape_key_add()`.
   - Drivers link keys to armature bones (e.g., jaw rotation → mouthOpen blendshape).
   - **Question:** Should the agent also generate FACS (Facial Action Coding System) rigs with RBF solvers, or is ARKit-52 + simple drivers sufficient for v1.0 MetaHuman compatibility?

5. **Headless test mode for sculpt**
   - Sculpt preview requires 3D viewport context.
   - Headless Blender (no UI) can run sculpt operators but cannot render the viewport preview.
   - **Question:** For CI/smoke tests, is it acceptable to run sculpt ops in headless mode without visual verification, or do you need a screenshotter?

6. **Brush stroke recording format**
   - If stroke playback is feasible, what is the input format?
   - Is it `[(x, y, pressure), ...]` in screen space, or world space, or normalized [0,1] space?
   - **Question:** Should tools record and replay strokes as JSON, or accept only real-time UI events?

---

## Next Steps (for Implementation Phase)

1. **Verify sculpt stroke playback** via test: `bpy.ops.sculpt.brush_stroke(stroke=[...])` with pre-built array.
2. **Prototype ARKit-52 setup** tool in a test `.blend` and export to FBX → UE5 → verify Morph Targets import.
3. **Draft retopo tool** using Shrinkwrap; document Polybuild as out-of-scope for v1.0.
4. **Build integration test harness** for character pipeline (box → sculpt → retopo → shape keys → FBX export → UE5 import).

---

**END OF RESEARCH REPORT**

This report covers 22 proposed tools across sculpt, shape keys, retopo (hybrid), UV unwrapping, and export, with feasibility verdicts, error codes, and the two critical open questions about sculpt brush stroke playback and retopo boundaries.