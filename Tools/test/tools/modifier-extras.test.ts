import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("modifier set/apply/remove/reorder (B2)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "ModBox", size: 2 });
    await blenderPost("/modifier/add", {
      objectName: "ModBox",
      type: "SUBSURF",
      name: "Sub",
    });
    await blenderPost("/modifier/add", {
      objectName: "ModBox",
      type: "BEVEL",
      name: "Bev",
    });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("sets a modifier property", async () => {
    const res = await blenderPost<{ updated: string[] }>("/modifier/set_property", {
      objectName: "ModBox",
      modifierName: "Sub",
      properties: { levels: 2, render_levels: 3 },
    });
    expect(res.ok).toBe(true);
    expect(res.data?.updated).toEqual(expect.arrayContaining(["levels", "render_levels"]));
  });

  it("rejects unknown property with INVALID_INPUT", async () => {
    const res = await blenderPost("/modifier/set_property", {
      objectName: "ModBox",
      modifierName: "Sub",
      properties: { not_a_real_prop_xyz: 5 },
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("rejects missing modifier with MODIFIER_NOT_FOUND", async () => {
    const res = await blenderPost("/modifier/set_property", {
      objectName: "ModBox",
      modifierName: "NoSuchMod",
      properties: { levels: 1 },
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("MODIFIER_NOT_FOUND");
  });

  it("reorders modifiers", async () => {
    const res = await blenderPost("/modifier/reorder", {
      objectName: "ModBox",
      modifierName: "Bev",
      direction: "UP",
    });
    expect(res.ok).toBe(true);
  });

  it("applies a modifier", async () => {
    const res = await blenderPost("/modifier/apply", {
      objectName: "ModBox",
      modifierName: "Sub",
    });
    expect(res.ok).toBe(true);

    const after = await blenderPost<{ modifiers: { name: string }[] }>("/modifier/list", {
      objectName: "ModBox",
    });
    expect(after.data?.modifiers.find((m) => m.name === "Sub")).toBeUndefined();
  });

  it("removes a modifier", async () => {
    const res = await blenderPost("/modifier/remove", {
      objectName: "ModBox",
      modifierName: "Bev",
    });
    expect(res.ok).toBe(true);
  });
});
