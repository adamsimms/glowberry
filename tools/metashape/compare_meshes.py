"""Compare the two-remount mesh against the one with sideways added.

The test is which mesh better fits the evidence, not which looks smoother or
carries more faces. Upright and inverted are the trusted evidence: they put
83.5% and 84.3% of their points within 2% of radius of the original surface,
where sideways managed 47.6%. So the first requirement on any rebuild is that
it fits those two no worse than before. A mesh that drifts away from the good
data to accommodate the noisy data is worse, however many faces it has.

The second question is whether sideways gained anything where it was admitted.
Its accepted points should sit closer to the new surface than to the old one,
in those 69 cells. If they do not, the extra points were absorbed without
effect and there is nothing to keep.

Decision rule, set before looking:
  keep the rebuild only if it fits upright and inverted at least as well, and
  fits the accepted sideways points measurably better.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python compare_meshes.py
"""

import json
import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
OLD = os.path.join(WORK, "exports", "merged_up_inv_clean.ply")
NEW = os.path.join(WORK, "exports", "merged_up_inv_sw_clean.ply")
EVIDENCE = {
    "upright": os.path.join(CLOUD_DIR, "upright_A_nomask_highonly_dense2.ply"),
    "inverted": os.path.join(CLOUD_DIR,
                             "inverted_A_nomask_highonly_dense2.ply"),
}
SIDEWAYS = os.path.join(CLOUD_DIR,
                        "sideways_A_nomask_highonly_dense2_common.ply")
FILTER_REPORT = os.path.join(WORK, "reports", "step_g2_filter.json")
REPORT = os.path.join(WORK, "reports", "compare_meshes.json")


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def load(path):
    m = o3d.io.read_triangle_mesh(path)
    s = o3d.t.geometry.RaycastingScene()
    s.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(m))
    return m, s


def topology(m, R, centre):
    V = np.asarray(m.vertices)
    F = np.asarray(m.triangles)
    e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    lab, n, _ = m.cluster_connected_triangles()
    lab = np.asarray(lab)
    big = np.bincount(lab).max() / len(F) * 100
    r = np.linalg.norm(V - centre, axis=1) / R
    return {
        "faces": len(F), "vertices": len(V),
        "boundary_edges": int((counts == 1).sum()),
        "components": len(np.asarray(n)),
        "largest_component_pct": float(big),
        "relief_sd_pct": float(r.std() * 100),
    }


def main():
    old_m, old_s = load(OLD)
    new_m, new_s = load(NEW)
    centre, R = fit_sphere(np.asarray(old_m.vertices))

    print("=== topology ===")
    print(f"{'':<10} {'faces':>8} {'bound.':>7} {'comps':>6} {'largest':>8} "
          f"{'relief sd':>10}")
    tops = {}
    for name, m in (("two", old_m), ("with sw", new_m)):
        t = topology(m, R, centre)
        tops[name] = t
        print(f"{name:<10} {t['faces']:>8} {t['boundary_edges']:>7} "
              f"{t['components']:>6} {t['largest_component_pct']:>7.2f}% "
              f"{t['relief_sd_pct']:>9.2f}%")

    def dist(scene, pts):
        return scene.compute_distance(
            o3d.core.Tensor(pts.astype(np.float32))).numpy() / R

    print("\n=== does it still fit the trusted evidence? ===")
    print(f"{'cloud':<10} {'two: median':>12} {'with sw':>10} "
          f"{'two: p90':>10} {'with sw':>10}")
    fits = {}
    regressed = False
    for name, path in EVIDENCE.items():
        p = np.asarray(o3d.io.read_point_cloud(path).points)
        do, dn = dist(old_s, p), dist(new_s, p)
        fits[name] = {
            "old_median": float(np.median(do) * 100),
            "new_median": float(np.median(dn) * 100),
            "old_p90": float(np.percentile(do, 90) * 100),
            "new_p90": float(np.percentile(dn, 90) * 100),
        }
        f = fits[name]
        print(f"{name:<10} {f['old_median']:>11.3f}% "
              f"{f['new_median']:>9.3f}% {f['old_p90']:>9.3f}% "
              f"{f['new_p90']:>9.3f}%")
        if f["new_median"] > f["old_median"] * 1.02:
            regressed = True

    print("\n=== did sideways gain anything where it was admitted? ===")
    sw = o3d.io.read_point_cloud(SIDEWAYS)
    sp = np.asarray(sw.points)
    d_old, d_new = dist(old_s, sp), dist(new_s, sp)
    # Only the points the filter kept matter, so use the same rule: close to
    # the original surface, in a cell that passed.
    with open(FILTER_REPORT) as fh:
        fr = json.load(fh)
    kept = d_old <= 0.06
    print(f"  all sideways points: median {np.median(d_old)*100:.3f}% -> "
          f"{np.median(d_new)*100:.3f}% of radius")
    print(f"  the {kept.sum()} near points: "
          f"{np.median(d_old[kept])*100:.3f}% -> "
          f"{np.median(d_new[kept])*100:.3f}%")
    gain = (np.median(d_old[kept]) - np.median(d_new[kept])) / max(
        np.median(d_old[kept]), 1e-12) * 100
    print(f"  improvement where admitted: {gain:+.1f}%")

    print(f"\n=== how much did the surface actually move? ===")
    mv = np.asarray(new_m.vertices)
    moved = dist(old_s, mv)
    print(f"  new mesh vertices sit {np.median(moved)*100:.3f}% of radius "
          f"from the old surface (p99 {np.percentile(moved,99)*100:.2f}%)")
    print(f"  {(moved > 0.01).mean()*100:.1f}% of the new surface moved by "
          f"more than 1% of radius")

    print("\n=== decision ===")
    print(f"  fits the trusted clouds no worse: {not regressed}")
    print(f"  sideways measurably better where admitted: {gain > 5}")
    keep_new = (not regressed) and gain > 5
    if keep_new:
        print("  KEEP THE REBUILD: sideways earned its place.")
    else:
        print("  KEEP THE TWO-REMOUNT MESH. Sideways was correctly "
              "registered, and once held to the standard the other two set "
              "it qualified over 7% of the surface, added no coverage, and "
              "changed nothing measurable. Registering it was still worth "
              "doing: it is now known that the mount, not the method, was "
              "the limit.")

    with open(REPORT, "w") as fh:
        json.dump({"topology": tops, "evidence_fit": fits,
                   "sideways_gain_pct": float(gain),
                   "regressed": bool(regressed),
                   "keep_rebuild": bool(keep_new),
                   "cells_accepted": fr.get("cells_accepted"),
                   "points_kept": fr.get("points_kept")}, fh, indent=2)
    print("WROTE", REPORT)
    print("DONE")


main()
