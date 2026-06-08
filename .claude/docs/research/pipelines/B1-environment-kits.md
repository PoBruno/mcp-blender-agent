Perfect. I now have comprehensive knowledge of the project structure, MCP contracts, UE5 export targets, and Blender 4.2+ APIs. Let me compile a detailed research report for the B1 domain.

---

# B1 Research Report: Modular Environment Kits Pipeline for Unreal Engine 5

## 1. Canonical Workflow (Ordered Steps)

### Step 1: Create blockout primitives on snap grid

**What the artist does:**
Create low-poly placeholder geometry (cubes, planes, cylinders) snapped to a grid (0.1m / 0.5m / 1m increments) to lay out the level topology and volumetric blocking.

**The Blender API to invoke:**
- **Primary:** `bpy.ops.mesh.primitive_cube_add(size, location, rotation)` (and cylinder, plane variants)
- **Alternative data-only:** `bpy.data.meshes.new()` + `bpy.data.objects.new()` + link to collection
- **Snap setup:** `bpy.context.scene.tool_settings.use_snap = True`; `tool_settings.snap_element = 'GRID'`; `tool_settings.snap_target = 'CLOSEST'`; `scene.unit_settings.scale_length = 1.0` (1m = 1 grid unit)

**Context-override needs:**
Yes — primitive operators require a 3D Viewport area context. Wrap: `bpy.context.temp_override(area=..., region=...)` where area.type is `'VIEW_3D'`.

**Mode requirements:**
Object Mode only.

**Modal? (Y/N):**
N — the operators are non-modal; size, location, rotation are parameters.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.mesh.html#bpy.ops.mesh.primitive_cube_add

---

### Step 2: Author modular static meshes

**What the artist does:**
Create individual small meshes (walls, floors, doors, stairs, trim) that compose the kit. Each piece is authored with:
- Consistent pivot at a snap corner (not geometric center)
- Applied transforms (Location 0, Rotation 0, Scale 1)
- Clean topology (triangulated or quads)
- Material slots ordered by intent (base surface first)
- Optional collision proxies (`UCX_*` child meshes)

**The Blender API to invoke:**
- **Data mesh inspection:** `bpy.data.objects[name].data` (mesh object)
- **Mesh mutation:** `bmesh` module for topology edits; `bpy.ops.mesh.quads_convert_to_tris()` for triangulation
- **Transform apply:** `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)`
- **Collision mesh creation:** `bpy.ops.mesh.primitive_cube_add()` to create `UCX_*` collision proxy, then reparent as child
- **Origin/pivot reset:** `bpy.ops.object.origin_set(type='ORIGIN_CURSOR')` (with cursor at snap corner)

**Context-override needs:**
Yes — mesh editing ops and origin_set require 3D Viewport context.

**Mode requirements:**
Object Mode for transforms; Edit Mode for mesh topology edits (wrap with `with_mode(obj, 'EDIT', lambda: ...)`).

**Modal? (Y/N):**
N — except for interactive pivot placement (agent should calculate target position, not interact).

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.origin_set
https://docs.blender.org/api/current/bpy.ops.mesh.html#bpy.ops.mesh.quads_convert_to_tris

---

### Step 3: Assign materials and validate slot order

**What the artist does:**
Slot materials per mesh part (body, trim, detail). Material slot order is critical for UE import (slot 0 = primary, etc.). Validate that each slot has a material assigned.

**The Blender API to invoke:**
- **Slot mutation:** `obj.material_slots[i]` is read-only (access via `obj.data.materials`); to add slot: `bpy.ops.object.material_slot_add()`
- **Slot assignment:** `bpy.ops.object.material_slot_assign()` (requires Edit Mode on selected faces)
- **Material creation:** `bpy.data.materials.new(name="Material")`
- **Assign to object:** `obj.data.materials.append(material)` or index-assign `obj.data.materials[0] = material`
- **Validate:** iterate `obj.data.materials` and check for None/emptiness

**Context-override needs:**
Yes — material_slot_assign requires 3D View context.

**Mode requirements:**
Edit Mode for face-group assignment; Object Mode for slot management.

**Modal? (Y/N):**
N.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.material_slot_add
https://docs.blender.org/api/current/bpy.types.Object.html#bpy.types.Object.material_slots

---

### Step 4: Create Linked Duplicates or Collection Instances for population

**What the artist does:**
Populate the level with hundreds of instances of kit meshes. Two strategies:
  1. **Linked Duplicates** — `obj_duplicate(linked=True)` — shares mesh data; each instance can have independent transform/material override.
  2. **Collection Instances** — whole collection as single instancer object; lighter in memory; used for large modular walls/rooms.

**The Blender API to invoke:**
- **Linked Duplicate:** `bpy.ops.object.duplicate(linked=True)` (requires selected object; produces new object in collection)
- **Collection Instance:** `bpy.ops.object.collection_instance_add(name='CollectionName', collection='CollectionName', location=(x,y,z))`
- **Collection creation:** `bpy.data.collections.new(name)` then link to context scene: `bpy.context.scene.collection.children.link(new_collection)`
- **Link objects to collection:** `collection.objects.link(obj)` (note: objects stay in their original collection; can be in multiple)

**Context-override needs:**
Yes — duplicate and collection_instance_add require 3D View context.

**Mode requirements:**
Object Mode.

**Modal? (Y/N):**
N.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.duplicate
https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.collection_instance_add

---

### Step 5: Position instances on grid using transforms

**What the artist does:**
Set instance locations, rotations, scales snapped to grid to align with neighboring pieces. Use viewport snap or direct coordinate assignment.

**The Blender API to invoke:**
- **Data transform:** `obj.location = (x, y, z)` (direct assignment; immediate, no undo unless wrapped in undo_push)
- **Data rotation:** `obj.rotation_euler = (rx, ry, rz)` or `obj.rotation_quaternion = (qw, qx, qy, qz)`
- **Data scale:** `obj.scale = (sx, sy, sz)`
- **Operator (modal-capable):** `bpy.ops.transform.translate(value=(dx, dy, dz), orient_type='GLOBAL')` (non-modal if value is provided)
- **Snap helper:** pre-calculate grid-snapped coordinates; feed to location assignment

**Context-override needs:**
Yes if using bpy.ops.transform; no if using data assignment (preferred for programmatic placement).

