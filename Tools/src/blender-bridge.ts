/**
 * HTTP bridge from the MCP server to the BlenderAgent Python addon.
 *
 * Handles snake_case ↔ camelCase translation, headless Blender spawn,
 * and surfaces typed errors when Blender isn't reachable.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { platform } from "node:os";
import { resolve } from "node:path";

import type { BlenderResponse } from "./types.js";

const DEFAULT_PORT = Number(process.env.BLENDER_PORT ?? process.env.BLENDER_AGENT_PORT ?? 9877);
const DEFAULT_HOST = process.env.BLENDER_HOST ?? "127.0.0.1";
const DEFAULT_TIMEOUT_MS = Number(process.env.BLENDER_TIMEOUT_MS ?? 60_000);

let headlessProcess: ChildProcess | null = null;
let guiProcess: ChildProcess | null = null;

function baseUrl(): string {
  return `http://${DEFAULT_HOST}:${DEFAULT_PORT}`;
}

export class BlenderBridgeError extends Error {
  readonly errorCode: string;
  readonly status?: number;
  readonly body?: unknown;
  constructor(message: string, errorCode: string, status?: number, body?: unknown) {
    super(message);
    this.name = "BlenderBridgeError";
    this.errorCode = errorCode;
    this.status = status;
    this.body = body;
  }
}

async function request<T>(
  method: "GET" | "POST",
  path: string,
  body?: unknown,
  timeoutMs?: number,
): Promise<BlenderResponse<T>> {
  const url = `${baseUrl()}${path}`;
  const controller = new AbortController();
  const effectiveTimeout = timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeoutHandle = setTimeout(() => controller.abort(), effectiveTimeout);
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutHandle);
    if ((err as Error).name === "AbortError") {
      throw new BlenderBridgeError(
        `Request to Blender timed out after ${effectiveTimeout}ms`,
        "BLENDER_TIMEOUT",
      );
    }
    throw new BlenderBridgeError(
      `Cannot reach Blender at ${url}: ${(err as Error).message}`,
      "BLENDER_UNREACHABLE",
    );
  }
  clearTimeout(timeoutHandle);

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new BlenderBridgeError(
      `Blender response was not JSON (status ${response.status})`,
      "INVALID_RESPONSE",
      response.status,
    );
  }
  if (!response.ok) {
    // If the response is a structured ToolResult ({ok:false, errorCode, message}),
    // return it as-is so the caller can branch on errorCode. Throw only when the
    // body is not the expected shape (raw error string, empty body, etc.).
    const obj = payload as { ok?: boolean; errorCode?: string; message?: string };
    if (obj && typeof obj === "object" && obj.ok === false && typeof obj.errorCode === "string") {
      return payload as BlenderResponse<T>;
    }
    throw new BlenderBridgeError(
      obj?.message ?? `Blender returned ${response.status}`,
      obj?.errorCode ?? `HTTP_${response.status}`,
      response.status,
      payload,
    );
  }
  return payload as BlenderResponse<T>;
}

export async function blenderGet<T>(path: string, timeoutMs?: number): Promise<BlenderResponse<T>> {
  return request<T>("GET", path, undefined, timeoutMs);
}

export async function blenderPost<T>(
  path: string,
  body: Record<string, unknown> = {},
  timeoutMs?: number,
): Promise<BlenderResponse<T>> {
  return request<T>("POST", path, body, timeoutMs);
}

export async function isBlenderReachable(): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl()}/server/status`);
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Locate the Blender executable for headless spawn.
 *
 * Order: BLENDER_BIN env, PATH (`blender`), well-known install paths per OS.
 */
export function findBlenderBinary(): string | null {
  const envBin = process.env.BLENDER_BIN;
  if (envBin && existsSync(envBin)) return resolve(envBin);

  const candidates: string[] = [];
  const os = platform();
  if (os === "win32") {
    candidates.push(
      "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe",
      "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe",
      "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe",
      "C:\\Program Files\\Blender Foundation\\Blender 4.4\\blender.exe",
      "C:\\Program Files\\Blender Foundation\\Blender 4.3\\blender.exe",
      "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
      "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Blender\\blender.exe",
    );
  } else if (os === "darwin") {
    candidates.push("/Applications/Blender.app/Contents/MacOS/Blender");
  } else {
    candidates.push("/usr/bin/blender", "/usr/local/bin/blender", "/opt/blender/blender");
  }
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  return null;
}

