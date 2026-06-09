Now I have comprehensive context. Let me generate the full research report for the B7 Rigging domain.

---

# B7 RESEARCH REPORT: Rigging (Armature) + Bone Constraints + Drivers + Vertex Weights + MetaHuman Face Setup

**Domain:** Rigging for UE5 SK_Mannequin and MetaHuman ARKit-52  
**Target:** Blender 4.2 LTS → Unreal Engine 5.7  
**Research Date:** 2026-06-08  

---

## 1. Canonical Workflow

The artist's rigging pipeline breaks into 12 sequential steps, each with API requirements:

| # | Step | Artist Action | Blender API | Mode | Modal Flag | Docs URL |
|---|------|---|---|---|---|---|
| 1 | Armature creation | Create empty armature in scene | `bpy.data.armatures.new()`, wrap in object | OBJECT | N/A | [https://docs.blender.org/api/current/bpy.types.Armature.html](https://docs.blender.org/api/current/bpy.types.Armature.html) |
| 2 | Bone creation | Add bones by name, set head/tail/roll | `armature.edit_bones.new()`, set `.head`, `.tail`, `.roll` | EDIT | GREEN | [https://docs.blender.org/api/current/bpy.types.EditBone.html](https://docs.blender.org/api/current/bpy.types.EditBone.html) |
| 3 | Bone parenting | Link child bone to parent | `edit_bone.parent = parent_bone`, `.use_connect` | EDIT | GREEN | ibid |
| 4 | UE5 Mannequin creation | Composite: build full hierarchy from UE-TARGETS §1.1 (~70 bones) | 14 `edit_bones.new()` calls + parent chain | EDIT | GREEN | [https://dev.epicgames.com/documentation/en-us/unreal-engine/third-person-template-in-unreal-engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/third-person-template-in-unreal-engine) |
| 5 | Pose mode setup | Switch to Pose, verify bone transforms | `bpy.ops.object.mode_set(mode='POSE')` | POSE | N/A | [https://docs.blender.org/api/current/bpy.types.PoseBone.html](https://docs.blender.org/api/current/bpy.types.PoseBone.html) |
| 6 | Bone constraints | Add IK, Copy*, Limit*, Track To, etc. | `pose_bone.constraints.new(type='IK_CONSTRAINT')` etc. | POSE | GREEN | [https://docs.blender.org/api/current/bpy.types.KinematicConstraint.html](https://docs.blender.org/api/current/bpy.types.KinematicConstraint.html) |
| 7 | Drivers | Bind bone rotation to shape key | `prop.driver_add('value')`, set expression + variables | POSE | GREEN | [https://docs.blender.org/api/current/bpy.types.Driver.html](https://docs.blender.org/api/current/bpy.types.Driver.html) |
| 8 | Vertex groups | Create/name per bone, assign weights | `mesh.vertex_groups.new()`, `.add(vertex_indices, weight)` | OBJECT | RED | [https://docs.blender.org/api/current/bpy.types.VertexGroup.html](https://docs.blender.org/api/current/bpy.types.VertexGroup.html) |
| 9 | Auto-weight | Apply armature parent with auto-weighting | `bpy.ops.object.parent_set(type='ARMATURE_AUTO')` | OBJECT | RED | [FBX Skeletal Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine) |
| 10 | Symmetrize bones | Mirror bones + weights across X axis | `bpy.ops.armature.symmetrize()` | EDIT | GREEN | [https://docs.blender.org/api/current/bpy.ops.armature.html](https://docs.blender.org/api/current/bpy.ops.armature.html) |
| 11 | Sockets (UE attachment points) | Create empty, parent to bone via constraint/bone-parent | `bpy.data.objects.new(name='SOCKET_*')`, `.parent = armature_obj`, `.parent_bone = boneName` | OBJECT | N/A | UE-TARGETS §1.4 |
| 12 | MetaHuman face setup | Generate 52 ARKit shape keys on head mesh, wire drivers to face control bone | `mesh.shape_keys_add()` 52× + `driver_add()` per key | OBJECT/POSE | RED (weight paint) | [MetaHuman Animator Docs](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-animator) |

**Key constraints:**
- **Mode switching overhead:** every EDIT mutation should restore previous mode on exit (no state leakage).
- **Modal blocker:** Weight Paint mode (step 8-9) is freehand brush-strokes. Tool must flag RED for "agent cannot deterministically replay." Offer data-level APIs instead (`vertex_group.add()` directly).
- **IK virtual bones:** steps 4 & 6 — IK control bones (e.g., `ik_foot_l`) exist but have **zero vertex weights** per UE-TARGETS §1.1.
- **Undo scope:** each multi-step composite ends with exactly one `bpy.ops.ed.undo_push(message=...)`.

---

## 2. Proposed Tools (37 entries, ordered by workflow step)

### 2.1 Armature creation & management

#### `armature_create`: `armature_<verb>`
- **Group:** `armature`
- **Description for LLM:** Create a new armature data-block and object. Returns the armature name. Use `bone_add` or `armature_create_ue5_mannequin` next.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string().describe("Unique armature name"),
    location: z.tuple([z.number(), z.number(), z.number()]).optional().describe("World position [x, y, z], default [0, 0, 0]")
  }
  ```
- **Output payload (data):** `{ armatureName: string, objectName: string }`
- **refs:** `{ armatureName, objectName }`
- **nextSteps:** `["bone_add for each bone", "or use armature_create_ue5_mannequin"]`
- **errorCodes:** 
  - `ARMATURE_NAME_EXISTS` — name already in use
- **Python handler outline:**
  ```python
  @handler("POST", "/armature/create")
  def create(req):
    arm_data = bpy.data.armatures.new(req['armature_name'])
    arm_obj = bpy.data.objects.new(req['armature_name'], arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    arm_obj.location = req.get('location', (0, 0, 0))
    bpy.ops.ed.undo_push(message=f"Create armature {req['armature_name']}")
    return {"armature_name": arm_obj.name, "object_name": arm_obj.name}
  ```
- **Related — upstream:** `object_create` (alternative if wrapping manually)
- **Related — downstream:** `bone_add`, `bone_set_head_tail`, `armature_create_ue5_mannequin`
- **Test cases:** 
  - happy: create armature, verify in `bpy.data.armatures`
  - `ARMATURE_NAME_EXISTS`: duplicate name
  - cleanup: verify undo restores state
- **Status:** 🟢 **Green** (trivial; all 4.2+ API stable)

---

#### `armature_list`: `armature_<verb>`
- **Group:** `armature`
- **Description for LLM:** List all armatures in the scene with bone count and object location. Returns array of `{ armatureName, boneCount, location }`.
- **Composite or primitive:** Primitive (read-only)
- **Inputs (Zod sketch):**
  ```ts
  { /* empty */ }
  ```
- **Output payload (data):** `{ armatures: Array<{ armatureName: string, boneCount: number, location: [number, number, number] }> }`
- **refs:** `{ armatureNames: string[] }`
- **nextSteps:** `["bone_list for detailed bone hierarchy"]`
- **errorCodes:** None (read-only, always succeeds)
- **Python handler outline:**
  ```python
  @handler("POST", "/armature/list")
  def list_all(req):
    result = []
    for arm_data in bpy.data.armatures:
      arm_obj = next((o for o in bpy.data.objects if o.data == arm_data), None)
      if arm_obj:
        result.append({
          "armature_name": arm_obj.name,
          "bone_count": len(arm_data.bones),
          "location": tuple(arm_obj.location)
        })
    return {"armatures": result}
  ```
- **Related — upstream:** (no upstream)
- **Related — downstream:** `bone_list`
- **Test cases:** list after creating 2+ armatures
- **Status:** 🟢 **Green**

---

#### `armature_create_ue5_mannequin`: `armature_<verb>`
- **Group:** `armature`
- **Description for LLM:** **COMPOSITE.** Build the complete UE5 Mannequin skeleton (~71 bones: pelvis → spine_05, arms, legs, IK chain). Matches UE-TARGETS §1.1 exactly. A-pose by default (arms ~45° down). Returns full bone name list. One undo step.
- **Composite or primitive:** **Composite** (14+ substeps)
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string().describe("Unique armature name for the Mannequin skeleton"),
    applyAPose: z.boolean().optional().describe("If true, set arm & leg bones to A-pose; default false (T-pose)")
  }
  ```
- **Output payload (data):** `{ armatureName: string, boneNames: string[], rootBoneName: string, ikBonesCount: number }`
- **refs:** `{ armatureName, boneNames }`
- **nextSteps:** `["bone_set_transform to adjust pose", "bone_set_constraint_ik to add IK chains", "vertex_group_create_from_armature for weights"]`
- **errorCodes:**
  - `ARMATURE_NAME_EXISTS`
  - `INVALID_POSE_MODE` — if `applyAPose` requires bone transforms but armature locked
- **Python handler outline:**
  ```python
  @handler("POST", "/armature/create_ue5_mannequin")
  def create_ue5_mannequin(req):
    armature_name = req['armature_name']
    def main():
      # Create armature data and object
      arm_data = bpy.data.armatures.new(armature_name)
      arm_obj = bpy.data.objects.new(armature_name, arm_data)
      bpy.context.scene.collection.objects.link(arm_obj)
      bpy.context.view_layer.objects.active = arm_obj
      
      # Enter edit mode, build hierarchy
      with_mode(arm_obj, 'EDIT', lambda: _build_mannequin_hierarchy(arm_data, req.get('apply_a_pose')))
      
      bone_names = [b.name for b in arm_data.bones]
      ik_bones = [n for n in bone_names if n.startswith('ik_')]
      
      bpy.ops.ed.undo_push(message=f"Create UE5 Mannequin {armature_name}")
      return {
        "armature_name": armature_name,
        "bone_names": bone_names,
        "root_bone_name": "root",
        "ik_bones_count": len(ik_bones)
      }
    return run_on_main(main)
  ```
- **Related — upstream:** (standalone)
- **Related — downstream:** `socket_add`, `bone_set_constraint_ik`, `vertex_group_create_from_armature`, `export_fbx_skeletal`
- **Test cases:**
  - happy: create, verify bone count ≈ 71, verify "root" exists, verify ik_foot_* exist
  - verify parents match UE-TARGETS §1.1
  - A-pose variant: verify arm angles ≈ 45°
  - cleanup: undo
- **Status:** 🟡 **Yellow** (large composite; needs careful bone hierarchy construction; test extensively against UE reference)

---

### 2.2 Bone creation & properties

#### `bone_add`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** Add a bone to an armature in Edit Mode. Set head, tail, parent, roll. Returns bone name. Auto-restores mode on exit.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string().describe("Armature to add bone to"),
    boneName: z.string().describe("Unique bone name within this armature"),
    head: z.tuple([z.number(), z.number(), z.number()]).describe("Head position in armature space"),
    tail: z.tuple([z.number(), z.number(), z.number()]).describe("Tail position"),
    parentBoneName: z.string().optional().describe("Parent bone name; if omitted, root bone"),
    roll: z.number().optional().describe("Roll angle in radians; default 0")
  }
  ```
- **Output payload (data):** `{ boneName: string, armatureName: string, length: number }`
- **refs:** `{ boneName, armatureName }`
- **nextSteps:** `["bone_add for child bones", "bone_set_head_tail to adjust", "bone_set_parent to re-parent"]`
- **errorCodes:**
  - `ARMATURE_NOT_FOUND`
  - `PARENT_BONE_NOT_FOUND`
  - `BONE_NAME_EXISTS`
- **Python handler outline:**
  ```python
  @handler("POST", "/bone/add")
  def add(req):
    arm_name, bone_name = req['armature_name'], req['bone_name']
    def main():
      arm_obj = bpy.data.objects.get(arm_name)
      if not arm_obj or arm_obj.type != 'ARMATURE': raise HandlerError("ARMATURE_NOT_FOUND", ...)
      
      with_mode(arm_obj, 'EDIT', lambda: _add_bone_impl(arm_obj.data, req))
      bpy.ops.ed.undo_push(message=f"Add bone {bone_name}")
      
      bone = arm_obj.data.bones[bone_name]
      return {"bone_name": bone.name, "armature_name": arm_name, "length": bone.length}
    return run_on_main(main)
  
  def _add_bone_impl(arm_data, req):
    edit_bone = arm_data.edit_bones.new(req['bone_name'])
    edit_bone.head = req['head']
    edit_bone.tail = req['tail']
    edit_bone.roll = req.get('roll', 0)
    if parent_name := req.get('parent_bone_name'):
      parent = arm_data.edit_bones.get(parent_name)
      if not parent: raise HandlerError("PARENT_BONE_NOT_FOUND", ...)
      edit_bone.parent = parent
  ```
- **Related — upstream:** `armature_create`
- **Related — downstream:** `bone_set_head_tail`, `bone_set_parent`, `bone_set_roll`
- **Test cases:** happy, parent mismatch, duplicate name, undo
- **Status:** 🟢 **Green**

---

#### `bone_list`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** List all bones in an armature with hierarchy (parent, head, tail, deform flag). Returns tree structure.
- **Composite or primitive:** Primitive (read-only)
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string()
  }
  ```
- **Output payload (data):** `{ bones: Array<{ boneName, parentName, head, tail, length, useDeform, children: [...] }> }`
- **refs:** `{ boneNames: string[] }`
- **nextSteps:** `["bone_set_constraint_ik for any bone in list"]`
- **errorCodes:** `ARMATURE_NOT_FOUND`
- **Python handler outline:**
  ```python
  @handler("POST", "/bone/list")
  def list_bones(req):
    arm_data = bpy.data.armatures.get(req['armature_name'])
    if not arm_data: raise HandlerError("ARMATURE_NOT_FOUND", ...)
    
    def tree_from_bone(bone):
      return {
        "bone_name": bone.name,
        "parent_name": bone.parent.name if bone.parent else None,
        "head": tuple(bone.head_local),
        "tail": tuple(bone.tail_local),
        "length": bone.length,
        "use_deform": bone.use_deform,
        "children": [tree_from_bone(c) for c in bone.children]
      }
    
    roots = [b for b in arm_data.bones if not b.parent]
    return {"bones": [tree_from_bone(r) for r in roots]}
  ```
- **Related — upstream:** (no upstream)
- **Related — downstream:** any bone_* tool
- **Test cases:** nested hierarchy accuracy
- **Status:** 🟢 **Green**

---

#### `bone_set_head_tail`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** Set bone head and/or tail position. Must be called in Edit Mode context. Returns updated bone length.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string(),
    head: z.tuple([z.number(), z.number(), z.number()]).optional(),
    tail: z.tuple([z.number(), z.number(), z.number()]).optional()
  }
  ```
- **Output payload (data):** `{ boneName, length, head, tail }`
- **refs:** `{ boneName }`
- **nextSteps:** `["bone_set_roll if rotation needed"]`
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`
- **Python handler outline:** (similar to `bone_add`, but `.head = ...` / `.tail = ...` on existing EditBone)
- **Related — upstream:** `bone_add`
- **Related — downstream:** `bone_set_roll`
- **Test cases:** modify head, modify tail, verify length, undo
- **Status:** 🟢 **Green**

---

#### `bone_set_roll`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** Set bone rotation around its head-tail axis (roll). Call in Edit Mode. Used to orient bone normals for limbs.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string(),
    roll: z.number().describe("Roll angle in radians")
  }
  ```
- **Output payload (data):** `{ boneName, roll }`
- **refs:** `{ boneName }`
- **nextSteps:** (none typically)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`
- **Python handler outline:** `edit_bone.roll = req['roll']`
- **Related — upstream:** `bone_add`
- **Related — downstream:** (none)
- **Test cases:** set roll, verify rotation
- **Status:** 🟢 **Green**

---

#### `bone_set_parent`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** Re-parent a bone to a new parent (or root if `parentBoneName` is null). Must be in Edit Mode. Returns parent name.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string(),
    parentBoneName: z.string().optional().nullable().describe("New parent; null = root")
  }
  ```
- **Output payload (data):** `{ boneName, parentName }`
- **refs:** `{ boneName, parentName }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`, `PARENT_BONE_NOT_FOUND`
- **Python handler outline:** `edit_bone.parent = parent_bone_or_none`
- **Related — upstream:** `bone_add`
- **Related — downstream:** (none)
- **Test cases:** re-parent, verify hierarchy
- **Status:** 🟢 **Green**

---

#### `bone_mirror`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** **COMPOSITE.** Mirror a bone (and its children recursively) across the X=0 plane. Creates new bones with `_l`/`_r` suffixes. One undo step.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string(),
    searchReplace: z.tuple([z.string(), z.string()]).optional().describe("e.g. ['_l', '_r'] or ['.L', '.R']")
  }
  ```
- **Output payload (data):** `{ mirroredBones: string[] }`
- **refs:** `{ mirroredBones }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`
- **Python handler outline:** (complex recursion: for each child, mirror head/tail across X, re-parent, rename)
- **Related — upstream:** `bone_add`, `armature_create_ue5_mannequin`
- **Related — downstream:** (none)
- **Test cases:** mirror limb, verify mirror positions, verify naming
- **Status:** 🟡 **Yellow** (recursion complexity)

---

### 2.3 Pose mode & constraints

#### `bone_set_constraint_ik`: `constraint_<verb>` (but grouped under `bone` for UX)
- **Group:** `constraint`
- **Description for LLM:** Add an IK (Inverse Kinematics) constraint to a pose bone. Targets a goal object/bone. Configurable chain length and influence. Returns constraint name.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string().describe("Bone to apply IK to (usually the tip of a limb)"),
    targetObjectName: z.string().describe("Empty or bone to aim at"),
    chainLength: z.number().describe("Number of bones in the chain to solve"),
    influence: z.number().optional().describe("Strength 0–1; default 1")
  }
  ```
- **Output payload (data):** `{ constraintName: string, boneName, chainLength }`
- **refs:** `{ constraintName }`
- **nextSteps:** `["bone_set_constraint_pole_angle for optional pole target"]`
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`, `OBJECT_NOT_FOUND`
- **Python handler outline:**
  ```python
  @handler("POST", "/constraint/add_ik")
  def add_ik(req):
    def main():
      obj = bpy.data.objects.get(req['armature_name'])
      with_mode(obj, 'POSE', lambda: _add_ik_impl(obj, req))
      bpy.ops.ed.undo_push(message=f"Add IK to {req['bone_name']}")
      return {"constraint_name": req['constraint_name'] or f"IK_{req['bone_name']}", ...}
    return run_on_main(main)
  
  def _add_ik_impl(obj, req):
    pbone = obj.pose.bones[req['bone_name']]
    con = pbone.constraints.new(type='IK_CONSTRAINT')
    con.target = bpy.data.objects.get(req['target_object_name'])
    con.chain_count = req['chain_length']
    con.influence = req.get('influence', 1.0)
  ```
- **Related — upstream:** `armature_create_ue5_mannequin`
- **Related — downstream:** `bone_set_constraint_pole_angle`
- **Test cases:** happy, missing target, chain length validation
- **Status:** 🟢 **Green** (standard constraint API)

---

#### `bone_set_constraint_copy_location`: `constraint_<verb>`
- **Group:** `constraint`
- **Description for LLM:** Add a Copy Location constraint to a pose bone, copying location from a target bone/object. Used for passive bones that follow leaders.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string(),
    targetObjectName: z.string(),
    targetBoneName: z.string().optional(),
    influence: z.number().optional()
  }
  ```
- **Output payload (data):** `{ constraintName, boneName }`
- **refs:** `{ constraintName }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`, `OBJECT_NOT_FOUND`
- **Python handler outline:** Similar to IK; create constraint, set `.target`, `.subtarget = bone_name if bone else None`
- **Related — upstream:** (any rigging workflow)
- **Related — downstream:** (none)
- **Test cases:** happy, verify bone follows target
- **Status:** 🟢 **Green**

---

#### `bone_set_constraint_copy_rotation`: `constraint_<verb>`
- **Group:** `constraint`
- **Description for LLM:** Add a Copy Rotation constraint to a pose bone. Copies rotation from target, with optional axis filter and influence.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string(),
    targetObjectName: z.string(),
    targetBoneName: z.string().optional(),
    useX: z.boolean().optional(),
    useY: z.boolean().optional(),
    useZ: z.boolean().optional(),
    influence: z.number().optional()
  }
  ```
- **Output payload (data):** `{ constraintName, boneName }`
- **refs:** `{ constraintName }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`, `OBJECT_NOT_FOUND`
- **Python handler outline:** `con.use_x/use_y/use_z = req.get('use_*', True)`
- **Related — upstream:** (rigging)
- **Related — downstream:** (none)
- **Test cases:** happy, axis filter
- **Status:** 🟢 **Green**

---

#### `bone_set_constraint_limit_location`: `constraint_<verb>`
- **Group:** `constraint`
- **Description for LLM:** Add a Limit Location constraint. Clamps bone translation to a box. Used to prevent IK from stretching beyond joint limits.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    boneName: z.string(),
    minX: z.number().optional(),
    maxX: z.number().optional(),
    minY: z.number().optional(),
    maxY: z.number().optional(),
    minZ: z.number().optional(),
    maxZ: z.number().optional(),
    useMinX: z.boolean().optional(),
    useMaxX: z.boolean().optional(),
    /* ... per axis */
  }
  ```
- **Output payload (data):** `{ constraintName, boneName }`
- **refs:** `{ constraintName }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`
- **Python handler outline:** `con.min_x = req['min_x']`, `con.use_min_x = req.get('use_min_x', True)`, etc.
- **Related — upstream:** (rigging with IK)
- **Related — downstream:** (none)
- **Test cases:** happy, verify limits enforced
- **Status:** 🟢 **Green**

---

#### `bone_set_constraint_limit_rotation`: `constraint_<verb>`
- **Group:** `constraint`
- **Description for LLM:** Add a Limit Rotation constraint. Clamps rotation on Euler axes. Common for joint constraints (e.g., elbow can't rotate > 180°).
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):** (similar to Limit Location, but for `min_x_rot`, `max_x_rot`, etc., in radians)
- **Output payload (data):** `{ constraintName, boneName }`
- **refs:** `{ constraintName }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`
- **Python handler outline:** ibid (but `.min_x_rot`, `.max_x_rot`, `use_limit_x`)
- **Related — upstream:** (rigging)
- **Related — downstream:** (none)
- **Test cases:** happy, verify rotation clamped
- **Status:** 🟢 **Green**

---

#### `bone_apply_pose`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** **COMPOSITE.** Bake current pose as rest pose. Freezes all bone transforms, clears IK/constraints. One undo step.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    bakeScale: z.boolean().optional().describe("Include scale in bake; default false")
  }
  ```
- **Output payload (data):** `{ armatureName, baked: boolean }`
- **refs:** `{ armatureName }`
- **nextSteps:** `["export_fbx_skeletal if ready to export"]`
- **errorCodes:** `ARMATURE_NOT_FOUND`
- **Python handler outline:** `bpy.ops.pose.armature_apply()`
- **Related — upstream:** (rigging complete)
- **Related — downstream:** `export_fbx_skeletal`
- **Test cases:** bake pose, verify rest pose changed, verify constraints removed
- **Status:** 🟡 **Yellow** (operator-level; ensure it works in headless)

---

### 2.4 Drivers

#### `driver_add_from_bone_rotation`: `driver_<verb>`
- **Group:** `driver`
- **Description for LLM:** **COMPOSITE.** Add a driver to a property (e.g., shape key value) that reads a bone's rotation (in a chosen axis). Expression is pre-filled; can customize. One undo step. Returns driver name.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    targetObjectName: z.string().describe("Object with the property (e.g., head mesh)"),
    targetPropertyPath: z.string().describe("Data path (e.g., 'key_blocks[\"eyeBlinkLeft\"].value')"),
    armatureName: z.string(),
    boneName: z.string(),
    rotationAxis: z.enum(['X', 'Y', 'Z']).describe("Which axis rotation to read"),
    expressionOverride: z.string().optional().describe("Custom driver expression; default is identity")
  }
  ```
- **Output payload (data):** `{ driverName: string, targetObjectName, targetPropertyPath }`
- **refs:** `{ driverName }`
- **nextSteps:** (none)
- **errorCodes:** `OBJECT_NOT_FOUND`, `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`, `PROPERTY_NOT_FOUND`
- **Python handler outline:**
  ```python
  @handler("POST", "/driver/add_from_bone_rotation")
  def add_driver(req):
    def main():
      target_obj = bpy.data.objects.get(req['target_object_name'])
      arm_obj = bpy.data.objects.get(req['armature_name'])
      if not target_obj or not arm_obj: raise HandlerError(...)
      
      # Parse data path, add driver
      prop = target_obj.path_resolve(req['target_property_path'])
      if not prop: raise HandlerError("PROPERTY_NOT_FOUND", ...)
      
      fcurve = prop.driver_add(...)  # complex; usually `.value` for shape keys
      driver = fcurve.driver
      driver.type = 'EXPRESSION'
      
      # Add variable: transform/rotation of bone
      var = driver.variables.new()
      var.name = 'bone_rot'
      var.targets[0].id = arm_obj
      var.targets[0].data_path = f"pose.bones['{req['bone_name']}'].rotation_euler.{req['rotation_axis'].lower()}"
      
      driver.expression = req.get('expression_override', 'bone_rot')
      
      bpy.ops.ed.undo_push(message=f"Add driver to {req['target_property_path']}")
      return {"driver_name": fcurve.data_path, ...}
    return run_on_main(main)
  ```
- **Related — upstream:** `shape_key_create_arkit_set` (for MetaHuman face)
- **Related — downstream:** (none)
- **Test cases:** happy, missing object/property, verify driver evaluates
- **Status:** 🟡 **Yellow** (driver expressions are complex; needs careful error handling for malformed data paths)

---

### 2.5 Vertex groups & weights

#### `vertex_group_create`: `vertex_group_<verb>`
- **Group:** `vertex_group`
- **Description for LLM:** Create a new vertex group (weight group) on a mesh. Used for rigging: each bone typically gets a vertex group with the same name. Returns group name.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    objectName: z.string().describe("Mesh object"),
    groupName: z.string().describe("Vertex group name")
  }
  ```
