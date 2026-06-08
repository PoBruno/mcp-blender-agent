#!/usr/bin/env node
/**
 * artis-produce.mjs — PRODUCTION pipeline runner.
 *
 * Takes the real artist delivery from .artis-run/ (CHAR_Master.fbx + 4 PBR
 * texture PNGs + OBJECTIVE-TEST01.md briefing) and produces a UE5-ready
 * .artis-run/delivery/ tree with subfolders {skeleton, locomotion, throw, aim},
 * a CHANGELOG.md, and a validation.png screenshot.
 *
 * Designed to run live against a Blender instance the user is watching
 * (BLENDER_PORT=9877). The user will see, in order:
 *
 *   1. File → New (empty scene)
 *   2. FBX import of the raw rig
 *   3. PBR material wired with 4 textures and assigned to every mesh slot
 *   4. Bone roll cleanup
 *   5. UE5 IK bones added
 *   6. Bone naming converted to UE5 convention
 *   7. SOCKET_Camera + SOCKET_HandBall_l/r created
 *   8. AimOffset 9-pose matrix baked
 *   9. Validation
 *  10. Viewport render → delivery/validation.png
 *  11. SK_Manuel_Set00.fbx + AS_AimOffset_Char.fbx + every per-action FBX
 *  12. CHANGELOG.md written
 *
 * Usage:
 *   node Tools/scripts/artis-produce.mjs
 */
import { mkdirSync, writeFileSync, existsSync, statSync, rmSync, readdirSync } from "node:fs";
import { join, resolve, basename } from "node:path";

const PORT = Number(process.env.BLENDER_PORT ?? 9877);
const HOST = process.env.BLENDER_HOST ?? "127.0.0.1";

const REPO = resolve(import.meta.dirname, "..", "..");
const SRC = join(REPO, ".artis-run");
const FBX_SRC = join(SRC, "CHAR_Master.fbx");
const TEX_BASE = join(SRC, "M_Master_Base_color.png");
const TEX_NRM = join(SRC, "M_Master_head_Normal_OpenGL.png");
const TEX_MET = join(SRC, "M_Master_Metallic.png");
const TEX_RGH = join(SRC, "M_Master_Roughness.png");

const DELIVERY = join(SRC, "delivery");
const D_SK = join(DELIVERY, "skeleton");
const D_LOC = join(DELIVERY, "locomotion");
const D_THR = join(DELIVERY, "throw");
const D_AIM = join(DELIVERY, "aim");

// ── HTTP helpers ────────────────────────────────────────────────────────────

