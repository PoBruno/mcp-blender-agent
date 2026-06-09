import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("material extras: delete, slot_add, assign_to_object", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "MatBox" });
    await blenderPost("/material/create", { name: "MatA" });
    await blenderPost("/material/create", { name: "MatB" });
    await blenderPost("/material/create", { name: "ToDelete" });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("adds an empty material slot", async () => {
    const res = await blenderPost<{ slotIndex: number }>("/material/slot_add", {
      objectName: "MatBox",
    });
    expect(res.ok).toBe(true);
    expect(typeof res.data?.slotIndex).toBe("number");
  });

  it("assigns a material to a specific slot", async () => {
    const res = await blenderPost<{ slotIndex: number; materialName: string }>(
      "/material/assign_to_object",
      { objectName: "MatBox", materialName: "MatA", slotIndex: 0 },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.materialName).toBe("MatA");
  });

  it("assigns a different material to slot 1", async () => {
    const res = await blenderPost<{ slotIndex: number }>("/material/assign_to_object", {
      objectName: "MatBox",
      materialName: "MatB",
      slotIndex: 1,
    });
    expect(res.ok).toBe(true);
    expect(res.data?.slotIndex).toBe(1);
  });

  it("legacy alias material/assign_slot works", async () => {
    const res = await blenderPost("/material/assign_slot", {
      objectName: "MatBox",
      materialName: "MatA",
      slotIndex: 0,
    });
    expect(res.ok).toBe(true);
  });

  it("deletes a material datablock", async () => {
    const res = await blenderPost<{ deleted: string }>("/material/delete", {
      materialName: "ToDelete",
    });
    expect(res.ok).toBe(true);
    expect(res.data?.deleted).toBe("ToDelete");
  });

  it("rejects deleting an unknown material with MATERIAL_NOT_FOUND", async () => {
    const res = await blenderPost("/material/delete", { materialName: "NopeNope" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("MATERIAL_NOT_FOUND");
  });
});
