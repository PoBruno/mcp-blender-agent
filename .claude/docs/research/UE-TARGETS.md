# UE-TARGETS.md

The export contract every Blender → Unreal flow must satisfy. Drawn from official UE 5.7 docs (FBX Skeletal Mesh Pipeline, Third/First Person Templates, Lyra Sample Game, MetaHuman documentation, Nanite, Lumen) plus the well-known ARKit 52 blendshape spec.

This file is the **source of truth for Phase 4 export tools** in [TOOL-CATALOG.md](TOOL-CATALOG.md). Any export tool whose output cannot satisfy at least one section of this contract is incomplete.

---

## 0. Conventions and axes — the foundation

| Axis / Unit | Blender (4.2+) | Unreal Engine 5 | Conversion rule for FBX export |
|---|---|---|---|
| Up axis | +Z | +Z | match (no rotation needed) |
| Forward axis | −Y | +X | rotate 90° around Z, OR set `axis_forward='Y'`, `axis_up='Z'` in FBX exporter and let it remap |
| Scale unit | 1 m | 1 cm (1 UE Unit = 1 cm) | FBX exporter `global_scale=1.0` + `apply_unit_scale=True` produces correct cm for UE |
| Handedness | right-handed | left-handed | FBX auto-converts; verify with the import-then-export round-trip test |
| FBX version | configurable | uses **FBX SDK 2020.2** | export with `version='BIN7400'` (FBX 2014+ binary) — older ASCII can break |

**Acceptance test for axes:** import a `BP_ThirdPersonCharacter` skeleton, re-export through Blender, re-import into UE — the bone roll on `pelvis` must be 0° (any drift = axis remap is wrong).

---

## 1. UE5 Third Person / First Person template — the SK_Mannequin contract

