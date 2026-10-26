# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Cloudberry built from reference photos rather than the scan's spheres.

Drupelets sit in rings (tiers) around the stem-to-tip axis, the way a
cloudberry grows: rings are spaced by one angular step from the stem to
the tip, each ring holds as many drupelets as fit at that step, and a cap
closes the tip. Drupelets are plump ovals (ellipsoids, longer along their
outward axis) that overlap their neighbours, so they meet in tight creases.
The stem end is tucked in: the outline the drupelets sit on narrows toward
the stem, and the crown flattens a little at the tip. A small core blob closes the stem end as a shallow dimple.

Stem at the bottom (-Z), as in the scan files. No stem or sepals. Seams use
the wander_50 recipe. Sizes are invented from the photos; the scan sets
only the 100 mm height convention.

Variants follow five reference photos (local, not in the repo):
  a_studio  studio pair with leaf: round, gentle stem taper, ~20
  b_bog     bog habitat: small even drupelets, very round, ~24
  c_plump   single berry, large plump lobes, barrel, ~14
  d_upright on the stem: upright, a little taller than wide, ~18
  e_white   white background: round, more irregular, ~22

Writes models/print/berry_ref_<name>_<H>mm.stl.

Run:
    uv run tools/mesh/berry_tiers.py [--height-mm 100] [--only a_studio c_plump]
