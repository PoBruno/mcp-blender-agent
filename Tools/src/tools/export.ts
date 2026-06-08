/**
 * Export / import tools (B1, B6, B7, B9).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

const FbxAxis = z.enum(["X", "Y", "Z", "-X", "-Y", "-Z"]);
const FbxScaleOpts = z.enum([
  "FBX_SCALE_NONE",
  "FBX_SCALE_UNITS",
  "FBX_SCALE_CUSTOM",
  "FBX_SCALE_ALL",
]);
const PathMode = z.enum(["AUTO", "ABSOLUTE", "RELATIVE", "MATCH", "STRIP", "COPY"]);

export function registerExportStaticTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "export_fbx_static",
      description:
        "Export selected objects as a static-mesh FBX with full UE5-friendly defaults (axis -Z forward / Y up, apply_unit_scale, armature_deform_only, no leaf bones).",
      inputSchema: {
        filepath: z.string().describe("Absolute output filepath."),
        objectNames: z.array(z.string()).min(1).describe("Objects to include in selection."),
        globalScale: z.number().positive().optional().describe("Scale (default 1.0)."),
        applyUnitScale: z.boolean().optional().describe("Apply scene unit scale (default true)."),
        applyScaleOptions: FbxScaleOpts.optional().describe("FBX scale handling."),
        axisForward: FbxAxis.optional().describe("Forward axis (default -Z)."),
        axisUp: FbxAxis.optional().describe("Up axis (default Y)."),
        objectTypes: z
          .array(z.enum(["MESH", "ARMATURE", "EMPTY", "CAMERA", "LIGHT", "OTHER"]))
          .optional()
          .describe("Object types to export."),
        useMeshModifiers: z.boolean().optional().describe("Apply modifiers on export."),
        meshSmoothType: z
          .enum(["OFF", "FACE", "EDGE"])
          .optional()
          .describe("Mesh smoothing export mode."),
        useSubsurf: z.boolean().optional().describe("Export subsurf as such."),
        useMeshEdges: z.boolean().optional().describe("Include loose edges."),
        useTspace: z.boolean().optional().describe("Export tangent space."),
        useTriangles: z.boolean().optional().describe("Convert all to triangles."),
        useCustomProps: z.boolean().optional().describe("Export ID custom properties."),
        addLeafBones: z.boolean().optional().describe("Add leaf bones (default false)."),
        primaryBoneAxis: FbxAxis.optional().describe("Primary bone axis (default Y)."),
        secondaryBoneAxis: FbxAxis.optional().describe("Secondary bone axis (default X)."),
        useArmatureDeformOnly: z
          .boolean()
          .optional()
          .describe("Export only deform bones (default true)."),
        bakeAnim: z.boolean().optional().describe("Bake animation."),
        pathMode: PathMode.optional().describe("Texture path mode."),
        embedTextures: z.boolean().optional().describe("Embed textures."),
        batchMode: z
          .enum(["OFF", "SCENE", "COLLECTION", "OBJECT", "GROUP", "SCENE_COLLECTION"])
          .optional()
          .describe("Batch mode."),
        bakeSpaceTransform: z.boolean().optional().describe("Bake space transform."),
      },
      handler: passthroughPost("/export/fbx_static"),
    },
    {
      name: "export_fbx_collection_batch",
      description:
        "Export each top-level object in a collection as its own FBX file (incl. UCX_/UBX_/SOCKET_ children if requested).",
      inputSchema: {
        collectionName: z.string().describe("Collection to walk."),
        outputDirectory: z.string().describe("Output directory."),
        filenameTemplate: z
          .string()
          .optional()
          .describe("Filename template; {ObjectName} substituted. Default 'SM_{ObjectName}.fbx'."),
        includeCollisionChildren: z
          .boolean()
          .optional()
          .describe("Include UCX_/UBX_/USP_/UCP_/SOCKET_/LOD_ children (default true)."),
        globalScale: z.number().positive().optional(),
        applyUnitScale: z.boolean().optional(),
        axisForward: FbxAxis.optional(),
        axisUp: FbxAxis.optional(),
      },
      handler: passthroughPost("/export/fbx_collection_batch"),
    },
    {
      name: "export_gltf",
      description: "Export selection as glTF 2.0 (.glb or .gltf).",
      inputSchema: {
        filepath: z.string().describe("Absolute output filepath."),
        objectNames: z.array(z.string()).min(1).describe("Objects to include in selection."),
        exportFormat: z.enum(["GLB", "GLTF_SEPARATE", "GLTF_EMBEDDED"]).optional().describe("glTF flavor."),
        exportApply: z.boolean().optional().describe("Apply modifiers on export."),
        exportAnimations: z.boolean().optional().describe("Include animations."),
        exportYup: z.boolean().optional().describe("Use Y-up convention (default true)."),
        exportExtras: z.boolean().optional().describe("Export custom props as extras."),
      },
      handler: passthroughPost("/export/gltf"),
    },
  ]);
}

export function registerExportAnimationTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "export_fbx_skeletal",
      description: "Export an armature + skinned meshes as a skeletal-mesh FBX (UE5 friendly).",
      inputSchema: {
        filepath: z.string().describe("Absolute output filepath."),
        armatureObjectName: z.string().describe("Armature whose mesh children are exported."),
        globalScale: z.number().positive().optional(),
        applyUnitScale: z.boolean().optional(),
        axisForward: FbxAxis.optional(),
        axisUp: FbxAxis.optional(),
        useMeshModifiers: z.boolean().optional(),
        meshSmoothType: z.enum(["OFF", "FACE", "EDGE"]).optional(),
        useTspace: z.boolean().optional(),
        addLeafBones: z.boolean().optional(),
        primaryBoneAxis: FbxAxis.optional(),
        secondaryBoneAxis: FbxAxis.optional(),
        useArmatureDeformOnly: z.boolean().optional(),
        bakeSpaceTransform: z.boolean().optional().describe("Bake space transform into the mesh (UE5: set true with axisForward='-Y', axisUp='Z' for a clean import)."),
        bakeAnim: z.boolean().optional(),
        pathMode: PathMode.optional(),
      },
      handler: passthroughPost("/export/fbx_skeletal"),
    },
    {
      name: "export_fbx_animation",
      description: "Export an animation-only FBX (armature + baked NLA/actions).",
      inputSchema: {
        filepath: z.string().describe("Absolute output filepath."),
        armatureObjectName: z.string().describe("Armature owning the animation."),
        globalScale: z.number().positive().optional(),
        applyUnitScale: z.boolean().optional(),
        axisForward: FbxAxis.optional(),
        axisUp: FbxAxis.optional(),
        addLeafBones: z.boolean().optional(),
        primaryBoneAxis: FbxAxis.optional(),
        secondaryBoneAxis: FbxAxis.optional(),
        bakeSpaceTransform: z.boolean().optional().describe("Bake space transform (UE5: set true with axisForward='-Y', axisUp='Z')."),
        useNlaStrips: z.boolean().optional().describe("Bake NLA strips (default true)."),
        useAllActions: z.boolean().optional().describe("Export every action as a take."),
        bakeAnimStep: z.number().positive().optional().describe("Bake step (default 1.0)."),
        bakeAnimSimplifyFactor: z.number().nonnegative().optional().describe("Simplify factor."),
        pathMode: PathMode.optional(),
      },
      handler: passthroughPost("/export/fbx_animation"),
    },
  ]);
}

export function registerImportTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "import_fbx",
      description: "Import an FBX file. Returns the names of new objects.",
      inputSchema: { filepath: z.string().describe("FBX filepath.") },
      handler: passthroughPost("/import/fbx"),
    },
    {
      name: "import_obj",
      description: "Import a Wavefront OBJ.",
      inputSchema: { filepath: z.string().describe("OBJ filepath.") },
      handler: passthroughPost("/import/obj"),
    },
    {
      name: "import_gltf",
      description: "Import a glTF 2.0 file (.glb or .gltf).",
      inputSchema: { filepath: z.string().describe("glTF filepath.") },
      handler: passthroughPost("/import/gltf"),
    },
  ]);
}
