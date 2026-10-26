# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Even out the drupelets while keeping the scan's layout.

The recovered spheres are all ~27-30 mm (at 100 mm) but overlap unevenly,
so some show 12% of the surface and two show under 3% (slivers). Deleting
the slivers and growing their neighbours left oversized, lopsided lumps.

Here every sphere moves and resizes a little, starting from the scan's
layout, to minimise:
- uneven shares: each drupelet's share of the surface (soft ownership by
  outer radius, seen from the berry centre) pulled toward 1/N.
- radius spread: drupelets stay a similar size.
- outline change: the union's outer radius stays near the original 12.
- deep overlap: centres closer than half the mean radius are pushed apart,
  so no seam is a shallow scratch.
Every sphere must still contain the berry centre (keeps the union
star-shaped, which the outline measure relies on).

Seams use the wander_50 recipe; each sphere keeps its own seam noise.

Writes models/print/berry_relax_<N>_<H>mm.stl and spheres_relax_<N>.json.

Run:
    uv run tools/mesh/lumps_relax.py [--height-mm 100] [--drop-sets "" "10 11"]
"""

import argparse
import json
import os
import sys

import numpy as np
import trimesh
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(__file__))
from lumps_clean import LOOKDEV, N_SPHERES, place, recover_spheres  # noqa: E402
from lumps_merge import radial  # noqa: E402
from lumps_seams import VARIANTS, seam_union  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print")

W_SHARE, W_RADIUS, W_OUTLINE, W_OVERLAP, W_CONTAIN = 400.0, 20.0, 3.0, 5.0, 50.0
SOFT_MM = 0.4  # ownership softness


def shares(C, R, centre, U, soft=SOFT_MM):
    oc = centre - C
    b = U @ oc.T
    c = (oc ** 2).sum(1) - R ** 2
    t = -b + np.sqrt(np.maximum(b * b - c, 0.0))
    w = np.exp((t - t.max(1, keepdims=True)) / soft)
    return (w / w.sum(1, keepdims=True)).mean(0)


def surface_shares(C, R, n=60000, seed=0):
    """True visible-area shares of the sharp union, for reporting."""
    rng = np.random.default_rng(seed)
    areas = []
    for i, (c, r) in enumerate(zip(C, R)):
        u = rng.normal(size=(n, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        d = np.linalg.norm((c + r * u)[:, None] - C[None], axis=2) - R
        d[:, i] = np.inf
        areas.append(4 * np.pi * r * r * (d > 0).all(1).mean())
    a = np.array(areas)
    return a / a.sum()


def relax(C0, R0, target_C, target_R, n_dirs=20000, seed=3):
    centre = target_C.mean(0)
    rng = np.random.default_rng(seed)
    U = rng.normal(size=(n_dirs, 3))
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    target, _ = radial(target_C, target_R, centre, U)
    n = len(R0)
    iu = np.triu_indices(n, 1)

    def unpack(x):
        x = x.reshape(n, 4)
        return C0 + x[:, :3], R0 + x[:, 3]

    def cost(x):
        C, R = unpack(x)
        r, _ = radial(C, R, centre, U)
        share = np.sum((shares(C, R, centre, U) * n - 1) ** 2) / n
        spread = np.var(R) / np.mean(R) ** 2
        outline = np.mean((r - target) ** 2)
        d = np.linalg.norm(C[:, None] - C[None], axis=2)[iu]
        overlap = np.mean(np.maximum(0.5 * R.mean() - d, 0) ** 2)
        contain = np.mean(np.maximum(np.linalg.norm(C - centre, axis=1) - (R - 2.0), 0) ** 2)
        return (W_SHARE * share + W_RADIUS * spread * 100 + W_OUTLINE * outline
                + W_OVERLAP * overlap + W_CONTAIN * contain)

    res = minimize(cost, np.zeros(4 * n), method="L-BFGS-B", options={"maxiter": 600})
    C, R = unpack(res.x)
    r, _ = radial(C, R, centre, U)
    return C, R, float(np.abs(r - target).max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    ap.add_argument("--drop-sets", nargs="+", default=["", "10 11"])
    args = ap.parse_args()

    scene = trimesh.load(LOOKDEV)
    V = np.asarray((scene.to_geometry() if hasattr(scene, "to_geometry") else scene).vertices,
                   dtype=np.float64)
    spheres, _ = recover_spheres(V, N_SPHERES)
    s = args.height_mm / np.ptp(V[:, 2])
    C = np.array([c * s for c, _ in spheres])
    R = np.array([r * s for _, r in spheres])
    sh = surface_shares(C, R)
    print(f"original 12: shares {sh.min():.1%} to {sh.max():.1%}, "
          f"radii {R.min():.1f} to {R.max():.1f} mm")

    for spec in args.drop_sets:
        drop = [int(i) for i in spec.split()]
        keep = [i for i in range(len(R)) if i not in drop]
        Cr, Rr, moved = relax(C[keep], R[keep], C, R)
        sh = surface_shares(Cr, Rr)
        n = len(keep)
        print(f"relax {n}: shares {sh.min():.1%} to {sh.max():.1%}, radii {Rr.min():.1f} to "
              f"{Rr.max():.1f} mm, outline change max {moved:.2f} mm, centres moved max "
              f"{np.linalg.norm(Cr - C[keep], axis=1).max():.1f} mm")
        m = seam_union(list(zip(Cr, Rr)), VARIANTS["wander_50"],
                       voxel=args.height_mm / 500, ids=keep)
        place(m, args.height_mm)
        stem = f"berry_relax_{n}_{int(args.height_mm)}mm"
        m.export(os.path.join(OUT_DIR, stem + ".stl"))
        with open(os.path.join(OUT_DIR, f"spheres_relax_{n}.json"), "w") as f:
            json.dump([{"id": i, "centre_mm": c.round(4).tolist(), "radius_mm": round(float(r), 4)}
                       for i, c, r in zip(keep, Cr, Rr)], f, indent=2)
        print(f"  watertight {m.is_watertight}, extents {np.round(m.extents, 1)} "
              f"-> models/print/{stem}.stl")


if __name__ == "__main__":
    main()