**Mode requirements:**
Object Mode.

**Modal? (Y/N):**
N if using data assignment (preferred); Y if using interactive bpy.ops.transform (avoid for headless).

**Doc URL:**
https://docs.blender.org/api/current/bpy.types.Object.html#bpy.types.Object.location
https://docs.blender.org/api/current/bpy.ops.transform.html#bpy.ops.transform.translate

---

### Step 6: Apply decals via projected geometry or shader (Geometry Nodes / Compositor)

**What the artist does:**
Project damage, signage, dirt onto level geometry. Options:
  1. **Projected empties with decal materials** — create an empty, position, assign a projector material, use data inheritance.
  2. **Geometry Nodes scatter + deform** — use GN point scatter + object instance for decal placement.

**The Blender API to invoke:**
- **Approach 1 (simple projection, not practical headless):** `bpy.ops.object.empty_add(type='PLAIN_AXES', location=..., rotation=...)` + material with World Projection; requires manual shader setup.
- **Approach 2 (Geometry Nodes, recommended):** Create a Geometry Node modifier on the target mesh: `bpy.ops.object.modifier_add(type='NODES')`, then read/write node tree inputs via `obj.modifiers['GeometryNodes'].node_group.inputs[...]`
- **Limitation:** GN node graph editing is via `bpy.data.node_groups` (complex); more practical to pre-author the GN graph in the source `.blend` and use as a template.

**Context-override needs:**
Empty add requires 3D View; modifier operations do not.

**Mode requirements:**
Object Mode.

**Modal? (Y/N):**
N (but decal material projection is visual feedback — agent cannot see result headless).

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.empty_add
https://docs.blender.org/api/current/bpy.types.GeometryNodeTree.html

---

### Step 7: UV layout & trim sheet assignment

**What the artist does:**
Pack UVs for modular pieces into a shared trim texture (atlas). Ensure consistent texel density across all pieces.

**The Blender API to invoke:**
- **UV access:** `obj.data.uv_layers[name]` → loop layer: `obj.data.uv_layers['UVMap'].data[i].uv` (read-only in Python; edit via bmesh)
- **UV editing (via bmesh):** enter Edit Mode, use `bmesh.from_edit_mesh()`, modify `loop.uv`, sync back: `bmesh.update_edit_mesh(mesh)`
- **Pack UVs operator (modal-capable):** `bpy.ops.uv.pack(self, context, ...)` — deprecated in 4.0+; modern workflow uses `bpy.ops.uv.smart_project()` or `bpy.ops.uv.unwrap()`
- **Texel density audit:** measure pixel area of UV bounds vs mesh bounds; validate ratio is consistent (1 pixel ≈ N cm on surface)

**Context-override needs:**
Yes for UV pack/unwrap operators (require UV Editor context, which is tricky headless). Prefer bmesh data access.

**Mode requirements:**
Edit Mode for UV operations.

**Modal? (Y/N):**
Y for interactive UV packing (red blocker for headless). Data-only assessment via bmesh is non-modal.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.uv.html
https://docs.blender.org/api/current/bmesh.html (uv_layers under bmesh.types.BMUVLoop)

---

### Step 8: Organize scene with View Layers & Collections

**What the artist does:**
Group kit meshes by room/zone into Collections. Create View Layers for per-layer export (e.g., "Base_Meshes", "Collision", "LODs").

**The Blender API to invoke:**
- **Collection creation:** `bpy.data.collections.new(name)`
- **Collection nesting:** `parent_collection.children.link(child_collection)`
- **Link object to collection:** `collection.objects.link(obj)`
- **Remove object from collection:** `collection.objects.unlink(obj)`
- **Create View Layer:** `bpy.context.scene.view_layers.new(name)` (returns ViewLayer)
- **Configure View Layer visibility:** `layer.use_pass_*` flags, `layer.objects[name].hide_get()` / `hide_set()`
- **Query active scene/layer:** `bpy.context.scene`, `bpy.context.view_layer`

**Context-override needs:**
No — all data operations.

**Mode requirements:**
Object Mode (View Layer context is scene-level).

**Modal? (Y/N):**
N.

**Doc URL:**
https://docs.blender.org/api/current/bpy.types.Collection.html
https://docs.blender.org/api/current/bpy.types.Scene.html#bpy.types.Scene.view_layers

---

### Step 9: Library Link modular kits from external `.blend` files

**What the artist does:**
Link (not append) master kit meshes from a central asset library `.blend`. Changes to the library are reflected everywhere linked.

**The Blender API to invoke:**
- **Link operator:** `bpy.ops.wm.link(filepath='path/to/asset.blend', directory='Object/', filename='MeshName', link=True, instance_collections=False)`
  - `directory` = subfolder within `.blend` (e.g., `'Object/'` for objects, `'Collection/'` for collections)
  - `filename` = exact data-block name to link
  - `link=True` means link (read-only); `link=False` means append (make local copy)
