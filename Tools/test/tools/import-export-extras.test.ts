import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { mkdtempSync, existsSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir: string;

describe("import round-trip (fbx/obj/gltf) and skeletal/animation FBX export", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-io-"));
    // Source rigged scene
    await blenderPost("/armature/create", { name: "ExpRig" });
    await blenderPost("/bone/add", {
      armatureObjectName: "ExpRig",
      name: "Root",
      head: [0, 0, 0],
      tail: [0, 0, 1],
    });
    await blenderPost("/object/create", { type: "CUBE", name: "ExpMesh", size: 1 });
    await blenderPost("/mesh/parent_to_armature", {
      meshObjectName: "ExpMesh",
      armatureObjectName: "ExpRig",
    });
    await blenderPost("/action/create", { name: "ExpAction" });
    await blenderPost("/action/assign_to_object", {
      objectName: "ExpRig",
      actionName: "ExpAction",
    });
    await blenderPost("/keyframe/bone_pose", {
      armatureObjectName: "ExpRig",
      boneName: "Root",
      frame: 1,
    });
    await blenderPost("/keyframe/bone_pose", {
      armatureObjectName: "ExpRig",
      boneName: "Root",
      frame: 10,
    });
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) {
      rmSync(workDir, { recursive: true, force: true });
    }
  });

  it("exports the rigged mesh as skeletal FBX", async () => {
    const out = join(workDir, "skel.fbx");
    const res = await blenderPost<{ filepath: string }>("/export/fbx_skeletal", {
      filepath: out,
      armatureObjectName: "ExpRig",
    });
    expect(res.ok).toBe(true);
    expect(existsSync(out)).toBe(true);
  });

  it("exports an animation-only FBX", async () => {
    const out = join(workDir, "anim.fbx");
    const res = await blenderPost<{ filepath: string }>("/export/fbx_animation", {
      filepath: out,
      armatureObjectName: "ExpRig",
      bakeAnimStep: 1.0,
    });
    expect(res.ok).toBe(true);
    expect(existsSync(out)).toBe(true);
  });

  it("imports the skeletal FBX back", async () => {
    const src = join(workDir, "skel.fbx");
    const res = await blenderPost<{ importedObjects: string[] }>("/import/fbx", {
      filepath: src,
    });
    expect(res.ok).toBe(true);
    expect((res.data?.importedObjects ?? []).length).toBeGreaterThan(0);
  });

  it("rejects import with missing file", async () => {
    const res = await blenderPost("/import/fbx", {
      filepath: join(workDir, "nope.fbx"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("export rejects non-armature source with INVALID_INPUT", async () => {
    const out = join(workDir, "fail.fbx");
    const res = await blenderPost("/export/fbx_skeletal", {
      filepath: out,
      armatureObjectName: "ExpMesh",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
