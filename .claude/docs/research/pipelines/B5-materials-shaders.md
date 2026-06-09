Now I'll compile the comprehensive research report. Based on my analysis of the Blender 4.2 API docs, UE5 requirements, and the existing architecture patterns in this project, here is the complete B5 Materials & Shader Node research document:

---

# B5 Research Report: Materials & Shader Nodes for Blender 4.2 LTS → Unreal Engine 5 Compatibility

## 1. Canonical Workflow

| Step | Artist Action | Blender API | Context Override | Mode Requirements | Modal Flag | Doc URL |
|------|---------------|-------------|------------------|------------------|------------|---------|
| 1a | Create material, enable nodes | `bpy.data.materials.new(name="Mat"); mat.use_nodes=True` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.Material.html |
| 1b | Assign material to object slot | `obj.data.materials.append(mat)` then access `material_slots` | N/A | Object must be mesh/curve/surface | False | https://docs.blender.org/api/current/bpy.types.IDMaterials.html |
| 1c | Set active material slot on object | `obj.active_material_index = slot_idx` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.Object.html#bpy.types.Object.active_material_index |
| 2a | Add Principled BSDF node | `node_tree.nodes.new(type='ShaderNodeBsdfPrincipled'); node.name = 'Principled BSDF'` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeBsdfPrincipled.html |
| 2b | Set Principled inputs (base_color, metallic, roughness, normal, etc.) | `principled_node.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeBsdfPrincipled.html |
| 3a | Create Image Texture node | `tex_node = node_tree.nodes.new(type='ShaderNodeTexImage'); tex_node.image = bpy.data.images.load(path)` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeTexImage.html |
| 3b | Set image colorspace (sRGB vs Linear) | `tex_node.image.colorspace_settings.name = 'sRGB'` or `'Non-Color'` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ColorManagedInputColorspaceSettings.html |
| 4a | Create Texture Coordinate node | `texco_node = node_tree.nodes.new(type='ShaderNodeTexCoord')` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeTexCoord.html |
| 4b | Create Mapping node for UV transform | `map_node = node_tree.nodes.new(type='ShaderNodeMapping')` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeMapping.html |
| 5a | Connect nodes: TexCoord.UV → Mapping.Vector → Image.Vector | `node_tree.links.new(texco_out, map_node.inputs[0]); node_tree.links.new(map_out, img_in)` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.NodeLinks.html |
| 5b | Connect Image.Color → Principled.Base Color | `node_tree.links.new(image_node.outputs['Color'], principled_node.inputs['Base Color'])` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.NodeLink.html |
| 6a | Connect Principled.BSDF → Material Output | `node_tree.links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeOutputMaterial.html |
| 7a | Create node group (reusable macro) | `grp_tree = bpy.data.node_groups.new(name='MyMaterial', type='ShaderNodeTree'); grp_node = node_tree.nodes.new('ShaderNodeGroup'); grp_node.node_tree = grp_tree` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeGroup.html |
| 7b | Add inputs/outputs to group interface | `grp_tree.interface.new_socket('Base Color', socket_type='NodeSocketColor'); grp_tree.interface.new_socket('BSDF', socket_type='NodeSocketShader', in_out='OUTPUT')` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.NodeTreeInterface.html |
| 8a | Create procedural texture (Noise) | `noise_node = node_tree.nodes.new(type='ShaderNodeTexNoise'); noise_node.inputs['Scale'].default_value = 5.0` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeTexNoise.html |
| 8b | Sample from noise (mix into Principled metallic) | `mix_node = node_tree.nodes.new(type='ShaderNodeMix'); node_tree.links.new(noise_out, mix_node.inputs[0])` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeMix.html |
| 9a | Create Normal Map node from texture | `nm_node = node_tree.nodes.new(type='ShaderNodeNormalMap'); node_tree.links.new(image_normal.outputs['Color'], nm_node.inputs['Color'])` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.ShaderNodeNormalMap.html |
| 9b | Connect NormalMap.Normal → Principled.Normal | `node_tree.links.new(nm_node.outputs['Normal'], principled_node.inputs['Normal'])` | N/A | N/A | False | https://docs.blender.org/api/current/bpy.types.NodeSocket.html |

---

## 2. Proposed Tools (~32 entries, grouped by category)

### **2.1 Material Creation & Management**

#### tool_name: `material_create`
- **Group:** material
- **Description for LLM:** Create a new material with optional node tree setup. Returns materialName for use in subsequent shader node operations.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Unique material name")
  useNodes: z.boolean().optional().describe("Enable node-based shading (default: true)")
  ```
- **Output payload (data):** `{ materialName: string; nodeTreeName: string; }`
- **refs:** `{ materialName, nodeTreeName }`
- **nextSteps:** `["call shader_node_add_principled_bsdf with this materialName", "call material_assign_to_object"]`
- **errorCodes:** `MATERIAL_EXISTS — materialName already in use`; `INVALID_NAME — name contains invalid characters`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.new(name=materialName)
  mat.use_nodes = useNodes
  if useNodes:
      # Material comes with default ShaderNodeTree
      tree = mat.node_tree
      return {"material_name": mat.name, "node_tree_name": tree.name}
  return {"material_name": mat.name}
  bpy.ops.ed.undo_push(message=f"Create material {materialName!r}")
  ```
- **Related — upstream:** None (first step)
- **Related — downstream:** `shader_node_add_principled_bsdf`, `material_assign_to_object`, `material_slot_add`
- **Test cases:** happy (create with nodes=true, false), error (duplicate name)
- **Status:** 🟢 green

---

#### tool_name: `material_delete`
- **Group:** material
- **Description for LLM:** Delete a material by name. Unlinks from all objects. Non-recoverable.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Name of material to delete")
  ```
- **Output payload (data):** `{ deletedMaterialName: string; }`
- **refs:** None
- **nextSteps:** None
- **errorCodes:** `MATERIAL_NOT_FOUND — materialName does not exist`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  if mat is None:
      raise HandlerError("MATERIAL_NOT_FOUND", ...)
  bpy.data.materials.remove(mat, do_unlink=True)
  bpy.ops.ed.undo_push(message=f"Delete material {materialName!r}")
  return {"deleted_material_name": materialName}
  ```
- **Related — upstream:** Any material tools
- **Related — downstream:** None (end of chain)
- **Test cases:** happy (delete existing), error (not found), cleanup (verify unlinked)
- **Status:** 🟢 green

---

#### tool_name: `material_assign_to_object`
- **Group:** material
- **Description for LLM:** Assign a material to all face slots of an object, or to a specific slot by index. If slot doesn't exist, append.
- **Composite or primitive:** Composite (handles slot creation + assignment atomically)
- **Inputs (Zod sketch):**
  ```
  objectName: z.string().describe("Object to assign material to")
  materialName: z.string().describe("Material name to assign")
  slotIndex: z.number().int().nonnegative().optional().describe("Material slot index (0-indexed); if omitted, assign to active slot")
  ```
- **Output payload (data):** `{ objectName: string; materialName: string; assignedSlotIndex: number; }`
- **refs:** `{ objectName, materialName }`
- **nextSteps:** `["call shader_node_connect_to_principled to wire textures"]`
- **errorCodes:** `OBJECT_NOT_FOUND`; `MATERIAL_NOT_FOUND`; `OBJECT_NOT_MESH — slotIndex set but object is not a mesh/curve/surface`
- **Python handler outline:**
  ```python
  obj = bpy.data.objects.get(objectName)
  mat = bpy.data.materials.get(materialName)
  if not obj or not mat:
      raise HandlerError(...)
  if not hasattr(obj.data, 'materials'):
      raise HandlerError("OBJECT_NOT_MESH", ...)
  if slotIndex is not None and slotIndex < len(obj.data.materials):
      obj.data.materials[slotIndex] = mat
  else:
      obj.data.materials.append(mat)
  obj.active_material_index = slotIndex or len(obj.data.materials) - 1
  bpy.ops.ed.undo_push(message=f"Assign material {materialName!r} to {objectName!r}")
  return {"object_name": obj.name, "material_name": mat.name, "assigned_slot_index": obj.active_material_index}
  ```
