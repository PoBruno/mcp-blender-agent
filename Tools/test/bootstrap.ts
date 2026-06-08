/**
 * Test bootstrap — spawns headless Blender 4.2+ (5.x recommended) with the BlenderAgent addon.
 *
 * Used by every integration test via beforeAll/afterAll.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { blenderGet, blenderPost, findBlenderBinary, isBlenderReachable } from "../src/blender-bridge.js";

let proc: ChildProcess | null = null;

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function repoRoot(): string {
  return resolve(__dirname, "..", "..");
}

export async function startBlender(opts?: { timeoutMs?: number }): Promise<void> {
  if (await isBlenderReachable()) return;
  const bin = findBlenderBinary();
  if (!bin) {
    throw new Error(
      "Blender binary not found. Set BLENDER_BIN env var or install Blender 4.2+.\n" +
        "On Windows the default install path is checked automatically.",
    );
  }
  const addonRoot = repoRoot();
  const pyCode = [
    "import sys",
    `sys.path.insert(0, r"${addonRoot}")`,
    "import BlenderAgent",
    "BlenderAgent.serve_blocking()",
  ].join("\n");

  proc = spawn(bin, ["--background", "--python-expr", pyCode], {
    env: { ...process.env, BLENDER_AGENT_PORT: process.env.BLENDER_PORT ?? "9877" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  proc.stderr?.on("data", (b) => process.stderr.write(`[blender] ${b}`));
  proc.stdout?.on("data", (b) => process.stdout.write(`[blender] ${b}`));

  const timeoutMs = opts?.timeoutMs ?? 60_000;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await isBlenderReachable()) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  await stopBlender();
  throw new Error(`Headless Blender did not respond within ${timeoutMs}ms`);
}

export async function stopBlender(): Promise<void> {
  try {
    await blenderPost("/server/shutdown", {});
  } catch {
    // ignore
  }
  if (proc) {
    try {
      proc.kill();
    } catch {
      // ignore
    }
    proc = null;
  }
}

export { blenderGet, blenderPost };

/** Quickly assert Blender is healthy — usable inside tests. */
export async function assertStatus(): Promise<void> {
  const res = await blenderGet<{ version: string }>("/server/status");
  if (!res.ok) {
    throw new Error(`server/status returned ok=false: ${JSON.stringify(res)}`);
  }
}