"""

import argparse
import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(__file__))
from lumps_clean import place  # noqa: E402
from lumps_seams import VARIANTS as SEAMS, seam_field  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print")

# count: target drupelets. aspect: height / width of the core. taper:
# core narrowing at the stem (fraction). elong: outward length / width of a
# drupelet. press: overlap with neighbours (1 = just touching). jitter:
# random spread of size and position (fraction of one step).
# Optional: square: exponent of a drupelet's outline where it meets its
# neighbours (2 = oval, higher = rounded polygon, so corners close with no
# gaps). poles: "ring" closes both ends with a ring meeting in a star, not
# one cap drupelet; end_n drupelets in each end ring, stretched toward the
# pole by end_stretch so they read as wedges meeting flat (tip_n /
# tip_stretch override these at the tip; end_elong sets the stem ring's
# elong). "spiral" keeps the stem ring and sets the rest on a golden-angle
# spiral, the way aggregate fruits grow. tip_jitter False keeps the tip
# star centred. step fixes the ring spacing instead of deriving it from
# count. ring_th overrides ring angles (degrees); mid_m_scale shortens the
# middle rings' drupelets along the stem-to-tip line (one value, or one per
# ring). base_bulge [amount, centre deg, width deg] enlarges the outline and
# drupelets around one band (e.g. just above the stem); bulges adds more
# bands in the same form. ring_around / ring_out (per ring) widen drupelets
# around the berry and push a row outward without making it taller;
# ring_plump grows a row's drupelets outward and around from their centres;
# ring_sag moves each drupelet's peak toward the stem, as if it hangs. ring_n overrides
# ring counts; ring_tilt (degrees, per ring) tilts rings toward tilt_az.
# lean [deg, azimuth] bends the berry from stem to tip; side_full [amount,
# azimuth] makes one side fuller. stem_flat / crown:
# flattening at the stem and tip ends; a lower
# crown_pow spreads the tip flattening wider, broadening the shoulders.
V6_CLEAR = {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.1,
            "press": 2.0, "jitter": 0.08, "seed": 1, "square": 2.5,
            "poles": "ring", "end_n": 4, "end_stretch": 1.25,
            "tip_n": 5, "tip_stretch": 1.12, "tip_jitter": False,
            "step": 0.77607, "stem_flat": 0.2, "crown": 0.10,
            "crown_pow": 3, "mid_m_scale": 0.9,
            "ring_th": [None, None, 111, 154],
            "base_bulge": [0.28, 50, 30]}

V7_BOTH = {**V6_CLEAR, "ring_n": [None, None, 8, None],
           "ring_tilt": [0, 0, 5, 0], "tilt_az": 30,
           "lean": [6, 200], "side_full": [0.03, 200]}

# Picked 2026-10-26.
V16_SUBTLE = {**V7_BOTH, "ring_n": [None, 10, 8, None],
              "ring_th": [None, None, 109, 156], "tilt_az": 120,
              "lean": [3, 200], "side_full": [0.0, 0.0],
              "ring_around": [1.0, 1.12, 1.0, 1.0], "ring_out": [1.0, 1.04, 1.0, 1.0],
              "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.10, 0.0],
              "aa_clip": [1.3, 1.6, 1.3, 1.3],
              "ring_jitter": [1.0, 0.5, 1.0, 0.3], "tip_jitter": True,
              "drupelet_tilt": [0, 4, 4, 2], "square_var": 0.08,
              "groove_var": 0.03, "oval": [0.018, 70]}

VARIANTS = {
    # Picked 2026-10-17 from a_studio: no gaps at junctions, flat star ends.
    "a_studio_v2": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.1,
                    "press": 2.0, "jitter": 0.08, "seed": 1, "square": 2.5,
                    "poles": "ring", "end_n": 4, "end_stretch": 1.25,
                    "stem_flat": 0.2, "crown": 0.12},
    # v2 with a broad, rounded tip: five plump drupelets meet there.
    "a_studio_v3": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.1,
                    "press": 2.0, "jitter": 0.08, "seed": 1, "square": 2.5,
                    "poles": "ring", "end_n": 4, "end_stretch": 1.25,
                    "tip_n": 5, "tip_stretch": 1.0, "tip_jitter": False,
                    "step": 0.77607,  # v2's ring spacing, so the stem end is unchanged
                    "stem_flat": 0.2, "crown": 0.10, "crown_pow": 3},
    # v3 with shorter middle-row drupelets (mid_m_scale) and a tip ring moved
    # off the pole and stretched, so tip drupelets get the room the middle
    # row took. Stem end identical to v3. Mild and stronger steps.
    "a_studio_v5_mild": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.1,
                         "press": 2.0, "jitter": 0.08, "seed": 1, "square": 2.5,
                         "poles": "ring", "end_n": 4, "end_stretch": 1.25,
                         "tip_n": 5, "tip_stretch": 1.12, "tip_jitter": False,
                         "step": 0.77607, "stem_flat": 0.2, "crown": 0.10,
                         "crown_pow": 3, "mid_m_scale": 0.9,
                         "ring_th": [None, None, 111, 154]},
    "a_studio_v5_strong": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.1,
                           "press": 2.0, "jitter": 0.08, "seed": 1, "square": 2.5,
                           "poles": "ring", "end_n": 4, "end_stretch": 1.25,
                           "tip_n": 5, "tip_stretch": 1.25, "tip_jitter": False,
                           "step": 0.77607, "stem_flat": 0.2, "crown": 0.10,
                           # Lower middle row borders the stem star; shorten it less.
                           "crown_pow": 3, "mid_m_scale": [1.0, 0.92, 0.82, 1.0],
                           "ring_th": [None, None, 109, 150]},
    # v5 mild with a wider base: a bulge centred just above the stem ring
    # enlarges the stem-ring and lower-row drupelets so the base is wider
    # than the middle; the stem star and the middle row barely move.
    "a_studio_v6_slight": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.1,
                           "press": 2.0, "jitter": 0.08, "seed": 1, "square": 2.5,
                           "poles": "ring", "end_n": 4, "end_stretch": 1.25,
                           "tip_n": 5, "tip_stretch": 1.12, "tip_jitter": False,
                           "step": 0.77607, "stem_flat": 0.2, "crown": 0.10,
                           "crown_pow": 3, "mid_m_scale": 0.9,
                           "ring_th": [None, None, 111, 154],
                           "base_bulge": [0.18, 50, 30]},
    "a_studio_v6_clear": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.1,
                          "press": 2.0, "jitter": 0.08, "seed": 1, "square": 2.5,
                          "poles": "ring", "end_n": 4, "end_stretch": 1.25,
                          "tip_n": 5, "tip_stretch": 1.12, "tip_jitter": False,
                          "step": 0.77607, "stem_flat": 0.2, "crown": 0.10,
                          "crown_pow": 3, "mid_m_scale": 0.9,
                          "ring_th": [None, None, 111, 154],
                          "base_bulge": [0.28, 50, 30]},
    # v6 clear with the upper middle row at 8 drupelets and tilted 5 degrees,
    # so the seam between the middle rows wanders (rows); a 6 degree lean and
    # one side 3% fuller (lean); and both together.
    "a_studio_v7_rows": {**V6_CLEAR, "ring_n": [None, None, 8, None],
                         "ring_tilt": [0, 0, 5, 0], "tilt_az": 30},
    "a_studio_v7_lean": {**V6_CLEAR, "lean": [6, 200], "side_full": [0.03, 200]},
    "a_studio_v7_both": {**V6_CLEAR, "ring_n": [None, None, 8, None],
                         "ring_tilt": [0, 0, 5, 0], "tilt_az": 30,
                         "lean": [6, 200], "side_full": [0.03, 200]},
    # v7 both with a bigger base row (its own narrow bulge, taller drupelets,
    # row moved up so more of it faces the side) and a deeper groove under
    # the tip ring (tip ring moved toward the pole, so it overlaps the upper
    # middle row less). Subtle and clear steps.
    "a_studio_v8_subtle": {**V7_BOTH, "ring_th": [None, 70, 111, 156],
                           "mid_m_scale": [1.0, 1.06, 0.9, 1.0],
                           "bulges": [[0.06, 70, 15]]},
    "a_studio_v8_clear": {**V7_BOTH, "ring_th": [None, 72, 111, 158],
                          "mid_m_scale": [1.0, 1.12, 0.9, 1.0],
                          "bulges": [[0.12, 70, 15]]},
    # v7 both with wider, plumper base-row drupelets (ring_around widens
    # them around the berry, which also lengthens their outward axis;
    # ring_out pushes the row out) at the same height and position, so the
    # stem star is unchanged; tip ring moved toward the pole for a deeper
    # groove under it. Subtle and clear steps.
    "a_studio_v9_subtle": {**V7_BOTH, "ring_th": [None, None, 111, 156],
                           "ring_around": [1.0, 1.12, 1.0, 1.0],
                           "ring_out": [1.0, 1.04, 1.0, 1.0]},
    "a_studio_v9_clear": {**V7_BOTH, "ring_th": [None, None, 111, 158],
                          "ring_around": [1.0, 1.22, 1.0, 1.0],
                          "ring_out": [1.0, 1.07, 1.0, 1.0]},
    # v9 with 8 drupelets in the base row (was 7), so no single one
    # dominates; each is narrower around the berry, same height.
    "a_studio_v10_subtle": {**V7_BOTH, "ring_n": [None, 8, 8, None],
                            "ring_th": [None, None, 111, 156],
                            "ring_around": [1.0, 1.12, 1.0, 1.0],
                            "ring_out": [1.0, 1.04, 1.0, 1.0]},
    "a_studio_v10_clear": {**V7_BOTH, "ring_n": [None, 8, 8, None],
                           "ring_th": [None, None, 111, 158],
                           "ring_around": [1.0, 1.22, 1.0, 1.0],
                           "ring_out": [1.0, 1.07, 1.0, 1.0]},
    # v10 with each base-row drupelet 8% plumper (outward and around, from
    # its own centre; same height).
    "a_studio_v11_subtle": {**V7_BOTH, "ring_n": [None, 8, 8, None],
                            "ring_th": [None, None, 111, 156],
                            "ring_around": [1.0, 1.12, 1.0, 1.0],
                            "ring_out": [1.0, 1.04, 1.0, 1.0],
                            "ring_plump": [1.0, 1.08, 1.0, 1.0]},
    "a_studio_v11_clear": {**V7_BOTH, "ring_n": [None, 8, 8, None],
                           "ring_th": [None, None, 111, 158],
                           "ring_around": [1.0, 1.22, 1.0, 1.0],
                           "ring_out": [1.0, 1.07, 1.0, 1.0],
                           "ring_plump": [1.0, 1.08, 1.0, 1.0]},
    # v11 with 9 drupelets in the base row (same height, each narrower
    # around) and the upper middle row sagging: each drupelet's peak sits
    # 20% or 35% of its half-height toward the stem. Footprints unchanged.
    "a_studio_v12_subtle_sag20": {**V7_BOTH, "ring_n": [None, 9, 8, None],
        "ring_th": [None, None, 111, 156],
        "ring_around": [1.0, 1.12, 1.0, 1.0], "ring_out": [1.0, 1.04, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.2, 0.0]},
    "a_studio_v12_subtle_sag35": {**V7_BOTH, "ring_n": [None, 9, 8, None],
        "ring_th": [None, None, 111, 156],
        "ring_around": [1.0, 1.12, 1.0, 1.0], "ring_out": [1.0, 1.04, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.35, 0.0]},
    "a_studio_v12_clear_sag20": {**V7_BOTH, "ring_n": [None, 9, 8, None],
        "ring_th": [None, None, 111, 158],
        "ring_around": [1.0, 1.22, 1.0, 1.0], "ring_out": [1.0, 1.07, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.2, 0.0]},
    "a_studio_v12_clear_sag35": {**V7_BOTH, "ring_n": [None, 9, 8, None],
        "ring_th": [None, None, 111, 158],
        "ring_around": [1.0, 1.22, 1.0, 1.0], "ring_out": [1.0, 1.07, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.35, 0.0]},
    # v12 with 10 base-row drupelets (same height, narrower around) and a
    # lighter sag on the upper middle row (10%).
    "a_studio_v13_subtle": {**V7_BOTH, "ring_n": [None, 10, 8, None],
        "ring_th": [None, None, 111, 156],
        "ring_around": [1.0, 1.12, 1.0, 1.0], "ring_out": [1.0, 1.04, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.10, 0.0], "aa_clip": [1.3, 1.6, 1.3, 1.3]},
    "a_studio_v13_clear": {**V7_BOTH, "ring_n": [None, 10, 8, None],
        "ring_th": [None, None, 111, 158],
        "ring_around": [1.0, 1.22, 1.0, 1.0], "ring_out": [1.0, 1.07, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.10, 0.0], "aa_clip": [1.3, 1.6, 1.3, 1.3]},
    # v13 balanced: lean, fuller side and the middle-row dip all pointed at
    # the same side, so that side read deformed and the other uniform. Lean
    # halved, fuller side off, middle-row tilt turned 90 degrees so its
    # wobble sits on the in-between sides; middle row 2 degrees lower so it
    # overlaps the base row more and the groove between them is shallower.
    "a_studio_v14_subtle": {**V7_BOTH, "ring_n": [None, 10, 8, None],
        "ring_th": [None, None, 109, 156], "tilt_az": 120,
        "lean": [3, 200], "side_full": [0.0, 0.0],
        "ring_around": [1.0, 1.12, 1.0, 1.0], "ring_out": [1.0, 1.04, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.10, 0.0],
        "aa_clip": [1.3, 1.6, 1.3, 1.3]},
    "a_studio_v14_clear": {**V7_BOTH, "ring_n": [None, 10, 8, None],
        "ring_th": [None, None, 109, 158], "tilt_az": 120,
        "lean": [3, 200], "side_full": [0.0, 0.0],
        "ring_around": [1.0, 1.22, 1.0, 1.0], "ring_out": [1.0, 1.07, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.10, 0.0],
        "aa_clip": [1.3, 1.6, 1.3, 1.3]},
    # v14 with a more even base row: its size and spacing variation cut to
    # 35% (other rows unchanged).
    "a_studio_v15_subtle": {**V7_BOTH, "ring_n": [None, 10, 8, None],
        "ring_th": [None, None, 109, 156], "tilt_az": 120,
        "lean": [3, 200], "side_full": [0.0, 0.0],
        "ring_around": [1.0, 1.12, 1.0, 1.0], "ring_out": [1.0, 1.04, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.10, 0.0],
        "aa_clip": [1.3, 1.6, 1.3, 1.3], "ring_jitter": [1.0, 0.35, 1.0, 1.0]},
    "a_studio_v15_clear": {**V7_BOTH, "ring_n": [None, 10, 8, None],
        "ring_th": [None, None, 109, 158], "tilt_az": 120,
        "lean": [3, 200], "side_full": [0.0, 0.0],
        "ring_around": [1.0, 1.22, 1.0, 1.0], "ring_out": [1.0, 1.07, 1.0, 1.0],
        "ring_plump": [1.0, 1.08, 1.0, 1.0], "ring_sag": [0.0, 0.0, 0.10, 0.0],
        "aa_clip": [1.3, 1.6, 1.3, 1.3], "ring_jitter": [1.0, 0.35, 1.0, 1.0]},
    # v15 subtle, base-row variation back up to 50% (with the groove variation
    # below, about 11% size spread), plus small realism
    # touches: drupelets tilted a few degrees off straight out, some rounder
    # and some more angular, groove depth varying around the berry, slightly
    # oval seen from the tip, a little irregularity in the tip star. The
    # _style version adds a shallow style mark at each drupelet's peak.
    "a_studio_v16_subtle": V16_SUBTLE,
    "a_studio_v16_subtle_style": {**V16_SUBTLE, "dimple": 0.05},
    # v16 subtle (picked) with a ripe slump: upper parts settle up to 2% of
    # the height (most at the tip) and the base row spreads 2%. _creases
    # adds a crisp line at the bottom of each groove (0.25 mm pinch, about
    # 0.35 mm wide at 100 mm) without changing the groove's width.
    "a_studio_v17_subtle": {**V16_SUBTLE, "slump": 0.02},
    "a_studio_v17_subtle_creases": {**V16_SUBTLE, "slump": 0.02, "crease_pinch": [0.25, 0.35]},
    # Plumper, less boxy drupelets (longer outward axis deepens creases at
    # the same overlap, so no gaps return). Same stem end as v3.
    "a_studio_v4_rings": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.4,
                          "press": 2.0, "jitter": 0.12, "seed": 1, "square": 2.25,
                          "poles": "ring", "end_n": 4, "end_stretch": 1.25,
                          "end_elong": 1.1, "tip_n": 5, "tip_stretch": 1.0, "tip_jitter": False,
                          "step": 0.77607, "stem_flat": 0.2, "crown": 0.10,
                          "crown_pow": 3},
    "a_studio_v4_spiral": {"count": 20, "aspect": 1.2, "taper": 0.30, "elong": 1.4,
                           "press": 2.0, "jitter": 0.06, "seed": 1, "square": 2.25,
                           "poles": "spiral", "end_n": 4, "end_stretch": 1.25,
                           "end_elong": 1.1, "step": 0.77607, "stem_flat": 0.2, "crown": 0.10,
                           "crown_pow": 3},
    "a_studio": {"count": 20, "aspect": 1.05, "taper": 0.30, "elong": 1.1,
                 "press": 2.0, "jitter": 0.08, "seed": 1},
    "b_bog": {"count": 24, "aspect": 1.05, "taper": 0.22, "elong": 1.05,
              "press": 1.9, "jitter": 0.05, "seed": 2},
    "c_plump": {"count": 14, "aspect": 1.08, "taper": 0.30, "elong": 1.15,
                "press": 2.0, "jitter": 0.10, "seed": 3},
    "d_upright": {"count": 18, "aspect": 1.15, "taper": 0.28, "elong": 1.1,
                  "press": 2.0, "jitter": 0.08, "seed": 4},
    "e_white": {"count": 22, "aspect": 1.05, "taper": 0.25, "elong": 1.1,
                "press": 2.0, "jitter": 0.12, "seed": 5},
}
R0 = 30.0  # outline radius at the tip end before scaling to height
DIMPLE_W = 0.16  # style-mark radius as a fraction of the drupelet's half-width
CROWN = 0.08  # default crown flattening at the tip, so a cap drupelet does not stand up


def tiers(step, poles="cap", end_n=3, tip_n=None):
    """Ring polar angles (0 = stem) and counts for one angular step."""
    if poles == "ring":
        # Rings spread evenly so each end is half a step from the pole and
        # closes with end_n (tip_n at the tip) drupelets meeting there.
        m = max(2, int(round((np.pi - step) / step)) + 1)
        ths = np.linspace(0.5 * step, np.pi - 0.5 * step, m)
        ends = {0: end_n, m - 1: tip_n or end_n}
        return [(th, ends[i] if i in ends
                 else max(3, int(round(2 * np.pi * np.sin(th) / step))))
                for i, th in enumerate(ths)]
    out = []
    th = 0.6 * step
    while th < np.pi - 0.5 * step:
        out.append((th, max(1, int(round(2 * np.pi * np.sin(th) / step)))))
        th += step
    if np.pi - out[-1][0] > 0.5 * step:
        out.append((np.pi, 1))
    return out


def step_for(count, poles="cap", end_n=3, tip_n=None):
    steps = np.linspace(0.35, 1.6, 400)
    n = np.array([sum(k for _, k in tiers(s, poles, end_n, tip_n)) for s in steps])
    return float(steps[np.argmin(np.abs(n - count) + 1e-3 * steps)])


def layout(spec):
    """Drupelet centres, local axes (rows: outward, meridian, azimuth), semi-axes."""
    rng = np.random.default_rng(spec["seed"])
    poles = spec.get("poles", "cap")
    end_n, tip_n = spec.get("end_n", 3), spec.get("tip_n")
    step = spec.get("step") or step_for(spec["count"], poles, end_n, tip_n)
    spiral = poles == "spiral"
    if spiral:
        poles = "ring"  # stem ring, outline and sizing as for rings
    rings = tiers(step, poles, end_n, tip_n)
    if spiral:
        rings = rings[:1]
    if spec.get("ring_th"):
        # Per-ring polar angle overrides in degrees (None keeps the default).
        rings = [(np.radians(t) if t is not None else th, n)
                 for (th, n), t in zip(rings, spec["ring_th"])]
    if spec.get("ring_n"):
        # Per-ring drupelet count overrides (None keeps the default).
        rings = [(th, c if c is not None else n) for (th, n), c in zip(rings, spec["ring_n"])]
    tilts = [np.radians(t or 0.0) for t in spec.get("ring_tilt", [])]
    tilt_az = np.radians(spec.get("tilt_az", 0.0))
    full_amt, full_az = spec.get("side_full", (0.0, 0.0))
    full_az = np.radians(full_az)
    mid_m = spec.get("mid_m_scale", 1.0)
    ring_around = spec.get("ring_around", [])
    ring_out = spec.get("ring_out", [])
    ring_plump = spec.get("ring_plump", [])
    ring_sag = spec.get("ring_sag", [])
    # How far a drupelet's width around may differ from its height
    # (one value, or one per ring).
    aa_clip = spec.get("aa_clip", 1.3)
    stretch_at = {}
    if poles == "ring":
        stretch_at = {0: spec.get("end_stretch", 1.0)}
        if not spiral:
            stretch_at[len(rings) - 1] = spec.get("tip_stretch", spec.get("end_stretch", 1.0))
    asp, j = spec["aspect"], spec["jitter"]
    crown, stem_flat = spec.get("crown", CROWN), spec.get("stem_flat", 0.0)

    bands = ([spec["base_bulge"]] if spec.get("base_bulge") else []) + spec.get("bulges", [])

    def bulge(th):
        out = 1.0
        for amt, centre, width in bands:
            out *= 1 + amt * np.exp(-((np.degrees(th) - centre) / width) ** 2)
        return out

    def outline_r(th):
        # Tucked at the stem, flattened at each end (high powers keep the
        # flattening near the poles).
        c = np.cos(th)
        return bulge(th) * R0 * (1 - spec["taper"] * ((1 + c) / 2) ** 2
                     - stem_flat * ((1 + c) / 2) ** 6
                     - crown * ((1 - c) / 2) ** spec.get("crown_pow", 6 if poles == "ring" else 4))

    def size_r(th):
        # Drupelet sizing ignores end flattening, so flattened ends sink
        # full-size drupelets into a flat face instead of shrinking them.
        if poles != "ring":
            return outline_r(th)
        return bulge(th) * R0 * (1 - spec["taper"] * ((1 + np.cos(th)) / 2) ** 2)

    C, B, A, S, P, D = [], [], [], [], [], []
    # Realism extras draw from their own stream so the layout above is
    # unchanged when they are turned on.
    rng2 = np.random.default_rng(spec["seed"] + 1000)
    d_tilt = spec.get("drupelet_tilt", [])
    sq, sq_var = spec.get("square", 2.0), spec.get("square_var", 0.0)
    gv = spec.get("groove_var", 0.0)
    gph = rng2.uniform(0, 2 * np.pi, 2)
    dimple = spec.get("dimple", 0.0)
    # press is measured at the sunken centres, not the outline:
    # a = p * (e - elong * a) * step / 2, solved for a.
    p = spec["press"]

    def add(th, phi, n, k, jk):
        """One drupelet at (th, phi); n is its ring's count (0 for spiral)."""
        elong = spec.get("end_elong", spec["elong"]) if k == 0 else spec["elong"]
        f = 1 / (1 + p * elong * step / 2)
        s, c = np.sin(th), np.cos(th)
        u = np.array([s * np.cos(phi), s * np.sin(phi), -c])
        out = np.array([u[0], u[1], u[2] / asp])
        out /= np.linalg.norm(out)
        az = np.array([-np.sin(phi), np.cos(phi), 0.0])
        az -= out * (az @ out)
        az /= np.linalg.norm(az)
        B.append([out, np.cross(out, az), az])
        # One side a little fuller than the other (0 at the poles).
        g = 1 + full_amt * s * np.cos(phi - full_az)
        es = size_r(th) * g
        Th.append(th)
        # Meridian spacing grows with aspect away from the poles.
        stretch = np.hypot(c, asp * s) if poles == "ring" else 1.0
        mk = mid_m[k] if isinstance(mid_m, (list, tuple)) and 0 <= k < len(mid_m) else mid_m
        mk = mk if isinstance(mk, (int, float)) else 1.0
        a_m = p * es * step / 2 * f * stretch * stretch_at.get(k, mk if k > 0 else 1.0)
        if n == 0:
            a_a = p * es * step / 2 * f
        else:
            a_a = a_m if n == 1 else p * np.pi * es * max(s, 1e-6) / n * f
        cl = aa_clip[k] if isinstance(aa_clip, (list, tuple)) and 0 <= k < len(aa_clip) else 1.3
        cl = aa_clip if isinstance(aa_clip, (int, float)) else cl
        a_a = float(np.clip(a_a, a_m / cl, a_m * cl))
        a_a *= ring_around[k] if 0 <= k < len(ring_around) else 1.0
        size = 1 + jk * rng.normal()
        ax = np.array([elong * (a_m + a_a) / 2, a_m, a_a]) * size
        # Groove depth varies gently around the berry: where drupelets are a
        # little wider and taller they overlap more and the creases close up.
        gf = 1 + gv * (0.6 * np.sin(2 * phi + gph[0]) + 0.4 * np.sin(3 * phi + 2 * th + gph[1]))
        ax = ax * [1.0, gf, gf]
        # Sink the centre so the drupelet's outer point sits on the outline.
        ro = ring_out[k] if 0 <= k < len(ring_out) else 1.0
        # Sag: the peak slides toward the stem by sg of the half-height while
        # the stem and tip edges stay put (the half toward the tip stretches,
        # the half toward the stem shortens).
        sg = ring_sag[k] if 0 <= k < len(ring_sag) else 0.0
        C.append(ro * g * outline_r(th) * u * [1, 1, asp] - ax[0] * out
                 - sg * ax[1] * B[-1][1])
        S.append(sg)
        # Plumper: grow outward and around from the same centre, not taller.
        pl = ring_plump[k] if 0 <= k < len(ring_plump) else 1.0
        A.append(ax * [pl, 1.0, pl])
        # Each drupelet leans a few degrees off straight out, so highlights
        # do not line up in rows.
        dt = np.radians(d_tilt[k] if 0 <= k < len(d_tilt) else 0.0) * rng2.normal()
        ang = rng2.uniform(0, 2 * np.pi)
        o, m_, a_ = (np.asarray(b) for b in B[-1])
        kx = np.cross(o, np.cos(ang) * m_ + np.sin(ang) * a_)
        kx /= np.linalg.norm(kx)
        B[-1] = [v * np.cos(dt) + np.cross(kx, v) * np.sin(dt) + kx * (kx @ v) * (1 - np.cos(dt))
                 for v in (o, m_, a_)]
        # Cross-section from rounder to more angular, drupelet to drupelet.
        P.append(float(np.clip(sq * (1 + sq_var * rng2.normal()), 2.0, 3.2)))
        # Style mark: shallow dimple at the peak, as a fraction of the
        # drupelet's outward half-depth.
        D.append(dimple * ax[0] * pl)

    Th = []
    for k, (th0, n) in enumerate(rings):
        # The tip ring can skip jitter so its star stays centred.
        jk = 0.0 if (k == len(rings) - 1 and poles == "ring" and not spiral
                     and not spec.get("tip_jitter", True)) else j
        # Per-ring scale on size and spacing variation; the same random
        # draws are still taken, so other rings do not change.
        rj = spec.get("ring_jitter", [])
        jk *= rj[k] if 0 <= k < len(rj) else 1.0
        tilt = tilts[k] if k < len(tilts) else 0.0
        for i in range(n):
            phi = 2 * np.pi * i / n + (k % 2) * np.pi / n + jk * step * rng.normal()
            th = th0 if n == 1 else th0 + 0.5 * jk * step * rng.normal()
            # A tilted ring rises on one side and dips on the other, so the
            # seam between rows wanders instead of running level.
            add(th + tilt * np.cos(phi - tilt_az), phi, n, k, jk)

    if spiral:
        # Golden-angle spiral, the way aggregate fruits set their drupelets:
        # equal area per drupelet from just past the stem ring to the tip,
        # so they nest with no rows and close the tip without a ring.
        ca = np.cos(rings[0][0] + 0.5 * step)
        ns = int(round(2 * np.pi * (ca + 1) / (0.866 * step ** 2)))
        golden = np.pi * (3 - np.sqrt(5))
        for i in range(ns):
            th = np.arccos(ca - (ca + 1) * (i + 0.5) / ns)
            phi = spec.get("spiral_phase", 0.0) + i * golden + j * step * rng.normal()
            add(th + 0.5 * j * step * rng.normal(), phi, 0, -1, j)
    if spec.get("lean"):
        # Bend toward one side: each drupelet turns about the stem pole by
        # an angle growing from 0 at the stem to the full lean at the tip.
        deg, laz = spec["lean"]
        d = np.array([np.cos(np.radians(laz)), np.sin(np.radians(laz)), 0.0])
        kx = np.cross([0.0, 0.0, 1.0], d)
        pivot = np.array([0.0, 0.0, -asp * outline_r(0.0)])

        def rot(v, a):
            return v * np.cos(a) + np.cross(kx, v) * np.sin(a) + kx * (kx @ v) * (1 - np.cos(a))

        for i, th in enumerate(Th):
            a = np.radians(deg) * (1 - np.cos(th)) / 2
            C[i] = pivot + rot(C[i] - pivot, a)
            B[i] = [rot(np.asarray(b), a) for b in B[i]]
    if poles == "ring":
        # Both ends are closed by drupelets; the core only fills the inside.
        r = 0.35 * outline_r(np.pi / 2)
        C.append(np.zeros(3))
        B.append(np.eye(3))
        A.append(np.array([r, r, r * asp]))
        S.append(0.0)
        P.append(sq)
        D.append(0.0)
    else:
        # Core: closes the stem end as a shallow dimple, hidden elsewhere.
        bottom = -asp * outline_r(0.0) * 0.9
        top = asp * 0.5 * R0
        C.append(np.array([0.0, 0.0, (bottom + top) / 2]))
        B.append(np.eye(3))
        A.append(np.array([0.75 * outline_r(np.pi / 2), 0.75 * outline_r(np.pi / 2),
                           (top - bottom) / 2]))
        S.append(0.0)
        P.append(sq)
        D.append(0.0)
    X = {"sag": np.array(S), "square": np.array(P), "dimple": np.array(D)}
    return np.array(C), np.array(B), np.array(A), X


