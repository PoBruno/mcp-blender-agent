# B9 — Lighting + Camera + Render + Scene/Collection/Library/Asset Browser + File IO

## Research Report

---

## Read-First Summary

**Completion status:** This report covers Blender 4.2 LTS APIs for all B9 sub-domains. Key findings:

- **Lighting:** 4 light types (SUN, POINT, SPOT, AREA) are creatable; Light Linking + Light Groups are 4.2+ features; HDRI setup via `bpy.context.scene.world.node_tree`.
- **Camera:** Full lens control (FOV, shift, clipping, DOF); `bpy.context.scene.camera` sets active camera; composition guides available but not editable (read-only).
- **Render:** `scene.render.engine` defaults to `'BLENDER_EEVEE_NEXT'` in 4.2 (not `'BLENDER_EEVEE'`); Cycles, EEVEE Next, Workbench supported; operators: `bpy.ops.render.render()` with animation/still flags.
- **Scene/Collection/Library/Asset:** Scenes, Collections, ViewLayers native; Library Link + Library Override are power features with known fragility; Asset marking via `ID.asset_mark()`.
- **File IO:** `bpy.ops.wm.save_as_mainfile()`, `wm.open_mainfile()`, `wm.append()`, `file.pack_all()` available; **exec_python** policy critical for security.

All Blender 4.2+ docs: https://docs.blender.org/api/current/bpy.types.html

---

## Part A — Lighting

### Canonical Workflow

1. **Create light:** `bpy.data.lights.new(name, type)` where type ∈ `{SUN, POINT, SPOT, AREA}`.
2. **Wrap in object:** `bpy.data.objects.new(name, object_data=light)` + `scene.collection.objects.link()`.
3. **Configure parameters:** energy, color, size, shape (AREA only), angle (SUN), spot_size, spot_blend.
4. **Set light groups** (4.2+): `scene.view_layers[i].lightgroups` for per-light render passes.
5. **Configure Light Linking** (4.2+): `light.linking.receiver_collections`, `light.linking.blocker_collections` for selective shadowing.
6. **HDRI setup:** `scene.world.node_tree` → add Environment Texture + Background shader; set filepath in Environment Texture node.
7. **Undo:** `bpy.ops.ed.undo_push(message=...)`.

**Key constraint:** Light Linking + Light Groups are Blender render-only; FBX export maps Blender lights → UE Movable lights (lights are dynamic in UE, not static). UE Lumen does not import Light Linking or Light Groups.

### Proposed Tools — Part A

#### A1 — `light_create`
- **Group:** lighting
- **Type:** primitive
- **Description:** Create a new light data-block and object. Set energy, color, and type (SUN, POINT, SPOT, AREA). Returns light object name for downstream tools.
- **Zod schema (input):**
  ```ts
  {
    name: z.string().describe("Light name (unique key)"),
    type: z.enum(["SUN", "POINT", "SPOT", "AREA"]).describe("Light type"),
    energy: z.number().optional().describe("Light energy in watts or exposure scale (default 1000)"),
    color: z.tuple([z.number(), z.number(), z.number()]).optional().describe("RGB color [0-1] (default white)"),
    temperature_enabled: z.boolean().optional().describe("Enable blackbody temperature (default false)"),
    temperature_kelvin: z.number().optional().describe("Color temperature in Kelvin if enabled (800-20000)")
  }
  ```
- **Output payload:** `{ objectName: string, lightName: string, type: string }`
- **Refs:** `{ objectName, lightName }`
- **NextSteps:** `["call light_set_transform", "call light_set_area_shape (if type=AREA)"]`
- **ErrorCodes:** `LIGHT_EXISTS`, `INVALID_TYPE`
- **Python outline:**
  ```python
  @handler("POST", "/lighting/create")
  def create(req):
    def main():
      light = bpy.data.lights.new(name=req["name"], type=req["type"])
      light.energy = req.get("energy", 1000.0)
      light.color = req.get("color", (1, 1, 1))
      obj = bpy.data.objects.new(name=req["name"], object_data=light)
      bpy.context.scene.collection.objects.link(obj)
      bpy.ops.ed.undo_push(message=f"Create light {req['name']}")
      return {"object_name": obj.name, "light_name": light.name, "type": light.type}
    return run_on_main(main)
  ```
- **Upstream:** none
- **Downstream:** `light_set_transform`, `light_set_area_shape`, `light_configure_linking`
- **Tests:** happy path, LIGHT_EXISTS, INVALID_TYPE
- **Status:** v1.0 candidate

#### A2 — `light_set_area_shape`
- **Group:** lighting
- **Type:** primitive
- **Description:** Set AREA light shape (SQUARE, RECTANGLE, DISK, ELLIPSE) and dimensions. Only applies to AREA lights.
- **Zod schema:**
  ```ts
  {
    objectName: z.string().describe("AREA light object name"),
    shape: z.enum(["SQUARE", "RECTANGLE", "DISK", "ELLIPSE"]).describe("AREA light shape"),
    size_x: z.number().optional().describe("Width for SQUARE/RECTANGLE/ELLIPSE (default 1.0)"),
    size_y: z.number().optional().describe("Height for RECTANGLE/ELLIPSE (default 1.0)")
  }
  ```
