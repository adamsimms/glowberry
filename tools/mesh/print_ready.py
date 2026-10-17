# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["pymeshlab", "trimesh", "numpy", "scipy", "networkx"]
# ///
"""Print-ready descendants of the provenance scan, as STL test-print files.

Two methods:

- voxel: Blender's voxel remesher closes the scan into one solid, Taubin
  smoothing removes scan pebbling without shrinking it. Faithful, but the
  noisy upper half stays rough: its noise is as deep as the drupelets, so
  stronger smoothing turns it into pits rather than removing it.
- sh: the berry is star-shaped from its centre, so radius is a function of
  direction. A robust (Huber-weighted) spherical-harmonic fit to that radius,
  evaluated on an icosphere, gives a smooth surface that keeps the large lumps
  and drops the noise. Degree 12 is the highest that does not ring.

Screened Poisson was tried first and aborts on this scan ("failed to close
loop") in both PyMeshLab and Open3D above depth 6.

Every output is checked watertight and single-bodied, scaled to --height-mm,
set on Z=0 with Z up. Deviation is a percentage of the fitted radius so it
reads the same at 100 mm and at 6 ft.

Does not touch models/provenance/ or models/smooth/. Writes models/print/.

Run:
    uv run tools/mesh/print_ready.py [--height-mm 100]
"""

import argparse
import json
import os
import subprocess
import tempfile

import numpy as np
import pymeshlab as ml
import trimesh
from scipy.spatial import cKDTree
from scipy.special import sph_harm_y

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCAN = os.path.join(ROOT, "models", "provenance", "berry_merged_up_inv_cm.glb")
LOOKDEV = os.path.join(ROOT, "models", "smooth", "berry_medium.glb")
OUT_DIR = os.path.join(ROOT, "models", "print")

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
BLENDER_SCRIPT = os.path.join(os.path.dirname(__file__), "voxel_remesh_blender.py")

# voxel_frac: voxel size as a fraction of the largest extent (higher = softer).
# taubin: smoothing steps. degree: spherical-harmonic degree.
VARIANTS = {
    "detail": {"method": "voxel", "voxel_frac": 0.004, "taubin": 10},
    "clean": {"method": "voxel", "voxel_frac": 0.008, "taubin": 30},
    "smooth": {"method": "sh", "degree": 12},
    # Packed-spheres look-dev (models/smooth/README.md), closed for printing.
    "lumps": {"method": "voxel", "voxel_frac": 0.003, "taubin": 0,
              "source": "lookdev"},
}
TARGET_FACES = 200_000


def load(path, gltf_y_up):
    scene = trimesh.load(path)
    m = scene.to_geometry() if hasattr(scene, "to_geometry") else scene
    m = trimesh.Trimesh(m.vertices, m.faces, process=True)
    if gltf_y_up:
        m.apply_transform(
            trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_scale(100.0 / m.extents.max())
    m.apply_translation(-m.bounds.mean(axis=0))
    return m


def fit_radius(V):
    A = np.hstack([2.0 * V, np.ones((len(V), 1))])
    b = np.sum(V ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def voxel_remesh(src_ply, frac, workdir):
    out = os.path.join(workdir, f"voxel_{os.path.basename(src_ply)}_{frac}.ply")
    subprocess.run(
        [BLENDER, "-b", "--factory-startup", "-P", BLENDER_SCRIPT, "--",
         src_ply, out, str(frac)],
        check=True, capture_output=True)
    return out


def build_voxel(src_ply, spec, workdir):
    ms = ml.MeshSet()
    ms.load_new_mesh(voxel_remesh(src_ply, spec["voxel_frac"], workdir))
    ms.meshing_remove_connected_component_by_diameter(
        mincomponentdiag=ml.PercentageValue(10))
    if spec["taubin"]:
        ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53,
                                        stepsmoothnum=spec["taubin"])
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=TARGET_FACES, preservenormal=True, preservetopology=True,
        qualitythr=0.5)
    ms.meshing_isotropic_explicit_remeshing(
        iterations=3, targetlen=ml.PercentageValue(0.35))
    ms.meshing_repair_non_manifold_edges()
    ms.meshing_close_holes(maxholesize=50)
    m = ms.current_mesh()
    out = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=True)
    out.fix_normals()
    return out


