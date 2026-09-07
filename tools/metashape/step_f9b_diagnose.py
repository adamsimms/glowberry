"""Step F9b: find out why sideways will not register.

What the numbers rule out. Its camera solution is not the weak one: sideways
aligned 76 cameras at 0.2370 px against upright's 75 at 0.2466, so the poses
are as good as the two that worked. Cleaning is not the answer either, since
the three cleaning passes that rescued the merged cloud moved its radial
scatter only from 11.72% to 11.37%, meaning the roughness is spread across the
whole surface rather than sitting in floaters.

What the numbers point at. Its cloud covers 89.8% of the sphere from a single
turntable pass, where upright managed 69.1% and inverted 81.8%. One mount
cannot see 90% of a sphere, because whatever holds the berry blocks the side it
touches. So the cloud almost certainly contains something that is not berry,
and if that something rotated with the berry it was reconstructed as part of
the object, which would defeat any shape match against a berry-only mesh.

This renders the three clouds side by side to see it, and measures how much of
each cloud sits outside a berry-sized shell.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python step_f9b_diagnose.py
"""

import json
import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
OUT = os.path.join(WORK, "icp", "sideways_diagnose.png")
REPORT = os.path.join(WORK, "reports", "step_f9b_diagnose.json")
GEOM = os.path.join(WORK, "reports", "capture_geometry.json")

CHUNKS = ["upright_A_nomask_highonly", "inverted_A_nomask_highonly",
          "sideways_A_nomask_highonly"]


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def rot(axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)


def axis_frame(a):
    a = np.asarray(a, float)
    a = a / np.linalg.norm(a)
    if a[1] < 0:
        a = -a
    v = np.cross(a, [0, 0, 1.0])
    s = np.linalg.norm(v)
    if s < 1e-9:
        return np.eye(3)
    return rot(v / s, np.degrees(np.arctan2(s, float(a @ [0, 0, 1.0])))) 


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(GEOM) as fh:
        geom = json.load(fh)

    fig, axes = plt.subplots(3, 3, figsize=(13.5, 13.5), dpi=105)
    out = {}

    for row, name in enumerate(CHUNKS):
        pcd = o3d.io.read_point_cloud(os.path.join(CLOUD_DIR, f"{name}.ply"))
        pts = np.asarray(pcd.points)
        col = (np.asarray(pcd.colors) if pcd.has_colors()
               else np.tile([0.8, 0.4, 0.15], (len(pts), 1)))

        axes_list = [np.asarray(f["axis"], float)
                     for f in geom[name]["groups"].values()]
        axes_list = [-a if a[1] < 0 else a for a in axes_list]
        Rf = axis_frame(np.mean(axes_list, axis=0))

        c, R = fit_sphere(pts)
        P = ((pts - c) @ Rf.T) / R          # turntable frame, unit radius
        r = np.linalg.norm(P, axis=1)

        # A berry is one lump. Points far outside a berry-sized shell are
        # something else: mount, background, or stray geometry.
        far = float((r > 1.35).mean() * 100)
        near = float((r < 0.6).mean() * 100)
        out[name] = {
            "points": len(pts), "fitted_radius": R,
            "radial_sd_pct": float(r.std() * 100),
            "beyond_1.35_radii_pct": far, "inside_0.6_radii_pct": near,
            "extent_in_radii": (P.max(axis=0) - P.min(axis=0)).tolist(),
        }
        print(f"{name}")
        print(f"  {len(pts)} points, radial scatter {r.std()*100:.2f}% "
              f"of radius")
        print(f"  {far:.2f}% of points sit beyond 1.35 radii, "
              f"{near:.2f}% inside 0.6 radii")
        print(f"  extent in radii: "
              f"{np.round(P.max(axis=0)-P.min(axis=0), 2).tolist()}")

        for cid, (a, b, lbl) in enumerate(
                [(0, 2, "x-z, turntable axis is up"),
                 (1, 2, "y-z"), (0, 1, "x-y, looking down the axis")]):
            ax = axes[row][cid]
            order = np.argsort(P[:, 3 - a - b] if a + b == 2 else P[:, 2])
            ax.scatter(P[order, a], P[order, b], s=0.35,
                       c=np.clip(col[order], 0, 1), linewidths=0)
            circ = plt.Circle((0, 0), 1.0, fill=False, color="k", lw=0.8,
                              ls="--", alpha=0.6)
            ax.add_patch(circ)
            ax.set_xlim(-2.2, 2.2)
            ax.set_ylim(-2.2, 2.2)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            if row == 0:
                ax.set_title(lbl, fontsize=10)
            if cid == 0:
                ax.set_ylabel(name.replace("_A_nomask_highonly", ""),
                              fontsize=11)

    fig.suptitle("The three clouds in their own turntable frames, scaled to "
                 "a fitted radius of 1.\nDashed circle is that radius: a "
                 "berry-only cloud should hug it.", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT)
    print("\nwrote", OUT)

    with open(REPORT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("WROTE", REPORT)
    print("DONE")


main()
