/**
 * Vision feedback tools (Sprint 6 — AAA pipeline).
 *
 * These give the agent eyes: render contact sheets, turntables, inspect
 * topology, report scale. They are how the "render → critique → refine"
 * recycling loop works.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerVisionTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "vision_contact_sheet",
      description:
        "Render N angles of the targets and compose a single PNG grid. Output path is the assembled sheet. Use this AFTER any model build to self-critique against the brief on the 6-axis rubric (silhouette/proportions/topology/material/lighting/reference).",
      inputSchema: {
        outputPath: z.string().describe("Absolute path for the assembled PNG (parent dir auto-created)."),
        objectNames: z.array(z.string()).optional().describe(
          "Specific objects to frame. Omit ⇒ all visible render objects.",
        ),
        angles: z.array(z.string()).optional().describe(
          "Angle keywords. Defaults to ['front','side','top','three_quarter']. Valid: front, back, left, right (alias: side), top, bottom, three_quarter, three_quarter_back.",
        ),
        resolution: z.number().int().min(64).max(4096).optional().describe(
          "Per-tile square resolution (px). Default 384.",
        ),
        padding: z.number().positive().optional().describe(
          "Camera framing padding multiplier. Default 1.4.",
        ),
        keepTiles: z.boolean().optional().describe(
          "Keep individual tile PNGs next to the grid. Default false.",
        ),
        engine: z.string().optional().describe(
          "Optional render engine override (BLENDER_EEVEE, BLENDER_EEVEE_NEXT, CYCLES).",
        ),
        sceneName: z.string().optional().describe("Scene to render. Default active."),
      },
      handler: passthroughPost("/vision/contact_sheet"),
    },
    {
      name: "vision_turntable",
      description:
        "Render a 360° rotation of the targets as a sequence of PNGs. Use for animation review or to capture references for video editors.",
      inputSchema: {
        outputDir: z.string().describe("Directory for the N rendered PNGs (auto-created)."),
        objectNames: z.array(z.string()).optional().describe("Targets. Omit ⇒ all visible."),
        frames: z.number().int().min(2).max(360).optional().describe("Frame count. Default 12 (every 30°)."),
        elevation: z.number().optional().describe("Camera elevation in degrees. Default 12."),
        resolution: z.number().int().min(64).max(4096).optional().describe("Square px. Default 512."),
        padding: z.number().positive().optional().describe("Framing padding. Default 1.4."),
        filenamePrefix: z.string().optional().describe("Filename prefix. Default 'turntable_'."),
        engine: z.string().optional().describe("Render engine override."),
        sceneName: z.string().optional().describe("Scene name."),
      },
      handler: passthroughPost("/vision/turntable"),
    },
    {
      name: "vision_topology_inspect",
      description:
        "Per-object topology metrics: tri/quad/ngon counts, manifoldness, loose vertices, UV presence, estimated render tris. Use as a quality gate before export.",
      inputSchema: {
        objectNames: z.array(z.string()).optional().describe(
          "Targets. Omit ⇒ all MESH objects in scene.",
        ),
      },
      handler: passthroughPost("/vision/topology_inspect"),
    },
    {
      name: "vision_scale_report",
      description:
        "World-space AABB + dimensions for the targets, with optional comparison to an expected size. Use to verify the asset matches the spec sheet's dimensions.",
      inputSchema: {
        objectNames: z.array(z.string()).optional().describe("Targets. Omit ⇒ all visible."),
        expected: z
          .object({
            x: z.number().positive().optional().describe("Expected X dimension (m)."),
            y: z.number().positive().optional().describe("Expected Y dimension (m)."),
            z: z.number().positive().optional().describe("Expected Z dimension (m)."),
          })
          .optional()
          .describe("Expected dimensions in meters."),
        tolerance: z.number().positive().optional().describe(
          "Fractional tolerance (0.10 ⇒ ±10%). Default 0.10.",
        ),
      },
      handler: passthroughPost("/vision/scale_report"),
    },
    {
      name: "vision_screenshot_viewport",
      description:
        "Capture the current 3D viewport to PNG. Only works in GUI mode (returns NO_VIEWPORT in background Blender).",
      inputSchema: {
        outputPath: z.string().describe("Absolute path for the PNG."),
      },
      handler: passthroughPost("/vision/screenshot_viewport"),
    },
  ]);
}
