"""Register the remounts using the turntable geometry to constrain rotation.

Unconstrained search failed: thousands of seeded ICP runs over SO(3) never
scored better than about twice chance, because a lumpy sphere matches a lumpy
sphere under many rotations once the tolerance approaches the relief.

The capture geometry removes almost all of that freedom. Every remount is a
turntable sequence, and the fitted camera rings show the turntable axis is the
same direction in all three chunks to within 3 degrees. The berry sat on a pin
along that axis, stem up for upright and stem down for inverted, so those two
differ by a 180 degree flip plus however far the turntable had been turned.
That leaves one unknown angle, not three.

One angle can be swept exhaustively and plotted. That matters more than the
saving in compute: a correct registration shows up as a sharp isolated peak in
the curve, which is evidence, whereas a best-of-thousands number from a blind
search has to be taken on faith. Sideways had its stem horizontal in an unknown
direction, so it needs two angles, swept as a grid and shown as a heatmap.

Outputs to metashape/icp/:
    constrained_upright_inverted.png   score against flip angle
    constrained_sideways.png           score over the two sideways angles
    constrained_transforms.json        the resulting transforms and peak stats

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python icp_constrained.py
"""

import json
import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
OUT_DIR = os.path.join(WORK, "icp")
GEOM = os.path.join(WORK, "reports", "capture_geometry.json")

UPRIGHT = "upright_A_nomask_highonly"
INVERTED = "inverted_A_nomask_highonly"
SIDEWAYS = "sideways_A_nomask_highonly"
NAMES = [UPRIGHT, INVERTED, SIDEWAYS]

# Scoring tolerance as a fraction of berry radius. Tight enough that the
# drupelet relief has to line up, loose enough to tolerate the 0.85 percent
# reconstruction repeatability measured between independent camera rings.
SCORE_TOL = 0.02
STEP_DEG = 1.0
GRID_STEP_DEG = 3.0


def rot(axis, deg):
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)
    T = np.eye(4)
    T[:3, :3] = R
    return T


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def axis_frame(axis):
    """Rotation taking the turntable axis to +z, so spin becomes rotation in z."""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    if a[1] < 0:          # consistent sign across chunks; all are near +y
        a = -a
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(a, z)
    s = np.linalg.norm(v)
    if s < 1e-9:
        return np.eye(4)
    return rot(v / s, np.degrees(np.arctan2(s, float(a @ z))))


def load(name, geom):
    """Load a cloud into its turntable frame: axis on +z, berry at unit radius."""
    pcd = o3d.io.read_point_cloud(os.path.join(CLOUD_DIR, f"{name}.ply"))
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

    rings = geom[name]["groups"]
    axes = []
    for f in rings.values():
        a = np.asarray(f["axis"], float)
        axes.append(-a if a[1] < 0 else a)
    axis = np.mean(axes, axis=0)

    pts = np.asarray(pcd.points)
    centre, radius = fit_sphere(pts)
    C = np.eye(4)
    C[:3, 3] = -centre
    S = np.eye(4)
    S[:3, :3] /= radius
    pre = axis_frame(axis) @ S @ C
    pcd.transform(pre.copy())
    print(f"{name.split('_')[0]:9} {len(pts):>7} points, fitted radius "
          f"{radius:.5f}, axis {np.round(axis, 4)}")
    return pcd, pre, radius


def score(src_pts, tree, tol):
    """Fraction of source points within tol of the target surface."""
    hit = 0
    for p in src_pts:
        k, _i, d2 = tree.search_hybrid_vector_3d(p, tol, 1)
        hit += 1 if k else 0
    return hit / len(src_pts)


def refine(src, dst, T0, tol):
    reg = o3d.pipelines.registration
    T = T0
    for mult in (4.0, 2.0, 1.0):
        r = reg.registration_icp(
            src, dst, tol * mult, T,
            reg.TransformationEstimationPointToPoint(False),
            reg.ICPConvergenceCriteria(max_iteration=200),
        )
        T = np.asarray(r.transformation)
    ev = reg.evaluate_registration(src, dst, tol, T)
    return T, ev.fitness, ev.inlier_rmse


