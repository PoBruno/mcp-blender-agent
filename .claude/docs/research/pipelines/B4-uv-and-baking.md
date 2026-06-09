Based on my research across the project documentation, Blender 4.2+ API, and UE-TARGETS specifications, here is the comprehensive **B4 — UV mapping and texture baking** research report:

---

# B4 Research: UV mapping + texture baking for game assets (Blender 4.2 LTS)

**Status:** research-only — no implementation. Scope: Cycles + Eevee Next, PBR game-asset pipeline for UE5 FBX export, normal/roughness/metallic/AO/curvature bakes, multi-layer UV systems, UDIM support, cage objects, trim sheets.

**Citation method:** Blender 4.2 API reference; URLs where primary source.

---

## 1. Canonical workflow steps (artist pipeline)

The production UV + bake workflow for game assets (props, characters, modular kits) decomposes into these ordered operations. Each step maps to a Blender API path with specifics on context-override needs.

### 1.1 UV layer & map setup (non-destructive)

**Step:** Create or select UV layer(s). Game assets typically use:
- **UV0 (layer `UVMap` by default in Blender)** → base color, roughness, metallic, normal, emission (PBR channels).
- **UV1 (layer `UVMap_Lightmap` or custom name)** → lightmap bakes (rare in Lumen-default UE5; keep empty if not needed).
- **UV2 (layer `UVMap_Vertex_Color_Mask`)** → rarely used; vertex paint mask coords if needed.

**API path:**
- `bpy.data.meshes[mesh_name].uv_layers.new(name="UVMap")` → create UV layer.
- `bpy.data.meshes[mesh_name].uv_layers.active = uv_layers["UVMap"]` → set active (affects unwrap).
- Read: `[loop.uv for loop in mesh.loops if ...]` is the low-level access; operators prefer selection.

**Context-override:** None needed (data access).

**Blender 4.2 docs:** https://docs.blender.org/api/current/bpy.types.UVLoopData.html, https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/uv_texture_spaces.html

---

### 1.2 UV seams & edge marking (Edit Mode)

**Step:** Mark sharp edges as seams so unwrap can cut along them. Necessary before smart-unwrap / smart-project / follow-active.

**API path:** `bpy.ops.mesh.mark_seam()` (requires Edit Mode + edge selection).

**Context-override:** **YES**. Must enter Edit Mode via `bpy.context.temp_override(...)` with `object=obj` context active, then switch mode.

```python
def mark_seam(obj: bpy.types.Object):
    # obj is already selected & active
    with bpy.context.temp_override(object=obj):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.mark_seam()  # marks selected edges (must pre-select in 3D viewport or via script)
        bpy.ops.object.mode_set(mode='OBJECT')
```

**Alternate (data-driven):** Loop over mesh edges, set `edge.use_seam = True` for qualifying edges (requires knowing topology). Less flexible; operators are standard.

**Blender 4.2 docs:** https://docs.blender.org/api/current/bpy.ops.mesh.html#bpy.ops.mesh.mark_seam, https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/unwrapping/seams.html

---

### 1.3 UV unwrapping (Edit Mode, multiple algorithms)

Unwrap operates in Edit Mode on the currently-active UV layer. **Five main unwrap types:**

#### A. **`Unwrap` (angle-preserving)** — best for characters, organic

- API: `bpy.ops.uv.unwrap(method='ANGLE_BASED')`
- Requires seams (step 1.2).
- Context-override: **YES** (Edit Mode).
- Blender 4.2 docs: https://docs.blender.org/api/current/bpy.ops.uv.html#bpy.ops.uv.unwrap

#### B. **`Smart UV Project`** — automatic, cuts seams for you

- API: `bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.0)`
- **No seams needed** (ignores them). Auto-generates islands.
- Context-override: **YES** (Edit Mode).
- Parameters: `angle_limit` (default 66°), `island_margin` (padding before pack).
- Blender 4.2 docs: https://docs.blender.org/api/current/bpy.ops.uv.html#bpy.ops.uv.smart_project

#### C. **`Lightmap Pack`** — for lightmap UV1 generation

- API: `bpy.ops.uv.lightmap_pack(PREF_CONTEXT='SEL_FACES')`
- Packs islands densely (assumes no seams needed; auto-seams).
- **Warning:** rarely used in Lumen-default UE5 (lightmass baking is disabled by default).
- Context-override: **YES** (Edit Mode).
- Blender 4.2 docs: https://docs.blender.org/api/current/bpy.ops.uv.html#bpy.ops.uv.lightmap_pack

#### D. **`Follow Active Quads`** — quad-based, requires face selection

- API: `bpy.ops.uv.follow_active_quads(mode='LENGTH_AVERAGE')`
- Traces quads from a reference face. Good for grids / modular assets.
- Context-override: **YES** (Edit Mode).
- Blender 4.2 docs: https://docs.blender.org/api/current/bpy.ops.uv.html#bpy.ops.uv.follow_active_quads

#### E. **`Project from View` / `Cylinder / Cube / Sphere Project`** — procedural projection

- API: 
  - `bpy.ops.uv.project_from_view(orthographic=False)` 
  - `bpy.ops.uv.cylinder_project(...)`, `bpy.ops.uv.cube_project(...)`, `bpy.ops.uv.sphere_project(...)`
- Projects UVs as if camera is looking at mesh.
- Context-override: **MAYBE** — `project_from_view` may need 3D Viewport context (`window` and `area` in override). Check: https://docs.blender.org/api/current/bpy.ops.uv.html#bpy.ops.uv.project_from_view
- Cylinder/Cube/Sphere: typically no viewport needed.

---

### 1.4 UV island packing (Edit Mode, post-unwrap)

**Step:** Arrange UV islands into the 0..1 texture-space rect to maximize coverage without overlap.

**API:** `bpy.ops.uv.pack_islands()`

**Parameters (4.2+):**
- `margin` (float): island margin in pixels (converted from normalized space). Default 0.0; common: 0.01–0.05 (1–5% normalized).
- `margin_method`: `'EXTEND'` (default) or `'ADJACENT'` (blend seams). UE typically uses `EXTEND`.
- `use_seams`: bool. If True, respect seams; if False, pack freely.

**Context-override:** **YES** (Edit Mode).

**Blender 4.2 docs:** https://docs.blender.org/api/current/bpy.ops.uv.html#bpy.ops.uv.pack_islands, https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/editing.html#pack-islands