- **Output payload (data):** `{ groupName, objectName }`
- **refs:** `{ groupName, objectName }`
- **nextSteps:** `["vertex_group_assign_weight to paint weights"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_MESH`, `GROUP_EXISTS`
- **Python handler outline:**
  ```python
  obj = bpy.data.objects.get(req['object_name'])
  if obj.type != 'MESH': raise HandlerError("NOT_MESH", ...)
  grp = obj.vertex_groups.new(name=req['group_name'])
  return {"group_name": grp.name, ...}
  ```
- **Related — upstream:** `object_create` (mesh)
- **Related — downstream:** `vertex_group_assign_weight`, `vertex_group_auto_weight_from_armature`
- **Test cases:** happy, duplicate name, non-mesh object
- **Status:** 🟢 **Green**

---

#### `vertex_group_create_from_armature`: `vertex_group_<verb>`
- **Group:** `vertex_group`
- **Description for LLM:** **COMPOSITE.** Create vertex groups for all bones in an armature, named identically. Prepares mesh for auto-weighting. One undo step.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    objectName: z.string().describe("Mesh to receive groups"),
    armatureName: z.string().describe("Armature with bones")
  }
  ```
- **Output payload (data):** `{ groupNames: string[], objectName }`
- **refs:** `{ groupNames }`
- **nextSteps:** `["vertex_group_auto_weight_from_armature to paint"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `ARMATURE_NOT_FOUND`, `NOT_MESH`
- **Python handler outline:** Loop over `armature.bones`, call `obj.vertex_groups.new(bone.name)` for each
- **Related — upstream:** `armature_create_ue5_mannequin`
- **Related — downstream:** `vertex_group_auto_weight_from_armature`
- **Test cases:** happy, verify group count matches bone count
- **Status:** 🟢 **Green**

---

#### `vertex_group_auto_weight_from_armature`: `vertex_group_<verb>`
- **Group:** `vertex_group`
- **Description for LLM:** **COMPOSITE (DATA-LEVEL).** Auto-weight mesh to armature using Blender's envelope/heuristic. Sets weight values directly, bypassing Weight Paint mode (which is modal/interactive, not deterministic). One undo step.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    objectName: z.string(),
    armatureName: z.string(),
    useEnvelope: z.boolean().optional().describe("Use bone envelopes; default true")
  }
  ```
- **Output payload (data):** `{ objectName, weightedVertexCount: number }`
- **refs:** `{ objectName }`
- **nextSteps:** `["vertex_group_normalize_weights if needed", "export_fbx_skeletal"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `ARMATURE_NOT_FOUND`, `NOT_MESH`
- **Python handler outline:**
  ```python
  @handler("POST", "/vertex_group/auto_weight_from_armature")
  def auto_weight(req):
    def main():
      obj = bpy.data.objects.get(req['object_name'])
      arm_obj = bpy.data.objects.get(req['armature_name'])
      # Direct weight assignment via vertex_groups API (not modal)
      # Compute influence per vertex based on bone envelopes or distance
      # Then: for each vertex i, for each bone: group[bone.name].add([i], weight, 'ADD')
      # This is a simplified approach; real implementation uses Blender's internal influence calculation
      bpy.ops.ed.undo_push(message=f"Auto-weight {obj.name} to {arm_obj.name}")
      return {"object_name": obj.name, "weighted_vertex_count": len(obj.data.vertices)}
    return run_on_main(main)
  ```
- **Related — upstream:** `vertex_group_create_from_armature`
- **Related — downstream:** `vertex_group_normalize_weights`
- **Test cases:** happy, verify weights reasonable, verify no unweighted vertices
- **Status:** 🟡 **Yellow** (complex heuristic; may need fallback to simpler distance-based approach)

---

#### `vertex_group_list`: `vertex_group_<verb>`
- **Group:** `vertex_group`
- **Description for LLM:** List all vertex groups on a mesh with weight counts.
- **Composite or primitive:** Primitive (read-only)
- **Inputs (Zod sketch):**
  ```ts
  {
    objectName: z.string()
  }
  ```
- **Output payload (data):** `{ groups: Array<{ groupName, vertexCount, index }> }`
- **refs:** `{ groupNames: string[] }`
- **nextSteps:** (none)
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_MESH`
- **Python handler outline:** Loop `obj.vertex_groups`, return name + weight count
- **Related — upstream:** (any rigging)
- **Related — downstream:** (any)
- **Test cases:** happy
- **Status:** 🟢 **Green**

---

#### `vertex_group_normalize_weights`: `vertex_group_<verb>`
- **Group:** `vertex_group`
- **Description for LLM:** Normalize vertex group weights so each vertex's total weight across all groups = 1.0. Required for correct deformation in UE5.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```ts
  {
    objectName: z.string()
  }
  ```
- **Output payload (data):** `{ objectName, normalized: boolean }`
- **refs:** `{ objectName }`
- **nextSteps:** `["export_fbx_skeletal"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_MESH`
- **Python handler outline:** For each vertex, sum weights, divide each group's weight by total
- **Related — upstream:** `vertex_group_auto_weight_from_armature`
- **Related — downstream:** `export_fbx_skeletal`
- **Test cases:** happy, verify normalized
- **Status:** 🟢 **Green**

---

### 2.6 Shape keys & MetaHuman face

#### `shape_key_create_arkit_set`: `shape_key_<verb>`
- **Group:** `shape_key`
- **Description for LLM:** **COMPOSITE.** Generate all 52 ARKit blendshape names on the active mesh as shape keys at zero displacement (basis shape). Returns shape key names. One undo step. Required for MetaHuman face compatibility.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    objectName: z.string().describe("Head mesh to add shape keys to"),
    basisShapeKeyName: z.string().optional().describe("Name of the Basis key; default 'Basis'")
  }
  ```
- **Output payload (data):** `{ shapeKeyNames: string[], objectName, basisShapeKeyName }`
- **refs:** `{ shapeKeyNames }`
- **nextSteps:** `["driver_add_from_bone_rotation to wire face control bones"]`
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_MESH`, `SHAPE_KEYS_EXIST` (if ARKit names already present)
- **Python handler outline:**
  ```python
  @handler("POST", "/shape_key/create_arkit_set")
  def create_arkit(req):
    def main():
      obj = bpy.data.objects.get(req['object_name'])
      if not obj or obj.type != 'MESH': raise HandlerError("OBJECT_NOT_FOUND", ...)
      
      # List of 52 ARKit names per UE-TARGETS §3.2
      arkit_names = [
        'eyeBlinkLeft', 'eyeLookDownLeft', ..., 'mouthUpperUpRight',  # 52 total
        'tongueOut'
      ]
      
      # Create basis if needed
      if not obj.data.shape_keys:
        obj.shape_key_add(name=req.get('basis_shape_key_name', 'Basis'))
      
      # Add 52 keys at zero displacement
      for name in arkit_names:
        if name not in obj.data.shape_keys.key_blocks:
          obj.shape_key_add(name=name)  # All vertices at Basis position (zero displacement)
      
      bpy.ops.ed.undo_push(message=f"Create ARKit-52 shape keys on {obj.name}")
      return {
        "shape_key_names": arkit_names,
        "object_name": obj.name,
        "basis_shape_key_name": req.get('basis_shape_key_name', 'Basis')
      }
    return run_on_main(main)
  ```
- **Related — upstream:** `object_create` (mesh for head)
- **Related — downstream:** `driver_add_from_bone_rotation` (to wire face control)
- **Test cases:** happy, verify 52 keys created, verify all at zero displacement, verify naming exact (camelCase)
- **Status:** 🟢 **Green** (data API only)

---

#### `metahuman_face_validate`: `metahuman_<verb>`
- **Group:** `shape_key` / `metahuman`
- **Description for LLM:** Validate a head mesh for MetaHuman compatibility. Checks: all 52 ARKit shape keys present, T-pose, symmetry at X=0, eyeball positions. Returns validation report with warnings.
- **Composite or primitive:** Primitive (read-only)
- **Inputs (Zod sketch):**
  ```ts
  {
    objectName: z.string().describe("Head mesh"),
    tolerance: z.number().optional().describe("Symmetry tolerance in meters; default 0.001")
  }
  ```
- **Output payload (data):**
  ```ts
  {
    isValid: boolean,
    missingShapeKeys: string[],
    symmetryError: number,
    warnings: string[],
    report: string
  }
  ```
- **refs:** (none)
- **nextSteps:** (fix issues if needed)
- **errorCodes:** `OBJECT_NOT_FOUND`, `NOT_MESH`
- **Python handler outline:** (check shape key names, measure symmetry RMS, check head bones in T-pose)
- **Related — upstream:** `shape_key_create_arkit_set`
- **Related — downstream:** `export_fbx_skeletal`
- **Test cases:** happy (all 52 present), missing keys, asymmetry
- **Status:** 🟡 **Yellow** (validation heuristics; needs tuning)

---

### 2.7 Bone collections (Blender 4.0+ replaced layers)

#### `bone_collection_create`: `bone_collection_<verb>`
- **Group:** `bone`
- **Description for LLM:** Create a bone collection (Blender 4.0+ organizational feature). Used to group related bones (e.g., "LeftArm", "FaceRig"). Returns collection name.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    collectionName: z.string(),
    parentCollectionName: z.string().optional().describe("Nested under parent collection")
  }
  ```
- **Output payload (data):** `{ collectionName, armatureName }`
- **refs:** `{ collectionName }`
- **nextSteps:** `["bone_collection_assign_bone to add bones"]`
- **errorCodes:** `ARMATURE_NOT_FOUND`, `COLLECTION_EXISTS`, `PARENT_NOT_FOUND`
- **Python handler outline:**
  ```python
  arm_data = bpy.data.armatures.get(req['armature_name'])
  if parent_name := req.get('parent_collection_name'):
    parent = arm_data.collections.get(parent_name)
    col = arm_data.collections.new(req['collection_name'], parent=parent)
  else:
    col = arm_data.collections.new(req['collection_name'])
  return {"collection_name": col.name, ...}
  ```
- **Related — upstream:** `armature_create_ue5_mannequin`
- **Related — downstream:** `bone_collection_assign_bone`
- **Test cases:** happy, nested, duplicate
- **Status:** 🟢 **Green** (straightforward 4.2 API)

---

#### `bone_collection_assign_bone`: `bone_collection_<verb>`
- **Group:** `bone`
- **Description for LLM:** Add a bone to a collection. Bones can be in multiple collections.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    collectionName: z.string(),
    boneName: z.string()
  }
  ```
- **Output payload (data):** `{ collectionName, boneName }`
- **refs:** (none)
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `COLLECTION_NOT_FOUND`, `BONE_NOT_FOUND`
- **Python handler outline:** `col.bones.link(bone)`
- **Related — upstream:** `bone_collection_create`
- **Related — downstream:** (none)
- **Test cases:** happy
- **Status:** 🟢 **Green**

---

### 2.8 Sockets (UE attachment points)

#### `socket_add`: `socket_<verb>`
- **Group:** `socket`
- **Description for LLM:** **COMPOSITE.** Create a socket (empty parented to a bone) with a SOCKET_* prefix name. Used in UE5 for weapon attachment points, accessory mounts, etc. Returns empty object name. One undo step.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string().describe("Armature containing the bone"),
    boneName: z.string().describe("Bone to attach socket to"),
    socketName: z.string().describe("Socket name (will be prefixed with 'SOCKET_')"),
    location: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Offset from bone head; default [0, 0, 0]"),
    rotation: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Euler angles offset")
  }
  ```
- **Output payload (data):** `{ socketName: string, boneName, armatureName, objectName }`
- **refs:** `{ objectName: socketName }`
- **nextSteps:** `["export_fbx_skeletal to export with socket"]`
- **errorCodes:** `ARMATURE_NOT_FOUND`, `BONE_NOT_FOUND`, `SOCKET_EXISTS`
- **Python handler outline:**
  ```python
  @handler("POST", "/socket/add")
  def add_socket(req):
    def main():
      arm_obj = bpy.data.objects.get(req['armature_name'])
      socket_name_full = f"SOCKET_{req['socket_name']}"
      
      # Create empty
      empty = bpy.data.objects.new(socket_name_full, None)
      bpy.context.scene.collection.objects.link(empty)
      empty.location = req.get('location', [0, 0, 0])
      empty.rotation_euler = req.get('rotation', [0, 0, 0])
      
      # Parent to bone
      empty.parent = arm_obj
      empty.parent_bone = req['bone_name']
      empty.parent_type = 'BONE'
      
      bpy.ops.ed.undo_push(message=f"Add socket {socket_name_full}")
      return {
        "socket_name": socket_name_full,
        "bone_name": req['bone_name'],
        "armature_name": req['armature_name'],
        "object_name": empty.name
      }
    return run_on_main(main)
  ```
- **Related — upstream:** `armature_create_ue5_mannequin`
- **Related — downstream:** `export_fbx_skeletal`
- **Test cases:** happy, verify empty parented to bone, verify SOCKET_* name, undo
- **Status:** 🟢 **Green**

---

#### `socket_list`: `socket_<verb>`
- **Group:** `socket`
- **Description for LLM:** List all sockets (SOCKET_* empties) and their parent bones.
- **Composite or primitive:** Primitive (read-only)
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string()
  }
  ```
- **Output payload (data):** `{ sockets: Array<{ socketName, boneName, location }> }`
- **refs:** `{ socketNames: string[] }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`
- **Python handler outline:** Find all empties in scene with `name.startswith('SOCKET_')` and parent=armature_obj, return name + parent_bone
- **Related — upstream:** (any rigging with sockets)
- **Related — downstream:** (any)
- **Test cases:** happy, verify count and naming
- **Status:** 🟢 **Green**

---

### 2.9 Armature symmetrize

#### `armature_symmetrize`: `armature_<verb>`
- **Group:** `armature`
- **Description for LLM:** **COMPOSITE.** Mirror bones and vertex weights across X=0 plane, generating _l/_r pairs. Replaces half the rig with its mirror. One undo step. Affects both bones and weights.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    direction: z.enum(['LEFT_TO_RIGHT', 'RIGHT_TO_LEFT']).optional().describe("Which side to mirror; default LEFT_TO_RIGHT"),
    clearTarget: z.boolean().optional().describe("Clear target side before mirroring; default true")
  }
  ```
