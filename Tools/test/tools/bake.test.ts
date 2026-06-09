import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { mkdtempSync, existsSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir: string;

describe("bake setup + run + image save (B3)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-bake-"));
    await blenderPost("/object/create", { type: "CUBE", name: "BakeTarget", size: 1 });
    await blenderPost("/material/create", { name: "BakeMat" });
    await blenderPost("/material/assign_to_object", {
      objectName: "BakeTarget",
      materialName: "BakeMat",
      slotIndex: 0,
    });
    await blenderPost("/uv/unwrap", { objectName: "BakeTarget" });
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) {
      rmSync(workDir, { recursive: true, force: true });
    }
  });

  it("creates a target image + texture node ready for bake", async () => {
    const res = await blenderPost<{ imageName: string; imageNodeName: string }>(
      "/bake/setup_target_image",
      {
        objectName: "BakeTarget",
        materialName: "BakeMat",
        imageName: "BakeImg",
        width: 64,
        height: 64,
      },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.imageName).toBe("BakeImg");
    expect(res.data?.imageNodeName).toBeTruthy();
  });

  it("rejects setup with material not in object slots", async () => {
    await blenderPost("/material/create", { name: "OrphanMat" });
    const res = await blenderPost("/bake/setup_target_image", {
      objectName: "BakeTarget",
      materialName: "OrphanMat",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("runs a DIFFUSE bake on Cycles with low samples", async () => {
    const res = await blenderPost<{ bakeType: string; samples: number }>("/bake/run", {
      objectName: "BakeTarget",
      type: "DIFFUSE",
      samples: 1,
      margin: 4,
      useClear: true,
    });
    expect(res.ok).toBe(true);
    expect(res.data?.bakeType).toBe("DIFFUSE");
  }, 120_000);

  it("rejects unknown bake type with INVALID_INPUT", async () => {
    const res = await blenderPost("/bake/run", {
      objectName: "BakeTarget",
      type: "NOT_REAL_TYPE",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("saves the baked image to PNG", async () => {
    const filepath = join(workDir, "bake_out.png");
    const res = await blenderPost<{ filepath: string }>("/image/save_as", {
      imageName: "BakeImg",
      filepath,
      fileFormat: "PNG",
    });
    expect(res.ok).toBe(true);
    expect(existsSync(filepath)).toBe(true);
  });

  it("rejects save_as with missing image", async () => {
    const res = await blenderPost("/image/save_as", {
      imageName: "NoImage",
      filepath: join(workDir, "x.png"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
