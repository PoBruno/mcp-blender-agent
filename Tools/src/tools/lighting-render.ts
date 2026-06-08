/**
 * Light + world + camera + render tools (B9).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

const Vec3 = z.tuple([z.number(), z.number(), z.number()]);

export function registerLightTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "light_create",
      description: "Create a light object (POINT/SUN/SPOT/AREA).",
      inputSchema: {
        type: z.enum(["POINT", "SUN", "SPOT", "AREA"]).describe("Light type."),
        name: z.string().optional().describe("Light name."),
        energy: z.number().nonnegative().optional().describe("Energy/power."),
        color: Vec3.optional().describe("RGB color."),
        location: Vec3.optional().describe("World location."),
        collectionName: z.string().optional().describe("Target collection."),
      },
      handler: passthroughPost("/light/create"),
    },
    {
      name: "light_set_property",
      description: "Set properties on a light's data (energy, color, spot_size, ...).",
      inputSchema: {
        objectName: z.string().describe("Light object."),
        properties: z.record(z.unknown()).describe("Property assignments."),
      },
      handler: passthroughPost("/light/set_property"),
    },
  ]);
}

export function registerWorldTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "world_create",
      description: "Create a World datablock (use_nodes=true).",
      inputSchema: { name: z.string().optional().describe("World name.") },
      handler: passthroughPost("/world/create"),
    },
    {
      name: "world_assign_to_scene",
      description: "Assign a World to a scene.",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene name; default = active."),
        worldName: z.string().describe("World name."),
      },
      handler: passthroughPost("/world/assign_to_scene"),
    },
  ]);
}

export function registerCameraTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "camera_create",
      description: "Create a camera with lens, location, rotation.",
      inputSchema: {
        name: z.string().optional().describe("Camera name."),
        location: Vec3.optional().describe("World location."),
        rotation: Vec3.optional().describe("Euler rotation (radians)."),
        lens: z.number().positive().optional().describe("Lens mm (default 50)."),
        collectionName: z.string().optional().describe("Target collection."),
      },
      handler: passthroughPost("/camera/create"),
    },
    {
      name: "camera_set_active",
      description: "Set the active camera of a scene.",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene name; default = active."),
        objectName: z.string().describe("Camera object."),
      },
      handler: passthroughPost("/camera/set_active"),
    },
  ]);
}

export function registerRenderTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "render_set_engine",
      description: "Set the render engine for a scene (CYCLES/EEVEE/EEVEE_NEXT/WORKBENCH).",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene; default = active."),
        engine: z.enum(["CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"]),
      },
      handler: passthroughPost("/render/set_engine"),
    },
    {
      name: "render_set_resolution",
      description: "Set render resolution and percentage.",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene; default = active."),
        width: z.number().int().min(1).describe("Pixel width."),
        height: z.number().int().min(1).describe("Pixel height."),
        percentage: z.number().int().min(1).max(100).optional().describe("Percentage (default 100)."),
      },
      handler: passthroughPost("/render/set_resolution"),
    },
    {
      name: "render_render_still",
      description: "Render a single frame and save to filepath.",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene; default = active."),
        filepath: z.string().describe("Absolute filepath."),
        fileFormat: z
          .enum(["PNG", "JPEG", "OPEN_EXR", "OPEN_EXR_MULTILAYER", "TIFF", "TARGA"])
          .optional()
          .describe("File format (default PNG)."),
      },
      handler: passthroughPost("/render/render_still"),
    },
    {
      name: "render_render_animation",
      description: "Render the animation frame range to disk.",
      inputSchema: {
        sceneName: z.string().optional().describe("Scene; default = active."),
        filepathPrefix: z.string().describe("Output filepath prefix (frame number appended)."),
        fileFormat: z
          .enum(["PNG", "JPEG", "OPEN_EXR", "OPEN_EXR_MULTILAYER", "TIFF", "TARGA"])
          .optional()
          .describe("File format (default PNG)."),
      },
      handler: passthroughPost("/render/render_animation"),
    },
  ]);
}