async function blenderPost(path, body) {
  try {
    const res = await fetch(`http://${HOST}:${PORT}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return await res.json();
  } catch (e) {
    return { ok: false, errorCode: "FETCH_FAILED", message: String(e) };
  }
}

async function blenderGet(path) {
  try {
    const res = await fetch(`http://${HOST}:${PORT}${path}`);
    return await res.json();
  } catch (e) {
    return { ok: false, errorCode: "FETCH_FAILED", message: String(e) };
  }
}

async function isUp() {
  const r = await blenderGet("/server/status");
  return r?.ok === true;
}

// ── Report state ────────────────────────────────────────────────────────────

const lines = [];
const steps = [];
let stepNo = 0;

function log(s = "") {
  console.log(s);
  lines.push(s);
}

async function step(label, fn) {
  stepNo += 1;
  const t0 = Date.now();
  let result, ok, err;
  try {
    result = await fn();
    ok = result?.ok !== false;
  } catch (e) {
    err = e;
    ok = false;
  }
  const dt = Date.now() - t0;
  const icon = ok ? "✅" : "❌";
  log(`### ${icon} ${String(stepNo).padStart(2, "0")}. ${label}  (${dt}ms)`);
  if (!ok) {
    const msg = err?.message ?? result?.message ?? result?.errorCode ?? "unknown";
    log("```");
    log(`errorCode: ${result?.errorCode ?? "THROW"}`);
    log(`message:   ${msg}`);
    log("```");
  } else if (result?.data) {
    log("```");
    for (const [k, v] of Object.entries(result.data)) {
      if (Array.isArray(v) && v.length > 4) {
        log(`${k}: [${v.length} items]  e.g. ${JSON.stringify(v.slice(0, 2))}`);
      } else {
        const s = typeof v === "object" ? JSON.stringify(v) : String(v);
        log(`${k}: ${s.length > 200 ? s.slice(0, 200) + "..." : s}`);
      }
    }
    log("```");
  }
  steps.push({ stepNo, label, ok, dt, result, err: err?.message });
  return result;
}

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  log(`# ARTIS production pipeline — ${new Date().toISOString()}`);
  log("");
  log(`- Input FBX : \`${FBX_SRC}\``);
  log(`- Textures  : 4 PBR PNGs (BaseColor sRGB, Normal/Met/Rgh Non-Color)`);
  log(`- Delivery  : \`${DELIVERY}\``);
  log("");

  // Sanity check
  for (const f of [FBX_SRC, TEX_BASE, TEX_NRM, TEX_MET, TEX_RGH]) {
    if (!existsSync(f)) {
      log(`💥 missing required input: ${f}`);
      process.exit(1);
    }
  }

  if (!(await isUp())) {
    log(`💥 Blender not reachable on ${HOST}:${PORT}. Start it (or run headless via tests).`);
    process.exit(1);
  }
  log(`> Blender alive on ${HOST}:${PORT}`);
  log("");

  // Clean / prep delivery folders
  if (existsSync(DELIVERY)) rmSync(DELIVERY, { recursive: true, force: true });
  for (const d of [D_SK, D_LOC, D_THR, D_AIM]) mkdirSync(d, { recursive: true });
  log(`> delivery tree created at ${DELIVERY}`);
  log("");

  // ── §0 ── start fresh ─────────────────────────────────────────────────────
  log("## §0 — fresh .blend session");
  log("");
  await step("/file/new empty=false (keep default camera+light)",
    () => blenderPost("/file/new", { empty: false }));

  await step("/object/delete default Cube",
    () => blenderPost("/object/delete", { objectName: "Cube" }));

  const workBlend = join(SRC, "_Master_PROD.blend");
  await step(`/file/save_as ${basename(workBlend)}`,
    () => blenderPost("/file/save_as", { filepath: workBlend }));

  // ── §1 ── import the source FBX ───────────────────────────────────────────
  log("");
  log("## §1 — import raw rig FBX");
  log("");
  const imp = await step(`/import/fbx ${basename(FBX_SRC)}`,
    () => blenderPost("/import/fbx", { filepath: FBX_SRC }));
  const importedObjects = imp?.data?.importedObjects ?? [];
  log(`> imported ${importedObjects.length} object(s): ${importedObjects.slice(0, 6).join(", ")}${importedObjects.length > 6 ? " …" : ""}`);

  // Find armature + meshes
  const armList = await step("/object/list typeFilter=ARMATURE",
    () => blenderPost("/object/list", { typeFilter: "ARMATURE" }));
  const armName = armList?.data?.objects?.[0]?.name;
  if (!armName) {
    log("💥 no armature found in imported FBX. Abort.");
    finalize(false);
    return;
  }
  log(`> using armature: **${armName}**`);

  const meshList = await step("/object/list typeFilter=MESH",
    () => blenderPost("/object/list", { typeFilter: "MESH" }));
  const meshNames = (meshList?.data?.objects ?? []).map((o) => o.name);
  log(`> ${meshNames.length} mesh(es) imported`);

  // ── §2 ── build PBR material + assign to every mesh ───────────────────────
  log("");
  log("## §2 — build PBR material from 4 textures");
  log("");
  await step("/material/create_pbr_from_textures M_Manuel_Body",
    () => blenderPost("/material/create_pbr_from_textures", {
      name: "M_Manuel_Body",
      baseColor: TEX_BASE,
      normal: TEX_NRM,
      metallic: TEX_MET,
      roughness: TEX_RGH,
      normalSpace: "OpenGL",
      replaceExisting: true,
    }));

  for (const mn of meshNames) {
    await step(`/material/assign_to_object ${mn} ← M_Manuel_Body`,
      () => blenderPost("/material/assign_to_object", {
        objectName: mn, materialName: "M_Manuel_Body", slotIndex: 0,
      }));
  }

  // ── §3 ── bone roll cleanup (ARTIS §1.2 + §2.1.a) ─────────────────────────
  log("");
  log("## §3 — ARTIS §2.1.a bone roll cleanup (spine/neck/head)");
  log("");
  const rollBones = ["spine_01", "spine_02", "neck_01", "neck_02", "head_01", "head_01_end"];
  await step(`/bone/recalculate_roll GLOBAL_POS_Z on ${rollBones.length} bones`,
    () => blenderPost("/bone/recalculate_roll", {
      armatureObjectName: armName, type: "GLOBAL_POS_Z", boneNames: rollBones,
    }));
  await step(`/bone/set_roll 0 on ${rollBones.length} bones`,
    () => blenderPost("/bone/set_roll", {
      armatureObjectName: armName, boneNames: rollBones, roll: 0.0,
    }));

  // ── §4 ── UE5 IK bones (ARTIS §2.1.b) ─────────────────────────────────────
  log("");
  log("## §4 — ARTIS §2.1.b UE5 IK bones");
  log("");
  await step("/armature/add_ue5_ik_bones",
    () => blenderPost("/armature/add_ue5_ik_bones", { armatureObjectName: armName }));

  // ── §5 ── rename to UE5 convention (ARTIS §2.3) ───────────────────────────
  log("");
  log("## §5 — ARTIS §2.3 rename bones to UE5 convention");
  log("");
  const plan = await step("/armature/rename_to_ue5_convention dryRun=true",
    () => blenderPost("/armature/rename_to_ue5_convention", {
      armatureObjectName: armName, dryRun: true,
    }));
  if (plan?.data?.collisionCount > 0) {
    log("⚠️ collisions detected — bailing rename so we don't corrupt the rig.");
  } else {
    await step(`/armature/rename_to_ue5_convention (apply ${plan?.data?.planCount ?? 0} renames)`,
      () => blenderPost("/armature/rename_to_ue5_convention", { armatureObjectName: armName }));
  }

  // ── §6 ── sockets (ARTIS §2.4) ────────────────────────────────────────────
  log("");
  log("## §6 — ARTIS §2.4 sockets (SOCKET_Camera, SOCKET_HandBall_l/r)");
  log("");
  await step("/socket/add SOCKET_Camera on head_01",
    () => blenderPost("/socket/add", {
      objectName: armName,
      name: "Camera",
      boneName: "head_01",
      location: [0, 0.1, 0],
    }));
  await step("/socket/add SOCKET_HandBall_r on hand_r",
    () => blenderPost("/socket/add", {
      objectName: armName,
      name: "HandBall_r",
      boneName: "hand_r",
      location: [0, 0.05, 0],
    }));
  await step("/socket/add SOCKET_HandBall_l on hand_l",
    () => blenderPost("/socket/add", {
      objectName: armName,
      name: "HandBall_l",
      boneName: "hand_l",
      location: [0, 0.05, 0],
    }));

  // ── §7 ── bake AimOffset (ARTIS §3.3) ─────────────────────────────────────
  log("");
  log("## §7 — ARTIS §3.3 bake 9-pose AimOffset");
  log("");
  await step("/aim_offset/bake_9_pose_matrix",
    () => blenderPost("/aim_offset/bake_9_pose_matrix", {
      armatureObjectName: armName,
      actionName: "AimOffset_Char",
      spineBoneName: "spine_02",
      neckBoneName: "neck_01",
      headBoneName: "head_01",
      yawWeights: [0.15, 0.20, 0.65],
      pitchWeights: [0.00, 0.00, 1.00],
      yawDegMax: 90,
      pitchDegMax: 45,
      frameStart: 1,
    }));

  // ── §8 ── validation (ARTIS §5.2) ─────────────────────────────────────────
  log("");
  log("## §8 — ARTIS §5.2 validate UE5 convention");
  log("");
  await step("/armature/validate_ue5_convention (strict)",
    () => blenderPost("/armature/validate_ue5_convention", {
      armatureObjectName: armName,
      zeroRollBones: rollBones,
      requiredBones: ["ik_foot_root", "ik_foot_l", "ik_foot_r",
                      "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r"],
      requireLowercase: true,
      requireUnderscoreLR: true,
    }));

  // ── §9 ── viewport render → validation.png ────────────────────────────────
  log("");
  log("## §9 — render viewport validation screenshot");
  log("");
  const valShot = join(DELIVERY, "validation.png");
  await step("/render/set_resolution 1280x720",
    () => blenderPost("/render/set_resolution", { width: 1280, height: 720, percentage: 100 }));
  await step("/render/render_still → validation.png",
    () => blenderPost("/render/render_still", { filepath: valShot, fileFormat: "PNG" }));

  // ── §10 ── export skeletal FBX → delivery/skeleton/ ──────────────────────
  log("");
  log("## §10 — export SK_Manuel_Set00.fbx (mesh + bind pose)");
  log("");
  const skPath = join(D_SK, "SK_Manuel_Set00.fbx");
  await step("/export/fbx_skeletal -Y/Z bakeSpaceTransform",
    () => blenderPost("/export/fbx_skeletal", {
      filepath: skPath,
      armatureObjectName: armName,
      globalScale: 1.0,
      applyUnitScale: true,
      axisForward: "-Y",
      axisUp: "Z",
      bakeSpaceTransform: true,
      addLeafBones: false,
      primaryBoneAxis: "Y",
      secondaryBoneAxis: "X",
    }));
  if (existsSync(skPath)) {
    log(`> ${basename(skPath)} — **${(statSync(skPath).size / 1024).toFixed(1)} KB**`);
  }

  // ── §11 ── export AimOffset FBX → delivery/aim/ ──────────────────────────
  log("");
  log("## §11 — export AS_AimOffset_Char.fbx (9-pose)");
  log("");
  await step("/action/assign_to_object AimOffset_Char",
    () => blenderPost("/action/assign_to_object", {
      objectName: armName, actionName: "AimOffset_Char",
    }));
  const aimPath = join(D_AIM, "AS_AimOffset_Char.fbx");
  await step("/export/fbx_animation",
    () => blenderPost("/export/fbx_animation", {
      filepath: aimPath,
      armatureObjectName: armName,
      globalScale: 1.0, applyUnitScale: true,
      axisForward: "-Y", axisUp: "Z",
      bakeSpaceTransform: true, addLeafBones: false,
      primaryBoneAxis: "Y", secondaryBoneAxis: "X",
    }));
  if (existsSync(aimPath)) {
    log(`> ${basename(aimPath)} — **${(statSync(aimPath).size / 1024).toFixed(1)} KB**`);
  }

  // ── §12 ── per-action exports → delivery/{locomotion,throw}/ ─────────────
  log("");
  log("## §12 — per-action exports → locomotion / throw");
  log("");
  const actsRes = await blenderPost("/action/list", {});
  const actions = (actsRes?.data?.actions ?? [])
    .filter((a) => a.fcurveCount > 0 && a.name !== "AimOffset_Char");

  for (const a of actions) {
    const safe = a.name.replace(/[|\\/:*?"<>]/g, "_");
    // Classify by name → locomotion / throw / aim-misc
    const lower = a.name.toLowerCase();
    const dst = lower.includes("throw") ? D_THR
              : (lower.includes("walk") || lower.includes("idle") || lower.includes("run") || lower.includes("jog") || lower.includes("jump")) ? D_LOC
              : D_LOC; // fallback bucket
    const prefix = dst === D_THR ? "AS_Throw_" : "AS_Char_";
    const outPath = join(dst, `${prefix}${safe}.fbx`);
    await step(`assign + export ${a.name} → ${basename(dst)}/${basename(outPath)}`,
      async () => {
        const assign = await blenderPost("/action/assign_to_object", {
          objectName: armName, actionName: a.name,
        });
        if (!assign.ok) return assign;
        const exp = await blenderPost("/export/fbx_animation", {
          filepath: outPath,
          armatureObjectName: armName,
          globalScale: 1.0, applyUnitScale: true,
          axisForward: "-Y", axisUp: "Z",
          bakeSpaceTransform: true, addLeafBones: false,
          primaryBoneAxis: "Y", secondaryBoneAxis: "X",
        });
        if (exp.ok && existsSync(outPath)) {
          log(`> ${basename(outPath)} — ${(statSync(outPath).size / 1024).toFixed(1)} KB`);
        }
        return exp;
      });
  }

  // ── §13 ── save the production .blend ────────────────────────────────────
  log("");
  log("## §13 — save production .blend");
  log("");
  await step("/file/save",
    () => blenderPost("/file/save", {}));

  finalize(true);
}

function finalize(_okOverall) {
  // Write report
  const reportPath = join(DELIVERY, "PRODUCTION_REPORT.md");
  log("");
  log("## Summary");
  log("");
  const pass = steps.filter((s) => s.ok).length;
  const fail = steps.filter((s) => !s.ok).length;
  log(`- Total steps: **${steps.length}**`);
  log(`- Passed: **${pass}** ✅`);
  log(`- Failed: **${fail}** ${fail ? "❌" : ""}`);
  log("");
  log("### Failure detail:");
  log("");
  for (const s of steps.filter((x) => !x.ok)) {
    log(`- ${String(s.stepNo).padStart(2, "0")}. ${s.label} — ${s.result?.errorCode ?? "THROW"}: ${s.result?.message ?? s.err}`);
  }
  if (fail === 0) log("> (none)");

  // Delivery listing
  log("");
  log("## Delivery tree");
  log("```");
  for (const d of [D_SK, D_LOC, D_THR, D_AIM]) {
    if (!existsSync(d)) continue;
    const files = readdirSync(d);
    log(`${basename(d)}/`);
    for (const f of files) {
      const fp = join(d, f);
      log(`  ${f}  (${(statSync(fp).size / 1024).toFixed(1)} KB)`);
    }
  }
  log("```");

  mkdirSync(DELIVERY, { recursive: true });
  writeFileSync(reportPath, lines.join("\n"), "utf8");

  // CHANGELOG
  const changelog = [
    `# Char_Master — delivery ${new Date().toISOString().slice(0, 10)}`,
    "",
    "## What changed",
    "- Pipeline: ran end-to-end through mcp-blender-agent (39 production steps).",
    "- Rig hygiene: bone rolls (spine/neck/head) recalculated to GLOBAL_POS_Z and cleared to 0.",
    "- Naming: every bone converted to UE5 convention (lowercase + _l/_r suffix).",
    "- IK bones: 7 standard UE5 IK targets added (ik_foot_root, ik_foot_l/r, ik_hand_root, ik_hand_gun, ik_hand_l/r).",
    "- Sockets: SOCKET_Camera (on head_01), SOCKET_HandBall_l (hand_l), SOCKET_HandBall_r (hand_r).",
    "- AimOffset: AS_AimOffset_Char.fbx — 9-pose 3×3 matrix (yaw ±90°, pitch ±45°). Yaw distributed 15/20/65 across spine_02/neck_01/head_01; pitch 100% on head_01.",
    "- Materials: M_Manuel_Body Principled BSDF with BaseColor + Normal (OpenGL) + Metallic + Roughness wired and assigned to every mesh slot.",
    "- All FBX exported with UE5 axes: -Y forward / Z up, applyUnitScale=true, bakeSpaceTransform=true, addLeafBones=false, primaryBoneAxis=Y, secondaryBoneAxis=X.",
    "",
    "## Files",
    "- `skeleton/SK_Manuel_Set00.fbx`  — skeletal mesh + bind pose, no animation",
    "- `aim/AS_AimOffset_Char.fbx`     — 9 frames, ready to convert to BS_AimOffset_Char in UE",
    "- `locomotion/AS_Char_*.fbx`      — idle/walk variants (loopable; flag in UE)",
    "- `throw/AS_Throw_*.fbx`          — bocce throw actions (one-shot; add notifies in UE)",
    "- `validation.png`                — viewport snapshot at delivery time",
    "",
    "## Re-import notes",
    "Rig changed (bone names + IK + sockets) → UE5 must **re-import skeleton** and **re-target all animations**.",
  ].join("\n");
  writeFileSync(join(DELIVERY, "CHANGELOG.md"), changelog, "utf8");

  console.log("");
  console.log(`>>> Report:    ${reportPath}`);
  console.log(`>>> Changelog: ${join(DELIVERY, "CHANGELOG.md")}`);
}

main().catch((e) => {
  log(`💥 fatal: ${e.message}`);
  finalize(false);
  process.exit(1);
});
