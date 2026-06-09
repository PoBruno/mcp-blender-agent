"""Handler package — importing this module side-effect-registers every handler.

Add new handler modules here. Order doesn't matter as long as each module's
top-level `@handler(...)` decorators are evaluated at import time.
"""

# Sprint 1 — Scene / collection / object / file / export
from . import scene  # noqa: F401
from . import collection  # noqa: F401
from . import view_layer  # noqa: F401
from . import object_ops  # noqa: F401
from . import collision  # noqa: F401
from . import uv  # noqa: F401
from . import material  # noqa: F401
from . import export_static  # noqa: F401
from . import file_io  # noqa: F401

# Sprint 2 — Modifiers, mesh edit, armature, bones, sculpt, shape keys, animation
from . import modifier  # noqa: F401
from . import mesh_edit  # noqa: F401
from . import armature  # noqa: F401
from . import bone  # noqa: F401
from . import constraint  # noqa: F401
from . import driver  # noqa: F401
from . import vertex_group  # noqa: F401
from . import sculpt  # noqa: F401
from . import shape_key  # noqa: F401
from . import animation  # noqa: F401
from . import metahuman  # noqa: F401
from . import socket  # noqa: F401
from . import bone_collection  # noqa: F401

# Sprint 3 — UV/bake, material/shader nodes, geometry nodes, compositor
from . import bake  # noqa: F401
from . import shader_node  # noqa: F401
from . import node_group  # noqa: F401
from . import geo_node  # noqa: F401
from . import compositor  # noqa: F401

# Sprint 4 — Lights, camera, render, library, export remainder, import
from . import light  # noqa: F401
from . import world  # noqa: F401
from . import camera  # noqa: F401
from . import render  # noqa: F401
from . import library  # noqa: F401
from . import asset  # noqa: F401
from . import export_animation  # noqa: F401
from . import import_ops  # noqa: F401

# Sprint 5 — exec_python (env-flagged)
from . import exec_python  # noqa: F401

# Sprint 6 — AAA pipeline: vision feedback, post-processing, parametric library
from . import vision  # noqa: F401
from . import postproc  # noqa: F401
from . import parametric  # noqa: F401
from . import generate  # noqa: F401
