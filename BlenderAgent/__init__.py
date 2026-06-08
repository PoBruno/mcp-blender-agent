"""BlenderAgent — MCP-driven control surface for Blender 4.2 LTS+ (tested on 5.x).

This addon runs an HTTP server inside Blender on port 9877 (configurable via
BLENDER_AGENT_PORT env var). The HTTP server runs on a background thread but
all `bpy.*` calls are marshalled to the main thread via `bpy.app.timers`
because `bpy` is not thread-safe.

See .claude/docs/ARCHITECTURE.md for the full design.
"""

bl_info = {
    "name": "BlenderAgent",
    "description": "MCP-driven control surface for AI coding agents.",
    "author": "PoBruno",
    "version": (0, 0, 1),
    "blender": (4, 2, 0),
    "location": "Background HTTP server on port 9877",
    "category": "Development",
    "support": "COMMUNITY",
    "doc_url": "https://github.com/PoBruno/mcp-blender-agent",
    "tracker_url": "https://github.com/PoBruno/mcp-blender-agent/issues",
}

import logging

from . import server

logger = logging.getLogger("BlenderAgent")


def register() -> None:
    """Blender addon entry point — called when the user enables the addon."""
    logger.info("BlenderAgent: register() called")
    server.start()


def unregister() -> None:
    """Blender addon teardown — called when the user disables the addon."""
    logger.info("BlenderAgent: unregister() called")
    server.stop()


def serve_blocking() -> None:
    """Headless entry point used by `blender --background --python-expr ...`.

    Starts the server then blocks the main thread, draining the timer queue
    until SIGINT or a /server/shutdown POST. This is what the vitest harness
    invokes; it is NOT used in the interactive (addon) path.
    """
    import time

    server.start()
    logger.info("BlenderAgent: serve_blocking entered")
    try:
        # The drain runs on `bpy.app.timers`. In `--background` mode, timers
        # only fire if the main thread is idle. We pump them manually here.
        while not server.shutdown_requested():
            server.drain_once()
            time.sleep(0.016)
    except KeyboardInterrupt:
        logger.info("BlenderAgent: KeyboardInterrupt — shutting down")
    finally:
        server.stop()


if __name__ == "__main__":
    # When run via `blender --python BlenderAgent/__init__.py`, register manually.
    register()
