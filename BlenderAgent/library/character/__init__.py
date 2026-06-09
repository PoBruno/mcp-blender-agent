"""Parametric character builders.

Each builder consumes an anatomy canon (heroic_male, fashion, chibi, etc.) +
a total height and produces a named-parts mesh hierarchy that is *proportionally
correct*: limb lengths, joint heights, head/shoulder/hip widths all derived from
the canon's heads-as-unit table in `BlenderAgent/library/anatomy/proportions`.

Designed as a base mesh — clean primitives positioned by anatomy data, ready
for `/postproc/voxel_remesh` → `/postproc/quad_remesh` → sculpting / rigging.
"""
