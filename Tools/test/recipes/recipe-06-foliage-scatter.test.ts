import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 6 — procedural_foliage_scatter_export
 *
 * Pragmatic version built from v1.0 primitives (no composite
 * "geo_node_instance_on_points_setup" helper yet).
 *
 * Chain:
 *   1. Terrain plane (subdivided)
 *   2. Tree proxy object (small cone) — instance source
 *   3. GeometryNodeTree wired:
 *        GroupInput.Geometry
 *          -> DistributePointsOnFaces.Mesh
 *        DistributePointsOnFaces.Points
 *          -> InstanceOnPoints.Points
 *        ObjectInfo (object=Tree_Proxy).Geometry
 *          -> InstanceOnPoints.Instance
 *        InstanceOnPoints.Instances
 *          -> RealizeInstances.Geometry
 *        RealizeInstances.Geometry
 *          -> GroupOutput.Geometry
 *   4. Apply the tree to Terrain via a Geometry Nodes modifier
 *   5. Modifier apply -> Terrain mesh now contains scattered tree geometry
 *   6. Batch FBX export the source collection (Path B from the recipe brief)
 *
 * This proves the geo-node primitive chain composes correctly without any
 * higher-level scatter helper.
 */
describe("Recipe 6 — procedural_foliage_scatter_export", () => {
  let workDir = "";

  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-recipe6-"));
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("scatters a tree proxy on a plane via geometry nodes and exports", async () => {
    // 1. Terrain
    const terrain = await blenderPost<{ objectName: string }>("/object/create", {
      type: "PLANE",
      name: "Terrain",
      location: [0, 0, 0],
    });
    expect(terrain.ok).toBe(true);

    // Up the resolution a touch so DistributePointsOnFaces has area to work with.
    const sub = await blenderPost("/modifier/add", {
      objectName: "Terrain",
      type: "SUBSURF",
      name: "TerrainSub",
      properties: { levels: 2, render_levels: 2 },
    });
    expect(sub.ok).toBe(true);

    const applySub = await blenderPost("/modifier/apply", {
      objectName: "Terrain",
      modifierName: "TerrainSub",
    });
    expect(applySub.ok).toBe(true);

    // 2. Tree proxy collection + cone
    const treesColl = await blenderPost("/collection/create", { name: "Trees_Source" });
    expect(treesColl.ok).toBe(true);

    const tree = await blenderPost<{ objectName: string }>("/object/create", {
      type: "CONE",
      name: "Tree_Proxy",
      collectionName: "Trees_Source",
      location: [10, 10, 0], // off to the side so it doesn't shadow the scatter
    });
    expect(tree.ok).toBe(true);

    // 3. Build the geometry-node graph
    const ng = await blenderPost<{ nodeGroupName: string }>("/geo_node/group_create", {
      name: "Forest_Scatter",
    });
    expect(ng.ok).toBe(true);
    const ngName = ng.data!.nodeGroupName;

    const dpop = await blenderPost("/geo_node/add_node", {
      nodeGroupName: ngName,
      type: "GeometryNodeDistributePointsOnFaces",
      name: "Distribute",
    });
    expect(dpop.ok).toBe(true);

    const setDensity = await blenderPost("/geo_node/set_node_input", {
      nodeGroupName: ngName,
      nodeName: "Distribute",
      inputName: "Density",
      value: 2.5,
    });
    expect(setDensity.ok).toBe(true);

    const iop = await blenderPost("/geo_node/add_node", {
      nodeGroupName: ngName,
      type: "GeometryNodeInstanceOnPoints",
      name: "Instance",
    });
    expect(iop.ok).toBe(true);

    const objInfo = await blenderPost("/geo_node/add_node", {
      nodeGroupName: ngName,
      type: "GeometryNodeObjectInfo",
      name: "TreeRef",
    });
    expect(objInfo.ok).toBe(true);

    const setObj = await blenderPost("/geo_node/set_node_input", {
      nodeGroupName: ngName,
      nodeName: "TreeRef",
      inputName: "Object",
      valueObjectName: "Tree_Proxy",
    });
    expect(setObj.ok, JSON.stringify(setObj)).toBe(true);

    const realize = await blenderPost("/geo_node/add_node", {
      nodeGroupName: ngName,
      type: "GeometryNodeRealizeInstances",
      name: "Realize",
    });
    expect(realize.ok).toBe(true);

    // Wire: GroupInput.Geometry -> Distribute.Mesh
    const l1 = await blenderPost("/geo_node/connect", {
      nodeGroupName: ngName,
      fromNodeName: "Group Input",
      fromSocketName: "Geometry",
      toNodeName: "Distribute",
      toSocketName: "Mesh",
    });
    expect(l1.ok, JSON.stringify(l1)).toBe(true);

    // Distribute.Points -> Instance.Points
    const l2 = await blenderPost("/geo_node/connect", {
      nodeGroupName: ngName,
      fromNodeName: "Distribute",
      fromSocketName: "Points",
      toNodeName: "Instance",
      toSocketName: "Points",
    });
    expect(l2.ok).toBe(true);

    // TreeRef.Geometry -> Instance.Instance
    const l3 = await blenderPost("/geo_node/connect", {
      nodeGroupName: ngName,
      fromNodeName: "TreeRef",
      fromSocketName: "Geometry",
      toNodeName: "Instance",
      toSocketName: "Instance",
    });
    expect(l3.ok).toBe(true);

    // Instance.Instances -> Realize.Geometry
    const l4 = await blenderPost("/geo_node/connect", {
      nodeGroupName: ngName,
      fromNodeName: "Instance",
      fromSocketName: "Instances",
      toNodeName: "Realize",
      toSocketName: "Geometry",
    });
    expect(l4.ok).toBe(true);

    // Realize.Geometry -> GroupOutput.Geometry
    const l5 = await blenderPost("/geo_node/connect", {
      nodeGroupName: ngName,
      fromNodeName: "Realize",
      fromSocketName: "Geometry",
      toNodeName: "Group Output",
      toSocketName: "Geometry",
    });
    expect(l5.ok).toBe(true);

    // 4. Apply to terrain
    const apply = await blenderPost<{ modifierName: string }>("/geo_node/apply_to_object", {
      objectName: "Terrain",
      nodeGroupName: ngName,
      modifierName: "Scatter",
    });
    expect(apply.ok).toBe(true);
    expect(apply.data?.modifierName).toBe("Scatter");

    // 5. Bake the modifier into the terrain mesh
    const bake = await blenderPost("/modifier/apply", {
      objectName: "Terrain",
      modifierName: "Scatter",
    });
    expect(bake.ok, JSON.stringify(bake)).toBe(true);

    // 6. Path B export — batch the source collection (one FBX per tree mesh)
    const outDir = join(workDir, "foliage");
    const batch = await blenderPost<{ exportedCount: number; failureCount: number }>(
      "/export/fbx_collection_batch",
      {
        collectionName: "Trees_Source",
        outputDirectory: outDir,
        filenameTemplate: "SM_{ObjectName}.fbx",
        globalScale: 1.0,
        applyUnitScale: true,
        axisForward: "-Z",
        axisUp: "Y",
      },
    );
    expect(batch.ok, JSON.stringify(batch)).toBe(true);
    expect(batch.data?.failureCount).toBe(0);
    expect(batch.data?.exportedCount).toBe(1);

    const treeFbx = join(outDir, "SM_Tree_Proxy.fbx");
    expect(existsSync(treeFbx)).toBe(true);
    expect(statSync(treeFbx).size).toBeGreaterThan(1024);
  }, 300_000);
});