---

### 1.5 UV island optimization (Edit Mode)

Post-pack, artists often:

#### A. **Average Islands Scale** (normalize texel density)
- API: `bpy.ops.uv.average_islands_scale()`
- Equalizes island sizes so all faces get similar texel density.
- Context-override: **YES** (Edit Mode).

#### B. **Minimize Stretch** (reduce distortion)
- API: `bpy.ops.uv.minimize_stretch(use_dissolve=False, iterations=0)`
- Relaxes UVs to reduce angle/area distortion.
- Context-override: **YES** (Edit Mode).

#### C. **Pack into User Region / UDIM** (tiling, 4.0+)
- API: `bpy.ops.uv.pack_islands_to_uv_islands()` (packs into defined user regions) or manual UDIM region setup.
- **UDIM support (4.0+):** Blender can now work with multiple 1024×1024 tiles (like Maya's UDIM). A tile at position (0,1) is named with suffix `_1001`, (1,1) is `_1002`, etc. (OpenUDIM convention).
- **Constraint:** Islands must lie within defined tile bounds or auto-tile (experimental in 4.2).
- Context-override: **YES** (Edit Mode).
- Blender 4.2 docs: https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/workflows/udims.html

---

### 1.6 UDIM tile creation & workflow (Edit Mode + Image creation)

**Blender 4.2 UDIM specifics:**

- **UDIM naming:** Image must be named `<base>_<tile_number>.exr` (or `.png` / `.tga`). Tile `(0,0)` = `_1001`, `(1,0)` = `_1002`, `(0,1)` = `_1011`, etc. (row-major, Maya convention).
- **Multi-tile support:** `bpy.data.images.new(..., use_multiview=False)` but then manually split into tileset, or use external tools.
- **Agent constraint:** Blender's UDIM tooling is limited. Recommend: agent bakes UV0 to a single 4096×4096 tile for UE (standard); if user needs UDIM tiling, offer `uv_split_to_udim_tiles()` composite that exports to separate files per tile for external reassembly. **Or:** document UDIMs as a "prepare offline" step (agent can read; can't easily author).

---

### 1.7 UV layer mask setup (Pin / Unpin vertices, Snap to Pixels)

**Step (optional):** Lock certain UV vertices to prevent them moving during layout.

**API:**
- `bpy.ops.uv.pin()` / `bpy.ops.uv.pin(clear=True)` (un-pin).
- Requires Edit Mode + UV Editor context (loop selection).
- Context-override: **MAYBE** — UV Editor may need special context. Check docs.

**Snap to Pixels:** `bpy.ops.uv.snap_selected(target='EDGE')`

**Context-override:** **YES** (Edit Mode).

---

## 2. Baking setup & execution

Baking in Blender requires:
1. **Target image(s)** — Image Texture node(s) in material(s), selected and active.
2. **UV map** — mesh must have a UV layer (created in step 1.1–1.6).
3. **Scene render settings** — Cycles render engine selected.
4. **Bake settings** — type, margin, cage object (optional), Selected-to-Active params.

### 2.1 Bake types (Cycles engine)

**Per Blender 4.2 API:** https://docs.blender.org/api/current/bpy.types.BakeSettings.html

| Bake type | Python enum | Use case | Notes |
|---|---|---|---|
| `COMBINED` | `.COMBINED` | All lighting + materials | default; includes diffuse, glossy, transmission, emission, AO. |
| `DIFFUSE` | `.DIFFUSE` | Base color / albedo | Set influence flags to get Direct/Indirect/Color subsets. |
| `GLOSSY` | `.GLOSSY` | Specular reflection | Rarely baked standalone. |
| `TRANSMISSION` | `.TRANSMISSION` | Glass/SSS | For translucent materials (rare for game PBR). |
| `EMIT` | `.EMIT` | Emissive channel | Separate glow bake. |
| `AMBIENT_OCCLUSION` | `.AMBIENT_OCCLUSION` | AO only | Ignores lights; bakes curvature occlusion. |
| `SHADOW` | `.SHADOW` | Shadow map | Rarely used. |
| `POSITION` | `.POSITION` | World-space XYZ position | R=X, G=Y, B=Z as texture. Used for some displacement workflows. |
| `NORMAL` | `.NORMAL` | Normal map (tangent or object space) | See 2.3 for space choice. |
| `UV` | `.UV` | UV coordinates as RGB | Debugging; rarely baked. |
| `ROUGHNESS` | `.ROUGHNESS` | PBR roughness channel | From Principled BSDF roughness input. |
| `METALLIC` | `.METALLIC` | PBR metallic channel | From Principled BSDF metallic input. |
| `ENVIRONMENT` | `.ENVIRONMENT` | World environment | Bakes world shader. |

**For UE PBR pipeline (base set):**
- **Normal** (`NORMAL`, tangent space by default).
- **Roughness** (`ROUGHNESS`).
- **Metallic** (`METALLIC`).
- **Diffuse** (`DIFFUSE` with direct/indirect/color flags).
- **AO** (`AMBIENT_OCCLUSION`).
- **Emit** (`EMIT`) if character has bioluminescent details.

### 2.2 Bake modes: single-mesh self-bake vs. Selected-to-Active

#### A. **Self-bake** (mesh baking its own material to its own UV)
- **Common use:** baking a high-detail Principled BSDF (with many node groups) into a simple texture for export.
- **API:** no special mode; just bake with the object selected + active. The target image must be in a material on the same object.
- **Cycles bake:** `bpy.ops.object.bake(type='...')`

#### B. **Selected-to-Active** (high-poly to low-poly cage workflow)
- **Common use:** bake detail from a sculpted/subdivided high-poly mesh onto a low-poly game mesh.
- **API:**
  - High-poly objects: select them.
  - Low-poly object: select AND make active (the target).
  - Set `bpy.context.scene.render.bake.use_selected_to_active = True`.
  - Optional: define a cage object via `bpy.context.scene.render.bake.cage_object = cage_obj`.
  - Call `bpy.ops.object.bake(type='NORMAL')` etc.
- **Ray distance:** When not using a cage, adjust `max_ray_distance` to control ray casting depth.
- **Cage extrusion:** If using auto cage (not manual cage object), adjust `cage_extrusion` to offset the cage outward.

**Blender 4.2 docs:**
- https://docs.blender.org/api/current/bpy.types.BakeSettings.html
- https://docs.blender.org/manual/en/4.2/render/cycles/baking.html

