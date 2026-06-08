/**
 * Bake + image tools (B4).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerBakeTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "bake_setup_target_image",
      description:
        "Create an Image and a selected ImageTexture node on a material so the next bake lands here.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        materialName: z.string().describe("Material owning the destination image node."),
        imageName: z.string().optional().describe("Image datablock name."),
        width: z.number().int().min(64).optional().describe("Width (default 1024)."),
        height: z.number().int().min(64).optional().describe("Height (default 1024)."),
      },
      handler: passthroughPost("/bake/setup_target_image"),
    },
    {
      name: "bake_run",
      description:
        "Run a Cycles bake. Engine is set to CYCLES first. Use bake_setup_target_image first.",
      inputSchema: {
        objectName: z.string().describe("Object to bake."),
        type: z
          .enum([
            "COMBINED",
            "AO",
            "SHADOW",
            "NORMAL",
            "UV",
            "ROUGHNESS",
            "EMIT",
            "ENVIRONMENT",
            "DIFFUSE",
            "GLOSSY",
            "TRANSMISSION",
            "POSITION",
          ])
          .describe("Bake pass type."),
        samples: z.number().int().min(1).optional().describe("Cycles samples."),
        useSelectedToActive: z.boolean().optional().describe("High→low transfer bake."),
        margin: z.number().int().nonnegative().optional().describe("Bake margin (default 16)."),
        marginType: z.enum(["EXTEND", "ADJACENT_FACES"]).optional().describe("Margin algorithm."),
        useClear: z.boolean().optional().describe("Clear image before bake (default true)."),
      },
      handler: passthroughPost("/bake/run"),
    },
    {
      name: "image_save_as",
      description: "Save a bpy.data.image to disk.",
      inputSchema: {
        imageName: z.string().describe("Image datablock name."),
        filepath: z.string().describe("Absolute output filepath."),
        fileFormat: z
          .enum(["PNG", "JPEG", "OPEN_EXR", "TIFF", "TARGA"])
          .optional()
          .describe("File format (default PNG)."),
      },
      handler: passthroughPost("/image/save_as"),
    },
  ]);
}
