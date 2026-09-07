"""Step F9: try once more to register sideways, now against the finished mesh.

Sideways failed against a single remount's point cloud. This retry changes the
target rather than the method, because the target is what was weak: the merged
mesh is a complete continuous surface covering 99.3% of the sphere, fused from
two independent reconstructions, where before sideways was matched against 79%
of one noisy cloud with a hole in it.

Method is the same constrained sweep that worked for inverted. The turntable
axis is known in every chunk to within 3 degrees, and sideways had its stem
horizontal in an unknown direction, so two angles remain: which horizontal
direction the stem pointed, and how far the turntable had been turned. Both are
swept exhaustively and shown as a heatmap, because a correct registration
should appear as a sharp isolated peak. That is evidence; a best-of-14400
number is not.

Distance is measured to the mesh surface with a raycasting scene, not to
nearest neighbours in a cloud, so a point is scored against real surface
rather than against whichever sample happened to land nearby.

ACCEPTANCE, fixed before running so the result cannot be talked into passing:

  1. the peak must stand clear of the best score outside its own neighbourhood
  2. ICP inlier RMSE must be comparable to the 1.30% of radius that upright and
     inverted achieved
  3. the overlay must show coincident silhouettes

Failing that, sideways stays out, the model ships at 99.3% coverage, and
step_f9b diagnoses whether the berry deformed in that mount.

Env:
    BERRY_SW_STEP=3         sweep step in degrees
    BERRY_SW_TILT=0         also sweep a tilt cone of this many degrees
    BERRY_SW_SAMPLES=4000   cloud points used per sweep evaluation

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python step_f9_sideways.py
"""

import json
import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
OUT_DIR = os.path.join(WORK, "icp")
GEOM = os.path.join(WORK, "reports", "capture_geometry.json")
MESH = os.path.join(WORK, "exports", "merged_up_inv_clean.ply")
SIDEWAYS = "sideways_A_nomask_highonly"
UPRIGHT = "upright_A_nomask_highonly"
REPORT = os.path.join(OUT_DIR, "sideways_retry.json")

STEP = float(os.environ.get("BERRY_SW_STEP", "3"))
TILT = float(os.environ.get("BERRY_SW_TILT", "0"))
SAMPLES = int(os.environ.get("BERRY_SW_SAMPLES", "4000"))
SCORE_TOL = 0.02          # fraction of radius, as in the run that worked
BASELINE_RMSE = 0.0130    # what upright and inverted achieved


def rot(axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    T = np.eye(4)
    T[:3, :3] = np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)
    return T


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def axis_frame(a):
    """Rotation putting axis a onto +z."""
    a = np.asarray(a, float)
    a = a / np.linalg.norm(a)
    if a[1] < 0:
        a = -a
    v = np.cross(a, [0, 0, 1.0])
    s = np.linalg.norm(v)
    if s < 1e-9:
        return np.eye(4)
    return rot(v / s, np.degrees(np.arctan2(s, float(a @ [0, 0, 1.0])))) 


def chunk_axis(geom, name):
    axes = []
    for f in geom[name]["groups"].values():
        a = np.asarray(f["axis"], float)
        axes.append(-a if a[1] < 0 else a)
    return np.mean(axes, axis=0)


def clean(pcd):
    """Same three passes that fixed the merged cloud.

    The first attempt gave this cloud only statistical outlier removal, and it
    carries 11.7% radial scatter against 8.0% for upright and 8.2% for
    inverted, so its noise exceeds the berry's own relief. A shape match cannot
    work while the shape is mostly noise. Clumped points survive the
    statistical pass, which is what the radial window and the cluster pass are
    for.
    """
    n0 = len(pcd.points)
    trimmed, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    if len(trimmed.points) >= 0.9 * n0:
        pcd = trimmed

    pts = np.asarray(pcd.points)
    c, R = fit_sphere(pts)
    rr = np.linalg.norm(pts - c, axis=1) / R
    keep = np.flatnonzero((rr > 0.55) & (rr < 1.6))
    if len(keep) >= 0.6 * len(pts):
        pcd = pcd.select_by_index(keep)

    n1 = len(pcd.points)
    labels = np.asarray(pcd.cluster_dbscan(eps=R / 40.0, min_points=10))
    if labels.max() >= 0:
        counts = np.bincount(labels[labels >= 0])
        big = np.flatnonzero(counts >= 0.001 * n1)
        keep = np.flatnonzero(np.isin(labels, big))
        if len(keep) >= 0.6 * n1:
            pcd = pcd.select_by_index(keep)

    pts = np.asarray(pcd.points)
    c, R = fit_sphere(pts)
    sd = np.linalg.norm(pts - c, axis=1).std() / R * 100
    print(f"cleaned: {n0} -> {len(pts)} points, radial scatter now "
          f"{sd:.2f}% of radius")
    return pcd


