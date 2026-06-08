import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 1 — character_export_ue5_skeletal (pragmatic v1.0)
 *
 * The brief Recipe references future composites we don't ship yet
 * (`armature_create_ue5_mannequin`, `retopo_create_base_cage`,
 * `vertex_group_auto_weight_from_armature`, `mesh_validate_for_export_ue5`).
 *
 * This test walks the *primitive* chain that DOES exist today and proves it
 * stitches together into a valid skeletal FBX. The full UE5-spec mannequin
 * builder is a future endpoint; here we hand-build a minimal 4-bone rig
 * (root -> pelvis -> spine -> head) that demonstrates the full pipeline.
 */
describe("Recipe 1 — character_export_ue5_skeletal (pragmatic)", () => {
  let workDir = "";

  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-recipe1-"));
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("builds a skeletal character end-to-end and exports as FBX", async () => {
    // 1. Scene scale (UE5: 1 unit = 1 m at globalScale=1.0)
    const unit = await blenderPost("/scene/set_unit_scale_for_modular_kit", { scale: 1.0 });
    expect(unit.ok).toBe(true);

    // 2. Collection
    const coll = await blenderPost("/collection/create", {
      parentPath: "Scene Collection",
      name: "Character",
    });
    expect(coll.ok).toBe(true);

    // 3. Base mesh — cube standing in for the sculpted body
    const body = await blenderPost<{ objectName: string }>("/object/create", {
      type: "CUBE",
      name: "Hero_Body",
      size: 1.6,
      location: [0, 0, 0.8],
      collectionName: "Character",
    });
    expect(body.ok).toBe(true);

    // Subdiv -> remesh-like density (proxy for sculpt)
    const sub = await blenderPost("/modifier/add", {
      objectName: "Hero_Body",
      type: "SUBSURF",
      name: "BodySub",
      properties: { levels: 2, render_levels: 2 },
    });
    expect(sub.ok).toBe(true);
    await blenderPost("/modifier/apply", { objectName: "Hero_Body", modifierName: "BodySub" });

    // 4. UV
    const uv = await blenderPost("/uv/smart_project", {
      objectName: "Hero_Body",
      angleLimit: 66,
      islandMargin: 0.02,
    });
    expect(uv.ok).toBe(true);
    await blenderPost("/uv/pack_islands", { objectName: "Hero_Body", margin: 0.005 });
    await blenderPost("/uv/average_islands_scale", { objectName: "Hero_Body" });

    const uvOk = await blenderPost<{ ok: boolean }>("/uv/validate_for_baking", {
      objectName: "Hero_Body",
    });
    expect(uvOk.ok).toBe(true);

    // 5. Minimal rig — root/pelvis/spine_01/head
    const arm = await blenderPost<{ armatureObjectName: string; armatureName: string }>(
      "/armature/create",
      { name: "SK_Hero", location: [0, 0, 0], collectionName: "Character" },
    );
    expect(arm.ok).toBe(true);
    const armName = arm.data?.armatureObjectName ?? "SK_Hero";

    const bones = [
      { name: "root", head: [0, 0, 0], tail: [0, 0, 0.1], parent: null as string | null },
      { name: "pelvis", head: [0, 0, 0.9], tail: [0, 0, 1.1], parent: "root" },
      { name: "spine_01", head: [0, 0, 1.1], tail: [0, 0, 1.4], parent: "pelvis" },
      { name: "head", head: [0, 0, 1.5], tail: [0, 0, 1.7], parent: "spine_01" },
    ];
    for (const b of bones) {
      const r = await blenderPost("/bone/add", {
        armatureObjectName: armName,
        name: b.name,
        head: b.head,
        tail: b.tail,
      });
      expect(r.ok, `bone ${b.name}`).toBe(true);
      if (b.parent) {
        const p = await blenderPost("/bone/set_parent", {
          armatureObjectName: armName,
          boneName: b.name,
          parentBoneName: b.parent,
          useConnect: false,
        });
        expect(p.ok, `parent ${b.name} -> ${b.parent}`).toBe(true);
      }
    }

    // 6. ARKit-52 face shape keys (this is the implemented composite!)
    const arkit = await blenderPost<{
      createdCount: number;
      existingCount: number;
      createdShapes: string[];
    }>("/metahuman/ensure_arkit52_shape_keys", { objectName: "Hero_Body" });
    expect(arkit.ok, JSON.stringify(arkit)).toBe(true);
    const totalShapes =
      (arkit.data?.createdCount ?? 0) + (arkit.data?.existingCount ?? 0);
    expect(totalShapes).toBe(52);

    // 7. Parent mesh to armature (Armature modifier)
    const parent = await blenderPost("/mesh/parent_to_armature", {
      meshObjectName: "Hero_Body",
      armatureObjectName: armName,
    });
    expect(parent.ok).toBe(true);

    // Manual vertex groups (one per deform bone)
    for (const b of bones) {
      const vg = await blenderPost("/vertex_group/create", {
        objectName: "Hero_Body",
        name: b.name,
      });
      expect(vg.ok, `vg ${b.name}`).toBe(true);
    }

    // 8. Weapon socket on the head bone
    const socket = await blenderPost<{ socketObjectName: string }>("/socket/add", {
      objectName: armName,
      name: "HeadAttach",
      location: [0, 0, 1.7],
    });
    expect(socket.ok).toBe(true);
    expect(socket.data?.socketObjectName).toBe("SOCKET_HeadAttach");

    // 9. Export skeletal FBX
    const fbxPath = join(workDir, "SK_Hero.fbx");
    const exp = await blenderPost("/export/fbx_skeletal", {
      filepath: fbxPath,
      armatureObjectName: armName,
      globalScale: 1.0,
      applyUnitScale: true,
      axisForward: "-Z",
      axisUp: "Y",
      useArmatureDeformOnly: true,
      addLeafBones: false,
      bakeAnim: false,
      useMeshModifiers: true,
    });
    expect(exp.ok, JSON.stringify(exp)).toBe(true);
    expect(existsSync(fbxPath)).toBe(true);
    expect(statSync(fbxPath).size).toBeGreaterThan(1024);
  }, 300_000);
});
