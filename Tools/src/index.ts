#!/usr/bin/env node
/**
 * blender-agent MCP server entry point.
 *
 * Boots an McpServer over stdio and registers every tool group.
 * Headless Blender is NOT spawned automatically here — use `ensureBlenderRunning`
 * from blender-bridge.ts in tests/CI.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { registerServerTools } from "./tools/server.js";
import {
  registerCollectionTools,
  registerSceneTools,
  registerViewLayerTools,
} from "./tools/scene.js";
import { registerObjectTools } from "./tools/object.js";
import { registerMeshTools } from "./tools/mesh.js";
import { registerModifierTools } from "./tools/modifier.js";
import {
  registerMaterialTools,
  registerNodeGroupTools,
  registerShaderNodeTools,
} from "./tools/material.js";
import { registerUVTools } from "./tools/uv.js";
import { registerBakeTools } from "./tools/bake.js";
import {
  registerCompositorTools,
  registerGeoNodeTools,
} from "./tools/geo-node.js";
import {
  registerArmatureTools,
  registerBoneCollectionTools,
  registerBoneTools,
  registerConstraintTools,
  registerDriverTools,
  registerMetaHumanTools,
  registerShapeKeyTools,
  registerVertexGroupTools,
} from "./tools/rig.js";
import { registerAnimationTools } from "./tools/animation.js";
import {
  registerCollisionTools,
  registerSculptTools,
  registerSocketTools,
} from "./tools/sculpt-collision.js";
import {
  registerCameraTools,
  registerLightTools,
  registerRenderTools,
  registerWorldTools,
} from "./tools/lighting-render.js";
import {
  registerAssetTools,
  registerFileTools,
  registerLibraryTools,
} from "./tools/file.js";
import {
  registerExportAnimationTools,
  registerExportStaticTools,
  registerImportTools,
} from "./tools/export.js";
import { registerExecTools } from "./tools/exec.js";
import { registerVisionTools } from "./tools/vision.js";
import { registerPostprocTools } from "./tools/postproc.js";
import { registerParametricTools } from "./tools/parametric.js";

export function buildServer(): McpServer {
  const server = new McpServer({
    name: "blender-agent",
    version: "0.0.1",
  });

  // Sprint 0
  registerServerTools(server);

  // Sprint 1
  registerSceneTools(server);
  registerCollectionTools(server);
  registerViewLayerTools(server);
  registerObjectTools(server);
  registerCollisionTools(server);
  registerMaterialTools(server);
  registerUVTools(server);
  registerFileTools(server);
  registerExportStaticTools(server);

  // Sprint 2
  registerModifierTools(server);
  registerMeshTools(server);
  registerArmatureTools(server);
  registerBoneTools(server);
  registerBoneCollectionTools(server);
  registerConstraintTools(server);
  registerDriverTools(server);
  registerVertexGroupTools(server);
  registerShapeKeyTools(server);
  registerAnimationTools(server);
  registerMetaHumanTools(server);
  registerSocketTools(server);
  registerSculptTools(server);

  // Sprint 3
  registerBakeTools(server);
  registerShaderNodeTools(server);
  registerNodeGroupTools(server);
  registerGeoNodeTools(server);
  registerCompositorTools(server);

  // Sprint 4
  registerLightTools(server);
  registerWorldTools(server);
  registerCameraTools(server);
  registerRenderTools(server);
  registerLibraryTools(server);
  registerAssetTools(server);
  registerExportAnimationTools(server);
  registerImportTools(server);

  // Sprint 5
  registerExecTools(server);

  // Sprint 6 — AAA pipeline (vision feedback, post-processing, parametric library)
  registerVisionTools(server);
  registerPostprocTools(server);
  registerParametricTools(server);

  return server;
}

async function main(): Promise<void> {
  const server = buildServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("blender-agent MCP server failed to start:", err);
  process.exit(1);
});
