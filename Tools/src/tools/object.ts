/**
 * Object primitive tools (B1, B7).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

const Vec3 = z.tuple([z.number(), z.number(), z.number()]);

export function registerObjectTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "object_create",
      description: "Create a primitive mesh or empty object in the scene.",
      inputSchema: {
        type: z
          .enum(["CUBE", "PLANE", "SPHERE", "CYLINDER", "CONE", "TORUS", "ICOSPHERE", "EMPTY"])
          .describe("Primitive type."),
        name: z.string().optional().describe("Object name."),
        size: z.number().positive().optional().describe("Primitive size (default 2.0)."),
        location: Vec3.optional().describe("World location [x,y,z]."),
        rotation: Vec3.optional().describe("Euler rotation in radians."),
        scale: Vec3.optional().describe("Object scale."),
        collectionName: z.string().optional().describe("Target collection."),
      },
      handler: passthroughPost("/object/create"),
    },
    {
      name: "object_apply_transform",
      description:
        "Bake object location/rotation/scale into mesh data (transform_apply). Apply SCALE before width-based ops (Bevel/Solidify) — non-uniform object scale distorts them. Defaults to scale only.",
      inputSchema: {
        objectName: z.string().describe("Object to apply."),
        location: z.boolean().optional().describe("Apply location (default false)."),
        rotation: z.boolean().optional().describe("Apply rotation (default false)."),
        scale: z.boolean().optional().describe("Apply scale (default true)."),
      },
      handler: passthroughPost("/object/apply_transform"),
    },
    {
      name: "object_set_mode",
      description:
        "Switch an object into a mode. Use to recover from a stuck Sculpt/Edit mode that makes operators (shade_smooth, join) fail their poll.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        mode: z
          .enum(["OBJECT", "EDIT", "POSE", "SCULPT", "VERTEX_PAINT", "WEIGHT_PAINT", "TEXTURE_PAINT"])
          .describe("Target mode."),
      },
      handler: passthroughPost("/object/set_mode"),
    },
    {
      name: "object_rename",
      description: "Rename an object. Blender may auto-suffix on collision; the final name is returned.",
      inputSchema: {
        objectName: z.string().describe("Current name."),
        newName: z.string().describe("Desired new name."),
      },
      handler: passthroughPost("/object/rename"),
    },
    {
      name: "object_add_blockout",
      description:
        "Add a cube blockout sized to a footprint (w,d,h in BU). Scale applied so dimensions match.",
      inputSchema: {
        name: z.string().describe("Object name."),
        footprint: Vec3.describe("[width, depth, height] in Blender units."),
        location: Vec3.optional().describe("Origin location."),
        collectionName: z.string().optional().describe("Target collection."),
      },
      handler: passthroughPost("/object/add_blockout"),
    },
    {
      name: "object_set_transform",
      description: "Set object location / rotation_euler / scale.",
      inputSchema: {
        objectName: z.string().describe("Object name."),
        location: Vec3.optional().describe("New location."),
        rotation: Vec3.optional().describe("New Euler rotation (radians)."),
        scale: Vec3.optional().describe("New scale."),
      },
      handler: passthroughPost("/object/set_transform"),
    },
    {
      name: "object_duplicate_linked",
      description: "Duplicate an object with linked (shared) mesh data.",
      inputSchema: {
        objectName: z.string().describe("Source object name."),
        newName: z.string().optional().describe("Name for the duplicate."),
      },
      handler: passthroughPost("/object/duplicate_linked"),
    },
    {
      name: "object_delete",
      description:
        "Remove one or more objects from the .blend (data + scene unlink). Idempotent — missing names are silently skipped unless strict=true. Use this to clean up default cubes after file_new before importing real content.",
      inputSchema: {
        objectNames: z
          .array(z.string())
          .optional()
          .describe("List of object names to delete."),
        objectName: z
          .string()
          .optional()
          .describe("Single object name (alternative to objectNames)."),
        strict: z
          .boolean()
          .optional()
          .describe("If true, raise OBJECT_NOT_FOUND on the first missing name."),
      },
      handler: passthroughPost("/object/delete"),
    },
    {
      name: "mesh_set_origin_to_snap_corner",
      description:
        "Move the object origin to a named corner of its bounding box (e.g. MIN_X_MIN_Y_MIN_Z).",
      inputSchema: {
        objectName: z.string().describe("Object name."),
        corner: z
          .enum([
            "MIN_X_MIN_Y_MIN_Z",
            "MAX_X_MIN_Y_MIN_Z",
            "MIN_X_MAX_Y_MIN_Z",
            "MAX_X_MAX_Y_MIN_Z",
            "MIN_X_MIN_Y_MAX_Z",
            "MAX_X_MIN_Y_MAX_Z",
            "MIN_X_MAX_Y_MAX_Z",
            "MAX_X_MAX_Y_MAX_Z",
          ])
          .describe("Bounding-box corner."),
      },
      handler: passthroughPost("/mesh/set_origin_to_snap_corner"),
    },
    {
      name: "collection_instance_create",
      description: "Create an Empty that instances a collection (single-object level placement).",
      inputSchema: {
        collectionName: z.string().describe("Collection to instance."),
        name: z.string().optional().describe("Empty name."),
        location: Vec3.optional().describe("Empty location."),
      },
      handler: passthroughPost("/collection/instance_create"),
    },
    {
      name: "mesh_parent_to_armature",
      description: "Parent a mesh to an armature and add/wire an Armature modifier.",
      inputSchema: {
        meshObjectName: z.string().describe("Mesh to parent."),
        armatureObjectName: z.string().describe("Armature object."),
      },
      handler: passthroughPost("/mesh/parent_to_armature"),
    },
    {
      name: "object_list",
      description:
        "List every object in bpy.data.objects with type, transform, parent, modifier count, collections, hide state. Optional type / name / collection filter. Pure read — use to discover what's in a loaded .blend before chaining mutations.",
      inputSchema: {
        typeFilter: z
          .union([z.string(), z.array(z.string())])
          .optional()
          .describe("Object type(s) to keep (e.g. 'ARMATURE' or ['MESH','ARMATURE'])."),
        namePattern: z
          .string()
          .optional()
          .describe("Substring filter on object names (case-sensitive)."),
        collectionName: z
          .string()
          .optional()
          .describe("Only objects belonging to this collection."),
      },
      handler: passthroughPost("/object/list"),
    },
    {
      name: "object_get_info",
      description:
        "Deep introspection of a single object — parent/children, modifiers, animation_data, plus type-specific summary (MESH: vert/uv/material/shape-key counts; ARMATURE: bone count, sockets; EMPTY: display type). Pure read.",
      inputSchema: {
        objectName: z.string().describe("Object name to inspect."),
      },
      handler: passthroughPost("/object/get_info"),
    },
  ]);
}