**Source:** [Third Person Template](https://dev.epicgames.com/documentation/en-us/unreal-engine/third-person-template-in-unreal-engine), [First Person Template](https://dev.epicgames.com/documentation/en-us/unreal-engine/first-person-template-in-unreal-engine), [FBX Skeletal Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine).

### 1.1 Skeletons

The UE5 Mannequins **Manny** (`SKM_Manny`) and **Quinn** (`SKM_Quinn`) share the **UE5 Mannequin skeleton** which is the same skeleton hierarchy as MetaHumans (Lyra docs: *"share the same core skeleton hierarchy as MetaHumans, with a compatible animation system"*).

**Required bone hierarchy** (root → leaves; bone names case-sensitive):

```
root
├── pelvis
│   ├── spine_01 → spine_02 → spine_03 → spine_04 → spine_05
│   │   ├── neck_01 → neck_02 → head
│   │   ├── clavicle_l → upperarm_l → lowerarm_l → hand_l
│   │   │   ├── thumb_01_l → thumb_02_l → thumb_03_l
│   │   │   ├── index_metacarpal_l → index_01_l → index_02_l → index_03_l
│   │   │   ├── middle_metacarpal_l → middle_01_l → middle_02_l → middle_03_l
│   │   │   ├── ring_metacarpal_l → ring_01_l → ring_02_l → ring_03_l
│   │   │   └── pinky_metacarpal_l → pinky_01_l → pinky_02_l → pinky_03_l
│   │   └── clavicle_r → … (mirror with _r suffix)
│   ├── thigh_l → calf_l → foot_l → ball_l
│   └── thigh_r → calf_r → foot_r → ball_r
└── (IK virtual chain, parented under root, NOT skinned)
    ├── ik_foot_root → ik_foot_l, ik_foot_r
    └── ik_hand_root → ik_hand_gun → ik_hand_l, ik_hand_r
```

**Rules the exporter must enforce:**

1. **Root bone is always named `root`** at world origin, axis-aligned with world.
2. **Pivot point of the skeletal mesh = root bone position** (per FBX Skeletal Mesh Pipeline: *"The pivot point of a Skeletal Mesh is always located at the root bone/joint of the skeleton"*). Mesh transformation in Blender is irrelevant — only the root bone matters.
3. **IK bones** (`ik_foot_*`, `ik_hand_*`) exist in the skeleton but **have zero vertex weights**. Required for UE5 IK Rig retargeting and Mannequin control rigs (`CR_Mannequin_BasicFootIK`, `CR_Mannequin_Body`).
4. **Naming suffixes** are `_l` / `_r` (not `.L` / `.R` — Blender convention must be normalized at export). The agent's bone-rename tool must offer both directions.
5. **A-pose** (arms ~45° down from horizontal), not T-pose, for Mannequin compatibility.

### 1.2 Skeletal Mesh requirements

- **Triangulated** before export (FBX pipeline doc: *"meshes in Unreal Engine must be triangulated"*). Prefer manual triangulation in Blender; auto-triangulation in the FBX exporter is a last resort.
- **Single mesh OR multi-part** ("modular character"): multiple meshes skinned to the same skeleton, exported in one FBX. UE imports them as one Skeletal Mesh with multiple sections.
- **Materials order matters**: for characters, slot 0 = body, slot 1 = head, etc. The exporter must preserve material slot order (Blender `obj.material_slots[i]` index).
- **UV channels**: multiple UV sets supported. Channel 0 = base color/PBR sample, channel 1 reserved for lightmaps if baked lighting is used (rare under Lumen — see §5).
- **Vertex colors**: one set per mesh, transferred via FBX with no special setup.
- **Smoothing groups**: enabled via FBX exporter `mesh_smooth_type='FACE'`.
- **Vertex group names must match bone names exactly.** No `.001` suffixes, no case mismatches. Unweighted vertices = warning on import; auto-fixed by binding to nearest bone.

### 1.3 Animation requirements

- **Mannequin animation set** lives under `Content/Characters/Mannequins/Animations` — there are two sets (Manny + Quinn) but they target the same skeleton, retargeted via [IK Rig](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-ik-rig).
- **Per-clip export:** one Action per FBX (the UE FBX pipeline doc states: *"only a single animation for each Skeletal Mesh can be imported in a single file"*). The agent's `export_fbx_animation` composite must bake one Action at a time.
- **Frame rate**: 30 fps for retail Mannequin animations; 60 fps acceptable for cinematics. Blender scene `render.fps` must be set before bake.
- **Root motion**: if used, must be baked onto the `root` bone (not `pelvis`). UE's "Enable Root Motion" checkbox on the AnimSequence consumes this.
- **NLA strips** can be exported sequentially as separate Actions by enabling "NLA Strips" in the FBX exporter and looping the export tool per strip.

### 1.4 Sockets

UE5 Sockets are bone-relative offset transforms attached to the **Skeleton Asset** (shared across meshes) or the **Skeletal Mesh** (mesh-exclusive). Used for weapons, accessories, particle attach points.

**Blender ↔ UE Socket bridge:** create an Empty in Blender parented to a bone (via "Bone" parenting). Name it with prefix `SOCKET_` (convention). The agent's `export_fbx_skeletal` tool detects `SOCKET_*` empties and writes them as FBX nodes parented to the target bone — UE recognizes these as Sockets on import.

### 1.5 LODs

- **LOD group naming** (Maya/Max convention preserved by FBX): wrap all LOD meshes in an empty/group named `LOD_<MeshName>`.
- LOD0 = full detail, LOD1+ = decimated. The agent's `mesh_create_lods` composite must produce N decimated copies + group them.
- UE also accepts per-LOD FBX (import as additional LODs in the Skeletal Mesh Editor).

### 1.6 Morph Targets

- Blender Shape Keys → FBX → UE Morph Targets is a 1:1 mapping when the FBX exporter has `add_leaf_bones=False, bake_anim=False` and shape keys are unmuted at export time.
- Shape key **names become Morph Target names**. Keep them clean (no spaces, no `.001`).
- **Nanite does NOT support Morph Targets** (Nanite doc: *"Deformation with Morph Targets is not supported with Nanite"*). For Nanite skeletal meshes, deformation must come from bones only.

---

## 2. UE5 Lyra Starter Game — modular character + gameplay-ready

**Source:** [Lyra Sample Game](https://dev.epicgames.com/documentation/en-us/unreal-engine/lyra-sample-game-in-unreal-engine).

### 2.1 What Lyra adds on top of §1

- **Same SK_Mannequin skeleton.** No extension; Lyra reuses Manny / Quinn meshes and animations.
- **Gameplay Feature Plugins** (ShooterCore, ShooterMaps, TopDownArena) are the modular architecture — Lyra ships content as plugin assets, not under `Content/`.
- **World Partition** maps (`L_Convolution_Blockout`, `L_Expanse`): levels are streamed by grid cells. Blender-exported levels for Lyra should be **modular kits** (small reusable static meshes), not monolithic world meshes.
- **Animation Blueprint + Control Rig** (`ABP_Manny`, `CR_Mannequin_BasicFootIK`, `CR_Mannequin_Body`): Lyra's anim system is IK-Rig-driven. Animations exported from Blender must be compatible with the IK Rig retargeting (means: skeleton hierarchy must match §1.1 exactly).

### 2.2 What the export contract adds for Lyra

- **Modular meshes with shared materials:** export sets of small static meshes that snap on a grid (10/50/100 UE units = 10/50/100 cm). Blender objects should be authored on a matching grid (`scene.unit_settings.length_unit='METERS'`, `tool_settings.use_snap=True`, snap increment 0.1m/0.5m/1m).
- **Material instance ready:** materials should expose simple parameters (base color, roughness, metallic, normal). The agent's `material_create_principled_for_ue` composite must emit a Principled BSDF with only the parameters UE's Material Importer maps cleanly (base color, metallic, roughness, normal, emissive, opacity).
- **M_PrototypeGrid material** (the gray grid in Lyra blockouts) is recreated in Blender via a checker-grid procedural material — the agent's `material_create_prototype_grid` composite produces this from scratch.

---

## 3. MetaHuman — face rig contract

**Source:** [MetaHuman Documentation](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-documentation-in-unreal-engine), [MetaHuman Facial Description Standard](https://dev.epicgames.com/documentation/en-us/metahuman/mh-standards-docs), [MetaHuman Animator](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-animator), [Apple ARKit blendshape spec](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation).

### 3.1 Body skeleton — shared with Mannequin

Per the Lyra doc: Mannequin and MetaHuman share the **same core body skeleton hierarchy** (§1.1). The only addition is a face rig anchored at the `head` bone.

### 3.2 ARKit 52 blendshapes — the canonical facial set

MetaHuman Animator (Live Link Face on iOS, Android) streams these exact 52 names. Any custom head mesh that wants to consume MetaHuman face animation **must** have shape keys named exactly:

| Group | Shape key names |
|---|---|
| Eyes | `eyeBlinkLeft`, `eyeLookDownLeft`, `eyeLookInLeft`, `eyeLookOutLeft`, `eyeLookUpLeft`, `eyeSquintLeft`, `eyeWideLeft`, `eyeBlinkRight`, `eyeLookDownRight`, `eyeLookInRight`, `eyeLookOutRight`, `eyeLookUpRight`, `eyeSquintRight`, `eyeWideRight` |
| Brows | `browDownLeft`, `browDownRight`, `browInnerUp`, `browOuterUpLeft`, `browOuterUpRight` |
| Cheeks | `cheekPuff`, `cheekSquintLeft`, `cheekSquintRight` |
| Nose | `noseSneerLeft`, `noseSneerRight` |
| Jaw | `jawForward`, `jawLeft`, `jawRight`, `jawOpen` |
| Mouth | `mouthClose`, `mouthFunnel`, `mouthPucker`, `mouthLeft`, `mouthRight`, `mouthSmileLeft`, `mouthSmileRight`, `mouthFrownLeft`, `mouthFrownRight`, `mouthDimpleLeft`, `mouthDimpleRight`, `mouthStretchLeft`, `mouthStretchRight`, `mouthRollLower`, `mouthRollUpper`, `mouthShrugLower`, `mouthShrugUpper`, `mouthPressLeft`, `mouthPressRight`, `mouthLowerDownLeft`, `mouthLowerDownRight`, `mouthUpperUpLeft`, `mouthUpperUpRight` |
| Tongue | `tongueOut` |

**Naming is camelCase, Left/Right (not _l/_r).** This is the Apple convention and the de-facto standard the MetaHuman Animator + Live Link Face pipeline assumes.

**Agent contract:** `shape_key_create_arkit_set` composite generates all 52 shape keys on the active mesh, named per the table above. `metahuman_face_validate` tool inspects a mesh and returns which of the 52 are missing.

### 3.3 Full MetaHuman face rig (FACS) — out of scope for v1.0

MetaHuman's full DNA rig has ~400 joints + RBF solvers. Authoring this from scratch in Blender is **infeasible** within tool scope (requires the MetaHuman DNA Calibration toolkit, currently Maya/Houdini only — see `MetaHuman for Maya` / `MetaHuman for Houdini` docs).

**v1.0 strategy:** ship the ARKit-52 blendshape pipeline. Custom heads can be driven by MetaHuman Animator → ARKit blendshape stream → UE morph targets. Document this as a "MetaHuman-compatible face" path, not "full MetaHuman face".

**v1.1 candidate:** integration with the MetaHuman for Houdini DNA workflow (the agent dispatches the rig generation step out-of-process). Defer.

### 3.4 Mesh-to-MetaHuman path

The "Mesh to MetaHuman" plugin path takes a custom head scan and produces a MetaHuman from it inside UE. Blender's role is to deliver a **clean topology head mesh** matching the MetaHuman face template (~10k tris, eyes/teeth/tongue submeshes). Export contract:

- Mesh in T-pose facing +X (UE forward).
- Eyeball center at known landmark — agent's `metahuman_face_validate` reports the position.
- Submeshes for `head`, `eyeLeft`, `eyeRight`, `teeth`, `tongue` (matching MetaHuman naming).
- Symmetry plane at world X=0.

---

## 4. Static meshes — props, environment, kits

**Source:** [FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine) (referenced by Skeletal Mesh doc).

### 4.1 Pivot & transform

- **Pivot at origin (0,0,0)** for prop meshes — UE places them by transforming the actor.
- **For modular kits** (snap-together level pieces): pivot at the **snap point** (typically a corner or socket), not the geometric center. The agent's `mesh_set_origin_to_snap_corner` composite handles this for kits.
- Apply Location, Rotation, and Scale in Blender before export — UE imports the apply-transform state.

### 4.2 LODs

- LOD group naming: wrap LOD meshes in an empty named `LOD_<MeshName>` (auto-detected by UE FBX importer).
- Or import LOD0 first, then add LOD1/2/3 from the Static Mesh editor (this is what the agent's `export_fbx_static` produces by default — one mesh per file, additional LODs as separate files).

### 4.3 Collision

UE FBX importer recognizes meshes named `UCX_<MeshName>` (convex collision), `UBX_<MeshName>` (box), `USP_<MeshName>` (sphere), `UCP_<MeshName>` (capsule) and converts them to collision primitives. **The agent's `collision_add_box` / `collision_add_convex` composites create properly-named child meshes that auto-convert on UE import.**

### 4.4 Lightmap UVs

- Channel 0 = PBR texturing.
- Channel 1 = lightmap (only if Lumen is **disabled** and the project uses Lightmass baked lighting).
- **Lumen-only projects (default for UE5)**: lightmap UVs are unnecessary; skip generating them to save build time and memory.
- The agent's `uv_generate_lightmap` composite must offer an opt-out flag (`enabled=False` by default for Lumen projects).

---

## 5. Nanite — high-poly Static & Skeletal meshes

**Source:** [Nanite Virtualized Geometry](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine).

### 5.1 What Nanite changes for the Blender authoring contract

| Concern | Pre-Nanite | Nanite |
|---|---|---|
| Triangle budget | thousands per mesh | millions allowed |
| LODs | manual, multi-LOD export | **none — Nanite handles LOD automatically** |
| Normal map baking | required for detail | **optional — direct high-poly displaces** |
| Tangent space | exported per-vertex | **derived in pixel shader** (per-vertex tangents discarded) |
| Morph targets | supported | **NOT supported** (see §5.3) |
| WPO displacement | supported | supported but split into clusters (perf cost) |
| Material blend mode | any | **Opaque + Masked only** (no Translucent on Nanite) |
| Lightmap UVs | required for baked lighting | optional (disable "Generate Lightmap UVs" on import) |

### 5.2 Enabling Nanite per asset

Nanite is opt-in per asset via the **Build Nanite** checkbox on FBX import, or via Static/Skeletal Mesh Editor → Nanite Settings → Enable Nanite Support, or via Content Browser batch right-click → Nanite > Enable.

**The agent's `export_fbx_static` and `export_fbx_skeletal` tools must expose a `nanite_recommended: boolean` flag in the response payload** based on triangle count + LOD count: if `tris > 100k && lods == 1` → `nanite_recommended = true`.

### 5.3 Hard incompatibilities for Nanite Skeletal Mesh

- **No Morph Targets.** A Nanite Skeletal Mesh with a face that needs MetaHuman ARKit blendshapes **must remain non-Nanite**. The agent's `metahuman_face_validate` tool warns if Nanite is requested + blendshapes present.
- **No per-vertex tangents.** Custom tangent-space normal maps may show artifacts. Use derived tangents (the default).

---

## 6. Lumen — lighting & material implications

**Source:** [Lumen Global Illumination and Reflections](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine).

### 6.1 What Lumen requires from Blender-exported content

- **Two-sided foliage**: meshes flagged as foliage need the Two-Sided Foliage shading model. Blender material must expose: base color, subsurface color (for backlight scatter), normal, opacity mask (for leaf cards). The agent's `material_create_foliage` composite emits this.
- **Generate Mesh Distance Fields** is on by default. Static meshes with non-manifold geometry can fail to generate distance fields. The agent's `mesh_validate_for_distance_fields` tool checks for non-manifold edges + open boundary loops and warns.
- **Static Mobility lights are not supported by Lumen.** Mannequin demo levels use Stationary + Movable lights. Blender's light export (FBX includes lights with type DirectionalLight/PointLight/SpotLight) maps to UE Movable lights by default — that's compatible.
- **Material Ambient Occlusion** output is supported for skeletal meshes with Lumen. The agent's `shader_node_add_principled_for_lumen` composite wires the AO output of the Principled BSDF.

### 6.2 What Lumen makes unnecessary

- Lightmap UVs (see §4.4).
- Pre-baked AO textures (use Material AO output instead).
- Pre-baked GI lightmaps (Lumen is fully dynamic).

---

## 7. FBX exporter parameter contract — Blender side

The agent's `export_fbx_skeletal` and `export_fbx_static` tools must expose **every** parameter of Blender's FBX exporter as a typed input. Critical parameters for UE compatibility:

| Blender FBX param | Required value for UE Mannequin | Required value for UE Static Mesh |
|---|---|---|
| `use_selection` | `True` (only export selected armature + meshes) | `True` |
| `global_scale` | `1.0` | `1.0` |
| `apply_unit_scale` | `True` | `True` |
| `apply_scale_options` | `'FBX_SCALE_NONE'` | `'FBX_SCALE_NONE'` |
| `axis_forward` | `'-Z'` | `'-Z'` |
| `axis_up` | `'Y'` | `'Y'` |
| `object_types` | `{'ARMATURE', 'MESH', 'EMPTY'}` (Empty for sockets) | `{'MESH', 'EMPTY'}` (Empty for collision) |
| `use_mesh_modifiers` | `True` | `True` |
| `mesh_smooth_type` | `'FACE'` | `'FACE'` |
| `use_subsurf` | `False` | `False` (apply manually) |
| `use_mesh_edges` | `False` | `False` |
| `use_tspace` | `True` | `True` |
| `use_triangles` | `True` (force triangulation) | `True` |
| `use_armature_deform_only` | `True` (skip IK control bones that aren't deform) | n/a |
| `add_leaf_bones` | `False` (UE adds its own leaf bones; doubles otherwise) | n/a |
| `primary_bone_axis` | `'Y'` | n/a |
| `secondary_bone_axis` | `'X'` | n/a |
| `armature_nodetype` | `'NULL'` | n/a |
| `bake_anim` | `True` for animation export, `False` for rest pose only | `False` |
| `bake_anim_use_all_bones` | `True` | n/a |
| `bake_anim_use_nla_strips` | `False` (per-strip export is handled outside) | n/a |
| `bake_anim_use_all_actions` | `False` (one Action per FBX) | n/a |
| `bake_anim_force_startend_keying` | `True` | n/a |
| `bake_anim_step` | `1.0` (every frame) | n/a |
| `bake_anim_simplify_factor` | `1.0` (no simplification) | n/a |
| `path_mode` | `'COPY'` | `'COPY'` |
| `embed_textures` | `False` (UE expects external textures) | `False` |
| `batch_mode` | `'OFF'` (caller batches via tool loop) | `'OFF'` |
| `use_custom_props` | `True` (preserves Blender custom props as FBX user attributes — useful for socket markers) | `True` |

**The agent's tool description must quote each parameter's effect on UE compatibility.** See [TOOL-CATALOG.md](TOOL-CATALOG.md) `export_fbx_skeletal` entry.

---

## 8. glTF as the secondary export path

UE5 has a Datasmith glTF importer and a community-maintained `glTFRuntime`. glTF is also the format of choice when going to other engines (Unity, Godot, web). The agent must offer `export_gltf` as a first-class peer to FBX with the same parameter completeness.

Key glTF-vs-FBX differences:

- glTF uses Khronos PBR (metallic-roughness only) — maps cleanly to Blender Principled BSDF (`base_color`, `metallic`, `roughness`, `normal`, `emissive`, `occlusion`, `alpha`).
- glTF supports morph targets natively and stores them more compactly than FBX.
- glTF doesn't support custom node attributes the way FBX does — collision/socket conventions need an alternative (use `extras` field; UE glTF importer reads `KHR_*` extensions).
- Animation: one glTF can carry multiple animations cleanly (unlike FBX's one-action-per-file restriction).

---

## 9. Per-class acceptance checklist (for `WORKFLOW-RECIPES.md`)

The composite recipes in [WORKFLOW-RECIPES.md](WORKFLOW-RECIPES.md) end with `verify_export_<class>` tools that assert these checklists.

### 9.1 `verify_export_ue5_skeletal_character`

- [ ] FBX file exists at `output_path`.
- [ ] FBX header reports version 2014+ (`BIN7400`).
- [ ] Skeleton root bone is named `root` and at world origin.
- [ ] Bone hierarchy matches §1.1 (or matches a user-supplied custom hierarchy).
- [ ] All vertex group names map to existing bones.
- [ ] No bones have `.001` / `.l` / `.L` suffix mismatches.
- [ ] Mesh is fully triangulated.
- [ ] Material slot count matches user-declared expectation.
- [ ] If A-pose expected: shoulder angle ≈ 45°.
- [ ] If MetaHuman-compatible: all 52 ARKit shape keys present (warn if not).

### 9.2 `verify_export_ue5_static_kit`

- [ ] Each mesh has pivot at the declared snap corner.
- [ ] Each mesh has applied transform (loc=0, rot=0, scale=1 in Blender post-apply).
- [ ] Mesh triangulated.
- [ ] LOD group present if `lod_count > 1`.
- [ ] `UCX_*` collision meshes present if `collision_required = true`.
- [ ] No N-gons (Nanite tolerates; some legacy importers reject).

### 9.3 `verify_export_ue5_animation`

- [ ] One Action per FBX.
- [ ] Frame range matches Action's start/end.
- [ ] Scene FPS matches user-declared target FPS.
- [ ] Root bone has root motion keyframes if `root_motion = true`.
- [ ] No bone scales other than 1.0 (UE skeletal anim ignores scale for retarget).

### 9.4 `verify_export_metahuman_face_compatible`

- [ ] All 52 ARKit blendshape names present and spelled exactly per §3.2.
- [ ] Head mesh is in T-pose facing +X.
- [ ] Symmetry plane at world X=0 (vertex offset RMS < 0.001 m).
- [ ] Submeshes for `head`, `eyeLeft`, `eyeRight`, `teeth`, `tongue` exist.
- [ ] Triangle count < 50k (MetaHuman heads are ~10k; warn above).

---

## 10. Open issues to resolve later

1. **UEFN (Fortnite Editor) skeleton differences** — UEFN may diverge from UE5 over time. Out of scope until a contributor needs it.
2. **Hair/Groom export** — UE Groom system consumes Alembic `.abc` curve data. The Alembic exporter parameter matrix needs its own §11 once Phase B-7 (rigging research) confirms what Blender's particle/hair-curves system can export.
3. **Niagara VFX bridge** — out of scope; we don't author VFX. Export an FBX skeletal mesh and Niagara binds to it on the UE side.
4. **Datasmith** — Epic's parametric scene importer. Lower priority than FBX/glTF; revisit post-1.0.
