# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Organic seams, full drupelets.

The drupelets stay the recovered spheres. Only a band around each seam
changes. On a seam the two nearest spheres are equally near, so the gap
between their distances is zero; on a dome it is large. A Gaussian of that
gap is the mask, so domes are untouched.

Inside the band, built into the distance field before meshing:
- wander: the seam slides toward one drupelet or the other along slow
  curves (each sphere's distance nudged by its own smooth noise).
- width: the groove's blend width swells and narrows along its length.
Both are invented, smooth, and long relative to the groove, so the seam
reads as a natural crease rather than a stitched line.

The "scan" variant then lets seams sink, never rise, where the real berry's
surface (robust spherical-harmonic fit, registered by ICP) sits lower.

Writes models/print/berry_seams_<name>_<H>mm.stl.

Run:
    uv run tools/mesh/lumps_seams.py [--height-mm 100] [--only wander wander_50]
"""

import argparse
import os
import sys

import numpy as np
import pymeshlab as ml
import trimesh
from skimage.measure import marching_cubes

sys.path.insert(0, os.path.dirname(__file__))
from lumps_clean import LOOKDEV, N_SPHERES, place, recover_spheres  # noqa: E402
from lumps_organic import register, scan_radius_fn  # noqa: E402
from print_ready import SCAN  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print")

GROOVE_MM = 0.6
SEAM_SIGMA_MM = 1.0
SH_DEGREE = 20
# wander_mm: sideways drift. width_var: +/- fraction of groove width.
# feature_mm: length of one wander along a seam. scan: inward pull fraction.
# Keep wander_mm * 2.4 * 0.86 / SEAM_SIGMA_MM under 1 or seams fold.
VARIANTS = {
    "wander": {"wander_mm": 0.2, "width_var": 0.6, "feature_mm": 20.0, "scan": 0.0},
    "wander_strong": {"wander_mm": 0.35, "width_var": 0.8, "feature_mm": 16.0, "scan": 0.0},
    "wander_scan": {"wander_mm": 0.2, "width_var": 0.6, "feature_mm": 20.0, "scan": 0.6},
    # Gentler steps of "wander" (percent of its drift).
    "wander_70": {"wander_mm": 0.14, "width_var": 0.6, "feature_mm": 20.0, "scan": 0.0},
    "wander_50": {"wander_mm": 0.10, "width_var": 0.6, "feature_mm": 20.0, "scan": 0.0},
    "wander_30": {"wander_mm": 0.06, "width_var": 0.6, "feature_mm": 20.0, "scan": 0.0},
}


def smooth_noise(P, feature_mm, waves=48, seed=11):
    """Unit-variance smooth noise from random plane waves."""
    rng = np.random.default_rng(seed)
    k = rng.normal(size=(waves, 3))
    k *= (2 * np.pi / feature_mm) * rng.uniform(0.6, 1.6, (waves, 1)) \
        / np.linalg.norm(k, axis=1, keepdims=True)
    ph = rng.uniform(0, 2 * np.pi, waves)
    return np.sin(P @ k.T + ph).sum(1) / np.sqrt(waves / 2)


def smin(d, k):
    m = d.min(axis=0)
    return m - k * np.log(np.exp(-(d - m) / k).sum(axis=0))


def seam_union(spheres, spec, voxel, level=0.0, ids=None):
    """Mesh the seam-wandered union; negative level gives an inward offset.

    ids are the spheres' original indices, so a sphere keeps its own seam
    noise when others are dropped from the list.
    """
    C = np.array([c for c, _ in spheres])
    R = np.array([r for _, r in spheres])

    def dist(x, Yf, Zf):
        return np.sqrt((x - C[:, 0, None]) ** 2 + (Yf - C[:, 1, None]) ** 2
                       + (Zf - C[:, 2, None]) ** 2) - R[:, None]

    return seam_field(dist, len(R), (C - R[:, None]).min(axis=0),
                      (C + R[:, None]).max(axis=0), spec, voxel, level, ids)


def seam_field(dist, n, lo, hi, spec, voxel, level=0.0, ids=None, level_fn=None):
    """seam_union for any blobs: dist(x, Yf, Zf) gives (n, len(Yf)) distances
    on the plane at x; lo/hi bound the blobs. level_fn(x, Yf, Zf), if given,
    is added to the field, so meshing at level 0 gives an inward offset that
    varies from point to point."""
    ids = range(n) if ids is None else ids
    k0 = GROOVE_MM / 4
    pad = 2 * k0 * np.log(n) + spec["wander_mm"] * 3 + 3 * voxel
    lo = np.asarray(lo) - pad
    hi = np.asarray(hi) + pad
    axes = [np.arange(lo[i], hi[i] + voxel, voxel) for i in range(3)]
    field = np.empty([len(a) for a in axes], np.float32)
    Y, Z = np.meshgrid(axes[1], axes[2], indexing="ij")
    Yf, Zf = Y.ravel(), Z.ravel()
    for ix, x in enumerate(axes[0]):
        d = dist(x, Yf, Zf)
        f = smin(d, k0)
        order = np.argsort(d, axis=0)[:2]
        cols = np.arange(d.shape[1])
        d1, d2 = d[order[0], cols], d[order[1], cols]
        w = np.exp(-((d2 - d1) / SEAM_SIGMA_MM) ** 2)
        band = np.flatnonzero((w > 0.01) & (np.abs(f) < 3.0))
        if len(band):
            P = np.column_stack([np.full(len(band), x), Yf[band], Zf[band]])
            wb = w[band]
            # One noise field per sphere keeps the shift continuous where the
            # nearest pair changes (triple junctions). tanh bounds it so the
            # seam cannot fold back on itself.
            N = np.stack([1.2 * np.tanh(smooth_noise(P, spec["feature_mm"], waves=24,
                                                     seed=100 + i) / 1.2)
                          for i in ids])
            db = d[:, band] + spec["wander_mm"] * wb * N
            kb = k0 * (1 + spec["width_var"] * wb
                       * np.tanh(smooth_noise(P, spec["feature_mm"] * 0.8, seed=23)))
            f[band] = smin(db, kb)
            if spec.get("pinch_mm"):
                # Crisp line at the very bottom of the groove: a narrow
                # inward pinch where the two nearest blobs are nearly level.
                top2 = np.sort(db, axis=0)[:2]
                f[band] += spec["pinch_mm"] * np.exp(
                    -((top2[1] - top2[0]) / spec["pinch_w_mm"]) ** 2)
        if level_fn is not None:
            f = f + level_fn(x, Yf, Zf)
        field[ix] = f.reshape(Y.shape)
    verts, faces, _, _ = marching_cubes(field, level, spacing=(voxel,) * 3)
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(verts + lo, faces))
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=400_000, preservenormal=True, preservetopology=True,
        qualitythr=0.5)
    m = ms.current_mesh()
    out = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=True)
    # Decimation can leave zero-volume specks; keep the berry.
    out = max(out.split(only_watertight=False), key=lambda b: len(b.faces))
    out.fix_normals()
    return out


def seam_mask(P, spheres):
    C = np.array([c for c, _ in spheres])
    R = np.array([r for _, r in spheres])
    d = np.linalg.norm(P[:, None, :] - C[None], axis=2) - R[None]
    d.sort(axis=1)
    return np.exp(-((d[:, 1] - d[:, 0]) / SEAM_SIGMA_MM) ** 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    ap.add_argument("--only", nargs="+", choices=list(VARIANTS))
    args = ap.parse_args()
    variants = {k: VARIANTS[k] for k in (args.only or VARIANTS)}

    scene = trimesh.load(LOOKDEV)
    V = np.asarray((scene.to_geometry() if hasattr(scene, "to_geometry") else scene).vertices,
                   dtype=np.float64)
    spheres, _ = recover_spheres(V, N_SPHERES)
    s = args.height_mm / np.ptp(V[:, 2])
    spheres_mm = [(c * s, r * s) for c, r in spheres]
    centre = np.mean([c for c, _ in spheres_mm], axis=0)

    r_scan = None
    for name, spec in variants.items():
        m = seam_union(spheres_mm, spec, voxel=args.height_mm / 500)
        if spec["scan"]:
            if r_scan is None:
                sscene = trimesh.load(SCAN)
                scan = sscene.to_geometry() if hasattr(sscene, "to_geometry") else sscene
                pts, _ = trimesh.sample.sample_surface_even(scan, 150_000, seed=0)
                M, med = register(pts, m)
                print(f"scan registered, median gap {med:.2f} mm")
                r_scan = scan_radius_fn(trimesh.transform_points(pts, M), centre, SH_DEGREE)
            v = m.vertices - centre
            r = np.linalg.norm(v, axis=1)
            u = v / r[:, None]
            dr = np.minimum(0.0, spec["scan"] * (r_scan(u) - r))
            m = trimesh.Trimesh(centre + u * (r + seam_mask(m.vertices, spheres_mm) * dr)[:, None],
                                m.faces, process=True)
            m.fix_normals()
        place(m, args.height_mm)
        path = os.path.join(OUT_DIR, f"berry_seams_{name}_{int(args.height_mm)}mm.stl")
        m.export(path)
        print(f"{name}: watertight {m.is_watertight}, volume {m.is_volume}, "
              f"bodies {len(m.split(only_watertight=False))} -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
