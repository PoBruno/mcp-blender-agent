/**
 * Tool result contract — every MCP tool returns this shape (per ADR-005 + mcp-tools rules).
 */
export type ToolResult<T = unknown> = {
  ok: boolean;
  data?: T;
  /** Stringified IDs the agent passes to the next tool. */
  refs?: Record<string, string | string[]>;
  /** Free-form hints to the agent, never imperatives. */
  nextSteps?: string[];
  warnings?: string[];
  /** Set when ok=false. Stable code from the error table. */
  errorCode?: string;
  /** Human-readable error explanation (when ok=false). */
  message?: string;
};

/** Lower-level response from the Blender HTTP layer. */
export type BlenderResponse<T = unknown> = ToolResult<T>;
