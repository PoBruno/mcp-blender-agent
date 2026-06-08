---
applyTo: "Tools/**/*.ts"
---

# TypeScript rules

Apply to all TS files under `Tools/`. Mirror of [`.claude/rules/typescript.md`](../../.claude/rules/typescript.md) — keep in sync.

## Module system

- ESM, `.js` extensions in imports (Node ESM quirk for TS).
- `"type": "module"` in `Tools/package.json`.
- `"module": "NodeNext"` in `tsconfig.json`.

## Strictness

- `strict: true`.
- No `any`. Use `unknown` and narrow with type guards.
- No `as` casts except at JSON boundaries — validate with Zod immediately after.
- Optional chaining / nullish coalescing over manual null checks.

## Async

- Always `await`. No `.then(...)` chains in tool code.
- No `process.exit()` mid-operation.
- Top-level entry wrapped in `.catch(err => { console.error(err); process.exit(1); })`.

## Logging

- `console.error` only — stdout is the MCP transport, polluting it breaks the protocol.
- Prefix `[blender-agent]` so users can grep.

## Tool registration

Each tool group lives in `Tools/src/tools/<group>.ts` exporting `register<Group>Tools(server: McpServer)`. `src/index.ts` calls every register function. No inline tool definitions in `index.ts`.

## HTTP calls to the addon

Use helpers in `src/blender-bridge.ts`:

- `blenderGet<T>(path: string): Promise<T>` for read-only.
- `blenderPost<T>(path: string, body: object): Promise<T>` for mutations.

Both throw on non-200. Catch and convert to structured output:

```ts
try {
  const data = await blenderPost<{ objectName: string }>("/object/create", input);
  return {
    ok: true,
    data,
    refs: { objectName: data.objectName },
    nextSteps: ["call object_set_transform with this objectName"],
  };
} catch (err) {
  return { ok: false, errorCode: "BLENDER_HTTP_FAILED", warnings: [String(err)] };
}
```

## Path / file handling

- `node:path` not string concat.
- `node:fs/promises` not `fs.readFileSync` in hot paths.
- Headless Blender detection via `findBlenderBinary` in `blender-bridge.ts` (checks `BLENDER_BIN` env, then `PATH`, then common install locations per OS).

## What not to do

- No imports from `dist/`. Source-relative only.
- No shelling out to `git`/`npm`/`node` from a tool — that's the install playbook's job.
- No env reads inside tool code — read once in `blender-bridge.ts` and export typed constants.
- No swallowed errors — convert to `{ ok: false, errorCode: "..." }`.
- No translation of Python snake_case to TS camelCase scattered across tools — do it once at the bridge boundary.
