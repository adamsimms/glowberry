# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Flesh textures on the wander_50 lumps, kept off the seams.

Textures are displacements along the surface normal, faded to zero near
seams by the same sphere-gap mask the seams use (inverted), so the chosen
seams stay as they are.

- vesicles: soft creases between cells (Worley F2-F1), like the pulp sacs
  that show through the drupelet skin in the scan's texture photos.
- skin: two octaves of smooth noise, a faint frosted wrinkle.
- nub: a small dimple at each drupelet's outermost point. The photos show
  dark style specks on drupelets; their exact position is not resolvable
  in the scan texture, so placement at the tip is an interpretation.
- flesh: all three together.
- inner_cutaway: hollow shell, smooth outside, vesicle cells cut into the
  inside wall so the wall thins at cell centres. Cut in half to show the
  inside. A mock for the lit 6 ft shell, not a print file for 1 to 2 in.

Sizes are at 100 mm tall. One drupelet is ~50 mm across here and ~0.9 m at
6 ft (x18.3), so 3.5 mm cells here are ~6 cm on the sculpture.

Writes models/print/berry_texture_<name>_<H>mm.stl.

Run:
    uv run tools/mesh/lumps_texture.py [--height-mm 100] [--only vesicles nub]
"""

import argparse
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(__file__))
from lumps_clean import LOOKDEV, N_SPHERES, place, recover_spheres  # noqa: E402
from lumps_seams import VARIANTS as SEAMS, seam_union, smooth_noise  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print")

SEAM = SEAMS["wander_50"]
DOME_SIGMA_MM = 1.5  # texture fades in over this gap from a seam

VESICLE = {"spacing_mm": 3.0, "depth_mm": 0.08, "crease_mm": 1.0}
SKIN = {"fine_mm": 2.0, "fine_depth": 0.02, "broad_mm": 7.0, "broad_depth": 0.05}
NUB = {"radius_mm": 0.8, "depth_mm": 0.35}
INNER = {"wall_mm": 1.5, "spacing_mm": 4.0, "depth_mm": 0.6, "crease_mm": 1.2}

# Quieter skins, picked over the others. Same noise seeds as SKIN, so each
# is the same pattern at a different strength or with one octave dropped.
SKIN_VARIANTS = {
    "skin_60": {**SKIN, "fine_depth": 0.012, "broad_depth": 0.03},
    "skin_35": {**SKIN, "fine_depth": 0.007, "broad_depth": 0.0175},
    "skin_broad": {**SKIN, "fine_depth": 0.0, "broad_depth": 0.03},
    "skin_fine": {**SKIN, "fine_depth": 0.012, "broad_depth": 0.0},
    # Smallest skin an FDM print can show: about one fine layer (0.1 mm) of
    # relief. The 2 mm octave is narrower than a 0.4 mm nozzle can draw, so
    # only the broad one is kept.
    "skin_fdm_min": {**SKIN, "fine_depth": 0.0, "broad_depth": 0.10},
}

NAMES = ["vesicles", "skin", "nub", "flesh", "inner_cutaway", *SKIN_VARIANTS]


def skin_layer(P, spec):
    return (spec["fine_depth"] * np.tanh(smooth_noise(P, spec["fine_mm"], seed=31))
            + spec["broad_depth"] * np.tanh(smooth_noise(P, spec["broad_mm"], seed=37)))


def sphere_gaps(P, spheres):
    C = np.array([c for c, _ in spheres])
    R = np.array([r for _, r in spheres])
    d = np.linalg.norm(P[:, None, :] - C[None], axis=2) - R[None]
    d.sort(axis=1)
    return d[:, 1] - d[:, 0]


def worley_crease(mesh, P, spacing, crease, seed=5):
    """1 on cell borders easing to 0 in cell centres (plump cells, soft grooves)."""
    count = int(mesh.area / (0.87 * spacing ** 2))
    seeds, _ = trimesh.sample.sample_surface_even(mesh, count, radius=0.6 * spacing, seed=seed)
    d, _ = cKDTree(seeds).query(P, k=2)
    t = np.clip((d[:, 1] - d[:, 0]) / crease, 0.0, 1.0)
    return 1.0 - t * t * (3.0 - 2.0 * t)


def sphere_normals(P, spheres):
    """Outward normal of the nearest sphere. Exact on domes, where textures live."""
    C = np.array([c for c, _ in spheres])
    R = np.array([r for _, r in spheres])
    d = np.linalg.norm(P[:, None, :] - C[None], axis=2) - R[None]
    n = P - C[d.argmin(axis=1)]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def nub_field(P, spheres, centre):
    out = np.zeros(len(P))
    for c, r in spheres:
        axis = (c - centre) / np.linalg.norm(c - centre)
        tip = c + r * axis
        out = np.maximum(out, np.exp(-(np.linalg.norm(P - tip, axis=1) / NUB["radius_mm"]) ** 2))
    return out


def displaced(mesh, dn, spheres):
    # Mesh vertex normals spike at a few decimation leftovers; sphere normals
    # do not, and every displacement is masked to the domes anyway.
    N = sphere_normals(mesh.vertices, spheres)
    m = trimesh.Trimesh(mesh.vertices + N * dn[:, None], mesh.faces, process=True)
    m.fix_normals()
    return m


def to_manifold(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def from_manifold(M):
    mm = M.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts),
                           process=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    ap.add_argument("--only", nargs="+", choices=NAMES)
    args = ap.parse_args()
    names = args.only or NAMES

    scene = trimesh.load(LOOKDEV)
    V = np.asarray((scene.to_geometry() if hasattr(scene, "to_geometry") else scene).vertices,
                   dtype=np.float64)
    spheres, _ = recover_spheres(V, N_SPHERES)
    s = args.height_mm / np.ptp(V[:, 2])
    spheres_mm = [(c * s, r * s) for c, r in spheres]
    centre = np.mean([c for c, _ in spheres_mm], axis=0)
    voxel = args.height_mm / 500

    outer = seam_union(spheres_mm, SEAM, voxel)
    fine = outer.subdivide()  # ~0.2 mm edges so 0.35 mm creases resolve
    P = fine.vertices
    dome = 1.0 - np.exp(-(sphere_gaps(P, spheres_mm) / DOME_SIGMA_MM) ** 2)

    layers = {}
    if {"vesicles", "flesh"} & set(names):
        layers["vesicles"] = -VESICLE["depth_mm"] * worley_crease(
            fine, P, VESICLE["spacing_mm"], VESICLE["crease_mm"])
    if {"skin", "flesh"} & set(names):
        layers["skin"] = skin_layer(P, SKIN)
    if {"nub", "flesh"} & set(names):
        layers["nub"] = -NUB["depth_mm"] * nub_field(P, spheres_mm, centre)

    outputs = {}
    for name in ("vesicles", "skin", "nub"):
        if name in names:
            outputs[name] = displaced(fine, dome * layers[name], spheres_mm)
    for name, spec in SKIN_VARIANTS.items():
        if name in names:
            outputs[name] = displaced(fine, dome * skin_layer(P, spec), spheres_mm)
    if "flesh" in names:
        outputs["flesh"] = displaced(fine, dome * (layers["vesicles"] + layers["skin"]
                                                   + layers["nub"]), spheres_mm)

    if "inner_cutaway" in names:
        inner = seam_union(spheres_mm, SEAM, voxel, level=-INNER["wall_mm"]).subdivide()
        Pi = inner.vertices
        inner_dome = 1.0 - np.exp(-(sphere_gaps(Pi, spheres_mm) / DOME_SIGMA_MM) ** 2)
        # Cells thin the wall at their centres; borders stay at full wall.
        thin = INNER["depth_mm"] * (1.0 - worley_crease(inner, Pi, INNER["spacing_mm"],
                                                        INNER["crease_mm"], seed=9))
        inner = displaced(inner, inner_dome * thin, spheres_mm)
        shell = to_manifold(outer) - to_manifold(inner)
        lo, hi = outer.bounds
        half = mf.Manifold.cube(tuple((hi - lo) * 1.2)).translate(
            (lo[0] - 0.1 * (hi - lo)[0], centre[1], lo[2] - 0.1 * (hi - lo)[2]))
        outputs["inner_cutaway"] = from_manifold(shell ^ half)

    for name, m in outputs.items():
        place(m, args.height_mm)
        path = os.path.join(OUT_DIR, f"berry_texture_{name}_{int(args.height_mm)}mm.stl")
        m.export(path)
        print(f"{name}: faces {len(m.faces)}, watertight {m.is_watertight}, "
              f"bodies {len(m.split(only_watertight=False))} -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
