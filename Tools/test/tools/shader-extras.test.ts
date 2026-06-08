import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("shader_node extras: connect (alias), remove, list", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/material/create", { name: "ShadeMat" });
    await blenderPost("/shader_node/add", {
      materialName: "ShadeMat",
      type: "ShaderNodeTexNoise",
      name: "Noise",
      location: [-300, 0],
    });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("lists the nodes of the material", async () => {
    const res = await blenderPost<{
      nodes: { name: string; type: string }[];
      links: unknown[];
    }>("/shader_node/list", { materialName: "ShadeMat" });
    expect(res.ok).toBe(true);
    const names = res.data?.nodes.map((n) => n.name) ?? [];
    expect(names).toContain("Noise");
  });

  it("connects Noise.Fac → Principled BSDF.Base Color via shader_node/connect", async () => {
    const res = await blenderPost("/shader_node/connect", {
      materialName: "ShadeMat",
      fromNodeName: "Noise",
      fromSocketName: "Fac",
      toNodeName: "Principled BSDF",
      toSocketName: "Base Color",
    });
    expect(res.ok).toBe(true);
  });

  it("rejects unknown source node with NODE_NOT_FOUND", async () => {
    const res = await blenderPost("/shader_node/connect", {
      materialName: "ShadeMat",
      fromNodeName: "NoSuchNode",
      fromSocketName: "Fac",
      toNodeName: "Principled BSDF",
      toSocketName: "Base Color",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("NODE_NOT_FOUND");
  });

  it("removes a node", async () => {
    const res = await blenderPost("/shader_node/remove", {
      materialName: "ShadeMat",
      nodeName: "Noise",
    });
    expect(res.ok).toBe(true);
  });

  it("removing an absent node returns NODE_NOT_FOUND", async () => {
    const res = await blenderPost("/shader_node/remove", {
      materialName: "ShadeMat",
      nodeName: "GoneAlready",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("NODE_NOT_FOUND");
  });
});
