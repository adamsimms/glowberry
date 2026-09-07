"""Step F9d: decide sideways by refining rivals, not by refining the winner.

Adding a tilt to the search changed the picture. Sweeping two angles gave a
peak 1.02x the best score elsewhere, which is nothing; allowing the berry to
sit tilted gave 1.22x, with tilt +20 and +30 both peaking at 0.366 at the same
spin and within 5 degrees of the same stem direction. Agreement between
neighbouring tilts is what a real solution looks like on a coarse grid, and it
says the berry was tilted about 25 degrees rather than lying flat on its side.

The honest way to settle it is not to grid the winner more finely, which
inflates its score while its rivals stay coarse. It is to take every serious
candidate the coarse sweep offers, refine all of them by the same amount, and
see whether one converges better than the rest. A correct orientation keeps
improving as it is refined; a coincidence does not.

So: sweep coarsely in three angles, take the best candidates that are well
separated from each other, run the same ICP on each, and rank by inlier RMSE
and fitness.

ACCEPTANCE, unchanged from step_f9:
  1. the winner must stand clear of the best rival, now measured after both
     have had the same refinement
  2. inlier RMSE comparable to the 1.30% of radius upright and inverted hit
  3. the overlay must show coincident silhouettes

Env:
    BERRY_D_STEP=6        coarse sweep step in degrees
    BERRY_D_TILT=40       tilt cone half-width
    BERRY_D_CANDIDATES=20 rivals to refine alongside the winner

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python step_f9d_refine.py
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
REPORT = os.path.join(WORK, "reports", "step_f9d_refine.json")

STEP = float(os.environ.get("BERRY_D_STEP", "6"))
TILT = float(os.environ.get("BERRY_D_TILT", "40"))
N_CAND = int(os.environ.get("BERRY_D_CANDIDATES", "20"))
SEPARATION = 30.0        # degrees; candidates closer than this are the same one
SCORE_TOL = 0.02
BASELINE_RMSE = 0.0130
SWEEP_SAMPLES = 4000
ICP_SAMPLES = 25000


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
    axes = [np.asarray(f["axis"], float)
            for f in geom[name]["groups"].values()]
    return np.mean([-a if a[1] < 0 else a for a in axes], axis=0)


def normalise(obj, axis):
    V = (np.asarray(obj.vertices) if hasattr(obj, "vertices")
         else np.asarray(obj.points))
    c, R = fit_sphere(V)
    C = np.eye(4)
    C[:3, 3] = -c
    S = np.eye(4)
    S[:3, :3] /= R
    return axis_frame(axis) @ S @ C, R


def clean(pcd):
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
    print(f"source cleaned: {n0} -> {len(pcd.points)} points")
    return pcd


def candidate_matrix(psi, th, tl):
    return (rot([0, 0, 1], th) @ rot([0, 1, 0], -90.0)
            @ rot([0, 0, 1], psi) @ rot([1, 0, 0], tl))


def angle_between(A, B):
    """Rotation angle taking A to B, in degrees."""
    Rm = A[:3, :3].T @ B[:3, :3]
    return float(np.degrees(np.arccos(np.clip((np.trace(Rm) - 1) / 2, -1, 1))))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(GEOM) as fh:
        geom = json.load(fh)

    mesh = o3d.io.read_triangle_mesh(MESH)
    pre_mesh, R = normalise(mesh, chunk_axis(geom, UPRIGHT))
    mesh.transform(pre_mesh.copy())
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
    print(f"target: merged mesh, {len(mesh.triangles)} faces, "
          f"fitted radius {R:.5f} normalised to 1")

    pcd = clean(o3d.io.read_point_cloud(
        os.path.join(CLOUD_DIR, f"{SIDEWAYS}.ply")))
    pre, R2 = normalise(pcd, chunk_axis(geom, SIDEWAYS))
    pcd.transform(pre.copy())
    src = np.asarray(pcd.points)

    rng = np.random.default_rng(0)
    sample = src[rng.choice(len(src), min(SWEEP_SAMPLES, len(src)),
                            replace=False)]

    angles = np.arange(0, 360, STEP)
    tilts = np.arange(-TILT, TILT + 1e-9, 10.0)
    print(f"\ncoarse sweep: {len(angles)}x{len(angles)}x{len(tilts)} = "
          f"{len(angles)**2*len(tilts)} orientations")

    records = []
    for tl in tilts:
        pre_tilt = rot([1, 0, 0], tl)
        for psi in angles:
            base = rot([0, 1, 0], -90.0) @ rot([0, 0, 1], psi) @ pre_tilt
            rotated = (base[:3, :3] @ sample.T).T
            for th in angles:
                Rz = rot([0, 0, 1], th)[:3, :3]
                q = o3d.core.Tensor(((Rz @ rotated.T).T).astype(np.float32))
                s = float(
                    (scene.compute_distance(q).numpy() < SCORE_TOL).mean())
                records.append((s, psi, th, tl))
        print(f"  tilt {tl:+.0f} done")

    records.sort(key=lambda r: -r[0])
    print(f"\nbest coarse score {records[0][0]:.4f}, "
          f"median {np.median([r[0] for r in records]):.4f}")

    # Keep candidates that are genuinely different orientations, not the same
    # peak sampled twice.
    chosen = []
    for s, psi, th, tl in records:
        M = candidate_matrix(psi, th, tl)
        if all(angle_between(M, c[4]) > SEPARATION for c in chosen):
            chosen.append((s, psi, th, tl, M))
        if len(chosen) >= N_CAND:
            break
    print(f"selected {len(chosen)} well-separated candidates, coarse scores "
          f"{chosen[0][0]:.4f} down to {chosen[-1][0]:.4f}")

    target = mesh.sample_points_uniformly(number_of_points=250000)
    target.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=SCORE_TOL * 3, max_nn=30))
    icp_src = pcd.random_down_sample(
        min(1.0, ICP_SAMPLES / max(len(src), 1)))
    reg = o3d.pipelines.registration

    print(f"\nrefining all {len(chosen)} with the same ICP "
          f"({len(icp_src.points)} points each)...")
    out = []
    for i, (s0, psi, th, tl, M) in enumerate(chosen):
        T = M
        for mult in (4.0, 2.0, 1.0):
            r = reg.registration_icp(
                icp_src, target, SCORE_TOL * mult, T,
                reg.TransformationEstimationPointToPlane(),
                reg.ICPConvergenceCriteria(max_iteration=120))
            T = np.asarray(r.transformation)
        ev = reg.evaluate_registration(icp_src, target, SCORE_TOL, T)
        out.append({
            "coarse": s0, "stem_deg": float(psi), "spin_deg": float(th),
            "tilt_deg": float(tl), "fitness": ev.fitness,
            "rmse": ev.inlier_rmse, "transform": T.tolist(),
        })
        print(f"  {i+1:>2}. coarse {s0:.4f} at stem {psi:>5.0f} spin "
              f"{th:>5.0f} tilt {tl:>+4.0f}  ->  fitness {ev.fitness:.4f}, "
              f"rmse {ev.inlier_rmse*100:.2f}%")

    out.sort(key=lambda r: -r["fitness"])

    # Cluster where the candidates ENDED, not where they started. Separation
    # was enforced on the starting orientations, so several starts can fall
    # into one basin, and comparing the best two results then compares one
    # solution against itself.
    clusters = []
    for r in out:
        T = np.asarray(r["transform"])
        for cl in clusters:
            if angle_between(np.asarray(cl[0]["transform"]), T) < SEPARATION:
                cl.append(r)
                break
        else:
            clusters.append([r])

    print(f"\n=== after equal refinement: {len(clusters)} distinct solutions "
          f"from {len(out)} starts ===")
    for i, cl in enumerate(clusters[:6]):
        b = cl[0]
        print(f"  {i+1}. fitness {b['fitness']:.4f}, rmse "
              f"{b['rmse']*100:.2f}%, reached from {len(cl)} of "
              f"{len(out)} starts")
        if len(cl) > 1:
            starts = ", ".join(
                f"stem {c['stem_deg']:.0f}/spin {c['spin_deg']:.0f}/tilt "
                f"{c['tilt_deg']:+.0f}" for c in cl)
            print(f"      independent starts agreeing: {starts}")

    win = clusters[0][0]
    rival = clusters[1][0] if len(clusters) > 1 else {"fitness": 0.0,
                                                      "rmse": 9.0}
    isolation = win["fitness"] / max(rival["fitness"], 1e-9)
    basin = len(clusters[0])
    print(f"\n  winner: fitness {win['fitness']:.4f}, rmse "
          f"{win['rmse']*100:.2f}% of radius, from stem "
          f"{win['stem_deg']:.0f}, spin {win['spin_deg']:.0f}, tilt "
          f"{win['tilt_deg']:+.0f}")
    print(f"  best genuinely different solution: fitness "
          f"{rival['fitness']:.4f}, rmse {rival['rmse']*100:.2f}%")
    print(f"  the winner is {isolation:.2f}x that, and {basin} separate "
          f"starts converged onto it")

    sharp = isolation > 1.25
    tight = win["rmse"] < 2.0 * BASELINE_RMSE
    verdict = "ACCEPT" if sharp and tight else "REJECT"
    print(f"\n  stands clear of rivals: {sharp} (needs > 1.25x)")
    print(f"  RMSE comparable:        {tight} (needs under "
          f"{2*BASELINE_RMSE*100:.2f}% of radius)")
    print(f"  VERDICT: {verdict}")

    with open(REPORT, "w") as fh:
        json.dump({
            "step_deg": STEP, "tilt_cone": TILT,
            "candidates": out, "isolation": isolation,
            "distinct_solutions": len(clusters),
            "starts_in_winning_basin": basin,
            "winner": win, "best_rival": rival,
            "sharp": bool(sharp), "rmse_ok": bool(tight),
            "verdict": verdict,
            "pre_sideways": pre.tolist(), "pre_mesh": pre_mesh.tolist(),
        }, fh, indent=2)
    print("WROTE", REPORT)
    print("DONE")


main()
