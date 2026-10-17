# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx"]
# ///
"""Rescale print STLs by widest point, the measure the caliper took.

Widest point is the longest chord through the mesh (convex-hull diameter),
which is how the provenance berry's 2.50 cm was reported. Output keeps Z up,
centred on X/Y, sitting on Z=0.

Run:
    uv run tools/mesh/resize.py IN.stl [IN2.stl ...] --widest-mm 25 25.4 50.8
"""

import argparse
import os

import numpy as np
import trimesh
from scipy.spatial.distance import pdist


def widest(m):
    H = m.convex_hull.vertices
    # Diameter lies between hull vertices that are extreme along some
    # direction; prune to those before the exact pairwise check.
    rng = np.random.default_rng(0)
    dirs = rng.normal(size=(4000, 3))
    proj = H @ dirs.T
    keep = np.unique(np.concatenate([proj.argmax(0), proj.argmin(0)]))
    return float(pdist(H[keep]).max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--widest-mm", type=float, nargs="+", required=True)
    args = ap.parse_args()
    for path in args.inputs:
        src = trimesh.load(path)
        base = os.path.splitext(path)[0].rsplit("_", 1)[0]
        for w in args.widest_mm:
            m = src.copy()
            m.apply_scale(w / widest(m))
            lo, hi = m.bounds
            m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
            out = f"{base}_w{w:g}mm.stl"
            m.export(out)
            print(f"{os.path.basename(out)}: widest {widest(m):.2f} mm, "
                  f"bbox {np.round(m.extents, 2)} mm, watertight {m.is_watertight}")


if __name__ == "__main__":
    main()
