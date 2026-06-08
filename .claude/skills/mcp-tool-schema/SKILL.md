---
name: mcp-tool-schema
description: How to design and register a new MCP tool — input schema (Zod), output contract, descriptions, tests. Read before adding any new tool to Tools/src/tools/.
---

# MCP tool schema

Checklist for adding a new tool. Read end-to-end before writing the tool file.

## Checklist

- [ ] Tool belongs in a group file under `Tools/src/tools/<group>.ts`. Pick existing if domain matches; create new if it doesn't.
- [ ] Tool name follows `<domain>_<verb>[<_qualifier>]`: `object_create`, `material_set_principled_param`, `bone_add`, `socket_add`, `export_fbx`.
- [ ] Zod schema for every input parameter, with `.describe()` on each.
- [ ] Return type is `Promise<ToolResult<T>>` where `T` is the success payload shape.
- [ ] On success: populate `data`, `refs`, optionally `nextSteps`, optionally `warnings`.
- [ ] On failure: `ok: false`, `errorCode` from the registry, `warnings` with detail.
- [ ] Description string written for the LLM consuming the tool — under 200 chars for simple, structured multi-line for complex (especially exports).
- [ ] Integration test in `Tools/test/tools/<tool-name>.test.ts` covering happy path, every `errorCode` branch, idempotency where applicable.
- [ ] Python handler exists if needed, registered via `@handler("METHOD", "/path")`, follows the handler pattern from [.claude/rules/python-blender.md](../../rules/python-blender.md).
- [ ] If a new `errorCode` is introduced: added to both [.claude/rules/mcp-tools.md](../../rules/mcp-tools.md) and [.github/instructions/mcp-tools.instructions.md](../../../.github/instructions/mcp-tools.instructions.md).
- [ ] If a new entity type is introduced: added to the ref-naming table in [.claude/skills/tool-chains/SKILL.md](../tool-chains/SKILL.md).

## Tool file template

```ts
// Tools/src/tools/my-domain.ts
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { blenderPost } from "../blender-bridge.js";
import type { ToolResult } from "../types.js";

export function registerMyDomainTools(server: McpServer): void {
  server.tool(
    "my_domain_do_thing",
    "Short imperative description aimed at the LLM. Under 200 chars. What it does, what it returns, when to call it next.",
    {
      objectName: z.string().describe("Object name (data-block key in bpy.data.objects)"),
      // ...
    },
    async (input): Promise<ToolResult<{ /* payload */ }>> => {
      try {
        const res = await blenderPost<{ /* python response */ }>("/my_domain/do_thing", input);
        return {
          ok: true,
          data: { /* mapped */ },
          refs: { /* IDs */ },
          nextSteps: ["call ... next"],
        };
      } catch (err) {
        // narrow to known errorCodes when possible
        return { ok: false, errorCode: "BLENDER_HTTP_FAILED", warnings: [String(err)] };
      }
    }
  );
}
```

Then add `registerMyDomainTools(server)` to `Tools/src/index.ts`.

## Python handler template

```python
# BlenderAgent/handlers/my_domain.py
import bpy
from ..server import handler, run_on_main, HandlerError, with_mode

@handler("POST", "/my_domain/do_thing")
def do_thing(req):
    object_name = req["object_name"]  # snake_case on the wire
    # ... pull other params

    def main():
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            raise HandlerError("OBJECT_NOT_FOUND", f"object {object_name!r} not found")

        # ... mutation
        bpy.ops.ed.undo_push(message="Do thing on object")
        return {"object_name": obj.name}

    return run_on_main(main)
```

Then ensure the module is imported in `BlenderAgent/handlers/__init__.py` so the `@handler` decorator runs.

## Description writing — for the LLM

The description is the agent's only hint at *when* to call the tool. Write it for that.

- ✅ "Add a bone to an armature. Switches to Edit Mode automatically and restores afterwards. Returns the bone name. Call bone_set_transform or socket_add next."
- ❌ "Adds a bone" (too terse — agent guesses inputs).
- ❌ "Switches active object to the armature, enters Edit Mode via bpy.ops.object.mode_set, calls armature.data.edit_bones.new with name parameter, sets head/tail from request payload..." (noise; wastes tokens).

For complex tools (`export_*` especially): multi-section structured description quoting the operator name and Blender's tooltip per parameter group.

## Tests are mandatory

Every new tool → `Tools/test/tools/<tool-name>.test.ts`.

Required cases:
- **Happy path.** Bootstrap Blender, call tool, assert response.
- **Every `errorCode` branch.** Provoke each failure and assert the code.
- **Idempotency.** Where applicable (e.g. mode switches): calling twice is the same as calling once.
- **Cleanup.** Tool leaves Blender state as found (no leaked objects, materials, actions).

Test skeleton:

```ts
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { bootstrapBlender, callTool } from "../bootstrap.js";

describe("my_domain_do_thing", () => {
  let ctx: Awaited<ReturnType<typeof bootstrapBlender>>;
  beforeAll(async () => { ctx = await bootstrapBlender(); });
  afterAll(async () => { await ctx.teardown(); });

  it("happy path", async () => {
    const res = await callTool(ctx, "my_domain_do_thing", { objectName: "Cube" });
    expect(res.ok).toBe(true);
    expect(res.refs?.objectName).toBe("Cube");
  });

  it("returns OBJECT_NOT_FOUND for missing object", async () => {
    const res = await callTool(ctx, "my_domain_do_thing", { objectName: "Nope" });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("OBJECT_NOT_FOUND");
  });
});
```