---

### 2.3 Normal map space (tangent vs. object)

**Critical for UE export:** Normal maps must be **tangent space** for compatibility.

**API:** `bpy.context.scene.render.bake.normal_space`
- Options: `'TANGENT'` (default, **correct for UE**), `'OBJECT'` (world space).
- **Rule:** Always bake with `normal_space = 'TANGENT'`.

**Tangent vector calculation (in Blender):**
- By default computed from smooth normals + edge split modifiers.
- Controlled via `mesh.use_auto_smooth` + `mesh.auto_smooth_angle`.

---

### 2.4 Cage objects (for high-to-low normal baking)

**What:** A slightly-inflated copy of the low-poly mesh. Normal rays cast inward from the cage to the high-poly, capturing fine detail without edge artifacts.

**Setup:**
```python
# Create cage: duplicate low-poly, apply solidify modifier (small offset, e.g. 0.1 Blender units)
cage_obj = low_poly.duplicate()
cage_obj.data = low_poly.data.copy()  # deep copy mesh data
solidify = cage_obj.modifiers.new(name='Solidify', type='SOLIDIFY')
solidify.thickness = 0.1  # or compute from bounding box
solidify.offset = 0.0  # keep centered

# Register cage
bpy.context.scene.render.bake.use_cage = True
bpy.context.scene.render.bake.cage_object = cage_obj
```

**Constraint:** Cage must have **identical topology** to low-poly (same vertex count, face order). Any deviation breaks the bake.

**Alternative (automatic):** Set `use_cage = False` and adjust `cage_extrusion` instead. Less reliable but avoids manual cage creation.

---

### 2.5 Bake margin (pixel padding around UV islands)

**Why:** To avoid seam artifacts from texture filtering / mip-mapping. Typically 16–32 px for 2K, 4–8 px for 1K.

**API:**
```python
bpy.context.scene.render.bake.margin = 16  # pixels (not normalized)
bpy.context.scene.render.bake.margin_type = 'EXTEND'  # 'EXTEND' or 'ADJACENT'
```

- `EXTEND`: extends island border pixels outward.
- `ADJACENT`: fills margin from neighboring faces (smoother blending, but requires careful seam placement).

---

### 2.6 Bake target: Image Texture node selection (crucial quirk)

**Critical constraint (Blender bake API):** `bpy.ops.object.bake(...)` reads the **currently-selected and active Image Texture node** in the object's material(s). If no node is selected/active, bake fails silently or errors.

**Setup pattern:**
```python
obj = bpy.data.objects[obj_name]
material = obj.data.materials[mat_index]

# Ensure material has Principled BSDF
principled = material.node_tree.nodes.get('Principled BSDF')
if not principled:
    principled = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')

# Create or get Image Texture node
img_node = material.node_tree.nodes.new('ShaderNodeTexImage')
img_node.image = bpy.data.images.new(name=f"Bake_{bake_type}_{mat_index}", width=2048, height=2048)

# **SELECT AND MAKE ACTIVE** — this is the quirk
material.node_tree.nodes.active = img_node
img_node.select = True

# Now bake
bpy.ops.object.bake(type='NORMAL', use_selected_to_active=False, ...)
```

**Agent responsibility:** Tools `bake_normal`, `bake_roughness` etc. must handle this node selection internally.

---

## 3. Image creation & output

### 3.1 Image creation & baking target

**API:**
```python
img = bpy.data.images.new(
    name="MyBake",
    width=2048,
    height=2048,
    alpha=False,  # or True for RGBA
    float_buffer=False  # True for 32-bit float; False for 8-bit
)
```

**Blender 4.2 docs:** https://docs.blender.org/api/current/bpy.types.Image.html

**Naming convention (for agent):** `<mesh_name>_<bake_type>` e.g., `Armor_Normal`, `Armor_Roughness`.

---

### 3.2 Image save (after bake)

**API:**
```python
img.save_render(filepath="C:/output/armor_normal.exr", scene=bpy.context.scene)
# Or: img.save(filepath=...) for bpy.data.images.load() type (read-only, needs temp repack)
```

**Format choice:**
- **`.exr`** (32-bit float, lossless) → **recommended for game baking** (preserves precision).
- **`.png`** (8-bit, lossless) → distribution format.
- **`.tga`** (8/16/32-bit, simple) → legacy but still used.

**File packing (optional):** `img.pack()` to embed in `.blend` file; `img.unpack()` to extract.

---

### 3.3 Composite normal map formats (tangent-space to UE convention)

Blender's tangent-space normal map (default):
- R = normal.X (left-right)
- G = normal.Y (forward-back)
- B = normal.Z (up-down, always positive in tangent space)

**OpenGL format (Blender default):** R=X, G=Y, B=Z.

**DirectX format (UE standard):** R=X, G=-Y, B=Z (green channel flipped).

**Agent tool** (`bake_normal`) should expose: `normal_format: 'OPENGL' | 'DIRECTX'` and automatically apply a swizzle during post-bake if needed. Or: document that UE FBX importer has a `Flip Green Channel` option on the texture import.

---

## 4. Multi-object & trim-sheet baking workflows

### 4.1 Multiple UV layer support (UV0, UV1, UV2)

**Scenario:** Character with separate lightmap layer.

```python
mesh = bpy.data.meshes[mesh_name]

# UV0 = PBR base
if "UVMap" not in mesh.uv_layers:
    mesh.uv_layers.new(name="UVMap")
mesh.uv_layers.active_index = mesh.uv_layers.find("UVMap")

# UV1 = lightmap (if needed; rare in Lumen default)
if "UVMap_Lightmap" not in mesh.uv_layers:
    mesh.uv_layers.new(name="UVMap_Lightmap")

# Bake to UVMap (base)
# ... bake_normal, bake_roughness etc. on UVMap ...

# Optionally bake lightmap (step is skip if Lumen-only)
# mesh.uv_layers.active_index = mesh.uv_layers.find("UVMap_Lightmap")
# ... bake AO or combined lighting ...
```

**UE5 import:** FBX importer auto-detects channel 1 as lightmap if present; otherwise ignored.

---

### 4.2 Trim sheet & modular asset baking

**Scenario:** 10 small modular kit pieces share one 2K trim texture. Each piece has a unique UV island within the trim sheet.

