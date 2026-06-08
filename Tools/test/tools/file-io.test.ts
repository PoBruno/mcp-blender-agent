import { tmpdir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdtempSync, rmSync } from "node:fs";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

let workDir = "";

describe("file IO — save / open / append (B9.E)", () => {
  beforeAll(async () => {
    await startBlender();
    workDir = mkdtempSync(join(tmpdir(), "blender-agent-fileio-"));
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
    if (workDir && existsSync(workDir)) rmSync(workDir, { recursive: true, force: true });
  });

  it("saves the file to a new path and re-opens it", async () => {
    await blenderPost("/object/create", { type: "CUBE", name: "Persistent" });

    const filepath = join(workDir, "scene.blend");
    const save = await blenderPost("/file/save_as", { filepath });
    expect(save.ok).toBe(true);
    expect(existsSync(filepath)).toBe(true);

    const open = await blenderPost("/file/open", { filepath });
    expect(open.ok).toBe(true);
  });

  it("rejects /file/open on a missing path with INVALID_INPUT", async () => {
    const res = await blenderPost("/file/open", {
      filepath: join(workDir, "does-not-exist.blend"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
