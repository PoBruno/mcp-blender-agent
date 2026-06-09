/**
 * Modifier tools (B2).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerModifierTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "modifier_add",
      description:
        "Add a modifier to an object (e.g. SUBSURF, MIRROR, BEVEL, ARRAY, BOOLEAN, SOLIDIFY, ARMATURE, NODES).",
      inputSchema: {
        objectName: z.string().describe("Object to receive the modifier."),
        type: z.string().describe("Modifier type — bpy ModifierType enum value."),
        name: z.string().optional().describe("Modifier name (defaults to type)."),
        params: z.record(z.unknown()).optional().describe("Property assignments after creation."),
      },
      handler: passthroughPost("/modifier/add"),
    },
    {
      name: "modifier_set_property",
      description: "Set one or more properties on an existing modifier.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        modifierName: z.string().describe("Modifier name."),
        properties: z.record(z.unknown()).describe("Property->value map."),
      },
      handler: passthroughPost("/modifier/set_property"),
    },
    {
      name: "modifier_apply",
      description: "Apply (bake) a modifier into the mesh.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        modifierName: z.string().describe("Modifier name."),
      },
      handler: passthroughPost("/modifier/apply"),
    },
    {
      name: "modifier_remove",
      description: "Remove a modifier without applying.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        modifierName: z.string().describe("Modifier name."),
      },
      handler: passthroughPost("/modifier/remove"),
    },
    {
      name: "modifier_list",
      description: "List modifiers on an object.",
      inputSchema: { objectName: z.string().describe("Object.") },
      handler: passthroughPost("/modifier/list"),
    },
    {
      name: "modifier_reorder",
      description: "Move a modifier UP or DOWN in the stack.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        modifierName: z.string().describe("Modifier name."),
        direction: z.enum(["UP", "DOWN"]).describe("Direction in stack."),
      },
      handler: passthroughPost("/modifier/reorder"),
    },
  ]);
}
