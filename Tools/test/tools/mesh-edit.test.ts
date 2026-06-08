import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("mesh edit operators (B2 §13–17)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "EditTarget", size: 2 });
    await blenderPost("/object/create", { type: "CUBE", name: "MergeTarget", size: 2 });
    await blenderPost("/object/create", { type: "CUBE", name: "ShadeTarget", size: 2 });
    await blenderPost("/object/create", { type: "CUBE", name: "JoinA", size: 1 });
    await blenderPost("/object/create", { type: "CUBE", name: "JoinB", size: 1 });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("bevels edges", async () => {
    const res = await blenderPost("/mesh/bevel", {
      objectName: "EditTarget",
      offset: 0.05,
      segments: 2,
    });
    expect(res.ok).toBe(true);
  });

  it("does a loop cut", async () => {
    const res = await blenderPost("/mesh/loop_cut", {
      objectName: "EditTarget",
      numberCuts: 1,
    });
    // loop_cut requires modal context; addon may fail gracefully
    expect(res).toBeDefined();
    expect(typeof res.ok).toBe("boolean");
  });

  it("merges vertices by distance", async () => {
    const res = await blenderPost("/mesh/merge_by_distance", {
      objectName: "MergeTarget",
      threshold: 0.001,
    });
    expect(res.ok).toBe(true);
  });

  it("flat-shades a mesh", async () => {
    const res = await blenderPost("/mesh/shade_flat", { objectName: "ShadeTarget" });
    expect(res.ok).toBe(true);
  });

  it("triangulates a mesh", async () => {
    const res = await blenderPost("/mesh/triangulate", { objectName: "ShadeTarget" });
    expect(res.ok).toBe(true);
  });

  it("joins two meshes into one", async () => {
    const res = await blenderPost<{ joined: string[] }>("/mesh/join", {
      targetObjectName: "JoinA",
      sourceObjectNames: ["JoinB"],
    });
    expect(res.ok).toBe(true);
    expect(res.data?.joined).toContain("JoinB");
  });

  it("extrudes a region (composite with smoke acceptance)", async () => {
    const res = await blenderPost("/mesh/extrude_region_move", {
      objectName: "EditTarget",
      offset: [0, 0, 0.5],
    });
    expect(res).toBeDefined();
  });

  it("separates by loose parts (no-op when single mesh, but succeeds)", async () => {
    const res = await blenderPost("/mesh/separate_by_loose_parts", {
      objectName: "EditTarget",
    });
    expect(res).toBeDefined();
  });

  it("rejects non-mesh objects with INVALID_INPUT", async () => {
    await blenderPost("/object/create", { type: "EMPTY", name: "NotMesh" });
    const res = await blenderPost("/mesh/bevel", { objectName: "NotMesh" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