def ellipsoid_dist(C, B, A, X):
    """Approximate signed distance to each drupelet on the plane at x.

    X holds per-drupelet extras: sag makes the stem-to-tip semi-axis 1 + sag
    on the tip side and 1 - sag on the stem side, so the peak sits toward
    the stem; square is the cross-section exponent (2 = oval, higher = more
    angular); dimple is the depth of the style mark at the peak.
    """
    S, P, D = X["sag"], X["square"], X["dimple"]
    oval = bool(np.all(P == 2.0))
    Pc = P[:, None]

    def dist(x, Yf, Zf):
        dx = (x - C[:, 0, None]).astype(np.float32)
        dy = (Yf[None] - C[:, 1, None]).astype(np.float32)
        dz = (Zf[None] - C[:, 2, None]).astype(np.float32)
        q = [B[:, a, 0, None] * dx + B[:, a, 1, None] * dy + B[:, a, 2, None] * dz
             for a in range(3)]
        a1 = A[:, 1, None] * (1 + np.where(q[1] > 0, 1, -1) * S[:, None])
        if not oval:
            # Rounded-polygon outline across the drupelet, oval along its
            # outward axis. F is 1 on the surface and grows linearly along
            # rays from the centre, so |q| (F - 1) / F is the distance to the
            # surface along that ray.
            t = (np.abs(q[1] / a1) ** Pc
                 + np.abs(q[2] / A[:, 2, None]) ** Pc) ** (2 / Pc)
            F = np.sqrt(t + (q[0] / A[:, 0, None]) ** 2)
            r = np.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2)
            d = r * (F - 1) / np.maximum(F, 1e-9)
        else:
            ax = [A[:, 0, None], a1, A[:, 2, None]]
            k0 = sum((qa / ax[a]) ** 2 for a, qa in enumerate(q))
            k1 = sum((qa / ax[a] ** 2) ** 2 for a, qa in enumerate(q))
            k0, k1 = np.sqrt(k0), np.sqrt(k1)
            d = k0 * (k0 - 1) / np.maximum(k1, 1e-9)
        if D.any():
            # Push the surface in around the peak only (outer half).
            lat = (q[1] / a1) ** 2 + (q[2] / A[:, 2, None]) ** 2
            front = np.clip(2 * q[0] / A[:, 0, None], 0, 1)
            d = d + D[:, None] * np.exp(-lat / DIMPLE_W ** 2) * front
        return d.astype(np.float64)
    return dist


