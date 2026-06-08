# SPRINTS.md

Active sprint tasks. **This file is the source of truth for what to work on.** [ROADMAP.md](../../ROADMAP.md) is the phase-level plan; this is the actionable breakdown of the current sprint.

## Task format

```markdown
- [ ] **SN-XX** One-line description — include done criteria inline
  _(requires SN-YY)_
  ⚠️ Note: one-line warning about a non-obvious constraint
  🔍 Research first: one-line of what to verify before writing code
```

`N` = sprint number, `XX` = zero-padded task number. Mark done with `[x]` and `<!-- done: YYYY-MM-DD -->` at the end of the line.

---

## Sprint 0 — Bootstrap (active)

Goal: a green Vitest test that spawns headless Blender, calls `server_status`, asserts the version. Everything required to make that pass — nothing more.

### Addon

- [ ] **S0-01** Create `BlenderAgent/__init__.py` with `bl_info` dict (name, version `(0, 0, 1)`, blender `(4, 2, 0)`, category `"Development"`) and `register()` / `unregister()` calling into `server.start()` / `server.stop()`.
  ⚠️ `bl_info` is parsed before module body runs — keep it a literal dict.

- [ ] **S0-02** Create `BlenderAgent/server.py` with the threading + drain pattern from [.claude/rules/python-blender.md](../rules/python-blender.md): `ThreadingHTTPServer` on a background thread, `queue.Queue` of jobs, `bpy.app.timers.register(_drain, persistent=True)`.
  🔍 Research first: confirm `persistent=True` survives addon reload and undo. Skim [`bpy.app.timers`](https://docs.blender.org/api/current/bpy.app.timers.html).
  ⚠️ The drain function must return the next poll interval (e.g. `0.016`) — returning `None` deregisters.

- [ ] **S0-03** Create `BlenderAgent/handlers/__init__.py` + `BlenderAgent/handlers/server_status.py` returning `{ "version": bpy.app.version_string, "scene": bpy.context.scene.name, "mode": "blender-agent" }`.

### TypeScript bridge

- [ ] **S0-04** `Tools/package.json` with `"type": "module"`, scripts `build` / `test` / `test:unit` / `digest`. Deps: `@modelcontextprotocol/sdk` (latest), `zod`. Dev deps: `typescript`, `vitest`, `@types/node`.

- [ ] **S0-05** `Tools/tsconfig.json` with `strict: true`, `module: "NodeNext"`, `target: "ES2022"`, `outDir: "dist"`, `rootDir: "src"`, `declaration: true`.

- [ ] **S0-06** `Tools/src/types.ts` with `ToolResult<T>` exported.

- [ ] **S0-07** `Tools/src/blender-bridge.ts` with `blenderGet<T>(path)` and `blenderPost<T>(path, body)`. Read `BLENDER_PORT` env (default `9876`). Throw on non-2xx. Include `findBlenderBinary()` (checks `BLENDER_BIN`, then `PATH`, then `C:\Program Files\Blender Foundation\Blender 4.2\blender.exe`, then macOS `/Applications/Blender.app/Contents/MacOS/Blender`).

- [ ] **S0-08** `Tools/src/tools/server-status.ts` registering tool `server_status`. Calls `blenderGet("/server/status")`. Returns `{ ok, data: { version, scene }, refs: { sceneName: data.scene } }`.

- [ ] **S0-09** `Tools/src/index.ts` boots `McpServer`, calls `registerServerStatusTools(server)`, connects to stdio transport, top-level `.catch(err => { console.error(err); process.exit(1); })`.

### Tests

- [ ] **S0-10** `Tools/vitest.config.ts` with project root `Tools/`, `globals: true`, `testTimeout: 60000` (Blender boot is slow).

- [ ] **S0-11** `Tools/test/bootstrap.ts` that spawns `blender --background --addons BlenderAgent --python-expr "import BlenderAgent; BlenderAgent.serve_blocking()"`, waits for `/server/status` to respond, exposes `teardown()`.
  ⚠️ Blender `--background` exits when the script finishes. Use a tiny `serve_blocking()` that loops `bpy.app.timers.register(...)` and a `while not shutdown_requested: time.sleep(0.1)` on the main thread.
  🔍 Research first: confirm `bpy.app.timers` actually runs in `--background` mode (sometimes they don't without `bpy.context.window_manager.event_timer_add` — needs verification).

- [ ] **S0-12** `Tools/test/tools/server-status.test.ts`: bootstrap Blender, call `server_status` via MCP client, assert `data.version.startsWith("4.")`.

### CI + repo polish

- [ ] **S0-13** `.github/workflows/ci.yml` matrix (ubuntu-latest, windows-latest, macos-latest) with Blender 4.2 LTS installed (cached). Steps: `npm install`, `npm run build`, `npm test`.
  🔍 Research first: pick or write a `setup-blender` action. Probably write one — `blender` zip download + extract + add to PATH.

- [ ] **S0-14** `CONTRIBUTING.md` short — link to CLAUDE.md, explain dual harness, explain `dev`-only workflow.

- [ ] **S0-15** First green CI tag `v0.0.1-bootstrap` on `dev`.

---

## Sprint 1 — Scene & object control

Planned after S0 lands. Will be expanded then. Outline:

- Scene group (~10 tools)
- Object group (~12 tools)
- Mesh read-only (~8 tools)
- Composite-flow pattern locked
- Demo: "create cube, parent to empty, transform, list scene" in Copilot chat.

---

## Done log

Empty. First entries land when S0 tasks complete.