**Workflow:**
1. Create trim sheet layout in external tool (e.g. Substance Designer) or hand-author in Blender.
2. Model each piece, UV-map each to its designated region of the sheet (e.g., piece A: UV [0, 0.5] × [0.5, 1.0]).
3. Bake each piece's material to the same trim image (different UV regions).
4. Export all pieces + one shared trim texture.

**Agent tool:** `uv_align_island_to_trim_row()` composite — repositions selected island(s) to a specified row in a trim sheet (assume rows are 0.5 wide: row 0 = [0, 0.5], row 1 = [0.5, 1.0], etc.).

```python
# Pseudo-code
def uv_align_island_to_trim_row(obj_name, trim_row, scale=1.0):
    # Assumes island is already roughly sized; scale to fit row height
    # Reposition to row_start.y
    row_start = (trim_row % 2) * 0.5
    # ... loop over selected loops, set uv.y += row_start ...
```

---

## 5. Special bakes: Curvature, Position, Bent Normal

### 5.1 Curvature bake (pseudo-AO from geometry)

**Use:** Show geometric detail (creases, ridges) without baking full AO.

**Method:** Use Blender's Geometry node → Pointiness output, bake via Emit node.

**Setup:**
```python
# In Principled BSDF material:
# 1. Add Geometry node
# 2. Connect Geometry.Pointiness → new Mix node
# 3. Mix Pointiness with a constant color (0.5) to normalize to [0.5, 1.0] range
# 4. Connect to Principled.Emission (not Base Color; this is a workaround)
# 5. Bake as EMIT

# OR simpler: use Ambient Occlusion node (AO settings include distance = 0 for pointiness-like effect)
ao_node = material.node_tree.nodes.new('ShaderNodeAmbientOcclusion')
ao_node.samples = 128  # quality
# Connect ao_node.Color → Principled.Base Color
```

**Bake:** `bpy.ops.object.bake(type='AMBIENT_OCCLUSION', ...)` or `type='EMIT'` if using Geometry.Pointiness → Emit chain.

**Blender 4.2 docs:** https://docs.blender.org/api/current/bpy.types.ShaderNodeGeometry.html

---

### 5.2 Position bake (world-space or object-space location)

**Use:** Displacement maps, procedural effects, debug visualization.

**Method:** Blender's `bpy.ops.object.bake(type='POSITION', ...)` automatically bakes world-space XYZ → RGB.

**Output:** Each pixel encodes surface position. UE can use this as a basis for procedural effects.

**Blender 4.2 constraint:** Position bake is world-space only (cannot easily switch to local space). Workaround: post-process in Compositor.

---

### 5.3 Bent Normal bake (shadowing from cavities)

**Use:** Soften AO shadows in recesses (more realistic look than hard AO).

**Method (node-based workaround since Blender lacks native bent-normal operator):**
1. Bake Normal (tangent) map as usual → Normal_TX.
2. Bake AO → AO_TX.
3. In UE Material, blend Normal_TX by AO_TX to darken normals in shadows.

OR (advanced):

Blend normal vectors in Blender pre-bake:
```python
# Use Geometry.Pointiness + Mix nodes to tint Principled.Normal
# before baking NORMAL type
```

**Constraint:** True bent-normal baking (full ray-marching from each surface point into neighboring geometry) is **not natively supported** in Blender. Recommend: agent documents this as "UE-side post-process" or offers an `exec_python` workaround using `bmesh` ray-marching (risky, slow).

---

## 6. Tool entries (draft catalog, B4 set)

Estimated **~22–24 tools** for the B4 domain. Below are key entries with descriptions, Zod sketches, errorCodes, and context-override notes.

---

### 6.1 **`uv_layer_create`**

**Purpose:** Create or get a named UV layer on a mesh.

**Description:**
> Create or retrieve a UV layer by name. Used to set up UV0 (primary PBR), UV1 (lightmap), or UV2 (vertex mask). Returns the layer name and index.

**Zod schema (sketch):**
```typescript
{
  objectName: z.string().describe("Mesh object name"),
  layerName: z.string().describe("New UV layer name, e.g., 'UVMap', 'UVMap_Lightmap'"),
  createIfMissing: z.boolean().optional().describe("If true, create; if false, error if missing")
}
```

**Output payload:**
```typescript
{
  layerName: string,
  layerIndex: number,
  isnew: boolean
}
```

**Refs:** `{ objectName, layerName }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `LAYER_EXISTS` (if createIfMissing=false and layer exists)

**Next steps:** `uv_unwrap`, `uv_mark_seams`

**Context-override:** None (data access).

**Handler outline:**
```python
@handler("POST", "/uv/layer_create")
def layer_create(req):
    obj_name = req["object_name"]
    layer_name = req["layer_name"]
    
    def main():
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != 'MESH':
            raise HandlerError("OBJECT_NOT_FOUND", ...)
        
        mesh = obj.data
        if layer_name in mesh.uv_layers:
            if not req.get("create_if_missing", True):
                raise HandlerError("LAYER_EXISTS", ...)
            idx = mesh.uv_layers.find(layer_name)
        else:
            layer = mesh.uv_layers.new(name=layer_name)
            idx = len(mesh.uv_layers) - 1
        
        return {"layer_name": layer_name, "layer_index": idx, "is_new": ...}
    
    return run_on_main(main)
```

---

### 6.2 **`uv_mark_seam`**

**Purpose:** Mark edges as seam in Edit Mode.

**Description:**
> Mark selected edges as UV seams (cuts for unwrapping). Switches to Edit Mode, marks, returns to Object Mode. Idempotent.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  edgeIndices: z.array(z.number()).optional().describe("If given, select these edge indices; else use current selection")
}
```

**Output:** `{ objectName, markedCount: number }`

**Refs:** `{ objectName }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `NO_SELECTION` (if no edges selected and edgeIndices not given)

**Context-override:** **YES** — Edit Mode via `bpy.context.temp_override(object=obj)`.

**Handler outline:**
```python
@handler("POST", "/uv/mark_seam")
def mark_seam(req):
    obj_name = req["object_name"]
    edge_indices = req.get("edge_indices")
    
    def main():
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != 'MESH':
            raise HandlerError("OBJECT_NOT_FOUND", ...)
        
        with bpy.context.temp_override(object=obj):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            
            if edge_indices:
                for idx in edge_indices:
                    obj.data.edges[idx].select = True
            
            bpy.ops.mesh.mark_seam()
            marked = sum(1 for e in obj.data.edges if e.use_seam)
            
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.ed.undo_push(message="Mark UV seams")
        return {"object_name": obj_name, "marked_count": marked}
    
    return run_on_main(main)
