"""Step F9e: the third acceptance test for sideways, against a fair control.

Sideways passed the two numeric tests: after refining twenty candidates
equally, one solution stood 1.33x clear of the best genuinely different one,
four independent starts converged onto it, and its RMSE was 1.18% of radius
against the 1.30% upright and inverted managed.

One number in that result needs checking rather than celebrating. Fitness was
0.4524, meaning fewer than half of the sideways points land within 2% of
radius of the mesh surface. Read cold that looks poor, but it has no meaning in
isolation, because the sideways cloud carries 11.4% radial scatter and noisy
points cannot sit near any surface however well the pose is solved.

So the control is upright and inverted. Both are known-good: they built this
mesh. Measuring all three clouds' distance to the mesh the same way says
whether 0.4524 is what a correct registration looks like for this data, or
whether sideways is genuinely worse.

Then the silhouettes, overlaid as cross sections. A correct pose puts the
sideways outline on the mesh outline in every slice.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python step_f9e_verify.py
"""

import json
import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
MESH = os.path.join(WORK, "exports", "merged_up_inv_clean.ply")
REFINE = os.path.join(WORK, "reports", "step_f9d_refine.json")
OUT = os.path.join(WORK, "icp", "sideways_verify.png")
REPORT = os.path.join(WORK, "reports", "step_f9e_verify.json")
TOL = 0.02


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def clean(pcd):
    n0 = len(pcd.points)
    t, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    if len(t.points) >= 0.9 * n0:
        pcd = t
    pts = np.asarray(pcd.points)
    c, R = fit_sphere(pts)
    rr = np.linalg.norm(pts - c, axis=1) / R
    keep = np.flatnonzero((rr > 0.55) & (rr < 1.6))
    if len(keep) >= 0.6 * len(pts):
        pcd = pcd.select_by_index(keep)
    n1 = len(pcd.points)
    lab = np.asarray(pcd.cluster_dbscan(eps=R / 40.0, min_points=10))
    if lab.max() >= 0:
        counts = np.bincount(lab[lab >= 0])
        big = np.flatnonzero(counts >= 0.001 * n1)
        keep = np.flatnonzero(np.isin(lab, big))
        if len(keep) >= 0.6 * n1:
            pcd = pcd.select_by_index(keep)
    return pcd


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(REFINE) as fh:
        ref = json.load(fh)
    pre_mesh = np.asarray(ref["pre_mesh"])
    pre_sw = np.asarray(ref["pre_sideways"])
    T = np.asarray(ref["winner"]["transform"])
    print(f"using the accepted pose: stem {ref['winner']['stem_deg']:.0f}, "
          f"spin {ref['winner']['spin_deg']:.0f}, tilt "
          f"{ref['winner']['tilt_deg']:+.0f}")

    mesh = o3d.io.read_triangle_mesh(MESH)
    mesh.transform(pre_mesh.copy())
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))

    # All three clouds into the normalised mesh frame. Upright and inverted
    # are already in the merged world frame, so they need only pre_mesh;
    # sideways needs its own normalisation and then the solved pose.
    subjects = {}
    for name, fn, extra in (
        ("upright", "upright_A_nomask_highonly_common.ply", None),
        ("inverted", "inverted_A_nomask_highonly_common.ply", None),
        ("sideways", "sideways_A_nomask_highonly.ply", T @ pre_sw),
    ):
        p = os.path.join(CLOUD_DIR, fn)
        if not os.path.exists(p):
            print(f"  missing {fn}")
            continue
        pcd = clean(o3d.io.read_point_cloud(p))
        pcd.transform((extra if extra is not None else pre_mesh).copy())
        subjects[name] = pcd

    print(f"\n=== distance to the merged mesh, measured identically ===")
    print(f"{'cloud':<10} {'points':>8} {'median':>8} {'p90':>8} "
          f"{'within 2%':>10}")
    stats = {}
    for name, pcd in subjects.items():
        q = o3d.core.Tensor(np.asarray(pcd.points).astype(np.float32))
        d = scene.compute_distance(q).numpy()
        stats[name] = {
            "points": len(d),
            "median_pct": float(np.median(d) * 100),
            "p90_pct": float(np.percentile(d, 90) * 100),
            "within_tol": float((d < TOL).mean()),
        }
        s = stats[name]
        print(f"{name:<10} {s['points']:>8} {s['median_pct']:>7.2f}% "
              f"{s['p90_pct']:>7.2f}% {s['within_tol']*100:>9.1f}%")

    ctrl = [stats[n]["within_tol"] for n in ("upright", "inverted")
            if n in stats]
    sw = stats.get("sideways", {}).get("within_tol", 0.0)
    floor = min(ctrl) if ctrl else 1.0
    print(f"\nupright and inverted are known-good: they built this mesh, so "
          f"their numbers are what a correct registration looks like here.")
    ok = sw >= 0.75 * floor
    if ok:
        print(f"  sideways at {sw*100:.1f}% within tolerance sits in the same "
              f"range as the controls ({', '.join(f'{c*100:.1f}%' for c in ctrl)}), "
              f"so 0.45 fitness reflects this data's noise, not a bad pose.")
    else:
        print(f"  sideways at {sw*100:.1f}% falls short of the controls "
              f"({', '.join(f'{c*100:.1f}%' for c in ctrl)}), so the pose is "
              f"worse than a correct registration should be.")

    # Cross sections. A correct pose lays the sideways outline on the mesh
    # outline in every slice.
    MV = np.asarray(mesh.vertices)
    SW = np.asarray(subjects["sideways"].points)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), dpi=110)
    slabs = [(2, 0, 1, "slice at z=0, seen along z"),
             (0, 1, 2, "slice at x=0, seen along x"),
             (1, 0, 2, "slice at y=0, seen along y")]
    for col, (cut, a, b, title) in enumerate(slabs):
        for row, half in enumerate((0.03, 0.10)):
            ax = axes[row][col]
            m = MV[np.abs(MV[:, cut]) < half]
            s = SW[np.abs(SW[:, cut]) < half]
            ax.scatter(m[:, a], m[:, b], s=1.2, c="0.55",
                       label=f"merged mesh ({len(m)})", linewidths=0)
            ax.scatter(s[:, a], s[:, b], s=1.2, c="tab:red", alpha=0.5,
                       label=f"sideways ({len(s)})", linewidths=0)
            ax.add_patch(plt.Circle((0, 0), 1.0, fill=False, color="k",
                                    lw=0.7, ls="--", alpha=0.5))
            ax.set_aspect("equal")
            ax.set_xlim(-1.5, 1.5)
            ax.set_ylim(-1.5, 1.5)
            ax.set_xticks([])
            ax.set_yticks([])
            if row == 0:
                ax.set_title(title, fontsize=10)
            if col == 0:
                ax.set_ylabel(f"slab half-width {half}", fontsize=9)
            ax.legend(fontsize=7, loc="lower right", markerscale=6)

    fig.suptitle("Sideways placed by the accepted pose, over the merged mesh. "
                 "Coincident outlines mean the pose is right.", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT)
    print("\nwrote", OUT)

    with open(REPORT, "w") as fh:
        json.dump({"tol": TOL, "stats": stats,
                   "control_floor": floor, "sideways_within_tol": sw,
                   "matches_controls": bool(ok)}, fh, indent=2)
    print("WROTE", REPORT)
    print("DONE")


main()
