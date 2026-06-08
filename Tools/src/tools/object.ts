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
  ]);
}
