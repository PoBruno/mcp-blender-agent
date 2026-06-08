import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("exec_python — DISABLED unless env flag set (ADR-008)", () => {
  beforeAll(async () => {
    await startBlender();
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("returns disabled status by default", async () => {
    const res = await blenderPost<{ execPythonAllowed: boolean }>("/exec/status", {});
    expect(res.ok).toBe(true);
    expect(res.data?.execPythonAllowed).toBe(false);
  });

  it("rejects /exec/python with EXEC_PYTHON_DISABLED when not enabled", async () => {
    const res = await blenderPost("/exec/python", { code: "_result = 1+1" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("EXEC_PYTHON_DISABLED");
  });
});
