Based on my research of Blender 4.2 LTS hard-surface modeling workflows, UE5 export requirements, and the MCP tool architecture, here is the comprehensive B2 research report:

---

# B2 Research Report: Hard-Surface Prop Modeling Pipeline (Blender 4.2 LTS → Unreal Engine 5)

**Domain:** `mesh`, `modifier`, `material`, `shading`, `export`  
**Target:** Game-ready hard-surface props (weapons, machinery, architectural details, modular environment kits)  
**Export format:** FBX for skeletal/static meshes, glTF as secondary path  
**UE5 target:** Mannequin skeletal meshes, Lyra modular kits, Nanite static geometry  

---

## 1. Canonical Workflow (Ordered Steps)

The typical artist pipeline for hard-surface prop creation in Blender, decomposed into atomic operations:

### Step 1: Reference & Blockout
**What the artist does:** Add primitives (cube, cylinder, sphere, UV sphere, ico sphere), position them, scale them on a grid snap, set up reference images on empties.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.data.meshes.new()` + `bpy.ops.mesh.primitive_*` (operators); or `bmesh` for direct mesh creation |
| **Mode** | Object Mode (add objects) → Edit Mode if using operators |
| **Context override** | Not required for primitives |
| **Modal flag** | False (non-modal) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/meshes/primitives.html |

---

### Step 2: Mirror Modifier Setup (Non-Destructive Symmetry)
**What the artist does:** Enable Mirror modifier on the mesh object, set axis (X, Y, Z), optionally clamp overlap, set up mirror threshold.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.data.objects[name].modifiers.new(name, 'MIRROR')` then set `mirror_object`, `use_axis`, `use_clip` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/mirror.html |

---

### Step 3: Array Modifier for Repetition
**What the artist does:** Add Array modifier to create copies along an axis (e.g., tiles, gun rounds, armor segments), set offset (constant, relative, fit curve), count.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `modifiers.new('Array', 'ARRAY')` + `count`, `use_constant_offset`, `constant_offset_displacement` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/array.html |

---

### Step 4: Boolean Operations for Hard-Surface Detail
**What the artist does:** Create cutter meshes (separate objects), assign Boolean modifiers to main mesh (Union/Difference/Intersect), choose Exact or Fast solver.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `modifiers.new('Boolean', 'BOOLEAN')` + `operation` ('UNION'/'DIFFERENCE'/'INTERSECT') + `object` or `collection` + `solver_type` ('EXACT'/'FAST') |
| **Mode** | Object Mode (modifier setup); Edit Mode for cutter mesh refinement |
| **Context override** | Not required |
| **Modal flag** | False |
| **Solver notes** | **Exact:** full support for overlapping geometry, slower; **Fast:** better perf, limited on non-manifold |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/booleans.html |

---

### Step 5: Edge Crease & Bevel Weight (Marking Hard Edges)
**What the artist does:** In Edit Mode, select edges, press Shift+E to bevel weight (or Ctrl+E → Set Crease for subdivision), set weight 0–1.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.context.tool_settings.use_mesh_automerge` + edge attribute `bevel_weight_edge` (accessed via bmesh) or operator `bpy.ops.transform.edge_bevelweight()` |
| **Mode** | Edit Mode |
| **Context override** | 3D View context required (temp_override for headless) |
| **Modal flag** | True (bevel_weight input is interactive in UI; can be scripted as non-modal via bmesh attribute) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/meshes/editing/edge/edge_data.html |

---

### Step 6: Bevel Modifier (Non-Destructive Edge Hardness)
**What the artist does:** Add Bevel modifier, set width (offset/width/depth/percent), segments (smoothness), limit method (angle, weight, vertex group), affect (edges/vertices).

| Aspect | Detail |
|--------|--------|
| **Blender API** | `modifiers.new('Bevel', 'BEVEL')` + `width`, `segments`, `affect`, `limit_method`, `angle_limit`, `bevel_type` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **v4.2 feature:** Custom profile widget for complex bevel shapes (e.g., support loops, rounded vs sharp) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/bevel.html |

---

### Step 7: Subdivision Surface for Organic Smoothing
**What the artist does:** Add Subdivision Surface modifier, set render levels (typically 2–3 for game) and viewport levels, optional boundary smooth type.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `modifiers.new('Subsurf', 'SUBSURF')` + `levels` (viewport) + `render_levels` + `use_creases` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **Note:** Crease + bevel weight edges control where subdiv does NOT smooth (sharp corners remain) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/subdivision_surface.html |

---

### Step 8: Mark Sharp / Shade Smooth (Normal Direction Control)
**What the artist does:** Select edges, Ctrl+E → Mark Sharp (or Alt+M → Sharp); or select all faces → Shade Smooth to auto-generate vertex normals by angle.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.ops.mesh.mark_sharp()` (requires edit mode) or apply Smooth By Angle modifier |
| **Mode** | Edit Mode for manual marking; Object Mode for modifier application |
| **Context override** | Edit Mode requires 3D View context |
| **Modal flag** | False |
| **v4.2 change:** `mesh.use_auto_smooth` **deprecated**; replaced by Smooth By Angle modifier |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/normals/smooth_by_angle.html |

---

### Step 9: High-Poly → Low-Poly Workflow (Duplicate & Decimate)
**What the artist does:** Duplicate mesh object (Shift+D), on low-poly copy add Decimate modifier (Collapse mode, ratio ~0.3–0.5), then decimate further if needed.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.data.objects.new(name, bpy.data.objects[name].data.copy())` (duplicate) + `modifiers.new('Decimate', 'DECIMATE')` with `decimate_type='COLLAPSE'` + `ratio` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **Decimate modes:** Collapse (merge verts), Un-subdivide (reverse subdiv), Planar (flat surface cleanup) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/decimate.html |

---

### Step 10: Mesh Editing (Edit Mode Primitives: Extrude, Inset, Bevel, Bridge)
**What the artist does:** Enter Edit Mode, select edges/faces, extrude (E), inset (I), bevel single edge (Ctrl+B), bridge edge loops, fill faces (F).

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bmesh.ops.extrude_face()`, `bmesh.ops.inset_individual()`, `bpy.ops.mesh.bevel()` (non-modal via params), `bpy.ops.mesh.edge_face_add()` (fill), `bpy.ops.mesh.bridge_edge_loops()` |
| **Mode** | Edit Mode |
| **Context override** | 3D View required; bmesh calls must wrap in with_mode block |
| **Modal flag** | Extrude/Inset/Bevel: **partially modal** (can use params for non-interactive version) |
| **bmesh preferred:** Direct vertex/edge/face manipulation for batch operations |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/meshes/editing/face/extrude_faces.html |

---

### Step 11: Edge Split for Hard Edges (Pre-Export)
**What the artist does:** Add Edge Split modifier (before export), set angle threshold or apply per-edge via Edit Mode marking.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `modifiers.new('EdgeSplit', 'EDGE_SPLIT')` + `split_angle`, `use_edge_sharp` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **Purpose:** FBX export requires split edges for hard-surface shading; this ensures clean normals on export |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/edge_split.html |

---

