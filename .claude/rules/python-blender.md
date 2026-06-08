---
applyTo: "BlenderAgent/**/*.py"
---

# Python (Blender addon) rules — Claude Code mirror

Mirror of [`.github/instructions/python-blender.instructions.md`](../../.github/instructions/python-blender.instructions.md). When you edit one, edit the other. Identical content; different harness location.

See the Copilot version for the full rule set:

- Threading + main-thread drain pattern (`bpy` is not thread-safe).
- API choices (`bpy.data` for data, `bpy.ops` for operators, `bmesh` for mesh edits, `mathutils` for math).
- Mode-aware mutation pattern (`with_mode`).
- Undo policy — one `bpy.ops.ed.undo_push` per composite.
- Context-override pattern for 3D-View-dependent operators.
- Error model — typed exceptions caught at handler boundary.
- Logging via `logging` module, never `print` from handlers.