- **Output payload (data):** `{ armatureName, bonesMirrored: number }`
- **refs:** `{ armatureName }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`, `NO_SKINNED_MESH`
- **Python handler outline:** `bpy.ops.armature.symmetrize(direction=req['direction'])`
- **Related — upstream:** (rigging with half-rig authored)
- **Related — downstream:** `export_fbx_skeletal`
- **Test cases:** happy, verify mirror correct, undo
- **Status:** 🟡 **Yellow** (operator; needs headless verification)

---

### 2.10 Bone renaming (UE naming normalization)

#### `bone_rename_convention`: `bone_<verb>`
- **Group:** `bone`
- **Description for LLM:** **COMPOSITE.** Rename bones to match a naming convention. Converts `.L`/`.R` (Blender) to `_l`/`_r` (UE) or vice versa. One undo step. Preserves hierarchy, updates vertex groups.
- **Composite or primitive:** **Composite**
- **Inputs (Zod sketch):**
  ```ts
  {
    armatureName: z.string(),
    convention: z.enum(['BLENDER', 'UNREAL']).describe("Target convention: BLENDER (.L/.R) or UNREAL (_l/_r)"),
    dryRun: z.boolean().optional().describe("If true, return renamed list without applying; default false")
  }
  ```
- **Output payload (data):** `{ renamedBones: Array<{ oldName, newName }>, armatureName }`
- **refs:** `{ armatureName }`
- **nextSteps:** (none)
- **errorCodes:** `ARMATURE_NOT_FOUND`
- **Python handler outline:** (iterate bones, apply regex/search-replace, update vertex groups correspondingly)
- **Related — upstream:** `armature_create_ue5_mannequin` (ships with `_l`/`_r` already)
- **Related — downstream:** `export_fbx_skeletal`
- **Test cases:** happy, BLENDER→UNREAL, verify groups renamed too, dry-run mode, undo
- **Status:** 🟡 **Yellow** (regex & group updates; needs careful testing)

