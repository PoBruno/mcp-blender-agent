import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 8 — animation_bake_export_gltf
 *
 * Chain:
 *   cube + armature -> assign action -> keyframes -> NLA push
 *   -> export GLTF -> file exists and is non-empty
 */
describe("Recipe 8 — animation_bake_export_gltf", () => {
  let workDir = "";

  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-recipe8-"));
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("authors keyframes on an object, pushes to NLA, exports GLTF", async () => {
    const obj = await blenderPost("/object/create", { type: "CUBE", name: "AnimBox" });
    expect(obj.ok).toBe(true);

    const action = await blenderPost("/action/create", { name: "Bounce" });
    expect(action.ok).toBe(true);

    const assign = await blenderPost("/action/assign_to_object", {
      objectName: "AnimBox",
      actionName: "Bounce",
    });
    expect(assign.ok).toBe(true);

    for (const frame of [1, 15, 30]) {
      const k = await blenderPost("/keyframe/add", {
        objectName: "AnimBox",
        dataPath: "location",
        frame,
      });
      expect(k.ok, `keyframe ${frame}`).toBe(true);
    }

    const range = await blenderPost("/scene/set_frame_range", {
      frameStart: 1,
      frameEnd: 30,
    });
    expect(range.ok).toBe(true);

    const push = await blenderPost<{ trackName: string }>(
      "/nla/push_action_to_strip",
      { objectName: "AnimBox", trackName: "BounceTrack" },
    );
    expect(push.ok).toBe(true);
    expect(push.refs?.actionName).toBe("Bounce");

    const filepath = join(workDir, "AnimBox.glb");
    const exp = await blenderPost<{ filepath: string }>("/export/gltf", {
      filepath,
      objectNames: ["AnimBox"],
      exportFormat: "GLB",
      exportAnimations: true,
    });
    expect(exp.ok).toBe(true);
    expect(existsSync(filepath)).toBe(true);
    expect(statSync(filepath).size).toBeGreaterThan(128);
  }, 180_000);
});