def peak_report(label, angles, scores):
    """A registration is only believable if its peak stands clear of the rest."""
    scores = np.asarray(scores)
    best = int(np.argmax(scores))
    med = float(np.median(scores))
    # Ignore everything within 20 degrees of the peak when measuring the runner
    # up, so the peak is not compared against its own shoulder.
    mask = np.abs(((angles - angles[best] + 180) % 360) - 180) > 20
    runner = float(scores[mask].max()) if mask.any() else med
    print(
        f"  {label}: peak {scores[best]:.4f} at {angles[best]:.1f} deg, "
        f"next unrelated peak {runner:.4f}, median {med:.4f}"
    )
    print(
        f"  peak stands {scores[best]/max(runner,1e-9):.2f}x above the next "
        f"and {scores[best]/max(med,1e-9):.2f}x above median"
    )
    return best, float(scores[best]), runner, med


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(GEOM) as fh:
        geom = json.load(fh)
    print("open3d", o3d.__version__)

    clouds, pre, radii = {}, {}, {}
    for n in NAMES:
        clouds[n], pre[n], radii[n] = load(n, geom)

    # Thin copies for sweeping, full clouds for the final refinement.
    thin = {n: clouds[n].voxel_down_sample(SCORE_TOL / 2) for n in NAMES}
    for n in NAMES:
        print(f"{n.split('_')[0]:9} {len(thin[n].points)} points for sweeping")
    trees = {n: o3d.geometry.KDTreeFlann(thin[n]) for n in NAMES}
    report = {"score_tolerance_fraction_of_radius": SCORE_TOL, "pairs": {}}

    # --- upright against inverted: one angle -------------------------------
    print(f"\n=== upright vs inverted: sweeping the flip angle, "
          f"{int(360/STEP_DEG)} steps ===")
    src = np.asarray(thin[INVERTED].points)
    flip = rot([1, 0, 0], 180.0)
    angles = np.arange(0, 360, STEP_DEG)
    scores = []
    for a in angles:
        T = rot([0, 0, 1], a) @ flip
        scores.append(score((T[:3, :3] @ src.T).T + T[:3, 3],
                            trees[UPRIGHT], SCORE_TOL))
    best, peak, runner, med = peak_report("upright vs inverted", angles, scores)

    T0 = rot([0, 0, 1], angles[best]) @ flip
    T_inv, fit, rmse = refine(clouds[INVERTED], clouds[UPRIGHT], T0, SCORE_TOL)
    print(f"  after ICP: fitness {fit:.4f}, inlier rmse "
          f"{rmse*100:.3f}% of radius")
    report["pairs"]["inverted_to_upright"] = {
        "sweep_peak_angle_deg": float(angles[best]),
        "sweep_peak_score": peak, "next_unrelated_peak": runner,
        "sweep_median": med, "icp_fitness": fit, "icp_inlier_rmse": rmse,
        "transform": T_inv.tolist(),
    }

    fig, ax = plt.subplots(figsize=(9, 4), dpi=110)
    ax.plot(angles, scores, lw=1.2)
    ax.axvline(angles[best], color="crimson", ls="--", lw=1,
               label=f"peak {angles[best]:.0f} deg")
    ax.axhline(med, color="grey", ls=":", lw=1, label="median")
    ax.set_xlabel("turntable angle applied to inverted, after a 180 deg flip")
    ax.set_ylabel(f"fraction within {SCORE_TOL*100:.0f}% of radius")
    ax.set_title("Inverted onto upright: one unknown angle")
    ax.legend()
    fig.tight_layout()
    p = os.path.join(OUT_DIR, "constrained_upright_inverted.png")
    fig.savefig(p)
    plt.close(fig)
    print("  wrote", p)

    # --- sideways against upright: two angles ------------------------------
    n = int(360 / GRID_STEP_DEG)
    print(f"\n=== sideways vs upright: sweeping two angles, {n}x{n} grid ===")
    src = np.asarray(thin[SIDEWAYS].points)
    tip = rot([0, 1, 0], -90.0)
    psis = np.arange(0, 360, GRID_STEP_DEG)
    thetas = np.arange(0, 360, GRID_STEP_DEG)
    grid = np.zeros((len(psis), len(thetas)))
    for i, psi in enumerate(psis):
        pre_r = tip @ rot([0, 0, 1], psi)
        rotated = (pre_r[:3, :3] @ src.T).T
        for j, th in enumerate(thetas):
            R = rot([0, 0, 1], th)[:3, :3]
            grid[i, j] = score((R @ rotated.T).T, trees[UPRIGHT], SCORE_TOL)
    i, j = np.unravel_index(np.argmax(grid), grid.shape)
    med = float(np.median(grid))
    print(f"  peak {grid[i, j]:.4f} at stem direction {psis[i]:.0f} deg, "
          f"spin {thetas[j]:.0f} deg; median {med:.4f} "
          f"({grid[i, j]/max(med,1e-9):.2f}x)")

    T0 = rot([0, 0, 1], thetas[j]) @ tip @ rot([0, 0, 1], psis[i])
    T_side, fit_s, rmse_s = refine(
        clouds[SIDEWAYS], clouds[UPRIGHT], T0, SCORE_TOL)
    print(f"  after ICP: fitness {fit_s:.4f}, inlier rmse "
          f"{rmse_s*100:.3f}% of radius")
    report["pairs"]["sideways_to_upright"] = {
        "sweep_peak_stem_deg": float(psis[i]),
        "sweep_peak_spin_deg": float(thetas[j]),
        "sweep_peak_score": float(grid[i, j]), "sweep_median": med,
        "icp_fitness": fit_s, "icp_inlier_rmse": rmse_s,
        "transform": T_side.tolist(),
    }

    fig, ax = plt.subplots(figsize=(7, 6), dpi=110)
    im = ax.imshow(grid, origin="lower", cmap="magma",
                   extent=[thetas[0], thetas[-1], psis[0], psis[-1]])
    ax.plot(thetas[j], psis[i], "co", ms=9, mfc="none", mew=2)
    ax.set_xlabel("spin about the berry axis (deg)")
    ax.set_ylabel("which horizontal direction the stem pointed (deg)")
    ax.set_title("Sideways onto upright: two unknown angles")
    plt.colorbar(im, ax=ax, label=f"fraction within {SCORE_TOL*100:.0f}% of radius")
    fig.tight_layout()
    p = os.path.join(OUT_DIR, "constrained_sideways.png")
    fig.savefig(p)
    plt.close(fig)
    print("  wrote", p)

    for k, v in report["pairs"].items():
        v["transform_ply_to_upright_frame"] = (
            np.asarray(v["transform"]) @ pre[
                INVERTED if "inverted" in k else SIDEWAYS]
        ).tolist()
    report["upright_pre_transform"] = pre[UPRIGHT].tolist()
    report["fitted_radii"] = {n: radii[n] for n in NAMES}
    with open(os.path.join(OUT_DIR, "constrained_transforms.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    print("  wrote", os.path.join(OUT_DIR, "constrained_transforms.json"))
    print("DONE")


main()