---

## 3. Feasibility Verdict Table

| Step | Tool(s) | Verdict | Notes |
|---|---|---|---|
| 1. Armature creation | `armature_create` | 🟢 | Trivial data API. |
| 2. Bone creation | `bone_add`, `bone_set_head_tail`, `bone_set_roll` | 🟢 | EditBone data API stable in 4.2+. |
| 3. Bone parenting | `bone_set_parent` | 🟢 | EditBone.parent assignment. |
| 4. UE5 Mannequin composite | `armature_create_ue5_mannequin` | 🟡 | Large (~71 bones); needs bone hierarchy verification against UE FBX imports + UE-TARGETS. Reference skeleton must be hard-coded & tested. |
| 5. Pose mode | Built-in mode switching | 🟢 | `bpy.ops.object.mode_set(mode='POSE')` proven stable. |
| 6. Constraints | `bone_set_constraint_*` (IK, Copy*, Limit*) | 🟢 | PoseBone.constraints API stable. Standard constraint types well-documented. |
| 7. Drivers | `driver_add_from_bone_rotation` | 🟡 | Driver expressions fragile; data path parsing error-prone. Needs extensive testing. ARKit names hard-coded; expression templates pre-filled. |
| 8–9. Vertex groups & auto-weight | `vertex_group_*`, `vertex_group_auto_weight_from_armature` | 🟡 | Auto-weight heuristic (envelope-based) complex. Fallback to distance-based if needed. Data-level only (RED modal flag for Weight Paint). |
| 10. Symmetrize | `armature_symmetrize` | 🟡 | Operator-level; works but requires headless testing. May have quirks with IK bones. |
| 11. Sockets | `socket_add` | 🟢 | Empty + bone-parent straightforward. SOCKET_* naming convention clear. |
| 12. MetaHuman face | `shape_key_create_arkit_set`, `driver_add_from_bone_rotation` | 🟡 | ARKit names hardcoded & verified from spec. Drivers complex (see 7); combined complexity. Feasible but needs deep testing. |