```

---

### 6.3 **`uv_unwrap`**

**Purpose:** Unwrap mesh using angle-based algorithm (requires seams).

**Description:**
> Unwrap the mesh into UV space using angle-preserving (Angle-Based) method. Requires pre-marked seams. Suitable for characters and organic shapes. Restores Edit Mode state on exit.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  uvLayerName: z.string().optional().describe("Name of UV layer to unwrap (default: active layer)"),
  margin: z.number().optional().describe("Island margin in normalized space, e.g., 0.01")
}
```

**Output:** `{ objectName, islandCount: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `NO_SEAMS` (if no seams marked)

**Context-override:** **YES** — Edit Mode.

---

### 6.4 **`uv_smart_project`**

**Purpose:** Automatic unwrap; cuts seams for you.

**Description:**
> Auto-unwrap mesh with Smart UV Project. No seams needed (auto-generates). Exports quickly for props/static geometry.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  angleLimit: z.number().optional().describe("Angle limit in degrees, default 66"),
  islandMargin: z.number().optional().describe("Island margin (normalized), default 0.0")
}
```

**Output:** `{ objectName, islandCount: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`

**Context-override:** **YES** — Edit Mode.

---

### 6.5 **`uv_pack_islands`**

**Purpose:** Arrange UV islands into texture space.

**Description:**
> Optimize island layout after unwrap. Packs islands into 0..1 space with configurable margin. Respects seams if configured. Call after any unwrap operation.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  uvLayerName: z.string().optional(),
  margin: z.number().optional().describe("Margin size in pixels (converted to normalized space for this image size); typical 16–32"),
  marginType: z.enum(['EXTEND', 'ADJACENT']).optional(),
  useSeams: z.boolean().optional(),
  imageWidth: z.number().optional().describe("Image width (for pixel-to-normalized margin conversion); default 2048")
}
```

**Output:** `{ objectName, islandCount: number, coverage: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`

**Context-override:** **YES** — Edit Mode.

---

### 6.6 **`uv_average_islands_scale`**

**Purpose:** Normalize texel density across islands.

**Description:**
> Average the scale of all UV islands to match texel density (ensures no island is over- or under-textured). Idempotent; call after pack_islands for best results.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  uvLayerName: z.string().optional()
}
```

**Output:** `{ objectName, islandCount: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`

**Context-override:** **YES** — Edit Mode.

---

### 6.7 **`uv_minimize_stretch`**

**Purpose:** Reduce UV distortion.

**Description:**
> Relax UV islands to minimize angle and area stretch. Improves texture quality by reducing seam artifacts. Idempotent.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  uvLayerName: z.string().optional(),
  iterations: z.number().optional().describe("Relaxation iterations, default 0 (auto)")
}
```

**Output:** `{ objectName }`

**ErrorCodes:** `OBJECT_NOT_FOUND`

**Context-override:** **YES** — Edit Mode.

---

### 6.8 **`bake_image_create`**

**Purpose:** Create and assign a bake target image.

**Description:**
> Create a new image and connect it as the active Image Texture node in a material. Returns image name for passing to bake operators. Essential setup before baking.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  materialIndex: z.number().optional().describe("Material slot index; default 0"),
  width: z.number().optional().describe("Image width, default 2048"),
  height: z.number().optional().describe("Image height, default 2048"),
  imageName: z.string().optional().describe("Override image name (default: auto-generated)"),
  colorDepth: z.enum(['8', '16', '32']).optional().describe("Bits per channel, default '8'")
}
```

**Output:**
```typescript
{
  imageName: string,
  width: number,
  height: number,
  nodeId: string  // internal ref for tracking node selection
}
```

**Refs:** `{ imageName }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `MATERIAL_NOT_FOUND` (if materialIndex >= slot count)

**Context-override:** None (data access).

**Handler outline:**
```python
@handler("POST", "/bake/image_create")
def image_create(req):
    obj_name = req["object_name"]
    mat_idx = req.get("material_index", 0)
    width = req.get("width", 2048)
    height = req.get("height", 2048)
    
    def main():
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != 'MESH':
            raise HandlerError("OBJECT_NOT_FOUND", ...)
        
        if mat_idx >= len(obj.material_slots):
            raise HandlerError("MATERIAL_NOT_FOUND", ...)
        
        material = obj.material_slots[mat_idx].material
        
        img = bpy.data.images.new(name=req.get("image_name", f"Bake_{obj_name}"), width=width, height=height)
        
        node_tree = material.node_tree
        img_node = node_tree.nodes.new('ShaderNodeTexImage')
        img_node.image = img
        
        node_tree.nodes.active = img_node
        img_node.select = True
        
        return {"image_name": img.name, "width": width, "height": height}
    
    return run_on_main(main)
```

---

### 6.9 **`bake_normal`**

**Purpose:** Bake normal map (tangent or object space).

**Description:**
> Bake surface normals to the active Image Texture node in the object's active material. Automatically sets Cycles render engine. Supports Selected-to-Active high-to-low baking with optional cage. Returns image name and bake status. Call `bake_image_create` first.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  selectedToActive: z.boolean().optional().describe("If true, bake high-poly to low-poly cage; if false, self-bake"),
  normalSpace: z.enum(['TANGENT', 'OBJECT']).optional().describe("Tangent for UE, Object for world-space; default TANGENT"),
  useSwizzle: z.enum(['OPENGL', 'DIRECTX']).optional().describe("Post-bake swizzle (OpenGL or DirectX); default OPENGL"),
  cageObject: z.string().optional().describe("Cage object name for Selected-to-Active"),
  cageExtrusion: z.number().optional().describe("Auto-cage offset if cageObject not given; default 0.05"),
  margin: z.number().optional().describe("Bake margin in pixels; default 16"),
  maxRayDistance: z.number().optional().describe("Ray distance for Selected-to-Active (when not using cage); default 1000")
}
```

**Output:**
```typescript
{
  imageName: string,
  bakeTime: number,  // seconds
  success: boolean
}
```

