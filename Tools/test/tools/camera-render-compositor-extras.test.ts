import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir = "";

describe("camera/render/compositor — new endpoints", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-cam-extras-"));
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("camera_set_dof sets focus_distance, fStop, and useDof", async () => {
    const cam = await blenderPost<{ cameraObjectName: string }>("/camera/create", {
      name: "Cam_DOF",
    });
    expect(cam.ok).toBe(true);
    const name = cam.data!.cameraObjectName;

    const dof = await blenderPost<{
      useDof: boolean;
      focusDistance: number;
      fStop: number;
    }>("/camera/set_dof", { objectName: name, focusDistance: 5.5, fStop: 2.0 });
    expect(dof.ok).toBe(true);
    expect(dof.data?.useDof).toBe(true);
    expect(dof.data?.focusDistance).toBeCloseTo(5.5, 5);
    expect(dof.data?.fStop).toBeCloseTo(2.0, 5);

    const off = await blenderPost<{ useDof: boolean }>("/camera/set_dof", {
      objectName: name,
      useDof: false,
    });
    expect(off.ok).toBe(true);
    expect(off.data?.useDof).toBe(false);
  });

  it("camera_set_dof with focusObjectName attaches focus_object", async () => {
    const cam = await blenderPost<{ cameraObjectName: string }>("/camera/create", {
      name: "Cam_FocusObj",
    });
    expect(cam.ok).toBe(true);
    const camName = cam.data!.cameraObjectName;

    const target = await blenderPost("/object/create", { type: "CUBE", name: "FocusTarget" });
    expect(target.ok).toBe(true);

    const dof = await blenderPost<{ focusObjectName: string }>("/camera/set_dof", {
      objectName: camName,
      focusObjectName: "FocusTarget",
      fStop: 1.8,
    });
    expect(dof.ok).toBe(true);
    expect(dof.data?.focusObjectName).toBe("FocusTarget");
  });

  it("camera_set_dof rejects non-camera object", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "NotACam" });
    const dof = await blenderPost("/camera/set_dof", {
      objectName: "NotACam",
      fStop: 2.8,
    });
    expect(dof.ok).toBe(false);
    expect(dof.errorCode).toBe("INVALID_INPUT");
  });

  it("camera_set_clipping sets clipStart and clipEnd", async () => {
    const cam = await blenderPost<{ cameraObjectName: string }>("/camera/create", {
      name: "Cam_Clip",
    });
    expect(cam.ok).toBe(true);
    const name = cam.data!.cameraObjectName;

    const clip = await blenderPost<{ clipStart: number; clipEnd: number }>(
      "/camera/set_clipping",
      { objectName: name, clipStart: 0.05, clipEnd: 500 },
    );
    expect(clip.ok).toBe(true);
    expect(clip.data?.clipStart).toBeCloseTo(0.05, 5);
    expect(clip.data?.clipEnd).toBeCloseTo(500, 5);
  });

  it("camera_set_clipping rejects clipEnd <= clipStart", async () => {
    const cam = await blenderPost<{ cameraObjectName: string }>("/camera/create", {
      name: "Cam_BadClip",
    });
    expect(cam.ok).toBe(true);

    const clip = await blenderPost("/camera/set_clipping", {
      objectName: cam.data!.cameraObjectName,
      clipStart: 10,
      clipEnd: 5,
    });
    expect(clip.ok).toBe(false);
    expect(clip.errorCode).toBe("INVALID_INPUT");
  });

  it("camera_set_clipping requires at least one clip value", async () => {
    const cam = await blenderPost<{ cameraObjectName: string }>("/camera/create", {
      name: "Cam_NoClip",
    });
    expect(cam.ok).toBe(true);

    const clip = await blenderPost("/camera/set_clipping", {
      objectName: cam.data!.cameraObjectName,
    });
    expect(clip.ok).toBe(false);
    expect(clip.errorCode).toBe("INVALID_INPUT");
  });

  it("render_set_output configures filepath, format, color, frames, fps", async () => {
    const out = join(workDir, "out_");
    const res = await blenderPost<{
      filepath: string;
      fileFormat: string;
      colorMode: string;
      colorDepth: string;
      frameStart: number;
      frameEnd: number;
      fps: number;
    }>("/render/set_output", {
      filepath: out,
      fileFormat: "OPEN_EXR",
      colorMode: "RGBA",
      colorDepth: "32",
      frameStart: 5,
      frameEnd: 12,
      frameStep: 2,
      fps: 30,
    });
    expect(res.ok).toBe(true);
    expect(res.data?.filepath).toBe(out);
    expect(res.data?.fileFormat).toBe("OPEN_EXR");
    expect(res.data?.colorMode).toBe("RGBA");
    expect(res.data?.colorDepth).toBe("32");
    expect(res.data?.frameStart).toBe(5);
    expect(res.data?.frameEnd).toBe(12);
    expect(res.data?.fps).toBe(30);
  });

  it("render_set_output rejects unknown fileFormat", async () => {
    const res = await blenderPost("/render/set_output", { fileFormat: "NOT_A_FORMAT" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("compositor_set_node_property toggles mute on a compositor node", async () => {
    await blenderPost("/compositor/enable", {});
    await blenderPost("/compositor/add_node", {
      type: "CompositorNodeBrightContrast",
      name: "BC_Mute",
    });

    const on = await blenderPost<{ propertyValue: boolean }>(
      "/compositor/set_node_property",
      { nodeName: "BC_Mute", propertyName: "mute", propertyValue: true },
    );
    expect(on.ok).toBe(true);
    expect(on.data?.propertyValue).toBe(true);

    const off = await blenderPost<{ propertyValue: boolean }>(
      "/compositor/set_node_property",
      { nodeName: "BC_Mute", propertyName: "mute", propertyValue: false },
    );
    expect(off.ok).toBe(true);
    expect(off.data?.propertyValue).toBe(false);
  });

  it("compositor_set_node_property errors on missing node", async () => {
    await blenderPost("/compositor/enable", {});
    const res = await blenderPost("/compositor/set_node_property", {
      nodeName: "DoesNotExist",
      propertyName: "mute",
      propertyValue: true,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("NODE_NOT_FOUND");
  });

  it("compositor_set_node_property errors on missing property", async () => {
    await blenderPost("/compositor/enable", {});
    await blenderPost("/compositor/add_node", {
      type: "CompositorNodeBrightContrast",
      name: "BC_BadProp",
    });
    const res = await blenderPost("/compositor/set_node_property", {
      nodeName: "BC_BadProp",
      propertyName: "totally_not_real",
      propertyValue: 1,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("compositor_set_node_input sets Saturation on HueSat", async () => {
    await blenderPost("/compositor/enable", {});
    await blenderPost("/compositor/add_node", {
      type: "CompositorNodeHueSat",
      name: "HS_Sat",
    });
    const res = await blenderPost("/compositor/set_node_input", {
      nodeName: "HS_Sat",
      inputName: "Saturation",
      value: 0.75,
    });
    expect(res.ok).toBe(true);
  });

  it("compositor_set_node_input errors on unknown socket", async () => {
    await blenderPost("/compositor/enable", {});
    await blenderPost("/compositor/add_node", {
      type: "CompositorNodeHueSat",
      name: "HS_BadInput",
    });
    const res = await blenderPost("/compositor/set_node_input", {
      nodeName: "HS_BadInput",
      inputName: "NotARealSocket",
      value: 1.0,
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
