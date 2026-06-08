/**
 * Animation tools (B6).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughPost, registerTools } from "../tool-helpers.js";

export function registerAnimationTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "action_create",
      description: "Create (or reuse) an Action datablock.",
      inputSchema: { name: z.string().describe("Action name.") },
      handler: passthroughPost("/action/create"),
    },
    {
      name: "action_assign_to_object",
      description: "Assign an Action to an object's animation_data.",
      inputSchema: {
        objectName: z.string().describe("Owner object."),
        actionName: z.string().describe("Action name."),
      },
      handler: passthroughPost("/action/assign_to_object"),
    },
    {
      name: "action_list",
      description:
        "List every Action in bpy.data.actions with frame range, fcurve count, slot count, fake-user flag. Pure read — handles both legacy and Blender 4.4+ layered actions.",
      inputSchema: {
        namePattern: z
          .string()
          .optional()
          .describe("Substring filter on action names."),
      },
      handler: passthroughPost("/action/list"),
    },
    {
      name: "action_inspect",
      description:
        "Deep-inspect a single action: categorize every fcurve as bone / shape_key / object / other, list touched bones, and compute a contentHash usable for dedup (NLA push-down clones produce identical hashes). Use BEFORE batch-exporting actions to filter out shape-key-only or duplicate takes.",
      inputSchema: {
        actionName: z.string().describe("Action name to inspect."),
      },
      handler: passthroughPost("/action/inspect"),
    },
    {
      name: "action_rename",
      description:
        "Rename an action. Idempotent (same name → no-op). Refuses name collision. Use to sanitize artist-named actions like 'Armature|Armature|Walk' → 'Walk_F' before export.",
      inputSchema: {
        actionName: z.string().describe("Current action name."),
        newName: z.string().describe("New action name."),
      },
      handler: passthroughPost("/action/rename"),
    },
    {
      name: "aim_offset_bake_9_pose_matrix",
      description:
        "Bake a 9-pose AimOffset (3x3 yaw/pitch grid) by distributing rotation across spine + neck + head bones (ARTIS §3.3 — 'cabeça gira mais que tronco'). Default weights split as 17/22/61% yaw and 5/15/80% pitch.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        actionName: z
          .string()
          .optional()
          .describe("Action to write keyframes into (default 'AimOffset', created if missing)."),
        spineBoneName: z.string().describe("Spine bone (e.g. spine_02)."),
        neckBoneName: z.string().describe("Neck bone (e.g. neck_01)."),
        headBoneName: z.string().describe("Head bone (e.g. head_01)."),
        yawWeights: z
          .array(z.number())
          .length(3)
          .optional()
          .describe("Yaw share [spine, neck, head] — default [0.17, 0.22, 0.61]."),
        pitchWeights: z
          .array(z.number())
          .length(3)
          .optional()
          .describe("Pitch share [spine, neck, head] — default [0.05, 0.15, 0.80]."),
        yawDegMax: z
          .number()
          .positive()
          .optional()
          .describe("Maximum yaw angle in degrees at corner poses (default 90)."),
        pitchDegMax: z
          .number()
          .positive()
          .optional()
          .describe("Maximum pitch angle in degrees at corner poses (default 45)."),
        frameStart: z
          .number()
          .int()
          .optional()
          .describe("First frame (default 1; 9 poses written to frameStart..frameStart+8)."),
        yawAxisWorld: z
          .array(z.number())
          .length(3)
          .optional()
          .describe("World yaw axis (default [0,0,1] — character up)."),
        pitchAxisWorld: z
          .array(z.number())
          .length(3)
          .optional()
          .describe("World pitch axis (default [1,0,0] — character right)."),
      },
      handler: passthroughPost("/aim_offset/bake_9_pose_matrix"),
    },
    {
      name: "aim_offset_validate_9_pose_matrix",
      description:
        "Replay a baked AimOffset and measure the WORLD-space yaw/pitch the probe bone (typically the head) actually reaches at each of the 9 frames. Returns per-pose error in degrees and a maxErrorDeg. Use after aim_offset_bake_9_pose_matrix to catch local-axis bugs that look correct numerically but render broken.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        actionName: z.string().optional().describe("Action to evaluate (default 'AimOffset')."),
        probeBoneName: z
          .string()
          .describe("Bone whose world rotation is sampled — typically the head bone."),
        yawDegMax: z.number().positive().optional().describe("Max yaw angle (default 90)."),
        pitchDegMax: z.number().positive().optional().describe("Max pitch angle (default 45)."),
        frameStart: z.number().int().optional().describe("First frame (default 1)."),
        toleranceDeg: z
          .number()
          .positive()
          .optional()
          .describe("Pass threshold for |actual-expected| on yaw AND pitch (default 5°)."),
        yawAxisWorld: z
          .array(z.number())
          .length(3)
          .optional()
          .describe("World yaw axis used to build the expected rotation (default [0,0,1])."),
        pitchAxisWorld: z
          .array(z.number())
          .length(3)
          .optional()
          .describe("World pitch axis used to build the expected rotation (default [1,0,0])."),
      },
      handler: passthroughPost("/aim_offset/validate_9_pose_matrix"),
    },
    {
      name: "keyframe_add",
      description: "Insert a keyframe at a frame for a data path.",
      inputSchema: {
        objectName: z.string().describe("Object."),
        dataPath: z.string().describe("data_path, e.g. 'location'."),
        frame: z.number().int().describe("Frame number."),
        arrayIndex: z.number().int().optional().describe("Array index (default -1)."),
      },
      handler: passthroughPost("/keyframe/add"),
    },
    {
      name: "keyframe_bone_pose",
      description: "Insert keyframes for a pose bone's location/rotation/scale at a frame.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        boneName: z.string().describe("Pose bone."),
        frame: z.number().int().describe("Frame."),
        channels: z
          .array(z.enum(["location", "rotation_quaternion", "rotation_euler", "scale"]))
          .optional()
          .describe("Channels to keyframe (default all)."),
      },
      handler: passthroughPost("/keyframe/bone_pose"),
    },
    {
      name: "nla_push_action_to_strip",
      description: "Push the active action onto a new NLA strip for the object.",
      inputSchema: {
        objectName: z.string().describe("Owner object."),
        trackName: z.string().optional().describe("NLA track name."),
      },
      handler: passthroughPost("/nla/push_action_to_strip"),
    },
  ]);
}