- **Output:** `{ lightName: string, shape: string }`
- **Refs:** `{ lightName }`
- **ErrorCodes:** `LIGHT_NOT_FOUND`, `WRONG_LIGHT_TYPE`
- **Status:** v1.0 candidate

#### A3 — `light_configure_linking`
- **Group:** lighting
- **Type:** primitive
- **Description:** (4.2+) Set Light Linking receiver/blocker collections. Only affects Cycles/EEVEE Next render; FBX export does not preserve this.
- **Zod schema:**
  ```ts
  {
    lightObjectName: z.string().describe("Light object name"),
    receiver_collection_names: z.array(z.string()).optional().describe("Collections that receive light"),
    blocker_collection_names: z.array(z.string()).optional().describe("Collections that block light"),
    mode: z.enum(["INCLUDE", "EXCLUDE"]).optional().describe("Include or exclude collections (default EXCLUDE)")
  }
  ```
- **Output:** `{ lightName: string, receiver_count: number, blocker_count: number }`
- **Refs:** `{ lightName }`
- **Warnings:** `["Light Linking is Blender-render-only; does not export to FBX/glTF"]`
- **ErrorCodes:** `LIGHT_NOT_FOUND`, `COLLECTION_NOT_FOUND`
- **Status:** v1.0 candidate

#### A4 — `light_create_group`
- **Group:** lighting
- **Type:** primitive
- **Description:** (4.2+) Create a light group for per-light render passes in the active view layer.
- **Zod schema:**
  ```ts
  {
    groupName: z.string().describe("Light group name"),
    lights: z.array(z.string()).optional().describe("Light object names to add to group")
  }
  ```
- **Output:** `{ groupName: string, lightCount: number }`
- **Refs:** `{ groupName }`
- **Warnings:** `["Light Groups are Blender-render-only; do not export to UE/Lumen"]`
- **Status:** v1.0 candidate

#### A5 — `world_set_hdri`
- **Group:** lighting (world)
- **Type:** composite
- **Description:** Set world HDRI environment. Configures Environment Texture node + Background shader + strength. Returns world name.
- **Zod schema:**
  ```ts
  {
    hdri_filepath: z.string().describe("Path to .exr or .hdr image file"),
    strength: z.number().optional().describe("Background emission strength (default 1.0)"),
    rotation_z: z.number().optional().describe("Rotation around Z in degrees (default 0)")
  }
  ```
- **Output:** `{ worldName: string, hdri_loaded: boolean }`
- **Refs:** `{ worldName }`
- **ErrorCodes:** `FILE_NOT_FOUND`, `INVALID_IMAGE_FORMAT`
- **Composite steps:** create Environment Texture node, create Background shader, connect nodes, set filepath + strength, one undo push.
- **Status:** v1.0 candidate

---

## Part B — Camera

### Canonical Workflow

1. **Create camera:** `bpy.data.cameras.new(name)` + wrap in object.
2. **Configure lens:** type (PERSP/ORTHO/PANO), lens (mm), sensor size, sensor_fit.
3. **Set clipping planes:** clip_start, clip_end.
4. **Enable DOF:** `camera.dof.use_dof`, set focus_distance, aperture_fstop.
5. **Enable composition guides:** show_composition_thirds, show_composition_golden, etc. (display-only flags).
6. **Set as active camera:** `scene.camera = obj`.
7. **Undo:** `bpy.ops.ed.undo_push(message=...)`.

**Key constraint:** Composition guides are read-only overlays (cannot be edited). Camera framing via `bpy.ops.view3d.camera_to_view_selected` requires context override with 3D View area.

### Proposed Tools — Part B

#### B1 — `camera_create`
- **Group:** camera
- **Type:** primitive
- **Description:** Create a new camera data-block and object. Configure lens type, focal length, sensor size. Returns camera object name.
- **Zod schema:**
  ```ts
  {
    name: z.string().describe("Camera name"),
    type: z.enum(["PERSP", "ORTHO", "PANO"]).optional().describe("Camera type (default PERSP)"),
    lens_mm: z.number().optional().describe("Focal length in mm for PERSP (default 50)"),
    sensor_width_mm: z.number().optional().describe("Sensor width in mm (default 36)"),
    sensor_height_mm: z.number().optional().describe("Sensor height in mm (default 24)"),
    sensor_fit: z.enum(["AUTO", "HORIZONTAL", "VERTICAL"]).optional().describe("Fit mode (default AUTO)")
  }
  ```
- **Output:** `{ objectName: string, cameraName: string, type: string }`
- **Refs:** `{ objectName, cameraName }`
- **Status:** v1.0 candidate