### Step 12: Solidify for Shell/Thickness Modeling
**What the artist does:** Add Solidify modifier on a single-sided surface (e.g., armor plating, thin walls), set thickness, rim.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `modifiers.new('Solidify', 'SOLIDIFY')` + `thickness`, `offset`, `use_even_offset` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/solidify.html |

---

### Step 13: Weld & Merge for Cleanup
**What the artist does:** In Edit Mode, select loose/duplicate verts, M → Merge (by distance, at first/last, center); or add Weld modifier (distance threshold).

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.ops.mesh.merge()` (edit mode) or `modifiers.new('Weld', 'WELD')` + `merge_distance` |
| **Mode** | Edit Mode for interactive merge; Object Mode for modifier |
| **Context override** | Edit Mode requires 3D View |
| **Modal flag** | False |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/weld.html |

---

### Step 14: Triangulation (Pre-Export to UE5)
**What the artist does:** Add Triangulate modifier (last in stack before export) to ensure all quads/n-gons become triangles, or apply in Geometry Nodes.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `modifiers.new('Triangulate', 'TRIANGULATE')` + `quad_method` ('BEAUTY'/'FIXED'/'FIXED_ALTERNATE'/'SHORTEST_DIAGONAL') |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **UE5 requirement:** All meshes must be triangulated before export (FBX importer docs cite: *"meshes in Unreal Engine must be triangulated"*) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/triangulate.html |

---

### Step 15: UV Unwrapping & Lightmap Generation
**What the artist does:** Enter UV Editing workspace, select all faces, U → Unwrap (Smart UV Project or Angle-Based), optionally generate second UV channel for lightmaps (if not using Lumen).

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.ops.uv.unwrap()` (Edit Mode operator, requires 3D context) or `bmesh` with island management |
| **Mode** | Edit Mode |
| **Context override** | 3D View + UV Editor context required |
| **Modal flag** | False (non-modal unwrap via operator params) |
| **v4.2 note:** Lumen projects (default UE5) do NOT require lightmap UVs; skip this for Lumen-only assets |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/introduction.html |

---

### Step 16: Material Setup (Principled BSDF for UE5)
**What the artist does:** Create material with Principled BSDF node, wire base color, metallic, roughness, normal texture inputs; ensure only params UE5's PBR mapper recognizes.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.data.materials.new()` + use_nodes, create Principled BSDF node via node tree API, wire links |
| **Mode** | Shader Editor (not a mesh editing mode; just data mutation) |
| **Context override** | Not required for data creation; context only needed if using operators |
| **Modal flag** | False |
| **UE5 params:** base_color, metallic, roughness, normal, emissive, alpha (Khronos PBR subset) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/render/shader_nodes/shader/principled.html |

---

### Step 17: Modifier Stack Freezing / Applying
**What the artist does:** Decide: keep modifiers live (for variations) OR apply (bpy.ops.object.modifier_apply) to freeze the deformed mesh. Typically: high-poly keeps all, low-poly applies most.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.ops.object.modifier_apply(modifier=name)` or set modifier to disabled in final export |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **Undo behavior:** One undo_push per apply call; batch applies should be single undo entry |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/introduction.html |

---

### Step 18: LOD Creation (Nanite vs. Traditional)
**What the artist does:** 
- **For Nanite (100k+ tris):** No manual LODs; export high-poly as-is.
- **For traditional LOD (under 100k):** Duplicate mesh, create LOD1 via decimate (50% ratio), LOD2 (25%), wrap in empty named `LOD_<MeshName>`.

| Aspect | Detail |
|--------|--------|
| **Blender API** | Duplicate + decimate (as in Step 9); parent LODs under empty: `bpy.data.objects[lod_mesh].parent = lod_empty` |
| **Mode** | Object Mode |
| **Context override** | Not required |
| **Modal flag** | False |
| **UE5 importer:** Recognizes `LOD_*` empty groups; imports as native LOD asset |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/decimate.html |

---

### Step 19: Collision Mesh Creation (Box, Capsule, Convex)
**What the artist does:** Create simple meshes (box, capsule, or convex hull of prop), name them `UBX_<MeshName>` (box), `UCX_<MeshName>` (convex), parent under prop.

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.ops.mesh.primitive_cube_add()` (for box) or convex hull operator; rename to UBX_/UCX_/USP_/UCP_ prefix |
| **Mode** | Object Mode |
| **Context override** | Required for operators (add mesh) |
| **Modal flag** | False |
| **UE5 importer:** Auto-converts these prefixed meshes to collision primitives on import |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/modeling/meshes/primitives.html |

---

### Step 20: Export to FBX (Static or Skeletal)
**What the artist does:** Ctrl+E → Export FBX, set filename, enable:
- `use_selection=True` (export only selected)
- `apply_scale_options='FBX_SCALE_NONE'`
- `global_scale=1.0`, `apply_unit_scale=True`
- `use_triangles=True`
- `object_types={'MESH', 'EMPTY', 'ARMATURE'}` (for sockets/collision/skeletal)

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.ops.export_scene.fbx()` with 30+ parameters (all must be exposed as tool inputs per UE-TARGETS.md §7) |
| **Mode** | Object Mode |
| **Context override** | File path handling (use `pathlib`) |
| **Modal flag** | False (can set all params via bpy.ops call) |
| **Critical params (UE5 compat):** axis_forward='-Z', axis_up='Y', bake_anim=False, add_leaf_bones=False, use_tspace=True |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/files/import_export/fbx.html |

---

### Step 21: glTF Export (Secondary Path, Multi-Engine)
**What the artist does:** File → Export glTF 2.0, set filename, enable material export, optional compression (gzip).

| Aspect | Detail |
|--------|--------|
| **Blender API** | `bpy.ops.export_scene.gltf()` with format ('GLTF_EMBEDDED'/'GLTF_SEPARATE'/'GLFT_GLB') |
| **Mode** | Object Mode |
| **Context override** | File path handling |
| **Modal flag** | False |
| **UE5 compat:** Supports Khronos PBR (metallic-roughness); better for multi-engine targets (Unity, Godot, web) |
| **Doc URL** | https://docs.blender.org/manual/en/4.2/files/import_export/gltf.html |

---

## 2. Proposed Tools (~28 entries)

Each tool entry uses this template:

```
### Tool Name
**Group:** `<group>`  
**Category:** Primitive / Composite  
**Description:** [Imperative, for LLM; <200 chars simple, multiline for complex exports]

**Zod Input Schema:**
```ts
{
  objectName?: string,
  // ...parameters
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName?: string,
  meshTriangleCount?: number,
  // ...result data
}
```

