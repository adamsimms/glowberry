"""Step G2: admit sideways only where it agrees with the mesh, by region.

Filtering point by point would be pointless. Keeping only sideways points that
already sit close to the mesh keeps exactly the points that tell us nothing
new, and throws away any that might fill the remaining gap, since there is no
mesh nearby for a gap point to agree with. It would look like a filter and act
like a copy.

So agreement is judged by region instead. The sphere is divided into equal-area
cells, and each cell is scored by how well the sideways points in it match the
mesh. Where a cell agrees, all of its sideways points are admitted, including
any that extend past the current surface, because the cell's agreement is the
evidence that its reconstruction is sound. Where a cell disagrees, it is
dropped whole.

The threshold is not chosen, it is measured. Upright and inverted built this
mesh, so scoring their cells the same way shows what agreement looks like for
data that is known good, and sideways cells are then required to reach that
standard rather than one invented for the occasion.

What this can and cannot buy. Coverage is already 99.3%, so there is almost no
gap to fill. The real gain would be redundancy: a third measurement in the
cells that pass, letting the mesher average down noise. If the rebuilt mesh in
step_g3 is not measurably better than the current one, that gain did not
materialise and the honest move is to keep the two-remount mesh.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python step_g2_sideways_filter.py
"""

import json
import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
MESH = os.path.join(WORK, "exports", "merged_up_inv_clean.ply")
MERGED_CLOUD = os.path.join(CLOUD_DIR, "merged_up_inv_dense.ply")
SIDEWAYS = os.path.join(CLOUD_DIR,
                        "sideways_A_nomask_highonly_dense2_common.ply")
CONTROLS = {
    "upright": os.path.join(CLOUD_DIR, "upright_A_nomask_highonly_dense2.ply"),
    "inverted": os.path.join(CLOUD_DIR,
                             "inverted_A_nomask_highonly_dense2.ply"),
}
OUT_CLOUD = os.path.join(CLOUD_DIR, "merged_up_inv_sw_dense.ply")
OUT_PNG = os.path.join(WORK, "icp", "sideways_filter.png")
REPORT = os.path.join(WORK, "reports", "step_g2_filter.json")

N_CELLS_Z = 24          # equal-area bands; cells = N_CELLS_Z * N_CELLS_PHI
N_CELLS_PHI = 48
MIN_PER_CELL = 25       # too few points to judge a cell on
POINT_TOL = 0.06        # within an accepted cell, drop points beyond this
KEEP_FLOOR = 0.9


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def clean(pcd, R):
    n0 = len(pcd.points)
    t, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    if len(t.points) >= KEEP_FLOOR * n0:
        pcd = t
    pts = np.asarray(pcd.points)
    c, _ = fit_sphere(pts)
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
    print(f"    cleaned {n0} -> {len(pcd.points)} points")
    return pcd


def cell_ids(pts, centre):
    v = pts - centre
    u = v / np.linalg.norm(v, axis=1)[:, None]
    zi = np.clip(((u[:, 2] + 1) / 2 * N_CELLS_Z).astype(int), 0, N_CELLS_Z - 1)
    ph = np.arctan2(u[:, 1], u[:, 0])
    pi_ = np.clip(((ph + np.pi) / (2 * np.pi) * N_CELLS_PHI).astype(int),
                  0, N_CELLS_PHI - 1)
    return zi * N_CELLS_PHI + pi_


