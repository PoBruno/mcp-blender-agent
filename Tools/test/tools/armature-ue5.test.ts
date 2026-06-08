import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("armature UE5 IK bones + convention validation", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("adds the 7 UE5 IK bones and is idempotent", async () => {
    await blenderPost("/armature/create", { name: "UE5Rig" });
    await blenderPost("/bone/add", {
      armatureObjectName: "UE5Rig",
      name: "root",
      head: [0, 0, 0],
      tail: [0, 0, 0.05],
    });

    const first = await blenderPost<{
      createdCount: number;
      existingCount: number;
      createdBones: string[];
    }>("/armature/add_ue5_ik_bones", { armatureObjectName: "UE5Rig" });
    expect(first.ok).toBe(true);
    expect(first.data?.createdCount).toBe(7);
    expect(first.data?.createdBones).toContain("ik_foot_root");
    expect(first.data?.createdBones).toContain("ik_hand_gun");

    // Idempotent — second call creates 0, sees all 7 existing
    const second = await blenderPost<{ createdCount: number; existingCount: number }>(
      "/armature/add_ue5_ik_bones",
      { armatureObjectName: "UE5Rig" },
    );
    expect(second.ok).toBe(true);
    expect(second.data?.createdCount).toBe(0);
    expect(second.data?.existingCount).toBe(7);
  });

  it("rejects when bones exist + skipExisting=false (INVALID_INPUT)", async () => {
    const res = await blenderPost("/armature/add_ue5_ik_bones", {
      armatureObjectName: "UE5Rig",
      skipExisting: false,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("validates a clean UE5 armature (passes)", async () => {
    // Rig already has lowercase names, no .L/.R, no required zero-roll bones declared
    const res = await blenderPost<{ passed: boolean; failureCount: number }>(
      "/armature/validate_ue5_convention",
      {
        armatureObjectName: "UE5Rig",
        requiredBones: ["ik_foot_root", "ik_hand_root", "root"],
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.passed).toBe(true);
    expect(res.data?.failureCount).toBe(0);
  });

  it("flags uppercase + .L/.R suffix + non-zero roll", async () => {
    await blenderPost("/armature/create", { name: "BadRig" });
    await blenderPost("/bone/add", {
      armatureObjectName: "BadRig",
      name: "Spine.L",
      head: [0, 0, 0],
      tail: [0, 0, 0.5],
      roll: 0.5,
    });

    const res = await blenderPost<{
      passed: boolean;
      failureCount: number;
      failures: { check: string; boneName: string; reason: string }[];
    }>("/armature/validate_ue5_convention", {
      armatureObjectName: "BadRig",
      zeroRollBones: ["Spine.L"],
      requiredBones: ["root"],
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("VALIDATION_FAILED");
    expect(res.data?.passed).toBe(false);
    const checks = (res.data?.failures ?? []).map((f) => f.check);
    expect(checks).toContain("lowercase");
    expect(checks).toContain("underscore_lr");
    expect(checks).toContain("zero_roll");
    expect(checks).toContain("required_bones");
  });

  it("rejects validation on missing armature with OBJECT_NOT_FOUND", async () => {
    const res = await blenderPost("/armature/validate_ue5_convention", {
      armatureObjectName: "NoSuchRig",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("OBJECT_NOT_FOUND");
  });
});