def build(spec, height_mm, voxel):
    """Mesh the drupelets at height_mm; returns the mesh, drupelet count, and
    the scaled layout (for skin), before slump and oval."""
    C, B, A, X = layout(spec)
    S = X["sag"]
    # Half extents per axis; a squarer outline reaches up to 2^(1/2 - 1/p) further.
    Ae = A * np.stack([np.ones_like(S), 1 + S, np.ones_like(S)], axis=1)
    ext = np.sqrt(((B * Ae[:, :, None]) ** 2).sum(axis=1)) * 2 ** max(0.0, 0.5 - 1 / X["square"].max())
    lo, hi = (C - ext).min(axis=0), (C + ext).max(axis=0)
    k = height_mm / (hi - lo)[2]
    C, A, lo, hi = C * k, A * k, lo * k, hi * k
    X = {**X, "dimple": X["dimple"] * k}
    seam = dict(SEAMS["wander_50"])
    if spec.get("crease_pinch"):
        seam["pinch_mm"], seam["pinch_w_mm"] = spec["crease_pinch"]
    m = seam_field(ellipsoid_dist(C, B, A, X), len(C), lo, hi, seam, voxel)
    return m, len(C) - 1, (C, B, A, X), (lo, hi, seam)


def drupelet_dists(P, lay, chunk=50_000):
    """Distance from each point to every drupelet, shape (len(P), n)."""
    dist = ellipsoid_dist(*lay)
    return np.concatenate([dist(P[i:i + chunk, 0], P[i:i + chunk, 1], P[i:i + chunk, 2]).T
                           for i in range(0, len(P), chunk)])


