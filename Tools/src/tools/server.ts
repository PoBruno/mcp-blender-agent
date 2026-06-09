/**
 * server_status, server_handlers, server_shutdown — Sprint 0 baseline.
 * blender_launch / blender_quit / addon_restart — lifecycle control so the
 * agent can guarantee an open Blender instead of failing on BLENDER_UNREACHABLE.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { blenderGet, launchBlenderGui } from "../blender-bridge.js";
import type { ToolResult } from "../types.js";
import { passthroughGet, passthroughPost, registerTools } from "../tool-helpers.js";

export function registerServerTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "server_status",
      description:
        "Return BlenderAgent runtime status: Blender version, active scene, mode, exec-python flag.",
      inputSchema: {},
      handler: passthroughGet("/server/status"),
    },
    {
      name: "server_handlers",
      description: "List all registered handler routes inside the BlenderAgent addon.",
      inputSchema: {},
      handler: passthroughGet("/server/handlers"),
    },
    {
      name: "server_shutdown",
      description: "Shut the BlenderAgent HTTP server down. Used by tests on teardown.",
      inputSchema: {},
      handler: passthroughPost("/server/shutdown"),
    },
    {
      name: "blender_launch",
      description:
        "Ensure a GUI Blender is running with the addon online. Reuses an already-open instance if one is reachable, otherwise launches Blender from the default install path (real window, not headless). Call this FIRST before any modeling so tool calls don't fail with BLENDER_UNREACHABLE, and so viewport snapshots work.",
      inputSchema: {
        blendFile: z
          .string()
          .optional()
          .describe("Optional .blend file to open on launch. Omit for a fresh scene."),
        timeoutMs: z
          .number()
          .int()
          .positive()
          .optional()
          .describe("How long to wait for Blender to come online. Default 60000."),
      },
      handler: async (args): Promise<ToolResult> => {
        const { alreadyRunning, binary } = await launchBlenderGui({
          blendFile: args.blendFile,
          timeoutMs: args.timeoutMs,
        });
        const status = await blenderGet<Record<string, unknown>>("/server/status");
        return {
          ok: true,
          data: { alreadyRunning, binary, status: status.data },
          refs: status.refs,
          nextSteps: alreadyRunning
            ? ["reused the running Blender — proceed with modeling tools"]
            : ["Blender launched and online — proceed with modeling tools"],
        };
      },
    },
    {
      name: "blender_quit",
      description:
        "Quit the host Blender process (optionally saving to a .blend first). After this Blender is gone — call blender_launch to bring it back. Use to recover a wedged session or free resources.",
      inputSchema: {
        saveAs: z
          .string()
          .optional()
          .describe("Optional .blend path to save before quitting."),
        delay: z
          .number()
          .positive()
          .optional()
          .describe("Seconds to wait before quitting so the HTTP response is sent first. Default 0.5."),
      },
      handler: passthroughPost("/server/blender_quit"),
    },
    {
      name: "addon_restart",
      description:
        "Disable + re-enable the BlenderAgent addon inside the running Blender to reload handler/operator/property registration without quitting Blender. Heavier than a handler-only reload; use after updating addon code.",
      inputSchema: {
        delay: z
          .number()
          .positive()
          .optional()
          .describe("Seconds before the restart fires so the HTTP response is sent first. Default 0.5."),
      },
      handler: passthroughPost("/server/addon_restart"),
    },
    {
      name: "batch",
      description:
        "Run many tool calls in ONE request — executes sequentially inside a single Blender main-thread job (no per-op round-trip, not interleaved with other requests). Use for multi-part builds (a chair, a character) to cut latency. Each op = {path: '/object/create', body: {...}}. Returns per-op results; stops at the first failure unless stopOnError=false.",
      inputSchema: {
        ops: z
          .array(
            z.object({
              path: z.string().describe("Handler route, e.g. '/object/create'."),
              method: z.enum(["POST", "GET"]).optional().describe("Default POST."),
              body: z.record(z.unknown()).optional().describe("Body for that op."),
            }),
          )
          .min(1)
          .describe("Ordered list of tool calls."),
        stopOnError: z.boolean().optional().describe("Stop at first failing op (default true)."),
      },
      handler: passthroughPost("/batch", { timeoutMs: 900_000 }),
    },
  ]);
}
