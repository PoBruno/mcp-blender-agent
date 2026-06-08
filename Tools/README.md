# Tools — TypeScript MCP server

This folder will hold the MCP server. It's not yet implemented — see [Sprint 0](../.claude/docs/SPRINTS.md) tasks S0-04 through S0-12.

## Expected layout (after S0)

```
Tools/
├── package.json
├── tsconfig.json
├── vitest.config.ts
├── scripts/
│   └── generate-tools-digest.mjs    # added Phase 5
├── src/
│   ├── index.ts                     # MCP server entry — boots stdio transport
│   ├── blender-bridge.ts            # HTTP client + headless lifecycle
│   ├── types.ts                     # ToolResult contract
│   └── tools/
│       └── server-status.ts         # first tool
└── test/
    ├── bootstrap.ts                 # spawns blender --background, waits for /server/status
    ├── helpers.ts                   # callTool, assertOk, etc.
    └── tools/
        └── server-status.test.ts    # first integration test
```

## Rules

Read [`.claude/rules/typescript.md`](../.claude/rules/typescript.md) and [`.claude/rules/mcp-tools.md`](../.claude/rules/mcp-tools.md) before touching anything here.

## Commands (after S0)

```powershell
npm install
npm run build      # tsc
npm test           # vitest (boots headless Blender)
npm run digest     # regenerates install/context-skill/TOOLS.md (added Phase 5)
```

Requires Blender 4.2 LTS on `PATH` or `BLENDER_BIN` env var pointing at the executable.
