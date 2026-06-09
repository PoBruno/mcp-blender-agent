import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("object transform / duplicate / origin / instance / parent_to_armature", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("sets transform on an existing object", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "Xform" });
    const res = await blenderPost<{ location: number[]; scale: number[] }>(
      "/object/set_transform",
      {
        objectName: "Xform",
        location: [1, 2, 3],
        rotation: [0, 0, 0.5],
        scale: [2, 2, 2],
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.location).toEqual([1, 2, 3]);
    expect(res.data?.scale).toEqual([2, 2, 2]);
  });

  it("duplicates an object with linked data", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "Original" });
    const res = await blenderPost<{ objectName: string }>("/object/duplicate_linked", {
      objectName: "Original",
      newName: "OriginalCopy",
    });
    expect(res.ok).toBe(true);
    expect(res.data?.objectName).toBe("OriginalCopy");
  });

  it("moves origin to a bounding-box corner", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "OriginBox", size: 2 });
    const res = await blenderPost<{ corner: string }>(
      "/mesh/set_origin_to_snap_corner",
      { objectName: "OriginBox", corner: "MIN_X_MIN_Y_MIN_Z" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.corner).toBe("MIN_X_MIN_Y_MIN_Z");
  });

  it("rejects malformed corner string", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "BadCorner" });
    const res = await blenderPost("/mesh/set_origin_to_snap_corner", {
      objectName: "BadCorner",
      corner: "GARBAGE",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("creates a collection instance empty", async () => {
    await blenderPost("/collection/create", { name: "KitGroup" });
    await blenderPost("/object/create", {
      type: "CUBE",
      name: "InCollection",
      collectionName: "KitGroup",
    });
    const res = await blenderPost<{ instanceOf: string }>("/collection/instance_create", {
      collectionName: "KitGroup",
      name: "KitInstance",
      location: [5, 0, 0],
    });
    expect(res.ok).toBe(true);
    expect(res.data?.instanceOf).toBe("KitGroup");
  });

  it("parents a mesh to an armature with an Armature modifier", async () => {
    await blenderPost("/armature/create", { name: "RigForMesh" });
    await blenderPost("/bone/add", {
      armatureObjectName: "RigForMesh",
      name: "Root",
      head: [0, 0, 0],
      tail: [0, 0, 1],
    });
    await blenderPost("/object/create", { type: "CUBE", name: "Skinned" });
    const res = await blenderPost<{ modifierName: string }>(
      "/mesh/parent_to_armature",
      { meshObjectName: "Skinned", armatureObjectName: "RigForMesh" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.modifierName).toBe("Armature");

    // Idempotent: second call reuses modifier
    const again = await blenderPost<{ modifierName: string }>(
      "/mesh/parent_to_armature",
      { meshObjectName: "Skinned", armatureObjectName: "RigForMesh" },
    );
    expect(again.ok).toBe(true);
    expect(again.data?.modifierName).toBe("Armature");
  });
});