def skinned(m, lay, skin):
    """lumps_texture skin on the drupelets: displaced along the nearest
    drupelet's normal, faded to zero near seams."""
    from lumps_texture import DOME_SIGMA_MM, SKIN_VARIANTS, skin_layer
    fine = m.subdivide()  # ~0.2 mm edges, as in lumps_texture
    P = fine.vertices
    d = drupelet_dists(P, lay)
    near = d.argmin(axis=1)
    ds = np.sort(d, axis=1)
    dome = 1.0 - np.exp(-((ds[:, 1] - ds[:, 0]) / DOME_SIGMA_MM) ** 2)
    # Normal of the nearest drupelet by central differences on its distance.
    eps, rows = 0.02, np.arange(len(P))
    N = np.zeros_like(P)
    for a in range(3):
        e = np.zeros(3)
        e[a] = eps
        N[:, a] = (drupelet_dists(P + e, lay)[rows, near]
                   - drupelet_dists(P - e, lay)[rows, near]) / (2 * eps)
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    dn = dome * skin_layer(P, SKIN_VARIANTS[skin])
    out = trimesh.Trimesh(P + N * dn[:, None], fine.faces, process=True)
    out.fix_normals()
    return out


def deform(m, spec, frame=None):
    """Whole-berry shape changes after meshing: ripe slump, then oval.

    frame (z0, height) defaults to the mesh's own; pass the outer surface's
    so an inner wall deforms with it."""
    m.vertices = deform_points(m.vertices, spec, frame or (m.vertices[:, 2].min(),
                                                           np.ptp(m.vertices[:, 2])))
    return m


