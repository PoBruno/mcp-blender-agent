/**
 * Raw Python exec — disabled unless BLENDER_AGENT_ALLOW_EXEC_PYTHON=1 (ADR-008).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { passthroughGet, passthroughPost, registerTools } from "../tool-helpers.js";

export function registerExecTools(server: McpServer): void {
  registerTools(server, [
    {
      name: "exec_python",
      description:
        "Execute an arbitrary Python snippet inside Blender. DISABLED by default — requires BLENDER_AGENT_ALLOW_EXEC_PYTHON=1 set BEFORE Blender starts.",
      inputSchema: {
        code: z.string().min(1).describe("Python source. Set `_result = ...` to return data."),
      },
      handler: passthroughPost("/exec/python"),
    },
    {
      name: "exec_status",
      description: "Return whether exec_python is currently enabled and the running Python version.",
      inputSchema: {},
      handler: passthroughGet("/exec/status"),
    },
  ]);
}
