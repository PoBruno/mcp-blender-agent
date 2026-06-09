import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir = "";

describe("vision feedback (snapshot + contact_sheet)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-vision-"));
    await blenderPost("/object/create", { type: "SPHERE", name: "VisionSubject" });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("snapshot falls back to a render in background mode and writes a PNG", async () => {
    const filepath = join(workDir, "snap.png");
    const res = await blenderPost<{ filepath: string; mode: string }>("/vision/snapshot", {
      objectNames: ["VisionSubject"],
      angle: "three_quarter",
      resolution: 256,
      samples: 8,
      outputPath: filepath,
    });
    expect(res.ok).toBe(true);
    // headless has no viewport, so it must take the render fallback
    expect(res.data?.mode).toBe("render");
    expect(existsSync(filepath)).toBe(true);
    expect(statSync(filepath).size).toBeGreaterThan(100);
  });

  it("snapshot requires outputPath", async () => {
    const res = await blenderPost("/vision/snapshot", { objectNames: ["VisionSubject"] });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("contact_sheet composes a grid PNG at low samples", async () => {
    const filepath = join(workDir, "sheet.png");
    const res = await blenderPost<{ contactSheet: string }>("/vision/contact_sheet", {
      objectNames: ["VisionSubject"],
      angles: ["front", "three_quarter"],
      resolution: 128,
      samples: 8,
      outputPath: filepath,
    });
    expect(res.ok).toBe(true);
    expect(existsSync(filepath)).toBe(true);
    expect(statSync(filepath).size).toBeGreaterThan(100);
  });

  it("screenshot_viewport returns NO_VIEWPORT in background mode", async () => {
    const res = await blenderPost("/vision/screenshot_viewport", {
      outputPath: join(workDir, "vp.png"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("NO_VIEWPORT");
  });
});
