/**
 * Mesh-edit (bmesh) tools (B3).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

const Vec3 = z.tuple([z.number(), z.number(), z.number()]);

export function registerMeshTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "mesh_extrude_region_move",
      description: "Extrude selected mesh region and translate.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        offset: Vec3.describe("Translation vector for the extrusion."),
      },
      handler: passthroughPost("/mesh/extrude_region_move"),
    },
    {
      name: "mesh_bevel",
      description: "Bevel selected edges/faces.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        offset: z.number().nonnegative().describe("Bevel offset distance."),
        segments: z.number().int().min(1).optional().describe("Segment count (default 2)."),
        profile: z.number().min(0).max(1).optional().describe("Profile factor (default 0.5)."),
      },
      handler: passthroughPost("/mesh/bevel"),
    },
    {
      name: "mesh_loop_cut",
      description: "Insert N edge loops on the active edge ring.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        numberCuts: z.number().int().min(1).optional().describe("Number of cuts (default 1)."),
      },
      handler: passthroughPost("/mesh/loop_cut"),
    },
    {
      name: "mesh_subdivide",
      description: "Subdivide the selected mesh faces.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        numberCuts: z.number().int().min(1).optional().describe("Number of subdivisions."),
        smoothness: z.number().min(0).optional().describe("Smoothness (default 0)."),
      },
      handler: passthroughPost("/mesh/subdivide"),
    },
    {
      name: "mesh_merge_by_distance",
      description: "Merge vertices closer than `threshold` (remove doubles).",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        threshold: z.number().positive().optional().describe("Merge distance (default 1e-4)."),
      },
      handler: passthroughPost("/mesh/merge_by_distance"),
    },
    {
      name: "mesh_shade_smooth",
      description: "Set object shading to smooth.",
      inputSchema: { objectName: z.string().describe("Mesh object.") },
      handler: passthroughPost("/mesh/shade_smooth"),
    },
    {
      name: "mesh_shade_flat",
      description: "Set object shading to flat.",
      inputSchema: { objectName: z.string().describe("Mesh object.") },
      handler: passthroughPost("/mesh/shade_flat"),
    },
    {
      name: "mesh_recalc_normals",
      description: "Recalculate face normals (outside or inside).",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        inside: z.boolean().optional().describe("Flip normals inward (default false)."),
      },
      handler: passthroughPost("/mesh/recalc_normals"),
    },
    {
      name: "mesh_triangulate",
      description: "Convert all quads to triangles.",
      inputSchema: { objectName: z.string().describe("Mesh object.") },
      handler: passthroughPost("/mesh/triangulate"),
    },
    {
      name: "mesh_join",
      description: "Join source meshes into the target mesh.",
      inputSchema: {
        targetObjectName: z.string().describe("Mesh to receive the geometry."),
        sourceObjectNames: z.array(z.string()).min(1).describe("Source meshes to merge in."),
      },
      handler: passthroughPost("/mesh/join"),
    },
    {
      name: "mesh_separate_by_loose_parts",
      description: "Separate loose mesh islands into new objects.",
      inputSchema: { objectName: z.string().describe("Mesh object.") },
      handler: passthroughPost("/mesh/separate_by_loose_parts"),
    },
  ]);
}