**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_IMAGE_NODE_ACTIVE` (if `bake_image_create` wasn't called), `INVALID_CAGE_OBJECT`, `BAKE_TIMEOUT` (30s default)

**Context-override:** No specific context needed; internal setting of render engine.

---

### 6.10 **`bake_roughness` / `bake_metallic` / `bake_diffuse` / `bake_ao`**

(Similar structure to bake_normal; abbreviated)

**Purpose:** Bake individual PBR channels.

**Zod schema (common):**
```typescript
{
  objectName: z.string(),
  materialIndex: z.number().optional(),
  margin: z.number().optional(),
  selectedToActive: z.boolean().optional()
}
```

**Output:** `{ imageName: string, bakeTime: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_IMAGE_NODE_ACTIVE`, `BAKE_TIMEOUT`

---

### 6.11 **`bake_curvature`** (special)

**Purpose:** Bake pseudo-AO from geometry pointiness.

**Description:**
> Bake curvature/pointiness as a pseudo-AO map. Requires setting up Geometry node → Pointiness → Emit chain in material before calling. This is a workaround for native bent-normal support.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  margin: z.number().optional()
}
```

**Output:** `{ imageName: string }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_EMIT_NODE_FOUND` (if material doesn't have Emit node wired to Pointiness)

---

### 6.12 **`bake_position`**

**Purpose:** Bake world-space position as texture.

**Description:**
> Bake world XYZ position to RGB. Used for procedural effects or displacement. Note: Blender only supports world-space; no local-space option.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  margin: z.number().optional()
}
```

**Output:** `{ imageName: string }`

---

### 6.13 **`image_save_render`**

**Purpose:** Save a baked image to disk.

**Description:**
> Save baked image using `image.save_render()`. Supports .exr (32-bit float, recommended), .png, .tga. Returns saved file path.

**Zod schema:**
```typescript
{
  imageName: z.string(),
  filepath: z.string().describe("Absolute output path, e.g., 'C:/output/armor_normal.exr'"),
  format: z.enum(['EXR', 'PNG', 'TARGA']).optional().describe("Output format; default EXR")
}
```

**Output:** `{ imageName: string, filepath: string, filesize: number }`

**ErrorCodes:** `IMAGE_NOT_FOUND`, `INVALID_PATH`, `SAVE_FAILED` (I/O error)

---

### 6.14 **`cage_object_create`**

**Purpose:** Create an auto-cage for Selected-to-Active normal baking.

**Description:**
> Create a slightly-inflated copy of the active mesh (cage) for high-to-low normal baking. Applies Solidify modifier with configurable offset. Validates topology match. Returns cage object name.

**Zod schema:**
```typescript
{
  objectName: z.string().describe("Mesh to create cage from"),
  thickness: z.number().optional().describe("Solidify thickness in Blender units; default 0.1"),
  cageName: z.string().optional().describe("Override cage name (default: auto-generated)")
}
```

**Output:** `{ cageObjectName: string }`

**Refs:** `{ cageObjectName }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_MESH`, `INVALID_TOPOLOGY` (if dup fails or mesh corrupt)

---

### 6.15 **`uv_project_from_view`** (composite)

**Purpose:** Project UVs from active camera viewpoint.

**Description:**
> Project UVs as if camera is looking at mesh. Useful for baked-down decals, projected textures, or simple props. Requires active camera. Context-sensitive; may need viewport override.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  orthographic: z.boolean().optional().describe("Orthographic or perspective projection; default false"),
  scaleUVs: z.boolean().optional().describe("Scale UV island after project; default true")
}
```

**Output:** `{ objectName, islandCount: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_ACTIVE_CAMERA`, `CONTEXT_OVERRIDE_FAILED` (viewport not available)

**Context-override:** **MAYBE** — `project_from_view` requires 3D Viewport context. May need `window`, `area` in override. Document as a potential blocker; test on headless.

---

### 6.16 **`uv_project_cube` / `uv_project_cylinder` / `uv_project_sphere`**

(Similar to project_from_view; procedural projection axes)

**Zod schema:**
```typescript
{
  objectName: z.string(),
  scale: z.number().optional().describe("Projection scale; default 1.0"),
  offset: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Projection center offset")
}
```

**No viewport context needed** (unlike project_from_view).

---

### 6.17 **`uv_follow_active_quads`**

**Purpose:** Unwrap quads following a reference face.

**Description:**
> Follow active quads: traces UV layout from a reference face through connected quads. Good for grid-like topology (modular assets). Requires Edit Mode, pre-selected face.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  mode: z.enum(['LENGTH_AVERAGE', 'LENGTH_LONGER']).optional().describe("Quad-following mode"),
  uvLayerName: z.string().optional()
}
```

**Output:** `{ objectName, islandCount: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `NO_FACE_SELECTED` (if no active face)

**Context-override:** **YES** — Edit Mode.

---

### 6.18 **`uv_lightmap_pack`** (optional, rarely used in Lumen default)

**Purpose:** Pack islands densely for lightmap baking (Lightmass workflow, not Lumen).

**Description:**
> Pack UV islands optimally for lightmap baking (legacy Lightmass workflow). Rarely used in default Lumen projects. Kept for backwards-compatibility. Call with `enabled=false` by default for new projects.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  enabled: z.boolean().optional().describe("If false, skip and warn; default false"),
  context: z.enum(['ALL_FACES', 'SEL_FACES']).optional()
}
```

**Output:** `{ objectName, islandCount: number, skipped: boolean }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `LIGHTMAP_DISABLED_WARN`

---

### 6.19 **`uv_align_to_trim_row`** (composite)

**Purpose:** Align UV island(s) to a trim sheet row.

**Description:**
> Reposition selected UV island(s) to align with a specified row in a trim sheet (0.5 high per row). Assumes trim sheet is 1.0 wide, N×0.5 tall. Scales island to fit row height. Used in modular asset workflows.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  trimRow: z.number().describe("Row index (0=top, 1=middle, 2=bottom, etc.)"),
  trimWidth: z.number().optional().describe("Trim sheet width (normalized); default 1.0"),
  trimRowHeight: z.number().optional().describe("Height per row; default 0.5")
}
```

**Output:** `{ objectName, island Count: number, newUVBounds: { minU, maxU, minV, maxV } }`

**ErrorCodes:** `OBJECT_NOT_FOUND`, `INVALID_TRIM_ROW` (row index out of range)

**Context-override:** **YES** — Edit Mode (to select/move UVs).

---

### 6.20 **`uv_snap_to_pixels`** (optional, precision tool)

**Purpose:** Snap UV vertices to pixel boundaries.

**Description:**
> Snap selected UV vertices to the nearest pixel boundary (useful for hard-edged decals, UI elements). Requires image resolution context.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  uvLayerName: z.string().optional(),
  imageWidth: z.number().optional().describe("Image width for pixel calculation; default 2048"),
  imageHeight: z.number().optional()
}
```

