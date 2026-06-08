import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("light set_property + asset mark/clear + compositor connect", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("sets light properties", async () => {
    const create = await blenderPost<{ lightObjectName: string }>("/light/create", {
      type: "POINT",
      name: "MyLight",
      energy: 500,
    });
    expect(create.ok).toBe(true);
    const res = await blenderPost<{ updated: string[] }>("/light/set_property", {
      objectName: create.data!.lightObjectName,
      properties: { energy: 1200.0 },
    });
    expect(res.ok).toBe(true);
    expect(res.data?.updated).toContain("energy");
  });

  it("rejects set_property on non-LIGHT with INVALID_INPUT", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "NotALight" });
    const res = await blenderPost("/light/set_property", {
      objectName: "NotALight",
      properties: { energy: 100 },
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("marks an object as an asset, then clears it", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "AssetCube" });
    const mark = await blenderPost<{ tags: string[] }>("/asset/mark", {
      objectName: "AssetCube",
      tags: ["modular", "prop"],
      description: "test asset",
    });
    expect(mark.ok).toBe(true);
    expect(mark.data?.tags).toEqual(expect.arrayContaining(["modular", "prop"]));

    const clear = await blenderPost("/asset/clear", { objectName: "AssetCube" });
    expect(clear.ok).toBe(true);
  });

  it("rejects clearing an asset on a non-asset object", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "NotAnAsset" });
    const res = await blenderPost("/asset/clear", { objectName: "NotAnAsset" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("connects two compositor nodes", async () => {
    await blenderPost("/compositor/enable", {});
    const add1 = await blenderPost<{ nodeName: string }>("/compositor/add_node", {
      type: "CompositorNodeRLayers",
      name: "RL",
    });
    expect(add1.ok).toBe(true);
    const add2 = await blenderPost<{ nodeName: string }>("/compositor/add_node", {
      type: "CompositorNodeBrightContrast",
      name: "BC",
    });
    expect(add2.ok).toBe(true);
    const link = await blenderPost("/compositor/connect", {
      fromNodeName: "RL",
      fromSocketName: "Image",
      toNodeName: "BC",
      toSocketName: "Image",
    });
    expect(link.ok).toBe(true);
  });
});
