import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("animation + keyframes + NLA (B6)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/object/create", { type: "CUBE", name: "AnimCube" });
    await blenderPost("/action/create", { name: "Bounce" });
    await blenderPost("/action/assign_to_object", {
      objectName: "AnimCube",
      actionName: "Bounce",
    });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("inserts keyframes at frames 1 and 30", async () => {
    const k1 = await blenderPost("/keyframe/add", {
      objectName: "AnimCube",
      dataPath: "location",
      frame: 1,
    });
    expect(k1.ok).toBe(true);

    const k2 = await blenderPost("/keyframe/add", {
      objectName: "AnimCube",
      dataPath: "location",
      frame: 30,
    });
    expect(k2.ok).toBe(true);
  });

  it("pushes the active action onto an NLA track", async () => {
    const res = await blenderPost<{ trackName: string; actionName: string }>(
      "/nla/push_action_to_strip",
      { objectName: "AnimCube", trackName: "BounceTrack" },
    );
    expect(res.ok).toBe(true);
    expect(res.refs?.actionName).toBe("Bounce");
  });

  it("sets scene frame range", async () => {
    const res = await blenderPost<{ frameStart: number; frameEnd: number }>(
      "/scene/set_frame_range",
      { frameStart: 1, frameEnd: 60 },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.frameStart).toBe(1);
    expect(res.data?.frameEnd).toBe(60);
  });
});
