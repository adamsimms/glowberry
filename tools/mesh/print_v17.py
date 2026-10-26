# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Test-print files for the picked berry (berry_tiers a_studio_v17_subtle).

Each print carries its number engraved on the stem star; the table in
docs/SCANNING.md maps numbers to files and notes. 6 and 9 get a dot so they
read the same at any rotation.

- Hollow resin (100 mm): the inner wall varies from 1.5 to 3 mm, so a lit
  berry shifts in tone without paint: thinner toward the stem end and at
  drupelet centres (brighter, amber), thicker toward the tip and along the
  grooves (darker, red-orange). The inner surface is the same drupelet
  field meshed at that varying offset, so it cannot fold. One 10 mm hole in
  the stem star lets resin drain and a light in; print stem toward the
  build plate so the cavity vents early.
- Solid resin (25 mm) and FDM (2 in, 100 mm): no flat; the lab adds a raft
  or supports.
- Colour: full-colour gradient 3MF (amber base to red-orange top) of the
  hollow 100 mm, 2 in, and 25 mm prints, each with its own ID.

Writes models/print/ready_v17/. Run:
    uv run tools/mesh/print_v17.py
"""

import os
import subprocess
import sys
import tempfile

import manifold3d as mf
import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(__file__))
from berry_tiers import (VARIANTS, build, clean, deform, deform_points,  # noqa: E402
                         drupelet_dists, ellipsoid_dist, skinned)
from scipy.spatial import cKDTree  # noqa: E402
from colour_files import gradient_colours, write_3mf, write_vrml_zip  # noqa: E402
from lumps_seams import seam_field  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "models", "print", "ready_v17")
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
TEXT_SCRIPT = os.path.join(os.path.dirname(__file__), "text_blender.py")

BERRY = "a_studio_v17_subtle"
HEIGHT_MM = 100.0
WALL_MIN_MM, WALL_MAX_MM = 1.5, 3.0
GROOVE_SIGMA_MM = 2.5  # how far the thicker wall spreads from a groove
LIGHT_HOLE_MM = 10.0

# number, output, kind, surface, size, largest label height mm, label depth mm
JOBS = [
    (1, "resin_skin35_100mm.stl", "hollow", "skin_35", None, 6.0, 0.6),
    (2, "resin_plain_100mm.stl", "hollow", "plain", None, 6.0, 0.6),
    (3, "resin_true_size_w25mm.stl", "solid", "plain", 25.0, 2.0, 0.3),
    (4, "fdm_plain_w2in.stl", "solid", "plain", 50.8, 3.5, 0.4),
    (5, "fdm_skin_fdm_min_100mm.stl", "solid", "skin_fdm_min", None, 6.0, 0.6),
    (6, "colour_gradient_skin35_100mm_hollow", "hollow", "skin_35", None, 6.0, 0.6),
    (7, "colour_gradient_w2in", "solid", "plain", 50.8, 3.5, 0.4),
    (8, "colour_gradient_w25mm", "solid", "plain", 25.0, 2.0, 0.3),
]


def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def from_mf(M):
    mm = M.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts),
                           process=True)


def wall_fn(dist, z_lo, z_hi):
    """Wall thickness at each point: height gradient plus groove proximity."""
    def fn(x, Yf, Zf):
        d = dist(x, Yf, Zf)
        top2 = np.partition(d, 1, axis=0)[:2]
        groove = np.exp(-((top2[1] - top2[0]) / GROOVE_SIGMA_MM) ** 2)
        t = np.clip((Zf - z_lo) / (z_hi - z_lo), 0, 1)
        t = t * t * (3 - 2 * t)
        return WALL_MIN_MM + (WALL_MAX_MM - WALL_MIN_MM) * (0.5 * t + 0.5 * groove)
    return fn


def fit(m, scale, shift):
    m.apply_scale(scale)
    m.apply_translation(shift)
    return m


def text_mesh(text, workdir):
    path = os.path.join(workdir, f"text_{text}.stl")
    if not os.path.exists(path):
        subprocess.run([BLENDER, "-b", "--factory-startup", "-P", TEXT_SCRIPT, "--", path, text],
                       check=True, capture_output=True)
    return trimesh.load(path)


def label_spot(raw, lay, pole_raw, keep_out):
    """Point on a stem-star drupelet furthest from any groove and outside
    keep_out (layout units) of the stem axis; returns it and its clearance."""
    v = raw.vertices
    d = drupelet_dists(v, lay)
    near = d.argmin(axis=1)
    ds = np.sort(d, axis=1)
    groove = v[ds[:, 1] - ds[:, 0] < 0.15]
    clear = cKDTree(groove).query(v)[0]
    rad = np.linalg.norm(v[:, :2] - pole_raw[:2], axis=1)
    ok = (near < 4) & (raw.vertex_normals[:, 2] < -0.5) & (rad > keep_out)
    i = np.flatnonzero(ok)[np.argmax(clear[ok])]
    return v[i], clear[i]


def label_cutter(m, text, height_mm, depth_mm, p, pole, workdir):
    """Text cut along the surface normal at p, reading normally from outside,
    its top pointing away from the stem axis."""
    v, n = m.vertices, m.vertex_normals
    near = np.linalg.norm(v - p, axis=1) < height_mm
    nrm = n[near].mean(axis=0)
    nrm /= np.linalg.norm(nrm)
    up = p - pole
    up -= nrm * (up @ nrm)
    up /= np.linalg.norm(up)
    side = np.cross(up, nrm)
    t = text_mesh(text, workdir)
    t.apply_translation(-t.bounds.mean(axis=0))
    t.apply_scale(height_mm / t.extents[1])
    # Prism from depth_mm under the surface to well outside it.
    t.apply_scale([1.0, 1.0, (depth_mm + 4.0) / t.extents[2]])
    t.apply_translation([0.0, 0.0, -t.bounds[0][2] - depth_mm])
    R = np.eye(4)
    R[:3, :3] = np.column_stack([side, up, nrm])
    R[:3, 3] = p
    t.apply_transform(R)
    if t.volume < 0:
        t.invert()
    return to_mf(t)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="glowberry_v17_")
    spec = VARIANTS[BERRY]

    raw, _, lay, (lo, hi, seam) = build(spec, HEIGHT_MM, voxel=HEIGHT_MM / 500)
    frame = (raw.vertices[:, 2].min(), np.ptp(raw.vertices[:, 2]))
    plain = deform(raw.copy(), spec, frame)
    scale = HEIGHT_MM / plain.extents[2]
    b = plain.bounds * scale
    shift = np.array([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])

    surfaces = {"plain": clean(fit(plain, scale, shift))}
    for sk in ("skin_35", "skin_fdm_min"):
        surfaces[sk] = clean(fit(deform(skinned(raw, lay, sk), spec, frame), scale, shift))
    print("outer surfaces done")

    C, B, A, X = lay
    dist = ellipsoid_dist(C, B, A, X)
    inner = seam_field(dist, len(C), lo, hi, seam, voxel=0.25, level=0.0,
                       level_fn=wall_fn(dist, frame[0], frame[0] + frame[1]))
    cavity = to_mf(clean(fit(deform(inner, spec, frame), scale, shift)))
    print("cavity done")

    # Stem pole: the centre of the stem star, carried through the same changes.
    pole_raw = C[:4].mean(axis=0)
    pole = deform_points(pole_raw[None], spec, frame)[0] * scale + shift
    # One label spot for every print: on a stem-star drupelet, clear of the
    # grooves and of the light hole.
    keep_out = (LIGHT_HOLE_MM / 2 + 3.0) / scale
    spot_raw, clear_raw = label_spot(raw, lay, pole_raw, keep_out)
    spot = deform_points(spot_raw[None], spec, frame)[0] * scale + shift
    clear = clear_raw * scale
    print(f"label spot clearance from grooves {clear:.1f} mm at 100 mm")

    for num, out, kind, surface, width, text_mm, depth in JOBS:
        label = f"{num}." if num % 10 in (6, 9) else str(num)
        m = surfaces[surface].copy()
        p, q, k = pole.copy(), spot.copy(), 1.0
        if width:
            k = width / max(m.extents[0], m.extents[1])
            m.apply_scale(k)
            p, q = p * k, q * k
        # Keep the label on the drupelet face: a character is about 0.7 of
        # its height wide.
        text_mm = min(text_mm, 1.6 * clear * k, 0.8 * clear * k / (0.35 * len(label)))
        M = to_mf(m)
        if kind == "hollow":
            M = M - cavity
            near = np.linalg.norm(m.vertices[:, :2] - p[:2], axis=1) < LIGHT_HOLE_MM / 2
            # Lowest surface on the axis is the stem star; cut just past
            # the wall there, not up through the tip.
            z_top = m.vertices[near, 2].min() + WALL_MAX_MM + 2.0
            hole = mf.Manifold.cylinder(z_top + 1.0, LIGHT_HOLE_MM / 2, LIGHT_HOLE_MM / 2, 64)
            M = M - hole.translate((p[0], p[1], -1.0))
        q = m.vertices[np.argmin(np.linalg.norm(m.vertices - q, axis=1))]
        M = M - label_cutter(m, label, text_mm, depth, q, p, workdir)
        r = from_mf(M)
        if out.endswith(".stl"):
            path = os.path.join(OUT_DIR, f"{num}_{out}")
            r.export(path)
        else:
            path = os.path.join(OUT_DIR, f"{num}_{out}.3mf")
            g = gradient_colours(r)
            write_3mf(path, r, g)
            write_vrml_zip(os.path.join(OUT_DIR, f"{num}_{out}.wrl.zip"), r, g)
        print(f"{label} {os.path.basename(path)}: watertight {r.is_watertight}, "
              f"bodies {len(r.split(only_watertight=False))}, volume {r.volume / 1000:.1f} cm3, "
              f"extents {np.round(r.extents, 1)}, label {text_mm:.1f} mm")


if __name__ == "__main__":
    main()
