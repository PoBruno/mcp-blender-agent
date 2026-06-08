import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("geometry nodes + compositor (B6/B8)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "PLANE", name: "Ground", size: 4 });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("creates a Geometry Node group with Group Input/Output pre-wired", async () => {
    const res = await blenderPost<{ nodeGroupName: string; created: boolean }>(
      "/geo_node/group_create",
      { name: "ScatterTree" },
    );
    expect(res.ok).toBe(true);
    expect(res.refs?.nodeGroupName).toBe("ScatterTree");
  });

  it("adds a DistributePointsOnFaces node and connects it", async () => {
    const add = await blenderPost("/geo_node/add_node", {
      nodeGroupName: "ScatterTree",
      type: "GeometryNodeDistributePointsOnFaces",
      name: "Distribute",
    });
    expect(add.ok).toBe(true);

    const connect = await blenderPost("/geo_node/connect", {
      nodeGroupName: "ScatterTree",
      fromNodeName: "Group Input",
      fromSocketName: "Geometry",
      toNodeName: "Distribute",
      toSocketName: "Mesh",
    });
    expect(connect.ok).toBe(true);
  });

  it("applies the node group to the Ground object", async () => {
    const res = await blenderPost<{ modifierName: string }>(
      "/geo_node/apply_to_object",
      { objectName: "Ground", nodeGroupName: "ScatterTree" },
    );
    expect(res.ok).toBe(true);
    expect(res.refs?.modifierName).toBeTruthy();
  });

  it("enables compositor and adds an RLayers node", async () => {
    const enable = await blenderPost("/compositor/enable", {});
    expect(enable.ok).toBe(true);

    const add = await blenderPost("/compositor/add_node", {
      type: "CompositorNodeRLayers",
      name: "RL",
    });
    expect(add.ok).toBe(true);
  });
});