def cell_medians(pts, dist, centre):
    """Median distance per direction cell, and the count in each."""
    cid = cell_ids(pts, centre)
    med = np.full(N_CELLS_Z * N_CELLS_PHI, np.nan)
    cnt = np.bincount(cid, minlength=N_CELLS_Z * N_CELLS_PHI)
    order = np.argsort(cid)
    cs, ds = cid[order], dist[order]
    edges = np.flatnonzero(np.diff(cs)) + 1
    for g in np.split(np.arange(len(cs)), edges):
        if len(g) >= MIN_PER_CELL:
            med[cs[g[0]]] = np.median(ds[g])
    return med, cnt, cid


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mesh = o3d.io.read_triangle_mesh(MESH)
    MV = np.asarray(mesh.vertices)
    centre, R = fit_sphere(MV)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
    print(f"mesh: {len(mesh.triangles)} faces, fitted radius {R:.5f}, "
          f"cells {N_CELLS_Z}x{N_CELLS_PHI}")

    def distances(path, do_clean=False):
        pcd = o3d.io.read_point_cloud(path)
        if do_clean:
            pcd = clean(pcd, R)
        p = np.asarray(pcd.points)
        d = scene.compute_distance(
            o3d.core.Tensor(p.astype(np.float32))).numpy() / R
        return pcd, p, d

    print("\n=== what agreement looks like for the clouds that built it ===")
    ctrl_med = []
    for name, path in CONTROLS.items():
        if not os.path.exists(path):
            print(f"  missing {os.path.basename(path)}")
            continue
        _, p, d = distances(path)
        med, cnt, _ = cell_medians(p, d, centre)
        ok = med[~np.isnan(med)]
        ctrl_med.append(ok)
        print(f"  {name:<9} {len(p):>7} points, {len(ok):>4} judged cells, "
              f"cell median {np.median(ok)*100:.2f}% of radius, "
              f"p90 {np.percentile(ok, 90)*100:.2f}%, "
              f"p95 {np.percentile(ok, 95)*100:.2f}%")
    all_ctrl = np.concatenate(ctrl_med)
    threshold = float(np.percentile(all_ctrl, 95))
    print(f"\n  threshold = the 95th percentile of known-good cells = "
          f"{threshold*100:.2f}% of radius")

    print("\n=== scoring sideways by cell ===")
    sw_pcd, sw, sw_d = distances(SIDEWAYS, do_clean=True)
    sw_med, sw_cnt, sw_cid = cell_medians(sw, sw_d, centre)
    judged = ~np.isnan(sw_med)
    accept = judged & (sw_med <= threshold)
    print(f"  {len(sw)} points in {judged.sum()} judged cells")
    print(f"  cell median {np.median(sw_med[judged])*100:.2f}% of radius "
          f"against {np.median(all_ctrl)*100:.2f}% for the controls")
    print(f"  cells accepted: {accept.sum()} of {judged.sum()} "
          f"({accept.sum()/max(judged.sum(),1)*100:.1f}%)")

    keep = np.isin(sw_cid, np.flatnonzero(accept)) & (sw_d <= POINT_TOL)
    print(f"  points kept: {keep.sum()} of {len(sw)} "
          f"({keep.sum()/len(sw)*100:.1f}%)")
    if keep.sum() == 0:
        print("\n  nothing survives. Sideways does not reach the standard the "
              "other two set anywhere on the berry, so the mesh stays as it "
              "is.")
        return

    merged = o3d.io.read_point_cloud(MERGED_CLOUD)
    mp = np.asarray(merged.points)
    print(f"\ncurrent cloud: {len(mp)} points")

    # How much of this is new rather than a third look at the same place.
    m_cells = set(np.unique(cell_ids(mp, centre)).tolist())
    kept_cells = set(np.unique(sw_cid[keep]).tolist())
    new_cells = kept_cells - m_cells
    print(f"  sideways contributes to {len(kept_cells)} cells, of which "
          f"{len(new_cells)} have no points at all today")
    print(f"  so this is mostly redundancy, not coverage: "
          f"{len(kept_cells)-len(new_cells)} cells gain a third measurement")

    out = merged + sw_pcd.select_by_index(np.flatnonzero(keep))
    o3d.io.write_point_cloud(OUT_CLOUD, out, compressed=True)
    mb = round(os.path.getsize(OUT_CLOUD) / 1e6, 1)
    print(f"\nwrote {os.path.basename(OUT_CLOUD)}: {len(out.points)} points "
          f"({mb} MB), up {(len(out.points)/len(mp)-1)*100:.1f}%")

    with open(REPORT, "w") as fh:
        json.dump({
            "threshold_pct_of_radius": threshold * 100,
            "control_cell_median_pct": float(np.median(all_ctrl) * 100),
            "sideways_cell_median_pct": float(
                np.median(sw_med[judged]) * 100),
            "cells_judged": int(judged.sum()),
            "cells_accepted": int(accept.sum()),
            "points_in": len(sw), "points_kept": int(keep.sum()),
            "cells_gaining_redundancy": len(kept_cells) - len(new_cells),
            "cells_newly_covered": len(new_cells),
            "merged_points_before": len(mp),
            "merged_points_after": len(out.points),
            "out": OUT_CLOUD,
        }, fh, indent=2)
    print("WROTE", REPORT)

    grid = np.full((N_CELLS_Z, N_CELLS_PHI), np.nan)
    grid.flat[:] = sw_med * 100
    fig, ax = plt.subplots(1, 2, figsize=(14, 5), dpi=110)
    im = ax[0].imshow(grid, origin="lower", cmap="viridis", aspect="auto",
                      vmin=0, vmax=threshold * 200)
    ax[0].set_title(f"Sideways agreement per cell, % of radius\n"
                    f"threshold {threshold*100:.2f}% from the known-good "
                    f"clouds")
    ax[0].set_xlabel("longitude cell")
    ax[0].set_ylabel("latitude cell")
    plt.colorbar(im, ax=ax[0])

    acc = np.full((N_CELLS_Z, N_CELLS_PHI), 0.0)
    acc.flat[judged] = 1.0
    acc.flat[accept] = 2.0
    ax[1].imshow(acc, origin="lower", cmap="RdYlGn", aspect="auto",
                 vmin=0, vmax=2)
    ax[1].set_title("Cell outcome: red unjudged, yellow rejected, "
                    "green accepted")
    ax[1].set_xlabel("longitude cell")
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    print("wrote", OUT_PNG)
    print("\nNext: step_g3_remesh.py, then compare against the current mesh")
    print("DONE")


main()
