import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("scene + collection + object Sprint 1 smoke", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("creates a scene, collection, and a blockout cube end-to-end", async () => {
    const scene = await blenderPost<{ sceneName: string }>("/scene/create", {
      name: "TestScene",
      unitSystem: "METRIC",
      scaleLength: 0.01,
    });
    expect(scene.ok).toBe(true);
    expect(scene.refs?.sceneName).toBe("TestScene");

    await blenderPost("/scene/set_active", { sceneName: "TestScene" });

    const col = await blenderPost<{ collectionName: string }>("/collection/create", {
      name: "TestCollection",
      sceneName: "TestScene",
    });
    expect(col.ok).toBe(true);
    expect(col.refs?.collectionName).toBe("TestCollection");

    const obj = await blenderPost<{ objectName: string; dimensions: number[] }>(
      "/object/add_blockout",
      {
        name: "TestBlockOut",
        footprint: [4, 2, 3],
        collectionName: "TestCollection",
      },
    );
    expect(obj.ok).toBe(true);
    expect(obj.data?.dimensions?.[0]).toBeCloseTo(4, 3);
    expect(obj.data?.dimensions?.[2]).toBeCloseTo(3, 3);
  });

  it("creates a material and assigns to the blockout", async () => {
    const mat = await blenderPost<{ materialName: string }>(
      "/material/create_procedural_grid",
      { name: "Grid_BlockOut", squareSize: 0.5 },
    );
    expect(mat.ok).toBe(true);

    const assign = await blenderPost("/material/assign_slot", {
      objectName: "TestBlockOut",
      materialName: "Grid_BlockOut",
    });
    expect(assign.ok).toBe(true);
  });

  it("smart-projects UVs", async () => {
    const uv = await blenderPost("/uv/smart_project", {
      objectName: "TestBlockOut",
      angleLimit: 66,
      islandMargin: 0.02,
    });
    expect(uv.ok).toBe(true);
  });
});
