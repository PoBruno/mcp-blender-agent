/**
 * Armature + bone + bone-collection + constraint + driver + vertex-group + shape-key tools (B7).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

const Vec3 = z.tuple([z.number(), z.number(), z.number()]);
const Vec4 = z.tuple([z.number(), z.number(), z.number(), z.number()]);

export function registerArmatureTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "armature_create",
      description: "Create a new armature object with empty data.",
      inputSchema: {
        name: z.string().optional().describe("Armature object name."),
        location: Vec3.optional().describe("World location."),
        collectionName: z.string().optional().describe("Target collection."),
      },
      handler: passthroughPost("/armature/create"),
    },
    {
      name: "armature_show_in_front",
      description: "Toggle armature display 'show_in_front'.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        show: z.boolean().optional().describe("Show in front (default true)."),
      },
      handler: passthroughPost("/armature/show_in_front"),
    },
  ]);
}

export function registerBoneTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "bone_add",
      description: "Add an edit bone (enters EDIT mode internally).",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        name: z.string().describe("Bone name."),
        head: Vec3.describe("Head position (local space)."),
        tail: Vec3.describe("Tail position (local space)."),
        parentName: z.string().optional().describe("Parent bone name."),
        useConnect: z.boolean().optional().describe("Connect to parent tail."),
        roll: z.number().optional().describe("Bone roll (radians)."),
      },
      handler: passthroughPost("/bone/add"),
    },
    {
      name: "bone_set_parent",
      description: "Re-parent a bone in EDIT mode.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneName: z.string().describe("Bone to re-parent."),
        parentName: z.string().optional().describe("Parent bone (omit to unparent)."),
        useConnect: z.boolean().optional().describe("Connect to parent tail."),
      },
      handler: passthroughPost("/bone/set_parent"),
    },
    {
      name: "bone_rename",
      description: "Rename a bone in EDIT mode (auto-updates vertex groups too).",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        oldName: z.string().describe("Current bone name."),
        newName: z.string().describe("New bone name."),
      },
      handler: passthroughPost("/bone/rename"),
    },
    {
      name: "bone_set_pose_transform",
      description: "Set pose-bone location / rotation_(quaternion|euler) / scale.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneName: z.string().describe("Pose bone name."),
        location: Vec3.optional().describe("Pose space translation."),
        rotationQuaternion: Vec4.optional().describe("Quaternion [w,x,y,z]."),
        rotationEuler: Vec3.optional().describe("Euler XYZ."),
        scale: Vec3.optional().describe("Pose scale."),
      },
      handler: passthroughPost("/bone/set_pose_transform"),
    },
    {
      name: "bone_delete",
      description: "Delete a bone in EDIT mode.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneName: z.string().describe("Bone to delete."),
      },
      handler: passthroughPost("/bone/delete"),
    },
  ]);
}

export function registerBoneCollectionTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "bone_collection_create",
      description: "Create a bone collection on an armature (Blender 4.x).",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        name: z.string().describe("Bone collection name."),
      },
      handler: passthroughPost("/bone_collection/create"),
    },
    {
      name: "bone_collection_assign_bone",
      description: "Assign a bone to a bone collection.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneCollectionName: z.string().describe("Bone collection name."),
        boneName: z.string().describe("Bone name."),
      },
      handler: passthroughPost("/bone_collection/assign_bone"),
    },
  ]);
}

export function registerConstraintTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "bone_add_constraint",
      description: "Add a constraint to a pose bone.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneName: z.string().describe("Pose bone name."),
        type: z.string().describe("Constraint type (e.g. IK, COPY_LOCATION, LIMIT_ROTATION)."),
        name: z.string().optional().describe("Constraint name."),
        targetObjectName: z.string().optional().describe("Target object name."),
        targetBoneName: z.string().optional().describe("Target bone (subtarget)."),
        params: z.record(z.unknown()).optional().describe("Property assignments."),
      },
      handler: passthroughPost("/bone/add_constraint"),
    },
    {
      name: "object_add_constraint",
      description: "Add a constraint to an object.",
      inputSchema: {
        objectName: z.string().describe("Owner object."),
        type: z.string().describe("Constraint type."),
        name: z.string().optional().describe("Constraint name."),
        targetObjectName: z.string().optional().describe("Target object."),
        params: z.record(z.unknown()).optional().describe("Property assignments."),
      },
      handler: passthroughPost("/object/add_constraint"),
    },
  ]);
}

export function registerDriverTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "driver_add",
      description: "Add a SCRIPTED driver to a data path on an object.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        dataPath: z.string().describe("data_path, e.g. 'location' or 'pose.bones[\"B\"].location'."),
        arrayIndex: z.number().int().optional().describe("Array index (default -1)."),
        expression: z.string().optional().describe("Python expression (default 'var')."),
        variables: z
          .array(z.record(z.unknown()))
          .optional()
          .describe("Driver variables: name, type, targetObjectName, dataPath, transformType, transformSpace."),
      },
      handler: passthroughPost("/driver/add"),
    },
    {
      name: "driver_remove",
      description: "Remove a driver by data_path/array_index.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        dataPath: z.string().describe("data_path."),
        arrayIndex: z.number().int().optional().describe("Array index (default -1)."),
      },
      handler: passthroughPost("/driver/remove"),
    },
  ]);
}

export function registerVertexGroupTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "vertex_group_create",
      description: "Create (or reuse) a vertex group on a mesh.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        name: z.string().describe("Vertex group name."),
      },
      handler: passthroughPost("/vertex_group/create"),
    },
    {
      name: "vertex_group_assign_vertices",
      description: "Assign vertices to a vertex group with a uniform weight.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        vertexGroupName: z.string().describe("Vertex group."),
        vertexIndices: z.array(z.number().int()).min(1).describe("Vertex indices."),
        weight: z.number().min(0).max(1).optional().describe("Weight (default 1.0)."),
      },
      handler: passthroughPost("/vertex_group/assign_vertices"),
    },
    {
      name: "vertex_group_delete",
      description: "Delete a vertex group from a mesh.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        vertexGroupName: z.string().describe("Vertex group to delete."),
      },
      handler: passthroughPost("/vertex_group/delete"),
    },
  ]);
}

export function registerShapeKeyTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "shape_key_add",
      description: "Add a shape key on a mesh (creates Basis first if missing).",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        name: z.string().optional().describe("Shape key name."),
        fromMix: z.boolean().optional().describe("Derive from current mix (default false)."),
      },
      handler: passthroughPost("/shape_key/add"),
    },
    {
      name: "shape_key_set_value",
      description: "Set the value (0..1) of a shape key on a mesh.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        shapeKeyName: z.string().describe("Shape key name."),
        value: z.number().describe("Value to set."),
      },
      handler: passthroughPost("/shape_key/set_value"),
    },
    {
      name: "shape_key_rename",
      description: "Rename a shape key.",
      inputSchema: {
        objectName: z.string().describe("Mesh object."),
        oldName: z.string().describe("Existing name."),
        newName: z.string().describe("New name."),
      },
      handler: passthroughPost("/shape_key/rename"),
    },
  ]);
}

export function registerMetaHumanTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "metahuman_arkit52_list",
      description: "Return the canonical ARKit-52 blendshape names (per ADR-009).",
      inputSchema: {},
      handler: passthroughPost("/metahuman/arkit52_list"),
    },
    {
      name: "metahuman_ensure_arkit52_shape_keys",
      description: "Ensure all 52 ARKit shape keys exist on the head mesh (creates missing).",
      inputSchema: { objectName: z.string().describe("Head mesh object.") },
      handler: passthroughPost("/metahuman/ensure_arkit52_shape_keys"),
    },
  ]);
}
