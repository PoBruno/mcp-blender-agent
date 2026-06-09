import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir = "";

describe("FBX static export + collision + collection batch (B1/B2)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-fbx-"));
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) {
      rmSync(workDir, { recursive: true, force: true });
    }
  });

  it("creates a wall, adds UCX collision, exports as FBX, file is non-empty", async () => {
    await blenderPost("/collection/create", { name: "KitWall" });
    const wall = await blenderPost("/object/add_blockout", {
      name: "SM_Wall_A",
      footprint: [4, 0.2, 3],
      collectionName: "KitWall",
    });
    expect(wall.ok).toBe(true);

    const ucx = await blenderPost<{ collisionObjectName: string }>(
      "/collision/add_convex_hull",
      { objectName: "SM_Wall_A" },
    );
    expect(ucx.ok).toBe(true);
    expect(ucx.refs?.collisionObjectName).toMatch(/^UCX_SM_Wall_A_/);

    const filepath = join(workDir, "SM_Wall_A.fbx");
    const fbx = await blenderPost<{ filepath: string }>("/export/fbx_static", {
      filepath,
      objectNames: ["SM_Wall_A", ucx.refs!.collisionObjectName as string],
    });
    expect(fbx.ok).toBe(true);
    expect(existsSync(filepath)).toBe(true);
    expect(statSync(filepath).size).toBeGreaterThan(1024);
  });

  it("batches a collection — each top-level object becomes its own .fbx", async () => {
    await blenderPost("/object/add_blockout", {
      name: "SM_Wall_B",
      footprint: [4, 0.2, 3],
      collectionName: "KitWall",
    });
    await blenderPost("/collision/add_box", { objectName: "SM_Wall_B" });

    const batchDir = join(workDir, "batch");
    const res = await blenderPost<{ exportedCount: number; failureCount: number }>(
      "/export/fbx_collection_batch",
      {
        collectionName: "KitWall",
        outputDirectory: batchDir,
        filenameTemplate: "{ObjectName}.fbx",
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.failureCount).toBe(0);
    expect(res.data?.exportedCount).toBeGreaterThanOrEqual(2);
    expect(existsSync(join(batchDir, "SM_Wall_A.fbx"))).toBe(true);
    expect(existsSync(join(batchDir, "SM_Wall_B.fbx"))).toBe(true);
  });
});
