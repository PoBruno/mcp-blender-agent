---
applyTo: "Tools/src/tools/**/*.ts"
---

# MCP tool contract

Apply to every file under `Tools/src/tools/`. This is the **agent-facing API contract**. Mirror of [`.claude/rules/mcp-tools.md`](../../.claude/rules/mcp-tools.md) — keep in sync.

## Required output shape

```ts
export type ToolResult<T = unknown> = {
  ok: boolean;
  data?: T;
  refs?: Record<string, string | string[]>;
  nextSteps?: string[];
  warnings?: string[];
  errorCode?: string;
};
```

| Field | Meaning |
|---|---|
| `ok` | `true` if operation succeeded. `false` → caller must inspect `errorCode`. |
| `data` | Tool-specific result payload. Type-parameterized. |
| `refs` | Map of named IDs the agent passes to subsequent tools. Single id (`<entity>Name` for Blender's name-keyed model: `objectName`, `materialName`, `actionName`, `boneName`) or an id list for enumerations (`objectNames`, `materialNames`). |
| `nextSteps` | Free-form hints. Never imperative — phrased as "you can call X next" or "consider Y if Z". |
| `warnings` | Non-fatal issues. Operation succeeded but something deserves attention. |
| `errorCode` | Stable code from the registry. Always set when `ok=false`. Never invent codes without adding to registry. |

## Error code registry

| Code | When |
|---|---|
| `BLENDER_NOT_RUNNING` | Addon HTTP server unreachable on port 9876. Caller should try `ensureBlender()`. |
| `BLENDER_HTTP_FAILED` | HTTP call to addon returned non-2xx or threw. |
| `BLENDER_TIMEOUT` | Main-thread drain didn't complete within timeout. Editor may be busy. |
| `OBJECT_NOT_FOUND` | Named object missing in `bpy.data.objects`. |
| `MATERIAL_NOT_FOUND` | Named material missing in `bpy.data.materials`. |
| `ACTION_NOT_FOUND` | Named action missing in `bpy.data.actions`. |
| `ARMATURE_NOT_FOUND` | Named armature missing. |
| `BONE_NOT_FOUND` | Named bone missing on armature. |
| `NODE_NOT_FOUND` | Named shader / geo / compositor node missing in tree. |
| `MODIFIER_NOT_FOUND` | Named modifier missing on object. |
| `CONSTRAINT_NOT_FOUND` | Named constraint missing on object / bone. |
| `INVALID_MODE` | Operator requires a specific mode (Edit / Pose / Object) and we couldn't switch. |
| `NO_VIEWPORT` | Operator requires 3D View context but headless Blender has none. |
| `OPERATOR_POLL_FAILED` | `bpy.ops.foo.bar.poll()` returned False. |
| `EXPORT_FAILED` | Export operator returned `{'CANCELLED'}` or raised. |
| `IMPORT_FAILED` | Import operator returned `{'CANCELLED'}` or raised. |
| `INVALID_PARAMS` | Input failed Zod validation (registration wrapper, not your handler). |
| `MAIN_THREAD_ERROR` | Exception raised inside the drain `fn`. Detail in `warnings`. |

Add new codes here AND in [`.claude/rules/mcp-tools.md`](../../.claude/rules/mcp-tools.md). Keep both in sync.

## Input validation with Zod

```ts
import { z } from "zod";

server.tool(
  "object_set_transform",
  "Set an object's location, rotation, and/or scale. Any unspecified component is left unchanged. Returns the resulting full transform.",
  {
    objectName: z.string().describe("Object name (data-block key in bpy.data.objects)"),
    location: z.tuple([z.number(), z.number(), z.number()]).optional(),
    rotationEuler: z.tuple([z.number(), z.number(), z.number()]).optional()
      .describe("XYZ Euler in radians"),
    scale: z.tuple([z.number(), z.number(), z.number()]).optional(),
  },
  async (input) => { /* impl */ }
);
```

- Every parameter `.describe()`d with what the agent needs to know.
- Optional via `.optional()`, never `| undefined`.
- IDs as opaque strings — never tightly typed.
- Tuples with explicit length where applicable (`tuple([...]).length(3)` style).

## ID chaining convention

Blender's data model is **name-keyed**. `refs` are emitted under the EXACT key the consuming tool accepts as input, so `refs.objectName` feeds the next tool's `objectName` param verbatim.

| Tool returns (primary key) | Consumed by param |
|---|---|
| `refs.objectName` | `objectName` |
| `refs.materialName` | `materialName` |
| `refs.actionName` | `actionName` |
| `refs.armatureName` | `armatureName` |
| `refs.boneName` | `boneName` |
| `refs.nodeName` | `nodeName` |
| `refs.modifierName` | `modifierName` |
| `refs.constraintName` | `constraintName` |
| `refs.collectionName` | `collectionName` |
| `refs.sceneName` | `sceneName` |
| `refs.objectNames[]` / `refs.materialNames[]` etc. | list enumerations |

When designing a tool, work backwards from the chain:
1. What does the agent know before calling? (inputs)
2. What does the agent need next? (refs + nextSteps)

## Tool descriptions

Written for the LLM agent:

- ✅ "Add a bone to an armature in edit mode. Returns the new bone name. Call bone_set_transform next."
- ❌ "Adds bone" (too terse)
- ❌ "This tool enters EDIT_ARMATURE mode via bpy.ops.object.mode_set, calls armature.edit_bones.new, sets head/tail, exits mode, returns bone name" (noise, wastes tokens)

Under 200 chars for simple tools. Multi-line structured for complex tools — especially the `export_*` family where every operator parameter is exposed.

## Export-tool descriptions are special

`export_fbx`, `export_gltf`, `export_obj`, `export_usd`, `export_alembic` each surface dozens of Blender operator parameters. Their descriptions must:

- State the operator they wrap (`bpy.ops.export_scene.fbx`).
- Group parameters by section (transform, geometry, armature, animation).
- Reference Blender's docs URL for the operator.

The Zod schema is the contract. Every parameter has `.describe()` that quotes the Blender tooltip verbatim where possible.

## Tests are mandatory

Every new tool → integration test at `Tools/test/tools/<tool-name>.test.ts`. Bootstrap from `Tools/test/bootstrap.ts` spawns headless Blender. Helpers in `Tools/test/helpers.ts`.

Required cases:
- Happy path.
- Each `errorCode` branch reachable.
- Idempotency where applicable.
- Cleanup — handler leaves Blender state as found.
