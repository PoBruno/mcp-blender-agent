/**
 * UV tools (B1, B4).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerUVTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "uv_layer_create",
      description: "Create a UV layer on a mesh (idempotent on name).",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        name: z.string().optional().describe("Layer name (default 'UVMap')."),
      },
      handler: passthroughPost("/uv/layer_create"),
    },
    {
      name: "uv_unwrap",
      description: "Generic angle-based/conformal unwrap of all faces.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        method: z.enum(["ANGLE_BASED", "CONFORMAL"]).optional().describe("Unwrap method."),
        margin: z.number().nonnegative().optional().describe("Margin (default 0.001)."),
      },
      handler: passthroughPost("/uv/unwrap"),
    },
    {
      name: "uv_smart_project",
      description:
        "Smart UV project — automatic seams + projection. Good kit default for modular meshes.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        angleLimit: z.number().positive().optional().describe("Angle limit degrees (default 66)."),
        islandMargin: z.number().nonnegative().optional().describe("Island margin (default 0.02)."),
        areaWeight: z.number().min(0).max(1).optional().describe("Area weight."),
        correctAspect: z.boolean().optional().describe("Correct aspect ratio."),
        scaleToBounds: z.boolean().optional().describe("Scale islands to bounds."),
      },
      handler: passthroughPost("/uv/smart_project"),
    },
    {
      name: "uv_unwrap_smart_project",
      description: "Alias for `uv_smart_project` with kit-friendly defaults.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        angleLimit: z.number().positive().optional(),
        islandMargin: z.number().nonnegative().optional(),
      },
      handler: passthroughPost("/uv/unwrap_smart_project"),
    },
    {
      name: "uv_pack_islands",
      description: "Pack UV islands within [0,1].",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        margin: z.number().nonnegative().optional().describe("Pack margin (default 0.005)."),
      },
      handler: passthroughPost("/uv/pack_islands"),
    },
    {
      name: "uv_average_islands_scale",
      description: "Average the scale of all UV islands.",
      inputSchema: { objectName: z.string().describe("Mesh object.") },
      handler: passthroughPost("/uv/average_islands_scale"),
    },
    {
      name: "uv_mark_seams",
      description: "Mark seams from current edge selection (or auto from sharp edges).",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        fromSharp: z.boolean().optional().describe("Mark seams on sharp edges (default false)."),
      },
      handler: passthroughPost("/uv/mark_seams"),
    },
    {
      name: "uv_minimize_stretch",
      description: "Minimize UV stretch via iterative relaxation.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        iterations: z.number().int().min(1).optional().describe("Iterations (default 32)."),
      },
      handler: passthroughPost("/uv/minimize_stretch"),
    },
    {
      name: "uv_validate_for_baking",
      description:
        "Validate UVs for baking: ensure a UV layer exists and count out-of-bounds loops.",
      inputSchema: { objectName: z.string().describe("Mesh object.") },
      handler: passthroughPost("/uv/validate_for_baking"),
    },
  ]);
}
