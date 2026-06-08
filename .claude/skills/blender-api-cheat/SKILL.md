---
name: blender-api-cheat
description: Blender Python API cheat sheet for AI agents — bpy.data vs bpy.ops, the main-thread rule, context overrides, mode switches, where to reach for bmesh vs operators. Read when picking the right API for a tool implementation.
---

# Blender API cheat sheet

Companion to [.claude/rules/python-blender.md](../../rules/python-blender.md). Load when designing or reviewing a Python handler.

## The four modules you'll touch every day

| Module | Use for |
|---|---|
| `bpy.data` | Direct access to all data-blocks. `bpy.data.objects`, `materials`, `actions`, `armatures`, `scenes`, `node_groups`, `meshes`. Read and mutate. |
| `bpy.ops` | Operators with side effects beyond a single data-block: mode switches, selection, file IO, render, import/export. Always check `op.poll()`. |
| `bmesh` | Non-trivial mesh editing. Open with `bmesh.from_edit_mesh` in Edit Mode or `bmesh.new()` + `from_mesh` in Object Mode. |
| `mathutils` | Vectors, matrices, quaternions, Euler. Never mix with raw tuples in math. |

## bpy.data vs bpy.ops — the decision

| Situation | Prefer |
|---|---|
| Create a data-block (`Mesh`, `Material`, `Action`) | `bpy.data.<type>.new(name=...)` |
| Set a property on an existing data-block | direct attribute assignment (`obj.location = ...`) |
| Switch object mode | `bpy.ops.object.mode_set(mode='EDIT')` |
| Modify the selection state | `bpy.ops.object.select_all(action='DESELECT')` |
| Apply a transform | `bpy.ops.object.transform_apply(...)` (no direct data API) |
| Add a modifier | `obj.modifiers.new(name=..., type='SUBSURF')` (data API works) |
| Add a constraint | `obj.constraints.new(type='COPY_LOCATION')` |
| Add a keyframe | `obj.keyframe_insert(data_path=..., frame=...)` |
| Render | `bpy.ops.render.render(...)` |
| Import/export FBX/glTF/USD/Alembic | `bpy.ops.import_scene.fbx(...)` / `bpy.ops.export_scene.fbx(...)` |
| Save file | `bpy.ops.wm.save_mainfile(...)` |
| Push undo step | `bpy.ops.ed.undo_push(message=...)` |

Rule of thumb: **prefer `bpy.data` mutation; reach for `bpy.ops` only when the operation is a side-effecting tool action.** Operator calls are heavier (they run polls, context checks, push undo) and depend on context.

## The main-thread rule

`bpy` is NOT thread-safe. Every handler body runs inside `run_on_main(fn, *args, **kwargs)` which:

1. Enqueues `fn` on a `queue.Queue` consumed by a `bpy.app.timers` drain.
2. Blocks the HTTP thread on a `threading.Event`.
3. Returns `fn`'s result (or re-raises its exception) on the HTTP thread.

Never call `bpy.*` from outside `fn`. Don't even touch `bpy.context` to "just peek".

## Context overrides — the 4.x way

```python
def with_view3d_override(fn):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                region = next(r for r in area.regions if r.type == 'WINDOW')
                with bpy.context.temp_override(window=window, area=area, region=region):
                    return fn()
    raise HandlerError("NO_VIEWPORT", "No 3D Viewport available (headless?)")
```

Operators that need 3D View context (view ops, some selection ops, render border):
- `bpy.ops.view3d.*`
- `bpy.ops.view3d.snap_*`
- some `bpy.ops.transform.*`

Operators that DON'T need a viewport (most data-block ops, exporters, file ops): no override needed.

## Mode-aware editing

```python
def with_mode(obj, mode, fn):
    prev_active = bpy.context.view_layer.objects.active
    prev_mode = obj.mode if obj == prev_active else "OBJECT"
    bpy.context.view_layer.objects.active = obj
    if obj.mode != mode:
        bpy.ops.object.mode_set(mode=mode)
    try:
        return fn()
    finally:
        if obj.mode != prev_mode:
            bpy.ops.object.mode_set(mode=prev_mode)
        bpy.context.view_layer.objects.active = prev_active
```

| Mode | What you can do |
|---|---|
| `OBJECT` | Most data-block reads, modifier add/remove, transform, parent. |
| `EDIT` (mesh) | Vertex / edge / face mutations via `bmesh`. |
| `EDIT` (armature) | Add / remove / rename / re-parent bones (`armature.edit_bones`). |
| `POSE` (armature) | Pose bone transforms, constraints on pose bones. |
| `SCULPT`, `WEIGHT_PAINT`, `VERTEX_PAINT`, `TEXTURE_PAINT` | Tool-specific — rarely needed for an MCP. |

## Common data-block accessors

```python
# objects, scenes, collections
bpy.data.objects["Cube"]                 # by name
bpy.data.objects.get("Cube")             # safe (None if missing)
bpy.context.scene                        # active scene
bpy.context.scene.collection             # root collection

# materials
bpy.data.materials["Mat"]
obj.data.materials                       # material slots on an object
obj.material_slots[0].material           # slot → material

# nodes
mat.node_tree                            # ShaderNodeTree
mat.node_tree.nodes                      # all nodes
mat.node_tree.links                      # all links
mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
mat.node_tree.links.new(node_a.outputs['BSDF'], node_b.inputs['Surface'])

# armatures + bones
arm = bpy.data.armatures["MyArmature"]
arm_obj.data.edit_bones                  # only in EDIT mode
arm_obj.data.bones                       # always (rest pose data)
arm_obj.pose.bones                       # only meaningful in POSE mode

# actions + F-curves
act = bpy.data.actions["MyAction"]
act.fcurves                              # F-curve list
fcu.keyframe_points

# modifiers + constraints
obj.modifiers.new(name="Subsurf", type='SUBSURF')
obj.constraints.new(type='COPY_LOCATION')
```

## Common gotchas

1. **Context is read-only.** `bpy.context.active_object = obj` raises. Use `bpy.context.view_layer.objects.active = obj`.
2. **Operator polls.** `bpy.ops.foo.bar.poll()` returns False → calling raises `RuntimeError`. Always check first if the operation is context-dependent.
3. **Renames append `.001`.** Blender silently uniquifies names. After `obj = bpy.data.objects.new(name="Cube")`, `obj.name` might be `"Cube.001"`. Always read it back.
4. **`bpy.ops` returns sets of strings.** `{'FINISHED'}`, `{'CANCELLED'}`, `{'PASS_THROUGH'}`. Check explicitly.
5. **Drivers reference by data path.** `obj.driver_add("location", 2)` adds a driver on Z; the path is what the F-curve panel shows.
6. **Node socket access by index OR name.** `node.inputs[0]` and `node.inputs["Base Color"]` both work. Prefer name in code that survives operator updates.
7. **`bpy.app.timers` in `--background`.** They run, but only if the main thread is alive. The serve script must `time.sleep()` in a loop, not return immediately.

## Useful references (in `ref/` — read, don't copy)

- `ref/blender-mcp/addon.py` — ahujasid's TCP-socket execute-in-main-thread pattern.
- `ref/blender-ai-mcp/blender_addon/` — PatrykIti's goal-routing and curated tools.
- [Blender Python API docs](https://docs.blender.org/api/current/).
