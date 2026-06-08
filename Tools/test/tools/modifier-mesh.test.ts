import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("modifier + mesh edit (B2/B3)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "ModTarget", size: 2 });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("adds a Subsurf modifier with params", async () => {
    const res = await blenderPost<{ modifierName: string; type: string }>("/modifier/add", {
      objectName: "ModTarget",
      type: "SUBSURF",
      params: { levels: 2, render_levels: 3 },
    });
    expect(res.ok).toBe(true);
    expect(res.data?.type).toBe("SUBSURF");
    expect(res.refs?.modifierName).toBe(res.data?.modifierName);
  });

  it("lists modifiers on the target object", async () => {
    const res = await blenderPost<{ modifiers: { name: string; type: string }[] }>(
      "/modifier/list",
      { objectName: "ModTarget" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.modifiers?.length).toBeGreaterThanOrEqual(1);
  });

  it("rejects unknown modifier type with INVALID_INPUT", async () => {
    const res = await blenderPost("/modifier/add", {
      objectName: "ModTarget",
      type: "NOT_A_REAL_MODIFIER",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("subdivides a mesh in EDIT mode", async () => {
    const res = await blenderPost("/mesh/subdivide", {
      objectName: "ModTarget",
      numberCuts: 1,
    });
    expect(res.ok).toBe(true);
  });

  it("shade-smooths the mesh", async () => {
    const res = await blenderPost("/mesh/shade_smooth", { objectName: "ModTarget" });
    expect(res.ok).toBe(true);
  });

  it("recalculates normals", async () => {
    const res = await blenderPost("/mesh/recalc_normals", {
      objectName: "ModTarget",
      inside: false,
    });
    expect(res.ok).toBe(true);
  });
});
