import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("uv extras: layer, unwrap, smart_project, pack, average, mark_seams, validate", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "UVCube", size: 1 });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("creates a UV layer", async () => {
    const res = await blenderPost<{ uvLayerName: string }>("/uv/layer_create", {
      objectName: "UVCube",
      name: "UVMap2",
    });
    expect(res.ok).toBe(true);
    expect(res.data?.uvLayerName).toBe("UVMap2");
  });

  it("unwraps with ANGLE_BASED", async () => {
    const res = await blenderPost("/uv/unwrap", {
      objectName: "UVCube",
      method: "ANGLE_BASED",
      margin: 0.001,
    });
    expect(res.ok).toBe(true);
  });

  it("runs unwrap_smart_project alias", async () => {
    const res = await blenderPost("/uv/unwrap_smart_project", {
      objectName: "UVCube",
      angleLimit: 60,
      islandMargin: 0.02,
    });
    expect(res.ok).toBe(true);
  });

  it("packs islands", async () => {
    const res = await blenderPost("/uv/pack_islands", {
      objectName: "UVCube",
      margin: 0.01,
    });
    expect(res.ok).toBe(true);
  });

  it("averages island scale", async () => {
    const res = await blenderPost("/uv/average_islands_scale", { objectName: "UVCube" });
    expect(res.ok).toBe(true);
  });

  it("marks seams", async () => {
    const res = await blenderPost("/uv/mark_seams", { objectName: "UVCube" });
    expect(res.ok).toBe(true);
  });

  it("minimizes stretch", async () => {
    const res = await blenderPost("/uv/minimize_stretch", {
      objectName: "UVCube",
      iterations: 4,
    });
    expect(res.ok).toBe(true);
  });

  it("validates UVs for baking", async () => {
    const res = await blenderPost<{ loopCount: number; outOfBoundsLoops: number }>(
      "/uv/validate_for_baking",
      { objectName: "UVCube" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.loopCount).toBeGreaterThan(0);
  });

  it("rejects non-mesh objects with INVALID_INPUT", async () => {
    await blenderPost("/object/create", { type: "EMPTY", name: "NotMeshUV" });
    const res = await blenderPost("/uv/layer_create", { objectName: "NotMeshUV" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
