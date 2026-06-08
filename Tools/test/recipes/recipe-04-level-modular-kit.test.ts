import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 4 — level_modular_kit_bake_export
 *
 * Full chain:
 *   scene unit scale -> collection -> 3 blockout walls
 *   -> UCX collision per wall
 *   -> procedural grid material assigned to each
 *   -> smart UV unwrap on each
 *   -> batch FBX export with UE5-correct axes
 */
describe("Recipe 4 — level_modular_kit_bake_export", () => {
  let workDir = "";

  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-recipe4-"));
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("builds and exports a 3-piece UE5 modular kit end-to-end", async () => {
    const sceneSetup = await blenderPost("/scene/set_unit_scale_for_modular_kit", {});
    expect(sceneSetup.ok).toBe(true);

    const coll = await blenderPost("/collection/create", { name: "Kit_Walls" });
    expect(coll.ok).toBe(true);

    const mat = await blenderPost<{ materialName: string }>(
      "/material/create_procedural_grid",
      { name: "Grid_Kit", squareSize: 0.5 },
    );
    expect(mat.ok).toBe(true);

    const walls = ["SM_Wall_A", "SM_Wall_B", "SM_Wall_C"];
    for (const name of walls) {
      const wall = await blenderPost("/object/add_blockout", {
        name,
        footprint: [4, 0.2, 3],
        collectionName: "Kit_Walls",
      });
      expect(wall.ok, `wall ${name} create`).toBe(true);

      const ucx = await blenderPost<{ collisionObjectName: string }>(
        "/collision/add_convex_hull",
        { objectName: name },
      );
      expect(ucx.ok, `wall ${name} UCX`).toBe(true);
      expect(ucx.refs?.collisionObjectName).toMatch(new RegExp(`^UCX_${name}_`));

      const slot = await blenderPost("/material/assign_slot", {
        objectName: name,
        materialName: "Grid_Kit",
        slotIndex: 0,
      });
      expect(slot.ok, `wall ${name} material assign`).toBe(true);

      const uv = await blenderPost("/uv/smart_project", { objectName: name });
      expect(uv.ok, `wall ${name} smart project`).toBe(true);
    }

    const batchDir = join(workDir, "batch");
    const batch = await blenderPost<{ exportedCount: number; failureCount: number }>(
      "/export/fbx_collection_batch",
      {
        collectionName: "Kit_Walls",
        outputDirectory: batchDir,
        filenameTemplate: "{ObjectName}.fbx",
        includeCollisionChildren: true,
      },
    );
    expect(batch.ok).toBe(true);
    expect(batch.data?.failureCount).toBe(0);
    expect(batch.data?.exportedCount).toBe(walls.length);

    for (const name of walls) {
      const fbxPath = join(batchDir, `${name}.fbx`);
      expect(existsSync(fbxPath), `${name}.fbx exists`).toBe(true);
      expect(statSync(fbxPath).size).toBeGreaterThan(1024);
    }
  }, 180_000);
});
