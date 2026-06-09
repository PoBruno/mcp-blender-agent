import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("armature + bone (B7)", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("creates an armature, adds bones, sets parent, renames", async () => {
    const arm = await blenderPost<{ armatureObjectName: string }>("/armature/create", {
      name: "TestRig",
    });
    expect(arm.ok).toBe(true);
    expect(arm.refs?.armatureName).toBe("TestRig");

    const root = await blenderPost("/bone/add", {
      armatureObjectName: "TestRig",
      name: "Root",
      head: [0, 0, 0],
      tail: [0, 0, 0.2],
    });
    expect(root.ok).toBe(true);

    const child = await blenderPost("/bone/add", {
      armatureObjectName: "TestRig",
      name: "Spine",
      head: [0, 0, 0.2],
      tail: [0, 0, 1.0],
      parentName: "Root",
      useConnect: true,
    });
    expect(child.ok).toBe(true);

    const renamed = await blenderPost<{ boneName: string }>("/bone/rename", {
      armatureObjectName: "TestRig",
      oldName: "Spine",
      newName: "Spine01",
    });
    expect(renamed.ok).toBe(true);
    expect(renamed.refs?.boneName).toBe("Spine01");
  });

  it("rejects bone_add on missing armature with OBJECT_NOT_FOUND", async () => {
    const res = await blenderPost("/bone/add", {
      armatureObjectName: "NoSuchRig",
      name: "X",
      head: [0, 0, 0],
      tail: [0, 0, 1],
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("OBJECT_NOT_FOUND");
  });

  it("adds a pose constraint (COPY_LOCATION) to the Root bone", async () => {
    await blenderPost("/object/create", { type: "EMPTY", name: "Target" });
    const res = await blenderPost<{ constraintName: string }>("/bone/add_constraint", {
      armatureObjectName: "TestRig",
      boneName: "Root",
      type: "COPY_LOCATION",
      targetObjectName: "Target",
    });
    expect(res.ok).toBe(true);
    expect(res.refs?.constraintName).toBeTruthy();
  });

  it("sets pose-bone location and reads it back", async () => {
    const res = await blenderPost<{ location: number[] }>("/bone/set_pose_transform", {
      armatureObjectName: "TestRig",
      boneName: "Root",
      location: [0.5, 0, 0],
    });
    expect(res.ok).toBe(true);
    expect(res.data?.location?.[0]).toBeCloseTo(0.5, 3);
  });

  it("creates a bone collection and assigns the Root bone", async () => {
    const bc = await blenderPost("/bone_collection/create", {
      armatureObjectName: "TestRig",
      name: "Deform",
    });
    expect(bc.ok).toBe(true);

    const assign = await blenderPost("/bone_collection/assign_bone", {
      armatureObjectName: "TestRig",
      boneCollectionName: "Deform",
      boneName: "Root",
    });
    expect(assign.ok).toBe(true);
  });
});
