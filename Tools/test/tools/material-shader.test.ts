import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("material + shader node graph (B5)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/material/create", { name: "TestMat", useNodes: true });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("adds a TexNoise node to the material tree", async () => {
    const res = await blenderPost<{ nodeName: string; type: string }>(
      "/shader_node/add",
      {
        materialName: "TestMat",
        type: "ShaderNodeTexNoise",
        name: "Noise",
        location: [-300, 0],
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.type).toBe("ShaderNodeTexNoise");
    expect(res.refs?.nodeName).toBe("Noise");
  });

  it("sets the Scale input value", async () => {
    const res = await blenderPost("/shader_node/set_input_value", {
      materialName: "TestMat",
      nodeName: "Noise",
      socketName: "Scale",
      value: 12.0,
    });
    expect(res.ok).toBe(true);
  });

  it("connects Noise.Color to Principled.Base Color", async () => {
    const res = await blenderPost("/shader_node/connect_pins", {
      materialName: "TestMat",
      fromNodeName: "Noise",
      fromSocketName: "Color",
      toNodeName: "Principled BSDF",
      toSocketName: "Base Color",
    });
    expect(res.ok).toBe(true);
  });

  it("creates a node group and instances it in the material", async () => {
    const ng = await blenderPost("/node_group/create", {
      name: "ReusableGroup",
      treeType: "ShaderNodeTree",
    });
    expect(ng.ok).toBe(true);

    const inst = await blenderPost<{ nodeName: string }>(
      "/node_group/instance_in_material",
      {
        materialName: "TestMat",
        nodeGroupName: "ReusableGroup",
        location: [100, 200],
      },
    );
    expect(inst.ok).toBe(true);
    expect(inst.refs?.nodeName).toBeTruthy();
  });

  it("creates a procedural grid material (Recipe 4 building block)", async () => {
    const res = await blenderPost<{ materialName: string }>(
      "/material/create_procedural_grid",
      { name: "Grid_Test", squareSize: 0.25 },
    );
    expect(res.ok).toBe(true);
    expect(res.refs?.materialName).toBe("Grid_Test");
  });
});
