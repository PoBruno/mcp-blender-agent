/**
 * Material / shader / node-group tools (B5).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerMaterialTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "material_create",
      description: "Create a Material (use_nodes=true by default). Idempotent on name.",
      inputSchema: {
        name: z.string().describe("Material name."),
        useNodes: z.boolean().optional().describe("Initialize node tree (default true)."),
      },
      handler: passthroughPost("/material/create"),
    },
    {
      name: "material_delete",
      description: "Delete a material datablock.",
      inputSchema: { materialName: z.string().describe("Material to delete.") },
      handler: passthroughPost("/material/delete"),
    },
    {
      name: "material_assign_slot",
      description: "Assign a material to an object's slot (creates the slot if missing).",
      inputSchema: {
        objectName: z.string().describe("Target object."),
        materialName: z.string().describe("Material to assign."),
        slotIndex: z.number().int().nonnegative().optional().describe("Slot index (default 0)."),
      },
      handler: passthroughPost("/material/assign_slot"),
    },
    {
      name: "material_slot_add",
      description: "Append an empty material slot on a mesh object.",
      inputSchema: { objectName: z.string().describe("Mesh object.") },
      handler: passthroughPost("/material/slot_add"),
    },
    {
      name: "material_create_procedural_grid",
      description:
        "Create a checker/grid procedural material (good for blockout visualization).",
      inputSchema: {
        name: z.string().optional().describe("Material name (default 'Grid_BlockOut')."),
        squareSize: z.number().positive().optional().describe("Square size (default 0.5)."),
      },
      handler: passthroughPost("/material/create_procedural_grid"),
    },
  ]);
}

export function registerShaderNodeTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "shader_node_add",
      description:
        "Add a node to a material/world/node-group tree by bl_idname (e.g. ShaderNodeBsdfPrincipled).",
      inputSchema: {
        materialName: z.string().optional().describe("Material owning the tree."),
        worldName: z.string().optional().describe("World owning the tree."),
        nodeGroupName: z.string().optional().describe("Node group tree name."),
        type: z.string().describe("Node bl_idname."),
        name: z.string().optional().describe("Node name."),
        location: z.tuple([z.number(), z.number()]).optional().describe("Editor [x,y] location."),
      },
      handler: passthroughPost("/shader_node/add"),
    },
    {
      name: "shader_node_set_input_value",
      description: "Set the default_value on a shader node input socket.",
      inputSchema: {
        materialName: z.string().optional().describe("Material tree."),
        worldName: z.string().optional().describe("World tree."),
        nodeGroupName: z.string().optional().describe("Node group tree."),
        nodeName: z.string().describe("Target node name."),
        socketName: z.union([z.string(), z.number().int()]).describe("Socket name or index."),
        value: z.unknown().describe("New value (scalar, color [r,g,b,a], or vector)."),
      },
      handler: passthroughPost("/shader_node/set_input_value"),
    },
    {
      name: "shader_node_connect_pins",
      description: "Create a link between two shader node sockets.",
      inputSchema: {
        materialName: z.string().optional().describe("Material tree."),
        worldName: z.string().optional().describe("World tree."),
        nodeGroupName: z.string().optional().describe("Node group tree."),
        fromNodeName: z.string().describe("Source node name."),
        fromSocketName: z.string().describe("Source output socket."),
        toNodeName: z.string().describe("Target node name."),
        toSocketName: z.string().describe("Target input socket."),
      },
      handler: passthroughPost("/shader_node/connect_pins"),
    },
    {
      name: "shader_node_remove",
      description: "Delete a shader node from a tree.",
      inputSchema: {
        materialName: z.string().optional(),
        worldName: z.string().optional(),
        nodeGroupName: z.string().optional(),
        nodeName: z.string().describe("Node to remove."),
      },
      handler: passthroughPost("/shader_node/remove"),
    },
    {
      name: "shader_node_list",
      description: "Snapshot of all nodes and links in a shader tree.",
      inputSchema: {
        materialName: z.string().optional(),
        worldName: z.string().optional(),
        nodeGroupName: z.string().optional(),
      },
      handler: passthroughPost("/shader_node/list"),
    },
  ]);
}

export function registerNodeGroupTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "node_group_create",
      description: "Create a new node-group datablock (default ShaderNodeTree).",
      inputSchema: {
        name: z.string().describe("Node group name."),
        treeType: z
          .enum(["ShaderNodeTree", "GeometryNodeTree", "CompositorNodeTree"])
          .optional()
          .describe("Tree type (default ShaderNodeTree)."),
      },
      handler: passthroughPost("/node_group/create"),
    },
    {
      name: "node_group_instance_in_material",
      description: "Add a ShaderNodeGroup pointing at an existing node group, in a material.",
      inputSchema: {
        materialName: z.string().describe("Host material."),
        nodeGroupName: z.string().describe("Existing node group to instance."),
        location: z.tuple([z.number(), z.number()]).optional().describe("Editor location."),
      },
      handler: passthroughPost("/node_group/instance_in_material"),
    },
  ]);
}
