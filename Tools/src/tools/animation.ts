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