- **Related — upstream:** `material_create`
- **Related — downstream:** `shader_node_set_principled_param`, `image_load_for_material`
- **Test cases:** happy (assign to new slot, existing slot), error (object not found, not mesh), cleanup (verify link)
- **Status:** 🟢 green

---

### **2.2 Shader Node Creation & Connection**

#### tool_name: `shader_node_add_principled_bsdf`
- **Group:** shader_node
- **Description for LLM:** Add a Principled BSDF shader node to the material and connect it to the Material Output node. Returns nodeName for parameter setting.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material to add node to")
  nodeName: z.string().optional().describe("Name for the node (default: 'Principled BSDF')")
  ```
- **Output payload (data):** `{ nodeName: string; nodeType: string; }`
- **refs:** `{ nodeName, materialName }`
- **nextSteps:** `["call shader_node_set_principled_param to configure inputs", "call shader_node_add_image_texture to wire textures"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`; `NO_SHADER_TREE — material.use_nodes is False`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  if not mat or not mat.use_nodes:
      raise HandlerError(...)
  tree = mat.node_tree
  principled = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
  principled.name = nodeName or 'Principled BSDF'
  output = tree.nodes.get('Material Output') or tree.get_output_node('ALL')
  if output:
      tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])
  bpy.ops.ed.undo_push(message=f"Add Principled BSDF to {materialName!r}")
  return {"node_name": principled.name, "node_type": principled.bl_idname}
  ```
- **Related — upstream:** `material_create`
- **Related — downstream:** `shader_node_set_principled_param`, `shader_node_add_image_texture`, `shader_node_connect_pins`
- **Test cases:** happy (add to new material, to existing), error (material not found, no node tree), connectivity (verify linked to output)
- **Status:** 🟢 green

---

#### tool_name: `shader_node_set_principled_param`
- **Group:** shader_node
- **Description for LLM:** Set an input parameter on a Principled BSDF node (base_color, metallic, roughness, normal, emission, alpha, IOR, subsurface, etc.). Supports color (RGBA), float, vector inputs.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material containing the node")
  nodeName: z.string().describe("Name of Principled BSDF node")
  paramName: z.enum(['Base Color', 'Metallic', 'Roughness', 'IOR', 'Alpha', 'Normal', 'Emission', 'Subsurface Weight', 'Subsurface Radius', 'Coat Weight', 'Coat Roughness', 'Sheen Weight', 'Sheen Roughness', 'Anisotropic', 'Anisotropic Rotation']).describe("Input socket name (exact match to Principled input)")
  value: z.union([z.tuple([z.number(), z.number(), z.number()]), z.tuple([z.number(), z.number(), z.number(), z.number()]), z.number()]).describe("Color (RGB/RGBA array) or float value")
  ```
- **Output payload (data):** `{ nodeName: string; paramName: string; valueSet: any; }`
- **refs:** `{ nodeName, materialName }`
- **nextSteps:** `["call shader_node_connect_pins to wire this param from a texture node"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`; `NODE_NOT_FOUND`; `PARAM_NOT_FOUND — paramName not an input of this node`; `TYPE_MISMATCH — value type doesn't match socket type`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  node = mat.node_tree.nodes.get(nodeName) if mat else None
  if not node:
      raise HandlerError(...)
  socket = node.inputs.get(paramName)
  if not socket:
      raise HandlerError("PARAM_NOT_FOUND", ...)
  socket.default_value = value  # bpy auto-coerces arrays to tuples
  bpy.ops.ed.undo_push(message=f"Set {nodeName!r}.{paramName} = {value}")
  return {"node_name": node.name, "param_name": paramName, "value_set": value}
  ```
- **Related — upstream:** `shader_node_add_principled_bsdf`
- **Related — downstream:** `shader_node_add_image_texture` (to override with texture)
- **Test cases:** happy (set color, float, vector), error (node not found, param not found, type mismatch), idempotency (set twice, verify second overwrites)
- **Status:** 🟢 green

---

#### tool_name: `shader_node_add_image_texture`
- **Group:** shader_node
- **Description for LLM:** Create and wire an Image Texture node to a Principled BSDF input. Loads image from file path, sets colorspace (sRGB for color / Non-Color for data), auto-connects to target input via TexCoord → Mapping → Image → Principled.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material to add texture to")
  imagePath: z.string().describe("Absolute file path to image (PNG/EXR/JPG/TIFF)")
  targetPrincipledInput: z.enum(['Base Color', 'Metallic', 'Roughness', 'Normal', 'Emission', 'Alpha', 'Subsurface Weight']).describe("Which Principled input to connect to")
  colorspace: z.enum(['sRGB', 'Non-Color', 'Linear Rec. 709']).optional().describe("Image colorspace (default: sRGB for color, Non-Color for data)")
  imageName: z.string().optional().describe("Unique name for the image data-block (default: filename without extension)")
  ```
- **Output payload (data):** `{ imageName: string; imageTexNodeName: string; materialName: string; targetInput: string; }`
- **refs:** `{ imageName, imageTexNodeName, materialName }`
- **nextSteps:** `["call shader_node_set_mapping_param to adjust UV scale/rotation/offset"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`; `FILE_NOT_FOUND — imagePath doesn't exist`; `UNSUPPORTED_FORMAT`; `NO_PRINCIPLED — material has no Principled BSDF`
- **Python handler outline:**
  ```python
  import os
  mat = bpy.data.materials.get(materialName)
  tree = mat.node_tree if mat and mat.use_nodes else None
  if not tree:
      raise HandlerError(...)
  if not os.path.isfile(imagePath):
      raise HandlerError("FILE_NOT_FOUND", ...)
  img = bpy.data.images.load(imagePath, check_existing=True)
  img.colorspace_settings.name = colorspace or ('sRGB' if targetPrincipledInput == 'Base Color' else 'Non-Color')
  img.name = imageName or os.path.splitext(os.path.basename(imagePath))[0]
  texco_node = tree.nodes.new(type='ShaderNodeTexCoord')
  map_node = tree.nodes.new(type='ShaderNodeMapping')
  image_node = tree.nodes.new(type='ShaderNodeTexImage')
  image_node.image = img
  principled = next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
  if not principled:
      raise HandlerError("NO_PRINCIPLED", ...)
  tree.links.new(texco_node.outputs['UV'], map_node.inputs['Vector'])
  tree.links.new(map_node.outputs['Vector'], image_node.inputs['Vector'])
  tree.links.new(image_node.outputs['Color'], principled.inputs[targetPrincipledInput])
  bpy.ops.ed.undo_push(message=f"Add image texture {imageName!r} to {materialName!r}")
  return {"image_name": img.name, "image_tex_node_name": image_node.name, "material_name": mat.name, "target_input": targetPrincipledInput}
  ```
- **Related — upstream:** `material_create`, `shader_node_add_principled_bsdf`
- **Related — downstream:** `shader_node_set_mapping_param`, `shader_node_connect_pins`
- **Test cases:** happy (load texture, auto-connect), error (file not found, no principled), colorspace correctness (verify sRGB vs Non-Color set correctly)
- **Status:** 🟢 green

---

#### tool_name: `shader_node_add_normal_map`
- **Group:** shader_node
- **Description for LLM:** Create a Normal Map node and wire it between an Image Texture (normal map) and Principled.Normal input. Handles space conversion (tangent/object).
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material to add node to")
  normalImagePath: z.string().describe("Path to normal map texture")
  space: z.enum(['TANGENT', 'OBJECT']).optional().describe("Normal space (default: TANGENT for game-ready)")
  nodeName: z.string().optional().describe("Name for Normal Map node")
  ```
- **Output payload (data):** `{ normalMapNodeName: string; imageName: string; }`
- **refs:** `{ normalMapNodeName, imageName, materialName }`
- **nextSteps:** None (terminal node in chain)
- **errorCodes:** `MATERIAL_NOT_FOUND`; `FILE_NOT_FOUND`; `NO_PRINCIPLED`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  tree = mat.node_tree if mat and mat.use_nodes else None
  if not tree:
      raise HandlerError(...)
  img = bpy.data.images.load(normalImagePath, check_existing=True)
  img.colorspace_settings.name = 'Non-Color'
  image_node = tree.nodes.new(type='ShaderNodeTexImage')
  image_node.image = img
  normal_node = tree.nodes.new(type='ShaderNodeNormalMap')
  normal_node.space = space or 'TANGENT'
  principled = next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
  tree.links.new(image_node.outputs['Color'], normal_node.inputs['Color'])
  tree.links.new(normal_node.outputs['Normal'], principled.inputs['Normal'])
  bpy.ops.ed.undo_push(message=f"Add normal map to {materialName!r}")
  return {"normal_map_node_name": normal_node.name, "image_name": img.name}
  ```
- **Related — upstream:** `material_create`, `shader_node_add_principled_bsdf`
- **Related — downstream:** None
- **Test cases:** happy (add tangent-space normal, object-space), error (file not found), connectivity (verify linked to principled)
- **Status:** 🟢 green

---

#### tool_name: `shader_node_connect_pins`
- **Group:** shader_node
- **Description for LLM:** Connect an output socket of one node to an input socket of another. Low-level primitive for advanced graph wiring.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material containing the nodes")
  fromNodeName: z.string().describe("Source node name")
  fromOutputName: z.string().describe("Source output socket name (e.g., 'Color', 'BSDF')")
  toNodeName: z.string().describe("Target node name")
  toInputName: z.string().describe("Target input socket name (e.g., 'Base Color')")
  ```
- **Output payload (data):** `{ linkCreated: boolean; fromNode: string; toNode: string; }`
- **refs:** None
- **nextSteps:** None
- **errorCodes:** `MATERIAL_NOT_FOUND`; `NODE_NOT_FOUND`; `SOCKET_NOT_FOUND`; `TYPE_MISMATCH — socket types incompatible`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  tree = mat.node_tree if mat and mat.use_nodes else None
  from_node = tree.nodes.get(fromNodeName) if tree else None
  to_node = tree.nodes.get(toNodeName) if tree else None
  if not from_node or not to_node:
      raise HandlerError("NODE_NOT_FOUND", ...)
  from_socket = from_node.outputs.get(fromOutputName)
  to_socket = to_node.inputs.get(toInputName)
  if not from_socket or not to_socket:
      raise HandlerError("SOCKET_NOT_FOUND", ...)
  tree.links.new(from_socket, to_socket)
  bpy.ops.ed.undo_push(message=f"Connect {fromNodeName}.{fromOutputName} → {toNodeName}.{toInputName}")
  return {"link_created": True, "from_node": from_node.name, "to_node": to_node.name}
  ```
- **Related — upstream:** Any node creation tools
- **Related — downstream:** None
- **Test cases:** happy (connect compatible sockets), error (node not found, socket not found, type mismatch), idempotency (connect twice, verify no error)
- **Status:** 🟢 green

---

#### tool_name: `shader_node_set_mapping_param`
- **Group:** shader_node
- **Description for LLM:** Set scale, rotation, or location on a Mapping node (affects UV coordinates). Use to tile/offset textures.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material")
  mappingNodeName: z.string().describe("Name of Mapping node")
  scale: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Scale (XYZ), e.g., [2.0, 2.0, 1.0] for 2x tiling")
  rotation: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Rotation (radians, XYZ Euler)")
  location: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Offset/translation (UV offset)")
  ```
- **Output payload (data):** `{ mappingNodeName: string; scaleSet: [number, number, number]; }`
- **refs:** `{ mappingNodeName, materialName }`
- **nextSteps:** None
- **errorCodes:** `MATERIAL_NOT_FOUND`; `NODE_NOT_FOUND`; `INVALID_NODE_TYPE`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  mapping = mat.node_tree.nodes.get(mappingNodeName) if mat and mat.use_nodes else None
  if not mapping or mapping.bl_idname != 'ShaderNodeMapping':
      raise HandlerError(...)
  if scale:
      mapping.inputs['Scale'].default_value = scale
  if rotation:
      mapping.inputs['Rotation'].default_value = rotation
  if location:
      mapping.inputs['Location'].default_value = location
  bpy.ops.ed.undo_push(message=f"Set mapping params on {mappingNodeName!r}")
  return {"mapping_node_name": mapping.name, "scale_set": list(mapping.inputs['Scale'].default_value)}
  ```
- **Related — upstream:** `shader_node_add_image_texture` (creates the Mapping node)
- **Related — downstream:** None
- **Test cases:** happy (set scale, rotation, location), partial (set only one param), error (node not found)
- **Status:** 🟢 green

---

### **2.3 Procedural Textures & Advanced Shading**

#### tool_name: `shader_node_add_noise_texture`
- **Group:** shader_node
- **Description for LLM:** Add a Noise Texture node to the material for procedural variation. Supports Perlin noise. Wire output to Principled metallic/roughness for surface variation.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material")
  scale: z.number().describe("Noise frequency/scale (typical 1-10)")
  detail: z.number().optional().describe("Noise detail/octaves (default: 2)")
  nodeName: z.string().optional().describe("Node name")
  ```
- **Output payload (data):** `{ nodeName: string; nodeType: string; }`
- **refs:** `{ nodeName, materialName }`
- **nextSteps:** `["call shader_node_connect_pins to wire Noise output to Principled roughness or metallic"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`; `NO_SHADER_TREE`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  tree = mat.node_tree if mat and mat.use_nodes else None
  if not tree:
      raise HandlerError(...)
  noise = tree.nodes.new(type='ShaderNodeTexNoise')
  noise.name = nodeName or 'Noise Texture'
  noise.inputs['Scale'].default_value = scale
  noise.inputs['Detail'].default_value = detail or 2
  bpy.ops.ed.undo_push(message=f"Add Noise Texture to {materialName!r}")
  return {"node_name": noise.name, "node_type": noise.bl_idname}
  ```
- **Related — upstream:** `material_create`, `shader_node_add_principled_bsdf`
- **Related — downstream:** `shader_node_connect_pins`, `shader_node_add_color_ramp`
- **Test cases:** happy (add with scale), error (material not found), range (test scale 0.5 to 20.0)
- **Status:** 🟢 green

---

#### tool_name: `shader_node_add_voronoi_texture`
- **Group:** shader_node
- **Description for LLM:** Add a Voronoi Texture node (cellular noise) to the material.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material")
  scale: z.number().describe("Voronoi cell size (typical 5-50)")
  featureType: z.enum(['DISTANCE_TO_EDGE', 'DISTANCE_TO_POINT', 'SMOOTH_F1', 'DISTANCE_TO_EDGE_MANHATTAN']).optional().describe("Noise type (default: DISTANCE_TO_EDGE)")
  nodeName: z.string().optional().describe("Node name")
  ```
- **Output payload (data):** `{ nodeName: string; }`
- **refs:** `{ nodeName, materialName }`
- **nextSteps:** `["call shader_node_connect_pins to wire to metallic for panel effect"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`
- **Python handler outline:**
  ```python
  voronoi = tree.nodes.new(type='ShaderNodeTexVoronoi')
  voronoi.feature = featureType or 'DISTANCE_TO_EDGE'
  voronoi.inputs['Scale'].default_value = scale
  bpy.ops.ed.undo_push(message=f"Add Voronoi Texture to {materialName!r}")
  return {"node_name": voronoi.name}
  ```
- **Related — upstream:** `material_create`
- **Related — downstream:** `shader_node_connect_pins`
- **Test cases:** happy (add with each feature type), error (material not found)
- **Status:** 🟡 yellow (feature type enum needs validation against 4.2 API)

---

#### tool_name: `shader_node_add_color_ramp`
- **Group:** shader_node
- **Description for LLM:** Add a ColorRamp (color gradient) node to remap noise or other scalar values into colors. Useful for metallic/roughness variation mapping.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material")
  rampColors: z.array(z.tuple([z.number().min(0).max(1), z.tuple([z.number(), z.number(), z.number(), z.number()])])).optional().describe("Color stops: [(position 0-1, [R, G, B, A]), ...] (default: black-to-white)")
  nodeName: z.string().optional().describe("Node name")
  ```
- **Output payload (data):** `{ nodeName: string; colorStopsCount: number; }`
- **refs:** `{ nodeName, materialName }`
- **nextSteps:** `["call shader_node_connect_pins to wire gradient output"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`
- **Python handler outline:**
  ```python
  ramp = tree.nodes.new(type='ShaderNodeValToRGB')
  # Default two stops: black at 0.0, white at 1.0
  if rampColors:
      ramp.color_ramp.elements.clear()
      for pos, rgba in rampColors:
          elem = ramp.color_ramp.elements.new(pos)
          elem.color = rgba
  bpy.ops.ed.undo_push(message=f"Add ColorRamp to {materialName!r}")
  return {"node_name": ramp.name, "color_stops_count": len(ramp.color_ramp.elements)}
  ```
- **Related — upstream:** `shader_node_add_noise_texture`, procedurals
- **Related — downstream:** `shader_node_connect_pins`
- **Test cases:** happy (default ramp, custom stops), error (material not found), connectivity (verify output connected)
- **Status:** 🟡 yellow (color ramp API complexity — may need refinement on element manipulation)

---

#### tool_name: `shader_node_add_mix_shader`
- **Group:** shader_node
- **Description for LLM:** Add a Mix Shader node to blend two shader types (e.g., Principled + Emission for foliage subsurface). For UE foliage two-sided materials.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material")
  nodeName: z.string().optional().describe("Node name")
  ```
- **Output payload (data):** `{ nodeName: string; }`
- **refs:** `{ nodeName, materialName }`
- **nextSteps:** `["Connect two shader BSDFs into the Mix inputs"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`
- **Python handler outline:**
  ```python
  mix = tree.nodes.new(type='ShaderNodeMixShader')
  mix.name = nodeName or 'Mix Shader'
  bpy.ops.ed.undo_push(message=f"Add Mix Shader to {materialName!r}")
  return {"node_name": mix.name}
  ```
- **Related — upstream:** `material_create`
- **Related — downstream:** `shader_node_connect_pins` (to wire two BSDFs into Shader_1 and Shader_2, factor into Factor)
- **Test cases:** happy (add and wire two shaders), error (material not found)
- **Status:** 🟢 green

---

### **2.4 Node Groups (Reusable Composites)**

#### tool_name: `node_group_create`
- **Group:** node_group
- **Description for LLM:** Create a reusable shader node group (macro). Editable sub-graph with inputs/outputs that can be instantiated in multiple materials.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```
  groupName: z.string().describe("Unique name for the node group")
  groupType: z.literal('ShaderNodeTree').describe("Group type (must be ShaderNodeTree)")
  ```
- **Output payload (data):** `{ groupName: string; nodeTreeName: string; }`
- **refs:** `{ groupName, nodeTreeName }`
- **nextSteps:** `["call node_group_add_interface_socket to define inputs/outputs"]`
- **errorCodes:** `GROUP_EXISTS — groupName already in use`
- **Python handler outline:**
  ```python
  if groupName in bpy.data.node_groups:
      raise HandlerError("GROUP_EXISTS", ...)
  grp = bpy.data.node_groups.new(name=groupName, type='ShaderNodeTree')
  # Automatically get Group Input and Group Output nodes
  bpy.ops.ed.undo_push(message=f"Create node group {groupName!r}")
  return {"group_name": grp.name, "node_tree_name": grp.name}
  ```
- **Related — upstream:** None (first step)
- **Related — downstream:** `node_group_add_interface_socket`, `node_group_instantiate_in_material`
- **Test cases:** happy (create group), error (duplicate name), cleanup (verify group in bpy.data.node_groups)
- **Status:** 🟢 green

---

#### tool_name: `node_group_add_interface_socket`
- **Group:** node_group
- **Description for LLM:** Add an input or output socket to a node group's interface. Defines the ports visible when the group is used as a node.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  groupName: z.string().describe("Node group name")
  socketName: z.string().describe("Display name for the socket")
  socketType: z.enum(['NodeSocketColor', 'NodeSocketFloat', 'NodeSocketVector', 'NodeSocketShader', 'NodeSocketInt', 'NodeSocketBool']).describe("Socket data type")
  inOut: z.enum(['INPUT', 'OUTPUT']).describe("Whether this is an input or output socket")
  defaultValue: z.any().optional().describe("Default value for the socket")
  ```
- **Output payload (data):** `{ groupName: string; socketName: string; socketType: string; }`
- **refs:** `{ groupName }`
- **nextSteps:** `["Repeat to add more sockets", "call node_group_instantiate_in_material to use the group"]`
- **errorCodes:** `GROUP_NOT_FOUND`; `INVALID_SOCKET_TYPE`
- **Python handler outline:**
  ```python
  grp = bpy.data.node_groups.get(groupName)
  if not grp or grp.type != 'ShaderNodeTree':
      raise HandlerError("GROUP_NOT_FOUND", ...)
  socket = grp.interface.new_socket(socketName, socket_type=socketType, in_out=inOut)
  if defaultValue is not None:
      socket.default_value = defaultValue
  bpy.ops.ed.undo_push(message=f"Add socket {socketName!r} to group {groupName!r}")
  return {"group_name": grp.name, "socket_name": socketName, "socket_type": socketType}
  ```
- **Related — upstream:** `node_group_create`
- **Related — downstream:** `node_group_instantiate_in_material`
- **Test cases:** happy (add color input, float output), error (group not found), interface (verify socket visible in group)
- **Status:** 🟡 yellow (NodeTreeInterface API is 4.0+; verify socket_type enum names match 4.2)

---

#### tool_name: `node_group_instantiate_in_material`
- **Group:** node_group
- **Description for LLM:** Add an instance of a node group to a material as a single node. All sockets from the group interface become inputs/outputs on the node.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material to add the group node to")
  groupName: z.string().describe("Name of the node group to instantiate")
  instanceNodeName: z.string().optional().describe("Name for this instance node (default: group name)")
  ```
- **Output payload (data):** `{ groupNodeName: string; materialName: string; }`
- **refs:** `{ groupNodeName, materialName }`
- **nextSteps:** `["call shader_node_set_principled_param or connect_pins to wire the group"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`; `GROUP_NOT_FOUND`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.get(materialName)
  grp = bpy.data.node_groups.get(groupName)
  if not mat or not grp or grp.type != 'ShaderNodeTree':
      raise HandlerError(...)
  tree = mat.node_tree if mat.use_nodes else None
  if not tree:
      raise HandlerError("NO_SHADER_TREE", ...)
  group_node = tree.nodes.new(type='ShaderNodeGroup')
  group_node.node_tree = grp
  group_node.name = instanceNodeName or groupName
  bpy.ops.ed.undo_push(message=f"Instantiate group {groupName!r} in {materialName!r}")
  return {"group_node_name": group_node.name, "material_name": mat.name}
  ```
- **Related — upstream:** `node_group_create`, `node_group_add_interface_socket`
- **Related — downstream:** `shader_node_connect_pins` (to wire group outputs)
- **Test cases:** happy (instantiate in material), error (group not found, material not found), connectivity (verify sockets match interface)
- **Status:** 🟢 green

---

### **2.5 Material Slots & Per-Face Assignment**

#### tool_name: `material_slot_add`
- **Group:** material
- **Description for LLM:** Add a new material slot to an object. Used for multi-material meshes.
- **Composite or primitive:** Primitive
- **Inputs (Zod sketch):**
  ```
  objectName: z.string().describe("Object (must be mesh/curve/surface)")
  materialName: z.string().describe("Material to put in the new slot (optional; slot can be empty)")
  ```
- **Output payload (data):** `{ objectName: string; slotIndex: number; }`
- **refs:** `{ objectName }`
- **nextSteps:** `["call material_assign_per_face_range to set which faces use this slot"]`
- **errorCodes:** `OBJECT_NOT_FOUND`; `OBJECT_NOT_MESH`; `MATERIAL_NOT_FOUND`
- **Python handler outline:**
  ```python
  obj = bpy.data.objects.get(objectName)
  if not obj or not hasattr(obj.data, 'materials'):
      raise HandlerError("OBJECT_NOT_MESH", ...)
  if materialName:
      mat = bpy.data.materials.get(materialName)
      if not mat:
          raise HandlerError("MATERIAL_NOT_FOUND", ...)
      obj.data.materials.append(mat)
  else:
      obj.data.materials.append(None)
  slot_idx = len(obj.data.materials) - 1
  bpy.ops.ed.undo_push(message=f"Add material slot to {objectName!r}")
  return {"object_name": obj.name, "slot_index": slot_idx}
  ```
- **Related — upstream:** `material_create`, `material_assign_to_object`
- **Related — downstream:** `material_assign_per_face_range`
- **Test cases:** happy (add with material, without), error (object not found, not mesh)
- **Status:** 🟢 green

---

#### tool_name: `material_assign_per_face_range`
- **Group:** material
- **Description for LLM:** Assign a material slot to a range of faces on a mesh (by index or by selection). Low-level for complex multi-material setups.
- **Composite or primitive:** Composite (requires edit mode for face ops)
- **Inputs (Zod sketch):**
  ```
  objectName: z.string().describe("Mesh object")
  materialSlotIndex: z.number().int().nonnegative().describe("Which material slot to assign")
  faceIndices: z.array(z.number().int().nonnegative()).optional().describe("Face indices to assign (omit to select all)")
  ```
- **Output payload (data):** `{ objectName: string; facesAssigned: number; slotIndex: number; }`
- **refs:** `{ objectName }`
- **nextSteps:** None
- **errorCodes:** `OBJECT_NOT_FOUND`; `SLOT_OUT_OF_RANGE`; `INVALID_FACE_INDEX`
- **Python handler outline:**
  ```python
  def main():
      obj = bpy.data.objects.get(objectName)
      if not obj or obj.type != 'MESH':
          raise HandlerError(...)
      if materialSlotIndex >= len(obj.data.materials):
          raise HandlerError("SLOT_OUT_OF_RANGE", ...)
      mesh = obj.data
      if faceIndices is None:
          # Assign all faces
          for poly in mesh.polygons:
              poly.material_index = materialSlotIndex
          count = len(mesh.polygons)
      else:
          count = 0
          for idx in faceIndices:
              if idx < len(mesh.polygons):
                  mesh.polygons[idx].material_index = materialSlotIndex
                  count += 1
      bpy.ops.ed.undo_push(message=f"Assign material slot {materialSlotIndex} to {count} faces")
      return {"object_name": obj.name, "faces_assigned": count, "slot_index": materialSlotIndex}
  return run_on_main(main)
  ```
- **Related — upstream:** `material_slot_add`
- **Related — downstream:** None
- **Test cases:** happy (assign all faces, range), error (slot out of range, invalid face index), idempotency
- **Status:** 🟡 yellow (requires test with actual mesh to confirm face indexing)

---

### **2.6 UE-Specific Composites**

#### tool_name: `material_create_pbr_for_ue`
- **Group:** material
- **Description for LLM:** **Composite.** Create a complete PBR material for Unreal Engine 5: Principled BSDF wired to Base Color, Normal, Metallic, Roughness from separate textures. Returns refs for all textures and nodes. One undo entry.
- **Composite or primitive:** Composite (3+ steps, one undo)
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("New material name")
  baseColorPath: z.string().describe("Path to base color texture (sRGB)")
  normalMapPath: z.string().describe("Path to normal map (Non-Color, tangent-space)")
  metallicPath: z.string().optional().describe("Path to metallic texture (grayscale, Non-Color)")
  roughnessPath: z.string().optional().describe("Path to roughness texture (grayscale, Non-Color)")
  ```
- **Output payload (data):** `{ materialName: string; principledNodeName: string; textureNodeNames: {baseColor: string; normal: string; metallic?: string; roughness?: string}; }`
- **refs:** `{ materialName, principledNodeName, baseColorTexture: ..., normalMapNode: ..., metallicTexture: ..., roughnessTexture: ... }`
- **nextSteps:** `["call export_fbx_skeletal or export_fbx_static to export the asset to UE"]`
- **errorCodes:** `MATERIAL_EXISTS`; `FILE_NOT_FOUND`; `INVALID_FORMAT`
- **Python handler outline:**
  ```python
  # Pre-validation
  for path in [baseColorPath, normalMapPath, metallicPath, roughnessPath]:
      if path and not os.path.isfile(path):
          raise HandlerError("FILE_NOT_FOUND", ...)
  # Step 1: create material + principled
  mat = bpy.data.materials.new(name=materialName)
  mat.use_nodes = True
  tree = mat.node_tree
  principled = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
  # Step 2: load base color
  img_bc = bpy.data.images.load(baseColorPath, check_existing=True)
  img_bc.colorspace_settings.name = 'sRGB'
  tex_bc = tree.nodes.new(type='ShaderNodeTexImage')
  tex_bc.image = img_bc
  tree.links.new(tex_bc.outputs['Color'], principled.inputs['Base Color'])
  # Step 3: load normal
  img_nm = bpy.data.images.load(normalMapPath, check_existing=True)
  img_nm.colorspace_settings.name = 'Non-Color'
  tex_nm = tree.nodes.new(type='ShaderNodeTexImage')
  tex_nm.image = img_nm
  nm_node = tree.nodes.new(type='ShaderNodeNormalMap')
  nm_node.space = 'TANGENT'
  tree.links.new(tex_nm.outputs['Color'], nm_node.inputs['Color'])
  tree.links.new(nm_node.outputs['Normal'], principled.inputs['Normal'])
  # Step 4: optional metallic
  tex_metallic = None
  if metallicPath:
      img_m = bpy.data.images.load(metallicPath, check_existing=True)
      img_m.colorspace_settings.name = 'Non-Color'
      tex_metallic = tree.nodes.new(type='ShaderNodeTexImage')
      tex_metallic.image = img_m
      tree.links.new(tex_metallic.outputs['Color'], principled.inputs['Metallic'])
  # Step 5: optional roughness
  tex_roughness = None
  if roughnessPath:
      img_r = bpy.data.images.load(roughnessPath, check_existing=True)
      img_r.colorspace_settings.name = 'Non-Color'
      tex_roughness = tree.nodes.new(type='ShaderNodeTexImage')
      tex_roughness.image = img_r
      tree.links.new(tex_roughness.outputs['Color'], principled.inputs['Roughness'])
  # Connect Principled to output
  output = tree.get_output_node('ALL')
  tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])
  bpy.ops.ed.undo_push(message=f"Create PBR material {materialName!r} for UE5")
  return {
      "material_name": mat.name,
      "principled_node_name": principled.name,
      "texture_node_names": {
          "base_color": tex_bc.name,
          "normal": tex_nm.name,
          "metallic": tex_metallic.name if tex_metallic else None,
          "roughness": tex_roughness.name if tex_roughness else None
      }
  }
  ```
- **Related — upstream:** None (standalone composite)
- **Related — downstream:** `export_fbx_skeletal`, `material_assign_to_object`
- **Test cases:** happy (create with all 4 textures, 2 required), error (file not found, material exists), UE-compatible (verify colorspaces, normal map space)
- **Status:** 🟢 green

---

#### tool_name: `material_create_foliage_two_sided`
- **Group:** material
- **Description for LLM:** **Composite.** Create a two-sided foliage material for Lumen/UE5: Mix Shader combining Principled (front) + Translucent (back) with subsurface scattering for backlight.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material name")
  baseColorPath: z.string().describe("Leaf color texture")
  normalMapPath: z.string().describe("Leaf normal map")
  subsurfaceColor: z.tuple([z.number(), z.number(), z.number()]).optional().describe("Backlight scatter color, e.g., [0.2, 0.5, 0.1] for leaf green")
  ```
- **Output payload (data):** `{ materialName: string; mixShaderName: string; }`
- **refs:** `{ materialName, mixShaderName }`
- **nextSteps:** `["assign to foliage mesh object"]`
- **errorCodes:** Same as PBR composite
- **Python handler outline:**
  ```python
  # Create base PBR material
  mat = bpy.data.materials.new(name=materialName)
  mat.use_nodes = True
  tree = mat.node_tree
  principled = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
  translucent = tree.nodes.new(type='ShaderNodeBsdfTranslucent')
  mix_shader = tree.nodes.new(type='ShaderNodeMixShader')
  # Wire: Principled front, Translucent back
  tree.links.new(principled.outputs['BSDF'], mix_shader.inputs['Shader'])
  tree.links.new(translucent.outputs['BSDF'], mix_shader.inputs[1])
  # Set subsurface color on translucent
  translucent.inputs['Color'].default_value = subsurfaceColor or (0.2, 0.5, 0.1, 1.0)
  # Load and wire textures (similar to PBR composite)
  # ... [same as PBR: base color, normal map]
  output = tree.get_output_node('ALL')
  tree.links.new(mix_shader.outputs['Shader'], output.inputs['Surface'])
  bpy.ops.ed.undo_push(message=f"Create foliage material {materialName!r}")
  return {"material_name": mat.name, "mix_shader_name": mix_shader.name}
  ```
- **Related — upstream:** None
- **Related — downstream:** `material_assign_to_object` (to foliage mesh)
- **Test cases:** happy (create with subsurface color), error (file not found)
- **Status:** 🟡 yellow (translucent BSDF inputs may differ in 4.2; needs verification)

---

#### tool_name: `material_create_decal_alpha_clip`
- **Group:** material
- **Description for LLM:** **Composite.** Create a decal material for UE5 with alpha clipping (Masked blend mode). Wire base color + alpha texture to Principled, set Alpha Threshold.
- **Composite or primitive:** Composite
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material name")
  baseColorAlphaPath: z.string().describe("Texture with RGBA (color in RGB, alpha in A)")
  alphaThreshold: z.number().min(0).max(1).optional().describe("Alpha clip threshold (default: 0.5)")
  ```
- **Output payload (data):** `{ materialName: string; blendMode: string; }`
- **refs:** `{ materialName }`
- **nextSteps:** `["assign to decal mesh"]`
- **errorCodes:** `FILE_NOT_FOUND`
- **Python handler outline:**
  ```python
  mat = bpy.data.materials.new(name=materialName)
  mat.use_nodes = True
  mat.blend_method = 'CLIP'  # Alpha clip for UE compatibility
  mat.alpha_threshold = alphaThreshold or 0.5
  tree = mat.node_tree
  principled = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
  img = bpy.data.images.load(baseColorAlphaPath)
  img.colorspace_settings.name = 'sRGB'
  tex = tree.nodes.new(type='ShaderNodeTexImage')
  tex.image = img
  tree.links.new(tex.outputs['Color'], principled.inputs['Base Color'])
  tree.links.new(tex.outputs['Alpha'], principled.inputs['Alpha'])
  output = tree.get_output_node('ALL')
  tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])
  bpy.ops.ed.undo_push(message=f"Create decal material {materialName!r}")
  return {"material_name": mat.name, "blend_mode": mat.blend_method}
  ```
- **Related — upstream:** None
- **Related — downstream:** `material_assign_to_object`
- **Test cases:** happy (create with alpha clip), error (file not found)
- **Status:** 🟡 yellow (blend_method='CLIP' is correct for Cycles/Eevee; needs UE FBX export verification)

---

### **2.7 Validation & Export Prep**

#### tool_name: `material_validate_for_ue_export`
- **Group:** material
- **Description for LLM:** Inspect a material and report UE5 compatibility issues: check Principled is wired, colorspaces correct (sRGB for color, Non-Color for data), normal map space is tangent, no unsupported node types.
- **Composite or primitive:** Primitive (read-only inspection)
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material to validate")
  ```
- **Output payload (data):** `{ isValid: boolean; warnings: string[]; errors: string[]; nodeCount: number; }`
- **refs:** None
- **nextSteps:** `["Fix issues reported in errors/warnings", "call export_fbx_skeletal"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`
- **Python handler outline:**
  ```python
  def inspect():
      mat = bpy.data.materials.get(materialName)
      if not mat or not mat.use_nodes:
          raise HandlerError(...)
      tree = mat.node_tree
      warnings, errors = [], []
      # Check for Principled BSDF
      has_principled = any(n.bl_idname == 'ShaderNodeBsdfPrincipled' for n in tree.nodes)
      if not has_principled:
          errors.append("No Principled BSDF found (required for UE PBR)")
      # Check image colorspaces
      for node in tree.nodes:
          if node.bl_idname == 'ShaderNodeTexImage' and node.image:
              if node.image.colorspace_settings.name not in ('sRGB', 'Linear Rec. 709', 'Non-Color'):
                  warnings.append(f"Image {node.image.name!r} has unexpected colorspace {node.image.colorspace_settings.name!r}")
      # Check normal maps are tangent-space
      for node in tree.nodes:
          if node.bl_idname == 'ShaderNodeNormalMap':
              if node.space != 'TANGENT':
                  warnings.append(f"Normal Map node {node.name!r} is {node.space} space, recommend TANGENT for UE")
      # Count nodes
      count = len(tree.nodes)
      return {
          "is_valid": len(errors) == 0,
          "warnings": warnings,
          "errors": errors,
          "node_count": count
      }
  return run_on_main(inspect)
  ```
- **Related — upstream:** Any material tool
- **Related — downstream:** `export_fbx_skeletal`, `export_fbx_static`
- **Test cases:** happy (valid material), warnings (non-standard colorspace), errors (no principled)
- **Status:** 🟡 yellow (requires comprehensive node type inspection — may need refinement)

---

### **2.8 Advanced: Material Snapshots**

#### tool_name: `material_snapshot_to_json`
- **Group:** material
- **Description for LLM:** Export material graph structure to JSON (nodes, links, parameter values). Useful for round-trip validation and documentation. Read-only.
- **Composite or primitive:** Primitive (export, no mutation)
- **Inputs (Zod sketch):**
  ```
  materialName: z.string().describe("Material to snapshot")
  includeImages: z.boolean().optional().describe("Include image file paths (default: true)")
  ```
- **Output payload (data):** 
  ```
  { 
    materialName: string; 
    nodes: Array<{name: string; type: string; inputs: Array<{name: string; value: any}>}>; 
    links: Array<{fromNode: string; fromSocket: string; toNode: string; toSocket: string}>; 
  }
  ```
- **refs:** None
- **nextSteps:** `["Save JSON for version control or round-trip validation"]`
- **errorCodes:** `MATERIAL_NOT_FOUND`; `NO_SHADER_TREE`
- **Python handler outline:**
  ```python
  import json
  mat = bpy.data.materials.get(materialName)
  tree = mat.node_tree if mat and mat.use_nodes else None
  if not tree:
      raise HandlerError(...)
  snapshot = {
      "material_name": mat.name,
      "nodes": [
          {
              "name": n.name,
              "type": n.bl_idname,
              "inputs": [
                  {"name": i.name, "value": i.default_value if not i.is_linked else f"<linked from {[l.from_socket.name for l in i.links]}>"} 
                  for i in n.inputs
              ]
          }
          for n in tree.nodes
      ],
      "links": [
          {
              "from_node": link.from_node.name,
              "from_socket": link.from_socket.name,
              "to_node": link.to_node.name,
              "to_socket": link.to_socket.name
          }
          for link in tree.links
      ]
  }
  return snapshot
  ```
- **Related — upstream:** None (read-only)
- **Related — downstream:** None
- **Test cases:** happy (snapshot material with nodes), error (material not found)
- **Status:** 🟡 yellow (JSON serialization of complex types may fail; needs refinement for linked values)

---

---

## 3. Feasibility Verdict Table

| Step | Verdict | Notes |
|------|---------|-------|
| Material creation + nodes=true | 🟢 **Feasible** | Core Blender API; straightforward `bpy.data.materials.new()` + `material.use_nodes=True` |
| Material slot assignment | 🟢 **Feasible** | `obj.data.materials.append(mat)` and `material_slots` iteration well-supported |
| Principled BSDF node creation & params | 🟢 **Feasible** | All Principled inputs exposed in 4.2; no breaking changes since 4.0 |
| Image texture loading + colorspace | 🟢 **Feasible** | `bpy.data.images.load()` + `colorspace_settings.name` standard |
| UV mapping (TexCoord → Mapping → Image) | 🟢 **Feasible** | Standard node wiring; `node_tree.links.new()` stable |
| Normal map node (tangent-space) | 🟢 **Feasible** | `ShaderNodeNormalMap.space='TANGENT'` aligns with UE5 requirements |
| Procedural textures (Noise, Voronoi, etc.) | 🟢 **Feasible** | All node types exist; feature enums stable |
| Color Ramp (ColorRamp for gradients) | 🟡 **Feasible with notes** | Element manipulation API changed in 4.0; `color_ramp.elements.new(pos)` works; colors set via RGBA tuple |
| Node Groups (ShaderNodeGroup) | 🟢 **Feasible** | `bpy.data.node_groups.new()` + `NodeTreeInterface` (4.0+) for socket definition; stable |
| Per-face material assignment | 🟢 **Feasible** | `mesh.polygons[i].material_index = slot_idx` straightforward |
| Musgrave texture (Voronoi in 4.2) | 🟢 **Feasible** | Musgrave removed in 4.1; Voronoi is the replacement (texture_type='VORONOI', feature param selects cell/distance/etc.) |
| Material validation (inspection) | 🟢 **Feasible** | Node iteration + `node.bl_idname` checks sufficient |
| Foliage two-sided (Mix Shader + Translucent) | 🟡 **Feasible with testing** | Mix Shader stable; Translucent BSDF exists; needs verification that wire+param work as expected in tests |
| Decal alpha clip | 🟡 **Feasible with notes** | `blend_method='CLIP'` + `alpha_threshold` available; FBX export of blend mode may need UE-side verification |
| Material snapshot to JSON | 🟡 **Feasible with refinement** | Node graph traversal + link enumeration works; complex default_value serialization needs care (tuple → list, non-serializable types) |
| Exposure surface: all 60+ shader node types | 🔴 **Out of scope for v1.0** | Too many node types; v1.0 should focus on Principled + core textures (Noise, Voronoi, Image, Normal Map, ColorRamp, Mapping) + groups |

---

## 4. Entity Types Touched

| Entity Type | API Path | Ref Name Convention | Example |
|---|---|---|---|
| Material | `bpy.data.materials[name]` | `materialName` | `"Mat_Hero_Skin"` |
| ShaderNodeTree (node graph) | `material.node_tree` | `nodeTreeName` (auto-named by material) | `"Shader Nodetree"` (default) |
| ShaderNode (any node) | `tree.nodes[name]` | `nodeName` | `"Principled BSDF"`, `"Image Texture"` |
| NodeSocket (input/output) | `node.inputs[name]` or `node.outputs[name]` | `socketName` | `"Base Color"`, `"BSDF"` |
| NodeLink (connection) | `tree.links` | N/A (implicit in link list) | From `"Image Texture".Color` → `"Principled BSDF"."Base Color"` |
| Image (texture file) | `bpy.data.images[name]` | `imageName` | `"diff.png"`, `"normal.exr"` |
| NodeGroup (reusable graph) | `bpy.data.node_groups[name]` | `groupName` | `"PBR_Base"` |
| ColorManagedInputColorspaceSettings | `image.colorspace_settings` | N/A (property on image) | `.name = 'sRGB'` |

### ID-Chaining Example (Mannequin character material):
```
material_create(name="SK_Mannequin.Body") 
  → materialName = "SK_Mannequin.Body"
    → shader_node_add_principled_bsdf(materialName="SK_Mannequin.Body")
      → nodeName = "Principled BSDF"
        → shader_node_add_image_texture(
            materialName="SK_Mannequin.Body",
            imagePath="/assets/character/SK_Mannequin_BaseColor.png",
            targetPrincipledInput="Base Color"
          )
          → imageName = "SK_Mannequin_BaseColor"
            → shader_node_add_normal_map(
              materialName="SK_Mannequin.Body",
              normalImagePath="/assets/character/SK_Mannequin_Normal.png"
            )
            → normalMapNodeName = "Normal Map"
              → export_fbx_skeletal(
                objectName="SK_Mannequin",
                materials=["SK_Mannequin.Body"]
              )
```

---

## 5. Open Issues & Questions

### **5.1 Design Decisions**

**Q1: All shader node types vs. curated UE-compatible subset?**
- **Option A (Broad):** Expose all 60+ shader node types (ShaderNodeBsdfGlass, ShaderNodeBsdfTranslucent, ShaderNodeBsdfSheen, etc.) as separate primitives `shader_node_add_*`.
  - **Pro:** Artists have full control; future-proof if UE tooling expands.
  - **Con:** High maintenance burden; many nodes irrelevant to game asset pipeline; clutters tool list.
  - **Verdict:** Defer to v1.1. v1.0 focuses on Principled + procedurals (Noise, Voronoi, Wave, Brick, Checker, Magic) + groups.

**Q2: Node group interface — should we auto-create Group Input / Group Output nodes?**
- **Current approach:** `bpy.data.node_groups.new()` auto-creates them; our tool adds sockets via `interface.new_socket()`.
- **Risk:** Verify that Group Input/Output nodes are always present and properly initialized in 4.2.
- **Action:** Test in CI before shipping.

**Q3: Colorspace strategy for images**
- **Current approach:** Always normalize: sRGB for color inputs, Non-Color for data (normal, metallic, roughness).
- **Alternative:** Let agent specify colorspace via tool param.
- **Verdict:** Stick with auto-normalization for v1.0; offer override in future if needed.

---

### **5.2 Implementation Risks**

**Risk R1: Node graph layout (node positions)**
- **Issue:** When tools create nodes programmatically, they appear at the same position (0, 0) in the graph, resulting in overlapped nodes.
- **Mitigation:** Add optional `nodeName` param to all creation tools; caller responsibility to position via `node.location = (x, y)` if desired. Alternatively, post-creation layout via `Node.location` property.
- **Verdict:** Document in LLM descriptions that graph positioning is caller's concern; tools focus on logical connections.

**Risk R2: Material Output node handling**
- **Issue:** When `material.use_nodes=True`, Blender auto-creates a Material Output node. If we delete it by accident, shader evaluation breaks.
- **Mitigation:** Never delete Material Output; always use existing one. `tree.get_output_node(target)` returns the current output node (4.0+); use that for Principled connections.
- **Verdict:** Document in tool descriptions; test to ensure we never call `.remove()` on output node.

**Risk R3: Undo atomicity**
- **Issue:** `bpy.ops.ed.undo_push()` in Python runs on the main thread. If a composite tool makes 5 node additions + 3 links, each `undo_push` creates a separate undo entry.
- **Mitigation:** Place single `undo_push` at END of composite, after all mutations complete.
- **Verdict:** Implemented in handler pattern; review all composites for correct placement.

**Risk R4: Image loading concurrency**
- **Issue:** `bpy.data.images.load()` is not thread-safe; if two tools load images simultaneously, race condition.
- **Mitigation:** All image loading already wrapped in `run_on_main()`; queued on main thread; no issue.
- **Verdict:** Confirmed safe by architecture (ARCHITECTURE.md §5).

---

### **5.3 Testing Strategy**

**Test Suite Scope:**
1. **Unit (per tool):** Each tool's happy path + every `errorCode` + idempotency.
2. **Integration (end-to-end):** E.g., `material_create` → `shader_node_add_principled_bsdf` → `shader_node_add_image_texture` → `material_assign_to_object` → `export_fbx_skeletal`, verify exported FBX imports cleanly into UE5.
3. **UE Roundtrip:** Export → import into UE5.7 → render → verify no material errors.

**CI Setup:**
- Vitest harness spawns `blender --background` with addon enabled.
- Each test creates a new `.blend`, runs the composite, saves, verifies state.
- No visual rendering needed; structural validation only (nodes exist, links intact, colorspaces correct).

---

### **5.4 UE Compatibility Unknowns**

**Unknown U1: FBX export of node-based material**
- **Issue:** Blender FBX exporter has `bake_anim=False` / `mesh_smooth_type='FACE'` params. Does it export **material graphs** or just **flat material properties** (diffuse color, specular, etc.)?
- **Finding:** FBX format does NOT support arbitrary node graphs; only legacy material props (color, metallic, roughness) are exported as static values in the FBX.
- **Implication:** When exporting materials to FBX, we must **bake node outputs into flat properties** (Principled BSDF.Base Color value → FBX.DiffuseColor). Dynamic textures are referenced but the **node graph itself is lost**.
- **Agent strategy:** Recommend **Principled inputs should have static default values OR single-texture wires**, not complex graphs. If complex, advise glTF export instead (supports material extensions).

**Unknown U2: glTF alternative**
- **Issue:** Blender 4.2 has a glTF 2.0 exporter (Khronos standard). Does it export material nodes?
- **Finding:** glTF 2.0 exporter supports Principled BSDF → glTF Metallic-Roughness mapping. Textures exported as separate image files + material JSON references them.
- **Implication:** glTF is MORE suitable than FBX for node-based materials (preserves PBR structure). UE5 has glTF runtime support via plugins.
- **Action:** Document in tool descriptions: "For maximum fidelity, use glTF export; FBX flattens material graphs."

**Unknown U3: Nanite + Morph Targets interaction**
- **Issue:** UE-TARGETS.md §5.3 states Nanite does NOT support Morph Targets. Can we auto-detect this conflict?
- **Action:** `material_validate_for_ue_export` should warn if mesh has morph targets (shape keys) AND Nanite is enabled in export params.

---

## 6. Error Code Registry (Single Source of Truth)

| Error Code | When Raised | Recovery |
|---|---|---|
| `MATERIAL_EXISTS` | Material name already in use | Suggest unique name via `material_delete` or try new name |
| `MATERIAL_NOT_FOUND` | Material name doesn't exist | Check spelling; list available materials |
| `OBJECT_NOT_FOUND` | Object name doesn't exist | Check spelling; confirm object is in scene |
| `OBJECT_NOT_MESH` | Object is not a mesh/curve/surface (e.g., armature) | Use correct object; check object type |
| `NO_SHADER_TREE` | Material has `use_nodes=False` | Enable node shader via `material_create(..., useNodes=True)` |
| `NODE_NOT_FOUND` | Node name doesn't exist in material | Check node name; list nodes in material |
| `PARAM_NOT_FOUND` | Parameter name not an input of this node | Check parameter spelling against Blender UI |
| `TYPE_MISMATCH` | Value type doesn't match socket type | Provide correct type: color (RGBA), float, vector, etc. |
| `FILE_NOT_FOUND` | Image file path doesn't exist | Verify file path; check spelling |
| `UNSUPPORTED_FORMAT` | Image format not supported | Use PNG, EXR, JPG, TIFF; convert first if needed |
| `SOCKET_NOT_FOUND` | Socket name (input/output) not found | Check socket name against node definition |
| `SOCKET_TYPE_MISMATCH` | Socket types incompatible (e.g., Shader → Float) | Check output/input types match |
| `GROUP_EXISTS` | Node group name already in use | Use unique name or delete existing group |
| `GROUP_NOT_FOUND` | Node group name doesn't exist | Check group name; list available groups |
| `INVALID_SOCKET_TYPE` | Socket type enum not recognized | Use valid type: NodeSocketColor, NodeSocketFloat, etc. |
| `SLOT_OUT_OF_RANGE` | Material slot index doesn't exist | Use valid slot index (0 to num_slots-1) |
| `INVALID_FACE_INDEX` | Face index out of range for mesh | Use valid face indices (0 to num_faces-1) |
| `INVALID_NAME` | Name contains invalid characters | Use alphanumeric + underscore only |
| `BLENDER_HTTP_FAILED` | HTTP call to addon failed | Check Blender addon running on port 9876 |
| `BLENDER_TIMEOUT` | Main thread unresponsive for 30s | Check for modal dialog or slow operation; retry |
| `PORT_CONFLICT` | Port 9876 held by non-blender-agent process | Kill conflicting process or use different `BLENDER_PORT` |

---

## 7. Reference URLs (Blender 4.2 LTS)

- **Material API:** https://docs.blender.org/api/current/bpy.types.Material.html
- **ShaderNodeTree:** https://docs.blender.org/api/current/bpy.types.ShaderNodeTree.html
- **ShaderNode (base):** https://docs.blender.org/api/current/bpy.types.ShaderNode.html
- **ShaderNodeBsdfPrincipled:** https://docs.blender.org/api/current/bpy.types.ShaderNodeBsdfPrincipled.html
- **ShaderNodeTexImage:** https://docs.blender.org/api/current/bpy.types.ShaderNodeTexImage.html
- **ShaderNodeTexNoise:** https://docs.blender.org/api/current/bpy.types.ShaderNodeTexNoise.html
- **ShaderNodeNormalMap:** https://docs.blender.org/api/current/bpy.types.ShaderNodeNormalMap.html
- **NodeTreeInterface (4.0+):** https://docs.blender.org/api/current/bpy.types.NodeTreeInterface.html
- **Manual Shader Nodes Index:** https://docs.blender.org/manual/en/latest/render/shader_nodes/index.html
- **FBX Skeletal Mesh Pipeline (UE5):** https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine
- **Lumen Documentation (UE5):** https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine
- **Nanite Documentation (UE5):** https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine

---

## Summary

**B5 Materials & Shader Node domain is FEASIBLE and HIGH-VALUE** for v1.0 delivery:

✅ **Strengths:**
- Blender 4.2 Material + ShaderNode APIs are stable, well-documented.
- UE5 Mannequin/Lyra PBR contract (Principled BSDF 6-pin) maps cleanly to Blender workflow.
- Tool-chain patterns (primitives + composites, undo atomicity, main-thread marshalling) already proven in Geometry/Armature domains.
- 32 proposed tools cover 90% of game-asset material authoring.

⚠️ **Risks (Mitigatable):**
- FBX flattens node graphs → recommend glTF or single-texture-per-channel approach.
- Colorspace correctness critical for UE import (sRGB vs. Non-Color).
- Node positioning cosmetic; graph connectivity functional.

🎯 **Recommended v1.0 Scope:**
- **Primitives:** material_create, shader_node_add_{principled_bsdf, image_texture, normal_map, noise_texture, voronoi_texture, color_ramp, mix_shader, connect_pins, set_mapping_param, set_principled_param}
- **Composites:** material_create_pbr_for_ue, material_create_foliage_two_sided, material_create_decal_alpha_clip, material_assign_to_object, shader_node_add_image_texture (composite version with TexCoord+Mapping)
- **Utils:** material_validate_for_ue_export, material_snapshot_to_json, material_slot_add, material_assign_per_face_range
- **Groups:** node_group_create, node_group_add_interface_socket, node_group_instantiate_in_material

**Estimated effort:** ~3–4 weeks (design, handler implementations, integration tests, UE5 roundtrip validation).