#### B2 — `camera_set_dof`
- **Group:** camera
- **Type:** primitive
- **Description:** Enable depth-of-field and set focus distance + aperture f-stop.
- **Zod schema:**
  ```ts
  {
    cameraObjectName: z.string().describe("Camera object name"),
    use_dof: z.boolean().describe("Enable DOF (default true)"),
    focus_distance: z.number().optional().describe("Distance in meters to focal plane"),
    aperture_fstop: z.number().optional().describe("Aperture f-number (default 2.8)")
  }
  ```
- **Output:** `{ cameraName: string, dof_enabled: boolean }`
- **Refs:** `{ cameraName }`
- **Status:** v1.0 candidate

#### B3 — `camera_set_clipping`
- **Group:** camera
- **Type:** primitive
- **Description:** Set near and far clipping planes.
- **Zod schema:**
  ```ts
  {
    cameraObjectName: z.string(),
    clip_start: z.number().optional().describe("Near clipping distance (default 0.1 m)"),
    clip_end: z.number().optional().describe("Far clipping distance (default 1000 m)")
  }
  ```
- **Status:** v1.0 candidate

#### B4 — `camera_set_active`
- **Group:** camera
- **Type:** primitive
- **Description:** Set this camera as the active camera for the scene. Used for rendering.
- **Zod schema:**
  ```ts
  {
    cameraObjectName: z.string().describe("Camera object name"),
    sceneName: z.string().optional().describe("Scene name (default active scene)")
  }
  ```
- **Output:** `{ cameraName: string, sceneCamera: string }`
- **Refs:** `{ sceneName, cameraName }`
- **Status:** v1.0 candidate

---

## Part C — Render

### Canonical Workflow

1. **Choose engine:** `scene.render.engine` ← `'BLENDER_EEVEE_NEXT'` (4.2 default) | `'CYCLES'` | `'BLENDER_WORKBENCH'`.
   - **CRITICAL:** In 4.2+, the enum value is `'BLENDER_EEVEE_NEXT'`, not `'BLENDER_EEVEE'`.
2. **Configure engine params:** Cycles (samples, denoiser, max_bounces) vs EEVEE Next (samples, SSR, SSGI, volumetrics).
3. **Set resolution:** `scene.render.resolution_x/y`, `resolution_percentage`.
4. **Set output:** `scene.render.filepath`, `image_settings.file_format`, `color_mode`, `compression`.
5. **Render still:** `bpy.ops.render.render(write_still=True)` with frame specified.
6. **Render animation:** `bpy.ops.render.render(animation=True)` with frame_start/frame_end.
7. **Viewport screenshot:** `bpy.ops.screen.screenshot(filepath=...)` (requires context override with Editor area).

**Key constraint:** `bpy.ops.render.render()` is a modal operator; requires full scene evaluation. Headless rendering uses spawned `blender --background` process.

### Proposed Tools — Part C

#### C1 — `render_set_engine`
- **Group:** render
- **Type:** primitive
- **Description:** Switch render engine and return current settings. Blender 4.2 default is EEVEE_NEXT.
- **Zod schema:**
  ```ts
  {
    engine: z.enum(["BLENDER_EEVEE_NEXT", "CYCLES", "BLENDER_WORKBENCH"]).describe("Render engine"),
    sceneName: z.string().optional().describe("Scene name (default active)")
  }
  ```
- **Output:** `{ engine: string, cycles_available: boolean, eevee_next_available: boolean }`
- **Refs:** `{ sceneName, engine }`
- **NextSteps:** `["call render_configure_cycles or render_configure_eevee_next"]`
- **Status:** v1.0 candidate

#### C2 — `render_configure_cycles`
- **Group:** render
- **Type:** primitive
- **Description:** Configure Cycles render parameters: samples, denoiser, max bounces, light tree, caustics.
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().optional(),
    samples: z.number().optional().describe("Render samples (default 128)"),
    use_denoiser: z.boolean().optional().describe("Enable denoiser (default true)"),
    denoiser: z.enum(["OPENIMAGEDENOISE", "OPTIX"]).optional().describe("Denoiser type"),
    max_bounces: z.number().optional().describe("Max light bounces (default 12)"),
    use_light_tree: z.boolean().optional().describe("Use light tree for importance sampling (default true)"),
    use_caustics: z.boolean().optional().describe("Include caustics (default true)")
  }
  ```
- **Output:** `{ engine: string, samples: number, denoiser: string, max_bounces: number }`
- **Refs:** `{ sceneName }`
- **Status:** v1.0 candidate

#### C3 — `render_configure_eevee_next`
- **Group:** render
- **Type:** primitive
- **Description:** Configure EEVEE Next render parameters: samples, SSR, SSGI, volumetrics, irradiance volumes (4.2+).
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().optional(),
    samples: z.number().optional().describe("Viewport samples (default 1)"),
    use_ssr: z.boolean().optional().describe("Enable screen-space reflections (default true)"),
    use_ssgi: z.boolean().optional().describe("Enable screen-space GI (default true)"),
    use_volumetrics: z.boolean().optional().describe("Enable volumetrics (default true)")
  }
  ```
