# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Full-colour test prints of the v18c berry (broader crown), coloured per
drupelet for the Mimaki's translucent mode.

The first Mimaki samples (v17, height gradient) showed that translucent mode
dilutes colour and that the seams came out paler than the drupelets. Here
each drupelet carries its own colour:

- by row: stem star and base row golden amber, middle row orange as before,
  tip row deeper burnt orange (kept orange, not crimson; the darker sample
  read as a raspberry);
- within each drupelet: lighter at the centre of the dome and on its lower
  side, deeper toward its edges and upper side;
- at the seams: deeper and darker, so the grooves read darker when lit;
- a little variation from drupelet to drupelet.

Colours blend over a short distance across each groove. Two strengths:
11 moderate, 12 strong. Both are 50 mm tall, solid, with the same light
pocket as print 9.

Writes models/print/ready_v18/. Run:
    uv run tools/mesh/print_v18.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from berry_tiers import V18C, drupelet_dists, undeform_points  # noqa: E402
from print_v17 import run  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print", "ready_v18")

# Rows in layout order: stem star, base, middle, tip.
ROWS = [4, 10, 8, 5]

# Tone scale in sRGB: negative is lighter golden amber, positive deeper
# burnt orange. Hues stay between about 13 and 38 degrees, never crimson.
PALETTE = [(-1.0, (253, 200, 90)), (-0.6, (251, 176, 64)), (0.0, (242, 122, 34)),
           (0.7, (224, 90, 24)), (1.0, (217, 74, 20)), (1.6, (184, 56, 14))]

STRENGTHS = {
    # row offsets (stem, base, middle, tip), centre-to-edge, lower-to-upper,
    # seam deepening, seam darkening, drupelet variation
    11: {"rows": (-0.6, -0.6, 0.0, 0.7), "edge": 0.35, "side": 0.25,
         "seam_tone": 0.5, "seam_dark": 0.15, "var": 0.12},
    12: {"rows": (-0.9, -0.9, 0.0, 1.0), "edge": 0.6, "side": 0.4,
         "seam_tone": 0.8, "seam_dark": 0.3, "var": 0.18},
}
BLEND_MM = 0.4  # colour blend across a groove, in the 100 mm frame
SEAM_MM = 1.2   # how far the seam colour reaches into a drupelet, 100 mm frame

JOBS = [
    (11, "cloudberry_colour_50mm_pocket_moderate", "pocket", "plain", 50.0, 3.5, 0.4),
    (12, "cloudberry_colour_50mm_pocket_strong", "pocket", "plain", 50.0, 3.5, 0.4),
]


def to_lin(c):
    c = np.asarray(c, float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.round(255 * np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055))


def tone_to_lin(s):
    """Tone value(s) to linear RGB along the palette."""
    xs = np.array([p[0] for p in PALETTE])
    cs = to_lin([p[1] for p in PALETTE])
    s = np.clip(s, xs[0], xs[-1])
    return np.stack([np.interp(s, xs, cs[:, i]) for i in range(3)], axis=-1)


def drupelet_colours(mesh, ctx):
    p = STRENGTHS[ctx["num"]]
    C, B, A, X = ctx["lay"]
    C, B, A = C[:-1], B[:-1], A[:-1]  # drop the core
    n = len(C)
    assert n == sum(ROWS), n
    row = np.repeat(np.arange(4), ROWS)
    rng = np.random.default_rng(11)
    var = p["var"] * (rng.random(n) * 2 - 1)

    # Final mesh back to the layout frame (100 mm tall).
    P = mesh.vertices / ctx["k"]
    P = (P - ctx["shift"]) / ctx["scale"]
    P = undeform_points(P, ctx["spec"], ctx["frame"])

    d = drupelet_dists(P, ctx["lay"])[:, :-1]
    dmin = d.min(axis=1, keepdims=True)
    ds = np.sort(d, axis=1)
    seam = np.exp(-((ds[:, 1] - ds[:, 0]) / SEAM_MM) ** 2)

    # Per-drupelet tone at every vertex, then a soft blend across grooves.
    q = np.einsum("nij,mnj->mni", B, P[:, None, :] - C[None])  # (verts, drupelets, 3)
    r2 = (q[..., 1] / A[None, :, 1]) ** 2 + (q[..., 2] / A[None, :, 2]) ** 2
    side = np.clip(q[..., 1] / A[None, :, 1], -1, 1)  # toward the tip is up
    tone = (np.array(p["rows"])[row][None] + var[None]
            + p["edge"] * (np.clip(r2, 0, 1.5) - 0.35) + p["side"] * side)
    w = np.exp(-(d - dmin) / BLEND_MM)
    w /= w.sum(axis=1, keepdims=True)
    t = (w * tone).sum(axis=1) + p["seam_tone"] * seam
    lin = tone_to_lin(t) * (1 - p["seam_dark"] * seam)[:, None]
    return to_srgb(lin).astype(np.uint8)


def main():
    run(V18C, JOBS, OUT_DIR, colour_fn=drupelet_colours)


if __name__ == "__main__":
    main()
