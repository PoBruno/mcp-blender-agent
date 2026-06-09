/**
 * Helpers shared by every tool registration file.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { blenderGet, blenderPost, BlenderBridgeError } from "./blender-bridge.js";
import type { ToolResult } from "./types.js";

export type ToolHandler<TArgs> = (args: TArgs) => Promise<ToolResult>;

type McpCallContent = { type: "text"; text: string };
type McpCallResult = {
  [x: string]: unknown;
  content: McpCallContent[];
  isError?: boolean;
};

/** Convert a ToolResult into the MCP content payload. */
export function toMcpResult(result: ToolResult): McpCallResult {
  return {
    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    isError: !result.ok,
  };
}

/** Catch BlenderBridgeError + unknown errors and return a structured ToolResult. */
export async function safe<TArgs>(args: TArgs, fn: ToolHandler<TArgs>): Promise<ReturnType<typeof toMcpResult>> {
  try {
    const result = await fn(args);
    return toMcpResult(result);
  } catch (err) {
    if (err instanceof BlenderBridgeError) {
      return toMcpResult({
        ok: false,
        errorCode: err.errorCode,
        message: err.message,
        warnings: [],
      });
    }
    return toMcpResult({
      ok: false,
      errorCode: "INTERNAL_ERROR",
      message: (err as Error).message,
    });
  }
}

/** Compact tool definition consumed by `registerTools`. */
export interface ToolDef<Shape extends z.ZodRawShape> {
  name: string;
  description: string;
  inputSchema: Shape;
  handler: (args: z.infer<z.ZodObject<Shape>>) => Promise<ToolResult>;
}

/** Register an array of ToolDef on an McpServer. */
export function registerTools<Shape extends z.ZodRawShape>(
  server: McpServer,
  tools: ToolDef<Shape>[],
): void {
  for (const t of tools) {
    // The SDK's tool() callback inference is too strict for our generic helper;
    // we already produce a fully-compatible CallToolResult shape from `safe()`,
    // so we cast the callback to the SDK's expected signature.
    const cb = async (args: z.infer<z.ZodObject<Shape>>): Promise<McpCallResult> =>
      safe(args, t.handler);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (server.tool as any)(t.name, t.description, t.inputSchema, cb);
  }
}

/** Convenience for "POST /<path>" forwarding tools.
 *
 * `opts.timeoutMs` overrides the bridge's default HTTP timeout — set it for
 * tools that wrap a heavy main-thread op (render, bake, remesh) so the client
 * waits long enough for the legitimate result instead of aborting early.
 */
export function passthroughPost<Shape extends z.ZodRawShape>(
  path: string,
  opts?: { timeoutMs?: number },
): (args: z.infer<z.ZodObject<Shape>>) => Promise<ToolResult> {
  return async (args) => {
    const res = await blenderPost(path, args as Record<string, unknown>, opts?.timeoutMs);
    return res;
  };
}

/** Convenience for "GET /<path>" forwarding tools. */
export function passthroughGet<Shape extends z.ZodRawShape>(
  path: string,
  opts?: { timeoutMs?: number },
): (_args: z.infer<z.ZodObject<Shape>>) => Promise<ToolResult> {
  return async () => {
    const res = await blenderGet(path, opts?.timeoutMs);
    return res;
  };
}
