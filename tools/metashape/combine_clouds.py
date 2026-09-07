"""Combine the two remount clouds into the single cloud the mesh is built from.

Both were exported in the shared frame, so this is a concatenation, not a
registration. The point of doing it here rather than in Metashape is that
mergeChunks cannot carry two sets of depth maps, so a combined point cloud is
the only representation that can hold both remounts at once and be imported
back for meshing.

Re-checks the frame at downscale 2 before combining. The earlier gate passed on
the downscale 4 clouds, and a finer surface is a stricter test of the same
registration: agreement that held at 4 could still come apart at 2 if the
transform were subtly wrong.

Cleaning is deliberately light and guarded. An earlier version of the
registration script lost 99,344 points to 160 by clustering with a radius
derived from mean nearest-neighbour distance, so any step that would remove
more than a small fraction is reverted rather than trusted.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python combine_clouds.py
"""

import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
OUT_DIR = os.path.join(WORK, "icp")
UPRIGHT = "upright_A_nomask_highonly_dense2"
INVERTED = "inverted_A_nomask_highonly_dense2"
COMBINED = os.path.join(CLOUD_DIR, "merged_up_inv_dense.ply")

NB = 96          # finer bins than the downscale 4 check, since there are more points
MIN_PTS = 2
KEEP_FLOOR = 0.9  # any single cleaning step may not remove more than 10%
# Keep points within this band of the fitted radius. The berry's own relief is
# within about 25%, so this cannot clip real surface.
R_WINDOW = (0.55, 1.6)
# A cluster smaller than this fraction of the cloud is a floater, not surface.
FLOATER_FRACTION = 0.001


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def occupancy(pts, centre):
    v = pts - centre
    r = np.linalg.norm(v, axis=1)
    lon = np.arctan2(v[:, 1], v[:, 0])
    sinlat = np.clip(v[:, 2] / r, -1, 1)
    g = np.zeros((NB, NB), int)
    np.add.at(g, (((sinlat + 1) / 2 * NB).astype(int).clip(0, NB - 1),
                  ((lon + np.pi) / (2 * np.pi) * NB).astype(int).clip(0, NB - 1)), 1)
    return g >= MIN_PTS


