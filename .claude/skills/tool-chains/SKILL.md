---
name: tool-chains
description: Designing composite Blender tools and chaining existing ones via the ID-passing contract. Read when adding a new tool, designing a multi-step flow, or refactoring primitives into a composite atomic flow.
---

# Tool chains

How MCP tools in `blender-agent` chain together to form workflows. Read before designing any new tool or composite.

## The chaining model

Every tool returns `refs` (named IDs) and `nextSteps` (hints). The agent consumes them as inputs to the next call. Multi-step workflows feel like dataflow:

```
object_create({ name: "Hero", type: "ARMATURE" })
   → refs: { objectName: "Hero" }
       ↓
bone_add({ objectName: "Hero", boneName: "Root", head: [0,0,0], tail: [0,0,1] })
   → refs: { objectName: "Hero", boneName: "Root" }
       ↓
socket_add({ objectName: "Hero", boneName: "Root", socketName: "Weapon_Socket" })
   → refs: { objectName: "Weapon_Socket", boneName: "Root" }
```

The agent never has to parse text. It passes names forward.

## When to write a composite (vs. a primitive)

Write a **composite** if all of these are true:
- The flow is at least 3 primitives.
- All primitives belong in one undoable unit (single Ctrl+Z reverses the whole thing).
- A failure mid-flow should clean up, not leave a half-mutated state.
- Agents will commonly want the whole flow, not parts of it.

Write a **primitive** if:
- The operation is a single conceptual mutation.
- Agents might want to interleave it with other domain operations.
- Composing on the agent side gives meaningful flexibility.

Both can coexist. `armature_create_with_bones` is a composite; `bone_add` stays as a primitive.

## Composite implementation pattern (Python side)

```python
# BlenderAgent/handlers/armature.py
@handler("POST", "/armature/create_with_bones")
def create_with_bones(req):
    name = req["name"]
    bones = req["bones"]  # list of { name, head, tail, parent? }

    def main():
        # Pre-validation BEFORE any mutation
        if name in bpy.data.objects:
            raise HandlerError("OBJECT_EXISTS", f"object {name!r} already exists")

        created_objects: list[str] = []
        try:
            # Step 1: create armature data + object
            arm_data = bpy.data.armatures.new(name=name)
            arm_obj = bpy.data.objects.new(name=name, object_data=arm_data)
            bpy.context.scene.collection.objects.link(arm_obj)
            created_objects.append(arm_obj.name)

            # Step 2: enter edit mode and add bones
            with_mode(arm_obj, 'EDIT', lambda: _add_bones(arm_data, bones))

            # Step 3: one undo push at the end
            bpy.ops.ed.undo_push(message=f"Create armature {name!r} with {len(bones)} bones")

            return {
                "object_name": arm_obj.name,
                "bone_names": [b["name"] for b in bones],
            }
        except Exception:
            # Roll back our partial state
            for obj_name in created_objects:
                obj = bpy.data.objects.get(obj_name)
                if obj is not None:
                    bpy.data.objects.remove(obj, do_unlink=True)
            raise

    return run_on_main(main)
```

Five required pieces:
1. **Pre-validation** — fail fast before touching any data.
2. **Track what we created** — for rollback if step N fails.
3. **All `bpy.*` inside `main`** — never on the HTTP thread.
4. **One `undo_push` at the end** — meaningful message.
5. **try/except cleanup** — composites don't leave debris.

## ID-chain naming — keep it exact

`refs` keys must match the next tool's input parameter name. Blender is name-keyed, so:

| Tool returns | Next tool consumes |
|---|---|
| `refs.objectName` | `objectName` |
| `refs.materialName` | `materialName` |
| `refs.boneName` | `boneName` |
| `refs.actionName` | `actionName` |
| `refs.nodeName` | `nodeName` |
| `refs.modifierName` | `modifierName` |
| `refs.constraintName` | `constraintName` |
| `refs.collectionName` | `collectionName` |
| `refs.sceneName` | `sceneName` |
| `refs.objectNames[]` | (list enumerations) |

When introducing a new entity type, **add the row here AND** in [.claude/rules/mcp-tools.md](../../rules/mcp-tools.md) AND [.github/instructions/mcp-tools.instructions.md](../../../.github/instructions/mcp-tools.instructions.md).

## Designing a new tool — work backwards from the chain

1. **What does the agent know before calling?** → input schema.
2. **What does the agent need next?** → `refs` + `nextSteps`.
3. **What's the smallest atomic mutation?** → handler body.
4. **What can go wrong?** → `errorCode` values.

If step 4 produces a code not in the registry, add it everywhere (rules/instructions/handler/test).

## When chaining feels awkward, write a composite

Signal: the agent has to call `tool_A` → read response → call `tool_B` → read response → call `tool_C` → and **none of those intermediate states is useful on its own**. That's a composite waiting to happen.

Example: "rename a bone and update all references to it in vertex groups, constraints, drivers, and actions" — five primitives, no one wants the intermediate states. Ship `bone_rename_with_refs` as a composite that calls them all and emits one undo push.

## Failure modes table (per composite)

Every composite documents its failure modes in the handler docstring:

```python
def create_with_bones(req):
    """Create an armature with bones.

    Failure modes:
      OBJECT_EXISTS         — name collides with existing object; nothing changes.
      INVALID_PARAMS        — malformed bones list; nothing changes.
      BONE_PARENT_NOT_FOUND — a bone's `parent` references a name not in the list; partial armature is rolled back.
    """
```

The TS tool's description references "Failure modes documented in the handler" so the agent knows what to expect.