- **Output:** `{ engine: string, ssr_enabled: boolean, ssgi_enabled: boolean }`
- **Status:** v1.0 candidate

#### C4 — `render_set_output`
- **Group:** render
- **Type:** primitive
- **Description:** Configure output filepath, resolution, file format, color mode, compression.
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().optional(),
    filepath: z.string().describe("Output file path (supports # for frame numbers)"),
    resolution_x: z.number().optional().describe("Width in pixels (default 1920)"),
    resolution_y: z.number().optional().describe("Height in pixels (default 1080)"),
    file_format: z.enum(["PNG", "JPEG", "TIFF", "OPEN_EXR", "OPEN_EXR_MULTILAYER"]).optional(),
    color_mode: z.enum(["RGB", "RGBA"]).optional().describe("RGB or RGBA (default RGB)"),
    compression: z.number().optional().describe("PNG compression 0-9 (default 15)")
  }
  ```
- **Output:** `{ filepath: string, resolution: [number, number], fileFormat: string }`
- **ErrorCodes:** `INVALID_PATH`, `PERMISSION_DENIED`
- **Status:** v1.0 candidate

#### C5 — `render_still_image`
- **Group:** render
- **Type:** composite
- **Description:** Render a single frame (still image) and save to disk. Handles frame setup, render, wait.
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().optional(),
    frame: z.number().optional().describe("Frame to render (default current frame)"),
    output_filepath: z.string().describe("Output file path with extension"),
    wait_timeout_sec: z.number().optional().describe("Timeout in seconds (default 300)")
  }
  ```
- **Output:** `{ filepath: string, rendered: boolean, frame: number }`
- **Refs:** `{ filepath }`
- **NextSteps:** `[]`
- **ErrorCodes:** `RENDER_TIMEOUT`, `FILE_WRITE_ERROR`
- **Composite steps:** set frame, set output filepath, call `bpy.ops.render.render(write_still=True)`, wait for completion, verify file exists.
- **Status:** v1.0 candidate

#### C6 — `render_animation`
- **Group:** render
- **Type:** composite
- **Description:** Render an animation frame range and save frames to disk.
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().optional(),
    frame_start: z.number().optional().describe("First frame (default scene.frame_start)"),
    frame_end: z.number().optional().describe("Last frame (default scene.frame_end)"),
    output_filepath: z.string().describe("Output path with # for frame numbers, e.g. /output/frame_####.png"),
    wait_timeout_sec: z.number().optional().describe("Timeout in seconds (default 3600)")
  }
  ```
- **Output:** `{ filepath_pattern: string, frame_start: number, frame_end: number, rendered: boolean }`
- **ErrorCodes:** `RENDER_TIMEOUT`
- **Status:** v1.0 candidate

#### C7 — `viewport_screenshot`
- **Group:** render
- **Type:** composite
- **Description:** Capture viewport (OpenGL) screenshot at current shading mode. Requires context override with 3D View.
- **Zod schema:**
  ```ts
  {
    output_filepath: z.string().describe("Output file path"),
    width: z.number().optional().describe("Screenshot width (default viewport width)"),
    height: z.number().optional().describe("Screenshot height (default viewport height)")
  }
  ```
- **Output:** `{ filepath: string, captured: boolean }`
- **Warnings:** `["Viewport screenshot uses current shading mode (Material Preview); quality lower than render"]`
- **ErrorCodes:** `NO_3D_VIEW_CONTEXT`
- **Status:** v1.0 candidate (requires UI context)

---

## Part D — Scene / Collection / Library / Asset Browser

### Canonical Workflow

**Scenes + Collections:**
1. Create scene: `bpy.data.scenes.new(name)`.
2. Create collection: `bpy.data.collections.new(name)`.
3. Link to parent: `parent_collection.children.link(new_collection)`.
4. Move object between collections: unlink from old, link to new.
5. Create view layer: `scene.view_layers.new(name)` for per-layer visibility/exclude/holdout/indirect-only controls.

**Library Link (power feature):**
1. `bpy.ops.wm.link(filepath, directory, filename)` links external `.blend` data (referenced, not copied).
2. On import, linked data stays external; edits to source `.blend` auto-sync in dependent file.

**Library Override (more power, more fragility):**
1. `bpy.ops.object.make_override_library()` creates local editable copies of linked data.
2. Requires careful resync (`bpy.ops.object.library_override_resync()`) if source changes.
3. Known issue: override hierarchies can break if parent hierarchy changes.

**Asset Marking:**
1. `bpy.data.objects[i].asset_mark()` marks object as asset.
2. `bpy.data.objects[i].asset_data` sets catalog, tags, description, preview.
3. Asset Browser reads `.blend_assets.cats.txt` catalogs from each asset library folder.

### Proposed Tools — Part D

#### D1 — `scene_create`
- **Group:** scene
- **Type:** primitive
- **Description:** Create a new scene with optional template (GENERAL, COMPOSITING, etc.).
- **Zod schema:**
  ```ts
  {
    name: z.string().describe("Scene name"),
    template: z.enum(["GENERAL", "COMPOSITING", "MOTION_TRACKING"]).optional().describe("Scene template (default GENERAL)")
  }
  ```
- **Output:** `{ sceneName: string }`
- **Refs:** `{ sceneName }`
- **Status:** v1.0 candidate

#### D2 — `scene_set_active`
- **Group:** scene
- **Type:** primitive
- **Description:** Switch active scene.
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().describe("Target scene name")
  }
  ```