def deform_points(v, spec, frame):
    v = np.array(v, dtype=np.float64)
    if spec.get("slump"):
        # A ripe berry settles on its stem end: upper parts drop (most at
        # the tip), and the base row spreads a little.
        s = spec["slump"]
        z0, H = frame
        t = (v[:, 2] - z0) / H
        v[:, 2] = z0 + H * (t - s * t ** 2)
        v[:, :2] *= (1 + s * np.exp(-((t - 0.3) / 0.22) ** 2))[:, None]
    if spec.get("oval"):
        # Slightly oval seen from the tip: wider along one azimuth, narrower
        # across it, same area.
        amt, oaz = spec["oval"]
        c, s_ = np.cos(np.radians(oaz)), np.sin(np.radians(oaz))
        R = np.array([[c, -s_], [s_, c]])
        M = R @ np.diag([1 + amt, 1 / (1 + amt)]) @ R.T
        v[:, :2] = v[:, :2] @ M.T
    return v


def clean(m):
    """Drop slivers that collapse when saved as float32 STL, keep the berry."""
    v = np.round(m.vertices.astype(np.float32), 4).astype(np.float64)
    m = trimesh.Trimesh(v, m.faces, process=True)
    m.update_faces(m.nondegenerate_faces(height=1e-6))
    m.remove_unreferenced_vertices()
    m = max(m.split(only_watertight=False), key=lambda b: len(b.faces))
    m.fix_normals()
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    ap.add_argument("--only", nargs="+", choices=list(VARIANTS))
    ap.add_argument("--skin", nargs="*", default=[],
                    help="also write skinned copies (lumps_texture names, e.g. skin_35 skin_fdm_min)")
    args = ap.parse_args()
    for name in args.only or VARIANTS:
        spec = VARIANTS[name]
        raw, n, lay, _ = build(spec, args.height_mm, voxel=args.height_mm / 500)
        outs = {"": raw.copy()}
        for sk in args.skin:
            outs[f"_{sk}"] = skinned(raw, lay, sk)
        for tagname, m in outs.items():
            m = clean(place(deform(m, spec), args.height_mm))
            path = os.path.join(OUT_DIR, f"berry_ref_{name}{tagname}_{int(args.height_mm)}mm.stl")
            m.export(path)
            print(f"{name}{tagname}: {n} drupelets, watertight {m.is_watertight}, "
                  f"extents {np.round(m.extents, 1)} -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
