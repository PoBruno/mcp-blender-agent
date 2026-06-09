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
      description: "Create (or reuse) an Action datablock. Fake-user is set by default so the action survives save/reload before it is assigned or pushed to NLA.",
      inputSchema: {
        name: z.string().describe("Action name."),
        useFakeUser: z.boolean().optional().describe("Keep the action even with 0 users (default true)."),
      },
      handler: passthroughPost("/action/create"),
    },
    {
      name: "pose_set",
      description:
        "Set (and optionally keyframe) MANY pose bones in one call. Replaces dozens of bone_set_pose_transform + keyframe_bone_pose calls. If `frame` is given, each touched bone is keyframed on the channel matching the rotation it set (euler vs quaternion).",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature object."),
        frame: z.number().int().optional().describe("If set, keyframe every touched bone at this frame."),
        pose: z
          .record(
            z.string(),
            z.object({
              rotationEuler: z.array(z.number()).optional().describe("[x,y,z] radians (sets XYZ mode)."),
              rotationQuaternion: z.array(z.number()).optional().describe("[w,x,y,z]."),
              location: z.array(z.number()).optional().describe("[x,y,z] pose translation."),
              scale: z.array(z.number()).optional().describe("[x,y,z] pose scale."),
            }),
          )
          .describe("Map of bone name → transform to apply."),
      },
      handler: passthroughPost("/pose/set"),
    },
    {
      name: "action_mirror",
      description:
        "Create an X-mirrored copy of an action (swaps _L/_R bone channels, negates location.x and euler Y/Z / quaternion y/z). Use to generate the opposite-side keys of a symmetric cycle (e.g. the second contact of a walk). Best-effort: assumes humanoid _L/_R naming and an X-symmetric rest pose.",
      inputSchema: {
        sourceActionName: z.string().describe("Action to mirror."),
        newActionName: z.string().describe("Name for the mirrored copy."),
        leftToken: z.string().optional().describe("Left-side token in bone names (default '_L')."),
        rightToken: z.string().optional().describe("Right-side token (default '_R')."),
      },
      handler: passthroughPost("/action/mirror"),
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
      name: "action_unassign_from_object",
      description:
        "Clear the active Action on an object so the rig evaluates at rest (bind pose). Idempotent — no-op when nothing is assigned. Use before rendering a clean bind-pose validation shot.",
      inputSchema: {
        objectName: z.string().describe("Owner object whose action will be cleared."),
      },
      handler: passthroughPost("/action/unassign_from_object"),
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
      name: "aim_offset_split_to_9_single_frame_actions",
      description:
        "Split a baked 9-pose AimOffset action (frames 1..9) into 9 single-frame actions, one per BlendSpace2D cell. Snapshots every touched pose-bone channel at the source frame and re-keys it at frame 1 of a new action. Cell suffixes: LU CU RU LC CC RC LD CD RD (Left/Center/Right × Up/Center/Down). Use before exporting individual AnimSequences for UE5 BlendSpace2D.",
      inputSchema: {
        armatureObjectName: z.string().describe("Armature owning the source action (used to snapshot pose at each source frame)."),
        sourceActionName: z.string().describe("The baked 9-pose master action (e.g. 'AimOffset_Char')."),
        targetPrefix: z
          .string()
          .optional()
          .describe("Prefix for the 9 new actions (default '<sourceActionName>_'). Final names = prefix + cell suffix."),
        frameStart: z
          .number()
          .int()
          .optional()
          .describe("Source frame of the first cell (default 1; 9 cells sampled at frameStart..frameStart+8)."),
      },
      handler: passthroughPost("/aim_offset/split_to_9_single_frame_actions"),
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
    {
      name: "nla_track_add",
      description: "Create an empty NLA track on an object. Returns the (possibly auto-suffixed) track name.",
      inputSchema: {
        objectName: z.string().describe("Owner object."),
        trackName: z.string().optional().describe("Desired name (default 'NlaTrack')."),
      },
      handler: passthroughPost("/nla/track_add"),
    },
    {
      name: "nla_list",
      description:
        "List every NLA track and its strips for an object. Returns blend type, extrapolation, frame range, mute and influence per strip.",
      inputSchema: {
        objectName: z.string().describe("Owner object."),
      },
      handler: passthroughPost("/nla/list"),
    },
    {
      name: "nla_strip_remove",
      description: "Remove a strip from an NLA track by name. Idempotent on absence.",
      inputSchema: {
        objectName: z.string().describe("Owner object."),
        trackName: z.string().describe("Track containing the strip."),
        stripName: z.string().describe("Strip to remove."),
      },
      handler: passthroughPost("/nla/strip_remove"),
    },
    {
      name: "nla_strip_update",
      description:
        "Mutate an NLA strip in place: blend type, extrapolation, mute, influence, frame range. Pass only the keys you want to change.",
      inputSchema: {
        objectName: z.string().describe("Owner object."),
        trackName: z.string().describe("Track containing the strip."),
        stripName: z.string().describe("Strip to update."),
        blendType: z.enum(["REPLACE", "COMBINE", "ADD", "SUBTRACT", "MULTIPLY"]).optional(),
        extrapolation: z.enum(["NOTHING", "HOLD", "HOLD_FORWARD"]).optional(),
        mute: z.boolean().optional(),
        influence: z.number().min(0).max(1).optional(),
        frameStart: z.number().optional(),
        frameEnd: z.number().optional(),
      },
      handler: passthroughPost("/nla/strip_update"),
    },
    {
      name: "anim_bake_action",
      description:
        "Bake an object's evaluated motion (constraints + drivers + NLA) into a flat keyed action. Wraps bpy.ops.nla.bake. Use to flatten IK solutions before export. POSE bake for armatures, OBJECT bake for everything else. Set clearConstraints=true to fully replace the rig solver with keyframes.",
      inputSchema: {
        objectName: z.string().describe("Armature or other animated object."),
        frameStart: z.number().int().describe("First frame to bake."),
        frameEnd: z.number().int().describe("Last frame to bake."),
        step: z.number().int().min(1).optional().describe("Frame step (default 1)."),
        onlySelectedBones: z.boolean().optional().describe("Restrict to selected pose bones (default false)."),
        visualKeying: z.boolean().optional().describe("Evaluate constraints (default true)."),
        clearConstraints: z.boolean().optional().describe("Delete constraints after baking (default false)."),
        clearParents: z.boolean().optional().describe("Delete parents after baking (default false)."),
        useCurrentAction: z.boolean().optional().describe("Bake into the existing action (default false → new action)."),
        bakeTypes: z
          .array(z.enum(["POSE", "OBJECT"]))
          .optional()
          .describe("What to bake (default ['POSE'] for armatures, ['OBJECT'] otherwise)."),
      },
      handler: passthroughPost("/anim/bake_action"),
    },
    {
      name: "fcurve_list",
      description:
        "List every fcurve on an action with metadata: data_path, array_index, keyframe count, interpolation types, frame and value range, modifiers. Layered-API aware. Set includeKeyframes=true to also emit per-key frame/value/interpolation/easing.",
      inputSchema: {
        actionName: z.string().describe("Action to inspect."),
        dataPathFilter: z.string().optional().describe("Substring filter on data_path."),
        includeKeyframes: z.boolean().optional().describe("Emit full keyframe arrays (default false)."),
      },
      handler: passthroughPost("/fcurve/list"),
    },
    {
      name: "fcurve_evaluate",
      description:
        "Evaluate one fcurve at one or more frames. Use to validate bakes (compare expected vs actual values) or to drive procedural keyframing.",
      inputSchema: {
        actionName: z.string().describe("Action containing the fcurve."),
        dataPath: z.string().describe("fcurve data_path (e.g. 'pose.bones[\"head\"].rotation_quaternion')."),
        arrayIndex: z.number().int().optional().describe("Array index (default 0)."),
        frames: z.array(z.number()).min(1).describe("Frames to sample."),
      },
      handler: passthroughPost("/fcurve/evaluate"),
    },
    {
      name: "keyframe_set_interpolation",
      description:
        "Set interpolation / easing / handle types on existing fcurve keyframes. Filter by data_path substring + array_index + frame range. Interpolation: BEZIER LINEAR CONSTANT SINE QUAD CUBIC QUART QUINT EXPO CIRC BACK BOUNCE ELASTIC. Easing: AUTO EASE_IN EASE_OUT EASE_IN_OUT. Handles: FREE ALIGNED VECTOR AUTO AUTO_CLAMPED.",
      inputSchema: {
        actionName: z.string().describe("Action."),
        dataPathFilter: z.string().optional().describe("Substring match on fcurve.data_path."),
        arrayIndex: z.number().int().optional().describe("Restrict to a single array index."),
        frameStart: z.number().optional().describe("Only keys at frame >= this."),
        frameEnd: z.number().optional().describe("Only keys at frame <= this."),
        interpolation: z
          .enum([
            "CONSTANT", "LINEAR", "BEZIER", "SINE", "QUAD", "CUBIC", "QUART",
            "QUINT", "EXPO", "CIRC", "BACK", "BOUNCE", "ELASTIC",
          ])
          .optional(),
        easing: z.enum(["AUTO", "EASE_IN", "EASE_OUT", "EASE_IN_OUT"]).optional(),
        handleLeft: z.enum(["FREE", "ALIGNED", "VECTOR", "AUTO", "AUTO_CLAMPED"]).optional(),
        handleRight: z.enum(["FREE", "ALIGNED", "VECTOR", "AUTO", "AUTO_CLAMPED"]).optional(),
      },
      handler: passthroughPost("/keyframe/set_interpolation"),
    },
    {
      name: "fcurve_add_modifier",
      description:
        "Add an fcurve modifier to one or more channels. CYCLES makes a clip loop without re-keying (set params.mode_before/mode_after='REPEAT'). NOISE adds procedural jitter. GENERATOR/FNGENERATOR drive math expressions. STEPPED quantizes the curve.",
      inputSchema: {
        actionName: z.string().describe("Action."),
        type: z
          .enum(["GENERATOR", "FNGENERATOR", "ENVELOPE", "CYCLES", "NOISE", "LIMITS", "STEPPED"])
          .describe("Modifier type."),
        dataPathFilter: z.string().optional().describe("Substring match (default = all fcurves)."),
        arrayIndex: z.number().int().optional(),
        params: z.record(z.unknown()).optional().describe("setattr on the modifier (e.g. {mode_before:'REPEAT', strength:0.5})."),
      },
      handler: passthroughPost("/fcurve/add_modifier"),
    },
    {
      name: "action_duplicate",
      description:
        "Deep-copy an action with a new name. Uses bpy's built-in .copy() so both legacy and layered fcurves are preserved verbatim. Fails if newName already exists.",
      inputSchema: {
        actionName: z.string().describe("Source action."),
        newName: z.string().describe("Name for the new action (must be unique)."),
      },
      handler: passthroughPost("/action/duplicate"),
    },
  ]);
}
