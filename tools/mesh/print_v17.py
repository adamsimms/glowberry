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
- Pocket (50 mm tall, full colour and plain): solid, since jetted support
  cannot be cleared from inside a hollow berry, with a 12 mm light pocket
  bored 25 mm up from the stem star and a 2 mm lead-in at its mouth. The
  number sits on the underside outside the pocket, on a base-row drupelet
  if the stem star is too small.

Writes models/print/ready_v17/. Run:
    uv run tools/mesh/print_v17.py
    uv run tools/mesh/print_v17.py --only 9 10   (selected jobs)
"""

import argparse
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
POCKET_MM, POCKET_DEPTH_MM = 12.0, 25.0
POCKET_MARGIN_MM = 2.0  # from the pocket edge to the nearest edge of the number
# 45 degree lead-in at the mouth. The pocket is about as wide as the stem
# star, so without it a thin ring of the star is left inside the recess.
POCKET_CHAMFER_MM = 2.0

# number, output, kind, surface, size, largest label height mm, label depth mm.
# size is the target width (larger of x and y) for scaled jobs, except for
# pocket jobs, where it is the height; None keeps 100 mm tall.
JOBS = [
    (1, "cloudberry_resin_100mm_hollow.stl", "hollow", "skin_35", None, 6.0, 0.6),
    (2, "cloudberry_resin_100mm_hollow_smooth.stl", "hollow", "plain", None, 6.0, 0.6),
    (3, "cloudberry_resin_25mm.stl", "solid", "plain", 25.0, 2.0, 0.3),
    (4, "cloudberry_fdm_2in.stl", "solid", "plain", 50.8, 3.5, 0.4),
    (5, "cloudberry_fdm_100mm.stl", "solid", "skin_fdm_min", None, 6.0, 0.6),
    (6, "cloudberry_colour_100mm_hollow", "hollow", "skin_35", None, 6.0, 0.6),
    (7, "cloudberry_colour_2in", "solid", "plain", 50.8, 3.5, 0.4),
    (8, "cloudberry_colour_25mm", "solid", "plain", 25.0, 2.0, 0.3),
    (9, "cloudberry_colour_50mm_pocket", "pocket", "plain", 50.0, 3.5, 0.4),
    (10, "cloudberry_50mm_pocket.stl", "pocket", "plain", 50.0, 3.5, 0.4),
]


def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def from_mf(M):
    mm = M.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts),
                           process=True)


def write_ply(path, m, colours):
    """Binary PLY with per-vertex colour (Mimaki and others read it)."""
    V, F = np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.int32)
    head = (f"ply\nformat binary_little_endian 1.0\ncomment units mm\n"
            f"element vertex {len(V)}\nproperty float x\nproperty float y\nproperty float z\n"
            "property uchar red\nproperty uchar green\nproperty uchar blue\n"
            f"element face {len(F)}\nproperty list uchar int vertex_indices\nend_header\n")
    vd = np.zeros(len(V), dtype=[("p", "<f4", 3), ("c", "u1", 3)])
    vd["p"], vd["c"] = V, colours
    fd = np.zeros(len(F), dtype=[("n", "u1"), ("i", "<i4", 3)])
    fd["n"], fd["i"] = 3, F
    with open(path, "wb") as f:
        f.write(head.encode())
        f.write(vd.tobytes())
        f.write(fd.tobytes())


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


def groove_clearance(raw, lay):
    """Nearest drupelet per vertex and distance to the nearest groove."""
    v = raw.vertices
    d = drupelet_dists(v, lay)
    ds = np.sort(d, axis=1)
    groove = v[ds[:, 1] - ds[:, 0] < 0.15]
    return d.argmin(axis=1), cKDTree(groove).query(v)[0]


def label_spot(raw, near, clear, pole_raw, keep_out, stem_star=True, need=None):
    """Point on a downward-facing drupelet (the stem star unless stem_star is
    False) outside keep_out (layout units) of the stem axis: the one furthest
    from any groove, or with need, the one closest to the axis at least need
    from a groove. Returns it and its clearance, or None if nothing fits."""
    v = raw.vertices
    rad = np.linalg.norm(v[:, :2] - pole_raw[:2], axis=1)
    ok = (raw.vertex_normals[:, 2] < -0.5) & (rad > keep_out)
    if stem_star:
        ok &= near < 4
    if need is not None:
        ok &= clear >= need
    if not ok.any():
        return None
    i = np.flatnonzero(ok)
    i = i[np.argmin(rad[i])] if need is not None else i[np.argmax(clear[i])]
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="+", metavar="N", help="build only these job numbers")
    only = ap.parse_args().only
    jobs = [j for j in JOBS if not only or j[0] in only]
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
        if any(j[3] == sk for j in jobs):
            surfaces[sk] = clean(fit(deform(skinned(raw, lay, sk), spec, frame), scale, shift))
    print("outer surfaces done")

    C, B, A, X = lay
    if any(j[2] == "hollow" for j in jobs):
        dist = ellipsoid_dist(C, B, A, X)
        inner = seam_field(dist, len(C), lo, hi, seam, voxel=0.25, level=0.0,
                           level_fn=wall_fn(dist, frame[0], frame[0] + frame[1]))
        cavity = to_mf(clean(fit(deform(inner, spec, frame), scale, shift)))
        print("cavity done")

    # Stem pole: the centre of the stem star, carried through the same changes.
    pole_raw = C[:4].mean(axis=0)
    pole = deform_points(pole_raw[None], spec, frame)[0] * scale + shift
    near_d, clear_d = groove_clearance(raw, lay)

    def place(spot_raw, clear_raw):
        return deform_points(spot_raw[None], spec, frame)[0] * scale + shift, clear_raw * scale

    # One label spot for the numbered prints 1 to 8: on a stem-star
    # drupelet, clear of the grooves and of the light hole.
    keep_out = (LIGHT_HOLE_MM / 2 + 3.0) / scale
    spot, clear = place(*label_spot(raw, near_d, clear_d, pole_raw, keep_out))
    print(f"label spot clearance from grooves {clear:.1f} mm at 100 mm")

    def fit_label(text_mm, clear, k, label):
        # Keep the label on the drupelet face: a character is about 0.7 of
        # its height wide.
        return min(text_mm, 1.6 * clear * k, 0.8 * clear * k / (0.35 * len(label)))

    def pocket_spot(k, text_mm, label):
        """Spot for a pocket job at scale k: the whole number stays
        POCKET_MARGIN_MM outside the pocket, as close to the axis as it fits
        at full height with 20% spare groove clearance (tucked under, not on
        the rim). Stem star if it fits there, else any downward-facing
        drupelet."""
        ko = (POCKET_MM / 2 + POCKET_MARGIN_MM + text_mm / 2) / k / scale
        need = 1.2 * text_mm / fit_label(1e9, 1.0, 1.0, label) / k / scale
        for stem_star, where in ((True, "stem star"), (False, "drupelet underside")):
            s = label_spot(raw, near_d, clear_d, pole_raw, ko, stem_star, need)
            if s is not None:
                return place(*s) + (where,)

    for num, out, kind, surface, width, text_mm, depth in jobs:
        label = f"{num}." if num % 10 in (6, 9) else str(num)
        m = surfaces[surface].copy()
        p, q, k, c = pole.copy(), spot.copy(), 1.0, clear
        if kind == "pocket":
            k = width / m.extents[2]
            q, c, where = pocket_spot(k, text_mm, label)
            print(f"{label} label on the {where}, {np.linalg.norm(q[:2] - p[:2]) * k:.1f} mm "
                  f"from the axis, groove clearance {c * k:.1f} mm")
            m.apply_scale(k)
            p, q = p * k, q * k
        elif width:
            k = width / max(m.extents[0], m.extents[1])
            m.apply_scale(k)
            p, q = p * k, q * k
        text_mm = fit_label(text_mm, c, k, label)
        M = to_mf(m)
        if kind == "pocket":
            near = np.linalg.norm(m.vertices[:, :2] - p[:2], axis=1) < POCKET_MM / 2
            # Measured from the lowest surface point around the axis (the
            # stem star), never from the tip.
            z0 = m.vertices[near, 2].min()
            r0 = POCKET_MM / 2
            pocket = mf.Manifold.cylinder(POCKET_DEPTH_MM + 1.0, r0, r0, 96).translate((p[0], p[1], z0 - 1.0))
            lead = mf.Manifold.cylinder(POCKET_CHAMFER_MM, r0 + POCKET_CHAMFER_MM, r0, 96)
            before = M.volume()
            M = M - (pocket + lead.translate((p[0], p[1], z0)))
            print(f"{label} pocket {POCKET_MM:.0f} mm wide, floor at z {z0 + POCKET_DEPTH_MM:.1f} mm "
                  f"({POCKET_DEPTH_MM:.0f} mm above the lowest point at the axis, z {z0:.2f}), "
                  f"{(before - M.volume()) / 1000:.2f} cm3 removed")
        if kind == "hollow":
            M = M - cavity
            near = np.linalg.norm(m.vertices[:, :2] - p[:2], axis=1) < LIGHT_HOLE_MM / 2
            # Lowest surface on the axis is the stem star; cut just past
            # the wall there, not up through the tip.
            z_top = m.vertices[near, 2].min() + WALL_MAX_MM + 2.0
            hole = mf.Manifold.cylinder(z_top + 1.0, LIGHT_HOLE_MM / 2, LIGHT_HOLE_MM / 2, 64)
            M = M - hole.translate((p[0], p[1], -1.0))
        q = m.vertices[np.argmin(np.linalg.norm(m.vertices - q, axis=1))]
        L = label_cutter(m, label, text_mm, depth, q, p, workdir)
        if kind == "pocket":
            # Footprint on the surface: the cutter flattened onto the plane
            # at q (its outer part sits in the air).
            lv = np.array(L.to_mesh().vert_properties)[:, :3]
            nrm = m.vertex_normals[np.linalg.norm(m.vertices - q, axis=1) < text_mm].mean(axis=0)
            nrm /= np.linalg.norm(nrm)
            lv -= np.outer((lv - q) @ nrm, nrm)
            gap = np.linalg.norm(lv[:, :2] - p[:2], axis=1).min() - POCKET_MM / 2
            print(f"{label} number {gap:.1f} mm from the pocket edge at its closest")
        M = M - L
        r = from_mf(M)
        if out.endswith(".stl"):
            path = os.path.join(OUT_DIR, f"{num}_{out}")
            r.export(path)
        else:
            path = os.path.join(OUT_DIR, f"{num}_{out}.3mf")
            g = gradient_colours(r)
            write_3mf(path, r, g)
            write_vrml_zip(os.path.join(OUT_DIR, f"{num}_{out}.wrl.zip"), r, g)
            write_ply(os.path.join(OUT_DIR, f"{num}_{out}.ply"), r, g)
        print(f"{label} {os.path.basename(path)}: watertight {r.is_watertight}, "
              f"bodies {len(r.split(only_watertight=False))}, volume {r.volume / 1000:.1f} cm3, "
              f"extents {np.round(r.extents, 1)}, label {text_mm:.1f} mm")


if __name__ == "__main__":
    main()
