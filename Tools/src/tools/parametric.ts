/**
 * Parametric library tools (Sprint 6).
 *
 * Phase A of the aaa-modeling skill: prefer parametric builders over manual
 * primitive composition. Also exposes the proportion/timing/material matrices
 * (the "pair representation" from AlphaFold) for the agent to query before
 * making decisions.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerParametricTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "parametric_list",
      description:
        "List every parametric builder registered in BlenderAgent/library. Each builder turns a small params dict into a topologically-clean named-parts asset.",
      inputSchema: {},
      handler: passthroughPost("/parametric/list"),
    },
    {
      name: "parametric_build",
      description:
        "Invoke a parametric builder by name. Pass partial params; missing keys fall back to the canonical defaults. Returns object names in refs for chaining into vision/postproc.",
      inputSchema: {
        name: z.string().describe(
          "Builder name (see parametric_list). E.g. 'chair_beach', 'table_dining', 'stool_bar'.",
        ),
        params: z
          .record(z.string(), z.unknown())
          .optional()
          .describe(
            "Builder-specific parameters. See the builder's docstring (parametric_list returns the first line of each). All keys are optional.",
          ),
      },
      handler: passthroughPost("/parametric/build"),
    },
    {
      name: "parametric_anatomy_human",
      description:
        "Resolve a human proportion canon (heroic_male, fashion, realistic_adult, chibi, etc.) at a given total height. Returns every landmark in meters. Use BEFORE creating an armature to lock proportions.",
      inputSchema: {
        canon: z.string().optional().describe(
          "Canon name. See listCanons. Required unless listCanons=true.",
        ),
        height: z.number().positive().optional().describe(
          "Total height in meters. Required unless listCanons=true.",
        ),
        listCanons: z.boolean().optional().describe(
          "List the available canon names instead of resolving.",
        ),
      },
      handler: passthroughPost("/parametric/anatomy/human"),
    },
    {
      name: "parametric_anatomy_furniture",
      description:
        "Return ergonomic default dimensions for a known furniture kind. Use BEFORE building to anchor the spec.",
      inputSchema: {
        kind: z.string().optional().describe(
          "Furniture kind. See list=true. Required unless list=true.",
        ),
        list: z.boolean().optional().describe("List known kinds instead."),
      },
      handler: passthroughPost("/parametric/anatomy/furniture"),
    },
    {
      name: "parametric_animation_timing",
      description:
        "Frame timing presets for common animation cycles (walk_cycle_human, run_cycle_human, idle_breathing, jump_neutral). Optionally rescale to a custom fps.",
      inputSchema: {
        kind: z.string().optional().describe(
          "Cycle name. See list=true.",
        ),
        fps: z.number().positive().optional().describe(
          "Target fps for rescaling (defaults to the preset's fps).",
        ),
        list: z.boolean().optional().describe("List known cycles instead."),
      },
      handler: passthroughPost("/parametric/animation/timing"),
    },
    {
      name: "parametric_material_recipe",
      description:
        "PBR values for a known material archetype (weathered_teak, polished_oak, faded_canvas_orange, brushed_aluminum, skin_caucasian, fabric_denim).",
      inputSchema: {
        name: z.string().optional().describe("Recipe name. See list=true."),
        list: z.boolean().optional().describe("List known recipes instead."),
      },
      handler: passthroughPost("/parametric/material/recipe"),
    },
  ]);
}
