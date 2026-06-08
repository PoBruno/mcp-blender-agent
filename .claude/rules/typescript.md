---
applyTo: "Tools/**/*.ts"
---

# TypeScript rules — Claude Code mirror

Mirror of [`.github/instructions/typescript.instructions.md`](../../.github/instructions/typescript.instructions.md). When you edit one, edit the other. Identical content; different harness location.

See the Copilot version for the full rule set:

- Module system (ESM, `.js` extensions, `NodeNext`).
- Strictness (`strict: true`, no `any`, no `as` outside boundaries).
- Async (`await` always, never `.then`).
- Logging (`console.error` only — stdout is the MCP transport).
- Tool registration pattern (`register<Group>Tools(server)` per file).
- HTTP helpers (`blenderGet`, `blenderPost`) in `blender-bridge.ts`.
- Path/file handling (`node:path`, `node:fs/promises`).
- snake_case ↔ camelCase translation done **only** at the bridge boundary.