- **Output:** `{ activeScene: string }`
- **Refs:** `{ sceneName }`
- **Status:** v1.0 candidate

#### D3 — `collection_create`
- **Group:** collection
- **Type:** primitive
- **Description:** Create a new collection and optionally link to parent collection.
- **Zod schema:**
  ```ts
  {
    name: z.string().describe("Collection name"),
    parent_collection_name: z.string().optional().describe("Parent collection name (default scene root)")
  }
  ```
- **Output:** `{ collectionName: string, parentName: string }`
- **Refs:** `{ collectionName }`
- **Status:** v1.0 candidate

#### D4 — `collection_move_objects`
- **Group:** collection
- **Type:** primitive
- **Description:** Move one or more objects between collections.
- **Zod schema:**
  ```ts
  {
    object_names: z.array(z.string()).describe("Objects to move"),
    target_collection_name: z.string().describe("Target collection name")
  }
  ```
- **Output:** `{ moved_count: number, targetCollection: string }`
- **ErrorCodes:** `OBJECT_NOT_FOUND`, `COLLECTION_NOT_FOUND`
- **Status:** v1.0 candidate

#### D5 — `view_layer_create`
- **Group:** scene
- **Type:** primitive
- **Description:** Create a new view layer with optional collection visibility settings.
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().optional(),
    layerName: z.string().describe("View layer name")
  }
  ```
- **Output:** `{ layerName: string, sceneName: string }`
- **Status:** v1.0 candidate

#### D6 — `library_link`
- **Group:** library
- **Type:** primitive
- **Description:** Link external `.blend` data (referenced, not copied). Requires caution: linked data stays external and syncs from source.
- **Zod schema:**
  ```ts
  {
    blend_filepath: z.string().describe("Path to external .blend file"),
    data_type: z.enum(["OBJECT", "COLLECTION", "MATERIAL", "LIGHT", "CAMERA"]).describe("Data type to link"),
    data_names: z.array(z.string()).describe("Names of data-blocks to link (e.g., ['Collection.001', 'Material.001'])"),
    link_to_collection: z.string().optional().describe("Target collection to link objects into (optional)")
  }
  ```
- **Output:** `{ linked_names: [string], external_filepath: string }`
- **Refs:** `{ linkedNames }`
- **Warnings:** `["Linked data is read-only unless overridden. Changes to source .blend auto-sync here."]`
- **ErrorCodes:** `FILE_NOT_FOUND`, `BLEND_FORMAT_INVALID`
- **Status:** v1.0 candidate

#### D7 — `library_make_override`
- **Group:** library
- **Type:** composite
- **Description:** Create Library Override for linked data. Converts linked reference to editable local copy. **Caution:** hierarchies can break on resync.
- **Zod schema:**
  ```ts
  {
    linked_object_names: z.array(z.string()).describe("Linked object names to override")
  }
  ```
- **Output:** `{ override_count: number, overridden_names: [string] }`
- **Warnings:** `["Library Override is fragile. Override hierarchies may break if parent hierarchy changes in source. Use library_resync to repair."]`
- **ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_LINKED`, `OVERRIDE_FAILED`
- **Status:** v1.0 candidate

#### D8 — `library_resync`
- **Group:** library
- **Type:** composite
- **Description:** Resync Library Override hierarchy with source. Call if override breaks after source edit.
- **Zod schema:**
  ```ts
  {
    override_object_names: z.array(z.string()).describe("Override object names to resync")
  }
  ```
- **Output:** `{ resynced_count: number }`
- **Warnings:** `["Resync can lose local edits if source hierarchy changed. Backup before calling."]`
- **ErrorCodes:** `OBJECT_NOT_OVERRIDE`, `RESYNC_FAILED`
- **Status:** v1.0 candidate

#### D9 — `library_make_local`
- **Group:** library
- **Type:** primitive
- **Description:** Break library link and copy data into current `.blend` (irreversible; unlinks from source).
- **Zod schema:**
  ```ts
  {
    linked_object_names: z.array(z.string()).describe("Linked object names to make local")
  }
  ```
- **Output:** `{ localized_count: number }`
- **ErrorCodes:** `OBJECT_NOT_FOUND`, `OBJECT_NOT_LINKED`
- **Status:** v1.0 candidate

