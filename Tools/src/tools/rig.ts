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
    {
      name: "armature_add_ue5_ik_bones",
      description:
        "Add the 7 UE5 SK_Mannequin IK control bones (ik_foot_root, ik_foot_l/r, ik_hand_root, ik_hand_gun, ik_hand_l/r). Non-deforming by default. Sibling-of-root layout that UE5 auto-detects on import.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        useDeform: z
          .boolean()
          .optional()
          .describe("Mark bones as deforming (default false — they're targets only)."),
        skipExisting: z
          .boolean()
          .optional()
          .describe("If true, skip bones that already exist (default true)."),
      },
      handler: passthroughPost("/armature/add_ue5_ik_bones"),
    },
    {
      name: "armature_validate_ue5_convention",
      description:
        "Validate an armature against UE5 SK_Mannequin conventions: lowercase names, _l/_r suffixes (not .L/.R), zero-roll on specified spine/neck/head bones, required bones present. Returns ok=false + errorCode='VALIDATION_FAILED' with a detailed failures[] if any check fails. Pure read; never mutates.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        zeroRollBones: z
          .array(z.string())
          .optional()
          .describe("Bones that MUST have |roll| < tolerance."),
        rollToleranceRad: z
          .number()
          .nonnegative()
          .optional()
          .describe("Roll tolerance in radians (default 0.01 ~= 0.57°)."),
        requireLowercase: z
          .boolean()
          .optional()
          .describe("Reject uppercase characters in bone names (default true)."),
        requireUnderscoreLR: z
          .boolean()
          .optional()
          .describe("Reject .L/.R suffix; UE5 expects _l/_r (default true)."),
        requiredBones: z
          .array(z.string())
          .optional()
          .describe("Bone names that MUST exist in the armature."),
      },
      handler: passthroughPost("/armature/validate_ue5_convention"),
    },
    {
      name: "armature_rename_to_ue5_convention",
      description:
        "Batch-rename every bone in an armature to UE5 conventions: .L/.R → _l/_r (also .L_end → _l_end) and lowercase. SOCKET_* and ik_* bones are skipped. Two-pass rename avoids transient collisions. Vertex groups auto-update. Wrap in dryRun=true first to preview the plan and detect name collisions.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        lowercase: z
          .boolean()
          .optional()
          .describe("Lowercase every bone name (default true)."),
        suffixLR: z
          .boolean()
          .optional()
          .describe("Rewrite .L/.R suffix to _l/_r (default true)."),
        dryRun: z
          .boolean()
          .optional()
          .describe("If true, return the plan and exit without mutating."),
        exclude: z
          .array(z.string())
          .optional()
          .describe("Bone names to leave untouched."),
      },
      handler: passthroughPost("/armature/rename_to_ue5_convention"),
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
    {
      name: "bone_list",
      description:
        "List all edit bones with head/tail/roll/length/parent/useDeform/useConnect. Optional substring name filter. Use to audit a rig (find rolled bones, build a name set for renaming, verify UE5 convention).",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        namePattern: z
          .string()
          .optional()
          .describe("Substring filter on bone names (case-sensitive)."),
      },
      handler: passthroughPost("/bone/list"),
    },
    {
      name: "bone_set_edit_transform",
      description:
        "Set head/tail/roll/useDeform/useConnect on an existing edit bone. Pass only the keys you want to change. All edits run in EDIT mode and are wrapped in a single undo.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneName: z.string().describe("Bone to mutate."),
        head: Vec3.optional().describe("New head (local space)."),
        tail: Vec3.optional().describe("New tail (local space)."),
        roll: z.number().optional().describe("New roll (radians)."),
        useDeform: z.boolean().optional().describe("Whether bone deforms geometry."),
        useConnect: z.boolean().optional().describe("Connect head to parent tail."),
      },
      handler: passthroughPost("/bone/set_edit_transform"),
    },
    {
      name: "bone_set_roll",
      description:
        "Set roll (radians) on one or more edit bones. Pass roll=0 to clear roll. Prefer bone_recalculate_roll when you want auto-fix from a reference axis.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneNames: z.array(z.string()).min(1).describe("Bones to update."),
        roll: z.number().describe("Roll value in radians."),
      },
      handler: passthroughPost("/bone/set_roll"),
    },
    {
      name: "bone_recalculate_roll",
      description:
        "Auto-recalculate roll on a set of bones using a reference axis (wraps bpy.ops.armature.calculate_roll). For UE5 spine/neck/head, use type='GLOBAL_POS_Z'. Valid types: POS_X/Y/Z, NEG_X/Y/Z, GLOBAL_POS_X/Y/Z, GLOBAL_NEG_X/Y/Z, ACTIVE, VIEW, CURSOR.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneNames: z.array(z.string()).min(1).describe("Bones to recalculate."),
        type: z
          .enum([
            "POS_X", "POS_Y", "POS_Z",
            "NEG_X", "NEG_Y", "NEG_Z",
            "GLOBAL_POS_X", "GLOBAL_POS_Y", "GLOBAL_POS_Z",
            "GLOBAL_NEG_X", "GLOBAL_NEG_Y", "GLOBAL_NEG_Z",
            "ACTIVE", "VIEW", "CURSOR",
          ])
          .optional()
          .describe("Reference axis (default 'GLOBAL_POS_Z')."),
      },
      handler: passthroughPost("/bone/recalculate_roll"),
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
