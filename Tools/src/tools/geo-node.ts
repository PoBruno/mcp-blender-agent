/**
 * Geometry-nodes + compositor tools (B8).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

const Vec2 = z.tuple([z.number(), z.number()]);

export function registerGeoNodeTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "geo_node_group_create",
      description: "Create a GeometryNodeTree pre-wired with Group Input → Group Output.",
      inputSchema: { name: z.string().describe("Node group name.") },
      handler: passthroughPost("/geo_node/group_create"),
    },
    {
      name: "geo_node_add_node",
      description: "Add a node by bl_idname into a GeometryNodeTree.",
      inputSchema: {
        nodeGroupName: z.string().describe("Geometry node group name."),
        type: z.string().describe("Node bl_idname (e.g. GeometryNodeMeshCube)."),
        name: z.string().optional().describe("Node name override."),
        location: Vec2.optional().describe("Editor location."),
      },
      handler: passthroughPost("/geo_node/add_node"),
    },
    {
      name: "geo_node_connect",
      description: "Link two sockets in a GeometryNodeTree.",
      inputSchema: {
        nodeGroupName: z.string().describe("Geometry node group name."),
        fromNodeName: z.string(),
        fromSocketName: z.string(),
        toNodeName: z.string(),
        toSocketName: z.string(),
      },
      handler: passthroughPost("/geo_node/connect"),
    },
    {
      name: "geo_node_apply_to_object",
      description: "Add a Geometry Nodes modifier to an object and wire it to a node group.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        nodeGroupName: z.string().describe("GeometryNodeTree name."),
        modifierName: z.string().optional().describe("Modifier name (default 'GeometryNodes')."),
      },
      handler: passthroughPost("/geo_node/apply_to_object"),
    },
  ]);
}

export function registerCompositorTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "compositor_enable",
      description: "Enable compositor nodes on the scene.",
      inputSchema: { sceneName: z.string().optional().describe("Scene; default = active.") },
      handler: passthroughPost("/compositor/enable"),
    },
    {
      name: "compositor_add_node",
      description: "Add a compositor node by bl_idname.",
      inputSchema: {
        sceneName: z.string().optional(),
        type: z.string().describe("Compositor node bl_idname (e.g. CompositorNodeRLayers)."),
        name: z.string().optional(),
        location: Vec2.optional(),
      },
      handler: passthroughPost("/compositor/add_node"),
    },
    {
      name: "compositor_connect",
      description: "Link two compositor sockets.",
      inputSchema: {
        sceneName: z.string().optional(),
        fromNodeName: z.string(),
        fromSocketName: z.string(),
        toNodeName: z.string(),
        toSocketName: z.string(),
      },
      handler: passthroughPost("/compositor/connect"),
    },
  ]);
}
