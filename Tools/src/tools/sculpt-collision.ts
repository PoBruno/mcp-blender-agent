/**
 * Sculpt + collision + socket tools (B2, B3).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

const Vec3 = z.tuple([z.number(), z.number(), z.number()]);

export function registerSculptTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "sculpt_enable_dyntopo",
      description: "Enter SCULPT mode and enable dyntopo with a detail-size.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        detailSize: z.number().positive().optional().describe("Dyntopo detail size."),
      },
      handler: passthroughPost("/sculpt/enable_dyntopo"),
    },
    {
      name: "sculpt_voxel_remesh",
      description: "Voxel remesh the mesh (uniform topology).",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        voxelSize: z.number().positive().optional().describe("Voxel size (default 0.05)."),
      },
      handler: passthroughPost("/sculpt/voxel_remesh"),
    },
  ]);
}

export function registerCollisionTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "collision_add_box",
      description: "Generate a UE5-named UBX_<Name>_NN box collision as a child empty mesh.",
      inputSchema: { objectName: z.string().describe("Parent mesh object.") },
      handler: passthroughPost("/collision/add_box"),
    },
    {
      name: "collision_add_convex_hull",
      description: "Generate a UE5-named UCX_<Name>_NN convex-hull collision child.",
      inputSchema: { objectName: z.string().describe("Parent mesh object.") },
      handler: passthroughPost("/collision/add_convex_hull"),
    },
  ]);
}

export function registerSocketTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "socket_add",
      description:
        "Add a SOCKET_<name> Empty for UE5 attachment. When boneName is set AND parent is an Armature, the empty is parented to that bone via parent_type='BONE' — UE5 detects this as a per-bone socket on import. Without boneName the empty is parented to the object's origin. Idempotent: re-running with the same name updates the existing socket.",
      inputSchema: {
        objectName: z.string().describe("Parent object (typically the Armature)."),
        name: z.string().describe("Socket short name (SOCKET_ prefix auto-added)."),
        boneName: z
          .string()
          .optional()
          .describe("Bone to attach to (parent must be an ARMATURE)."),
        location: Vec3.optional().describe("Local offset relative to parent / bone head."),
        rotation: Vec3.optional().describe("Local Euler rotation in radians."),
      },
      handler: passthroughPost("/socket/add"),
    },
  ]);
}
