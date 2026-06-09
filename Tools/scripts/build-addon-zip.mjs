#!/usr/bin/env node
/**
 * Build the prepack assets for @pobruno/blender-agent:
 *
 *   1. Tools/assets/BlenderAgent.zip   — built from ../BlenderAgent/
 *   2. Tools/LICENSE                   — copied from the repo root
 *   3. Tools/skill/*.md                — copied from ../install/context-skill/
 *                                         so the install harness can find them
 *                                         via `blender-agent --print-skill-dir`
 *                                         without needing the source repo.
 *
 * The zip layout must put BlenderAgent/__init__.py at the top level, because
 * that's what Blender's Add-on installer expects.
 *
 * Runs cross-platform without adding a runtime/dev dependency: shells out to
 * PowerShell's Compress-Archive on Windows and to system `zip` on macOS/Linux.
 */

import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  rmSync,
  statSync,
} from "node:fs";
import { spawnSync } from "node:child_process";
import { platform } from "node:os";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const toolsRoot = resolve(__dirname, "..");
const repoRoot = resolve(toolsRoot, "..");

const addonSource = resolve(repoRoot, "BlenderAgent");
const assetsDir = resolve(toolsRoot, "assets");
const zipPath = resolve(assetsDir, "BlenderAgent.zip");
const licenseSource = resolve(repoRoot, "LICENSE");
const licenseDest = resolve(toolsRoot, "LICENSE");
const skillSource = resolve(repoRoot, "install", "context-skill");
const skillDest = resolve(toolsRoot, "skill");

if (!existsSync(addonSource) || !statSync(addonSource).isDirectory()) {
  console.error(`Addon source not found at ${addonSource}.`);
  process.exit(1);
}

if (!existsSync(resolve(addonSource, "__init__.py"))) {
  console.error(
    `Addon source ${addonSource} does not contain __init__.py — refusing to zip a non-addon folder.`
  );
  process.exit(1);
}

mkdirSync(assetsDir, { recursive: true });
if (existsSync(zipPath)) rmSync(zipPath, { force: true });

const isWindows = platform() === "win32";
let result;

if (isWindows) {
  const ps = [
    "Compress-Archive",
    "-Path",
    `"${addonSource}"`,
    "-DestinationPath",
    `"${zipPath}"`,
    "-Force",
  ].join(" ");
  result = spawnSync("powershell.exe", ["-NoProfile", "-Command", ps], {
    stdio: "inherit",
  });
} else {
  result = spawnSync(
    "zip",
    ["-r", zipPath, "BlenderAgent", "-x", "*/__pycache__/*", "*/.DS_Store"],
    { cwd: repoRoot, stdio: "inherit" }
  );
}

if (result.status !== 0) {
  console.error(`Zip command exited with status ${result.status}.`);
  process.exit(result.status ?? 1);
}

if (!existsSync(zipPath)) {
  console.error(`Zip command succeeded but ${zipPath} was not produced.`);
  process.exit(1);
}

const { size } = statSync(zipPath);
console.log(`Wrote ${zipPath} (${size} bytes).`);

if (existsSync(licenseSource)) {
  copyFileSync(licenseSource, licenseDest);
  console.log(`Copied ${licenseSource} -> ${licenseDest}.`);
} else {
  console.warn(
    `LICENSE not found at ${licenseSource}; the published tarball will be missing one.`
  );
}

if (existsSync(skillSource) && statSync(skillSource).isDirectory()) {
  if (existsSync(skillDest)) rmSync(skillDest, { recursive: true, force: true });
  mkdirSync(skillDest, { recursive: true });
  const files = readdirSync(skillSource).filter((f) => f.endsWith(".md"));
  for (const f of files) {
    copyFileSync(join(skillSource, f), join(skillDest, f));
  }
  console.log(
    `Copied ${files.length} skill files from ${skillSource} -> ${skillDest}.`
  );
} else {
  console.warn(
    `Skill source not found at ${skillSource}; the install harness will need an alternate fetch path.`
  );
}