def normalise(points_or_mesh, axis):
    """Centre on the fitted sphere, scale to unit radius, axis onto +z."""
    V = (np.asarray(points_or_mesh.vertices)
         if hasattr(points_or_mesh, "vertices")
         else np.asarray(points_or_mesh.points))
    c, R = fit_sphere(V)
    C = np.eye(4)
    C[:3, 3] = -c
    S = np.eye(4)
    S[:3, :3] /= R
    return axis_frame(axis) @ S @ C, R


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(GEOM) as fh:
        geom = json.load(fh)

    mesh = o3d.io.read_triangle_mesh(MESH)
    pre_mesh, R = normalise(mesh, chunk_axis(geom, UPRIGHT))
    mesh.transform(pre_mesh.copy())
    print(f"target mesh: {len(mesh.triangles)} faces, fitted radius {R:.5f} "
          f"normalised to 1.0")

    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))

    pcd = o3d.io.read_point_cloud(os.path.join(CLOUD_DIR, f"{SIDEWAYS}.ply"))
    pcd = clean(pcd)
    pre, R2 = normalise(pcd, chunk_axis(geom, SIDEWAYS))
    pcd.transform(pre.copy())
    src = np.asarray(pcd.points)
    print(f"source cloud: {len(src)} points, fitted radius {R2:.5f} "
          f"normalised to 1.0")
    print(f"radius ratio sideways/merged: {R2/R:.4f}")

    rng = np.random.default_rng(0)
    sample = src[rng.choice(len(src), min(SAMPLES, len(src)), replace=False)]

    tip = rot([0, 1, 0], -90.0)
    tilts = ([0.0] if TILT <= 0
             else list(np.arange(-TILT, TILT + 1e-9, 10.0)))
    angles = np.arange(0, 360, STEP)
    print(f"\nsweeping {len(angles)}x{len(angles)} angles"
          f"{f' over {len(tilts)} tilts' if len(tilts) > 1 else ''}, "
          f"{len(sample)} points each")

    best = None
    grid = np.zeros((len(angles), len(angles)))
    for tl in tilts:
        pre_tilt = rot([1, 0, 0], tl)
        g = np.zeros((len(angles), len(angles)))
        for i, psi in enumerate(angles):
            base = tip @ rot([0, 0, 1], psi) @ pre_tilt
            rotated = (base[:3, :3] @ sample.T).T
            for j, th in enumerate(angles):
                Rz = rot([0, 0, 1], th)[:3, :3]
                q = o3d.core.Tensor(((Rz @ rotated.T).T).astype(np.float32))
                g[i, j] = float(
                    (scene.compute_distance(q).numpy() < SCORE_TOL).mean())
        i, j = np.unravel_index(np.argmax(g), g.shape)
        if best is None or g[i, j] > best[0]:
            best = (g[i, j], tl, angles[i], angles[j])
            grid = g
        if len(tilts) > 1:
            print(f"  tilt {tl:+.0f} deg: peak {g[i,j]:.4f} at stem "
                  f"{angles[i]:.0f}, spin {angles[j]:.0f}")

    peak, tl, psi, th = best
    med = float(np.median(grid))

    # Compare the peak against the best score well away from it, so its own
    # shoulder does not flatter it.
    ii, jj = np.meshgrid(angles, angles, indexing="ij")
    far = (np.abs(((ii - psi + 180) % 360) - 180) > 20) | \
          (np.abs(((jj - th + 180) % 360) - 180) > 20)
    runner = float(grid[far].max())
    print(f"\npeak {peak:.4f} at stem {psi:.0f} deg, spin {th:.0f} deg, "
          f"tilt {tl:+.0f}")
    print(f"  median {med:.4f}, best away from the peak {runner:.4f}")
    print(f"  peak stands {peak/max(runner,1e-9):.2f}x above that and "
          f"{peak/max(med,1e-9):.2f}x above median")

    # Refine against points sampled off the mesh, since ICP needs a cloud.
    target = mesh.sample_points_uniformly(number_of_points=200000)
    target.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=SCORE_TOL * 3, max_nn=30))
    reg = o3d.pipelines.registration
    T = rot([0, 0, 1], th) @ tip @ rot([0, 0, 1], psi) @ rot([1, 0, 0], tl)
    for mult in (4.0, 2.0, 1.0):
        r = reg.registration_icp(
            pcd, target, SCORE_TOL * mult, T,
            reg.TransformationEstimationPointToPlane(),
            reg.ICPConvergenceCriteria(max_iteration=200))
        T = np.asarray(r.transformation)
    ev = reg.evaluate_registration(pcd, target, SCORE_TOL, T)
    print(f"  after ICP: fitness {ev.fitness:.4f}, inlier rmse "
          f"{ev.inlier_rmse*100:.2f}% of radius "
          f"(upright/inverted achieved {BASELINE_RMSE*100:.2f}%)")

    sharp = peak > 1.25 * runner
    tight = ev.inlier_rmse < 2.0 * BASELINE_RMSE
    verdict = "ACCEPT" if sharp and tight else "REJECT"
    print(f"\n  sharp isolated peak: {sharp} (needs peak > 1.25x the best "
          f"elsewhere)")
    print(f"  RMSE comparable:     {tight} (needs under "
          f"{2*BASELINE_RMSE*100:.2f}% of radius)")
    print(f"  VERDICT: {verdict}")
    if verdict == "REJECT":
        print("  sideways stays out. The model ships at 99.3% coverage from "
              "upright and inverted. Run step_f9b to diagnose why.")

    with open(REPORT, "w") as fh:
        json.dump({
            "target": MESH, "source": SIDEWAYS, "step_deg": STEP,
            "tilt_deg": TILT, "samples": len(sample),
            "peak": peak, "peak_stem_deg": float(psi),
            "peak_spin_deg": float(th), "peak_tilt_deg": float(tl),
            "median": med, "best_away_from_peak": runner,
            "icp_fitness": ev.fitness, "icp_inlier_rmse": ev.inlier_rmse,
            "sharp": bool(sharp), "rmse_ok": bool(tight),
            "verdict": verdict, "transform_normalised": T.tolist(),
            "pre_sideways": pre.tolist(), "pre_mesh": pre_mesh.tolist(),
        }, fh, indent=2)
    print("WROTE", REPORT)

    fig, ax = plt.subplots(figsize=(7.4, 6.2), dpi=110)
    im = ax.imshow(grid, origin="lower", cmap="magma",
                   extent=[angles[0], angles[-1], angles[0], angles[-1]])
    ax.plot(th, psi, "co", ms=10, mfc="none", mew=2)
    ax.set_xlabel("spin about the berry axis (deg)")
    ax.set_ylabel("which horizontal direction the stem pointed (deg)")
    ax.set_title(f"Sideways onto the merged mesh: {verdict}\n"
                 f"peak {peak:.3f}, elsewhere {runner:.3f}, median {med:.3f}")
    plt.colorbar(im, ax=ax,
                 label=f"fraction within {SCORE_TOL*100:.0f}% of radius")
    fig.tight_layout()
    p = os.path.join(OUT_DIR, "sideways_retry.png")
    fig.savefig(p)
    print("wrote", p)
    print("DONE")


main()
