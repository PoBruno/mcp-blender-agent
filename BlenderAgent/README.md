# BlenderAgent — Python addon

This folder will hold the Blender addon. It's not yet implemented — see [Sprint 0](../.claude/docs/SPRINTS.md) tasks S0-01 through S0-03.

## Expected layout (after S0)

```
BlenderAgent/
├── __init__.py            # bl_info + register() / unregister()
├── server.py              # HTTP listener (bg thread) + bpy.app.timers drain (main thread)
└── handlers/
    ├── __init__.py        # imports every handler module so decorators register
    └── server_status.py   # first handler — returns Blender version + active scene
```

## Why pure Python with stdlib only

- `bpy` is the Blender Python API. No external HTTP framework needed — `http.server.ThreadingHTTPServer` is enough.
- Zero pip deps means zero install pain — drop the folder in Blender's addons directory, enable, done.
- Aligns with `ahujasid/blender-mcp` and `PatrykIti/blender-ai-mcp`. Both stdlib-only.

## Rules

Read [`.claude/rules/python-blender.md`](../.claude/rules/python-blender.md) before touching anything here. The main-thread rule is non-negotiable.