- **Alternative data approach:** `bpy.data.libraries.load('path/to/asset.blend', link=True, relative=False)` → context manager pattern (advanced)
- **Override library:** `bpy.ops.object.make_override_library(collection=...)` (for library overrides; UE5 doesn't use this pattern, but Blender 4.0+ supports it)

**Context-override needs:**
Yes — wm.link requires file browser context (very headless-unfriendly; typically requires the filepath be provided).

**Mode requirements:**
Object Mode (scene-level operation).

**Modal? (Y/N):**
Y for interactive file selection; N if filepath is hardcoded.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.wm.html#bpy.ops.wm.link

---

### Step 10: Add collision proxies (`UCX_*` empties / mesh children)

**What the artist does:**
Create collision shapes for each modular piece (convex hulls, boxes, capsules). Name them `UCX_MeshName`, `UBX_MeshName`, etc. per UE convention.

**The Blender API to invoke:**
- **Create box collision:** `bpy.ops.mesh.primitive_cube_add(size=..., location=..., name='UCX_MyMesh')`
- **Create convex hull from mesh:** Select mesh faces → `bpy.ops.mesh.convex_hull(use_existing_faces=False, delete_unused=True)` → duplicate result as child with `UCX_*` naming
- **Parent collision to mesh:** Create collision mesh as sibling, then parent: `collision_obj.parent = mesh_obj`; set `collision_obj.parent_bone` if needed (mesh-only for static)
- **Mark as collision:** No special Blender marker; naming convention is used by UE FBX importer

**Context-override needs:**
Yes for primitive add; no for parenting.

**Mode requirements:**
Object Mode.

**Modal? (Y/N):**
N.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.mesh.html#bpy.ops.mesh.primitive_cube_add
https://docs.blender.org/api/current/bpy.ops.mesh.html#bpy.ops.mesh.convex_hull

---

### Step 11: LOD creation (optional, for high-poly kits)

**What the artist does:**
For complex meshes, create LOD0 (highest detail), LOD1 (decimated), LOD2 (very low poly). Group under a parent empty named `LOD_MeshName`.

**The Blender API to invoke:**
- **Decimate modifier:** `bpy.ops.object.modifier_add(type='DECIMATE')` → `modifier.ratio = 0.5` (50% of vertices)
- **Apply modifier:** `bpy.ops.object.modifier_apply(modifier='Decimate')`
- **Create LOD hierarchy:** Parent LOD1, LOD2 under `LOD_*` empty: `lod_group = bpy.data.objects.new('LOD_MyMesh', None)` → link to collection → set children's parent
- **Alternative via Geometry Nodes:** Use GN LOD switch node (more advanced)

**Context-override needs:**
Yes for object creation.

**Mode requirements:**
Object Mode.

**Modal? (Y/N):**
N.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.modifier_add
https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.modifier_apply

---

### Step 12: Batch export FBX with UE5-compatible settings

**What the artist does:**
Export each mesh (or per-collection) as a separate FBX file with standardized naming (`SM_`, `UCX_` prefixes), correct axis mapping, scale, and collision detection.

**The Blender API to invoke:**
- **Select for export:** `obj.select_set(True)` on target objects
- **Export operator:** `bpy.ops.export_scene.fbx(filepath='...', use_selection=True, use_mesh_modifiers=True, mesh_smooth_type='FACE', bake_anim=False, axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True, use_triangles=True, object_types={'MESH', 'EMPTY'}, add_leaf_bones=False, use_armature_deform_only=False, use_mesh_edges=False, use_tspace=True, path_mode='COPY', embed_textures=False)`
- **Frame range for animation:** Set `scene.frame_start`, `scene.frame_end` before export
- **Per-collection export loop:** iterate `bpy.data.collections`, select members, export to `f"{collection.name}.fbx"`

**Context-override needs:**
Yes — export requires file browser / context (typically path is provided, but still needs active scene context).

**Mode requirements:**
Object Mode.

**Modal? (Y/N):**
N if filepath is provided.

**Doc URL:**
https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.fbx
https://docs.blender.org/api/4.2/en/manual/files/import_export/index.html (UE-specific export guide)

---

## 2. Proposed Tools (Catalog)

### `scene_create`
- **Group:** `scene`
- **Description:** Create a new scene with unit settings configured for modular kit authoring (metric, 1m grid).
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `sceneName: z.string().describe("Name of the scene to create")`
  - `unitScale: z.number().optional().describe("Unit scale in meters (default 1.0)")`
- **Output payload (data):** `{ sceneName: string }`
- **refs (IDs for chaining):** `{ sceneName }`
- **nextSteps:** [`collection_create`, `viewport_set_shading`]
- **errorCodes:** `SCENE_EXISTS` (name collision)
- **Python handler outline:**
  ```python
  def main():
    if scene_name in bpy.data.scenes:
      raise HandlerError("SCENE_EXISTS", f"Scene {scene_name!r} already exists")
    scene = bpy.data.scenes.new(scene_name)
    scene.unit_settings.length_unit = 'METERS'
    scene.unit_settings.scale_length = unit_scale
    bpy.context.window.scene = scene
    bpy.ops.ed.undo_push(message=f"Create scene {scene_name!r}")
    return {"scene_name": scene.name}
  ```
- **Related tools — upstream producers:** (none)
- **Related tools — downstream consumers:** `collection_create`, `object_add_blockout`, `viewport_set_shading`
- **Test cases:** Happy path (new scene); error on duplicate name; verify unit_settings applied
- **Status:** green

---

### `collection_create`
- **Group:** `collection`
- **Description:** Create a collection for organizing modular kit meshes (e.g., "Walls", "Floors", "Trim"). Returns collection name for child linking.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `collectionName: z.string().describe("Name of the collection")`
  - `parentCollectionName: z.string().optional().describe("Parent collection name; if omitted, add to scene root")`
- **Output payload (data):** `{ collectionName: string }`
- **refs (IDs for chaining):** `{ collectionName }`
- **nextSteps:** [`object_add_blockout`, `object_link_to_collection`]
- **errorCodes:** `COLLECTION_EXISTS`, `PARENT_COLLECTION_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    if collection_name in bpy.data.collections:
      raise HandlerError("COLLECTION_EXISTS", f"Collection {collection_name!r} exists")
    coll = bpy.data.collections.new(collection_name)
    if parent_name:
      parent = bpy.data.collections.get(parent_name)
      if not parent:
        raise HandlerError("PARENT_NOT_FOUND", f"Parent {parent_name!r} not found")
      parent.children.link(coll)
    else:
      bpy.context.scene.collection.children.link(coll)
    bpy.ops.ed.undo_push(message=f"Create collection {collection_name!r}")
    return {"collection_name": coll.name}
  ```
- **Related tools — upstream producers:** `scene_create`
- **Related tools — downstream consumers:** `object_add_blockout`, `object_link_to_collection`, `export_fbx_collection_batch`
- **Test cases:** Happy path; duplicate name error; missing parent error; verify collection parent/child chain
- **Status:** green

---

### `object_add_blockout`
- **Group:** `object`
- **Description:** Add a blockout primitive (cube, plane, cylinder) on the grid at the specified location. Snap-friendly for level layout.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Name of the blockout object")`
  - `primitiveType: z.enum(['CUBE', 'PLANE', 'CYLINDER']).describe("Primitive shape")`
  - `size: z.number().optional().describe("Size of the primitive in meters (default 1.0)")`
  - `location: z.tuple([z.number(), z.number(), z.number()]).optional().describe("World location (snap-grid aligned, default origin)")`
  - `collectionName: z.string().optional().describe("Collection to add object to")`
- **Output payload (data):** `{ objectName: string, location: [number, number, number], boundingBox: {min: [number, number, number], max: [number, number, number]} }`
- **refs (IDs for chaining):** `{ objectName }`
- **nextSteps:** [`object_set_transform`, `object_duplicate`, `material_assign_slot`]
- **errorCodes:** `OBJECT_EXISTS`, `COLLECTION_NOT_FOUND`, `INVALID_PRIMITIVE_TYPE`
- **Python handler outline:**
  ```python
  def main():
    if object_name in bpy.data.objects:
      raise HandlerError("OBJECT_EXISTS", f"Object {object_name!r} exists")
    
    with bpy.context.temp_override(area=get_3d_view_area()):
      if primitive_type == 'CUBE':
        bpy.ops.mesh.primitive_cube_add(size=size, location=tuple(location or [0, 0, 0]))
      elif primitive_type == 'PLANE':
        bpy.ops.mesh.primitive_plane_add(size=size, location=tuple(location or [0, 0, 0]))
      elif primitive_type == 'CYLINDER':
        bpy.ops.mesh.primitive_cylinder_add(radius=size*0.5, depth=size, location=tuple(location or [0, 0, 0]))
    
    obj = bpy.context.active_object
    obj.name = object_name
    if collection_name:
      coll = bpy.data.collections.get(collection_name)
      if not coll:
        raise HandlerError("COLLECTION_NOT_FOUND", f"Collection {collection_name!r} not found")
      coll.objects.link(obj)
      bpy.context.scene.collection.objects.unlink(obj)
    
    bbox_min = [min(v.co[i] for v in obj.data.vertices) for i in range(3)]
    bbox_max = [max(v.co[i] for v in obj.data.vertices) for i in range(3)]
    bpy.ops.ed.undo_push(message=f"Add blockout {object_name!r}")
    return {"object_name": obj.name, "location": list(obj.location), "bounding_box": {"min": bbox_min, "max": bbox_max}}
  ```
- **Related tools — upstream producers:** `collection_create`
- **Related tools — downstream consumers:** `object_set_transform`, `object_duplicate`, `material_assign_slot`, `export_fbx_static`
- **Test cases:** Happy path (cube on grid); all primitive types; duplicate name error; collection not found error; bounding box calculation
- **Status:** yellow (context-override for 3D View may be fragile in headless; feasible but needs robust area detection)

---

### `object_set_transform`
- **Group:** `object`
- **Description:** Set object location, rotation, scale with grid snapping. Snap resolution is scene-configurable.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Object to transform")`
  - `location: z.tuple([z.number(), z.number(), z.number()]).optional().describe("World location")`
  - `rotation: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Rotation in Euler angles (radians)")`
  - `scale: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Scale factors")`
  - `snapGridSize: z.number().optional().describe("Snap to grid (0.1 / 0.5 / 1.0 meters; default 0 = no snap)")`
- **Output payload (data):** `{ objectName: string, location: [number, number, number], rotation: [number, number, number], scale: [number, number, number] }`
- **refs (IDs for chaining):** `{ objectName }`
- **nextSteps:** [`object_set_transform` (chain for array placement), `export_fbx_static`]
- **errorCodes:** `OBJECT_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(object_name)
    if not obj:
      raise HandlerError("OBJECT_NOT_FOUND", f"Object {object_name!r} not found")
    
    if location:
      loc = list(location)
      if snap_grid_size > 0:
        loc = [round(c / snap_grid_size) * snap_grid_size for c in loc]
      obj.location = loc
    
    if rotation:
      obj.rotation_euler = rotation
    
    if scale:
      obj.scale = scale
    
    bpy.ops.ed.undo_push(message=f"Set transform on {object_name!r}")
    return {"object_name": obj.name, "location": list(obj.location), "rotation": list(obj.rotation_euler), "scale": list(obj.scale)}
  ```
- **Related tools — upstream producers:** `object_add_blockout`
- **Related tools — downstream consumers:** `object_duplicate`, `export_fbx_static`
- **Test cases:** Happy path; grid snap (0.1m, 0.5m, 1.0m); partial updates (location only, rotation only, etc.); object not found
- **Status:** green

---

### `object_duplicate_linked`
- **Group:** `object`
- **Description:** Create a linked duplicate of an object (shares mesh data; independent transforms). Used for populating kit instances.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Object to duplicate")`
  - `newName: z.string().optional().describe("Name of duplicate; auto-generated if omitted")`
  - `location: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Location of duplicate; default is same as original")`
  - `collectionName: z.string().optional().describe("Collection to add duplicate to")`
- **Output payload (data):** `{ objectName: string, originalObjectName: string, dataShared: boolean }`
- **refs (IDs for chaining):** `{ objectName }`
- **nextSteps:** [`object_set_transform`, `object_duplicate_linked` (for array), `export_fbx_static`]
- **errorCodes:** `OBJECT_NOT_FOUND`, `COLLECTION_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    orig = bpy.data.objects.get(object_name)
    if not orig:
      raise HandlerError("OBJECT_NOT_FOUND", f"Object {object_name!r} not found")
    
    with bpy.context.temp_override(area=get_3d_view_area()):
      bpy.context.view_layer.objects.active = orig
      orig.select_set(True)
      bpy.ops.object.duplicate(linked=True)
    
    dup = bpy.context.active_object
    dup.name = new_name or f"{orig.name}.001"
    if location:
      dup.location = location
    
    if collection_name:
      coll = bpy.data.collections.get(collection_name)
      if not coll:
        raise HandlerError("COLLECTION_NOT_FOUND", f"Collection {collection_name!r} not found")
      coll.objects.link(dup)
      bpy.context.scene.collection.objects.unlink(dup)
    
    bpy.ops.ed.undo_push(message=f"Duplicate linked {object_name!r} -> {dup.name!r}")
    return {"object_name": dup.name, "original_object_name": orig.name, "data_shared": True}
  ```
- **Related tools — upstream producers:** `object_add_blockout`, `mesh_create_kit_piece`
- **Related tools — downstream consumers:** `object_set_transform`, `export_fbx_static` (batch)
- **Test cases:** Happy path; linked data verification; location offset; collection placement; object not found
- **Status:** yellow (context-override needed)

---

### `mesh_set_origin_to_snap_corner`
- **Group:** `mesh`
- **Description:** Set the origin/pivot of a mesh to a specified snap corner (0.5m offset for modular alignment). Critical for UE5 modular kit snapping.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Mesh object to adjust")`
  - `corner: z.enum(['MIN_XYZ', 'MAX_XYZ', 'CENTER']).optional().describe("Snap corner (default MIN_XYZ for grid origin)")`
- **Output payload (data):** `{ objectName: string, originWorldPosition: [number, number, number] }`
- **refs (IDs for chaining):** `{ objectName }`
- **nextSteps:** [`object_set_transform`, `export_fbx_static`]
- **errorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(object_name)
    if not obj:
      raise HandlerError("OBJECT_NOT_FOUND", f"Object {object_name!r} not found")
    if obj.type != 'MESH':
      raise HandlerError("OBJECT_NOT_MESH", f"Object {object_name!r} is not a mesh")
    
    mesh = obj.data
    vertices = [v.co for v in mesh.vertices]
    if corner == 'MIN_XYZ':
      corner_pos = [min(v[i] for v in vertices) for i in range(3)]
    elif corner == 'MAX_XYZ':
      corner_pos = [max(v[i] for v in vertices) for i in range(3)]
    elif corner == 'CENTER':
      center = [(max(v[i] for v in vertices) + min(v[i] for v in vertices)) / 2 for i in range(3)]
      corner_pos = center
    
    offset = mathutils.Vector(corner_pos) - mathutils.Vector(obj.location)
    for v in mesh.vertices:
      v.co -= offset
    obj.location = mathutils.Vector(obj.location) + offset
    
    bpy.ops.ed.undo_push(message=f"Set origin {object_name!r} to {corner}")
    return {"object_name": obj.name, "origin_world_position": list(obj.location)}
  ```
- **Related tools — upstream producers:** `mesh_create_kit_piece`, `import_fbx_static`
- **Related tools — downstream consumers:** `export_fbx_static`
- **Test cases:** Happy path (MIN_XYZ, MAX_XYZ, CENTER); not mesh error; verify world position after offset
- **Status:** green

---

### `collision_add_convex_hull`
- **Group:** `collision`
- **Description:** Create a convex collision mesh (`UCX_*` named child) from the object's mesh geometry.
- **Composite or primitive:** Composite (creates & parents collision child)
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Mesh object to generate collision for")`
  - `collisionName: z.string().optional().describe("Name of collision child (default UCX_<objectName>)")`
- **Output payload (data):** `{ objectName: string, collisionName: string }`
- **refs (IDs for chaining):** `{ collisionName, objectName }`
- **nextSteps:** [`collision_add_convex_hull` (for LODs), `export_fbx_static`]
- **errorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `COLLISION_EXISTS`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(object_name)
    if not obj:
      raise HandlerError("OBJECT_NOT_FOUND", f"Object {object_name!r} not found")
    if obj.type != 'MESH':
      raise HandlerError("OBJECT_NOT_MESH", f"Object {object_name!r} is not a mesh")
    
    coll_name = collision_name or f"UCX_{object_name}"
    if coll_name in bpy.data.objects:
      raise HandlerError("COLLISION_EXISTS", f"Collision {coll_name!r} already exists")
    
    with bpy.context.temp_override(area=get_3d_view_area()):
      obj.select_set(True)
      bpy.context.view_layer.objects.active = obj
      bpy.ops.object.mode_set(mode='EDIT')
      bpy.ops.mesh.select_all(action='SELECT')
      bpy.ops.mesh.convex_hull(use_existing_faces=False, delete_unused=True)
      bpy.ops.object.mode_set(mode='OBJECT')
    
    coll_mesh = bpy.context.active_object
    coll_mesh.name = coll_name
    coll_mesh.parent = obj
    coll_mesh.parent_type = 'OBJECT'
    bpy.context.scene.collection.objects.unlink(coll_mesh)
    
    bpy.ops.ed.undo_push(message=f"Add collision {coll_name!r} to {object_name!r}")
    return {"object_name": obj.name, "collision_name": coll_mesh.name}
  ```
- **Related tools — upstream producers:** `mesh_create_kit_piece`, `object_add_blockout`
- **Related tools — downstream consumers:** `export_fbx_static`
- **Test cases:** Happy path; not mesh error; collision exists error; verify parent-child relationship; convex hull generation
- **Status:** yellow (requires mode switch + Edit Mode context; feasible but needs frame context handling)

---

### `collection_instance_create`
- **Group:** `collection`
- **Description:** Create a collection instance (single lightweight object referencing a collection). Used for large modular structures.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `collectionName: z.string().describe("Collection to instance")`
  - `instanceName: z.string().optional().describe("Name of instance object; default <collectionName>_Instance")`
  - `location: z.tuple([z.number(), z.number(), z.number()]).optional().describe("World location of instance")`
- **Output payload (data):** `{ objectName: string, collectionName: string }`
- **refs (IDs for chaining):** `{ objectName }`
- **nextSteps:** [`object_set_transform`, `collection_instance_create` (for array), `export_fbx_collection_batch`]
- **errorCodes:** `COLLECTION_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    coll = bpy.data.collections.get(collection_name)
    if not coll:
      raise HandlerError("COLLECTION_NOT_FOUND", f"Collection {collection_name!r} not found")
    
    with bpy.context.temp_override(area=get_3d_view_area()):
      bpy.ops.object.collection_instance_add(
        name=instance_name or f"{collection_name}_Instance",
        collection=collection_name,
        location=tuple(location or [0, 0, 0])
      )
    
    inst = bpy.context.active_object
    bpy.ops.ed.undo_push(message=f"Create collection instance {inst.name!r} from {collection_name!r}")
    return {"object_name": inst.name, "collection_name": collection_name}
  ```
- **Related tools — upstream producers:** `collection_create`, `object_link_to_collection`
- **Related tools — downstream consumers:** `object_set_transform`, `export_fbx_collection_batch`
- **Test cases:** Happy path; collection not found; instance count verification
- **Status:** yellow (3D View context needed)

---

### `material_create_procedural_grid`
- **Group:** `material`
- **Description:** Create a procedural prototype/debug grid material (checker pattern). Used for initial blockout visualization in Lyra style.
- **Composite or primitive:** Composite (creates material + shader nodes)
- **Inputs (Zod sketch):**
  - `materialName: z.string().describe("Name of material")`
  - `gridScale: z.number().optional().describe("Grid size in UV space (default 1.0)")`
  - `gridColor1: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional().describe("Primary color RGBA (default white)")`
  - `gridColor2: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional().describe("Secondary color RGBA (default gray)")`
- **Output payload (data):** `{ materialName: string }`
- **refs (IDs for chaining):** `{ materialName }`
- **nextSteps:** [`material_assign_slot`]
- **errorCodes:** `MATERIAL_EXISTS`
- **Python handler outline:**
  ```python
  def main():
    if material_name in bpy.data.materials:
      raise HandlerError("MATERIAL_EXISTS", f"Material {material_name!r} exists")
    
    mat = bpy.data.materials.new(material_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Checker texture → Principled BSDF → Material Output
    checker = nodes.new(type='ShaderNodeTexChecker')
    checker.inputs['Scale'].default_value = grid_scale
    checker.inputs['Color1'].default_value = grid_color1 or (1, 1, 1, 1)
    checker.inputs['Color2'].default_value = grid_color2 or (0.5, 0.5, 0.5, 1)
    
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1)
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(checker.outputs['Color'], principled.inputs['Base Color'])
    mat.node_tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    bpy.ops.ed.undo_push(message=f"Create material {material_name!r}")
    return {"material_name": mat.name}
  ```
- **Related tools — upstream producers:** (none)
- **Related tools — downstream consumers:** `material_assign_slot`
- **Test cases:** Happy path; material exists error; shader node tree creation & linking
- **Status:** green

---

### `material_assign_slot`
- **Group:** `material`
- **Description:** Assign a material to a specific material slot on an object.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Object to assign material to")`
  - `materialName: z.string().describe("Material to assign")`
  - `slotIndex: z.number().optional().describe("Material slot index (default 0)")`
- **Output payload (data):** `{ objectName: string, materialName: string, slotIndex: number }`
- **refs (IDs for chaining):** `{ objectName, materialName }`
- **nextSteps:** [`material_assign_slot` (chain for multi-slot), `export_fbx_static`]
- **errorCodes:** `OBJECT_NOT_FOUND`, `MATERIAL_NOT_FOUND`, `SLOT_INDEX_OUT_OF_RANGE`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(object_name)
    if not obj:
      raise HandlerError("OBJECT_NOT_FOUND", f"Object {object_name!r} not found")
    if not obj.data:
      raise HandlerError("OBJECT_NOT_MESH", f"Object {object_name!r} has no data")
    
    mat = bpy.data.materials.get(material_name)
    if not mat:
      raise HandlerError("MATERIAL_NOT_FOUND", f"Material {material_name!r} not found")
    
    if slot_index >= len(obj.data.materials):
      raise HandlerError("SLOT_INDEX_OUT_OF_RANGE", f"Slot {slot_index} out of range [0, {len(obj.data.materials)-1}]")
    
    obj.data.materials[slot_index] = mat
    bpy.ops.ed.undo_push(message=f"Assign material {material_name!r} to {object_name!r}[{slot_index}]")
    return {"object_name": obj.name, "material_name": mat.name, "slot_index": slot_index}
  ```
- **Related tools — upstream producers:** `material_create_procedural_grid`, `material_create_principled_ue5`
- **Related tools — downstream consumers:** `export_fbx_static`
- **Test cases:** Happy path; object not found; material not found; slot index out of range
- **Status:** green

---

### `uv_unwrap_smart_project`
- **Group:** `uv`
- **Description:** Unwrap UVs using smart projection (angle-aware, seam-aware). Designed for modular kit pieces.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Mesh to unwrap")`
  - `angleLimit: z.number().optional().describe("Angle limit in degrees (default 66)")`
  - `islandMargin: z.number().optional().describe("Island margin in UV space (default 0.02)")`
- **Output payload (data):** `{ objectName: string, uvMapName: string, islandCount: number }`
- **refs (IDs for chaining):** `{ objectName }`
- **nextSteps:** [`export_fbx_static`]
- **errorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `NO_UV_LAYER`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(object_name)
    if not obj:
      raise HandlerError("OBJECT_NOT_FOUND", f"Object {object_name!r} not found")
    if obj.type != 'MESH':
      raise HandlerError("OBJECT_NOT_MESH", f"Object {object_name!r} is not a mesh")
    
    if len(obj.data.uv_layers) == 0:
      obj.data.uv_layers.new(name="UVMap")
    
    with bpy.context.temp_override(area=get_3d_view_area()):
      bpy.context.view_layer.objects.active = obj
      obj.select_set(True)
      bpy.ops.object.mode_set(mode='EDIT')
      bpy.ops.mesh.select_all(action='SELECT')
      bpy.ops.uv.smart_project(angle_limit=math.radians(angle_limit or 66), island_margin=island_margin or 0.02)
      bpy.ops.object.mode_set(mode='OBJECT')
    
    uv_layer = obj.data.uv_layers.active
    bpy.ops.ed.undo_push(message=f"Smart project UVs on {object_name!r}")
    return {"object_name": obj.name, "uv_map_name": uv_layer.name, "island_count": len(obj.data.polygons)}
  ```
- **Related tools — upstream producers:** `object_add_blockout`, `mesh_create_kit_piece`
- **Related tools — downstream consumers:** `export_fbx_static`
- **Test cases:** Happy path; object not found; not mesh; UV layer creation; angle limit application
- **Status:** yellow (modal operator in Edit Mode; requires context override)

---

### `export_fbx_static`
- **Group:** `export`
- **Description:** Export a static mesh with UE5-compatible settings (axis remap, scale, collision detection, triangulation).
- **Composite or primitive:** Composite (selects, applies modifiers, exports, cleans up)
- **Inputs (Zod sketch):**
  - `objectName: z.string().describe("Mesh object to export")`
  - `outputPath: z.string().describe("Output .fbx file path")`
  - `includeCollision: z.boolean().optional().describe("Include UCX_* children (default true)")`
  - `triangulateNgons: z.boolean().optional().describe("Triangulate before export (default true)")`
  - `globalScale: z.number().optional().describe("Global scale (default 1.0 for cm in UE; use 1.0 for Blender meters → 1cm)")`
- **Output payload (data):** `{ filePath: string, objectName: string, triangleCount: number, fileSize: number }`
- **refs (IDs for chaining):** (none)
- **nextSteps:** (file written; can import into UE5)
- **errorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `EXPORT_FAILED`, `FILE_WRITE_FAILED`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(object_name)
    if not obj:
      raise HandlerError("OBJECT_NOT_FOUND", f"Object {object_name!r} not found")
    if obj.type != 'MESH':
      raise HandlerError("OBJECT_NOT_MESH", f"Object {object_name!r} is not a mesh")
    
    # Triangulate if needed
    if triangulate_ngons:
      with bpy.context.temp_override(area=get_3d_view_area()):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Select object and children for export
    obj.select_set(True)
    if include_collision:
      for child in obj.children:
        if child.name.startswith('UCX_'):
          child.select_set(True)
    
    try:
      bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        object_types={'MESH', 'EMPTY'},
        mesh_smooth_type='FACE',
        use_mesh_modifiers=True,
        use_triangles=True,
        bake_anim=False,
        axis_forward='-Z',
        axis_up='Y',
        global_scale=global_scale or 1.0,
        apply_unit_scale=True,
        use_custom_props=True,
        add_leaf_bones=False,
        use_armature_deform_only=False,
        path_mode='COPY',
        embed_textures=False,
        use_tspace=True
      )
    except Exception as e:
      raise HandlerError("EXPORT_FAILED", str(e))
    
    tris = sum(len(obj.data.polygons) for f in obj.data.polygons if len(f.vertices) == 3)
    bpy.ops.ed.undo_push(message=f"Export FBX {object_name!r}")
    return {"file_path": output_path, "object_name": obj.name, "triangle_count": tris, "file_size": os.path.getsize(output_path)}
  ```
- **Related tools — upstream producers:** `object_add_blockout`, `mesh_create_kit_piece`, `collision_add_convex_hull`, `uv_unwrap_smart_project`, `material_assign_slot`
- **Related tools — downstream consumers:** (external: UE5 importer)
- **Test cases:** Happy path (export, file exists, valid FBX); not mesh; triangulation verification; collision inclusion; axis/scale verification
- **Status:** green

---

### `export_fbx_collection_batch`
- **Group:** `export`
- **Description:** Batch-export all mesh objects in a collection as separate FBX files (one file per object). Each file is UE5-compatible.
- **Composite or primitive:** Composite (loops, exports, applies naming convention)
- **Inputs (Zod sketch):**
  - `collectionName: z.string().describe("Collection to export")`
  - `outputDirPath: z.string().describe("Output directory path")`
  - `namingPrefix: z.string().optional().describe("Prefix for output files (e.g., 'SM_' for static meshes)")`
- **Output payload (data):** `{ collectionName: string, fileCount: number, exportedFiles: string[] }`
- **refs (IDs for chaining):** (none)
- **nextSteps:** (files written; can batch-import into UE5)
- **errorCodes:** `COLLECTION_NOT_FOUND`, `OUTPUT_DIR_NOT_FOUND`, `EXPORT_FAILED`
- **Python handler outline:**
  ```python
  def main():
    coll = bpy.data.collections.get(collection_name)
    if not coll:
      raise HandlerError("COLLECTION_NOT_FOUND", f"Collection {collection_name!r} not found")
    
    if not os.path.isdir(output_dir_path):
      raise HandlerError("OUTPUT_DIR_NOT_FOUND", f"Directory {output_dir_path!r} not found")
    
    exported_files = []
    for obj in coll.all_objects:
      if obj.type != 'MESH':
        continue
      
      file_name = f"{naming_prefix or 'SM_'}{obj.name}.fbx"
      file_path = os.path.join(output_dir_path, file_name)
      
      try:
        obj.select_set(True)
        bpy.ops.export_scene.fbx(
          filepath=file_path,
          use_selection=True,
          object_types={'MESH', 'EMPTY'},
          ... # (same params as export_fbx_static)
        )
        exported_files.append(file_path)
        obj.select_set(False)
      except Exception as e:
        raise HandlerError("EXPORT_FAILED", f"Failed to export {obj.name}: {str(e)}")
    
    bpy.ops.ed.undo_push(message=f"Batch export collection {collection_name!r} ({len(exported_files)} files)")
    return {"collection_name": collection_name, "file_count": len(exported_files), "exported_files": exported_files}
  ```
- **Related tools — upstream producers:** `collection_create`, `object_link_to_collection`, `export_fbx_static`
- **Related tools — downstream consumers:** (external: UE5 batch importer)
- **Test cases:** Happy path (N objects exported); collection not found; dir not found; verify all files created; naming prefix applied
- **Status:** green

---

### `scene_set_unit_scale_for_modular_kit`
- **Group:** `scene`
- **Description:** Configure scene units for modular kit authoring: metric, 1m grid, appropriate grid visualization.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `sceneName: z.string().describe("Scene to configure")`
  - `gridUnit: z.enum(['0.1', '0.5', '1.0']).optional().describe("Grid unit in meters (default '1.0')")`
- **Output payload (data):** `{ sceneName: string, unitSystem: string, gridUnit: string }`
- **refs (IDs for chaining):** `{ sceneName }`
- **nextSteps:** [`collection_create`]
- **errorCodes:** `SCENE_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    scene = bpy.data.scenes.get(scene_name)
    if not scene:
      raise HandlerError("SCENE_NOT_FOUND", f"Scene {scene_name!r} not found")
    
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'METERS'
    
    grid_float = float(grid_unit or '1.0')
    scene.grid_scale = grid_float
    
    bpy.ops.ed.undo_push(message=f"Configure scene {scene_name!r} for modular kit (grid {grid_unit}m)")
    return {"scene_name": scene.name, "unit_system": scene.unit_settings.system, "grid_unit": grid_unit or '1.0'}
  ```
- **Related tools — upstream producers:** `scene_create`
- **Related tools — downstream consumers:** `object_add_blockout`, `object_set_transform`
- **Test cases:** Happy path; all grid units (0.1, 0.5, 1.0); scene not found
- **Status:** green

---

### `view_layer_create_for_export`
- **Group:** `scene`
- **Description:** Create a View Layer (e.g., "Base_Meshes", "Collision") for organizing export passes. Enables per-layer batch export.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  - `sceneName: z.string().describe("Scene to add layer to")`
  - `layerName: z.string().describe("Name of new View Layer")`
  - `parentLayerName: z.string().optional().describe("Parent layer name (typically 'Master')")`
- **Output payload (data):** `{ sceneName: string, layerName: string }`
- **refs (IDs for chaining):** `{ layerName }`
- **nextSteps:** [`object_link_to_layer`]
- **errorCodes:** `SCENE_NOT_FOUND`, `PARENT_LAYER_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    scene = bpy.data.scenes.get(scene_name)
    if not scene:
      raise HandlerError("SCENE_NOT_FOUND", f"Scene {scene_name!r} not found")
    
    layer = scene.view_layers.new(layer_name)
    bpy.ops.ed.undo_push(message=f"Create View Layer {layer_name!r} in {scene_name!r}")
    return {"scene_name": scene.name, "layer_name": layer.name}
  ```
- **Related tools — upstream producers:** `scene_create`
- **Related tools — downstream consumers:** `export_fbx_collection_batch` (per-layer)
- **Test cases:** Happy path; scene not found; layer name uniqueness
- **Status:** green

---

## 3. Feasibility Verdict Table

| Step / Capability | Verdict | Notes |
|---|---|---|
| Blockout primitives on grid | green | `bpy.ops.mesh.primitive_*_add` fully exposed; grid snap via data + tool_settings; 3D View context override needed (feasible) |
| Modular kit authoring | green | Mesh editing via bmesh (non-modal); transform apply straightforward; collision proxy naming via convention (no Blender marker) |
| Material assignment | green | Material slot management data-only; no modal operators |
| Linked Duplicates | yellow | `bpy.ops.object.duplicate(linked=True)` requires 3D View context; feasible with area detection |
| Collection Instances | yellow | `bpy.ops.object.collection_instance_add` requires 3D View context; feasible with area detection |
| Grid snapping | green | Purely data-driven via pre-calculated snap math; no operators needed |
| Decal projection (simple) | red | Interactive shader setup or GN node editing both impractical for agent; workaround: use pre-authored GN graphs as templates and expose parameters |
| UV unwrapping (smart project) | yellow | `bpy.ops.uv.smart_project` requires UV Editor context; feasible in Edit Mode with context override; but interactive (Y if context obtained) |
| Trim sheet UV packing | red | Advanced layout via `bpy.ops.uv.pack` is modal-only in 4.2+; workaround: expose `island_margin` parameter to user, rely on smart_project + manual island reposition |
| LOD creation (decimation) | green | Modifier add/apply fully data-driven; mesh decimation is deterministic |
| Scene organization (Collections/Layers) | green | All data-only; no modal operators |
| Library linking | yellow | `bpy.ops.wm.link` modal for file selection; feasible if filepath is hardcoded; use `bpy.data.libraries.load(...)` as modern alternative (available in 4.0+) |
| Collision proxies (naming) | green | Mesh creation + naming convention; UE FBX importer recognizes `UCX_*` pattern |
| Batch export FBX (UE5 settings) | green | All FBX exporter parameters exposed and validated for UE5; no hidden operator limitations |
| Context-override for 3D View | yellow | Reliable area detection: loop `for area in bpy.context.screen.areas if area.type == 'VIEW_3D'`; headless (no screen) returns None (handle gracefully) |
| Modal operators (net) | yellow | Knife tool, sculpt brushes, paint mode = RED blockers; UV pack, smart project = YELLOW (require Edit/UV context); workaround: expose as pre-authored templates, parametrize non-modal alternatives |

---

## 4. Entity Types Touched (For the Type Graph)

- **Object** (type 'MESH', 'EMPTY') — mesh objects, empties (collisions, sockets, instances)
- **Mesh** — geometry data (vertices, edges, faces, UV layers)
- **Collection** — hierarchy for organizing kit pieces + instances
- **Material** — procedural debug grids, PBR for UE5 export
- **Image** — textures referenced by materials (embedded or external)
- **Scene** — unit settings, grid scale, frame range (for batch operations)
- **ViewLayer** — per-layer export organization
- **Modifier** — collisions stored as mesh children (no modifiers used directly in B1 scope)
- **GeometryNodeTree** (advanced) — decal scattering via GN (out of initial scope, template-based)
- **BlendData** — library data for linking external asset `.blend` files

---

## 5. Open Issues / Questions for the User

1. **Decal projection strategy:** Is shader-based (material projection) acceptable, or must the agent compute decal geometry? Geometry Nodes scatter is complex to author via API. **Recommendation:** expose pre-authored GN graph templates; user selects template, agent parametrizes.

2. **UV packing (trim sheets):** Modern `bpy.ops.uv.pack` is modal-only. Should the agent fallback to `smart_project` + manual island repositioning via bmesh? Or is a separate "trim sheet layout" tool out of scope for v1.0? **Recommendation:** v1.0 = smart_project only; trim sheet authoring deferred to Phase 2.

3. **Headless rendering in blockout phase:** Blockout artists want real-time preview. Does the agent need viewport screenshot capability, or is off-screen render sufficient for blocking review? **Recommendation:** add `viewport_screenshot` tool (read-only, no mutation) + `render_image` (Eevee/Cycles) for visual validation.

4. **Library Override vs Library Linking:** UE5 doesn't use Blender's Library Override system. Should the agent expose `bpy.ops.object.make_override_library`, or stick to pure linking (read-only)? **Recommendation:** v1.0 = linking only; overrides deferred.

5. **Collision types beyond convex:** Should `collision_add_*` support box (`UBX_*`), sphere (`USP_*`), capsule (`UCP_*`), or only convex hull for v1.0? **Recommendation:** v1.0 = convex hull + box (from primitives); capsule deferred.

6. **Grid snap fidelity:** What tolerance (epsilon) for grid snapping? Floating-point rounding errors can accumulate over 100+ placements. **Recommendation:** expose `snapTolerance: z.number().optional()` parameter (default 1e-4 meters).

7. **Batch export naming:** Should the agent sanitize object names for UE5 validity (no spaces, special chars)? Or assume the user provides clean names? **Recommendation:** normalize to `[A-Za-z0-9_]` per UE naming convention; warn on changes.

---

**End of Research Report**