**Output:** `{ objectName, snappedVertexCount: number }`

**ErrorCodes:** `OBJECT_NOT_FOUND`

**Context-override:** **YES** — Edit Mode.

---

### 6.21 **`uv_validate_for_baking`** (verify tool)

**Purpose:** Pre-bake validation.

**Description:**
> Validate mesh is ready for baking: has UV layer, no isolated islands, no overlapping UVs (optional), UV bounds sanity. Returns warnings/errors. Idempotent.

**Zod schema:**
```typescript
{
  objectName: z.string(),
  checkOverlap: z.boolean().optional().describe("Check for overlapping islands; slow; default false"),
  uvLayerName: z.string().optional()
}
```

**Output:**
```typescript
{
  objectName: string,
  isValid: boolean,
  issues: Array<{ severity: 'ERROR' | 'WARNING', message: string }>
}
```

**ErrorCodes:** `OBJECT_NOT_FOUND`

---

### 6.22 **`image_pack` / `image_unpack`**

**Purpose:** Embed or extract image from .blend.

**Description:**
> Pack baked image into .blend file (embeds PNG/EXR) or unpack to disk. Used for distribution or cleanup.

**Zod schema:**
```typescript
{
  imageName: z.string(),
  packed: z.boolean().describe("If true, pack; if false, unpack to specified path"),
  unpackPath: z.string().optional().describe("Path to unpack to (if packed=false)")
}
```

**Output:** `{ imageName: string, packed: boolean }`

**ErrorCodes:** `IMAGE_NOT_FOUND`

---

## 7. Open questions & constraints

### 7.1 Bake API viewport context

**Question:** `bpy.ops.uv.project_from_view()` docs suggest it may need 3D Viewport context (`window`, `area`) in `bpy.context.temp_override(...)`. In headless mode, there is no 3D Viewport.

**Constraint:** Test required on headless Blender to confirm:
- Does `project_from_view` fail without viewport?
- If so, mark as `BLOCKED_HEADLESS` and offer `cube_project` / `sphere_project` as workaround.

**Recommendation:** Agent tool `uv_project_from_view` should gracefully fall back or warn if headless.

### 7.2 Automatic cage creation

**Question:** Should `bake_normal(..., cageObject=None)` auto-generate a cage using Solidify, or should it always require a pre-created cage?

**Constraint:** Auto-cage (Solidify) is simple but may not suit all high-poly scenarios. Manual cage gives artist control.

**Recommendation:** Ship both: `cage_object_create()` for manual cage, and allow `cage_extrusion` parameter in `bake_normal()` for auto-cage fallback. Document that manual cage is preferred for production.

### 7.3 UDIM support & multi-tile baking

**Question:** Blender 4.2 has partial UDIM support. Should the agent attempt to bake multi-tile UDIMs, or stick to single 4K tile?

**Constraint:** Multi-tile baking is complex (requires exporting per-tile, managing naming). Single tile is simpler and fits UE best-practice (use trim sheets for modular kits, not UDIM tiling).

**Recommendation:** Agent ships single-tile baking. Document UDIM as "prepare offline" or offer `uv_split_to_udim_tiles()` composite for **export-time** tiling (export to separate files, not bake-in-place).

### 7.4 Bent Normal baking

**Question:** Blender lacks native Bent Normal (shadowing vector field). Should agent ship it as node-setup + workaround, or defer?

**Constraint:** Bent Normal is nice-to-have; not essential for base PBR export.

**Recommendation:** v1.0 ship without. Document in `nextSteps` for users who want it: "use Geometry.Pointiness → tint Normal in Compositor post-bake" or use external baker (Marmoset, Substance). Flag as v1.1 candidate if demand emerges.

### 7.5 Context-override for UV Editor

**Question:** Some UV ops may require UV Editor context (e.g., `pin`, `snap_to_pixels`). Does temp_override work?

**Constraint:** UV Editor is a different context than 3D Viewport. Blender API docs are silent on this.

