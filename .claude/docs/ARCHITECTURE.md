# ARCHITECTURE.md

The product bible for `mcp-blender-agent`. Every architectural decision must be consistent with this document. When something changes here, update [DECISIONS.md](DECISIONS.md) with an ADR.

This file is the Blender twin of [`mcp-unreal-agent`'s ARCHITECTURE.md](https://github.com/PoBruno/mcp-unreal-agent/blob/main/.claude/docs/ARCHITECTURE.md). Differences are spelled out where they matter.

---

## 1. What we are building

An MCP server that gives AI coding agents complete control of a Blender 4.2 LTS+ session.

Not just inspection. Not just scene generation. The agent should be able to:

- **Read and mutate any data-block:** objects, meshes, armatures, materials, shader/geometry node trees, actions, NLA tracks, drivers, modifiers, constraints, render settings.
- **Execute composite flows atomically** — e.g. "create armature, add 5 bones with sockets, assign weights, save" is one undo entry the agent calls once.
- **Granular import/export** — every parameter of every FBX/glTF/USD/Alembic exporter is a typed input.
- **Render** — Cycles / Eevee / Workbench, image / animation / viewport screenshot.
- **Drive the viewport headlessly when needed** — for CI smoke tests.

The agent's experience is the first-class concern. The Python addon surface area is the lever.

See [`OBJECTIVES.md`](../../OBJECTIVES.md) for the product brief.

---

## 2. Two-process system

```
┌──────────────────────────────────┐
│ Coding agent (Claude / Copilot)  │
│  ─────────────────────────────── │
│  speaks MCP over stdio           │
└────────────┬─────────────────────┘
             │ MCP JSON-RPC
             ▼
┌──────────────────────────────────┐
│ blender-agent (Node.js)          │
│  Tools/dist/index.js             │
│  ─────────────────────────────── │
│  - registers MCP tools           │
│  - validates input (Zod)         │
│  - calls addon HTTP              │
│  - shapes structured output      │
└────────────┬─────────────────────┘
             │ HTTP localhost:9876
             ▼
┌──────────────────────────────────┐
│ BlenderAgent addon (Python)      │
│  BlenderAgent/                   │
│  ─────────────────────────────── │
│  Mode A: enabled in running      │
│   Blender (preferred)            │
│  Mode B: blender --background    │
│   (spawned by Node if no editor) │
│  ─────────────────────────────── │
│  - HTTP listener on 9876         │
│   (background thread)            │
│  - drain queue                   │
│   (bpy.app.timers, main thread)  │
│  - per-domain handler files      │
└──────────────────────────────────┘
```

### Why two processes

- **MCP servers are tiny and stateless.** The Node side has no Blender dependency, starts in <100 ms, is restartable.
- **The addon owns Blender.** `bpy.*` only exists inside a Blender process.
- **HTTP between them is the right boundary.** Same machine, localhost, low latency, JSON serializable, easy to debug with curl.

### Why HTTP, not a socket protocol

`ahujasid/blender-mcp` uses a raw TCP socket with a JSON-over-newline protocol. That works but has no HTTP semantics (status codes, paths, headers) — every error is a parse-the-payload exercise. We use HTTP for the same reasons `mcp-unreal-agent` does: better dev ergonomics, easier debugging, trivial proxy-ability.

---

## 3. Two serving modes for the addon

### Mode A: enabled in running Blender (preferred)

The user installs `BlenderAgent` via **Edit → Preferences → Add-ons → Install…** and enables it. The addon registers and immediately starts the HTTP server. Every interactive workflow uses this mode.

### Mode B: headless (`blender --background`)

The TS server spawns:

```
blender --background --python-expr "import BlenderAgent; BlenderAgent.serve()"
```

Used for:
- **CI / Vitest integration tests.** No interactive Blender available.
- **Batch ops.** Re-export hundreds of files.
- **First-time install verification.** Detect that the addon works before asking the user to open Blender.

The TS server detects which mode is live via `GET /server/status` and never spawns a duplicate. If port `9876` is held but the response doesn't have the expected `mode: "blender-agent"` field → port collision → caller error with `errorCode: "PORT_CONFLICT"`.

### Shutdown

- Mode A: never shut down by the agent. The user closes Blender.
- Mode B: shut down via `POST /server/shutdown` (or process kill on `SIGINT` / `SIGTERM`).

---

## 4. The HTTP bridge

Port `9876` by default (override with `BLENDER_PORT` env var). Localhost only. No TLS. No auth. This is a developer tool — the threat model is "the developer's own machine".

If you ever expose this beyond localhost, you must add auth. **Don't.**

### Request shape

```
POST /<domain>/<verb>
Content-Type: application/json

{ "param_1": ..., "param_2": ... }
```

Python uses `snake_case`; the TS bridge translates camelCase ↔ snake_case at the boundary. Tool code never sees the wire format.

### Response shape

Success:

```json
{ "ok": true, "data": { ... } }
```

Failure:

```json
{ "ok": false, "error_code": "OBJECT_NOT_FOUND", "message": "..." }
```

The TS server wraps both into `ToolResult<T>` and adds `refs`, `nextSteps`, `warnings` based on `data`.

---

## 5. The threading model — the single biggest difference from `mcp-unreal-agent`

**`bpy` is not thread-safe.** This is the load-bearing fact of this architecture. UE5 has the same constraint with the game thread, but its handlers can use `AsyncTask(ENamedThreads::GameThread, [...])` and block on a `TPromise`. Blender's equivalent is `bpy.app.timers`.

### Pattern

```
┌───────────────────────────────┐
│ HTTP handler thread (Python)  │
│   parses JSON                 │
│   builds fn(*args, **kwargs)  │
│   creates threading.Event     │
│   enqueues (fn, event, result)│
│   event.wait(timeout=30s)     │
│   reads result, returns 200   │
└───────────┬───────────────────┘
            │ queue.Queue
            ▼
┌───────────────────────────────┐
│ bpy.app.timers drain (main)   │
│   runs every ~16ms            │
│   pops one job                │
│   calls fn(*args, **kwargs)   │
│   stores result               │
│   event.set()                 │
└───────────────────────────────┘
```

A 30-second timeout protects against deadlock. If the main thread is stuck (modal operator running, slow render), the handler returns `errorCode: "BLENDER_TIMEOUT"`.

### Why not a modal operator instead

Modal operators have a complex lifecycle (`invoke`, `execute`, `modal`, `cancel`) and depend on UI events. Timers are simpler and run regardless of UI state. ADR-001 covers this.

---

## 6. The handler shape

```python
# BlenderAgent/handlers/object.py
import bpy
from ..server import handler, run_on_main, HandlerError

@handler("POST", "/object/create")
def create(req):
    name = req["name"]
    type_ = req.get("type", "MESH").upper()
    location = tuple(req.get("location", [0, 0, 0]))

    def main():
        if name in bpy.data.objects:
            raise HandlerError("OBJECT_EXISTS", f"object {name!r} already exists")
        if type_ == "MESH":
            mesh = bpy.data.meshes.new(name=name)
            obj = bpy.data.objects.new(name=name, object_data=mesh)
        elif type_ == "EMPTY":
            obj = bpy.data.objects.new(name=name, object_data=None)
        else:
            raise HandlerError("INVALID_PARAMS", f"unsupported type {type_!r}")
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        bpy.ops.ed.undo_push(message=f"Create object {name!r}")
        return {"object_name": obj.name}

    return run_on_main(main)
```

Six required pieces:
1. `@handler("METHOD", "/path")` — registers with the HTTP server.
2. Inputs unpacked from `req` (the parsed JSON body).
3. Validation that **must** raise `HandlerError(code, message)` for known failure modes.
4. **All `bpy.*` calls inside `main`** — never outside.
5. `bpy.ops.ed.undo_push(message=...)` at the end of every mutation.
6. Return a JSON-serializable dict — the bridge wraps it in `{"ok": true, "data": ...}`.

---

## 7. The TS tool shape

```ts
// Tools/src/tools/object.ts
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { blenderPost } from "../blender-bridge.js";
import type { ToolResult } from "../types.js";

export function registerObjectTools(server: McpServer): void {
  server.tool(
    "object_create",
    "Create a new object in the active scene. Returns the object name (use for object_set_transform, object_set_visibility, etc).",
    {
      name: z.string().describe("Desired object name; must be unique"),
      type: z.enum(["MESH", "EMPTY", "CAMERA", "LIGHT", "CURVE", "ARMATURE"]).optional(),
      location: z.tuple([z.number(), z.number(), z.number()]).optional(),
    },
    async (input): Promise<ToolResult<{ objectName: string }>> => {
      try {
        const res = await blenderPost<{ object_name: string }>("/object/create", input);
        const objectName = res.object_name;
        return {
          ok: true,
          data: { objectName },
          refs: { objectName },
          nextSteps: ["call object_set_transform with this objectName"],
        };
      } catch (err) {
        return { ok: false, errorCode: "BLENDER_HTTP_FAILED", warnings: [String(err)] };
      }
    }
  );
}
```

The bridge translates `objectName` → `object_name` automatically (config in `blender-bridge.ts`), but explicit destructuring on the response stays in the tool to keep the rename visible.

---

## 8. Composite atomic flows

Every multi-step mutation that conceptually belongs together is one tool that ends with one undo push.

Example: `armature_add_socket` —

```python
def main():
    # 1. switch to edit mode on the armature
    # 2. find the bone
    # 3. create an empty parented to the bone via constraint or parent-bone slot
    # 4. name it
    # 5. exit edit mode
    bpy.ops.ed.undo_push(message=f"Add socket {socket_name!r} on bone {bone_name!r}")
    return {"object_name": empty.name, "bone_name": bone_name}
```

The agent calls this **once**. Ctrl+Z reverses the entire socket creation, not five micro-steps. See [`.claude/skills/tool-chains/SKILL.md`](../skills/tool-chains/SKILL.md).

---

## 9. Snapshots, not binary diffs

`.blend` is binary. Diffing it is intractable. Diffing structured JSON snapshots is trivial.

Every group with a "graph" surface (shader nodes, geometry nodes, compositor) exposes:

- `<group>_snapshot_graph` — returns a normalized JSON dump of the graph.
- `<group>_diff_graph` — takes two snapshots, returns a structured diff (added/removed/changed nodes and links).
- `<group>_restore_graph` — applies a snapshot to recreate the graph.

This is the agent's mechanism for "show me what changed in this material" without parsing `.blend`.

---

## 10. Install flow

End users install the MCP into their agent harness by running a one-prompt installer. The brain lives at `install/AGENT-INSTALL.md` (added in Phase 5, mirroring `mcp-unreal-agent`).

Steps the installer performs:

1. **Detect:** OS, Blender version, agent harness (Claude / Copilot / Cursor / Claude Desktop), existing MCP configs, conflicts.
2. **Plan:** primary harness, addon install path, MCP config entry, managed instruction block.
3. **Ask:** confirm with user.
4. **Execute:** download `BlenderAgent.zip`, install via `blender --background --python-expr "bpy.ops.preferences.addon_install(filepath='...')"`. Install TS server via npm. Merge MCP config without overwriting.
5. **Inject:** copy `install/context-skill/{SKILL.md|instructions.md, FLOWS.md, TOOLS.md}` into the user's harness, insert a delimited managed block in the primary instruction file.
6. **Verify:** call `server_status` end-to-end. If green, done.
7. **Uninstall:** strip managed block, remove skill files, remove MCP entry, disable addon. Leaves `.blend` files alone.

The passive context skill (`SKILL.md` for Claude, `instructions.md` with `applyTo: "**"` for Copilot) makes the agent always-on aware of: the contract, the canonical flows, the tool digest, the error registry.

---

## 11. Versioning

- Addon and TS server share one version, set in `BlenderAgent/__init__.py` (`bl_info["version"]`) and `Tools/package.json` (`version`). A CI check fails on mismatch.
- `dev` is permanent integration. `main` is release-only. v1.0 is the first tag on `main`.

---

## 12. What we explicitly don't do

(Subset of [`OBJECTIVES.md`](../../OBJECTIVES.md) §5 most relevant to architecture.)

- **No C++ Blender plugin.** Python addon is the right boundary. The cost/benefit of C++ here is negative.
- **No Blender 3.x support.** `bpy.context.temp_override` (4.x API) is non-negotiable.
- **No telemetry.** Zero exfiltration.
- **No bundled external services** (Hyper3D, Sketchfab). Compose with `ahujasid/blender-mcp` instead.

---

## 13. Tool layering and per-domain research

The 228-tool v1.0 surface is organized into 9 artist-workflow pipelines (B1..B9). Each pipeline has a feasibility study, type-graph, and tool catalog under [`research/`](research/). When designing or implementing a tool:

1. Find its canonical owner pipeline in [research/TOOL-CATALOG.md](research/TOOL-CATALOG.md).
2. Read its entry's research file (`research/pipelines/B*.md`) for full schema, API path, and error codes.
3. Check feasibility in [research/BPY-FEASIBILITY.md](research/BPY-FEASIBILITY.md) — 🟢 ship, 🟡 ship with documented constraint, 🔴 defer or out-of-scope.
4. Trace inputs and outputs in [research/TYPE-GRAPH.md](research/TYPE-GRAPH.md) to fill in `relatedTools.upstream[]` / `relatedTools.downstream[]`.
5. If the tool participates in an end-to-end recipe, the recipe in [research/WORKFLOW-RECIPES.md](research/WORKFLOW-RECIPES.md) defines the integration test expectations.

The research files are authoritative for tool design. This file (ARCHITECTURE.md) stays at the system-architecture level — threading, IPC, contract shape, install flow.

See [DECISIONS.md ADR-012](DECISIONS.md) for the layering rationale and ADR-013 for the tool-count baseline.
