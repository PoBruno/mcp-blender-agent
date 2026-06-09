import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 5 — prop_high_to_low_bake_export
 *
 * Pragmatic version using v1.0 primitives only (no composite "bake_pbr_set"
 * helper yet — agents chain these calls).
 *
 * Chain:
 *   1. high-poly source cube (subdivision modifier baked = "Sculpt_HighPoly")
 *   2. duplicate-linked to a "Sculpt_LowPoly" target
 *   3. decimate modifier on low-poly -> apply -> proves topology mutated
 *   4. UV smart-project + pack on low-poly
 *   5. material + bake target image (1024) on low-poly
 *   6. bake AO (Cycles, low samples) onto the target image
 *   7. save image to disk
 *   8. add convex hull collision (UCX_)
 *   9. export low-poly + UCX as a single FBX static mesh
 *
 * AO is used (not full PBR set) because it's the fastest single-pass bake on
 * Cycles and proves the whole bake-target/save pipeline end-to-end.
 */
describe("Recipe 5 — prop_high_to_low_bake_export", () => {
  let workDir = "";

  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-recipe5-"));
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("builds a high-to-low bake-and-export pipeline end-to-end", async () => {
    // 1. High-poly source: cube + subsurf to drive triangle count up
    const high = await blenderPost<{ objectName: string }>("/object/create", {
      type: "CUBE",
      name: "Sculpt_HighPoly",
      location: [0, 0, 0],
    });
    expect(high.ok).toBe(true);

    const subsurf = await blenderPost("/modifier/add", {
      objectName: "Sculpt_HighPoly",
      type: "SUBSURF",
      name: "Subdiv",
      properties: { levels: 3, render_levels: 3 },
    });
    expect(subsurf.ok).toBe(true);

    const applyHigh = await blenderPost("/modifier/apply", {
      objectName: "Sculpt_HighPoly",
      modifierName: "Subdiv",
    });
    expect(applyHigh.ok).toBe(true);

    // 2. Low-poly: independent cube (smaller subdiv) so decimate doesn't
    //    mutate the high-poly mesh (linked dup would share data).
    const low = await blenderPost<{ objectName: string }>("/object/create", {
      type: "CUBE",
      name: "Sculpt_LowPoly",
      location: [0, 0, 0],
    });
    expect(low.ok).toBe(true);
    expect(low.data?.objectName).toBe("Sculpt_LowPoly");

    const lowSub = await blenderPost("/modifier/add", {
      objectName: "Sculpt_LowPoly",
      type: "SUBSURF",
      name: "LowSub",
      properties: { levels: 1, render_levels: 1 },
    });
    expect(lowSub.ok).toBe(true);

    const decimate = await blenderPost("/modifier/add", {
      objectName: "Sculpt_LowPoly",
      type: "DECIMATE",
      name: "LOD",
      properties: { ratio: 0.5 },
    });
    expect(decimate.ok).toBe(true);

    const applyLowSub = await blenderPost("/modifier/apply", {
      objectName: "Sculpt_LowPoly",
      modifierName: "LowSub",
    });
    expect(applyLowSub.ok).toBe(true);

    const applyDecimate = await blenderPost("/modifier/apply", {
      objectName: "Sculpt_LowPoly",
      modifierName: "LOD",
    });
    expect(applyDecimate.ok).toBe(true);

    // 3. UV unwrap low-poly
    const uv = await blenderPost("/uv/smart_project", {
      objectName: "Sculpt_LowPoly",
      angleLimit: 66,
      islandMargin: 0.02,
    });
    expect(uv.ok).toBe(true);

    const pack = await blenderPost("/uv/pack_islands", {
      objectName: "Sculpt_LowPoly",
      margin: 0.005,
    });
    expect(pack.ok).toBe(true);

    // 4. Material on low-poly
    const mat = await blenderPost<{ materialName: string }>("/material/create", {
      name: "M_Prop",
    });
    expect(mat.ok).toBe(true);

    const assign = await blenderPost("/material/assign_slot", {
      objectName: "Sculpt_LowPoly",
      materialName: "M_Prop",
      slotIndex: 0,
    });
    expect(assign.ok).toBe(true);

    // 5. Bake target image (small — 256 — to keep the test fast)
    const target = await blenderPost<{ imageName: string }>("/bake/setup_target_image", {
      objectName: "Sculpt_LowPoly",
      materialName: "M_Prop",
      imageName: "T_Prop_AO",
      width: 256,
      height: 256,
    });
    expect(target.ok).toBe(true);
    expect(target.data?.imageName).toBe("T_Prop_AO");

    // 6. Bake AO (single pass, low samples = fast)
    const bake = await blenderPost("/bake/run", {
      objectName: "Sculpt_LowPoly",
      type: "AO",
      samples: 4,
      margin: 8,
      useClear: true,
    });
    expect(bake.ok, JSON.stringify(bake)).toBe(true);

    // 7. Save the bake to disk
    const aoPath = join(workDir, "T_Prop_AO.png");
    const save = await blenderPost("/image/save_as", {
      imageName: "T_Prop_AO",
      filepath: aoPath,
      fileFormat: "PNG",
    });
    expect(save.ok).toBe(true);
    expect(existsSync(aoPath)).toBe(true);
    expect(statSync(aoPath).size).toBeGreaterThan(128);

    // 8. Collision
    const ucx = await blenderPost<{ collisionObjectName: string }>(
      "/collision/add_convex_hull",
      { objectName: "Sculpt_LowPoly" },
    );
    expect(ucx.ok).toBe(true);
    expect(ucx.refs?.collisionObjectName).toMatch(/^UCX_Sculpt_LowPoly_/);

    // 9. Export low-poly + UCX as one FBX
    const fbxPath = join(workDir, "SM_Prop.fbx");
    const exported = await blenderPost("/export/fbx_static", {
      filepath: fbxPath,
      objectNames: ["Sculpt_LowPoly", ucx.refs!.collisionObjectName as string],
      globalScale: 1.0,
      applyUnitScale: true,
      axisForward: "-Z",
      axisUp: "Y",
      useMeshModifiers: true,
    });
    expect(exported.ok, JSON.stringify(exported)).toBe(true);
    expect(existsSync(fbxPath)).toBe(true);
    expect(statSync(fbxPath).size).toBeGreaterThan(1024);
  }, 300_000);
});
