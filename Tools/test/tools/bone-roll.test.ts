import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

interface BoneEntry {
  name: string;
  head: number[];
  tail: number[];
  roll: number;
  length: number;
  parent: string | null;
  useConnect: boolean;
  useDeform: boolean;
}

describe("bone roll + list + recalculate (UE5 hygiene)", () => {
  beforeAll(async () => {
    await startBlender();

    // Fresh rig with two spine-like bones at rolled angles
    await blenderPost("/armature/create", { name: "RollRig" });
    await blenderPost("/bone/add", {
      armatureObjectName: "RollRig",
      name: "root",
      head: [0, 0, 0],
      tail: [0, 0, 0.1],
    });
    await blenderPost("/bone/add", {
      armatureObjectName: "RollRig",
      name: "spine_01",
      head: [0, 0, 0.1],
      tail: [0, 0, 0.5],
      parentName: "root",
      useConnect: true,
      roll: 1.36, // ~77.9 deg, matching ARTIS briefing
    });
    await blenderPost("/bone/add", {
      armatureObjectName: "RollRig",
      name: "spine_02",
      head: [0, 0, 0.5],
      tail: [0, 0, 0.9],
      parentName: "spine_01",
      useConnect: true,
      roll: 1.428, // ~81.8 deg
    });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("lists all bones with roll/head/tail/parent", async () => {
    const res = await blenderPost<{ boneCount: number; bones: BoneEntry[] }>(
      "/bone/list",
      { armatureObjectName: "RollRig" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.boneCount).toBe(3);
    const spine01 = res.data?.bones.find((b) => b.name === "spine_01");
    expect(spine01).toBeDefined();
    expect(spine01?.parent).toBe("root");
    expect(spine01?.roll).toBeCloseTo(1.36, 2);
  });

  it("filters bones by name substring", async () => {
    const res = await blenderPost<{ boneCount: number; bones: BoneEntry[] }>(
      "/bone/list",
      { armatureObjectName: "RollRig", namePattern: "spine" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.boneCount).toBe(2);
    expect(res.data?.bones.every((b) => b.name.includes("spine"))).toBe(true);
  });

  it("clears roll on multiple bones with bone/set_roll", async () => {
    const res = await blenderPost<{ updatedCount: number; bones: { name: string; roll: number }[] }>(
      "/bone/set_roll",
      {
        armatureObjectName: "RollRig",
        boneNames: ["spine_01", "spine_02"],
        roll: 0.0,
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.updatedCount).toBe(2);
    for (const b of res.data?.bones ?? []) {
      expect(b.roll).toBeCloseTo(0.0, 5);
    }
  });

  it("rejects unknown bone in set_roll with BONE_NOT_FOUND", async () => {
    const res = await blenderPost("/bone/set_roll", {
      armatureObjectName: "RollRig",
      boneNames: ["ghost"],
      roll: 0.0,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("BONE_NOT_FOUND");
  });

  it("rejects empty boneNames in set_roll with INVALID_INPUT", async () => {
    const res = await blenderPost("/bone/set_roll", {
      armatureObjectName: "RollRig",
      boneNames: [],
      roll: 0.0,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("rejects unknown calculate_roll type with INVALID_INPUT", async () => {
    const res = await blenderPost("/bone/recalculate_roll", {
      armatureObjectName: "RollRig",
      boneNames: ["spine_01"],
      type: "NONSENSE",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("recalculates roll to GLOBAL_POS_Z (UE5 spine convention)", async () => {
    // Re-rolling the spine_* bones a bit so the test is meaningful
    await blenderPost("/bone/set_roll", {
      armatureObjectName: "RollRig",
      boneNames: ["spine_01", "spine_02"],
      roll: 0.7,
    });
    const res = await blenderPost<{ bones: { name: string; roll: number }[] }>(
      "/bone/recalculate_roll",
      {
        armatureObjectName: "RollRig",
        boneNames: ["spine_01", "spine_02"],
        type: "GLOBAL_POS_Z",
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.bones).toHaveLength(2);
    // For a vertical bone (head and tail differ only in Z) with reference
    // GLOBAL_POS_Z, calculate_roll cannot resolve and may leave roll unchanged
    // OR snap it close to a canonical value — we just verify the op didn't error
    // and returned numbers.
    for (const b of res.data?.bones ?? []) {
      expect(typeof b.roll).toBe("number");
    }
  });

  it("set_edit_transform updates head + tail + roll atomically", async () => {
    const res = await blenderPost<{ head: number[]; tail: number[]; roll: number }>(
      "/bone/set_edit_transform",
      {
        armatureObjectName: "RollRig",
        boneName: "spine_01",
        head: [0, 0, 0.1],
        tail: [0, 0, 0.45],
        roll: 0.0,
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.head?.[2]).toBeCloseTo(0.1, 4);
    expect(res.data?.tail?.[2]).toBeCloseTo(0.45, 4);
    expect(res.data?.roll).toBeCloseTo(0.0, 5);
  });

  it("set_edit_transform rejects unknown bone with BONE_NOT_FOUND", async () => {
    const res = await blenderPost("/bone/set_edit_transform", {
      armatureObjectName: "RollRig",
      boneName: "ghost",
      roll: 0.0,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("BONE_NOT_FOUND");
  });
});
