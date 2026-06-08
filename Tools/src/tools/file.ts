/**
 * File IO + library + asset tools (B9).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerFileTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "file_new",
      description:
        "Reset the Blender session to a fresh empty .blend (factory startup). Active filepath becomes empty until file_save_as. Use empty=true to skip the default cube/camera/light.",
      inputSchema: {
        empty: z
          .boolean()
          .optional()
          .describe("If true, start with no default cube/camera/light (default false)."),
      },
      handler: passthroughPost("/file/new"),
    },
    {
      name: "file_save",
      description: "Save the current .blend (must have been saved before).",
      inputSchema: {},
      handler: passthroughPost("/file/save"),
    },
    {
      name: "file_save_as",
      description: "Save the current file to a new filepath.",
      inputSchema: { filepath: z.string().describe("Absolute filepath.") },
      handler: passthroughPost("/file/save_as"),
    },
    {
      name: "file_open",
      description: "Open a .blend file (replaces current scene).",
      inputSchema: { filepath: z.string().describe("Absolute filepath to open.") },
      handler: passthroughPost("/file/open"),
    },
    {
      name: "file_append_data",
      description: "Append datablocks from another .blend file.",
      inputSchema: {
        filepath: z.string().describe("Source .blend filepath."),
        datablockType: z
          .enum(["Object", "Material", "Mesh", "Armature", "Action", "Image", "NodeGroup"])
          .describe("Datablock type to append."),
        names: z.array(z.string()).min(1).describe("Datablock names to append."),
      },
      handler: passthroughPost("/file/append_data"),
    },
    {
      name: "file_pack_all",
      description: "Pack all external textures/files into the .blend.",
      inputSchema: {},
      handler: passthroughPost("/file/pack_all"),
    },
    {
      name: "file_unpack_all",
      description: "Unpack all packed files using a chosen method.",
      inputSchema: {
        method: z
          .enum([
            "USE_LOCAL",
            "WRITE_LOCAL",
            "USE_ORIGINAL",
            "WRITE_ORIGINAL",
            "KEEP",
            "REMOVE",
          ])
          .optional()
          .describe("Unpack method (default USE_LOCAL)."),
      },
      handler: passthroughPost("/file/unpack_all"),
    },
  ]);
}

export function registerLibraryTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "library_link",
      description: "Link (don't append) datablocks from a library .blend.",
      inputSchema: {
        filepath: z.string().describe("Library .blend filepath."),
        datablockType: z
          .enum(["Object", "Collection", "Material", "NodeGroup", "Action"])
          .describe("Datablock kind."),
        names: z.array(z.string()).min(1).describe("Names to link."),
      },
      handler: passthroughPost("/library/link"),
    },
    {
      name: "library_make_override",
      description: "Create a library override on a linked object (Blender 4.x flow).",
      inputSchema: { objectName: z.string().describe("Linked object name.") },
      handler: passthroughPost("/library/make_override"),
    },
    {
      name: "library_reload",
      description: "Reload a library by its filepath.",
      inputSchema: { filepath: z.string().describe("Library filepath.") },
      handler: passthroughPost("/library/reload"),
    },
  ]);
}

export function registerAssetTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "asset_mark",
      description: "Mark an object as an asset; set tags / catalog / description.",
      inputSchema: {
        objectName: z.string().describe("Object to mark."),
        tags: z.array(z.string()).optional().describe("Asset tags."),
        catalogId: z.string().optional().describe("Asset catalog UUID."),
        description: z.string().optional().describe("Asset description."),
      },
      handler: passthroughPost("/asset/mark"),
    },
    {
      name: "asset_clear",
      description: "Clear an object's asset marker.",
      inputSchema: { objectName: z.string().describe("Object.") },
      handler: passthroughPost("/asset/clear"),
    },
  ]);
}
