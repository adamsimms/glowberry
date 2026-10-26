# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Drop the sliver drupelets and let their neighbours fill the space.

Spheres 10 and 11 are almost buried: each shows under 3% of the surface, as a
band or a wedge. Deleting a sphere outright opens a valley up to ~6.5 mm deep
(at 100 mm) where the neighbours meet behind it. "fill" instead lets every
bordering sphere grow and shift (centre and radius) so the outer envelope
stays where it was everywhere else, and the gap closes as far as round
drupelets allow. "plain" is the outright delete, for comparison.

Seams use the wander_50 recipe from lumps_seams.py, with each sphere keeping
its own seam noise.

Writes models/print/berry_merge_<tag>_<name>_<H>mm.stl and spheres_<tag>_<name>.json.
BODY is the sphere set the texture, prep, and colour scripts build from.

Run:
    uv run tools/mesh/lumps_merge.py [--height-mm 100] [--drop 10 11]
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
from lumps_seams import VARIANTS, seam_union  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print")

# Picked 2026-10-17: slivers 10 and 11 removed, neighbours filled in.
BODY = [10, 11]


def tag(drop):
    return "no" + "_".join(map(str, drop)) if drop else "all12"


def base_stl(drop, size="100mm"):
    """Untextured body file: the fill variant, or wander_50 when nothing is dropped."""
    if not drop:
        return f"berry_seams_wander_50_{size}.stl"
    return f"berry_merge_{tag(drop)}_fill_{size}.stl"


def body_spheres(height_mm, drop=BODY):
    """Spheres in output millimetres and their original ids."""
    scene = trimesh.load(LOOKDEV)
    V = np.asarray((scene.to_geometry() if hasattr(scene, "to_geometry") else scene).vertices,
                   dtype=np.float64)
    spheres, _ = recover_spheres(V, N_SPHERES)
    s = height_mm / np.ptp(V[:, 2])
    C = np.array([c * s for c, _ in spheres])
    R = np.array([r * s for _, r in spheres])
    if not drop:
        return list(zip(C, R)), list(range(len(R)))
    Cf, Rf, keep = fill(C, R, drop)
    return list(zip(Cf, Rf)), keep


def radial(C, R, centre, U):
    """Outer radius of the union along unit directions U from centre.

    Valid because every sphere contains the berry centre.
    """
    oc = centre - C
    b = U @ oc.T
    c = (oc ** 2).sum(1) - R ** 2
    t = -b + np.sqrt(np.maximum(b * b - c, 0.0))
    return t.max(1), t.argmax(1)


def neighbours(C, R, i):
    return [j for j in range(len(R))
            if j != i and np.linalg.norm(C[i] - C[j]) < R[i] + R[j]
            and _shares_seam(C, R, i, j)]


def _shares_seam(C, R, i, j, n=20000, seed=0):
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    P = C[i] + R[i] * u
    d = np.linalg.norm(P[:, None] - C[None], axis=2) - R[None]
    d[:, i] = np.inf
    vis = (d > 0).all(1)
    return bool(vis.any() and (d[vis].argmin(1) == j).any()
                and (d[vis][d[vis].argmin(1) == j].min(1) < 0.5).any())


def fill(C, R, drop, n_dirs=60000, seed=2):
    centre = C.mean(0)
    rng = np.random.default_rng(seed)
    U = rng.normal(size=(n_dirs, 3))
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    target, own = radial(C, R, centre, U)
    gap = np.isin(own, drop)
    keep = [i for i in range(len(R)) if i not in drop]
    movers = sorted({j for i in drop for j in neighbours(C, R, i)} - set(drop))
    Ck, Rk = C[keep].copy(), R[keep].copy()
    mi = [keep.index(j) for j in movers]

    def unpack(x):
        Cn, Rn = Ck.copy(), Rk.copy()
        x = x.reshape(-1, 4)
        Cn[mi] += x[:, :3]
        Rn[mi] += x[:, 3]
        return Cn, Rn

    def cost(x):
        Cn, Rn = unpack(x)
        r, _ = radial(Cn, Rn, centre, U)
        e = r - target
        rest = np.mean(e[~gap] ** 2)
        dent = np.mean(np.minimum(e[gap], 0) ** 2)
        bulge = np.mean(np.maximum(e[gap], 0) ** 2)
        return 4 * rest + dent + 2 * bulge + 1e-3 * np.mean(x ** 2)

    res = minimize(cost, np.zeros(4 * len(movers)), method="L-BFGS-B",
                   options={"maxiter": 400})
    Cn, Rn = unpack(res.x)
    r, _ = radial(Cn, Rn, centre, U)
    e = r - target
    print(f"fill: moved spheres {movers}; remaining dent max "
          f"{-e[gap].min():.2f} mm, rest of surface max change "
          f"{np.abs(e[~gap]).max():.2f} mm")
    return Cn, Rn, keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    ap.add_argument("--drop", type=int, nargs="+", default=[10, 11])
    args = ap.parse_args()

    scene = trimesh.load(LOOKDEV)
    V = np.asarray((scene.to_geometry() if hasattr(scene, "to_geometry") else scene).vertices,
                   dtype=np.float64)
    spheres, _ = recover_spheres(V, N_SPHERES)
    s = args.height_mm / np.ptp(V[:, 2])
    C = np.array([c * s for c, _ in spheres])
    R = np.array([r * s for _, r in spheres])

    keep = [i for i in range(len(R)) if i not in args.drop]
    Cf, Rf, _ = fill(C, R, args.drop)
    variants = {"plain": (C[keep], R[keep]), "fill": (Cf, Rf)}
    t = tag(args.drop)
    for name, (Cv, Rv) in variants.items():
        m = seam_union(list(zip(Cv, Rv)), VARIANTS["wander_50"],
                       voxel=args.height_mm / 500, ids=keep)
        place(m, args.height_mm)
        stem = f"berry_merge_{t}_{name}_{int(args.height_mm)}mm"
        m.export(os.path.join(OUT_DIR, stem + ".stl"))
        with open(os.path.join(OUT_DIR, f"spheres_{t}_{name}.json"), "w") as f:
            json.dump([{"id": i, "centre_mm": c.round(4).tolist(), "radius_mm": round(float(r), 4)}
                       for i, c, r in zip(keep, Cv, Rv)], f, indent=2)
        print(f"{name}: watertight {m.is_watertight}, extents {np.round(m.extents, 1)} "
              f"-> models/print/{stem}.stl")


if __name__ == "__main__":
    main()