export async function ensureBlenderRunning(opts?: { timeoutMs?: number }): Promise<void> {
  if (await isBlenderReachable()) return;
  const bin = findBlenderBinary();
  if (!bin) {
    throw new BlenderBridgeError(
      "Blender not reachable and no executable found. Set BLENDER_BIN or install Blender 4.2+ (5.x recommended).",
      "BLENDER_NOT_FOUND",
    );
  }

  const addonPath = resolve(process.cwd(), "..", "BlenderAgent");
  const args = [
    "--background",
    "--python-expr",
    "import sys, importlib, importlib.util\n" +
      `sys.path.insert(0, r"${resolve(process.cwd(), "..")}")\n` +
      "import BlenderAgent\nBlenderAgent.serve_blocking()\n",
  ];
  headlessProcess = spawn(bin, args, {
    env: { ...process.env, BLENDER_AGENT_ADDON_PATH: addonPath },
    stdio: ["ignore", "pipe", "pipe"],
    detached: false,
  });
  headlessProcess.stderr?.on("data", (chunk) => console.error("[blender]", String(chunk).trimEnd()));

  const timeoutMs = opts?.timeoutMs ?? 30_000;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await isBlenderReachable()) return;
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new BlenderBridgeError(
    `Headless Blender did not respond within ${timeoutMs}ms`,
    "BLENDER_TIMEOUT",
  );
}

/**
 * Bootstrap snippet run by a freshly spawned GUI Blender. Tries to enable an
 * installed BlenderAgent addon; if it isn't installed, injects the repo onto
 * sys.path and registers it directly. `register()` is idempotent (server.start
 * no-ops if already running) so the double path is safe.
 */
function guiBootstrap(): string {
  return [
    "import sys, os, importlib.util",
    "repo = os.environ.get('BLENDER_AGENT_REPO')",
    "import bpy",
    "try:",
    "    bpy.ops.preferences.addon_enable(module='BlenderAgent')",
    "except Exception:",
    "    pass",
    "if importlib.util.find_spec('BlenderAgent') is None and repo:",
    "    sys.path.insert(0, repo)",
    "try:",
    "    import BlenderAgent",
    "    BlenderAgent.register()",
    "except Exception as exc:",
    "    print('BlenderAgent bootstrap failed:', exc)",
  ].join("\n");
}

/**
 * Ensure a GUI Blender is running with the addon online. Idempotent — if one is
 * already reachable on the port it is reused (the "use the open Blender" path).
 * Otherwise spawns Blender from the default path (no --background, real window)
 * and waits for the HTTP server to come up.
 */
export async function launchBlenderGui(
  opts?: { timeoutMs?: number; blendFile?: string },
): Promise<{ alreadyRunning: boolean; binary?: string }> {
  if (await isBlenderReachable()) return { alreadyRunning: true };

  const bin = findBlenderBinary();
  if (!bin) {
    throw new BlenderBridgeError(
      "Blender not reachable and no executable found. Set BLENDER_BIN or install Blender 4.2+ (5.x recommended).",
      "BLENDER_NOT_FOUND",
    );
  }

  const repo = process.env.BLENDER_AGENT_REPO ?? resolve(process.cwd(), "..");
  const args: string[] = [];
  if (opts?.blendFile) args.push(opts.blendFile);
  args.push("--python-expr", guiBootstrap());

  guiProcess = spawn(bin, args, {
    env: { ...process.env, BLENDER_AGENT_REPO: repo, BLENDER_AGENT_PORT: String(DEFAULT_PORT) },
    stdio: "ignore",
    detached: true,
  });
  guiProcess.unref();

  const timeoutMs = opts?.timeoutMs ?? 60_000;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await isBlenderReachable()) return { alreadyRunning: false, binary: bin };
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new BlenderBridgeError(
    `GUI Blender was spawned but did not come online within ${timeoutMs}ms`,
    "BLENDER_TIMEOUT",
  );
}

export async function shutdownHeadlessBlender(): Promise<void> {
  if (!headlessProcess) return;
  try {
    await blenderPost("/server/shutdown", {});
  } catch {
    // ignore
  }
  try {
    headlessProcess.kill();
  } catch {
    // ignore
  }
  headlessProcess = null;
}
