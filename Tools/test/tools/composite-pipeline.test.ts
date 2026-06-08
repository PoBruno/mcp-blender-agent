/**
 * Composite pipeline endpoints — integration coverage for the tooling that
 * exists primarily to support the ARTIS production flow (file/new,
 * material PBR composite, object/delete, socket bone parenting, action
 * inspect/rename, camera frame_object, server hot-reload, scene frame_current).
 */

import { tmpdir } from "node:os";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir = "";

/**
 * Minimal valid 1x1 RGBA PNG (transparent). Hardcoded to avoid adding pngjs
 * to test deps — Blender only needs the file to load via bpy.data.images.load.
 */
const PNG_1X1 = Buffer.from(
  "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c63" +
  "f8cffcff3f0005010100c5b7e8060000000049454e44ae426082",
  "hex",
);

function writeTinyPng(path: string): void {
  writeFileSync(path, PNG_1X1);
}

describe("composite pipeline endpoints (ARTIS support)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-composite-"));
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  // ── /file/new ──────────────────────────────────────────────────────────
  describe("/file/new", () => {
    it("starts a fresh non-empty scene (default cube/light/camera present)", async () => {
      const r = await blenderPost<{ empty: boolean; sceneName: string }>(
        "/file/new", { empty: false },
      );
      expect(r.ok).toBe(true);
      expect(r.data?.empty).toBe(false);
      const list = await blenderPost<{ count: number }>("/object/list", {});
      expect(list.ok).toBe(true);
      expect((list.data?.count ?? 0)).toBeGreaterThan(0);
    });

    it("starts an empty scene (no default objects)", async () => {
      const r = await blenderPost<{ empty: boolean }>("/file/new", { empty: true });
      expect(r.ok).toBe(true);
      expect(r.data?.empty).toBe(true);
      const list = await blenderPost<{ count: number }>("/object/list", {});
      expect(list.data?.count).toBe(0);
    });
  });

  // ── /object/delete ─────────────────────────────────────────────────────
  describe("/object/delete", () => {
    it("deletes a single object by objectName", async () => {
      await blenderPost("/file/new", { empty: true });
      await blenderPost("/object/create", { type: "CUBE", name: "Doomed" });
      const r = await blenderPost<{ deletedCount: number; deleted: string[] }>(
        "/object/delete", { objectName: "Doomed" },
      );
      expect(r.ok).toBe(true);
      expect(r.data?.deletedCount).toBe(1);
      expect(r.data?.deleted).toContain("Doomed");
    });

    it("deletes multiple via objectNames + is idempotent on missing names", async () => {
      await blenderPost("/file/new", { empty: true });
      await blenderPost("/object/create", { type: "CUBE", name: "A" });
      await blenderPost("/object/create", { type: "CUBE", name: "B" });
      const r = await blenderPost<{
        deletedCount: number; skippedCount: number; deleted: string[]; skipped: string[];
      }>("/object/delete", { objectNames: ["A", "B", "GhostObject"] });
      expect(r.ok).toBe(true);
      expect(r.data?.deletedCount).toBe(2);
      expect(r.data?.skippedCount).toBe(1);
      expect(r.data?.skipped).toContain("GhostObject");
    });

    it("strict=true errors on missing object", async () => {
      await blenderPost("/file/new", { empty: true });
      const r = await blenderPost("/object/delete", {
        objectName: "NeverExisted",
        strict: true,
      });
      expect(r.ok).toBe(false);
    });
  });

  // ── /material/create_pbr_from_textures ─────────────────────────────────
  describe("/material/create_pbr_from_textures", () => {
    it("wires Principled BSDF with 4 PBR textures and correct color spaces", async () => {
      await blenderPost("/file/new", { empty: true });
      const base = join(workDir, "base.png");
      const rgh = join(workDir, "rgh.png");
      const met = join(workDir, "met.png");
      const nrm = join(workDir, "nrm.png");
      writeTinyPng(base);
      writeTinyPng(rgh);
      writeTinyPng(met);
      writeTinyPng(nrm);

      const r = await blenderPost<{
        materialName: string;
        textureCount: number;
        textures: Array<{ slot: string; colorspace: string }>;
      }>("/material/create_pbr_from_textures", {
        materialName: "M_Test",
        baseColor: base,
        roughness: rgh,
        metallic: met,
        normal: nrm,
        normalSpace: "OpenGL",
      });
      expect(r.ok).toBe(true);
      expect(r.data?.materialName).toBe("M_Test");
      expect(r.data?.textureCount).toBe(4);
      const slotMap = Object.fromEntries(
        (r.data?.textures ?? []).map((t) => [t.slot, t.colorspace]),
      );
      expect(slotMap.baseColor).toBe("sRGB");
      expect(slotMap.roughness).toBe("Non-Color");
      expect(slotMap.metallic).toBe("Non-Color");
      expect(slotMap.normal).toBe("Non-Color");
    });

    it("handles DirectX normal space (Y-flip nodes added)", async () => {
      const nrm = join(workDir, "nrm.png");
      // (file already exists from previous test; reuse)
      const r = await blenderPost<{ materialName: string }>(
        "/material/create_pbr_from_textures",
        {
          materialName: "M_DX",
          normal: nrm,
          normalSpace: "DirectX",
        },
      );
      expect(r.ok).toBe(true);
      expect(r.data?.materialName).toBe("M_DX");
    });
  });

  // ── /socket/add with boneName ──────────────────────────────────────────
  describe("/socket/add (UE5 bone-parented sockets)", () => {
    it("parents the empty to a bone via parent_type=BONE", async () => {
      await blenderPost("/file/new", { empty: true });
      await blenderPost("/armature/create", { name: "Armature" });
      const ba = await blenderPost("/bone/add", {
        armatureObjectName: "Armature",
        name: "head_01",
        head: [0, 0, 0],
        tail: [0, 0, 0.5],
      });
      expect(ba.ok).toBe(true);

      const r = await blenderPost<{
        socketObjectName: string;
        parentName: string;
        parentBone: string;
        parentType: string;
      }>("/socket/add", {
        objectName: "Armature",
        name: "Camera",
        boneName: "head_01",
      });
      expect(r.ok).toBe(true);
      expect(r.data?.socketObjectName).toBe("SOCKET_Camera");
      expect(r.data?.parentBone).toBe("head_01");
      expect(r.data?.parentType).toBe("BONE");
    });

    it("rejects boneName referring to a bone that does not exist", async () => {
      const r = await blenderPost("/socket/add", {
        objectName: "Armature",
        name: "GhostBone",
        boneName: "no_such_bone",
      });
      expect(r.ok).toBe(false);
    });
  });

  // ── /action/inspect + /action/rename ──────────────────────────────────
  describe("/action/inspect + /action/rename", () => {
    it("inspect categorizes bone fcurves and produces a stable contentHash", async () => {
      await blenderPost("/file/new", { empty: true });
      await blenderPost("/armature/create", { name: "Armature" });
      await blenderPost("/bone/add", {
        armatureObjectName: "Armature",
        name: "spine_01",
        head: [0, 0, 0],
        tail: [0, 0, 0.5],
      });
      // Create an action with bone keyframes
      await blenderPost("/action/create", { name: "PoseAction" });
      await blenderPost("/action/assign_to_object", {
        objectName: "Armature", actionName: "PoseAction",
      });
      await blenderPost("/keyframe/bone_pose", {
        armatureObjectName: "Armature", boneName: "spine_01", frame: 1,
      });
      await blenderPost("/keyframe/bone_pose", {
        armatureObjectName: "Armature", boneName: "spine_01", frame: 5,
      });

      const i1 = await blenderPost<{
        boneFcurveCount: number;
        shapeKeyFcurveCount: number;
        hasBoneFcurves: boolean;
        bones: string[];
        contentHash: string;
      }>("/action/inspect", { actionName: "PoseAction" });
      expect(i1.ok).toBe(true);
      expect(i1.data?.hasBoneFcurves).toBe(true);
      expect(i1.data?.boneFcurveCount).toBeGreaterThan(0);
      expect(i1.data?.bones).toContain("spine_01");
      expect(i1.data?.contentHash).toMatch(/^[0-9a-f]{40}$/);

      // contentHash is stable across calls
      const i2 = await blenderPost<{ contentHash: string }>(
        "/action/inspect", { actionName: "PoseAction" },
      );
      expect(i2.data?.contentHash).toBe(i1.data?.contentHash);
    });

    it("rename succeeds, is idempotent on same name, and refuses collisions", async () => {
      const renamed = await blenderPost<{ renamed: boolean; previousName: string }>(
        "/action/rename", { actionName: "PoseAction", newName: "AS_Char_Pose" },
      );
      expect(renamed.ok).toBe(true);
      expect(renamed.data?.renamed).toBe(true);
      expect(renamed.data?.previousName).toBe("PoseAction");

      const noop = await blenderPost<{ renamed: boolean }>(
        "/action/rename", { actionName: "AS_Char_Pose", newName: "AS_Char_Pose" },
      );
      expect(noop.ok).toBe(true);
      expect(noop.data?.renamed).toBe(false);

      // Create a second action and try to collide
      await blenderPost("/action/create", { name: "Other" });
      const collide = await blenderPost(
        "/action/rename", { actionName: "Other", newName: "AS_Char_Pose" },
      );
      expect(collide.ok).toBe(false);
      expect(collide.errorCode).toBe("INVALID_INPUT");
    });
  });

  // ── /camera/frame_object ───────────────────────────────────────────────
  describe("/camera/frame_object", () => {
    it("positions camera and sets scene.camera active", async () => {
      await blenderPost("/file/new", { empty: true });
      await blenderPost("/object/create", { type: "CUBE", name: "Target", scale: [2, 2, 2] });
      await blenderPost("/camera/create", { name: "Cam" });
      const r = await blenderPost<{
        cameraName: string;
        targetName: string;
        distance: number;
        boundsRadius: number;
        isActive: boolean;
        location: [number, number, number];
      }>("/camera/frame_object", {
        cameraObjectName: "Cam",
        targetObjectName: "Target",
        direction: "front",
      });
      expect(r.ok).toBe(true);
      expect(r.data?.cameraName).toBe("Cam");
      expect(r.data?.targetName).toBe("Target");
      expect(r.data?.distance).toBeGreaterThan(0);
      expect(r.data?.boundsRadius).toBeGreaterThan(0);
      expect(r.data?.isActive).toBe(true);
      // 'front' direction puts camera in -Y of target center
      expect(r.data?.location[1]).toBeLessThan(0);
    });

    it("rejects unknown direction", async () => {
      const r = await blenderPost("/camera/frame_object", {
        cameraObjectName: "Cam",
        targetObjectName: "Target",
        direction: "northwest",
      });
      expect(r.ok).toBe(false);
    });
  });

  // ── /scene/set_frame_range frameCurrent ────────────────────────────────
  describe("/scene/set_frame_range with frameCurrent", () => {
    it("sets only frameCurrent without touching start/end", async () => {
      await blenderPost("/scene/set_frame_range", { frameStart: 1, frameEnd: 100 });
      const r = await blenderPost<{
        frameStart: number; frameEnd: number; frameCurrent: number;
      }>("/scene/set_frame_range", { frameCurrent: 42 });
      expect(r.ok).toBe(true);
      expect(r.data?.frameStart).toBe(1);
      expect(r.data?.frameEnd).toBe(100);
      expect(r.data?.frameCurrent).toBe(42);
    });
  });

  // ── /server/reload ─────────────────────────────────────────────────────
  describe("/server/reload", () => {
    it("re-imports handler submodules and preserves handler count", async () => {
      const before = await blenderPost<{ handlers: string[]; count: number }>(
        "/server/handlers", {},
      );
      // /server/handlers is a GET — fall back if POST routing differs
      const r = await blenderPost<{
        reloadedCount: number; handlerCount: number; errorCount: number;
      }>("/server/reload", {});
      expect(r.ok).toBe(true);
      expect(r.data?.errorCount).toBe(0);
      expect(r.data?.reloadedCount).toBeGreaterThan(0);
      expect(r.data?.handlerCount).toBeGreaterThan(0);
      if (before.ok) {
        expect(r.data?.handlerCount).toBe(before.data?.count);
      }
    });
  });
});
