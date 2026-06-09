import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { assertStatus, blenderGet, startBlender, stopBlender } from "../bootstrap.js";

describe("server_status", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("responds with ok=true and Blender 4.2+ version (4.x or 5.x)", async () => {
    await assertStatus();
    const res = await blenderGet<{
      version: string;
      versionTuple: number[];
      addonVersion: number[];
      mode: string;
    }>("/server/status");
    expect(res.ok).toBe(true);
    expect(res.data?.version).toMatch(/^(4|5)\./);
    const v = res.data?.versionTuple ?? [0, 0, 0];
    const supported = v[0] > 4 || (v[0] === 4 && v[1] >= 2);
    expect(supported, `Blender ${v.join(".")} below required 4.2`).toBe(true);
  });

  it("lists registered handlers", async () => {
    const res = await blenderGet<{ handlers: string[] }>("/server/handlers");
    expect(res.ok).toBe(true);
    const handlers = res.data?.handlers ?? [];
    expect(handlers).toContain("GET /server/status");
    expect(handlers).toContain("POST /scene/create");
    expect(handlers).toContain("POST /object/create");
    expect(handlers).toContain("POST /export/fbx_static");
  });
});
