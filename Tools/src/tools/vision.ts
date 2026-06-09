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
      name: "vision_snapshot",
      description:
        "Fast single PNG of the current state — the feedback tool for the inner refine loop. Prefers an instant viewport screenshot (GUI Blender) and falls back to one fast EEVEE render in background mode. Frames the target objects. Call this each iteration; reserve vision_contact_sheet / full renders for the final beauty gate.",
      inputSchema: {
        outputPath: z.string().describe("Absolute path for the PNG (parent dir auto-created)."),
        objectNames: z.array(z.string()).optional().describe(
          "Objects to frame. Omit ⇒ all visible render objects.",
        ),
        angle: z.string().optional().describe(
          "Viewing angle. Default 'three_quarter'. Valid: front, back, left, right (alias side), top, bottom, three_quarter, three_quarter_back.",
        ),
        resolution: z.number().int().min(64).max(4096).optional().describe(
          "Fallback-render square resolution (px). Default 512. Ignored on the viewport path.",
        ),
        samples: z.number().int().min(1).max(4096).optional().describe(
          "Fallback-render samples. Default 16 (fast preview).",
        ),
        shading: z.string().optional().describe(
          "Viewport shading on the GUI path: SOLID, MATERIAL (default), RENDERED, WIREFRAME.",
        ),
        forceRender: z.boolean().optional().describe(
          "Skip the viewport path and always render. Default false.",
        ),
        sceneName: z.string().optional().describe("Scene name. Default active."),
      },
      handler: passthroughPost("/vision/snapshot", { timeoutMs: 120_000 }),
    },
    {
      name: "vision_contact_sheet",
      description:
        "Render N angles of the targets and compose a single PNG grid. Output path is the assembled sheet. Use this for the final multi-angle gate; for the inner refine loop prefer vision_snapshot (faster). Self-critique against the brief on the 6-axis rubric (silhouette/proportions/topology/material/lighting/reference).",
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
        samples: z.number().int().min(1).max(4096).optional().describe(
          "Render samples. Default 16 (fast preview).",
        ),
        engine: z.string().optional().describe(
          "Optional render engine override. Default EEVEE for speed (BLENDER_EEVEE, BLENDER_EEVEE_NEXT, CYCLES).",
        ),
        sceneName: z.string().optional().describe("Scene to render. Default active."),
      },
      handler: passthroughPost("/vision/contact_sheet", { timeoutMs: 300_000 }),
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
        samples: z.number().int().min(1).max(4096).optional().describe("Render samples. Default 16."),
        filenamePrefix: z.string().optional().describe("Filename prefix. Default 'turntable_'."),
        engine: z.string().optional().describe("Render engine override. Default EEVEE for speed."),
        sceneName: z.string().optional().describe("Scene name."),
      },
      handler: passthroughPost("/vision/turntable", { timeoutMs: 600_000 }),
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
    {
      name: "vision_render_action",
      description:
        "Render an action's frames from a fixed angle and assemble a horizontal strip PNG — so you can SEE the motion (walk/idle/etc) in one image. Optionally assigns the action first. Use this to review an animation instead of guessing from keyframes.",
      inputSchema: {
        outputDir: z.string().describe("Directory for the frame PNGs + strip (auto-created)."),
        frameStart: z.number().int().describe("First frame."),
        frameEnd: z.number().int().describe("Last frame."),
        step: z.number().int().min(1).optional().describe("Frame step. Default 2."),
        objectNames: z.array(z.string()).optional().describe("Framed targets. Omit ⇒ all visible."),
        armatureObjectName: z.string().optional().describe("Armature to assign the action to (with actionName)."),
        actionName: z.string().optional().describe("Action to assign before rendering."),
        angle: z.string().optional().describe("Camera angle. Default 'three_quarter' (use 'left'/'right' for walk profiles)."),
        resolution: z.number().int().min(64).max(4096).optional().describe("Per-frame square px. Default 384."),
        samples: z.number().int().min(1).max(4096).optional().describe("Render samples. Default 16."),
        engine: z.string().optional().describe("Render engine override. Default EEVEE."),
        filenamePrefix: z.string().optional().describe("Frame filename prefix. Default 'action_'."),
        makeStrip: z.boolean().optional().describe("Assemble a horizontal strip PNG. Default true."),
        sceneName: z.string().optional().describe("Scene name."),
      },
      handler: passthroughPost("/vision/render_action", { timeoutMs: 900_000 }),
    },
    {
      name: "vision_silhouette_compare",
      description:
        "Render the model's silhouette and score it against a reference image: returns IoU + a diff heatmap (green=overlap, red=excess to trim, blue=missing to add). A pLDDT-style structural-confidence signal to drive the refine loop. Reference should be an alpha-matte or clean-background image.",
      inputSchema: {
        referenceImage: z.string().describe("Path to the reference image (alpha matte or clean bg)."),
        outputPath: z.string().describe("Path for the diff heatmap PNG."),
        objectNames: z.array(z.string()).optional().describe("Targets. Omit ⇒ all visible."),
        angle: z.string().optional().describe("Camera angle. Default 'front'."),
        resolution: z.number().int().min(64).max(2048).optional().describe("Square px. Default 256."),
        threshold: z.number().min(0).max(1).optional().describe("Alpha/silhouette threshold. Default 0.5."),
        samples: z.number().int().min(1).max(256).optional().describe("Render samples. Default 8."),
        engine: z.string().optional().describe("Render engine override."),
        sceneName: z.string().optional().describe("Scene name."),
      },
      handler: passthroughPost("/vision/silhouette_compare", { timeoutMs: 300_000 }),
    },
  ]);
}