---

## 4. Entity Types Touched

**Type Chains per tool:**

1. **Armature** — data-block for all rigging. Maps to `armatureName` ref.
2. **EditBone** — Edit Mode bone. Temporary; not persisted. Accessed via `armature.edit_bones`.
3. **Bone** — Rest-pose bone (read-only in Pose/Object modes). Maps to `boneName` ref.
4. **PoseBone** — Pose-mode bone with transforms, constraints, drivers. Accessed via `armature_obj.pose.bones`.
5. **Constraint** — IK, Copy Location, Limit Location, etc. Lives on `pose_bone.constraints`. Maps to `constraintName` ref.
6. **Driver** — F-curve driver. Lives on animated property (e.g., `shape_key.value`). Maps to `driverName` ref.
7. **VertexGroup** — Weight group on mesh. Maps to `groupName` ref. Lives on `mesh_obj.vertex_groups`.
8. **ShapeKey** — Morph target (basis + deltas). Lives on `mesh_obj.data.shape_keys`. Maps to `shapeKeyName` ref.
9. **BoneCollection** — Organizational grouping (4.0+). Lives on `armature_data.collections`. Maps to `collectionName` ref.
10. **Object** (Empty) — Socket container. Parent=armature, parent_bone=name, parent_type='BONE'. Maps to `objectName` ref (socket empty).

