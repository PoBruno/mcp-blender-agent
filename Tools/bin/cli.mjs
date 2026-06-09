#!/usr/bin/env node
/**
 * blender-agent CLI entry.
 *
 * Modes:
 *
 *   blender-agent                       → boot the MCP server over stdio (default)
 *   blender-agent --print-addon-zip     → print the absolute path of the bundled
 *                                          BlenderAgent.zip so the user can install
 *                                          it via Blender's Add-ons UI
 *   blender-agent --print-skill-dir     → print the absolute path of the bundled
 *                                          context-skill directory so the install
 *                                          harness can copy the SKILL/FLOWS/TOOLS
 *                                          markdown into the user's harness
 *   blender-agent --version             → print the package version
 *   blender-agent --help                → usage
 *
 * The MCP server itself lives at ../dist/index.js. This file exists only to make
 * `npx @pobruno/blender-agent --print-addon-zip` a one-liner end users (and their
 * AI agents) can call without booting the MCP transport first.
 */

import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, resolve } from "node:path";
import { existsSync, readFileSync } from "node:fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageRoot = resolve(__dirname, "..");

const args = process.argv.slice(2);
const flag = args[0];

function printVersion() {
  const pkg = JSON.parse(readFileSync(resolve(packageRoot, "package.json"), "utf8"));
  process.stdout.write(`${pkg.version}\n`);
}

function printHelp() {
  process.stdout.write(
    [
      "blender-agent — MCP server for Blender 4.2 LTS+",
      "",
      "Usage:",
      "  blender-agent                       Boot the MCP server over stdio (default).",
      "                                       Intended to be invoked by your agent harness",
      "                                       via its MCP config (Claude Code, Copilot, etc.).",
      "",
      "  blender-agent --print-addon-zip     Print the absolute path of the bundled",
      "                                       BlenderAgent.zip so you can install it via",
      "                                       Blender's Edit → Preferences → Add-ons → Install...",
      "",
      "  blender-agent --print-skill-dir     Print the absolute path of the bundled",
      "                                       context-skill directory (SKILL.md, FLOWS.md,",
      "                                       TOOLS.md, MANAGED-BLOCK.md, instructions.md).",
      "                                       Used by install/AGENT-INSTALL.md when injecting",
      "                                       the passive Blender context into your harness.",
      "",
      "  blender-agent --version             Print the package version.",
      "  blender-agent --help                Show this message.",
      "",
      "Repo: https://github.com/PoBruno/mcp-blender-agent",
    ].join("\n") + "\n"
  );
}

function printAddonZipPath() {
  const zipPath = resolve(packageRoot, "assets", "BlenderAgent.zip");
  if (!existsSync(zipPath)) {
    process.stderr.write(
      `BlenderAgent.zip not found at ${zipPath}.\n` +
        `If you are running from source, run 'npm run build:addon-zip' inside the Tools/ directory first.\n`
    );
    process.exit(2);
  }
  process.stdout.write(`${zipPath}\n`);
}

function printSkillDir() {
  const skillDir = resolve(packageRoot, "skill");
  if (!existsSync(skillDir)) {
    process.stderr.write(
      `Skill directory not found at ${skillDir}.\n` +
        `If you are running from source, run 'npm run build:addon-zip' inside the Tools/ directory first.\n`
    );
    process.exit(2);
  }
  process.stdout.write(`${skillDir}\n`);
}

async function runServer() {
  // Delegate to the compiled MCP server entry. Keep this dynamic so --print-addon-zip
  // doesn't pay the SDK import cost. Wrap in pathToFileURL — on Windows the ESM loader
  // refuses bare absolute paths (D:\...) and requires a file:// URL.
  const entry = pathToFileURL(resolve(packageRoot, "dist", "index.js")).href;
  await import(entry);
}

switch (flag) {
  case undefined:
  case "":
    await runServer();
    break;
  case "--print-addon-zip":
  case "--addon-zip":
    printAddonZipPath();
    break;
  case "--print-skill-dir":
  case "--skill-dir":
    printSkillDir();
    break;
  case "--version":
  case "-v":
    printVersion();
    break;
  case "--help":
  case "-h":
    printHelp();
    break;
  default:
    process.stderr.write(`Unknown flag: ${flag}\n\n`);
    printHelp();
    process.exit(64);
}
