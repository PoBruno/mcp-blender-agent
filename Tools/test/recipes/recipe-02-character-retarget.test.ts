import { describe, it } from "vitest";

/**
 * Recipe 2 — character_retarget_to_ue5_mannequin
 *
 * SKIPPED for v1.0. The full recipe needs four composite tools that haven't
 * been built yet:
 *
 *   - armature_apply_scale            (apply object scale to armature data;
 *                                      Mixamo imports at 0.01)
 *   - bone_rename_convention          (internal mixamorig:* -> UE5 mannequin map)
 *   - armature_create_ue5_mannequin   (full 64+ bone mannequin builder)
 *   - armature_retarget_to_ue5_mannequin
 *                                     (bake one armature's action onto another
 *                                      via visual-key constraints)
 *
 * It also needs a Mixamo-style FBX fixture; without one the import step is
 * meaningless.
 *
 * When those tools land, replace the skipped test below with a full chain
 * mirroring the brief at `.claude/docs/research/WORKFLOW-RECIPES.md` §Recipe 2.
 */
describe("Recipe 2 — character_retarget_to_ue5_mannequin", () => {
  it.skip("retargets a Mixamo action onto SK_Mannequin (needs future composites)", () => {
    // intentionally empty — see file header for required endpoints
  });
});
