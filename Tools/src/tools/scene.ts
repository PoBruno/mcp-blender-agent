/**
 * Scene + collection + view-layer tools (B1, B9.D).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughGet, passthroughPost, registerTools } from "../tool-helpers.js";

export function registerSceneTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "scene_create",
      description: "Create a new scene with unit-system, scale, and frame-range.",
      inputSchema: {
        name: z.string().describe("New scene name."),
        unitSystem: z.enum(["METRIC", "IMPERIAL", "NONE"]).optional().describe("Unit system."),
        scaleLength: z.number().positive().optional().describe("Unit scale length (default 1.0)."),
        frameStart: z.number().int().optional().describe("Start frame (default 1)."),
        frameEnd: z.number().int().optional().describe("End frame (default 250)."),
      },
      handler: passthroughPost("/scene/create"),
    },
    {
      name: "scene_set_active",
      description: "Set the active scene on the current window.",
      inputSchema: { sceneName: z.string().describe("Scene name to activate.") },
      handler: passthroughPost("/scene/set_active"),
    },
    {
      name: "scene_set_unit_scale_for_modular_kit",
      description: "Configure scene units for UE5 modular-kit workflows (defaults to 1 BU = 1 cm).",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene name; default = active."),
        scale: z.number().positive().optional().describe("Unit scale length (default 0.01)."),
      },
      handler: passthroughPost("/scene/set_unit_scale_for_modular_kit"),
    },
    {
      name: "scene_list",
      description: "List all scenes in the file.",
      inputSchema: {},
      handler: passthroughGet("/scene/list"),
    },
    {
      name: "scene_set_frame_range",
      description: "Set scene frame_start and frame_end.",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene name; default = active."),
        frameStart: z.number().int().describe("Start frame."),
        frameEnd: z.number().int().describe("End frame."),
      },
      handler: passthroughPost("/scene/set_frame_range"),
    },
  ]);
}

export function registerCollectionTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "collection_create",
      description: "Create a collection (idempotent — returns existing if already present).",
      inputSchema: {
        name: z.string().describe("Collection name."),
        parentPath: z.string().optional().describe("Parent collection name."),
        sceneName: z.string().optional().describe("Scene to attach to; default = active."),
      },
      handler: passthroughPost("/collection/create"),
    },
    {
      name: "collection_move_objects",
      description: "Move objects into a target collection, unlinking from previous collections.",
      inputSchema: {
        collectionName: z.string().describe("Target collection name."),
        objectNames: z.array(z.string()).min(1).describe("Object names to move."),
      },
      handler: passthroughPost("/collection/move_objects"),
    },
    {
      name: "collection_list",
      description: "List all collections with their object counts.",
      inputSchema: {},
      handler: passthroughGet("/collection/list"),
    },
    {
      name: "collection_delete",
      description: "Delete a collection. Objects within are unlinked, not deleted.",
      inputSchema: { collectionName: z.string().describe("Collection name to delete.") },
      handler: passthroughPost("/collection/delete"),
    },
  ]);
}

export function registerViewLayerTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "view_layer_create",
      description: "Create a new view layer on a scene.",
      inputSchema: {
        name: z.string().describe("View layer name."),
        sceneName: z.string().optional().describe("Scene name; default = active."),
      },
      handler: passthroughPost("/view_layer/create"),
    },
    {
      name: "view_layer_create_for_export",
      description:
        "Create an export-only view layer that excludes all collections except those named.",
      inputSchema: {
        name: z.string().optional().describe("View layer name (default 'Export')."),
        collectionNames: z.array(z.string()).min(1).describe("Collections to keep visible."),
        sceneName: z.string().optional().describe("Scene name; default = active."),
      },
      handler: passthroughPost("/view_layer/create_for_export"),
    },
    {
      name: "view_layer_list",
      description: "List view layers on a scene.",
      inputSchema: { sceneName: z.string().optional().describe("Scene; default = active.") },
      handler: passthroughGet("/view_layer/list"),
    },
  ]);
}
