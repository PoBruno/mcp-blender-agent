import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { mkdtempSync, existsSync, rmSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir: string;

describe("render animation small frame range (B9)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-render-"));
    await blenderPost("/object/create", { type: "CUBE", name: "RenderCube" });
    await blenderPost("/render/set_engine", { engine: "BLENDER_EEVEE" });
    await blenderPost("/render/set_resolution", { width: 64, height: 64, percentage: 100 });
    await blenderPost("/scene/set_frame_range", { frameStart: 1, frameEnd: 2 });
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) {
      rmSync(workDir, { recursive: true, force: true });
    }
  });

  it("renders a 2-frame animation to PNG", async () => {
    const prefix = join(workDir, "anim_");
    const res = await blenderPost<{ frameStart: number; frameEnd: number }>(
      "/render/render_animation",
      { filepathPrefix: prefix, fileFormat: "PNG" },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.frameStart).toBe(1);
    expect(res.data?.frameEnd).toBe(2);
    const files = readdirSync(workDir);
    expect(files.length).toBeGreaterThanOrEqual(2);
  }, 120_000);

  it("rejects render_animation without filepathPrefix", async () => {
    const res = await blenderPost("/render/render_animation", {});
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
