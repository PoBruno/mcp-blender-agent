/**
 * server_status, server_handlers, server_shutdown — Sprint 0 baseline.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

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
  ]);
}
