# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Slicer-ready copies of the chosen test prints.

- resin_hollow: 2 mm wall, two 3 mm drain holes beside the lowest point,
  label between them. The inner wall is the wander_50 seam field meshed at
  -2 mm (a true inward offset, no folds at the seams); the skin is far
  thinner than the wall, so one cavity serves both 100 mm resin prints.
- resin_solid: small enough to print solid; label at the lowest point.
- fdm_flat: a flat at the stem end (the bottom, where the scan's pin went
  in) so the berry stands without supports under a dome; label in the flat.

Labels are cut 0.4 to 0.5 mm deep and mirrored so they read from below.

Writes models/print/ready/. Sources in models/print/ are not changed.

Run:
    uv run tools/mesh/print_prep.py
"""

import os
import subprocess
import sys
import tempfile

import manifold3d as mf
import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(__file__))
from lumps_clean import LOOKDEV, N_SPHERES, recover_spheres  # noqa: E402
from lumps_seams import VARIANTS as SEAMS, seam_union  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(ROOT, "models", "print")
OUT_DIR = os.path.join(SRC_DIR, "ready")
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
TEXT_SCRIPT = os.path.join(os.path.dirname(__file__), "text_blender.py")

WALL_MM = 2.0
DRAIN_MM = 3.0
DRAIN_OFFSET_MM = 8.0

# source, output, mode, label, label height mm, flat depth mm
JOBS = [  # noqa: E501
    ("berry_texture_skin_35_100mm.stl", "resin_skin35_100mm.stl", "resin_hollow", "35", 6.0, 0),
    ("berry_seams_wander_50_100mm.stl", "resin_plain_100mm.stl", "resin_hollow", "0", 6.0, 0),
    ("berry_seams_wander_50_w25mm.stl", "resin_plain_true_size_25mm.stl", "resin_solid", "0", 2.5, 0),
    ("berry_texture_skin_fdm_min_100mm.stl", "fdm_skin_min_100mm.stl", "fdm_flat", "F", 6.0, 1.0),
    ("berry_seams_wander_50_w50.8mm.stl", "fdm_plain_2in.stl", "fdm_flat", "0", 4.0, 0.6),
]


def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def from_mf(M):
    mm = M.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts),
                           process=True)


def text_mesh(text, height_mm, workdir):
    path = os.path.join(workdir, f"text_{text}.stl")
    if not os.path.exists(path):
        subprocess.run([BLENDER, "-b", "--factory-startup", "-P", TEXT_SCRIPT, "--", path, text],
                       check=True, capture_output=True)
    m = trimesh.load(path)
    m.apply_translation(-m.bounds.mean(axis=0))
    m.apply_scale(height_mm / m.extents[1])
    # Mirror X so it reads correctly when the print is turned over.
    m.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
    m.invert() if m.volume < 0 else None
    return m


def label_cutter(text, height_mm, workdir, x, y, z_top):
    """Text prism from below the bed up to z_top."""
    t = text_mesh(text, height_mm, workdir)
    depth = z_top + 1.0
    t.apply_scale([1.0, 1.0, depth / t.extents[2]])
    t.apply_translation([x - t.bounds.mean(axis=0)[0], y - t.bounds.mean(axis=0)[1],
                         -1.0 - t.bounds[0][2]])
    return to_mf(t)


def lowest_point(m):
    v = m.vertices
    near = v[v[:, 2] < v[:, 2].min() + 0.05]
    return near.mean(axis=0)


def cavity_100mm():
    """wander_50 field at -WALL_MM, in the same frame as the 100 mm files."""
    scene = trimesh.load(LOOKDEV)
    V = np.asarray((scene.to_geometry() if hasattr(scene, "to_geometry") else scene).vertices,
                   dtype=np.float64)
    spheres, _ = recover_spheres(V, N_SPHERES)
    s = 100.0 / np.ptp(V[:, 2])
    spheres_mm = [(c * s, r * s) for c, r in spheres]
    spec = SEAMS["wander_50"]
    outer = seam_union(spheres_mm, spec, voxel=0.2)
    inner = seam_union(spheres_mm, spec, voxel=0.2, level=-WALL_MM)
    k = 100.0 / outer.extents[2]
    lo, hi = outer.bounds
    shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]]) * k
    inner.apply_scale(k)
    inner.apply_translation(shift)
    return inner


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="glowberry_prep_")
    cavity = None

    for src, out, mode, label, text_mm, flat in JOBS:
        m = trimesh.load(os.path.join(SRC_DIR, src))
        M = to_mf(m)
        x, y, z = lowest_point(m)

        if mode == "resin_hollow":
            if cavity is None:
                cavity = to_mf(cavity_100mm())
            M = M - cavity
            for dx in (-DRAIN_OFFSET_MM, DRAIN_OFFSET_MM):
                hole = mf.Manifold.cylinder(WALL_MM + 6.0, DRAIN_MM / 2, DRAIN_MM / 2, 48)
                M = M - hole.translate((x + dx, y, -1.0))
            M = M - label_cutter(label, text_mm, workdir, x, y, z + 0.5)
        elif mode == "resin_solid":
            M = M - label_cutter(label, text_mm, workdir, x, y, z + 0.3)
        else:
            big = 10 * max(m.extents)
            keep = mf.Manifold.cube((big, big, big)).translate((-big / 2, -big / 2, flat))
            M = (M ^ keep).translate((0.0, 0.0, -flat))
            # Centre the label on the flat itself and keep it inside the flat.
            fv = from_mf(M).vertices
            fv = fv[fv[:, 2] < 1e-3][:, :2]
            fx, fy = fv.mean(axis=0)
            fit = 0.55 * np.ptp(fv, axis=0).min()
            M = M - label_cutter(label, min(text_mm, fit), workdir, fx, fy, 0.4)

        r = from_mf(M)
        path = os.path.join(OUT_DIR, out)
        r.export(path)
        print(f"{out}: {mode}, label '{label}', watertight {r.is_watertight}, "
              f"bodies {len(r.split(only_watertight=False))}, volume {r.volume / 1000:.1f} cm3, "
              f"height {r.extents[2]:.1f} mm")


if __name__ == "__main__":
    main()
