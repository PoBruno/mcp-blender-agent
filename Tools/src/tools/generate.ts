/**
 * Generative bridges (S6-15) — image-to-3D via external backends.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerGenerateTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "generate_image_to_3d",
      description:
        "Generate a mesh from a reference image via a configured image-to-3D backend (Hunyuan3D local / Tripo / Meshy / Rodin) — the realistic path for organic/photoreal content. Returns imported object names. With no backend configured returns errorCode BACKEND_NOT_CONFIGURED plus how to enable it; fall back to the parametric/primitive path meanwhile.",
      inputSchema: {
        imagePath: z.string().describe("Path to the reference image."),
        name: z.string().optional().describe("Name for the generated object."),
        targetPolycount: z.number().int().positive().optional().describe("Desired tri budget."),
        removeBackground: z.boolean().optional().describe("Ask the backend to matte the subject."),
        importInto: z.string().optional().describe("Collection to import the result into."),
      },
      handler: passthroughPost("/generate/image_to_3d", { timeoutMs: 900_000 }),
    },
  ]);
}
