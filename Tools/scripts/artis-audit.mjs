#!/usr/bin/env node
/**
 * ARTIS audit — runs the entire ARTIS_AGENT_OBJECTIVE.md briefing against a
 * real .blend file, captures every step (OK / FAIL / GAP), and writes a
 * markdown report. Headless; does not touch the user's open Blender instance.
 *
 * Usage:
 *   node Tools/scripts/artis-audit.mjs
 *
 * Env:
 *   BLENDER_BIN, BLENDER_PORT (defaults 9877), ARTIS_BLEND (input .blend),
 *   ARTIS_OUT_DIR (output dir for FBX + report).
 */

import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync, existsSync, statSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..", "..");

const BLENDER_BIN =
  process.env.BLENDER_BIN ||
  "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Blender\\blender.exe";
const PORT = process.env.BLENDER_PORT || "9877";
const INPUT_BLEND =
  process.env.ARTIS_BLEND ||
  resolve(repoRoot, ".artis-run", "_Master_work.blend");
const OUT_DIR =
  process.env.ARTIS_OUT_DIR || resolve(repoRoot, ".artis-run", "out");

mkdirSync(OUT_DIR, { recursive: true });

const baseUrl = `http://localhost:${PORT}`;
const report = [];
const log = (line) => {
  console.log(line);
  report.push(line);
};

let stepCount = 0;
const recordStep = async (label, fn) => {
  stepCount += 1;
  const id = String(stepCount).padStart(2, "0");
  const t0 = Date.now();
  try {
    const res = await fn();
    const ms = Date.now() - t0;
    if (res && res.ok === false) {
      log(`### ❌ ${id}. ${label}  (${ms}ms)`);
      log("```");
      log(`errorCode: ${res.errorCode}`);
      log(`message:   ${res.message ?? ""}`);
      log("```");
      return res;
    }
    log(`### ✅ ${id}. ${label}  (${ms}ms)`);
    if (res && res.data) {
      const summary = summarize(res.data);
      if (summary) {
        log("```");
        log(summary);
        log("```");
      }
    }
    return res;
  } catch (err) {
    const ms = Date.now() - t0;
    log(`### 💥 ${id}. ${label}  (${ms}ms) — RAW THROW`);
    log("```");
    log(String(err?.stack ?? err));
    log("```");
    return { ok: false, errorCode: "THROW", message: String(err) };
  }
};

const recordGap = (label, why, proposedTool) => {
  log(`### ⚠️ GAP — ${label}`);
  log(`- **Why blocked:** ${why}`);
  log(`- **Proposed tool:** ${proposedTool}`);
};

function summarize(data) {
  const lines = [];
  for (const k of Object.keys(data)) {
    const v = data[k];
    if (Array.isArray(v)) {
      lines.push(`${k}: [${v.length} items]`);
      if (v.length > 0 && v.length <= 8 && typeof v[0] !== "object") {
        lines.push(`  ${JSON.stringify(v)}`);
      } else if (v.length > 0 && typeof v[0] === "object") {
        const sample = v.slice(0, 3).map((x) => JSON.stringify(x)).join("\n  ");
        lines.push(`  sample (first 3):\n  ${sample}`);
      }
    } else if (v && typeof v === "object") {
      lines.push(`${k}: ${JSON.stringify(v).slice(0, 200)}`);
    } else {
      lines.push(`${k}: ${JSON.stringify(v)}`);
    }
  }
  return lines.join("\n");
}

async function blenderPost(path, body = {}) {
  const res = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = await res.json().catch(() => ({ ok: false, errorCode: "BAD_JSON" }));
  return j;
}
async function blenderGet(path) {
  const res = await fetch(`${baseUrl}${path}`);
  return res.json();
}

async function isUp() {
  try {
    const r = await fetch(`${baseUrl}/server/status`);
    return r.ok;
  } catch {
    return false;
  }
}