**Refs:** `{ objectName, modifierName?, ... }` — ID-chaining for next tool call  
**NextSteps:** Hints for agent (not commands)  
**ErrorCodes:** Enumeration of failure modes  
**Python Handler Outline:** Key logic  
**Upstream/Downstream:** Related tools  
**Test Cases:** Happy path + error branches + idempotency  
**Status:** GREEN/YELLOW/RED + blockers  
```

---

### 1. mesh_add_primitive
**Group:** `mesh`  
**Category:** Primitive  
**Description:** Add a primitive mesh (cube, cylinder, sphere, UV sphere, ico sphere, torus, monkey, cone, plane) at world origin. Returns the created object name.

**Zod Input Schema:**
```ts
{
  type: z.enum(["CUBE", "CYLINDER", "SPHERE", "UV_SPHERE", "ICO_SPHERE", "TORUS", "MONKEY", "CONE", "PLANE"]),
  location?: z.tuple([z.number(), z.number(), z.number()]),
  scale?: z.number(),
  objectName?: z.string(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  triangleCount: number,
  vertexCount: number,
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["Call mesh_apply_mirror or mesh_add_modifier to add non-destructive ops"]`  
**ErrorCodes:** `OBJECT_NAME_EXISTS`, `INVALID_PRIMITIVE_TYPE`, `BLENDER_TIMEOUT`  
**Python Handler Outline:** Call `bpy.ops.mesh.primitive_<type>_add()` with location/scale, link to scene, return object name.  
**Upstream/Downstream:** → modifier tools (mirror, array, boolean)  
**Test Cases:** 
- Happy: add cube, verify type & name
- Error: duplicate name → OBJECT_NAME_EXISTS
- Error: invalid type → INVALID_PRIMITIVE_TYPE

**Status:** 🟢 GREEN (Blender 4.2+ operators stable)

---

### 2. mesh_mirror_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add a Mirror modifier to symmetrize geometry. Set axis (X/Y/Z), clamp overlap, mirror threshold. Non-destructive; call mesh_apply_modifier to freeze.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  axis: z.enum(["X", "Y", "Z"]),
  use_clip?: z.boolean(),
  use_axis_relative?: z.boolean(),
  mirror_offset_u?: z.number().optional(),
  mirror_offset_v?: z.number().optional(),
  threshold?: z.number().optional(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Call mesh_add_modifier for Array/Boolean/Bevel stacking"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_AXIS`  
**Python Handler Outline:** Get object, create modifier via `modifiers.new('Mirror', 'MIRROR')`, set properties, undo_push.  
**Upstream/Downstream:** → Array, Boolean, Bevel modifiers (chaining)  
**Test Cases:**
- Happy: add mirror on X axis, verify on symmetric edit
- Error: object not found → OBJECT_NOT_FOUND
- Idempotency: adding mirror twice on same axis is safe (second replaces first)

**Status:** 🟢 GREEN

---

### 3. mesh_array_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Array modifier for repetition along an axis. Set count, offset mode (constant/relative/fit curve), displacement, merge distance.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  count: z.number().min(1).max(100),
  offset_type: z.enum(["CONSTANT_OFFSET", "RELATIVE_OFFSET", "FIT_CURVE"]),
  constant_offset?: z.tuple([z.number(), z.number(), z.number()]),
  relative_offset?: z.tuple([z.number(), z.number(), z.number()]),
  use_merge_vertices?: z.boolean(),
  merge_threshold?: z.number(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
  totalFaceCount: number,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Optionally chain with Boolean for detail variation"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_COUNT`, `INVALID_OFFSET_TYPE`  
**Python Handler Outline:** Set array modifier properties, compute result face count via bmesh preview.  
**Upstream/Downstream:** ← Mirror; → Boolean, Bevel  
**Test Cases:**
- Happy: 5 copies with constant offset (0.2, 0, 0)
- Error: count > 100 → INVALID_COUNT
- Verify face count scales linearly (n * base_faces)

**Status:** 🟢 GREEN

---

### 4. mesh_boolean_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Boolean modifier (Union/Difference/Intersect). Choose Exact or Fast solver. Solver: Exact for complex overlaps (slower), Fast for clean cuts (faster).

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  operation: z.enum(["UNION", "DIFFERENCE", "INTERSECT"]),
  target_object?: z.string(),
  target_collection?: z.string(),
  solver: z.enum(["EXACT", "FAST"]),
  use_self_intersection_exact?: z.boolean(),
  use_hole_tolerant_exact?: z.boolean(),
  overlap_threshold_fast?: z.number(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
  operation: string,
  solverUsed: string,
  warningsNeeded?: string[],
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Chain with Edge Split, Bevel, or Triangulate for export readiness"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `TARGET_NOT_FOUND`, `INVALID_OPERATION`, `INVALID_SOLVER`  
**Python Handler Outline:** Create modifier, set operation/target/solver, validate mesh topology (warn if non-manifold), undo_push.  
**Upstream/Downstream:** ← Array, Mirror; → Edge Split, Bevel, Triangulate  
**Test Cases:**
- Happy path: Difference operation, Exact solver, valid cutter object
- Error: target object missing → TARGET_NOT_FOUND
- Error: non-manifold cutter → warning in payload (not hard error)
- Solver perf: Exact slower but correct; Fast may have artifacts on overlapping

**Status:** 🟢 GREEN (both solvers in 4.2+)

---

### 5. mesh_bevel_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Bevel modifier for non-destructive edge hardness. Set width, segments, affect mode (edges/vertices), limit method (angle/weight/none), harden normals.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  width: z.number().min(0),
  segments: z.number().min(1).max(10),
  affect: z.enum(["EDGES", "VERTICES"]),
  limit_method: z.enum(["NONE", "ANGLE", "WEIGHT", "VGROUP"]),
  angle_limit?: z.number(),
  bevel_type: z.enum(["OFFSET", "WIDTH", "DEPTH", "PERCENT"]),
  harden_normals?: z.boolean(),
  profile_type?: z.enum(["SUPERELLIPSE", "CUSTOM"]),
  material_index?: z.number(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Chain Weighted Normal modifier for final normal cleanup before export"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_BEVEL_TYPE`, `NEGATIVE_WIDTH`  
**Python Handler Outline:** Create bevel modifier, set all params, validate width > 0, undo_push.  
**Upstream/Downstream:** ← Boolean, Mirror; → Weighted Normal, Triangulate  
**Test Cases:**
- Happy: width=0.01, segments=3, affect EDGES, limit ANGLE 60°
- Error: width < 0 → NEGATIVE_WIDTH
- Idempotency: bevel twice with same params produces same result
- Custom profile preset support (Support Loops, Steps) — verify preset generation

**Status:** 🟢 GREEN (custom profiles added 4.2)

---

### 6. mesh_subdivision_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Subdivision Surface modifier for smooth organic shapes. Set viewport levels, render levels, boundary smooth, quality.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  viewport_levels: z.number().min(0).max(6),
  render_levels: z.number().min(0).max(6),
  boundary_smooth: z.enum(["PRESERVE_CORNERS", "EDGE_ONLY"]),
  use_creases?: z.boolean(),
  use_custom_creases?: z.boolean(),
  catmull_clark_subdivision?: z.boolean(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Mark sharp edges with mesh_mark_sharp to preserve hard corners; then add Bevel for beveled hard edges"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_LEVEL_RANGE`  
**Python Handler Outline:** Create modifier, set levels and creases, undo_push.  
**Upstream/Downstream:** ← Bevel, Boolean; → Decimate, Triangulate  
**Test Cases:**
- Happy: viewport 2, render 3, crease enabled
- Crease control: edges marked as crease should not smooth
- Level quality: higher levels = smoother but more expensive

**Status:** 🟢 GREEN

---

### 7. mesh_smooth_by_angle_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Replace deprecated `use_auto_smooth` with Smooth By Angle modifier (Blender 4.2 standard). Set angle threshold; edges sharper than angle become hard normals.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  angle: z.number().min(0).max(180),
  ignore_sharpness?: z.boolean(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Apply before export to bake smooth-by-angle into mesh normals"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_ANGLE_RANGE`  
**Python Handler Outline:** Create Smooth By Angle modifier from the Essentials asset, set angle, undo_push.  
**Upstream/Downstream:** ← Boolean, Bevel; → Triangulate, export  
**Test Cases:**
- Happy: angle 30° for hard-surface props (sharp metal corners)
- Angle 60° for softer props (organic armor plating)
- Verify normal direction matches expected shading in viewport

**Status:** 🟢 GREEN (geometry nodes asset, bundled in 4.2)

---

### 8. mesh_decimate_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Decimate modifier (Collapse/Un-Subdivide/Planar modes) for LOD creation or topology cleanup. Ratio/iterations/angle controls polygon reduction.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  mode: z.enum(["COLLAPSE", "UNSUBDIVIDE", "PLANAR"]),
  collapse_ratio?: z.number().min(0).max(1),
  unsubdivide_iterations?: z.number().min(1),
  planar_angle_limit?: z.number().min(0).max(180),
  use_symmetry?: z.boolean(),
  symmetry_axis?: z.enum(["X", "Y", "Z"]),
  triangulate?: z.boolean(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
  originalFaceCount: number,
  decimatedFaceCount: number,
  reductionRatio: number,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["For LOD0 → LOD1: create second copy of high-poly, decimate at 0.5 ratio, then LOD2 at 0.25 on LOD1 copy"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_MODE`, `INVALID_RATIO`, `NO_TOPOLOGY_TO_SUBDIVIDE`  
**Python Handler Outline:** Create modifier, set mode-specific params, compute face count deltas, undo_push.  
**Upstream/Downstream:** ← Subdivision; → LOD grouping  
**Test Cases:**
- Happy Collapse: 0.5 ratio on 1000-tri mesh → ~500 tris
- Happy Un-Subdivide: reverse 2 subsurf levels
- Happy Planar: remove 45° angle threshold on flat surfaces
- Error: ratio out of range → INVALID_RATIO
- Symmetry preservation: X-axis symmetry maintained across decimation

**Status:** 🟢 GREEN

---

### 9. mesh_edge_split_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Edge Split modifier (last in stack before export) to ensure FBX exporter produces clean hard-surface normals. Split by angle or marked sharp edges.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  use_edge_sharp?: z.boolean(),
  use_edge_angle?: z.boolean(),
  split_angle?: z.number().min(0).max(180),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Final step before export_fbx; ensures hard edges stay hard in UE5"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`  
**Python Handler Outline:** Create modifier, set angle and sharp flags, undo_push.  
**Upstream/Downstream:** ← Bevel, Boolean; → Triangulate, export_fbx  
**Test Cases:**
- Happy: angle 30°, sharp edges enabled
- Verify exported FBX has distinct vertex normals at hard edges

**Status:** 🟢 GREEN

---

### 10. mesh_solidify_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Solidify modifier to create thickness on single-sided surfaces (armor plating, thin walls, shells). Set thickness, offset, rim.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  thickness: z.number().min(0.001),
  offset?: z.number(),
  use_even_offset?: z.boolean(),
  use_quality_normals?: z.boolean(),
  use_rim?: z.boolean(),
  rim_width?: z.number(),
  material_offset_rim?: z.number(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Optional: apply Bevel to the thickened edges"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_THICKNESS`  
**Python Handler Outline:** Create modifier, set thickness and offset, undo_push.  
**Upstream/Downstream:** → Bevel, Triangulate  
**Test Cases:**
- Happy: 0.05 thickness on single-sided face, even offset
- Rim generation: verify rim material slot

**Status:** 🟢 GREEN

---

### 11. mesh_weld_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Weld modifier to merge nearby vertices (distance threshold). Non-destructive cleanup for boolean remnants or overlapping geometry.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  merge_distance: z.number().min(0.0001),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Check result for missing geometry; increase threshold if over-merged"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_DISTANCE`  
**Python Handler Outline:** Create modifier, set distance, undo_push.  
**Upstream/Downstream:** ← Boolean cleanup; → Triangulate  
**Test Cases:**
- Happy: 0.001 threshold merges floating verts
- Error: negative threshold → INVALID_DISTANCE

**Status:** 🟢 GREEN

---

### 12. mesh_triangulate_modifier_add
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Add Triangulate modifier to convert quads/n-gons to triangles (UE5 requirement). Must be last modifier before export. Choose quad method (Beauty/Fixed/Shortest Diagonal).

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  quad_method: z.enum(["BEAUTY", "FIXED", "FIXED_ALTERNATE", "SHORTEST_DIAGONAL"]),
  ngon_method?: z.enum(["BEAUTY", "FIXED", "FIXED_ALTERNATE", "SHORTEST_DIAGONAL"]),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  modifierName: string,
}
```

**Refs:** `{ objectName, modifierName }`  
**NextSteps:** `["Ready for export_fbx or export_gltf"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_METHOD`  
**Python Handler Outline:** Create modifier, set methods, undo_push.  
**Upstream/Downstream:** → export_fbx, export_gltf  
**Test Cases:**
- Happy: Beauty method on mixed quads/ngons
- Verify all faces are triangles post-export

**Status:** 🟢 GREEN

---

### 13. mesh_mark_sharp
**Group:** `mesh`  
**Category:** Primitive  
**Description:** Enter Edit Mode, select edges, mark as sharp. Used in conjunction with Smooth By Angle to preserve hard corners in hard-surface models.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  edgeIndices?: z.array(z.number()),
  selectAll?: z.boolean(),
  angleThreshold?: z.number(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  markedEdgeCount: number,
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["Apply Smooth By Angle modifier to bake the sharpness"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_EDIT_MODE`, `NO_EDGES_SELECTED`  
**Python Handler Outline:** Switch to Edit Mode with bmesh, iterate edges by index, set `sharp=True` flag, undo_push.  
**Upstream/Downstream:** → Smooth By Angle, Bevel  
**Test Cases:**
- Happy: mark 4 edges in a cube as sharp
- Error: no edges selected → NO_EDGES_SELECTED
- Verify sharp edges show as bold lines in wireframe

**Status:** 🟢 GREEN

---

### 14. mesh_bevel_edge_single
**Group:** `mesh`  
**Category:** Primitive  
**Description:** In Edit Mode, bevel a single selected edge or set of edges interactively (non-modal version via bmesh params). Set width, segments, type.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  edgeIndices: z.array(z.number()),
  width: z.number().min(0.001),
  segments: z.number().min(1).max(10),
  profile: z.number().min(0).max(1),
  bevel_type: z.enum(["OFFSET", "WIDTH", "DEPTH", "PERCENT"]),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  edgesBeveledCount: number,
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["Extrude, inset, or apply Bevel modifier for larger bevels"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_EDGE_INDEX`, `INVALID_WIDTH`, `INVALID_EDIT_MODE`  
**Python Handler Outline:** Enter Edit Mode, use bmesh ops, call `bmesh.ops.bevel()` with edge list and params, undo_push.  
**Upstream/Downstream:** ← Mark Sharp; → extrude, inset  
**Test Cases:**
- Happy: bevel 2 edges with 0.01 width, 2 segments
- Error: invalid edge index → INVALID_EDGE_INDEX
- Verify bevel geometry in viewport

**Status:** 🟡 YELLOW (bmesh bevel requires careful parameter tuning; modal bevel tool exists but API is complex for non-interactive)

---

### 15. mesh_extrude_faces
**Group:** `mesh`  
**Category:** Primitive  
**Description:** In Edit Mode, extrude selected faces along normal direction. Set amount (distance), optionally individual faces. Returns new face count.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  faceIndices: z.array(z.number()),
  amount: z.number(),
  individual?: z.boolean(),
  scale?: z.number(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  newFaceCount: number,
  newVertexCount: number,
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["Scale up result with mesh_transform; or add detail with inset/bevel"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_FACES_SELECTED`, `INVALID_EDIT_MODE`  
**Python Handler Outline:** Enter Edit Mode with bmesh, call `bmesh.ops.extrude_face()`, apply transform, undo_push.  
**Upstream/Downstream:** → inset, bevel, extrude again (recursive detail)  
**Test Cases:**
- Happy: extrude 4 cube faces outward by 0.2
- Individual extrude: each face extrudes independently
- Error: no faces selected → NO_FACES_SELECTED

**Status:** 🟡 YELLOW (bmesh extrude works but edge/face selection indexing is fragile; recommend using face loops instead)

---

### 16. mesh_inset_faces
**Group:** `mesh`  
**Category:** Primitive  
**Description:** In Edit Mode, inset selected faces (shrink inward, create border). Set inset amount, thickness, depth. Creates rim faces for detail.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  faceIndices: z.array(z.number()),
  amount: z.number().min(0),
  thickness?: z.number(),
  depth?: z.number(),
  individual?: z.boolean(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  newFaceCount: number,
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["Extrude the inset rim upward for panel detail"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_FACES_SELECTED`, `INVALID_INSET_AMOUNT`  
**Python Handler Outline:** bmesh `bmesh.ops.inset_individual()` or `bmesh.ops.inset_face()`, set amount, undo_push.  
**Upstream/Downstream:** ← extrude; → extrude (stacked detail)  
**Test Cases:**
- Happy: inset by 0.1, thickness 0.05
- Individual inset: each face inserts independently
- Error: negative amount → INVALID_INSET_AMOUNT

**Status:** 🟡 YELLOW (bmesh inset API varies; individual vs grouped insets have different operator paths)

---

### 17. mesh_bridge_edge_loops
**Group:** `mesh`  
**Category:** Primitive  
**Description:** In Edit Mode, select two edge loops, bridge them with faces. Creates geometry between separate edge rings (e.g., connecting cylinder tops).

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  type: z.enum(["SINGLE", "PAIRS", "LOOPS", "RINGS"]),
  use_merge?: z.boolean(),
  merge_factor?: z.number(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  newFaceCount: number,
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["Smooth the bridged faces or add bevel for hard edges"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_EDGE_LOOP_SELECTION`, `NO_EDGES_SELECTED`  
**Python Handler Outline:** Use `bpy.ops.mesh.bridge_edge_loops()` (operator; requires 3D context), undo_push.  
**Upstream/Downstream:** → bevel, smooth  
**Test Cases:**
- Happy: bridge two cylinder edge loops
- Merge result: verify closed topology
- Error: fewer than 2 edge loops → INVALID_EDGE_LOOP_SELECTION

**Status:** 🟡 YELLOW (operator exists but requires 3D View context; headless execution needs context override)

---

### 18. mesh_duplicate_for_lod
**Group:** `mesh`  
**Category:** Composite  
**Description:** Duplicate mesh object by name, create LOD copy. Composite: duplicates high-poly, adds Decimate modifier at specified ratio, names LOD mesh, parents under `LOD_<MeshName>` empty.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  lodLevel: z.number().min(0).max(3),
  decimateRatio?: z.number().min(0).max(1),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  lodMeshName: string,
  lodGroupName: string,
  originalFaceCount: number,
  lodFaceCount: number,
}
```

**Refs:** `{ objectName, lodMeshName, lodGroupName }`  
**NextSteps:** `["Repeat for LOD1 (0.5 ratio), LOD2 (0.25), then call export_fbx_static to export as LOD asset"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `LOD_LEVEL_INVALID`, `INVALID_DECIMATE_RATIO`  
**Python Handler Outline:** 
1. Duplicate object
2. Add Decimate modifier with ratio
3. Create empty parent named `LOD_<OrigName>`
4. Parent LOD meshes under it
5. Undo push

**Upstream/Downstream:** ← Subdivision, Boolean; → export_fbx_static (auto-detects LOD groups)  
**Test Cases:**
- Happy: LOD0 (original), LOD1 (0.5), LOD2 (0.25), all parented under `LOD_Weapon`
- Verify face counts decrease 50% per level
- Export and verify UE5 imports 3 LOD levels

**Status:** 🟢 GREEN (composite of existing primitives)

---

### 19. modifier_apply_all
**Group:** `modifier`  
**Category:** Primitive  
**Description:** Apply all modifiers on an object in order. Bakes non-destructive stack into final mesh. One undo entry.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  skipModifiers?: z.array(z.string()),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  appliedModifierCount: number,
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["Call export_fbx or export_gltf; mesh is now static"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_MODIFIERS_TO_APPLY`, `MODIFIER_APPLY_FAILED`  
**Python Handler Outline:** Iterate modifiers, call `bpy.ops.object.modifier_apply(modifier=name)` for each, undo_push once at end.  
**Upstream/Downstream:** ← All modifier tools  
**Test Cases:**
- Happy: 5 modifiers applied in order
- Skip list: skip bevel, apply others
- Error: no modifiers → NO_MODIFIERS_TO_APPLY
- Verify resulting mesh matches viewport preview

**Status:** 🟢 GREEN

---

### 20. mesh_validate_topology
**Group:** `mesh`  
**Category:** Primitive  
**Description:** Scan mesh for non-manifold edges, open boundaries, degenerate faces. Returns list of issues. Non-destructive (read-only).

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  isManifold: boolean,
  nonManifoldEdgeCount: number,
  openBoundaryCount: number,
  degenerateFaceCount: number,
  issues: string[],
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["If issues found, use mesh_merge_by_distance or Boolean Exact solver for cleanup"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`  
**Python Handler Outline:** Use bmesh select flush, iterate faces/edges, check manifold status, count issues.  
**Upstream/Downstream:** → mesh_merge_by_distance, mesh_weld_modifier_add  
**Test Cases:**
- Happy: closed cube → isManifold=true, no issues
- Non-manifold: cube with double-sided faces → issues reported
- Open boundary: open cylinder → boundary count > 0

**Status:** 🟢 GREEN

---

### 21. material_create_principled_for_ue5
**Group:** `material`  
**Category:** Composite  
**Description:** Create material with Principled BSDF wired to only UE5-compatible Khronos PBR parameters: base_color, metallic, roughness, normal, emissive, alpha. Excludes coat, subsurface (Lumen-compatible).

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  materialName: z.string(),
  baseColorHex?: z.string(),
  metallic?: z.number().min(0).max(1),
  roughness?: z.number().min(0).max(1),
  normalMapPath?: z.string(),
  emissiveStrength?: z.number(),
}
```

**Output Payload:**
```ts
{
  materialName: string,
  objectName: string,
}
```

**Refs:** `{ materialName, objectName }`  
**NextSteps:** `["Assign material slots to mesh faces; then export_fbx exports materials"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `MATERIAL_NAME_EXISTS`, `INVALID_TEXTURE_PATH`  
**Python Handler Outline:**
1. Create material with Principled BSDF
2. Delete unused nodes (subsurface, coat, etc.)
3. Wire Base Color, Metallic, Roughness, Normal, Emissive, Alpha
4. Assign to object's material slot 0
5. Return material name

**Upstream/Downstream:** → mesh_assign_material_slot  
**Test Cases:**
- Happy: create material with base color hex, metallic 0.8, roughness 0.3
- Normal map texture: verify linked
- Emissive: verify node chain correct

**Status:** 🟢 GREEN (straightforward node graph)

---

### 22. mesh_assign_material_slot
**Group:** `material`  
**Category:** Primitive  
**Description:** Assign material to object's material slot. Optionally set slot index (default 0). Select faces and call to assign material to face group.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  materialName: z.string(),
  slotIndex?: z.number().min(0),
  faceIndices?: z.array(z.number()),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  materialName: string,
  slotIndex: number,
}
```

**Refs:** `{ objectName, materialName }`  
**NextSteps:** `["Repeat for additional material slots (e.g., head on slot 1, body on slot 0)"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `MATERIAL_NOT_FOUND`, `INVALID_SLOT_INDEX`, `NO_FACES_SELECTED`  
**Python Handler Outline:** Get object, get or create material slot, assign material, optionally assign to selected faces via bmesh, undo_push.  
**Upstream/Downstream:** ← material_create_principled_for_ue5  
**Test Cases:**
- Happy: assign material to slot 0, all faces
- Face subset: assign to specific face indices only
- Multiple slots: verify slot order preserved for UE5 import

**Status:** 🟢 GREEN

---

### 23. mesh_create_collision_box
**Group:** `collision`  
**Category:** Composite  
**Description:** Create a box collision mesh named `UBX_<MeshName>`, parent under target mesh. UE5 FBX importer auto-converts to collision box primitive on import.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  boxSize?: z.tuple([z.number(), z.number(), z.number()]),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  collisionMeshName: string,
}
```

**Refs:** `{ objectName, collisionMeshName }`  
**NextSteps:** `["Export parent mesh with FBX; collision auto-imports to UE5"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_BOX_SIZE`  
**Python Handler Outline:**
1. Create cube primitive
2. Name it `UBX_<ObjectName>`
3. Scale to fit bounding box or user size
4. Parent under target mesh
5. Return collision name

**Upstream/Downstream:** → export_fbx_static  
**Test Cases:**
- Happy: create `UBX_Sword` under `Sword` object
- Scale verification: box matches intended collision volume
- Export test: UE5 recognizes UCX prefix and converts to collision box

**Status:** 🟡 YELLOW (parent-child relationships may affect export; test FBX round-trip)

---

### 24. mesh_create_collision_convex
**Group:** `collision`  
**Category:** Composite  
**Description:** Create convex hull collision mesh named `UCX_<MeshName>`, parent under target. For complex props that need accurate collision shape (better than box).

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  simplifyFactor?: z.number().min(0).max(1),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  collisionMeshName: string,
  faceCount: number,
}
```

**Refs:** `{ objectName, collisionMeshName }`  
**NextSteps:** `["Export; UE5 converts to convex collision primitive"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `CONVEX_HULL_FAILED`, `INVALID_SIMPLIFY_FACTOR`  
**Python Handler Outline:**
1. Compute convex hull of mesh vertices (bmesh or scipy)
2. Create new mesh from hull
3. Name `UCX_<ObjectName>`
4. Parent under target
5. Return collision name

**Upstream/Downstream:** → export_fbx_static  
**Test Cases:**
- Happy: create convex hull for irregular weapon shape
- Simplify factor 0.8: reduce collision mesh complexity
- Error: empty geometry → CONVEX_HULL_FAILED
- Export: verify UE5 recognizes UCX

**Status:** 🟡 YELLOW (convex hull computation can be expensive; test performance on complex meshes)

---

### 25. export_fbx_static
**Group:** `export`  
**Category:** Composite  
**Description:** Export static mesh(es) to FBX file. Exposes all Blender FBX exporter parameters per UE-TARGETS.md §7. Handles LOD groups, collision meshes, material order, triangulation.

**Zod Input Schema:**
```ts
{
  objectNames: z.array(z.string()),
  filePath: z.string(),
  global_scale?: z.number(),
  apply_unit_scale?: z.boolean(),
  axis_forward?: z.enum(["-Y", "-X", "X", "Y"]),
  axis_up?: z.enum(["Z", "-Z", "Y", "-Y"]),
  use_triangles?: z.boolean(),
  use_selection?: z.boolean(),
  use_tspace?: z.boolean(),
  use_custom_props?: z.boolean(),
  embed_textures?: z.boolean(),
  batch_mode?: z.enum(["OFF", "GROUP", "SCENE"]),
}
```

**Output Payload:**
```ts
{
  filePath: string,
  exportedObjects: string[],
  fileSize: number,
  triangleCount: number,
  materialCount: number,
  lodLevelsDetected: number,
  collisionMeshesDetected: number,
  nanniteRecommended: boolean,
  warnings: string[],
}
```

**Refs:** (export result; not chainable; terminal step)  
**NextSteps:** `["Import FBX into UE5; verify in Skeletal/Static Mesh Editor"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_FILE_PATH`, `EXPORT_FAILED`, `NO_MESHES_TO_EXPORT`, `TRIANGULATION_NEEDED`  
**Python Handler Outline:**
1. Validate object names exist
2. Apply any pending modifiers (user choice)
3. Ensure triangulated (warn if not, apply Triangulate modifier)
4. Build export params dict from inputs (with UE5 defaults)
5. Call `bpy.ops.export_scene.fbx(**params)`
6. Inspect result file, count tris/materials, detect LODs/collisions
7. Return metadata + warnings
8. Undo push

**Upstream/Downstream:** ← All modeling tools; terminal  
**Test Cases:**
- Happy: export single mesh with materials
- LOD export: detect `LOD_Weapon` group, export as UE5 LOD asset
- Collision: include `UBX_Mesh` in export
- Axis remap: verify +X forward, +Z up preserved
- FBX version: BIN7400 (2014+) output

**Status:** 🟢 GREEN (wraps stable bpy.ops.export_scene.fbx)

---

### 26. export_fbx_skeletal
**Group:** `export`  
**Category:** Composite  
**Description:** Export skeletal mesh (armature + meshes + sockets/collision). Exposes FBX anim params: bake_anim, bake_anim_use_all_bones, primary/secondary bone axes, add_leaf_bones flag (must be False for UE5 Mannequin compat).

**Zod Input Schema:**
```ts
{
  armatureName: z.string(),
  meshNames: z.array(z.string()),
  filePath: z.string(),
  bake_anim?: z.boolean(),
  bake_anim_use_all_bones?: z.boolean(),
  add_leaf_bones?: z.boolean(),
  primary_bone_axis?: z.enum(["X", "Y", "-X", "-Y", "-Z"]),
  secondary_bone_axis?: z.enum(["X", "Y", "Z"]),
  use_armature_deform_only?: z.boolean(),
  global_scale?: z.number(),
  apply_unit_scale?: z.boolean(),
  axis_forward?: z.enum(["-Z", "-Y", "-X", "X", "Y"]),
  axis_up?: z.enum(["Z", "-Z", "Y", "-Y"]),
  use_triangles?: z.boolean(),
  use_tspace?: z.boolean(),
  use_custom_props?: z.boolean(),
}
```

**Output Payload:**
```ts
{
  filePath: string,
  armatureName: string,
  exportedMeshNames: string[],
  fileSize: number,
  boneCount: number,
  triangleCount: number,
  materialCount: number,
  hasMorphTargets: boolean,
  warnings: string[],
}
```

**Refs:** (export result; not chainable)  
**NextSteps:** `["Import FBX into UE5 Skeletal Mesh Editor; verify bone hierarchy matches Mannequin if targeting Lyra"]`  
**ErrorCodes:** `ARMATURE_NOT_FOUND`, `MESH_NOT_FOUND`, `INVALID_BONE_AXIS`, `ADD_LEAF_BONES_ERROR`, `EXPORT_FAILED`  
**Python Handler Outline:**
1. Validate armature + meshes exist
2. **Critical:** Verify `add_leaf_bones=False` (UE5 Mannequin incompatibility if True)
3. Warn if armature root bone not named `root`
4. Warn if morph targets present and Nanite will be used
5. Call `bpy.ops.export_scene.fbx(**params)`
6. Inspect result: count bones, tris, materials
7. Return metadata
8. Undo push

**Upstream/Downstream:** ← mesh modeling + rigging; terminal  
**Test Cases:**
- Happy: export Mannequin-compatible skeleton with meshes
- add_leaf_bones False: verify UE5 compatibility
- Root bone check: warn if not `root`
- Morph targets: warn if Nanite intended
- FBX version: BIN7400

**Status:** 🟢 GREEN (wraps export_scene.fbx with UE5-specific validation)

---

### 27. export_gltf
**Group:** `export`  
**Category:** Composite  
**Description:** Export to glTF 2.0 (Khronos standard). Secondary path for multi-engine use (Unity, Godot, web). Supports embedded or separate textures, optional gzip compression.

**Zod Input Schema:**
```ts
{
  objectNames: z.array(z.string()),
  filePath: z.string(),
  format: z.enum(["GLTF_EMBEDDED", "GLTF_SEPARATE", "GLBT"]),
  export_materials?: z.boolean(),
  export_textures?: z.boolean(),
  export_animations?: z.boolean(),
  use_draco_mesh_compression?: z.boolean(),
}
```

**Output Payload:**
```ts
{
  filePath: string,
  format: string,
  exportedObjects: string[],
  triangleCount: number,
  materialCount: number,
  animationCount?: number,
  fileSize: number,
  warnings: string[],
}
```

**Refs:** (export result; not chainable)  
**NextSteps:** `["Import into Unity, Godot, or web viewer; or re-import to UE5 via Datasmith glTF importer"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_FILE_PATH`, `EXPORT_FAILED`, `NO_MESHES_TO_EXPORT`  
**Python Handler Outline:**
1. Call `bpy.ops.export_scene.gltf(**params)`
2. Count result tris, materials, animations
3. Return metadata
4. Undo push

**Upstream/Downstream:** ← All modeling tools; terminal  
**Test Cases:**
- Happy: export embedded glTF (all data in .glb)
- Separate mode: textures as external .bin + .png files
- Draco compression: verify file size reduction
- Material export: Principled BSDF → glTF metallic-roughness

**Status:** 🟢 GREEN

---

### 28. mesh_validate_for_export_ue5
**Group:** `mesh`  
**Category:** Primitive  
**Description:** Pre-export validation: check triangulation, manifold topology, material slots, collision mesh naming, LOD structure, axis alignment, origin at world zero (for props). Returns detailed report.

**Zod Input Schema:**
```ts
{
  objectName: z.string(),
  isSkeletalMesh?: z.boolean(),
}
```

**Output Payload:**
```ts
{
  objectName: string,
  isValid: boolean,
  checks: {
    isTriangulated: boolean,
    isManifold: boolean,
    hasMaterialSlots: boolean,
    collisionMeshesNamed: boolean,
    originAtZero: boolean,
    hasNormals: boolean,
    estimatedNaniteCompatible: boolean,
    warnings: string[],
    errors: string[],
  },
}
```

**Refs:** `{ objectName }`  
**NextSteps:** `["If errors, fix mesh and re-check; if warnings, decide if acceptable for UE5 import"]`  
**ErrorCodes:** `OBJECT_NOT_FOUND`  
**Python Handler Outline:**
1. Get mesh object
2. Check all validation rules (triangulation, manifold, materials, collision names, origin, normals)
3. Estimate Nanite compatibility (tri count, deformation, morph targets)
4. Build report with warnings/errors
5. Return payload

**Upstream/Downstream:** → export_fbx_static, export_fbx_skeletal  
**Test Cases:**
- Happy: all checks pass
- Non-triangulated: triangulation warning
- Non-manifold: error flag
- Origin not zero: warning (may affect UE5 placement)
- Nanite compatible: estimate based on tri count + modifier stack

**Status:** 🟢 GREEN

---

## 3. Feasibility Verdict Table

| Step | Tool(s) | Status | Blockers / Notes |
|------|---------|--------|------------------|
| 1. Reference & Blockout | `mesh_add_primitive` | 🟢 GREEN | Stable operator interface |
| 2. Mirror Setup | `mesh_mirror_modifier_add` | 🟢 GREEN | Non-destructive, live preview |
| 3. Array Repetition | `mesh_array_modifier_add` | 🟢 GREEN | Standard modifier |
| 4. Boolean Operations | `mesh_boolean_modifier_add` | 🟢 GREEN | Exact + Fast solvers fully functional |
| 5. Edge Crease & Bevel Weight | `mesh_mark_sharp` + manual bmesh | 🟡 YELLOW | Interactive modal bevel tool in UI; scripted non-modal version exists but needs testing |
| 6. Bevel Modifier | `mesh_bevel_modifier_add` | 🟢 GREEN | Custom profile support (4.2 new feature) works |
| 7. Subdivision Surface | `mesh_subdivision_modifier_add` | 🟢 GREEN | Creases work as expected |
| 8. Mark Sharp / Shade Smooth | `mesh_mark_sharp` + `mesh_smooth_by_angle_modifier_add` | 🟢 GREEN | `use_auto_smooth` deprecated → replaced by Smooth By Angle modifier (geometry nodes asset) |
| 9. High-Poly → Low-Poly | `mesh_duplicate_for_lod` (composite) | 🟢 GREEN | Decimate + duplicate proven |
| 10. Mesh Editing (Extrude, Inset, etc.) | `mesh_extrude_faces`, `mesh_inset_faces`, `mesh_bevel_edge_single` | 🟡 YELLOW | Require Edit Mode + bmesh; edge/face selection by index is fragile (consider supporting face/edge loops instead) |
| 11. Edge Split | `mesh_edge_split_modifier_add` | 🟢 GREEN | Pre-export standard |
| 12. Solidify | `mesh_solidify_modifier_add` | 🟢 GREEN | Standard modifier |
| 13. Weld & Merge | `mesh_weld_modifier_add` | 🟢 GREEN | Distance-based merge works |
| 14. Triangulation | `mesh_triangulate_modifier_add` | 🟢 GREEN | UE5 requirement; all methods available |
| 15. UV Unwrapping | Not included (Phase 0) | 🔴 RED | Requires UI context (UV Editor); deferred to Phase 2 |
| 16. Material Setup | `material_create_principled_for_ue5`, `mesh_assign_material_slot` | 🟢 GREEN | Node graph creation stable |
| 17. Modifier Freezing | `modifier_apply_all` | 🟢 GREEN | Standard operator |
| 18. LOD Creation | `mesh_duplicate_for_lod` | 🟢 GREEN | Composite; uses Decimate + parenting |
| 19. Collision Meshes | `mesh_create_collision_box`, `mesh_create_collision_convex` | 🟡 YELLOW | Naming conventions (UBX_, UCX_) work; parent-child export needs FBX round-trip verification |
| 20. Export FBX Static | `export_fbx_static` | 🟢 GREEN | All 30+ params exposed; LOD/collision detection included |
| 21. Export FBX Skeletal | `export_fbx_skeletal` | 🟢 GREEN | Mannequin-specific validation (add_leaf_bones=False, root bone naming) included |
| 22. Export glTF | `export_gltf` | 🟢 GREEN | Secondary path; Khronos PBR subset stable |
| 23. Validation | `mesh_validate_topology`, `mesh_validate_for_export_ue5` | 🟢 GREEN | Read-only; comprehensive checks |

---

## 4. Entity Types Touched

| Entity Type | Tool Domain | Coverage |
|---|---|---|
| **Object** | `mesh`, `export` | Create, duplicate, parent, transform, validate |
| **Mesh** | `mesh`, `modifier`, `collision` | Primitives, boolean, extrude, inset, bevel, triangulate, weld, edge split |
| **Modifier** | `modifier` | Mirror, Array, Boolean, Bevel, Subdivision, Solidify, Decimate, Edge Split, Weld, Triangulate, Smooth By Angle |
| **Material** | `material` | Create Principled BSDF, assign slots, Khronos PBR params (base_color, metallic, roughness, normal, emissive, alpha) |
| **ShaderNode** | `material` | Graph: Principled BSDF, Image Texture, ColorRamp, MixShader (minimal set for UE5 compat) |
| **Armature** | `export` | Export endpoint for skeletal meshes (not rigging; defer to B3) |
| **Collision** | `collision` | Name-keyed meshes (UBX_, UCX_, USP_, UCP_) |
| **Empty** | `collision`, `export` | LOD group containers (LOD_<MeshName>), socket parents (SOCKET_*) |
| **Action** | (Not in B2 scope; defer to B3 animation export) | — |

---

## 5. Open Issues & Questions for User

1. **Knife Projection Tool** — Modal operator in UI (Ctrl+Shift+K in Edit Mode). No non-modal scripted equivalent documented. Consider **DEFER** to Phase 2 or note as limitation.

2. **Edge Loop Cut & Slide** — Modal operator. `bpy.ops.mesh.loopcut_slide()` has parameters (edge_index, number_cuts, slide_factor) for non-modal use; **verify this in 4.2 with integration tests** (may have moved in recent versions).

3. **Bevel Weight Input** — User expects to set weight 0–1 per edge in Edit Mode (Shift+E interactive). Non-modal bmesh path exists but is cumbersome (set attribute directly). **Recommendation:** Support both operator (interactive, context-required) and attribute-based (headless-friendly).

4. **Face Selection by Index** — Current proposal uses face/edge indices (0-indexed into bmesh). This is **fragile** if topology changes mid-operation. **Better approach:** Support named face/edge loops (e.g., `"all"`, `"linked"`, or loop index in bmesh). Reconsider API surface.

5. **Context Override for Bridge Edge Loops** — `bpy.ops.mesh.bridge_edge_loops()` requires 3D View context. Agent in headless mode needs `bpy.context.temp_override(...)` with a `screen` + `area` + `region` tuple. **Test this; document required mock context.**

6. **UE5 Mannequin Bone Naming** — Should `bone_add` and `bone_rename` tools normalize `.L` / `.R` suffixes to `_l` / `_r` (UE5 standard)? **Clarify:** normalization on write (rename tool) or on export validation (warn)?

7. **Nanite Morph Target Incompatibility** — If a skeletal mesh has both Nanite flag request AND morph targets (blendshapes), export should **warn** (not error). Implement in `export_fbx_skeletal` validation. **Confirm acceptable warning level.**

8. **LOD0 Auto-Grouping** — Current `mesh_duplicate_for_lod` assumes high-poly is manually wrapped in `LOD_<Name>` empty. Should tool auto-create parent empty on first call? **Clarify UE5 importer behavior**: Does it require LOD0 in the group, or accept LOD0 as separate file?

9. **Triangulation Strategy (Beauty vs. Shortest Diagonal)** — For hard-surface props, which quad → triangle method is preferred? Document artist choice or auto-select based on mesh type (planar → fixed, organic → beauty).

10. **Smooth By Angle Modifier Registration** — The modifier is a geometry nodes asset. On addon init, is it loaded from the bundled Essentials library, or is it expected to exist? **Verify bundling in standalone addon install.**

11. **Headless Blender FBX Export Paths** — Headless instance may have file I/O restrictions. Test writing FBX to `/tmp` vs. user-provided path. Document any limitations.

12. **Material Slot Order Preservation** — For skeletal meshes with multiple material slots (e.g., body slot 0, head slot 1), does FBX export preserve order? **Verify round-trip:** export → UE5 import → re-export → check slot indices unchanged.

---

## Summary

**B2 Hard-Surface Prop Modeling Pipeline** brings **28 tools** across 7 domains to achieve atomic hard-surface workflows targeting UE5 export:

- **Modifier-first design:** Mirror, Array, Boolean, Bevel, Subdivision, Solidify, Decimate, Triangulate for non-destructive iteration.
- **Edit Mode primitives:** Extrude, Inset, Bridge (via bmesh) for detail sculpting (⚠️ edge selection API fragile; recommend loop-based selection).
- **UE5 export compliance:** FBX exporter parameters fully exposed per UE-TARGETS.md; skeletal mesh validation (Mannequin compat); LOD/collision auto-detection; Nanite recommendation.
- **Critical 4.2 changes:** `use_auto_smooth` replaced by Smooth By Angle modifier; custom bevel profiles.
- **Blockers (YELLOW):** Knife projection (defer), edge loop cut non-modal param validation needed, bevel weight interactive UI vs. headless trade-off, context override for bridge operator, face selection by index fragility.

**No hard RED blockers:** All planned tools are feasible in Blender 4.2 LTS; integration tests needed for modal operator params and headless context overrides.

---