def main():
    up = o3d.io.read_point_cloud(os.path.join(CLOUD_DIR, f"{UPRIGHT}.ply"))
    inv = o3d.io.read_point_cloud(os.path.join(CLOUD_DIR, f"{INVERTED}.ply"))
    P, Q = np.asarray(up.points), np.asarray(inv.points)
    print(f"upright  {len(P)} points")
    print(f"inverted {len(Q)} points")

    centre, radius = fit_sphere(np.vstack([P, Q]))
    _, r_up = fit_sphere(P)
    _, r_inv = fit_sphere(Q)
    print(f"\nsphere fit: radius {radius:.5f} combined, {r_up:.5f} upright, "
          f"{r_inv:.5f} inverted ({abs(r_up-r_inv)/radius*100:.2f}% apart)")

    a, b = occupancy(P, centre), occupancy(Q, centre)
    print(f"coverage: upright {a.mean()*100:.1f}%, inverted {b.mean()*100:.1f}%, "
          f"together {(a|b).mean()*100:.1f}%, shared {(a&b).mean()*100:.1f}%")

    # Agreement only where both have surface.
    v = Q - centre
    r = np.linalg.norm(v, axis=1)
    lon = np.arctan2(v[:, 1], v[:, 0])
    sinlat = np.clip(v[:, 2] / r, -1, 1)
    bi = ((sinlat + 1) / 2 * NB).astype(int).clip(0, NB - 1)
    bj = ((lon + np.pi) / (2 * np.pi) * NB).astype(int).clip(0, NB - 1)
    idx = np.flatnonzero((a & b)[bi, bj])
    rng = np.random.default_rng(0)
    if len(idx) > 20000:
        idx = rng.choice(idx, 20000, replace=False)
    tree = o3d.geometry.KDTreeFlann(up)
    d = np.empty(len(idx))
    for i, k in enumerate(idx):
        _, _, d2 = tree.search_knn_vector_3d(Q[k], 1)
        d[i] = np.sqrt(d2[0])
    q = np.percentile(d, [50, 90]) / radius * 100
    print(f"agreement across the shared band, % of radius: median {q[0]:.2f}, "
          f"p90 {q[1]:.2f}")
    if q[0] > 3.0:
        print("  registration does not hold at this resolution; stop here")
        return

    merged = up + inv
    n0 = len(merged.points)
    print()

    trimmed, _ = merged.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    if len(trimmed.points) >= KEEP_FLOOR * n0:
        merged = trimmed
        print(f"statistical outliers: {n0} -> {len(merged.points)} points")
    else:
        print(f"statistical outlier removal would cut {n0} to "
              f"{len(trimmed.points)}, more than the "
              f"{(1-KEEP_FLOOR)*100:.0f}% allowed; skipped")

    # Radial window. The first mesh from this cloud reached +300% of radius and
    # broke into 1015 components, so some points sit far off the berry. Its own
    # relief stays within about 25% of radius, so this window cannot clip real
    # surface, and statistical outlier removal misses these because they arrive
    # in clumps rather than as isolated points.
    pts = np.asarray(merged.points)
    c, R = fit_sphere(pts)
    rr = np.linalg.norm(pts - c, axis=1) / R
    keep = np.flatnonzero((rr > R_WINDOW[0]) & (rr < R_WINDOW[1]))
    print(f"radial window {R_WINDOW[0]:g} to {R_WINDOW[1]:g} of radius: "
          f"{len(pts)} -> {len(keep)} points "
          f"(furthest point was at {rr.max():.2f} radii)")
    if len(keep) >= KEEP_FLOOR * len(pts):
        merged = merged.select_by_index(keep)
    else:
        print("  that would cut more than allowed; skipped")

    # Drop detached floaters. The cluster radius is a fraction of the berry,
    # not of mean nearest-neighbour distance, which once shattered a cloud
    # from 99,344 points to 160.
    n1 = len(merged.points)
    labels = np.asarray(merged.cluster_dbscan(eps=R / 40.0, min_points=10))
    if labels.max() >= 0:
        counts = np.bincount(labels[labels >= 0])
        big = np.flatnonzero(counts >= FLOATER_FRACTION * n1)
        keep = np.flatnonzero(np.isin(labels, big))
        print(f"clusters: {len(counts)} found, {len(big)} hold at least "
              f"{FLOATER_FRACTION*100:g}% of points each; "
              f"{n1} -> {len(keep)} points")
        if len(keep) >= KEEP_FLOOR * n1:
            merged = merged.select_by_index(keep)
        else:
            print("  that would cut more than allowed; skipped")

    o3d.io.write_point_cloud(COMBINED, merged)
    mb = round(os.path.getsize(COMBINED) / 1e6, 1)
    print(f"wrote {COMBINED} ({len(merged.points)} points, {mb} MB)")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4), dpi=110)
    for k, (i, j, t) in enumerate([(0, 1, "XY"), (0, 2, "XZ"), (1, 2, "YZ")]):
        for pts, c, l in ((P, (0.90, 0.35, 0.20), "upright"),
                          (Q, (0.20, 0.55, 0.90), "inverted")):
            sm = pts[rng.choice(len(pts), min(25000, len(pts)), replace=False)]
            axes[k].scatter(sm[:, i], sm[:, j], s=0.5, alpha=0.3, c=[c], label=l)
        axes[k].set_aspect("equal")
        axes[k].set_title(t)
        axes[k].legend(markerscale=14)
    fig.suptitle("Combined cloud at downscale 2, before meshing")
    fig.tight_layout()
    p = os.path.join(OUT_DIR, "combined_dense2.png")
    fig.savefig(p)
    print("wrote", p)
    print("DONE")


main()
