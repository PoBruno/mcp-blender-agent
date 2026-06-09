/**
 * Post-processing pipeline tools (Sprint 6).
 *
 * Phase 7 of the aaa-modeling skill: retopo, UV, decimate, LOD, normals.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerPostprocTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "postproc_voxel_remesh",
      description:
        "Voxel-remesh to uniform topology. Heals intersections, fills gaps, removes non-manifold geometry. Smaller voxelSize ⇒ denser mesh. Run BEFORE quad_remesh on dirty meshes.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        voxelSize: z.number().positive().optional().describe(
          "Voxel side length in meters (default 0.02). Smaller = denser.",
        ),
        adaptivity: z.number().min(0).max(1).optional().describe("0..1, default 0."),
        useSmoothShade: z.boolean().optional().describe("Smooth normals. Default true."),
      },
      handler: passthroughPost("/postproc/voxel_remesh"),
    },
    {
      name: "postproc_quad_remesh",
      description:
        "QuadriFlow quad-dominant remesh. Use AFTER voxel_remesh for clean topology suitable for rigging/animation.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        targetFaces: z.number().int().min(16).optional().describe(
          "Target quad face count. Default 2000.",
        ),
        useMeshSymmetry: z.boolean().optional().describe("Preserve X-symmetry. Default false."),
        useSharpEdges: z.boolean().optional().describe("Preserve sharp edges. Default true."),
        useSmoothNormals: z.boolean().optional().describe("Smooth normals on output. Default true."),
      },
      handler: passthroughPost("/postproc/quad_remesh"),
    },
    {
      name: "postproc_smart_uv_project",
      description:
        "Smart UV project across the whole mesh — one-shot unwrap suitable for baking.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        angleLimit: z.number().positive().optional().describe("Angle limit in degrees. Default 66."),
        islandMargin: z.number().min(0).optional().describe("Island margin (UV units). Default 0.02."),
        areaWeight: z.number().min(0).max(1).optional().describe("Area-weighted importance. Default 0."),
        correctAspect: z.boolean().optional().describe("Correct aspect from material. Default true."),
        scaleToBounds: z.boolean().optional().describe("Scale to UV bounds. Default true."),
      },
      handler: passthroughPost("/postproc/smart_uv_project"),
    },
    {
      name: "postproc_decimate",
      description:
        "Add a DECIMATE modifier (COLLAPSE/UNSUBDIV/DISSOLVE). Set apply=true to bake immediately, or leave live for LOD chains.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        decimateType: z.enum(["COLLAPSE", "UNSUBDIV", "DISSOLVE"]).optional().describe(
          "Algorithm. Default COLLAPSE.",
        ),
        ratio: z.number().min(0).max(1).optional().describe("COLLAPSE ratio. Default 0.5."),
        iterations: z.number().int().min(1).optional().describe("UNSUBDIV iterations. Default 2."),
        angleLimit: z.number().positive().optional().describe("DISSOLVE angle (deg). Default 5."),
        apply: z.boolean().optional().describe("Apply modifier immediately. Default false."),
        modifierName: z.string().optional().describe("Modifier name. Default 'Decimate'."),
      },
      handler: passthroughPost("/postproc/decimate"),
    },
    {
      name: "postproc_lod_generate",
      description:
        "Generate N decimated LOD copies. Each is independent and named '<base>_LOD<i>'. The base is preserved unchanged as LOD0.",
      inputSchema: {
        objectName: z.string().describe("Mesh object (becomes LOD0, unchanged)."),
        levels: z.number().int().min(1).max(8).optional().describe("Number of LODs to create. Default 3."),
        ratios: z.array(z.number().min(0.001).max(0.999)).optional().describe(
          "Per-level collapse ratios. Default [0.5,0.25,0.10]. Length must equal levels.",
        ),
      },
      handler: passthroughPost("/postproc/lod_generate"),
    },
    {
      name: "postproc_auto_smooth_normals",
      description:
        "Set shade-smooth + auto-smooth angle. On 4.1+ adds a Smooth-by-Angle modifier; on earlier sets the legacy mesh.use_auto_smooth flag.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        angle: z.number().positive().optional().describe("Angle in degrees. Default 30."),
      },
      handler: passthroughPost("/postproc/auto_smooth_normals"),
    },
  ]);
}
