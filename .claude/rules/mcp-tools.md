---
applyTo: "Tools/src/tools/**/*.ts"
---

# MCP tool contract — Claude Code mirror

Mirror of [`.github/instructions/mcp-tools.instructions.md`](../../.github/instructions/mcp-tools.instructions.md). When you edit one, edit the other. Identical content; different harness location.

See the Copilot version for the full rule set:

- Required output shape `{ ok, data, refs, nextSteps, warnings, errorCode }`.
- Error code registry (single source of truth for both files — duplicate the table when adding codes).
- Input validation with Zod (every param `.describe()`d, optional via `.optional()`).
- ID-chaining convention (Blender is name-keyed: `objectName`, `materialName`, `actionName`, `boneName`, `nodeName`).
- Tool description guidance (LLM audience; under 200 chars for simple; structured multiline for exports).
- Export tools are special — every operator parameter is a typed input with `.describe()` quoting the Blender tooltip.
- Tests are mandatory — `Tools/test/tools/<tool>.test.ts` covering happy path, every `errorCode`, idempotency, cleanup.
