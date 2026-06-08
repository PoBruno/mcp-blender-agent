import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

/**
 * Recipe 3 — metahuman_face_blendshapes_setup
 *
 * Chain:
 *   create face mesh -> ensure all 52 ARKit shape keys
 *   -> idempotent re-run -> set a few values -> assert
 */
describe("Recipe 3 — metahuman_face_blendshapes_setup", () => {
  beforeAll(async () => {
    await startBlender();
  }, 120_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("sets up a full ARKit-52 face rig idempotently", async () => {
    const head = await blenderPost("/object/create", {
      type: "PLANE",
      name: "FaceMesh",
      size: 1,
    });
    expect(head.ok).toBe(true);

    const list = await blenderPost<{ blendshapes: string[]; count: number }>(
      "/metahuman/arkit52_list",
      {},
    );
    expect(list.data?.count).toBe(52);

    const first = await blenderPost<{ createdCount: number; existingCount: number }>(
      "/metahuman/ensure_arkit52_shape_keys",
      { objectName: "FaceMesh" },
    );
    expect(first.ok).toBe(true);
    expect(first.data?.createdCount).toBe(52);
    expect(first.data?.existingCount).toBe(0);

    const second = await blenderPost<{ createdCount: number; existingCount: number }>(
      "/metahuman/ensure_arkit52_shape_keys",
      { objectName: "FaceMesh" },
    );
    expect(second.ok).toBe(true);
    expect(second.data?.createdCount).toBe(0);
    expect(second.data?.existingCount).toBe(52);

    const expressions: Record<string, number> = {
      jawOpen: 0.7,
      eyeBlinkLeft: 1.0,
      browInnerUp: 0.4,
      mouthSmileLeft: 0.6,
    };
    for (const [shape, value] of Object.entries(expressions)) {
      const set = await blenderPost<{ value: number }>("/shape_key/set_value", {
        objectName: "FaceMesh",
        shapeKeyName: shape,
        value,
      });
      expect(set.ok, `set ${shape}`).toBe(true);
      expect(set.data?.value).toBeCloseTo(value, 3);
    }
  }, 120_000);
});
