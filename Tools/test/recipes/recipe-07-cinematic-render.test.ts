import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, readdirSync, rmSync, statSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 7 — cinematic_render_sequence
 *
 * Full chain:
 *   scene + EEVEE engine + tiny output config (we use 64x64 / 2 frames so the
 *     test actually finishes in CI)
 *   -> 3 lights (Area key, Area fill, Spot rim) with shape/size tweaks
 *   -> 2 cameras with DOF + clipping; active camera = wide
 *   -> compositor: RenderLayers -> HueSat -> BrightContrast (proxy for the
 *      grade chain) wired into Composite output
 *   -> render still + render animation (2 frames, PNG)
 *
 * Notes:
 *   - We don't use Cycles here (slow + needs GPU); render_set_engine ranges
 *     over the EEVEE alias both 4.2 ("BLENDER_EEVEE_NEXT") and 5.x ("BLENDER_EEVEE")
 *     so the same call works on either.
 *   - We avoid CompositorNodeComposite (removed in 5.x); CompositorNodeBrightContrast
 *     is the tail of the chain.
 *   - HDRI/world environment is deliberately out of scope (no fixture file).
 */
describe("Recipe 7 — cinematic_render_sequence", () => {
  let workDir = "";

  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-recipe7-"));
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("builds and renders a 2-frame cinematic with DOF, lights, compositor", async () => {
    // 1. Scene + engine
    const scene = await blenderPost<{ sceneName: string }>("/scene/create", {
      name: "Cinematic_Opening",
      unitSystem: "METRIC",
      scaleLength: 1.0,
      frameStart: 1,
      frameEnd: 2,
    });
    expect(scene.ok).toBe(true);
    const sceneName = scene.data!.sceneName;

    const setActive = await blenderPost("/scene/set_active", { sceneName });
    expect(setActive.ok).toBe(true);

    const engine = await blenderPost<{ engine: string }>("/render/set_engine", {
      sceneName,
      engine: "BLENDER_EEVEE",
    });
    expect(engine.ok).toBe(true);

    // 2. Render output — tiny size so the actual render finishes fast.
    const renderDir = join(workDir, "render");
    const setOutput = await blenderPost<{
      filepath: string;
      fileFormat: string;
      fps: number;
      frameStart: number;
      frameEnd: number;
    }>("/render/set_output", {
      sceneName,
      filepath: join(renderDir, "frame_"),
      fileFormat: "PNG",
      colorMode: "RGBA",
      colorDepth: "8",
      frameStart: 1,
      frameEnd: 2,
      fps: 24,
    });
    expect(setOutput.ok).toBe(true);
    expect(setOutput.data?.fileFormat).toBe("PNG");
    expect(setOutput.data?.fps).toBe(24);

    const setRes = await blenderPost("/render/set_resolution", {
      sceneName,
      width: 64,
      height: 64,
      percentage: 100,
    });
    expect(setRes.ok).toBe(true);

    // 3. Lights — key (area), fill (area), rim (spot)
    const key = await blenderPost<{ lightObjectName: string }>("/light/create", {
      name: "KeyLight",
      type: "AREA",
      energy: 500,
      color: [1.0, 0.95, 0.85],
      location: [3, -3, 4],
    });
    expect(key.ok).toBe(true);
    const keyName = key.data!.lightObjectName;

    const keyShape = await blenderPost("/light/set_property", {
      objectName: keyName,
      properties: { shape: "RECTANGLE", size: 2.0, size_y: 1.0 },
    });
    expect(keyShape.ok).toBe(true);

    const fill = await blenderPost<{ lightObjectName: string }>("/light/create", {
      name: "FillLight",
      type: "AREA",
      energy: 120,
      color: [0.8, 0.85, 1.0],
      location: [-3, -2, 3],
    });
    expect(fill.ok).toBe(true);

    const rim = await blenderPost<{ lightObjectName: string }>("/light/create", {
      name: "RimLight",
      type: "SPOT",
      energy: 300,
      color: [1.0, 0.9, 0.8],
      location: [0, 4, 5],
    });
    expect(rim.ok).toBe(true);

    // 4. Cameras — wide + close, both with DOF + clipping
    const camWide = await blenderPost<{ cameraObjectName: string }>("/camera/create", {
      name: "Cam_Wide",
      lens: 35,
      location: [0, -8, 1.7],
      rotation: [1.4835, 0, 0],
    });
    expect(camWide.ok).toBe(true);
    const wideName = camWide.data!.cameraObjectName;

    const wideDof = await blenderPost<{ useDof: boolean; fStop: number; focusDistance: number }>(
      "/camera/set_dof",
      { objectName: wideName, focusDistance: 8.0, fStop: 2.8 },
    );
    expect(wideDof.ok).toBe(true);
    expect(wideDof.data?.useDof).toBe(true);
    expect(wideDof.data?.fStop).toBeCloseTo(2.8, 5);
    expect(wideDof.data?.focusDistance).toBeCloseTo(8.0, 5);

    const wideClip = await blenderPost<{ clipStart: number; clipEnd: number }>(
      "/camera/set_clipping",
      { objectName: wideName, clipStart: 0.1, clipEnd: 1000 },
    );
    expect(wideClip.ok).toBe(true);
    expect(wideClip.data?.clipStart).toBeCloseTo(0.1, 5);
    expect(wideClip.data?.clipEnd).toBeCloseTo(1000, 5);

    const camClose = await blenderPost<{ cameraObjectName: string }>("/camera/create", {
      name: "Cam_Close",
      lens: 85,
      location: [0.3, -2, 1.7],
      rotation: [1.535, 0, 0.0873],
    });
    expect(camClose.ok).toBe(true);
    const closeName = camClose.data!.cameraObjectName;

    const closeDof = await blenderPost("/camera/set_dof", {
      objectName: closeName,
      focusDistance: 2.0,
      fStop: 1.4,
    });
    expect(closeDof.ok).toBe(true);

    const setActiveCam = await blenderPost("/camera/set_active", {
      sceneName,
      objectName: wideName,
    });
    expect(setActiveCam.ok).toBe(true);

    // 5. Compositor: RenderLayers -> HueSat -> BrightContrast
    const compEnable = await blenderPost("/compositor/enable", { sceneName });
    expect(compEnable.ok).toBe(true);

    const rlNode = await blenderPost<{ nodeName: string }>("/compositor/add_node", {
      sceneName,
      type: "CompositorNodeRLayers",
      name: "RenderLayers",
    });
    expect(rlNode.ok).toBe(true);

    const hueNode = await blenderPost<{ nodeName: string }>("/compositor/add_node", {
      sceneName,
      type: "CompositorNodeHueSat",
      name: "KeyGrade",
    });
    expect(hueNode.ok).toBe(true);

    // Pull saturation down via input default_value (the dynamic recipe form).
    const hueSet = await blenderPost("/compositor/set_node_input", {
      sceneName,
      nodeName: "KeyGrade",
      inputName: "Saturation",
      value: 0.9,
    });
    expect(hueSet.ok).toBe(true);

    const bcNode = await blenderPost<{ nodeName: string }>("/compositor/add_node", {
      sceneName,
      type: "CompositorNodeBrightContrast",
      name: "Tail",
    });
    expect(bcNode.ok).toBe(true);

    // Mute Tail then unmute — proves set_node_property works on RNA bools.
    const muteOn = await blenderPost("/compositor/set_node_property", {
      sceneName,
      nodeName: "Tail",
      propertyName: "mute",
      propertyValue: true,
    });
    expect(muteOn.ok).toBe(true);
    const muteOff = await blenderPost("/compositor/set_node_property", {
      sceneName,
      nodeName: "Tail",
      propertyName: "mute",
      propertyValue: false,
    });
    expect(muteOff.ok).toBe(true);

    const link1 = await blenderPost("/compositor/connect", {
      sceneName,
      fromNodeName: "RenderLayers",
      fromSocketName: "Image",
      toNodeName: "KeyGrade",
      toSocketName: "Image",
    });
    expect(link1.ok).toBe(true);

    const link2 = await blenderPost("/compositor/connect", {
      sceneName,
      fromNodeName: "KeyGrade",
      fromSocketName: "Image",
      toNodeName: "Tail",
      toSocketName: "Image",
    });
    expect(link2.ok).toBe(true);

    // 6. Render a still and a tiny animation.
    const still = await blenderPost<{ filepath: string }>("/render/render_still", {
      sceneName,
      filepath: join(renderDir, "still.png"),
      fileFormat: "PNG",
    });
    expect(still.ok, JSON.stringify(still)).toBe(true);
    expect(existsSync(join(renderDir, "still.png"))).toBe(true);
    expect(statSync(join(renderDir, "still.png")).size).toBeGreaterThan(64);

    const anim = await blenderPost("/render/render_animation", {
      sceneName,
      filepathPrefix: join(renderDir, "anim_"),
      fileFormat: "PNG",
    });
    expect(anim.ok, JSON.stringify(anim)).toBe(true);

    const frames = readdirSync(renderDir).filter((f) => f.startsWith("anim_") && f.endsWith(".png"));
    expect(frames.length).toBeGreaterThanOrEqual(2);
  }, 300_000);
});
