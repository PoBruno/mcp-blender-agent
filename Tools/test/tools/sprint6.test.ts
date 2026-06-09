import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let work = "";

describe("Sprint 6 — gap-fix tools", () => {
  beforeAll(async () => {
    await startBlender();
    work = mkdtempSync(join(tmpdir(), "blender-agent-s6-"));
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (work && existsSync(work)) rmSync(work, { recursive: true, force: true });
  });

  it("object_apply_transform bakes scale to 1", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "ApplyMe" });
    await blenderPost("/object/set_transform", { objectName: "ApplyMe", scale: [2, 1, 0.5] });
    const r = await blenderPost<{ scale: number[] }>("/object/apply_transform", { objectName: "ApplyMe", scale: true });
    expect(r.ok).toBe(true);
    expect(r.data!.scale.map((v) => Math.round(v))).toEqual([1, 1, 1]);
  });

  it("object_set_mode + object_rename", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "ModeMe" });
    const e = await blenderPost<{ mode: string }>("/object/set_mode", { objectName: "ModeMe", mode: "EDIT" });
    expect(e.ok && e.data!.mode).toBe("EDIT");
    await blenderPost("/object/set_mode", { objectName: "ModeMe", mode: "OBJECT" });
    const rn = await blenderPost<{ objectName: string }>("/object/rename", { objectName: "ModeMe", newName: "Renamed" });
    expect(rn.ok && rn.data!.objectName).toBe("Renamed");
  });

  it("render_set_view_transform → Standard", async () => {
    const r = await blenderPost<{ viewTransform: string }>("/render/set_view_transform", { viewTransform: "Standard" });
    expect(r.ok && r.data!.viewTransform).toBe("Standard");
  });

  it("material_set_principled applies base color + roughness in one call", async () => {
    await blenderPost("/material/create", { name: "M6" });
    const r = await blenderPost<{ applied: string[] }>("/material/set_principled", {
      materialName: "M6",
      baseColor: [0.8, 0.1, 0.1, 1],
      roughness: 0.2,
      metallic: 0.5,
    });
    expect(r.ok).toBe(true);
    expect(r.data!.applied).toEqual(expect.arrayContaining(["baseColor", "roughness", "metallic"]));
  });

  it("armature_create_biped builds 19 bones", async () => {
    const r = await blenderPost<{ boneCount: number; bones: string[] }>("/armature/create_biped", { name: "Biped", height: 1.8 });
    expect(r.ok).toBe(true);
    expect(r.data!.boneCount).toBe(19);
    expect(r.data!.bones).toEqual(expect.arrayContaining(["pelvis", "upperarm_L", "foot_R", "head"]));
  });

  it("pose_set sets + keyframes many bones at once", async () => {
    await blenderPost("/action/create", { name: "Pose6" });
    await blenderPost("/action/assign_to_object", { objectName: "Biped", actionName: "Pose6" });
    const r = await blenderPost<{ bonesSet: string[]; keyframed: boolean }>("/pose/set", {
      armatureObjectName: "Biped",
      frame: 1,
      pose: {
        upperarm_L: { rotationEuler: [-2.6, 0, 0] },
        upperarm_R: { rotationEuler: [-2.6, 0, 0] },
        thigh_L: { rotationEuler: [0.4, 0, 0] },
      },
    });
    expect(r.ok).toBe(true);
    expect(r.data!.keyframed).toBe(true);
    expect(r.data!.bonesSet).toHaveLength(3);
  });

  it("action_mirror copies + flips an action", async () => {
    const r = await blenderPost<{ actionName: string }>("/action/mirror", {
      sourceActionName: "Pose6",
      newActionName: "Pose6_Mirror",
    });
    expect(r.ok).toBe(true);
    const list = await blenderPost<{ actions: { name: string }[] }>("/action/list", {});
    expect(list.data!.actions.map((a) => a.name)).toContain("Pose6_Mirror");
  });

  it("vision_render_action writes frames + a strip", async () => {
    const r = await blenderPost<{ count: number; strip: string }>("/vision/render_action", {
      objectNames: ["Biped"],
      armatureObjectName: "Biped",
      actionName: "Pose6",
      frameStart: 1,
      frameEnd: 3,
      step: 1,
      resolution: 128,
      samples: 4,
      outputDir: join(work, "action"),
    });
    expect(r.ok).toBe(true);
    expect(r.data!.count).toBe(3);
    expect(existsSync(r.data!.strip)).toBe(true);
    expect(statSync(r.data!.strip).size).toBeGreaterThan(100);
  });

  it("vision_silhouette_compare returns IoU + heatmap", async () => {
    await blenderPost("/object/create", { type: "SPHERE", name: "SilSubj" });
    const ref = join(work, "ref.png");
    await blenderPost("/vision/snapshot", { objectNames: ["SilSubj"], angle: "front", forceRender: true, resolution: 128, samples: 4, outputPath: ref });
    const out = join(work, "heat.png");
    const r = await blenderPost<{ iou: number; heatmap: string }>("/vision/silhouette_compare", {
      objectNames: ["SilSubj"],
      referenceImage: ref,
      outputPath: out,
      angle: "front",
      resolution: 128,
    });
    expect(r.ok).toBe(true);
    expect(typeof r.data!.iou).toBe("number");
    expect(r.data!.iou).toBeGreaterThanOrEqual(0);
    expect(existsSync(out)).toBe(true);
  });

  it("batch runs multiple ops in one request", async () => {
    const r = await blenderPost<{ results: { ok: boolean }[]; count: number }>("/batch", {
      ops: [
        { path: "/object/create", body: { type: "CUBE", name: "B1" } },
        { path: "/object/create", body: { type: "SPHERE", name: "B2" } },
        { path: "/object/rename", body: { objectName: "B1", newName: "B1r" } },
      ],
    });
    expect(r.ok).toBe(true);
    expect(r.data!.count).toBe(3);
    expect(r.data!.results.every((x) => x.ok)).toBe(true);
  });

  it("batch stops at first error and reports failedAt", async () => {
    const r = await blenderPost<{ failedAt: number }>("/batch", {
      ops: [
        { path: "/object/create", body: { type: "CUBE", name: "OK1" } },
        { path: "/object/rename", body: { objectName: "DOES_NOT_EXIST", newName: "x" } },
        { path: "/object/create", body: { type: "CUBE", name: "NeverRuns" } },
      ],
    });
    expect(r.ok).toBe(false);
    expect(r.data!.failedAt).toBe(1);
  });

  it("generate_image_to_3d reports BACKEND_NOT_CONFIGURED", async () => {
    const ref = join(work, "ref.png");
    const r = await blenderPost("/generate/image_to_3d", { imagePath: ref });
    expect(r.ok).toBe(false);
    expect(r.errorCode).toBe("BACKEND_NOT_CONFIGURED");
  });

  it("keyframe_bone_pose default channel follows euler rotation_mode", async () => {
    await blenderPost("/bone/set_pose_transform", { armatureObjectName: "Biped", boneName: "head", rotationEuler: [0.3, 0, 0] });
    const k = await blenderPost<{ insertedChannels: string[] }>("/keyframe/bone_pose", { armatureObjectName: "Biped", boneName: "head", frame: 5 });
    expect(k.ok).toBe(true);
    expect(k.data!.insertedChannels).toContain("rotation_euler");
  });
});