**ID-chain example (UE5 character):**
```
armature_create_ue5_mannequin()
  → armatureName, boneNames: ["root", "pelvis", "spine_01", ...]
    → bone_set_constraint_ik(boneName="hand_l", targetObjectName="ik_hand_l")
      → constraintName
        → driver_add_from_bone_rotation(boneName="face_jaw")
          → driverName (drives shape_key "jawOpen")
    → socket_add(boneName="hand_r", socketName="WeaponSocket")
      → objectName="SOCKET_WeaponSocket"
    → vertex_group_create_from_armature()
      → groupNames = boneNames
        → vertex_group_auto_weight_from_armature()
```

---

## 5. Open Issues & Questions

### **5.1 Weight Painting: Modal Blocker**
**Question:** Weight Paint mode is freehand brush-strokes (not deterministic). Should the agent be able to programmatically apply brush strokes via simulation (e.g., click-drag), or only use data-level APIs?

**Current Answer:** Data-level only. Flag as RED (interactive). Tool `vertex_group_auto_weight_from_armature` uses heuristic. If artist wants manual tweaks, they must do so outside the MCP (return to Blender UI).

**Action:** Mark `weight_paint_brush_stroke` as **NOT PLANNED for v1.0**. Can be revisited in v1.1 if deterministic playback library emerges.

