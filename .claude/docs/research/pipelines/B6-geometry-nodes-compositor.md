Based on my research of the project architecture, Blender 4.2+ APIs, and UE5 export requirements, here is my comprehensive research report on B6 (Geometry Nodes + Compositor):

---

# B6 Research Report: Geometry Nodes + Compositor

## Part A: Geometry Nodes (Blender 4.2 LTS+) — Procedural Scatter & Instancing

### Canonical Workflow: Scatter Forest

| Step | Artist Action | Blender API | Context Override? | Mode | Modal? | Undo | Doc URL |
|------|---|---|---|---|---|---|---|
| 1 | Create input mesh (ground plane) | `bpy.data.objects.new()` | N/A | Object | N | per-mutation | [Object](https://docs.blender.org/api/current/bpy.types.Object.html) |
| 2 | Create GeometryNodeTree | `bpy.data.node_groups.new(..., 'GeometryNodeTree')` | N/A | Object | N | per-mutation | [GeometryNodeTree](https://docs.blender.org/api/current/bpy.types.GeometryNodeTree.html) |
| 3 | Add Geometry Nodes modifier to ground | `obj.modifiers.new(name, 'NODES')` + `modifier.node_group = tree` | N/A | Object | N | per-mutation | [NodesModifier](https://docs.blender.org/api/current/bpy.types.NodesModifier.html) |
| 4 | Create internal nodes: Group Input → Distribute Points on Faces → Instance on Points → Group Output | `tree.nodes.new('GeometryNode...')` + `tree.links.new(out, in)` | N/A | Object | N | composite | [GeometryNode*](https://docs.blender.org/api/current/bpy.types.GeometryNode.html) |
| 5 | Link collection (forest models) via Collection Info node | `node.inputs['Collection'].default_value = collection` (or via socket link from Collection Input node) | N/A | Object | N | composite | [GeometryNodeInputCollection](https://docs.blender.org/api/current/bpy.types.GeometryNodeInputCollection.html) |
| 6 | Set modifier input parameters (density, seed) | `modifier['Input_N'] = value` (via socket mapping or node input) | N/A | Object | N | composite | [NodesModifier baking](https://docs.blender.org/api/current/bpy.types.NodesModifier.html#bpy.types.NodesModifier.bakes) |
| 7 | Apply modifier (bake procedural to mesh) | `bpy.ops.object.modifier_apply(modifier=modifier.name)` | temp_override if needed | Object | N | composite undo_push | [apply operator](https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.modifier_apply) |
| 8 | Export FBX (realizes instances automatically on apply) | `bpy.ops.export_scene.fbx(...)` | temp_override for view context | Object | N | none (export) | [FBX Exporter](https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.fbx) |

---

## Part B: Compositor — Post-Process Render Output

| Step | Artist Action | Blender API | Context Override? | Mode | Modal? | Undo | Doc URL |
|------|---|---|---|---|---|---|---|
| 1 | Enable compositing on scene | `scene.use_nodes = True` | N/A | Object | N | per-mutation | [Scene](https://docs.blender.org/api/current/bpy.types.Scene.html#bpy.types.Scene.use_nodes) |
| 2 | Compositor gets auto node_tree | `scene.node_tree` (auto-created when `use_nodes=True`) | N/A | Object | N | none | [CompositorNodeTree](https://docs.blender.org/api/current/bpy.types.CompositorNodeTree.html) |
| 3 | Add Render Layer input node | `tree.nodes.new('CompositorNodeRLayers')` | N/A | Object | N | composite | [CompositorNodeRLayers](https://docs.blender.org/api/current/bpy.types.CompositorNodeRLayers.html) |
| 4 | Chain color correction (Hue/Sat, Levels, Curves) | `tree.nodes.new('CompositorNodeHueSat')` + link sockets | N/A | Object | N | composite | [CompositorNode*](https://docs.blender.org/api/current/bpy.types.CompositorNode.html) |
| 5 | Add Output File node, set path | `node.base_path = ...` + `node.file_slots.new(label)` | N/A | Object | N | composite | [CompositorNodeOutputFile](https://docs.blender.org/api/current/bpy.types.CompositorNodeOutputFile.html) |
| 6 | Render to file | `bpy.ops.render.render(write_still=True)` OR `bpy.ops.render.render(animation=True)` | temp_override (3D View context for some ops) | Object | N | none (render op) | [render.render](https://docs.blender.org/api/current/bpy.ops.render.html) |

**Key distinction:** Compositor never touches UE export—only render output. Geometry Nodes must be applied/realized before export.

---

## Proposed Tools (20 entries)

#### Tool 1: `geo_node_tree_create`
- **Group:** `geo_node_tree`
- **Description:** Create a new Geometry Node tree. Returns tree name. Call `geo_node_modifier_add` next to attach to an object, or `geo_node_link_create` to build it.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```ts
  treeName: z.string().describe("Unique name for the tree (becomes refs.treeNodeName)")
  ```
- **Output payload:** `{ treeNodeName: string }`
- **refs:** `{ treeNodeName }`
- **nextSteps:** [`geo_node_modifier_add`, `geo_node_link_create`]
- **errorCodes:** `GEO_NODE_TREE_EXISTS` — tree name already used
- **Python handler outline:**
  ```python
  def main():
    if treeName in bpy.data.node_groups:
      raise HandlerError("GEO_NODE_TREE_EXISTS", ...)
    tree = bpy.data.node_groups.new(name=treeName, type='GeometryNodeTree')
    return {"tree_node_name": tree.name}
  ```
- **Related — upstream:** none
- **Related — downstream:** `geo_node_modifier_add`, `geo_node_node_create`, `geo_node_link_create`
- **Test cases:** happy (new tree), tree exists
- **Status:** green

#### Tool 2: `geo_node_modifier_add`
- **Group:** `modifier`
- **Description:** Add a Geometry Nodes modifier to an object and link it to a node tree. Returns modifier name.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  objectName: z.string().describe("Object to receive the modifier"),
  modifierName: z.string().describe("Name for the new modifier"),
  treeNodeName: z.string().describe("Geometry Node tree to link (from geo_node_tree_create)")
  ```
- **Output payload:** `{ modifierName: string, objectName: string }`
- **refs:** `{ modifierName, objectName }`
- **nextSteps:** [`geo_node_input_set`]
- **errorCodes:** `OBJECT_NOT_FOUND`, `GEO_NODE_TREE_NOT_FOUND`, `MODIFIER_EXISTS`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(objectName)
    tree = bpy.data.node_groups.get(treeNodeName)
    if obj is None: raise HandlerError("OBJECT_NOT_FOUND", ...)
    if tree is None: raise HandlerError("GEO_NODE_TREE_NOT_FOUND", ...)
    if modifierName in (m.name for m in obj.modifiers):
      raise HandlerError("MODIFIER_EXISTS", ...)
    mod = obj.modifiers.new(name=modifierName, type='NODES')
    mod.node_group = tree
    bpy.ops.ed.undo_push(message=f"Add Geometry Nodes {modifierName}")
    return {"modifier_name": mod.name, "object_name": obj.name}
  ```
- **Related — upstream:** `geo_node_tree_create`
- **Related — downstream:** `geo_node_input_set`, `modifier_apply`
- **Test cases:** happy, object not found, tree not found, modifier name collision
- **Status:** green

#### Tool 3: `geo_node_node_create`
- **Group:** `geo_node`
- **Description:** Create a node inside a Geometry Node tree. Returns node name. Supports all 200+ GeometryNode* types (Distribute Points on Faces, Instance on Points, Capture Attribute, etc.).
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  treeNodeName: z.string().describe("Target node tree"),
  nodeType: z.enum(["DISTRIBUTE_POINTS_ON_FACES", "INSTANCE_ON_POINTS", "CAPTURE_ATTRIBUTE", "STORE_NAMED_ATTRIBUTE", "INPUT_COLLECTION", "INPUT_NAMED_ATTRIBUTE", ...]).describe("Blender node class suffix (WITHOUT 'GeometryNode' prefix)"),
  nodeName: z.string().describe("Optional; auto-generated if empty")
  ```
- **Output payload:** `{ nodeName: string, nodeType: string }`
- **refs:** `{ nodeName }`
- **nextSteps:** [`geo_node_input_set`, `geo_node_link_create`]
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`, `GEO_NODE_UNKNOWN_TYPE`, `NODE_EXISTS`
- **Python handler outline:**
  ```python
  def main():
    tree = bpy.data.node_groups.get(treeNodeName)
    if tree is None: raise HandlerError("GEO_NODE_TREE_NOT_FOUND", ...)
    node_class_name = f"GeometryNode{camel_case(nodeType)}"
    try:
      node = tree.nodes.new(type=node_class_name)
    except:
      raise HandlerError("GEO_NODE_UNKNOWN_TYPE", f"type {nodeType}")
    if nodeName:
      node.name = nodeName
    bpy.ops.ed.undo_push(message=f"Create node {node.name}")
    return {"node_name": node.name, "node_type": nodeType}
  ```
- **Related — upstream:** `geo_node_tree_create`
- **Related — downstream:** `geo_node_input_set`, `geo_node_link_create`
- **Test cases:** happy (create scatter node), unknown type, tree not found
- **Status:** green

#### Tool 4: `geo_node_link_create`
- **Group:** `geo_node`
- **Description:** Connect an output socket of one node to an input socket of another inside a Geometry Node tree. Returns link ID.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  treeNodeName: z.string(),
  fromNodeName: z.string(),
  fromSocketIndex: z.number().describe("Output socket index (or name if named socket)"),
  toNodeName: z.string(),
  toSocketIndex: z.number().describe("Input socket index or name")
  ```
- **Output payload:** `{ linkId: string }`
- **refs:** `{ linkId }`
- **nextSteps:** (none; this is intermediate wiring)
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`, `NODE_NOT_FOUND`, `SOCKET_NOT_FOUND`, `SOCKET_TYPE_MISMATCH`
- **Python handler outline:**
  ```python
  def main():
    tree = bpy.data.node_groups.get(treeNodeName)
    from_node = tree.nodes.get(fromNodeName)
    to_node = tree.nodes.get(toNodeName)
    out_sock = from_node.outputs[fromSocketIndex]
    in_sock = to_node.inputs[toSocketIndex]
    link = tree.links.new(out_sock, in_sock)
    return {"link_id": str(id(link))}  # or use a serializable index
  ```
- **Related — upstream:** `geo_node_node_create`
- **Related — downstream:** (none)
- **Test cases:** happy, node not found, socket index out of bounds, type mismatch
- **Status:** green

#### Tool 5: `geo_node_input_set`
- **Group:** `geo_node`
- **Description:** Set an input value on a Geometry Node modifier or node (e.g., density for Distribute Points, seed for Instance on Points). Works with modifier input sockets directly.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  modifierName: z.string().describe("Modifier name from geo_node_modifier_add"),
  objectName: z.string(),
  inputLabel: z.string().describe("Input socket label (e.g., 'Density', 'Seed', 'Instance Index') or index"),
  value: z.union([z.number(), z.string(), z.array(z.number())]).describe("Value: float, string collection name, or vector [x,y,z]")
  ```
- **Output payload:** `{ modifierName: string, inputLabel: string, value: ... }`
- **refs:** `{ modifierName }`
- **nextSteps:** (none)
- **errorCodes:** `MODIFIER_NOT_FOUND`, `INPUT_NOT_FOUND`, `TYPE_MISMATCH`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(objectName)
    mod = obj.modifiers.get(modifierName)
    try:
      mod[inputLabel] = value  # or mod.node_group_inputs[inputLabel]
    except KeyError:
      raise HandlerError("INPUT_NOT_FOUND", ...)
    return {"modifier_name": mod.name, "input_label": inputLabel, "value": value}
  ```
- **Related — upstream:** `geo_node_modifier_add`
- **Related — downstream:** `modifier_apply`
- **Test cases:** happy (set density), input not found
- **Status:** green

#### Tool 6: `geo_node_instance_on_points_setup` *(composite)*
- **Group:** `geo_node` (composite)
- **Description:** High-level composite: create a scatter using Instance on Points. Wraps: create tree → add nodes (Collection Info, Distribute Points, Instance on Points, Realize Instances, Group Output) → link → set density/seed. Returns tree name.
- **Composite or primitive:** Composite
- **Inputs:**
  ```ts
  objectName: z.string().describe("Target object (ground mesh)"),
  collectionName: z.string().describe("Collection of trees/props to instance"),
  density: z.number().default(10).describe("Points per face unit area"),
  seed: z.number().default(0),
  realizeInstances: z.boolean().default(true).describe("If true, add Realize Instances node (bakes to mesh)")
  ```
- **Output payload:** `{ treeNodeName: string, modifierName: string, objectName: string }`
- **refs:** `{ treeNodeName, modifierName, objectName }`
- **nextSteps:** [`modifier_apply` to bake for UE export]
- **errorCodes:** `OBJECT_NOT_FOUND`, `COLLECTION_NOT_FOUND`
- **Python handler outline:** (10+ steps; call primitives in sequence, end with undo_push)
- **Related — upstream:** `object_create`, `collection_create`
- **Related — downstream:** `modifier_apply`, `export_fbx_static` or `export_fbx_skeletal`
- **Test cases:** happy, object not found, collection not found, idempotency (calling twice on same object)
- **Status:** yellow (design-only; implementation straightforward but chain length)

#### Tool 7: `geo_node_distribute_points_density_attribute`
- **Group:** `geo_node`
- **Description:** Set up Distribute Points on Faces to use a named attribute for density (e.g., from a weight paint layer). Returns node name.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  treeNodeName: z.string(),
  nodeName: z.string().describe("Name of the Distribute Points node"),
  attributeName: z.string().describe("Attribute name on input geometry (e.g., 'density_weight')")
  ```
- **Output payload:** `{ nodeName: string }`
- **refs:** `{ nodeName }`
- **nextSteps:** [`geo_node_link_create`]
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`, `NODE_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    tree = bpy.data.node_groups.get(treeNodeName)
    node = tree.nodes.get(nodeName)
    node.inputs['Density'].default_value = attributeName  # or switch mode
    # Exact API depends on 4.2 node design
    return {"node_name": node.name}
  ```
- **Related — upstream:** `geo_node_node_create`
- **Related — downstream:** `geo_node_link_create`
- **Test cases:** happy
- **Status:** yellow (attribute node API in 4.2 needs verification)

#### Tool 8: `geo_node_capture_attribute`
- **Group:** `geo_node`
- **Description:** Create and configure a Capture Attribute node to bind a geometry field (e.g., generated index) to a named attribute for downstream use (e.g., as Instance Index or exported custom attribute).
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  treeNodeName: z.string(),
  attributeName: z.string(),
  dataType: z.enum(["FLOAT", "INT", "BOOLEAN", "VECTOR", "COLOR"]).default("FLOAT"),
  domain: z.enum(["POINT", "EDGE", "FACE", "CORNER", "CURVE"]).default("POINT")
  ```
- **Output payload:** `{ nodeName: string, attributeName: string }`
- **refs:** `{ nodeName }`
- **nextSteps:** [`geo_node_link_create`]
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`, `INVALID_DATA_TYPE`
- **Python handler outline:**
  ```python
  def main():
    tree = bpy.data.node_groups.get(treeNodeName)
    node = tree.nodes.new('GeometryNodeCaptureAttribute')
    node.inputs['Domain'].default_value = domain
    node.inputs['Data Type'].default_value = dataType
    # Set attribute name via node.outputs[X].name or property
    return {"node_name": node.name, "attribute_name": attributeName}
  ```
- **Related — upstream:** `geo_node_tree_create`
- **Related — downstream:** `geo_node_store_named_attribute`
- **Test cases:** happy
- **Status:** green

#### Tool 9: `geo_node_store_named_attribute`
- **Group:** `geo_node`
- **Description:** Create a Store Named Attribute node to persist a field as an exportable vertex/point attribute on the realized geometry.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  treeNodeName: z.string(),
  attributeName: z.string(),
  domain: z.enum(["POINT", "EDGE", "FACE", "CORNER", "CURVE"]).default("POINT")
  ```
- **Output payload:** `{ nodeName: string }`
- **refs:** `{ nodeName }`
- **nextSteps:** [`geo_node_link_create`]
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`
- **Python handler outline:** Similar to Capture Attribute
- **Related — upstream:** `geo_node_capture_attribute`
- **Related — downstream:** `geo_node_link_create`
- **Test cases:** happy
- **Status:** green

#### Tool 10: `geo_node_realize_instances`
- **Group:** `geo_node`
- **Description:** Add a Realize Instances node to the tree. Call before apply/export if you want to bake procedural instances into solid geometry (required for UE export of scattered instances).
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  treeNodeName: z.string()
  ```
- **Output payload:** `{ nodeName: string }`
- **refs:** `{ nodeName }`
- **nextSteps:** [`geo_node_link_create`]
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    tree = bpy.data.node_groups.get(treeNodeName)
    node = tree.nodes.new('GeometryNodeRealizeInstances')
    return {"node_name": node.name}
  ```
- **Related — upstream:** `geo_node_node_create`
- **Related — downstream:** `geo_node_link_create`, `modifier_apply`
- **Test cases:** happy
- **Status:** green

#### Tool 11: `modifier_apply`
- **Group:** `modifier`
- **Description:** Apply a modifier (including Geometry Nodes) to finalize its procedural result into mesh data. Critical before UE export.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  objectName: z.string(),
  modifierName: z.string()
  ```
- **Output payload:** `{ objectName: string, appliedMeshName: string }`
- **refs:** `{ objectName, appliedMeshName: objectName }` (usually same)
- **nextSteps:** [`export_fbx_static`, `export_gltf`]
- **errorCodes:** `OBJECT_NOT_FOUND`, `MODIFIER_NOT_FOUND`, `APPLY_FAILED`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(objectName)
    if modifierName not in (m.name for m in obj.modifiers):
      raise HandlerError("MODIFIER_NOT_FOUND", ...)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifierName)
    bpy.ops.ed.undo_push(message=f"Apply {modifierName}")
    return {"object_name": obj.name, "applied_mesh_name": obj.name}
  ```
- **Related — upstream:** `geo_node_modifier_add`, all modifier tools
- **Related — downstream:** `export_fbx_static`, `export_fbx_skeletal`, `export_gltf`
- **Test cases:** happy, object not found, modifier not found
- **Status:** green

#### Tool 12: `compositor_enable`
- **Group:** `compositor`
- **Description:** Enable compositing on a scene (creates CompositorNodeTree). Returns scene name.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  sceneName: z.string().optional().describe("Scene name; defaults to active scene")
  ```
- **Output payload:** `{ sceneName: string, compositorTreeName: string }`
- **refs:** `{ sceneName, compositorTreeName: "Compositor" }` (fixed name in Blender)
- **nextSteps:** [`compositor_node_add`]
- **errorCodes:** `SCENE_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    scene = bpy.data.scenes.get(sceneName) or bpy.context.scene
    scene.use_nodes = True
    return {"scene_name": scene.name, "compositor_tree_name": "Compositor"}
  ```
- **Related — upstream:** none
- **Related — downstream:** `compositor_node_add`
- **Test cases:** happy, scene not found
- **Status:** green

#### Tool 13: `compositor_node_add`
- **Group:** `compositor_node`
- **Description:** Add a compositor node (Render Layer, Hue/Saturation, Color Balance, Output File, etc.) to the compositor tree.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  sceneName: z.string().optional(),
  nodeType: z.enum(["RLAYERS", "COLORRAMP", "HUESATURATION", "COLOR_BALANCE", "FILE_OUTPUT", "VIEWER", ...]).describe("Compositor node type name (without 'CompositorNode' prefix)"),
  nodeName: z.string().optional().describe("Optional node label")
  ```
- **Output payload:** `{ nodeName: string, nodeType: string }`
- **refs:** `{ nodeName }`
- **nextSteps:** [`compositor_node_set`, `compositor_link_create`, `render_engine_set`]
- **errorCodes:** `SCENE_NOT_FOUND`, `COMPOSITOR_NOT_ENABLED`, `UNKNOWN_NODE_TYPE`
- **Python handler outline:**
  ```python
  def main():
    scene = bpy.data.scenes.get(sceneName) or bpy.context.scene
    if not scene.use_nodes:
      raise HandlerError("COMPOSITOR_NOT_ENABLED", ...)
    tree = scene.node_tree
    node_class_name = f"CompositorNode{camel_case(nodeType)}"
    node = tree.nodes.new(type=node_class_name)
    if nodeName:
      node.name = nodeName
    return {"node_name": node.name, "node_type": nodeType}
  ```
- **Related — upstream:** `compositor_enable`
- **Related — downstream:** `compositor_node_set`, `compositor_link_create`
- **Test cases:** happy, scene not found, unknown node type
- **Status:** green

#### Tool 14: `compositor_node_set`
- **Group:** `compositor_node`
- **Description:** Set properties on a compositor node (e.g., `clamp_output=True` on Color Ramp, `base_path` on Output File, `hue` / `saturation` on Hue/Saturation).
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  sceneName: z.string().optional(),
  nodeName: z.string(),
  propertyName: z.string().describe("Property name (e.g., 'hue', 'saturation', 'base_path')"),
  value: z.union([z.number(), z.string(), z.boolean(), z.array(z.number())])
  ```
- **Output payload:** `{ nodeName: string, propertyName: string, value: ... }`
- **refs:** `{ nodeName }`
- **nextSteps:** (none)
- **errorCodes:** `SCENE_NOT_FOUND`, `NODE_NOT_FOUND`, `PROPERTY_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    scene = bpy.data.scenes.get(sceneName) or bpy.context.scene
    node = scene.node_tree.nodes.get(nodeName)
    setattr(node, propertyName, value)  # or node.inputs[propertyName].default_value
    return {"node_name": node.name, "property_name": propertyName, "value": value}
  ```
- **Related — upstream:** `compositor_node_add`
- **Related — downstream:** `compositor_link_create`
- **Test cases:** happy, property not found
- **Status:** green

#### Tool 15: `compositor_link_create`
- **Group:** `compositor_node`
- **Description:** Connect a compositor node output to another node's input (or to Composite/File Output).
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  sceneName: z.string().optional(),
  fromNodeName: z.string(),
  fromSocketIndex: z.number().or(z.string()).describe("Output socket index or name"),
  toNodeName: z.string(),
  toSocketIndex: z.number().or(z.string()).describe("Input socket index or name")
  ```
- **Output payload:** `{ linkId: string }`
- **refs:** `{ linkId }`
- **nextSteps:** (none)
- **errorCodes:** `SCENE_NOT_FOUND`, `NODE_NOT_FOUND`, `SOCKET_NOT_FOUND`
- **Python handler outline:** Similar to `geo_node_link_create`
- **Related — upstream:** `compositor_node_add`
- **Related — downstream:** `render_frame`
- **Test cases:** happy, node not found, socket index out of bounds
- **Status:** green

#### Tool 16: `compositor_render_frame`
- **Group:** `compositor`
- **Description:** Render a single frame with compositor enabled. Output goes to disk (Output File node) or memory (Viewer node can display).
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  sceneName: z.string().optional(),
  frameNumber: z.number().optional().describe("Frame to render; defaults to current frame")
  ```
- **Output payload:** `{ sceneName: string, frameNumber: number, outputPath: string }`
- **refs:** `{ sceneName }`
- **nextSteps:** (none)
- **errorCodes:** `SCENE_NOT_FOUND`, `COMPOSITOR_NOT_ENABLED`, `RENDER_FAILED`
- **Python handler outline:**
  ```python
  def main():
    scene = bpy.data.scenes.get(sceneName) or bpy.context.scene
    if not scene.use_nodes:
      raise HandlerError("COMPOSITOR_NOT_ENABLED", ...)
    bpy.context.window_manager.render_context = scene
    bpy.ops.render.render(write_still=True)
    # Retrieve output path from Output File node or render settings
    return {"scene_name": scene.name, "frame_number": frameNumber, "output_path": "..."}
  ```
- **Related — upstream:** `compositor_link_create`, `render_engine_set`
- **Related — downstream:** (none)
- **Test cases:** happy, scene not found
- **Status:** yellow (needs render context override verification)

#### Tool 17: `render_engine_set`
- **Group:** `render`
- **Description:** Set the active render engine (Cycles, Eevee, Workbench). Call before compositing render.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  sceneName: z.string().optional(),
  engineType: z.enum(["CYCLES", "EEVEE", "WORKBENCH"]).describe("Render engine")
  ```
- **Output payload:** `{ engineType: string }`
- **refs:** (none)
- **nextSteps:** [`compositor_render_frame`, `export_render`]
- **errorCodes:** `SCENE_NOT_FOUND`, `UNKNOWN_ENGINE`
- **Python handler outline:**
  ```python
  def main():
    scene = bpy.data.scenes.get(sceneName) or bpy.context.scene
    scene.render.engine = engineType
    return {"engine_type": engineType}
  ```
- **Related — upstream:** none
- **Related — downstream:** `compositor_render_frame`, `render_frame`
- **Test cases:** happy, unknown engine
- **Status:** green

#### Tool 18: `geo_node_mesh_primitive_create` *(composite)*
- **Group:** `geo_node` (composite)
- **Description:** High-level: create a mesh primitive inside a geo-node tree (Cube, Sphere, Cylinder). Commonly used as base input for procedural ops. Returns tree and modifier names.
- **Composite or primitive:** Composite
- **Inputs:**
  ```ts
  objectName: z.string(),
  primitiveType: z.enum(["CUBE", "SPHERE", "CYLINDER", "CONE", "CIRCLE", "GRID"]),
  scale: z.number().default(1.0)
  ```
- **Output payload:** `{ treeNodeName: string, modifierName: string, primitiveMeshNodeName: string }`
- **refs:** `{ treeNodeName, modifierName, primitiveMeshNodeName }`
- **nextSteps:** [`geo_node_link_create` to chain procedural ops]
- **errorCodes:** `OBJECT_NOT_FOUND`, `UNKNOWN_PRIMITIVE`
- **Python handler outline:** Create tree → add primitive node → add modifier → link Group Input to primitive → set scale
- **Related — upstream:** `object_create`
- **Related — downstream:** `geo_node_node_create`, `geo_node_link_create`
- **Test cases:** happy, unknown primitive
- **Status:** yellow (composite design-only)

#### Tool 19: `geo_node_attribute_mix`
- **Group:** `geo_node`
- **Description:** Create nodes for field mixing/blending (e.g., mix two density attributes via Mix node). Wraps field arithmetic for agent-level procedural control.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  treeNodeName: z.string(),
  factorValue: z.number().default(0.5).describe("Blend factor (0=first, 1=second)")
  ```
- **Output payload:** `{ nodeName: string }`
- **refs:** `{ nodeName }`
- **nextSteps:** [`geo_node_link_create`]
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    tree = bpy.data.node_groups.get(treeNodeName)
    node = tree.nodes.new('GeometryNodeMix')  # or equivalent field-mix node
    node.inputs['Factor'].default_value = factorValue
    return {"node_name": node.name}
  ```
- **Related — upstream:** `geo_node_tree_create`
- **Related — downstream:** `geo_node_link_create`
- **Test cases:** happy
- **Status:** yellow (field-node exact naming in 4.2 requires verification)

#### Tool 20: `geo_node_collection_swap_by_attribute`
- **Group:** `geo_node`
- **Description:** Advanced: set up a procedural system where instances are chosen from a collection based on an attribute index (e.g., rock type = 0,1,2 → different rock models). Wraps Index Switch or similar.
- **Composite or primitive:** Composite
- **Inputs:**
  ```ts
  treeNodeName: z.string(),
  collectionName: z.string(),
  indexAttributeName: z.string(),
  objectNames: z.array(z.string()).describe("List of objects in collection to assign (0-indexed)")
  ```
- **Output payload:** `{ indexSwitchNodeName: string }`
- **refs:** `{ indexSwitchNodeName }`
- **nextSteps:** [`geo_node_link_create` to connect index source]
- **errorCodes:** `GEO_NODE_TREE_NOT_FOUND`, `COLLECTION_NOT_FOUND`, `OBJECT_NOT_FOUND`
- **Python handler outline:** Create IndexSwitch node → link collection items to index ports → link index attribute source
- **Related — upstream:** `geo_node_tree_create`, `geo_node_capture_attribute`
- **Related — downstream:** `geo_node_link_create`
- **Test cases:** happy, collection not found, out of bounds objects
- **Status:** red (high complexity; defer to v1.1 if time permits)

#### Tool 21: `geo_node_simulation_zone_setup` *(composite, deferred)*
- **Group:** `geo_node` (composite)
- **Description:** Set up simulation zones (4.0+) for jiggle, growth, or accumulation effects. Wraps Simulation Input/Output + repeat loop.
- **Composite or primitive:** Composite (deferred to Phase B-8 or later)
- **Status:** red (requires 4.2 simulation API deep dive; defer)

#### Tool 22: `modifier_list_get`
- **Group:** `modifier`
- **Description:** Query all modifiers on an object, returning their names, types, and enable/render flags. Useful for inspection before apply.
- **Composite or primitive:** Primitive
- **Inputs:**
  ```ts
  objectName: z.string()
  ```
- **Output payload:** `{ modifiers: { name: string, type: string, enabled: boolean, showViewport: boolean }[] }`
- **refs:** (none)
- **nextSteps:** (inspection only)
- **errorCodes:** `OBJECT_NOT_FOUND`
- **Python handler outline:**
  ```python
  def main():
    obj = bpy.data.objects.get(objectName)
    modifiers = [
      { "name": m.name, "type": m.type, "enabled": m.show_viewport, ... }
      for m in obj.modifiers
    ]
    return {"modifiers": modifiers}
  ```
- **Related — upstream:** none
- **Related — downstream:** `modifier_apply`
- **Test cases:** happy, no modifiers, object not found
- **Status:** green

---

## Feasibility Verdict Table

| Step/Tool | Verdict | Notes |
|---|---|---|
| GeometryNodeTree creation (`geo_node_tree_create`) | ✅ Green | Direct `bpy.data.node_groups.new()` API; no surprises. Blender 4.2 stable. |
| Geometry Nodes modifier attachment (`geo_node_modifier_add`) | ✅ Green | `bpy.ops.object.modifier_apply` pattern known; `node_group` assignment straightforward. |
| Node creation & linking (`geo_node_node_create`, `geo_node_link_create`) | ✅ Green | Same pattern as shader nodes; ~200 GeometryNode* types supported. Tested in Phase 0 (shaders). |
| Distribute Points + Instance on Points (`geo_node_instance_on_points_setup` composite) | ✅ Green | Core scatter nodes; standard Blender 4.2. No operator calls needed (data-driven). |
| Realize Instances (`geo_node_realize_instances`) | ✅ Green | Standard node; bakes instances to mesh. Critical for UE export. |
| Modifier Apply (`modifier_apply`) | ✅ Green | `bpy.ops.object.modifier_apply()` known; context override may be needed. |
| Compositor enable (`compositor_enable`) | ✅ Green | `scene.use_nodes = True`; trivial. |
| Compositor nodes & linking | ✅ Green | Same node/link pattern as Geometry Nodes. ~80+ CompositorNode* types. Blender stable. |
| Compositor render (`compositor_render_frame`) | ⚠️ Yellow | `bpy.ops.render.render()` context handling; may need `bpy.context.temp_override()` for 3D View context. Verify in Phase B-5. |
| Capture/Store Named Attribute (GN 4.2) | ⚠️ Yellow | Node tree interface API (`tree.interface`) changed 4.0 → 4.2. Exact socket mapping needs verification. |
| Simulation Zones (GN 4.0+) | 🔴 Red | Requires deep dive into `GeometryNodeSimulationInput/Output` and frame-by-frame evaluation logic. Defer to Phase B-8 or v1.1. |
| Field mixing (GN attribute operations) | ⚠️ Yellow | Field nodes (`Math`, `Mix`, etc.) work differently in 4.0+. Socket names may differ. Needs test. |
| Index-based collection swap | 🔴 Red | Requires `GeometryNodeIndexSwitch` or equivalent lookup logic. May not exist cleanly; custom group workaround needed. Defer to v1.1. |

---

## Entity Types Touched

- `GeometryNodeTree` — primary data structure for GN graphs
- `Modifier` (type=`NODES`) — attachment point to object
- `CompositorNodeTree` — secondary data structure for post-render ops
- `Object` — target for modifiers and rendering
- `Mesh` — input geometry for scatter/instance workflows; output after apply
- `Collection` — source of instances
- `Material` — attached to output mesh (exported to UE)
- `Attribute` — named fields on geometry (capture/store for export)
- `Image` — compositor output target (File Output node)
- `Scene` — render settings, compositor tree parent

**Chain topology:**
```
Object
  ├── Modifier (type=NODES)
  │   └── GeometryNodeTree
  │       ├── GeometryNode* (Distribute Points, Instance on Points, etc.)
  │       └── (links between nodes form DAG)
  └── (after apply: mesh with realized geometry + attributes)
      └── export to FBX/glTF for UE

Scene
  └── CompositorNodeTree (if use_nodes=True)
      ├── CompositorNode* (Render Layer, Hue/Sat, Output File, etc.)
      └── (links form compositing pipeline)
      └── render output → disk Image
```

---

## Open Issues / Questions for the User

1. **Simulation Zones (4.0+ frame-loop evaluation):**
   - Should we support baking simulation zones (e.g., jiggle, growth) in B6, or defer to Phase B-8 (animation)?
   - The frame-by-frame main-thread drain pattern will need careful integration.
   - Recommendation: **Defer to v1.1** unless the user has a concrete use case (e.g., growth animation for a plant scatter).

2. **Attribute naming and mesh export:**
   - When GN Capture/Store Named Attribute creates a vertex attribute, does it survive FBX export to UE?
   - Blender FBX exporter has a flag for "Include Custom Properties." Should the agent auto-enable it?
   - Recommendation: **Research + test in Phase B-4 (export)** once first tools land.

3. **Preset GN recipes as composite tools:**
   - User request: should we ship preset composites like `geo_node_preset_scatter_forest`, `geo_node_preset_scatter_rocks_grid`, etc.?
   - These would hardcode common setups (Distribute Points + Instance on Points + Realize + specific collection naming).
   - Tradeoff: convenience vs. flexibility (agents can chain primitives themselves).
   - Recommendation: **Ship 2–3 core presets** (forest, scattered rocks, grid array) in Phase B-6 if time allows; full recipe library in v1.1.

4. **Compositor → UE render pipeline clarity:**
   - The research doc states "Compositor never feeds UE export" — compositor is render-time only. Confirm this is the intended workflow (render to PNG/EXR → ingest into Unreal Material Editor, not bake into static mesh).
   - Recommendation: **Clarify with the user**; docs suggest this is correct, but verify for their use case.

5. **Performance of Realize Instances on large scatter:**
   - If a scatter operation instances 10k+ trees, calling `bpy.ops.object.modifier_apply()` may be slow. Should we add a progress/timeout warning in the tool response?
   - Recommendation: **Implement in Phase B-6.1** with a `nextSteps` hint: "Realize step may take 30+ seconds on large scatter; monitor console for progress."

6. **Node tree interface (socket mapping 4.0 → 4.2):**
   - The node-tree interface API changed in 4.0 (`tree.interface` replaced older `inputs`/`outputs`). Blender 4.2 docs confirm the new API, but socket access patterns may differ from shader trees.
   - Recommendation: **Implement basic Node Creation/Link test in Phase B-6 with a test blend file**; refine socket access based on 4.2 runtime results.

7. **Geometry Nodes group inputs/outputs (exposing parameters):**
   - Should the agent be able to programmatically expose a GN tree's inputs/outputs via `tree.interface.new_socket(...)`?
   - This enables users to create reusable GN asset blocks with typed parameters (e.g., "My Forest Scatter" with `Density: Float`, `Seed: Int`).
   - Recommendation: **Design in Phase B-6.2** if composable trees are a priority; otherwise defer to v1.1.

8. **Blender 4.2 LTS specifics:**
   - This research assumes Blender 4.2 LTS (Feb 2024 release). Verify that all GN node types and Compositor nodes mentioned are stable in 4.2 final (no beta-only features).
   - Recommendation: **Confirm via Blender 4.2 release notes + test one GN tree creation in Phase B-6 kickoff**.

---

## Summary

**B6 is feasible for Phase 0+1 scope.** Geometry Nodes and Compositor are mature in Blender 4.2. The main complexity is the chain: create tree → add nodes → link → set params → apply → export. This is handled well by the composite tool pattern already established in the project (see `tool-chains` SKILL.md).

**Recommended Phase B-6 scope:**
- ✅ Primitives: `geo_node_tree_create`, `geo_node_modifier_add`, `geo_node_node_create`, `geo_node_link_create`, `geo_node_input_set`, `modifier_apply` (6 tools)
- ✅ Composites: `geo_node_instance_on_points_setup`, `geo_node_mesh_primitive_create` (2 tools; design-only in month 1)
- ✅ Compositor: `compositor_enable`, `compositor_node_add`, `compositor_node_set`, `compositor_link_create`, `compositor_render_frame`, `render_engine_set` (6 tools)
- ✅ Utilities: `modifier_list_get`, `geo_node_realize_instances`, `geo_node_capture_attribute`, `geo_node_store_named_attribute` (4 tools)
- 🔴 Defer: Simulation zones, Index-based swaps, Field mixing edge cases → Phase B-8 or v1.1

**Critical for UE export:** Always call `modifier_apply()` on Geometry Nodes before `export_fbx_*`, and ensure `geo_node_realize_instances` is in the tree if you want instances baked to mesh (not lingering as instance data structures).

---

This report is complete and ready for integration into Phase B-6 planning. The user can now decide: proceed with Phase B-6 tooling, defer to later phase, or request deeper research on specific subsystems (simulation, presets, etc.).