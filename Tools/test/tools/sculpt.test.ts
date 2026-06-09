import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("sculpt: dyntopo + voxel remesh (B3)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "DynBox", size: 1 });
    await blenderPost("/object/create", { type: "CUBE", name: "RemeshBox", size: 1 });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("enables dyntopo", async () => {
    const res = await blenderPost<{ detailSize: number }>("/sculpt/enable_dyntopo", {
      objectName: "DynBox",
      detailSize: 10.0,
    });
    expect(res.ok).toBe(true);
    expect(res.data?.detailSize).toBe(10.0);
  });

  it("voxel remeshes", async () => {
    const res = await blenderPost<{ voxelSize: number }>("/sculpt/voxel_remesh", {
      objectName: "RemeshBox",
      voxelSize: 0.1,
    });
    expect(res.ok).toBe(true);
    expect(res.data?.voxelSize).toBe(0.1);
  });
});
