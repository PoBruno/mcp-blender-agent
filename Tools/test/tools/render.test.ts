import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir = "";

describe("render + camera + light + world (B9)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-render-"));
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("creates a camera, sets it active, configures a 256x256 EEVEE render, renders to disk", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "Subject" });
    const cam = await blenderPost("/camera/create", {
      name: "Cam",
      location: [0, -4, 2.5],
      rotation: [1.2, 0, 0],
    });
    expect(cam.ok).toBe(true);

    await blenderPost("/camera/set_active", { objectName: "Cam" });

    await blenderPost("/light/create", {
      type: "SUN",
      name: "Sun",
      energy: 3,
      location: [0, 0, 5],
    });

    await blenderPost("/world/create", { name: "GreyWorld" });
    await blenderPost("/world/assign_to_scene", { worldName: "GreyWorld" });

    // EEVEE_NEXT in Blender 4.2+; fall back to BLENDER_EEVEE otherwise
    const eng = await blenderPost("/render/set_engine", { engine: "BLENDER_EEVEE_NEXT" });
    if (!eng.ok) {
      await blenderPost("/render/set_engine", { engine: "BLENDER_EEVEE" });
    }

    await blenderPost("/render/set_resolution", {
      width: 256,
      height: 256,
      percentage: 100,
    });

    const filepath = join(workDir, "render.png");
    const res = await blenderPost<{ filepath: string }>("/render/render_still", {
      filepath,
      fileFormat: "PNG",
    });
    expect(res.ok).toBe(true);
    expect(existsSync(filepath)).toBe(true);
    expect(statSync(filepath).size).toBeGreaterThan(100);
  });
});
