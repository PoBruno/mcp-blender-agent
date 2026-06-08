import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderGet, blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("collection + view_layer + scene list (B1, B9.D)", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("creates a collection, moves an object into it, then lists and deletes it", async () => {
    const made = await blenderPost<{ collectionName: string; created: boolean }>(
      "/collection/create",
      { name: "Movables" },
    );
    expect(made.ok).toBe(true);
    expect(made.data?.created).toBe(true);

    const obj = await blenderPost<{ objectName: string }>("/object/create", {
      type: "CUBE",
      name: "MoveMe",
    });
    expect(obj.ok).toBe(true);

    const move = await blenderPost<{ movedObjects: string[] }>(
      "/collection/move_objects",
      { collectionName: "Movables", objectNames: ["MoveMe"] },
    );
    expect(move.ok).toBe(true);
    expect(move.data?.movedObjects).toContain("MoveMe");

    const list = await blenderGet<{
      collections: { name: string; objectCount: number }[];
    }>("/collection/list");
    expect(list.ok).toBe(true);
    const movables = list.data?.collections.find((c) => c.name === "Movables");
    expect(movables?.objectCount).toBeGreaterThanOrEqual(1);

    // Idempotent re-create returns created: false
    const again = await blenderPost<{ created: boolean }>("/collection/create", {
      name: "Movables",
    });
    expect(again.data?.created).toBe(false);

    const del = await blenderPost("/collection/delete", { collectionName: "Movables" });
    expect(del.ok).toBe(true);
  });

  it("creates a view layer, an export view layer, and lists them", async () => {
    await blenderPost("/collection/create", { name: "Exportable" });
    const vl = await blenderPost<{ viewLayerName: string }>("/view_layer/create", {
      name: "Renders",
    });
    expect(vl.ok).toBe(true);
    expect(vl.data?.viewLayerName).toBe("Renders");

    const xvl = await blenderPost<{ enabledCollections: string[] }>(
      "/view_layer/create_for_export",
      { name: "ExportOnly", collectionNames: ["Exportable"] },
    );
    expect(xvl.ok).toBe(true);
    expect(xvl.data?.enabledCollections).toEqual(["Exportable"]);

    const list = await blenderGet<{ viewLayers: string[] }>("/view_layer/list");
    expect(list.ok).toBe(true);
    expect(list.data?.viewLayers).toContain("Renders");
    expect(list.data?.viewLayers).toContain("ExportOnly");
  });

  it("lists scenes", async () => {
    const res = await blenderGet<{ scenes: { name: string }[] }>("/scene/list");
    expect(res.ok).toBe(true);
  });

  it("rejects an unknown collection on delete with COLLECTION_NOT_FOUND", async () => {
    const res = await blenderPost("/collection/delete", {
      collectionName: "DoesNotExist_xyz",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("COLLECTION_NOT_FOUND");
  });
});