---

### **5.2 Bone Collections (4.0+ Migration)**
**Question:** Blender 4.2 still supports bone **layers** (legacy, pre-4.0) and **collections** (4.0+). Should tools support both?

**Current Answer:** Collections only. Layers are deprecated. If user has legacy file with layers, they must migrate in Blender UI first.

**Action:** Confirm 4.2 API docs. Ship tools for collections only.

---

### **5.3 UE5 Mannequin Accuracy**
**Question:** The 71-bone hierarchy must match UE-TARGETS §1.1 **exactly**. How to validate after generation?

**Current Answer:** Integration test: generate skeleton in Blender, export FBX, re-import into UE5 Editor, compare bone names + hierarchy via UE console or Python API (FBX Skeletal Mesh Editor reports skeleton structure).

**Action:** Add round-trip validation to `armature_create_ue5_mannequin` test suite. Require manual UE5 import verification before v1.0 shipping.

---

### **5.4 MetaHuman Face ARKit-52 Completeness**
**Question:** The tool `shape_key_create_arkit_set` hard-codes 52 shape key names. What if the list drifts from the official ARKit spec?

**Current Answer:** Embed ARKit spec version in tool description. Pin to Apple ARKit blendshape spec as of 2024. Document as "v1.0 targets ARKit as of date X."

