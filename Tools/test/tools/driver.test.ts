import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("driver add/remove (B6)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "Source" });
    await blenderPost("/object/create", { type: "CUBE", name: "Driven" });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("adds a driver on location.z driven by Source.location.x", async () => {
    const res = await blenderPost<{ variableCount: number }>("/driver/add", {
      objectName: "Driven",
      dataPath: "location",
      arrayIndex: 2,
      expression: "var * 2",
      variables: [
        {
          name: "var",
          type: "TRANSFORMS",
          targetObjectName: "Source",
          transformType: "LOC_X",
          transformSpace: "WORLD_SPACE",
        },
      ],
    });
    expect(res.ok).toBe(true);
    expect(res.data?.variableCount).toBe(1);
  });

  it("removes a driver", async () => {
    const res = await blenderPost("/driver/remove", {
      objectName: "Driven",
      dataPath: "location",
      arrayIndex: 2,
    });
    expect(res.ok).toBe(true);
  });

  it("rejects removing a missing driver with DRIVER_NOT_FOUND", async () => {
    const res = await blenderPost("/driver/remove", {
      objectName: "Driven",
      dataPath: "location",
      arrayIndex: 2,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("DRIVER_NOT_FOUND");
  });

  it("rejects driver_add with no dataPath", async () => {
    const res = await blenderPost("/driver/add", { objectName: "Driven" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
