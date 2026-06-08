import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 9 — UE5 character rig hygiene + AimOffset export
 *
 * Walks the artist briefing (ARTIS_AGENT_OBJECTIVE.md) end-to-end:
 *  - Build a minimal UE5-style skeleton with rolled spine/neck/head bones
 *  - bone/list audit, recalculate_roll to clear them
 *  - armature/add_ue5_ik_bones (idempotent)
 *  - socket/add for SOCKET_Camera + SOCKET_HandBall_R
 *  - keyframe_bone_pose 9-pose AimOffset matrix (yaw/pitch on head_01)
 *  - armature/validate_ue5_convention — must pass
 *  - export_fbx_skeletal with UE5 axes + bakeSpaceTransform
 *  - export_fbx_animation per "action" with the same axes
 */
describe("Recipe 9 — UE5 character rig hygiene + AimOffset export", () => {
  let workDir = "";

  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-recipe9-"));
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("cleans rolls, adds IK + sockets, bakes a 9-pose AimOffset, validates, exports", async () => {
    // 1. Scene + collection
    await blenderPost("/scene/set_unit_scale_for_modular_kit", { scale: 1.0 });
    await blenderPost("/collection/create", {
      parentPath: "Scene Collection",
      name: "Manuel",
    });

    // 2. Mesh stand-in
    await blenderPost("/object/create", {
      type: "CUBE",
      name: "Manuel_Body",
      size: 0.9,
      location: [0, 0, 0.9],
      collectionName: "Manuel",
    });

    // 3. Armature with rolled bones — exactly the ARTIS briefing scenario
    const arm = await blenderPost<{ armatureObjectName: string }>("/armature/create", {
      name: "SK_Manuel",
      location: [0, 0, 0],
      collectionName: "Manuel",
    });
    expect(arm.ok).toBe(true);
    const armName = arm.data?.armatureObjectName ?? "SK_Manuel";

    // Vertical chain, rolled (77.9°, 81.8°, 104.5°, 90.4°)
    const chain = [
      { name: "root", head: [0, 0, 0], tail: [0, 0, 0.1], parent: null, roll: 0 },
      { name: "pelvis", head: [0, 0, 0.9], tail: [0, 0, 1.0], parent: "root", roll: 0 },
      { name: "spine_01", head: [0, 0, 1.0], tail: [0, 0, 1.2], parent: "pelvis", roll: 1.36 },
      { name: "spine_02", head: [0, 0, 1.2], tail: [0, 0, 1.4], parent: "spine_01", roll: 1.428 },
      { name: "neck_01", head: [0, 0, 1.4], tail: [0, 0, 1.55], parent: "spine_02", roll: 1.824 },
      { name: "head_01", head: [0, 0, 1.55], tail: [0, 0, 1.75], parent: "neck_01", roll: 1.578 },
      // Hand for sockets
      { name: "hand_r", head: [-0.3, 0, 1.1], tail: [-0.4, 0, 1.1], parent: "spine_02", roll: 0 },
    ] as const;

    for (const b of chain) {
      const r = await blenderPost("/bone/add", {
        armatureObjectName: armName,
        name: b.name,
        head: b.head,
        tail: b.tail,
        roll: b.roll,
      });
      expect(r.ok, `bone ${b.name}`).toBe(true);
      if (b.parent) {
        await blenderPost("/bone/set_parent", {
          armatureObjectName: armName,
          boneName: b.name,
          parentBoneName: b.parent,
          useConnect: false,
        });
      }
    }

    // 4. Audit — find rolled bones
    const auditBefore = await blenderPost<{
      bones: { name: string; roll: number }[];
    }>("/bone/list", { armatureObjectName: armName, namePattern: "spine" });
    expect(auditBefore.ok).toBe(true);
    const rolledBefore = (auditBefore.data?.bones ?? []).filter((b) => Math.abs(b.roll) > 0.01);
    expect(rolledBefore.length).toBe(2);

    // 5. Auto-fix rolls on spine/neck/head with GLOBAL_POS_Z
    const fix = await blenderPost("/bone/recalculate_roll", {
      armatureObjectName: armName,
      boneNames: ["spine_01", "spine_02", "neck_01", "head_01"],
      type: "GLOBAL_POS_Z",
    });
    expect(fix.ok).toBe(true);

    // For purely vertical bones, calculate_roll cannot resolve from +Z (the
    // bone IS pointing +Z). Manually clear those rolls — this mirrors the
    // artist's manual cleanup pass when the auto-fix is ambiguous.
    await blenderPost("/bone/set_roll", {
      armatureObjectName: armName,
      boneNames: ["spine_01", "spine_02", "neck_01", "head_01"],
      roll: 0.0,
    });

    const auditAfter = await blenderPost<{
      bones: { name: string; roll: number }[];
    }>("/bone/list", {
      armatureObjectName: armName,
      namePattern: "spine",
    });
    for (const b of auditAfter.data?.bones ?? []) {
      expect(Math.abs(b.roll)).toBeLessThan(0.02);
    }

    // 6. UE5 IK control bones
    const ik = await blenderPost<{ createdCount: number; existingCount: number }>(
      "/armature/add_ue5_ik_bones",
      { armatureObjectName: armName },
    );
    expect(ik.ok).toBe(true);
    expect(ik.data?.createdCount).toBe(7);

    // 7. Sockets — Camera on head, HandBall on right hand (ARTIS use case)
    const cam = await blenderPost<{ socketObjectName: string }>("/socket/add", {
      objectName: armName,
      name: "Camera",
      boneName: "head_01",
      location: [0, 0.1, 1.7],
    });
    expect(cam.ok).toBe(true);
    expect(cam.data?.socketObjectName).toBe("SOCKET_Camera");

    const handBall = await blenderPost<{ socketObjectName: string }>("/socket/add", {
      objectName: armName,
      name: "HandBall_R",
      boneName: "hand_r",
      location: [-0.4, 0, 1.1],
    });
    expect(handBall.ok).toBe(true);
    expect(handBall.data?.socketObjectName).toBe("SOCKET_HandBall_R");

    // 8. Mesh -> armature parenting
    await blenderPost("/mesh/parent_to_armature", {
      meshObjectName: "Manuel_Body",
      armatureObjectName: armName,
    });

    // 9. AimOffset 9-pose matrix on head_01 (yaw -90/0/+90, pitch -90/0/+90)
    // Frames 1..9 in the order: (yaw, pitch) sweep.
    const aimOffsets: Array<[number, number, number, number]> = [
      // [frame, yawDeg, pitchDeg, _unused]
      [1, -90, -90, 0],
      [2, 0, -90, 0],
      [3, 90, -90, 0],
      [4, -90, 0, 0],
      [5, 0, 0, 0],
      [6, 90, 0, 0],
      [7, -90, 90, 0],
      [8, 0, 90, 0],
      [9, 90, 90, 0],
    ];
    const DEG = Math.PI / 180;
    for (const [frame, yaw, pitch] of aimOffsets) {
      // Quaternion for ZYX rotation (yaw around Z, pitch around X). For a simple
      // AimOffset on the head, treat as two consecutive rotations.
      const cy = Math.cos((yaw * DEG) / 2);
      const sy = Math.sin((yaw * DEG) / 2);
      const cp = Math.cos((pitch * DEG) / 2);
      const sp = Math.sin((pitch * DEG) / 2);
      const quat: [number, number, number, number] = [
        cy * cp,           // w
        cy * sp,           // x
        sy * sp,           // y (mixed term)
        sy * cp,           // z
      ];
      await blenderPost("/bone/set_pose_transform", {
        armatureObjectName: armName,
        boneName: "head_01",
        rotationQuaternion: quat,
      });
      const kf = await blenderPost("/keyframe/bone_pose", {
        armatureObjectName: armName,
        boneName: "head_01",
        frame,
        channels: ["rotation_quaternion"],
      });
      expect(kf.ok, `keyframe frame ${frame}`).toBe(true);
    }

    // 10. UE5 convention validation — must pass after our cleanup
    const validate = await blenderPost<{ passed: boolean; failureCount: number }>(
      "/armature/validate_ue5_convention",
      {
        armatureObjectName: armName,
        zeroRollBones: ["spine_01", "spine_02", "neck_01", "head_01"],
        requiredBones: ["ik_foot_root", "ik_foot_l", "ik_foot_r", "ik_hand_root"],
      },
    );
    expect(validate.ok, JSON.stringify(validate.data)).toBe(true);
    expect(validate.data?.passed).toBe(true);

    // 11. Export skeletal FBX with UE5 axes + bakeSpaceTransform
    const skPath = join(workDir, "SK_Manuel.fbx");
    const skExp = await blenderPost("/export/fbx_skeletal", {
      filepath: skPath,
      armatureObjectName: armName,
      globalScale: 1.0,
      applyUnitScale: true,
      axisForward: "-Y",
      axisUp: "Z",
      bakeSpaceTransform: true,
      useArmatureDeformOnly: true,
      addLeafBones: false,
      bakeAnim: false,
      useMeshModifiers: true,
      primaryBoneAxis: "Y",
      secondaryBoneAxis: "X",
    });
    expect(skExp.ok, JSON.stringify(skExp)).toBe(true);
    expect(existsSync(skPath)).toBe(true);
    expect(statSync(skPath).size).toBeGreaterThan(1024);

    // 12. Export AimOffset as animation FBX
    const aimPath = join(workDir, "A_Manuel_AimOffset.fbx");
    const aimExp = await blenderPost("/export/fbx_animation", {
      filepath: aimPath,
      armatureObjectName: armName,
      globalScale: 1.0,
      applyUnitScale: true,
      axisForward: "-Y",
      axisUp: "Z",
      bakeSpaceTransform: true,
      addLeafBones: false,
      primaryBoneAxis: "Y",
      secondaryBoneAxis: "X",
    });
    expect(aimExp.ok, JSON.stringify(aimExp)).toBe(true);
    expect(existsSync(aimPath)).toBe(true);
    expect(statSync(aimPath).size).toBeGreaterThan(1024);
  }, 300_000);
});