#### D10 — `asset_mark`
- **Group:** asset
- **Type:** primitive
- **Description:** Mark an object or data-block as an asset. Sets asset metadata: catalog, tags, description.
- **Zod schema:**
  ```ts
  {
    data_name: z.string().describe("Object or material name to mark as asset"),
    catalog_name: z.string().optional().describe("Asset catalog (e.g., 'Characters/Rigged')"),
    tags: z.array(z.string()).optional().describe("Asset tags (e.g., ['rigged', 'biped'])"),
    description: z.string().optional().describe("Asset description"),
    generate_preview: z.boolean().optional().describe("Generate thumbnail preview (default false)")
  }
  ```
- **Output:** `{ assetName: string, catalog: string, tags: [string] }`
- **Refs:** `{ assetName }`
- **Status:** v1.0 candidate

#### D11 — `asset_unmark`
- **Group:** asset
- **Type:** primitive
- **Description:** Unmark an asset.
- **Zod schema:**
  ```ts
  {
    assetName: z.string().describe("Asset name to unmark")
  }
  ```
- **Status:** v1.0 candidate

---

## Part E — File IO + Safety

### Canonical Workflow

1. **Save current file:** `bpy.ops.wm.save_mainfile()`.
2. **Save as new file:** `bpy.ops.wm.save_as_mainfile(filepath, compress)`.
3. **Open file (replaces session):** `bpy.ops.wm.open_mainfile(filepath)` — careful, closes current work.
4. **Append data from external `.blend`:** `bpy.ops.wm.append(filepath, directory, filename)` (copy, not link).
5. **Pack all external files:** `bpy.ops.file.pack_all()` → embeds textures/images into `.blend`.
6. **Unpack all:** `bpy.ops.file.unpack_all()` → extracts packed files to disk.

**Critical safety:** `exec_python(code: string)` is **not shipped by default** and should remain **opt-in behind env flag** (`BLENDER_AGENT_ALLOW_EXEC=1`). This prevents accidental code injection + privilege escalation attacks.

### Proposed Tools — Part E

#### E1 — `file_save`
- **Group:** file_io
- **Type:** primitive
- **Description:** Save current `.blend` file. No-op if file never saved (new file).
- **Zod schema:**
  ```ts
  {
    compress: z.boolean().optional().describe("Use zstd compression (default true)")
  }
  ```
- **Output:** `{ saved: boolean, filepath: string }`
- **ErrorCodes:** `FILE_NOT_SAVED_YET`, `PERMISSION_DENIED`
- **Status:** v1.0 candidate

#### E2 — `file_save_as`
- **Group:** file_io
- **Type:** primitive
- **Description:** Save `.blend` file to a new path. Creates new file or overwrites existing.
- **Zod schema:**
  ```ts
  {
    filepath: z.string().describe("Target .blend filepath"),
    compress: z.boolean().optional().describe("Use zstd compression (default true)"),
    relative_paths: z.boolean().optional().describe("Store relative paths for external files (default true)")
  }
  ```
- **Output:** `{ filepath: string, saved: boolean }`
- **ErrorCodes:** `PERMISSION_DENIED`, `INVALID_PATH`, `DISK_FULL`
- **Status:** v1.0 candidate

#### E3 — `file_open`
- **Group:** file_io
- **Type:** primitive
- **Description:** **WARNING:** Open a `.blend` file (replaces current session). Unsaved work is lost if not saved first.
- **Zod schema:**
  ```ts
  {
    filepath: z.string().describe("Path to .blend file to open"),
    load_ui: z.boolean().optional().describe("Load UI configuration from file (default true)")
  }
  ```
- **Output:** `{ filepath: string, opened: boolean }`
- **Warnings:** `["Opening a file replaces the current session. Unsaved work is lost. Call file_save before opening another file."]`
- **ErrorCodes:** `FILE_NOT_FOUND`, `BLEND_FORMAT_INVALID`
- **Status:** v1.0 candidate

#### E4 — `file_append_data`
- **Group:** file_io
- **Type:** primitive
- **Description:** Append data-blocks from external `.blend` (copy into current file, unlike library_link).
- **Zod schema:**
  ```ts
  {
    blend_filepath: z.string().describe("Source .blend filepath"),
    data_type: z.enum(["OBJECT", "COLLECTION", "MATERIAL", "LIGHT", "MESH", "ACTION"]).describe("Data type to append"),
    data_names: z.array(z.string()).describe("Names to append (e.g., ['Cube', 'Material.001'])")
  }
  ```
- **Output:** `{ appended_names: [string], filepath: string }`
- **ErrorCodes:** `FILE_NOT_FOUND`, `DATA_NOT_FOUND`
- **Status:** v1.0 candidate

#### E5 — `file_pack_all`
- **Group:** file_io
- **Type:** composite
- **Description:** Embed all external image/texture files into the `.blend` file. Increases file size; makes `.blend` portable.
- **Zod schema:**
  ```ts
  {
    sceneName: z.string().optional().describe("Scene to pack (all if omitted)")
  }
  ```
