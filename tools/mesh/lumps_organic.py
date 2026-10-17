# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Organic lumps: the 12-sphere look pulled part way toward the real scan.

Starts from the smooth-union lumps (lumps_clean.py) with a narrow groove,
then moves each vertex radially toward the scan's own surface, taken as a
robust spherical-harmonic fit so scan noise does not come along. The pull
fraction is the only source of irregularity in the "scan" variants, so the
unevenness is the berry's, not invented. The "skin" variant adds a faint
procedural texture on top; that part is an aesthetic choice, not evidence.

The scan and the look-dev live in different frames (Metashape chunk vs the
scaled GLB), so the scan is registered to the lumps by ICP with scale,
seeded from the 24 axis-aligned rotations.

Writes models/print/berry_organic_<name>_<H>mm.stl.

Run:
    uv run tools/mesh/lumps_organic.py [--height-mm 100]
"""

import argparse
import itertools
import os
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(__file__))
from lumps_clean import LOOKDEV, N_SPHERES, groove_union, place, recover_spheres  # noqa: E402
from print_ready import SCAN, real_sh  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print")

GROOVE_MM = 0.6
SH_DEGREE = 20
# pull: fraction of the way toward the scan surface. skin_mm: texture depth.
VARIANTS = {
    "light": {"pull": 0.25, "skin_mm": 0.0},
    "medium": {"pull": 0.45, "skin_mm": 0.0},
    "medium_skin": {"pull": 0.45, "skin_mm": 0.15},
}


def rotations24():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for i, (p, s) in enumerate(zip(perm, signs)):
                R[i, p] = s
            if np.linalg.det(R) > 0:
                out.append(R)
    return out


def register(src_pts, target):
    """Similarity transform taking src_pts onto target mesh surface."""
    tgt_pts, _ = trimesh.sample.sample_surface(target, 60_000, seed=3)
    tree = cKDTree(tgt_pts)
    sc, tc = src_pts.mean(0), tgt_pts.mean(0)
    s0 = np.sqrt(((tgt_pts - tc) ** 2).sum(1).mean() / ((src_pts - sc) ** 2).sum(1).mean())
    sub = src_pts[np.random.default_rng(0).choice(len(src_pts), 20_000, replace=False)]
    best = None
    for R in rotations24():
        init = np.eye(4)
        init[:3, :3] = s0 * R
        init[:3, 3] = tc - s0 * R @ sc
        M, _, cost = trimesh.registration.icp(sub, tgt_pts, initial=init,
                                              max_iterations=40, scale=True)
        if best is None or cost < best[1]:
            best = (M, cost)
    M = best[0]
    d, _ = tree.query(trimesh.transform_points(sub, M))
    return M, float(np.median(d))


def scan_radius_fn(pts, centre, degree):
    v = pts - centre
    r = np.linalg.norm(v, axis=1)
    B = real_sh(v / r[:, None], degree)
    w = np.ones(len(r))
    for _ in range(6):
        BW = B * w[:, None]
        coef = np.linalg.solve(BW.T @ B, BW.T @ r)
        res = np.abs(r - B @ coef)
        k = 1.5 * 1.4826 * np.median(res) + 1e-12
        w = np.where(res <= k, 1.0, k / res)
    return lambda u: real_sh(u, degree) @ coef


def skin(P, depth, feature_mm=4.0, waves=48, seed=7):
    """Sum of random plane waves: smooth, isotropic, cheap."""
    rng = np.random.default_rng(seed)
    k = rng.normal(size=(waves, 3))
    k *= (2 * np.pi / feature_mm) * rng.uniform(0.6, 1.6, (waves, 1)) / np.linalg.norm(k, axis=1, keepdims=True)
    ph = rng.uniform(0, 2 * np.pi, waves)
    n = np.sin(P @ k.T + ph).sum(1)
    return depth * n / np.abs(n).max()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    args = ap.parse_args()

    scene = trimesh.load(LOOKDEV)
    V = np.asarray((scene.to_geometry() if hasattr(scene, "to_geometry") else scene).vertices,
                   dtype=np.float64)
    spheres, _ = recover_spheres(V, N_SPHERES)
    s = args.height_mm / np.ptp(V[:, 2])
    spheres_mm = [(c * s, r * s) for c, r in spheres]
    base = groove_union(spheres_mm, blend=GROOVE_MM / 4, voxel=args.height_mm / 500)
    centre = np.mean([c for c, _ in spheres_mm], axis=0)
    print(f"base groove {GROOVE_MM} mm: {len(base.faces)} faces")

    sscene = trimesh.load(SCAN)
    scan = sscene.to_geometry() if hasattr(sscene, "to_geometry") else sscene
    scan_pts, _ = trimesh.sample.sample_surface_even(scan, 150_000, seed=0)
    M, med = register(scan_pts, base)
    scan_pts = trimesh.transform_points(scan_pts, M)
    print(f"scan registered, median gap {med:.2f} mm ({med / args.height_mm:.2%} of height)")
    r_scan = scan_radius_fn(scan_pts, centre, SH_DEGREE)

    v = base.vertices - centre
    r = np.linalg.norm(v, axis=1)
    u = v / r[:, None]
    rs = r_scan(u)
    for name, spec in VARIANTS.items():
        r_new = r + spec["pull"] * (rs - r)
        P = centre + u * r_new[:, None]
        if spec["skin_mm"]:
            P = P + u * skin(P, spec["skin_mm"])[:, None]
        m = trimesh.Trimesh(P, base.faces, process=True)
        m.fix_normals()
        place(m, args.height_mm)
        path = os.path.join(OUT_DIR, f"berry_organic_{name}_{int(args.height_mm)}mm.stl")
        m.export(path)
        print(f"{name}: watertight {m.is_watertight}, volume {m.is_volume}, "
              f"bodies {len(m.split(only_watertight=False))}, "
              f"extents {np.round(m.extents, 1)} -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