**Recommendation:** Test on actual UV ops. If blocked, document as "requires user to have UV Editor open" (fallback: agent can guide user, can't automate).

---

## 8. ErrorCodes registry (B4 domain)

| ErrorCode | HTTP status | Meaning | Typical cause |
|---|---|---|---|
| `OBJECT_NOT_FOUND` | 404 | Object name not in scene | Name typo, object deleted |
| `OBJECT_NOT_MESH` | 400 | Object exists but not a mesh | Object is Armature, Light, etc. |
| `MATERIAL_NOT_FOUND` | 404 | Material index out of range | Index >= material_slots count |
| `NO_IMAGE_NODE_ACTIVE` | 400 | No Image Texture node selected in material | Call `bake_image_create` first |
| `NO_SEAMS` | 400 | Unwrap requested but no seams marked | Call `uv_mark_seam` first |
| `BAKE_TIMEOUT` | 500 | Bake operation exceeded 30s | Scene too complex, render settings too high |
| `INVALID_CAGE_OBJECT` | 404 | Cage object name not found | Name typo |
| `INVALID_TOPOLOGY` | 400 | Cage object has different topology than low-poly | Cage mesh corrupted or topology changed |
| `NO_FACE_SELECTED` | 400 | Follow Active Quads requires active face | Select a face in Edit Mode first |
| `NO_ACTIVE_CAMERA` | 404 | Project From View needs camera | Add a camera to scene |
| `CONTEXT_OVERRIDE_FAILED` | 500 | Viewport context not available (headless?) | Fallback to non-viewport projection method |
| `LIGHTMAP_DISABLED_WARN` | 200 (warn) | Lightmap Pack called but Lumen is default | Return success but warn "skip for Lumen projects" |
| `INVALID_TRIM_ROW` | 400 | Trim sheet row index out of valid range | Row index < 0 or > max rows |
| `IMAGE_NOT_FOUND` | 404 | Image name not in bpy.data.images | Image deleted or name wrong |
| `INVALID_PATH` | 400 | Filepath is invalid (syntax, permissions) | Check path syntax and disk write access |
| `SAVE_FAILED` | 500 | Disk write error | Disk full, permissions denied |
| `NO_EMIT_NODE_FOUND` | 400 | Curvature bake: no Emit node in material | Material setup incomplete |

---

## 9. Composite tool candidates (B4)

Multi-step flows that are worth packaging as single high-level tools:

### 9.1 **`bake_normal_high_to_low`** (composite)

**Orchestrated steps:**
1. `cage_object_create(low_poly_obj)` → get cage name
2. `bake_image_create(low_poly_obj)` → get image name
3. `bake_normal(..., selectedToActive=True, cageObject=cage_name)` → bake
4. `image_save_render(image_name, filepath)` → save

**Returns:** `{ imageName, filePath, bakeTime }`

---

### 9.2 **`uv_prepare_for_export`** (composite)

**Orchestrated steps:**
1. Select all faces (`bpy.ops.mesh.select_all()`)
2. `uv_smart_project(obj, angleLimit=66)` → unwrap
3. `uv_pack_islands(obj)` → pack
4. `uv_average_islands_scale(obj)` → normalize
5. `uv_minimize_stretch(obj, iterations=1)` → relax
6. `uv_validate_for_baking(obj, checkOverlap=True)` → verify
7. Returns validation result or error

**Returns:** `{ objectName, isValid, issues }`

---

### 9.3 **`bake_pbr_set`** (composite)

**Orchestrated steps:**
1. `bake_image_create(obj)` × 5 (Normal, Roughness, Metallic, Diffuse, AO) → get 5 image names
2. `bake_normal(..., image=images[0])` → bake
3. `bake_roughness(..., image=images[1])` → bake
4. `bake_metallic(..., image=images[2])` → bake
5. `bake_diffuse(..., image=images[3])` → bake
6. `bake_ao(..., image=images[4])` → bake
7. Loop through images, `image_save_render()` each → save all 5

**Returns:** `{ objectName, bakedImages: { normal, roughness, metallic, diffuse, ao }, filepaths }`

---

## 10. Estimated tool count & phasing

| Category | Count | Tools |
|---|---|---|
| UV Setup | 2 | `uv_layer_create`, `uv_mark_seam` |
| UV Unwrap | 5 | `uv_unwrap`, `uv_smart_project`, `uv_lightmap_pack`, `uv_follow_active_quads`, `uv_project_*` (3 variants) |
| UV Edit | 6 | `uv_pack_islands`, `uv_average_islands_scale`, `uv_minimize_stretch`, `uv_snap_to_pixels`, `uv_validate_for_baking`, `uv_align_to_trim_row` |
| Bake Target | 2 | `bake_image_create`, `image_save_render` |
| Bake Ops | 6 | `bake_normal`, `bake_roughness`, `bake_metallic`, `bake_diffuse`, `bake_ao`, `bake_curvature`, `bake_position` |
| Bake Support | 2 | `cage_object_create`, `image_pack`/`image_unpack` |
| Composites | 3 | `bake_normal_high_to_low`, `uv_prepare_for_export`, `bake_pbr_set` |
| **Total** | **~26–28** | |

---

## 11. Integration notes for project

- **New Python handler module:** `BlenderAgent/handlers/uv_bake.py` (replaces or supplements generic handlers).
- **New TS tool group:** `Tools/src/tools/uv-bake.ts` registering ~26 tools.
- **New tests:** `Tools/test/tools/uv-*.test.ts` (individual tests per tool), plus integration tests for composites.
- **New errorCodes:** Add all B4 codes to [.claude/rules/mcp-tools.md](.claude/rules/mcp-tools.md) registry.
- **Documentation:** Tool descriptions follow LLM-audience style per [mcp-tool-schema SKILL.md](.claude/skills/mcp-tool-schema/SKILL.md).

---

## 12. Blockers & workarounds

| Blocker | Severity | Workaround |
|---|---|---|
| Viewport context for `project_from_view` in headless | MEDIUM | Fall back to `cube_project`; document limitation. Test on headless first. |
| Bent Normal baking (no native support) | LOW | Use Geometry.Pointiness → Emit node chain; document as approximate. Or defer to v1.1. |
| UDIM multi-tile baking (limited 4.2 support) | MEDIUM | Single 4K tile only in v1.0. Export multi-tile via separate files + external UDIM assembly. |
| UV Editor context (for pin/snap) | MEDIUM | May require special context override; test and document. Fallback: `pin` as data mutation (slower). |
| Lightmap Pack (legacy, Lumen doesn't use) | LOW | Keep tool but default `enabled=false`; warn if called. Document as "Lightmass only". |

---

## 13. Citations & references

| Resource | URL |
|---|---|
| Blender 4.2 UV API | https://docs.blender.org/api/current/bpy.types.UVLoopData.html |
| Blender 4.2 UV Unwrapping Docs | https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/unwrapping/index.html |
| Blender 4.2 Baking Docs | https://docs.blender.org/manual/en/4.2/render/cycles/baking.html |
| Blender 4.2 UDIM Workflows | https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/workflows/udims.html |
| Blender 4.2 Geometry Node (Pointiness) | https://docs.blender.org/api/current/bpy.types.ShaderNodeGeometry.html |
| Blender 4.2 bpy.ops.uv.* Reference | https://docs.blender.org/api/current/bpy.ops.uv.html |
| Blender 4.2 Bake Settings | https://docs.blender.org/api/current/bpy.types.BakeSettings.html |
| UE5 FBX Skeletal Mesh Pipeline (texture import) | https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine |
| UE-TARGETS.md §4.4 (Lightmap UVs) | [in this project] |
| UE-TARGETS.md §5–6 (Nanite, Lumen implications) | [in this project] |

---

## 14. Conclusion & next steps

**Status:** All B4 domain workflows are **feasible in Blender 4.2 LTS** with the APIs documented above. Context-override is required for Edit Mode ops (seam marking, unwrapping, packing); no Edit Mode work is required for image creation or bake execution.

**Risk items:**
- Viewport context for `project_from_view` (test on headless).
- Bent Normal workarounds (node setup is manual; may need documentation).
- UDIM tiling (complex; recommend single-tile for v1.0).

**Phase B4 research artifacts:**
- This document (workflow + tool sketches).
- [.claude/docs/TOOL-CATALOG.md](TOOL-CATALOG.md) (to be written in Phase E) will expand each tool entry with full Zod schemas, error handling, and test sketches.
- Integration test templates will be drafted in Phase E.

**Ready for Phase C (feasibility crosswalk) and Phase E (full catalog).**

---

**End of B4 research report.**