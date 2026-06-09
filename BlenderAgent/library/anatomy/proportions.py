"""Anatomy & proportion priors — the 'pair representation' of AAA modeling.

Read by both the agent (via /parametric/anatomy/* endpoints) and by parametric
builders that need to derive secondary dimensions from a single primary one.

All units: meters. All ratios: dimensionless (numerator / denominator).

Sources for each table are cited inline. We bias toward classical art-anatomy
canons (Loomis, Bridgman, Hampton) over photographic anthropometry because:
  - canons are simpler (heads-as-unit instead of mm tables),
  - art-canons are what art directors give as direction,
  - we can layer photographic correction on top later.

The point of this module is that the agent can ask:
    > "I want a 7.5-head heroic male, 1.85m tall. What's his shoulder width?"
and get back: 0.50m (1.85 * (3/7.5 * 1.0) — 3 head widths, 1 head = 1/7.5 of height).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional

# ---------------------------------------------------------------------------
# Human proportion canons (Loomis-style, head-counts)
# ---------------------------------------------------------------------------

#: Head count = total body height divided by head height. Higher = more heroic.
HumanCanonName = Literal[
    "realistic_adult",   # ~7.0 heads, average real adult
    "fashion",           # ~8.0 heads, fashion plates, exaggerated long
    "heroic_male",       # ~7.5 heads, classic comic / Loomis "Ideal Man"
    "heroic_female",     # ~7.5 heads (or 8 for fashion-leaning), Loomis "Ideal Woman"
    "chibi",             # ~3.0 heads, super-deformed
    "child_5yr",         # ~5.5 heads
    "teen_15yr",         # ~6.5 heads
]


@dataclass(frozen=True)
class HumanCanon:
    """One human proportion canon. All ratios expressed in 'heads'.

    A 'head' is the unit: head_height = total_height / heads_count.
    """
    name: str
    heads_count: float
    # vertical landmarks measured from top of head, in heads
    chin_at_heads: float = 1.0
    shoulder_at_heads: float = 1.33      # ~1/3 head below chin
    nipple_at_heads: float = 2.0
    navel_at_heads: float = 3.0
    crotch_at_heads: float = 4.0
    knee_at_heads: float = 5.5
    # horizontal widths in heads
    head_width_in_heads: float = 0.75    # head is taller than wide
    shoulder_width_in_heads: float = 3.0
    chest_width_in_heads: float = 2.5
    waist_width_in_heads: float = 2.0
    hip_width_in_heads: float = 2.5
    # limbs in heads
    upper_arm_length_in_heads: float = 1.33
    forearm_length_in_heads: float = 1.20
    hand_length_in_heads: float = 0.75    # hand covers chin to hairline
    thigh_length_in_heads: float = 2.0
    shin_length_in_heads: float = 1.75
    foot_length_in_heads: float = 1.0


HUMAN_CANONS: Dict[str, HumanCanon] = {
    "realistic_adult": HumanCanon(
        name="realistic_adult",
        heads_count=7.0,
        shoulder_width_in_heads=2.66,
        hip_width_in_heads=2.33,
    ),
    "fashion": HumanCanon(
        name="fashion",
        heads_count=8.0,
        shoulder_at_heads=1.5,
        nipple_at_heads=2.25,
        navel_at_heads=3.25,
        crotch_at_heads=4.25,
        knee_at_heads=6.0,
        upper_arm_length_in_heads=1.5,
        forearm_length_in_heads=1.33,
        thigh_length_in_heads=2.25,
        shin_length_in_heads=2.0,
    ),
    "heroic_male": HumanCanon(
        name="heroic_male",
        heads_count=7.5,
        shoulder_width_in_heads=3.0,
        chest_width_in_heads=2.66,
        hip_width_in_heads=2.33,
    ),
    "heroic_female": HumanCanon(
        name="heroic_female",
        heads_count=7.5,
        shoulder_width_in_heads=2.5,
        hip_width_in_heads=2.66,   # wider hips than shoulders
        waist_width_in_heads=1.75,
    ),
    "chibi": HumanCanon(
        name="chibi",
        heads_count=3.0,
        shoulder_at_heads=1.25,
        nipple_at_heads=1.5,
        navel_at_heads=2.0,
        crotch_at_heads=2.25,
        knee_at_heads=2.66,
        head_width_in_heads=1.0,
        shoulder_width_in_heads=1.5,
        upper_arm_length_in_heads=0.5,
        forearm_length_in_heads=0.5,
        hand_length_in_heads=0.5,
        thigh_length_in_heads=0.5,
        shin_length_in_heads=0.5,
        foot_length_in_heads=0.5,
    ),
    "child_5yr": HumanCanon(
        name="child_5yr",
        heads_count=5.5,
        # children have larger heads relative to body
        head_width_in_heads=1.0,
        shoulder_width_in_heads=2.0,
        hip_width_in_heads=2.0,
    ),
    "teen_15yr": HumanCanon(
        name="teen_15yr",
        heads_count=6.5,
        shoulder_width_in_heads=2.5,
        hip_width_in_heads=2.25,
    ),
}


def resolve_human(canon_name: str, total_height_m: float) -> Dict[str, float]:
    """Given a canon + total height, derive every measurement in meters."""
    canon = HUMAN_CANONS.get(canon_name)
    if canon is None:
        raise ValueError(
            f"unknown canon {canon_name!r}, valid: {sorted(HUMAN_CANONS)}"
        )
    head = total_height_m / canon.heads_count
    return {
        "canon": canon.name,
        "total_height_m": total_height_m,
        "head_height_m": head,
        "head_width_m": head * canon.head_width_in_heads,
        "shoulder_height_m": total_height_m - head * canon.shoulder_at_heads,
        "nipple_height_m": total_height_m - head * canon.nipple_at_heads,
        "navel_height_m": total_height_m - head * canon.navel_at_heads,
        "crotch_height_m": total_height_m - head * canon.crotch_at_heads,
        "knee_height_m": total_height_m - head * canon.knee_at_heads,
        "shoulder_width_m": head * canon.shoulder_width_in_heads,
        "chest_width_m": head * canon.chest_width_in_heads,
        "waist_width_m": head * canon.waist_width_in_heads,
        "hip_width_m": head * canon.hip_width_in_heads,
        "upper_arm_length_m": head * canon.upper_arm_length_in_heads,
        "forearm_length_m": head * canon.forearm_length_in_heads,
        "hand_length_m": head * canon.hand_length_in_heads,
        "thigh_length_m": head * canon.thigh_length_in_heads,
        "shin_length_m": head * canon.shin_length_in_heads,
        "foot_length_m": head * canon.foot_length_in_heads,
    }


# ---------------------------------------------------------------------------
# Furniture proportion priors
# ---------------------------------------------------------------------------

#: Reference dims (meters). Used when the user gives no dims — these are
#: ergonomic defaults from ANSI/HUMANSCALE 1/2/3 furniture standards, rounded
#: to the nearest 0.05m.
FURNITURE_DEFAULTS: Dict[str, Dict[str, float]] = {
    "chair_dining": {
        "seat_height": 0.45,
        "seat_depth":  0.40,
        "seat_width":  0.45,
        "back_height": 0.85,  # floor to top of backrest
        "back_angle_deg": 10,
    },
    "chair_office": {
        "seat_height": 0.46,
        "seat_depth":  0.45,
        "seat_width":  0.48,
        "back_height": 1.10,
        "back_angle_deg": 15,
    },
    "chair_lounge": {
        "seat_height": 0.40,
        "seat_depth":  0.50,
        "seat_width":  0.55,
        "back_height": 0.90,
        "back_angle_deg": 25,
    },
    "chair_beach": {
        # low recliner, long, foldable
        "length":            1.70,
        "width":             0.60,
        "seat_height":       0.35,
        "back_angle_deg":    28,
        "leg_thickness":     0.04,
        "rail_thickness":    0.05,
        "slat_count":        7,
        "slat_thickness":    0.012,
        "slat_gap":          0.015,
    },
    "table_dining": {
        "top_height":  0.75,
        "top_length":  1.80,
        "top_width":   0.90,
        "top_thickness": 0.04,
        "leg_thickness": 0.06,
    },
    "table_coffee": {
        "top_height":  0.45,
        "top_length":  1.20,
        "top_width":   0.60,
        "top_thickness": 0.03,
        "leg_thickness": 0.05,
    },
    "stool_bar": {
        "seat_height": 0.75,
        "seat_diameter": 0.32,
        "footrest_height": 0.30,
        "leg_thickness": 0.03,
    },
    "sofa_2seat": {
        "length":            1.60,
        "depth":             0.90,
        "height":            0.85,
        "seat_height":       0.45,
        "seat_cushion_thick": 0.18,
        "back_cushion_thick": 0.20,
        "arm_height":        0.62,
        "arm_thickness":     0.18,
    },
}


def furniture_defaults(kind: str) -> Dict[str, float]:
    """Return the ergonomic default dims for a furniture kind."""
    if kind not in FURNITURE_DEFAULTS:
        raise ValueError(
            f"unknown furniture kind {kind!r}, valid: {sorted(FURNITURE_DEFAULTS)}"
        )
    return dict(FURNITURE_DEFAULTS[kind])


# ---------------------------------------------------------------------------
# Animation timing priors (frames at 24 fps unless noted)
# ---------------------------------------------------------------------------

ANIMATION_TIMINGS: Dict[str, Dict[str, float]] = {
    "walk_cycle_human": {
        "fps": 24,
        "total_frames": 32,         # one full cycle (L + R steps)
        "step_frames": 16,
        "contact_at": [0, 8, 16, 24],
        "passing_at": [4, 12, 20, 28],
    },
    "run_cycle_human": {
        "fps": 24,
        "total_frames": 16,
        "step_frames": 8,
        "contact_at": [0, 4, 8, 12],
        "passing_at": [2, 6, 10, 14],
        "airborne_frames_per_step": 2,
    },
    "idle_breathing": {
        "fps": 24,
        "total_frames": 72,         # 3 second loop, breaths sync
        "inhale_frames": 18,
        "hold_frames": 6,
        "exhale_frames": 24,
        "settle_frames": 24,
    },
    "jump_neutral": {
        "fps": 24,
        "anticipation_frames": 8,
        "takeoff_frames": 4,
        "airborne_frames": 14,
        "land_frames": 6,
        "recovery_frames": 12,
    },
}


def animation_timing(kind: str, fps: Optional[float] = None) -> Dict[str, float]:
    """Return frame timing for a known animation kind, optionally rescaled to fps."""
    base = ANIMATION_TIMINGS.get(kind)
    if base is None:
        raise ValueError(
            f"unknown animation kind {kind!r}, valid: {sorted(ANIMATION_TIMINGS)}"
        )
    out = dict(base)
    if fps is not None and fps != base["fps"]:
        scale = fps / base["fps"]
        out["fps"] = fps
        for key, val in base.items():
            if key == "fps":
                continue
            if isinstance(val, (int, float)):
                out[key] = val * scale
            elif isinstance(val, list):
                out[key] = [v * scale for v in val]
    return out


# ---------------------------------------------------------------------------
# Material recipes (PBR ranges)
# ---------------------------------------------------------------------------

#: For each named material archetype, a recipe with PBR ranges. Use the
#: midpoint as default, with deltas for variation. Roughness/metallic are
#: physically grounded (Disney BRDF references).
MATERIAL_RECIPES: Dict[str, Dict[str, float]] = {
    "weathered_teak": {
        "base_color_r": 0.45, "base_color_g": 0.27, "base_color_b": 0.14,
        "roughness": 0.78, "metallic": 0.0, "specular": 0.4,
    },
    "polished_oak": {
        "base_color_r": 0.58, "base_color_g": 0.40, "base_color_b": 0.22,
        "roughness": 0.32, "metallic": 0.0, "specular": 0.5,
    },
    "faded_canvas_orange": {
        "base_color_r": 0.85, "base_color_g": 0.35, "base_color_b": 0.10,
        "roughness": 0.85, "metallic": 0.0, "specular": 0.3,
    },
    "brushed_aluminum": {
        "base_color_r": 0.91, "base_color_g": 0.92, "base_color_b": 0.92,
        "roughness": 0.35, "metallic": 1.0, "specular": 0.5,
    },
    "skin_caucasian": {
        "base_color_r": 0.92, "base_color_g": 0.72, "base_color_b": 0.62,
        "roughness": 0.55, "metallic": 0.0, "specular": 0.45,
    },
    "fabric_denim": {
        "base_color_r": 0.20, "base_color_g": 0.30, "base_color_b": 0.48,
        "roughness": 0.92, "metallic": 0.0, "specular": 0.2,
    },
}


def material_recipe(name: str) -> Dict[str, float]:
    """Return PBR values for a known material archetype."""
    if name not in MATERIAL_RECIPES:
        raise ValueError(
            f"unknown material recipe {name!r}, valid: {sorted(MATERIAL_RECIPES)}"
        )
    return dict(MATERIAL_RECIPES[name])
