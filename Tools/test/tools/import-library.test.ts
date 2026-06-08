import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { mkdtempSync, existsSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir: string;

const MINIMAL_OBJ_CUBE = `# minimal cube
v -1 -1 -1
v 1 -1 -1
v 1 1 -1
v -1 1 -1
v -1 -1 1
v 1 -1 1
v 1 1 1
v -1 1 1
f 1 2 3 4
f 5 8 7 6
f 1 5 6 2
f 2 6 7 3
f 3 7 8 4
f 4 8 5 1
`;

describe("OBJ + glTF import (and library/* error paths)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-imp-"));
    await blenderPost("/object/create", { type: "CUBE", name: "ExpStatic", size: 1 });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) {
      rmSync(workDir, { recursive: true, force: true });
    }
  });

  it("imports a hand-written minimal OBJ", async () => {
    const out = join(workDir, "static.obj");
    writeFileSync(out, MINIMAL_OBJ_CUBE);

    const res = await blenderPost<{ importedObjects: string[] }>("/import/obj", {
      filepath: out,
    });
    expect(res.ok).toBe(true);
    expect((res.data?.importedObjects ?? []).length).toBeGreaterThan(0);
  });

  it("round-trips glTF via /export/gltf then /import/gltf", async () => {
    const out = join(workDir, "scene.glb");
    const exp = await blenderPost("/export/gltf", {
      filepath: out,
      objectNames: ["ExpStatic"],
      exportFormat: "GLB",
    });
    expect(exp.ok).toBe(true);
    expect(existsSync(out)).toBe(true);

    const res = await blenderPost<{ importedObjects: string[] }>("/import/gltf", {
      filepath: out,
    });
    expect(res.ok).toBe(true);
    expect((res.data?.importedObjects ?? []).length).toBeGreaterThan(0);
  });

  it("rejects /import/obj with missing file", async () => {
    const res = await blenderPost("/import/obj", {
      filepath: join(workDir, "nope.obj"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("rejects /import/gltf with missing file", async () => {
    const res = await blenderPost("/import/gltf", {
      filepath: join(workDir, "nope.glb"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("rejects /library/link with missing file (INVALID_INPUT)", async () => {
    const res = await blenderPost("/library/link", {
      filepath: join(workDir, "nope.blend"),
      datablockType: "Object",
      names: ["X"],
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("rejects /library/make_override on a non-linked object", async () => {
    const res = await blenderPost("/library/make_override", { objectName: "ExpStatic" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("rejects /library/reload for an unknown library", async () => {
    const res = await blenderPost("/library/reload", {
      filepath: join(workDir, "no_such_lib.blend"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });

  it("rejects /library/make_override with no objectName", async () => {
    const res = await blenderPost("/library/make_override", {});
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
