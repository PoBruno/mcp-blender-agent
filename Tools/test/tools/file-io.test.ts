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

  it("appends an Object, links it into the scene and returns its name", async () => {
    await blenderPost("/file/new", { empty: true });
    await blenderPost("/object/create", { type: "CUBE", name: "AppendDonor" });
    const donorPath = join(workDir, "donor.blend");
    expect((await blenderPost("/file/save_as", { filepath: donorPath })).ok).toBe(true);

    await blenderPost("/file/new", { empty: true });
    const res = await blenderPost("/file/append_data", {
      filepath: donorPath,
      datablockType: "Object",
      names: ["AppendDonor"],
    });
    expect(res.ok).toBe(true);
    expect(res.data.appended).toEqual(["AppendDonor"]);
    expect(res.refs.objectNames).toEqual(["AppendDonor"]);

    const list = await blenderPost("/object/list", { namePattern: "AppendDonor" });
    expect(list.data.count).toBe(1);
    expect(list.data.objects[0].collections.length).toBeGreaterThan(0);
  });

  it("rejects /file/open on a missing path with INVALID_INPUT", async () => {
    const res = await blenderPost("/file/open", {
      filepath: join(workDir, "does-not-exist.blend"),
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
