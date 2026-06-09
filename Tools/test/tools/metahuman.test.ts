import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("MetaHuman ARKit-52 (B7)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "PLANE", name: "Head", size: 1 });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("returns all 52 ARKit blendshape names", async () => {
    const res = await blenderPost<{ blendshapes: string[]; count: number }>(
      "/metahuman/arkit52_list",
      {},
    );
    expect(res.ok).toBe(true);
    expect(res.data?.count).toBe(52);
    expect(res.data?.blendshapes).toContain("eyeBlinkLeft");
    expect(res.data?.blendshapes).toContain("jawOpen");
    expect(res.data?.blendshapes).toContain("tongueOut");
  });

  it("creates all 52 shape keys on a fresh mesh", async () => {
    const res = await blenderPost<{ createdCount: number; existingCount: number }>(
      "/metahuman/ensure_arkit52_shape_keys",
      { objectName: "Head" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.createdCount).toBe(52);
    expect(res.data?.existingCount).toBe(0);
  });

  it("is idempotent — second call creates 0 new keys", async () => {
    const res = await blenderPost<{ createdCount: number; existingCount: number }>(
      "/metahuman/ensure_arkit52_shape_keys",
      { objectName: "Head" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.createdCount).toBe(0);
    expect(res.data?.existingCount).toBe(52);
  });

  it("sets a shape key value", async () => {
    const res = await blenderPost<{ value: number }>("/shape_key/set_value", {
      objectName: "Head",
      shapeKeyName: "jawOpen",
      value: 0.7,
    });
    expect(res.ok).toBe(true);
    expect(res.data?.value).toBeCloseTo(0.7, 3);
  });
});