- **Output:** `{ packed_count: number }`
- **ErrorCodes:** `PACK_FAILED`
- **Status:** v1.0 candidate

#### E6 — `file_unpack_all`
- **Group:** file_io
- **Type:** composite
- **Description:** Extract all packed files to disk in folder relative to `.blend`.
- **Zod schema:**
  ```ts
  {
    target_folder: z.string().optional().describe("Extract to folder (default textures/ subfolder)")
  }
  ```
- **Output:** `{ unpacked_count: number }`
- **ErrorCodes:** `UNPACK_FAILED`, `PERMISSION_DENIED`
- **Status:** v1.0 candidate

#### E7 — `exec_python` — **NOT SHIPPED BY DEFAULT**
- **Group:** admin (private)
- **Type:** primitive
- **Description:** **SECURITY RISK.** Execute arbitrary Python code inside Blender. **Requires env flag `BLENDER_AGENT_ALLOW_EXEC=1` to enable.** Use only for trusted agent workflows; never expose to untrusted input. **Recommendation:** Ship as opt-in diagnostic tool, not default capability.
- **Zod schema:**
  ```ts
  {
    code: z.string().describe("Python code to execute"),
    globals_dict: z.record(z.unknown()).optional().describe("Pre-populated globals (optional)")
  }
  ```
- **Output:** `{ executed: boolean, result: unknown, error_message?: string }`
- **Warnings:** `["SECURITY: exec_python is dangerous. Only enable BLENDER_AGENT_ALLOW_EXEC=1 for trusted workflows. Never expose this tool to untrusted input."]`
- **ErrorCodes:** `EXEC_DISABLED`, `SYNTAX_ERROR`, `RUNTIME_ERROR`
- **Status:** **v1.1 candidate** (deferred to post-release, opt-in only)
- **Python outline (if enabled):**
  ```python
  @handler("POST", "/admin/exec_python")
  def exec_python(req):
    if not os.getenv("BLENDER_AGENT_ALLOW_EXEC"):
      raise HandlerError("EXEC_DISABLED", "exec_python requires BLENDER_AGENT_ALLOW_EXEC=1")
    def main():
      try:
        result = eval(req["code"], req.get("globals_dict", {}))
        return {"executed": True, "result": str(result)}
      except Exception as e:
        raise HandlerError("RUNTIME_ERROR", str(e))
    return run_on_main(main)
  ```

---

## Feasibility Verdict

| Sub-domain | Tools | v1.0 Ready | Constraints | Notes |
|---|---|---|---|---|
| **A — Lighting** | 5 | ✅ Yes | Light Linking is 4.2+; doesn't export to FBX/UE. | All CRUD ops supported natively. |
| **B — Camera** | 4 | ✅ Yes | Composition guides are read-only. Framing via context-override ops. | Full lens control available. |
| **C — Render** | 7 | ✅ Yes | Engine enum is `BLENDER_EEVEE_NEXT` (not `EEVEE`) in 4.2+. Modal operators need timeout protection. | Still + animation rendering proven. |
| **D — Scene/Collection/Library/Asset** | 11 | ⚠️ Partial | Library Override has known fragility. Resync can break hierarchies. Asset cataloging requires `.cats.txt` file management. | Link / Override / Make-Local all exist; require caution. |
| **E — File IO** | 7 (6 + 1 deferred) | ✅ Yes (E1-E6) | `exec_python` deferred to v1.1, behind env flag. | Save / Open / Append / Pack / Unpack proven. |

---

## Entity Types Touched (ID Chains)

| Entity | Example Refs | Tools That Chain |
|---|---|---|
| `lightName` | `"Sunlight"` | light_create → light_set_transform → light_configure_linking |
| `cameraName` | `"Camera"` | camera_create → camera_set_dof → camera_set_active |
| `sceneName` | `"Scene"` | scene_create → scene_set_active → render_set_engine |
| `collectionName` | `"Characters"` | collection_create → collection_move_objects |
| `objectName` (light) | `"Light.001"` | light_create (output) → world_set_hdri (input as owner) |
| `layerName` | `"Render.Lights"` | view_layer_create → (layer-specific render) |
| `linkedNames[]` | `["Character.001", "Rig.001"]` | library_link → library_make_override → library_resync |
| `assetName` | `"Asset.Rigged_Character"` | asset_mark → (Asset Browser discovery) |
| `filepath` | `"/output/frame_####.png"` | render_still_image / render_animation (outputs) |

---

## Open Issues / Questions

### A — Lighting

1. **Light Linking API maturity (4.2):** Is `light.linking` fully stable, or are there known regressions in 4.2.0 LTS?
   - **Recommendation:** Ship as v1.0; document as "experimental in 4.2".

2. **Light Groups UI consistency:** Are light groups named via `scene.view_layers[i].lightgroups` or a separate collection?
   - **Research needed:** Verify enum API vs direct object access in 4.2.