def real_sh(u, degree):
    th = np.arccos(np.clip(u[:, 2], -1.0, 1.0))
    ph = np.arctan2(u[:, 1], u[:, 0])
    cols = []
    for l in range(degree + 1):
        for m in range(-l, l + 1):
            Y = sph_harm_y(l, abs(m), th, ph)
            if m == 0:
                cols.append(Y.real)
            else:
                cols.append(np.sqrt(2.0) * (Y.imag if m < 0 else Y.real))
    return np.stack(cols, axis=1)


def build_sh(src, spec):
    pts, _ = trimesh.sample.sample_surface_even(src, 150_000, seed=0)
    c = pts.mean(axis=0)
    v = pts - c
    r = np.linalg.norm(v, axis=1)
    B = real_sh(v / r[:, None], spec["degree"])
    w = np.ones(len(r))
    for _ in range(6):
        BW = B * w[:, None]
        coef = np.linalg.solve(BW.T @ B, BW.T @ r)
        res = np.abs(r - B @ coef)
        k = 1.5 * 1.4826 * np.median(res) + 1e-12
        w = np.where(res <= k, 1.0, k / res)
    ico = trimesh.creation.icosphere(subdivisions=7)
    rr = real_sh(ico.vertices, spec["degree"]) @ coef
    return trimesh.Trimesh(c + ico.vertices * rr[:, None], ico.faces, process=True)


def deviation(a, b, radius, n=400_000):
    """Symmetric surface distance between a and b, as % of radius.

    Nearest dense sample stands in for nearest surface point; the error is
    about the sample spacing, well under 0.1% of radius at this n.
    """
    pa, _ = trimesh.sample.sample_surface(a, n, seed=1)
    pb, _ = trimesh.sample.sample_surface(b, n, seed=2)
    da, _ = cKDTree(pb).query(pa)
    db, _ = cKDTree(pa).query(pb)
    d = np.concatenate([da, db]) / radius * 100.0
    return {"mean_pct": round(float(d.mean()), 2),
            "p95_pct": round(float(np.percentile(d, 95)), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-mm", type=float, default=100.0)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="glowberry_print_")

    sources = {
        "scan": load(SCAN, gltf_y_up=True),
        # Written by Open3D straight from Metashape's Z-up frame.
        "lookdev": load(LOOKDEV, gltf_y_up=False),
    }
    plys = {}
    for key, mesh in sources.items():
        plys[key] = os.path.join(workdir, f"{key}.ply")
        mesh.export(plys[key])
    scan = sources["scan"]
    radius = fit_radius(scan.vertices)

    report = {"scan": os.path.relpath(SCAN, ROOT), "height_mm": args.height_mm,
              "variants": {}}
    for name, spec in VARIANTS.items():
        key = spec.get("source", "scan")
        if spec["method"] == "voxel":
            m = build_voxel(plys[key], spec, workdir)
        else:
            m = build_sh(sources[key], spec)
        info = dict(spec)
        if key == "scan":
            info["deviation_from_scan"] = deviation(m, scan, radius)
        m.apply_scale(args.height_mm / m.extents[2])
        lo, hi = m.bounds
        m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
        info.update({
            "faces": int(len(m.faces)),
            "watertight": bool(m.is_watertight),
            "is_volume": bool(m.is_volume),
            "bodies": len(m.split(only_watertight=False)),
            "extents_mm": [round(float(x), 1) for x in m.extents],
            "volume_cm3": round(float(m.volume) / 1000.0, 1),
        })
        path = os.path.join(OUT_DIR, f"berry_{name}_{int(args.height_mm)}mm.stl")
        m.export(path)
        report["variants"][name] = info
        print(f"{name}: {json.dumps(info)}")

    with open(os.path.join(OUT_DIR, "report.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