async function startBlender() {
  if (await isUp()) {
    log("> Blender already running on port " + PORT);
    return null;
  }
  const pyCode = [
    "import sys",
    `sys.path.insert(0, r"${repoRoot}")`,
    "import BlenderAgent",
    "BlenderAgent.serve_blocking()",
  ].join("\n");

  const proc = spawn(
    BLENDER_BIN,
    ["--background", INPUT_BLEND, "--python-expr", pyCode],
    {
      env: { ...process.env, BLENDER_AGENT_PORT: PORT },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  proc.stderr.on("data", (b) => process.stderr.write(`[blender] ${b}`));
  proc.stdout.on("data", (b) => process.stderr.write(`[blender] ${b}`));

  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    if (await isUp()) return proc;
    await new Promise((r) => setTimeout(r, 750));
  }
  throw new Error("Blender did not come up in 90s");
}

async function stopBlender(proc) {
  if (!proc) return;
  try {
    await blenderPost("/server/shutdown", {});
  } catch {}
  try {
    proc.kill();
  } catch {}
}

// ─────────────────────────────────────────────────────────────────────────────

async function main() {
  log("# ARTIS audit report");
  log("");
  log(`- Input .blend: \`${INPUT_BLEND}\``);
  log(`- Output dir:   \`${OUT_DIR}\``);
  log(`- Blender:      \`${BLENDER_BIN}\``);
  log(`- Date:         ${new Date().toISOString()}`);
  log("");
  log("Steps below mirror the ARTIS_AGENT_OBJECTIVE.md briefing sections.");
  log("Status: ✅ pass, ❌ tool-returned error, 💥 raw throw, ⚠️ GAP (no tool).");
  log("");

  if (!existsSync(INPUT_BLEND)) {
    log(`> ERROR: input .blend not found at ${INPUT_BLEND}`);
    return 2;
  }

  log("## Bootstrap");
  log("");
  const proc = await startBlender();

  try {
    // ── Discovery ────────────────────────────────────────────────────────────
    log("");
    log("## 1. Discovery — what's inside _Master.blend?");
    log("");

    const allObjects = await recordStep("/object/list — enumerate every object",
      () => blenderPost("/object/list", {}));

    const armRes = await recordStep("/object/list typeFilter=ARMATURE",
      () => blenderPost("/object/list", { typeFilter: "ARMATURE" }));

    const armatures = armRes?.data?.objects ?? [];
    if (armatures.length === 0) {
      log("> ❌ No armature found in scene — aborting briefing flow");
      return 3;
    }
    const armName = armatures[0].name;
    log(`> Using armature: **${armName}**`);

    await recordStep(`/object/get_info ${armName}`,
      () => blenderPost("/object/get_info", { objectName: armName }));

    await recordStep("/object/list typeFilter=MESH",
      () => blenderPost("/object/list", { typeFilter: "MESH" }));

    await recordStep("/action/list — discover existing animations",
      () => blenderPost("/action/list", {}));

    // ── Section 1.2 audit: rolls ──────────────────────────────────────────────
    log("");
    log("## 2. ARTIS §1.2 — audit bone rolls");
    log("");

    const boneListRes = await recordStep(`/bone/list ${armName}`,
      () => blenderPost("/bone/list", { armatureObjectName: armName }));

    const allBones = boneListRes?.data?.bones ?? [];
    log("");
    log(`> Armature has **${allBones.length}** bones total.`);
    log("");

    // Find the spine/neck/head chain that briefing complains about
    const targetNames = ["spine_01", "spine_02", "spine_03", "neck_01", "neck_02",
                         "head_01", "head_01_end"];
    const present = allBones.filter((b) => targetNames.includes(b.name));
    const rolled = present.filter((b) => Math.abs(b.roll) > 0.01);

    log("### Spine/neck/head chain found:");
    log("```");
    log("name           roll(rad)   roll(deg)");
    for (const b of present) {
      const deg = (b.roll * 180) / Math.PI;
      log(`${b.name.padEnd(15)} ${b.roll.toFixed(4).padStart(8)}   ${deg.toFixed(2).padStart(8)}`);
    }
    log("```");
    log("");
    log(`> **${rolled.length}** out of ${present.length} target bones have rolled axes (|roll|>0.01).`);
    log("");

    // ── Section 1.2 fix: recalculate_roll + manual zero ──────────────────────
    log("");
    log("## 3. ARTIS §2.1.a — fix bone rolls (recalculate + clear)");
    log("");

    const targetsPresent = present.map((b) => b.name);
    if (targetsPresent.length > 0) {
      await recordStep(`/bone/recalculate_roll GLOBAL_POS_Z on ${targetsPresent.length} bones`,
        () => blenderPost("/bone/recalculate_roll", {
          armatureObjectName: armName,
          boneNames: targetsPresent,
          type: "GLOBAL_POS_Z",
        }));

      // Hard-zero in case recalculate couldn't resolve a vertical bone
      await recordStep(`/bone/set_roll 0 on ${targetsPresent.length} bones`,
        () => blenderPost("/bone/set_roll", {
          armatureObjectName: armName,
          boneNames: targetsPresent,
          roll: 0.0,
        }));

      const afterRes = await recordStep("/bone/list verify rolls cleared",
        () => blenderPost("/bone/list", { armatureObjectName: armName }));
      const afterTargets = (afterRes?.data?.bones ?? [])
        .filter((b) => targetNames.includes(b.name));
      log("### Rolls after cleanup:");
      log("```");
      for (const b of afterTargets) {
        const deg = (b.roll * 180) / Math.PI;
        log(`${b.name.padEnd(15)} ${b.roll.toFixed(4).padStart(8)}   ${deg.toFixed(2).padStart(8)}`);
      }
      log("```");
    } else {
      log("> No spine/neck/head bones found — skipping roll fix.");
    }

    // ── Section 2.1.b: UE5 IK bones ──────────────────────────────────────────
    log("");
    log("## 4. ARTIS §2.1.b — add UE5 IK control bones");
    log("");

    await recordStep(`/armature/add_ue5_ik_bones ${armName}`,
      () => blenderPost("/armature/add_ue5_ik_bones", {
        armatureObjectName: armName,
      }));

    await recordStep("/armature/add_ue5_ik_bones (idempotency check)",
      () => blenderPost("/armature/add_ue5_ik_bones", {
        armatureObjectName: armName,
      }));

    // ── Section 2.4: sockets ─────────────────────────────────────────────────
    log("");
    log("## 5. ARTIS §2.4 — create sockets (Camera + HandBall_R/L)");
    log("");

    // Find a head_01 + hand_l/r — if they don't exist we GAP
    const haveHead = allBones.some((b) => b.name === "head_01");
    const haveHandR = allBones.some((b) => b.name === "hand_r");
    const haveHandL = allBones.some((b) => b.name === "hand_l");
    const haveNeck = allBones.some((b) => b.name === "neck_01");
    const haveSpine2 = allBones.some((b) => b.name === "spine_02");

    // Diagnostic — what does the actual rig look like?
    const ue5ish = allBones
      .map((b) => b.name)
      .filter((n) => /^(spine|neck|head|hand|foot|thigh|calf|upperarm|lowerarm|clavicle|pelvis|root)/i.test(n));
    log("### UE5-style bone names found in this rig:");
    log("```");
    log(ue5ish.slice(0, 40).join("\n"));
    if (ue5ish.length > 40) log(`... (+${ue5ish.length - 40} more)`);
    log("```");
    log("");

    if (haveHead) {
      await recordStep("/socket/add SOCKET_Camera on head_01",
        () => blenderPost("/socket/add", {
          objectName: armName,
          name: "Camera",
          boneName: "head_01",
          location: [0, 0.1, 0],
        }));
    } else {
      recordGap("SOCKET_Camera", "no head_01 bone in this armature",
        "n/a — naming mismatch with briefing; needs manual mapping");
    }

    if (haveHandR) {
      await recordStep("/socket/add SOCKET_HandBall_R on hand_r",
        () => blenderPost("/socket/add", {
          objectName: armName,
          name: "HandBall_R",
          boneName: "hand_r",
          location: [0, 0, 0],
        }));
    } else {
      recordGap("SOCKET_HandBall_R", "no hand_r bone in this armature",
        "n/a — naming mismatch; consider /armature/map_to_ue5_naming composite");
    }

    if (haveHandL) {
      await recordStep("/socket/add SOCKET_HandBall_L on hand_l",
        () => blenderPost("/socket/add", {
          objectName: armName,
          name: "HandBall_L",
          boneName: "hand_l",
          location: [0, 0, 0],
        }));
    }

    // ── Section 3.3: AimOffset 9-pose ────────────────────────────────────────
    log("");
    log("## 6. ARTIS §3.3 — bake 9-pose AimOffset");
    log("");

    if (!haveHead) {
      recordGap("AimOffset", "no head_01 bone — can't bake head/spine rotations",
        "n/a — needs armature with head_01/neck_01/spine_02 present");
    } else if (!haveNeck || !haveSpine2) {
      log(`> head_01 found, but neck_01=${haveNeck} spine_02=${haveSpine2} — falling back to head-only 9-pose.`);
      // Fallback to head-only flow
      await recordStep("/action/create AimOffset_Manuel",
        () => blenderPost("/action/create", { name: "AimOffset_Manuel" }));
      await recordStep("/action/assign_to_object AimOffset_Manuel -> armature",
        () => blenderPost("/action/assign_to_object", {
          objectName: armName,
          actionName: "AimOffset_Manuel",
        }));
      await recordStep("/scene/set_frame_range 1..9",
        () => blenderPost("/scene/set_frame_range", { frameStart: 1, frameEnd: 9 }));

      const DEG = Math.PI / 180;
      const poses = [
        [1, -90, 45], [2, 0, 45], [3, 90, 45],
        [4, -90, 0], [5, 0, 0], [6, 90, 0],
        [7, -90, -45], [8, 0, -45], [9, 90, -45],
      ];
      let posesPassed = 0;
      for (const [frame, yaw, pitch] of poses) {
        const cy = Math.cos((yaw * DEG) / 2);
        const sy = Math.sin((yaw * DEG) / 2);
        const cp = Math.cos((pitch * DEG) / 2);
        const sp = Math.sin((pitch * DEG) / 2);
        const quat = [cy * cp, cy * sp, sy * sp, sy * cp];
        const setRes = await blenderPost("/bone/set_pose_transform", {
          armatureObjectName: armName,
          boneName: "head_01",
          rotationQuaternion: quat,
        });
        const kfRes = await blenderPost("/keyframe/bone_pose", {
          armatureObjectName: armName,
          boneName: "head_01",
          frame,
          channels: ["rotation_quaternion"],
        });
        if (setRes?.ok && kfRes?.ok) posesPassed += 1;
      }
      log(`### ✅ AimOffset head-only 9 poses baked (${posesPassed}/9)`);
    } else {
      // Full 3-bone composite
      await recordStep("/aim_offset/bake_9_pose_matrix (3-bone distribution, ARTIS §3.3)",
        () => blenderPost("/aim_offset/bake_9_pose_matrix", {
          armatureObjectName: armName,
          actionName: "AimOffset_Manuel",
          spineBoneName: "spine_02",
          neckBoneName: "neck_01",
          headBoneName: "head_01",
          // briefing defaults: 60/40 yaw split, pitch mainly head
        }));
    }

    // ── Section 5.2: validation ──────────────────────────────────────────────
    log("");
    log("## 7. ARTIS §5.2 — validate UE5 convention");
    log("");

    const validateRes = await recordStep("/armature/validate_ue5_convention (strict)",
      () => blenderPost("/armature/validate_ue5_convention", {
        armatureObjectName: armName,
        zeroRollBones: targetsPresent,
        requiredBones: ["ik_foot_root", "ik_foot_l", "ik_foot_r",
                        "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r"],
        requireLowercase: true,
        requireUnderscoreLR: true,
      }));

    if (validateRes?.data?.failures?.length) {
      log("### Validation failures (first 30):");
      log("```");
      log("check               bone                          reason");
      for (const f of validateRes.data.failures.slice(0, 30)) {
        log(`${(f.check ?? '').padEnd(20)}${(f.boneName ?? '').padEnd(30)}${f.reason ?? ''}`);
      }
      if (validateRes.data.failures.length > 30) {
        log(`... (+${validateRes.data.failures.length - 30} more)`);
      }
      log("```");
      const byCheck = {};
      for (const f of validateRes.data.failures) {
        byCheck[f.check] = (byCheck[f.check] ?? 0) + 1;
      }
      log("### Failure totals by check:");
      log("```");
      for (const [k, v] of Object.entries(byCheck)) log(`${k.padEnd(20)} ${v}`);
      log("```");
    }

    // ── Auto-fix: rename to UE5 convention ───────────────────────────────────
    log("");
    log("## 7b. Auto-fix — rename bones to UE5 convention (.L→_l, lowercase)");
    log("");

    const dryRes = await recordStep("/armature/rename_to_ue5_convention dryRun=true",
      () => blenderPost("/armature/rename_to_ue5_convention", {
        armatureObjectName: armName,
        dryRun: true,
      }));
    if (dryRes?.data?.planCount > 0) {
      log(`> Plan: ${dryRes.data.planCount} bones to rename, ${dryRes.data.collisionCount ?? 0} collisions.`);
      if (dryRes.data.collisions?.length) {
        log("```");
        for (const c of dryRes.data.collisions.slice(0, 10)) {
          log(`${c.from} → ${c.to}  (${c.reason})`);
        }
        log("```");
      }
    }
    const renameRes = await recordStep("/armature/rename_to_ue5_convention (apply)",
      () => blenderPost("/armature/rename_to_ue5_convention", {
        armatureObjectName: armName,
      }));
    log(`> renamed ${renameRes?.data?.renamedCount ?? 0} bones`);

    const reValidate = await recordStep("/armature/validate_ue5_convention (post-rename)",
      () => blenderPost("/armature/validate_ue5_convention", {
        armatureObjectName: armName,
        requiredBones: ["ik_foot_root", "ik_foot_l", "ik_foot_r",
                        "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r"],
        requireLowercase: true,
        requireUnderscoreLR: true,
      }));
    if (reValidate?.data?.failures?.length) {
      const byCheck = {};
      for (const f of reValidate.data.failures) {
        byCheck[f.check] = (byCheck[f.check] ?? 0) + 1;
      }
      log("### Remaining failures after auto-fix:");
      log("```");
      for (const [k, v] of Object.entries(byCheck)) log(`${k.padEnd(20)} ${v}`);
      log("```");
    } else {
      log("> ✅ Armature now passes UE5 convention check.");
    }

    // ── Section 4.1: export skeletal FBX ─────────────────────────────────────
    log("");
    log("## 8. ARTIS §4.1 — export skeletal FBX (UE5 axes)");
    log("");

    const skPath = join(OUT_DIR, "SK_Manuel_Set00.fbx");
    const skRes = await recordStep("/export/fbx_skeletal -Y forward, Z up, bakeSpaceTransform",
      () => blenderPost("/export/fbx_skeletal", {
        filepath: skPath,
        armatureObjectName: armName,
        globalScale: 1.0,
        applyUnitScale: true,
        axisForward: "-Y",
        axisUp: "Z",
        bakeSpaceTransform: true,
        useArmatureDeformOnly: true,
        addLeafBones: false,
        bakeAnim: false,
        useMeshModifiers: true,
        primaryBoneAxis: "Y",
        secondaryBoneAxis: "X",
      }));

    if (skRes?.ok && existsSync(skPath)) {
      log(`> Exported \`${skPath}\` — **${(statSync(skPath).size / 1024).toFixed(1)} KB**`);
    }

    // ── Section 4.2: export animation FBX (AimOffset) ────────────────────────
    log("");
    log("## 9. ARTIS §4.2 — export AimOffset animation FBX");
    log("");

    if (!haveHead) {
      log("> Skipped — no head_01 means no AimOffset was baked.");
    } else {
      const aimPath = join(OUT_DIR, "AS_AimOffset_Manuel.fbx");
      const aimRes = await recordStep("/export/fbx_animation AimOffset",
        () => blenderPost("/export/fbx_animation", {
          filepath: aimPath,
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
      if (aimRes?.ok && existsSync(aimPath)) {
        log(`> Exported \`${aimPath}\` — **${(statSync(aimPath).size / 1024).toFixed(1)} KB**`);
      }
    }

    // ── Locomotion FBX per-action (existing actions) ─────────────────────────
    log("");
    log("## 10. ARTIS §3.1 — export each existing action as its own FBX");
    log("");

    const actsRes = await blenderPost("/action/list", {});
    const actions = (actsRes?.data?.actions ?? []).filter((a) => a.fcurveCount > 0);
    if (actions.length === 0) {
      log("> No actions with fcurves in this .blend. ARTIS locomotion table (§3.1)");
      log("> requires the artist to have produced Idle/Walk/Run actions; none here.");
    } else {
      for (const a of actions) {
        // Sanitize: '|' / '\' / '/' / ':' / '*' / '?' / '"' / '<' / '>' invalid on Windows
        const safe = a.name.replace(/[|\\/:*?"<>]/g, "_");
        await recordStep(`assign + export action ${a.name} → AS_${safe}.fbx`, async () => {
          const assign = await blenderPost("/action/assign_to_object", {
            objectName: armName,
            actionName: a.name,
          });
          if (!assign.ok) return assign;
          const outPath = join(OUT_DIR, `AS_${safe}.fbx`);
          const exp = await blenderPost("/export/fbx_animation", {
            filepath: outPath,
            armatureObjectName: armName,
            globalScale: 1.0,
            applyUnitScale: true,
            axisForward: "-Y",
            axisUp: "Z",
            bakeSpaceTransform: true,
            addLeafBones: false,
            primaryBoneAxis: "Y",
            secondaryBoneAxis: "X",
          });
          if (exp.ok && existsSync(outPath)) {
            log(`> exported ${outPath} (${(statSync(outPath).size / 1024).toFixed(1)} KB)`);
          }
          return exp;
        });
      }
    }

    log("");
    log("## Done");
    log("");
    log(`Total steps: ${stepCount}`);
  } finally {
    await stopBlender(proc);
  }

  const reportPath = join(OUT_DIR, "AUDIT_REPORT.md");
  writeFileSync(reportPath, report.join("\n"));
  console.log(`\n>>> Report written to ${reportPath}\n`);
  return 0;
}

main()
  .then((code) => process.exit(code ?? 0))
  .catch((err) => {
    console.error("audit crashed:", err);
    process.exit(1);
  });