3. **HDRI node tree creation:** Does `scene.world.node_tree` auto-create if None, or must we create it manually?
   - **Recommendation:** Create manually; check for None; emit warning if already has nodes.

### B — Camera

1. **Composition guides:** Can composition guides be toggled without context override, or are they view-only UI flags?
   - **Answer (verified):** Read-only flags only. No way to edit guide positions programmatically. Document as limitation.

2. **Background images:** `camera.background_images` collection is available. Should we expose a tool for adding background reference images?
   - **Recommendation:** Defer to v1.1; not essential for v1.0 export pipeline.

### C — Render

1. **Engine enum in 4.2:** Confirm `'BLENDER_EEVEE_NEXT'` is correct enum value (not `'BLENDER_EEVEE'`).
   - **Verified:** Yes, 4.2+ uses `'BLENDER_EEVEE_NEXT'`. Legacy `'BLENDER_EEVEE'` removed.

2. **Render timeout:** How to gracefully cancel a long-running `bpy.ops.render.render()` from HTTP handler?
   - **Recommendation:** Use 30-second handler timeout; if render not done, return `errorCode: "RENDER_TIMEOUT"`. Render continues in background (Blender process continues).

3. **Viewport screenshot with shading modes:** Does `bpy.ops.screen.screenshot` respect current viewport shading (Material Preview, Rendered, etc.)?
   - **Recommendation:** Document as limitation; screenshot uses current viewport state. No API to change shading programmatically.

### D — Scene / Collection / Library / Asset

1. **Library Override fragility:** What is the documented minimum-safe upgrade path from linked data → override?
   - **Recommendation:** Document as "expert-only"; provide `library_resync` tool; warn in docstrings.

2. **Asset catalog files:** Must `.blend_assets.cats.txt` exist before asset marking, or is it created on-demand?
   - **Research needed:** Test asset_mark on a fresh library folder; check if catalog auto-creates.

3. **Collection exports:** Are `collection.export_*` fields used for anything, or are they deprec ated?
   - **Recommendation:** Investigate; defer unless needed for v1.0.

### E — File IO

1. **Relative path handling:** When saving with `relative_paths=True`, does Blender automatically rewrite texture paths, or must we do it manually?
   - **Recommendation:** Ship as default behavior; document in tool description.

2. **`exec_python` security:** Should this be a MCP tool at all, or only a diagnostic HTTP endpoint behind admin auth?
   - **Recommendation:** **Do NOT ship as MCP tool in v1.0.** Implement behind optional HTTP-only admin endpoint with env flag. Revisit in v1.1 with hardened sandboxing.

3. **`exec_python` alternatives:** For v1.0, can we satisfy 95% of use cases with composite tools instead of raw eval?
   - **Recommendation:** Yes. Ship `exec_python` as v1.1 deferred, opt-in feature.

---

## Conclusion: exec_python Policy (Critical)

**Explicit Recommendation:**

Do **NOT ship `exec_python` as a standard MCP tool in v1.0**. Instead:

1. **Defer to v1.1** as a diagnostic-only feature.
2. **Opt-in enforcement:** Behind env flag `BLENDER_AGENT_ALLOW_EXEC=1`.
3. **HTTP-only:** Never expose via MCP protocol; reserve for trusted direct-use workflows.
4. **Rationale:**
   - Arbitrary Python execution inside Blender can trigger GPU driver crashes, infinite loops, data corruption.
   - No sandboxing in Blender; `exec_python` runs with full addon privileges.
   - Better design: **compose primitives into composite tools** to handle 99% of workflows without eval.
   - Example: instead of `exec_python("bpy.ops.object.shade_smooth()")`, ship `object_shade_smooth()` tool.

**For v1.0, ship E1-E6 (file IO primitives). Omit E7. Revisit in v1.1 with security model.**

---

## Blender 4.2 API References (Cited)

- Light types & parameters: https://docs.blender.org/api/current/bpy.types.Light.html
- Camera data: https://docs.blender.org/api/current/bpy.types.Camera.html
- RenderSettings: https://docs.blender.org/api/current/bpy.types.RenderSettings.html
- Scene: https://docs.blender.org/api/current/bpy.types.Scene.html
- Collection: https://docs.blender.org/api/current/bpy.types.Collection.html
- Library: https://docs.blender.org/api/current/bpy.types.Library.html
- World (HDRI): https://docs.blender.org/api/current/bpy.types.World.html

---

## Summary: Tool Count & Status

**Part A (Lighting):** 5 tools, all v1.0 candidate  
**Part B (Camera):** 4 tools, all v1.0 candidate  
**Part C (Render):** 7 tools, all v1.0 candidate  
**Part D (Scene/Collection/Library/Asset):** 11 tools, 10 v1.0 + 1 v1.1 (override resync for fragility)  
**Part E (File IO):** 7 tools, 6 v1.0 + 1 v1.1 deferred (exec_python, opt-in safety)  

**Total: 34 tools proposed for B9 domain. 32 v1.0-ready, 2 deferred to v1.1 with safety rationale.**