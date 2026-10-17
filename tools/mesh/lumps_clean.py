# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Clean joins for the packed-spheres look (models/smooth/berry_medium.glb).

The look-dev moved the scan's own vertices onto the sphere union, so joins
follow the scan's irregular triangles and print as zigzags. Here the 12
spheres are recovered from that file (each lump is an exact spherical cap)
and the union is rebuilt from the spheres themselves:

- sharp: exact boolean union, joins are true sphere-sphere circles.
- groove: smooth union (polynomial smooth-min of sphere distances), joins
  become a rounded groove of width set by --groove-mm.

The union is star-shaped about the berry centre (every sphere contains it),
so its outer surface is the same envelope the look-dev computed.

Writes models/print/berry_lumps_{sharp,groove}_<H>mm.stl and spheres.json.

Run:
    uv run tools/mesh/lumps_clean.py [--height-mm 100] [--groove-mm 2.5]
"""

import argparse
import json
import os

import manifold3d as mf
import numpy as np
import pymeshlab as ml
import trimesh
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOOKDEV = os.path.join(ROOT, "models", "smooth", "berry_medium.glb")
OUT_DIR = os.path.join(ROOT, "models", "print")
N_SPHERES = 12


def fit_sphere(P):
    A = np.hstack([2.0 * P, np.ones((len(P), 1))])
    b = np.sum(P ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def recover_spheres(V, n, seeds=600, k=60, seed=0):
    """Greedy: fit spheres to local patches, keep the n with most inliers."""
    rng = np.random.default_rng(seed)
    scale = np.ptp(V, axis=0).max()
    tol = 2e-4 * scale
    tree = cKDTree(V)
    cands = []
    for i in rng.choice(len(V), seeds, replace=False):
        _, nn = tree.query(V[i], k)
        c, r = fit_sphere(V[nn])
        if r > scale:
            continue
        inl = np.abs(np.linalg.norm(V - c, axis=1) - r) < tol
        cands.append((int(inl.sum()), c, r, inl))
    cands.sort(key=lambda t: -t[0])
    taken = np.zeros(len(V), bool)
    spheres = []
    for cnt, c, r, inl in cands:
        new = inl & ~taken
        if new.sum() < 0.6 * cnt:
            continue
        c, r = fit_sphere(V[inl])  # refine on all inliers
        spheres.append((c, r))
        taken |= inl
        if len(spheres) == n:
            break
    return spheres, float(taken.mean())


def sharp_union(spheres, segments=384):
    parts = [mf.Manifold.sphere(r, segments).translate(tuple(c)) for c, r in spheres]
    u = mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    m = u.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3],
                           np.asarray(m.tri_verts), process=True)


def groove_union(spheres, blend, voxel):
    C = np.array([c for c, _ in spheres])
    R = np.array([r for _, r in spheres])
    # Smooth-min lowers the field by up to blend*ln(n), so the surface swells.
    pad = blend * np.log(len(R)) + 3 * voxel
    lo = (C - R[:, None]).min(axis=0) - pad
    hi = (C + R[:, None]).max(axis=0) + pad
    axes = [np.arange(lo[i], hi[i] + voxel, voxel) for i in range(3)]
    field = np.empty([len(a) for a in axes], np.float32)
    Y, Z = np.meshgrid(axes[1], axes[2], indexing="ij")
    for ix, x in enumerate(axes[0]):
        d = np.sqrt((x - C[:, 0, None, None]) ** 2 + (Y - C[:, 1, None, None]) ** 2
                    + (Z - C[:, 2, None, None]) ** 2) - R[:, None, None]
        # Exponential smooth-min over all spheres; blend is the groove width.
        m = d.min(axis=0)
        field[ix] = m - blend * np.log(np.exp(-(d - m) / blend).sum(axis=0))
    verts, faces, _, _ = marching_cubes(field, 0.0, spacing=(voxel,) * 3)
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(verts + lo, faces))
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=400_000, preservenormal=True, preservetopology=True,
        qualitythr=0.5)
    m = ms.current_mesh()
    out = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=True)
    out.fix_normals()
    return out


def place(m, height):
    m.apply_scale(height / m.extents[2])
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    ap.add_argument("--groove-mm", type=float, default=2.5)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    scene = trimesh.load(LOOKDEV)
    src = scene.to_geometry() if hasattr(scene, "to_geometry") else scene
    V = np.asarray(src.vertices, dtype=np.float64)
    spheres, covered = recover_spheres(V, N_SPHERES)
    print(f"recovered {len(spheres)} spheres covering {covered:.1%} of vertices")

    # Work in output millimetres so groove width and voxel size are physical.
    s = args.height_mm / np.ptp(V[:, 2])
    spheres_mm = [(c * s, r * s) for c, r in spheres]
    with open(os.path.join(OUT_DIR, "spheres.json"), "w") as f:
        json.dump([{"centre_mm": c.round(4).tolist(), "radius_mm": round(r, 4)}
                   for c, r in spheres_mm], f, indent=2)

    variants = {
        "sharp": sharp_union(spheres_mm),
        "groove": groove_union(spheres_mm, blend=args.groove_mm / 4,
                               voxel=args.height_mm / 500),
    }
    for name, m in variants.items():
        place(m, args.height_mm)
        path = os.path.join(OUT_DIR, f"berry_lumps_{name}_{int(args.height_mm)}mm.stl")
        m.export(path)
        print(f"{name}: faces {len(m.faces)}, watertight {m.is_watertight}, "
              f"bodies {len(m.split(only_watertight=False))}, "
              f"extents {np.round(m.extents, 1)}  -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