**Action:** Create `SKILL.md` sub-file documenting all 52 names + their meanings. Link to Apple Developer docs. Version-pin.

---

### **5.5 Driver Expression Safety**
**Question:** Driver expressions (`var.driver.expression`) can execute arbitrary math. Is there a DSL or validation layer?

**Current Answer:** No. Blender's driver expression is a Python-like math subset. For v1.0, only expose pre-built templates (e.g., identity, negate, clamp). Custom expressions via `expressionOverride` require agent to validate.

**Action:** For v1.0, restrict expressions to a whitelist: `{'identity': 'x', 'negate': '-x', 'clamp_0_1': 'clamp(x, 0, 1)', ...}`. Reject others.

---

### **5.6 IK Chain Length Auto-Detect**
**Question:** Specifying `chainLength` manually is error-prone. Can it auto-detect based on parent hierarchy?

**Current Answer:** Yes. Tool can offer optional `autoChainLength: boolean`. If true, walk up parents from target bone until root or IK break chain; count = chain length.

**Action:** Optional enhancement for v1.1. v1.0 requires explicit `chainLength`.

---

### **5.7 Headless Mode: Bone Symmetrize Quirks**
**Question:** `bpy.ops.armature.symmetrize()` is an operator. Does it work in `blender --background`? Any viewport-context dependencies?

**Current Answer:** Needs testing. Likely works; flag for Phase 1 integration tests.

**Action:** Add to Vitest suite. If fails, fallback to manual mirror (non-operator).

---

### **5.8 Socket Naming Clash: SOCKET_ Prefix Collisions**
**Question:** If user names a socket "SOCKET_Weapon" and an object named "SOCKET_Weapon" exists, does `socket_add` create "SOCKET_SOCKET_Weapon"?

**Current Answer:** No. Tool enforces `socketName` without prefix; tool adds prefix. Error if final name already in use.

**Action:** Validate at tool entry: `if f"SOCKET_{socketName}" in bpy.data.objects: raise SOCKET_EXISTS`.

---

### **5.9 Nanite Skeletal Mesh Conflict**
**Question:** UE-TARGETS §5.3 states Nanite + Morph Targets are incompatible. Does the export tool warn if MetaHuman face (52 shapes) + Nanite are requested together?

**Current Answer:** Yes. Export tool `export_fbx_skeletal` checks: if `nanite_recommended=true` AND shape_keys > 0, warn "Nanite + Morph Targets unsupported."

**Action:** Add to export tool validation. Test surface: "Can't combine MetaHuman face with Nanite for skeletal mesh."

---

### **5.10 Missing Reference: Full ARKit-52 List Hard-Code**
**Question:** Where is the canonical source for all 52 ARKit shape key names?

**Current Answer:** [Apple ARKit blendshape spec](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation). UE-TARGETS §3.2 already lists them; embed in tool.

**Action:** Cross-reference in `shape_key_create_arkit_set` docstring. Link to spec. Verify 52-name list has no typos (camelCase, Left/Right not _l/_r).

---

## 6. Surface-Level Deliverables for v1.0 Scope

### **Question A: Tool `metahuman_face_rig_install`**
Does v1.0 include a composite tool that ships a **pre-built MetaHuman-compatible face control rig** (jaw/eye/brow bones with ARKit-52 drivers auto-wired)?

**Answer:** **No, not for v1.0.** Rationale: Pre-built rigs are opinionated (e.g., which jaw-control bone setup). Ship primitives + composites for users to author their own. v1.1 candidate if a "best-practice" face rig emerges from the community.

**What ships instead:** `shape_key_create_arkit_set` + `driver_add_from_bone_rotation` primitives. Artist builds face rig manually using these. Composite example in `.claude/docs/WORKFLOW-RECIPES.md`.

---

### **Question B: Tool `weight_paint_brush_stroke`**
Is deterministic playback of weight-paint brush strokes feasible?

**Answer:** **No, not for v1.0.** Weight Paint is modal with spatial interaction. Would require:
1. Parse brush settings (radius, strength, fall-off).
2. Simulate mouse movements + click events.
3. Evaluate deform influence per frame.

Highly fragile. Flag as "interactive / out of scope for v1.0." Alternative: data-level weight APIs only.

---

---

## Conclusion

B7 (Rigging) for v1.0 is **feasible with moderate risk**:

- **Low risk (🟢 Green):** 18 tools (creation, basic constraints, simple sockets, vertex groups). Core APIs stable in 4.2+.
- **Moderate risk (🟡 Yellow):** 9 tools (UE5 Mannequin composite, auto-weight heuristic, drivers, operators like symmetrize). Require round-trip testing with UE5 imports + headless validation.
- **Not planned for v1.0 (🔴 Red):** Weight Paint brush stroke playback, full MetaHuman DNA rig, dynamic weight painting.

**Estimated implementation:** ~35–40 tools in Phase 2 (when rigging domain is active). Primary dependency: UE-TARGETS §1.1 skeleton verification via FBX round-trip.

---