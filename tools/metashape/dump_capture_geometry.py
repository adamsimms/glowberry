"""Export each remount's turntable geometry, to constrain the rotation search.

Searching all of SO(3) does not work on this berry. Thousands of seeded ICP
runs never beat about twice chance, because a lumpy sphere fits a lumpy sphere
under many rotations once the tolerance is anywhere near the relief.

The capture itself removes most of that freedom. Each remount is a turntable
sequence, so the camera positions in a ring lie on a circle whose axis is the
turntable axis, and the berry was mounted on a pin along that axis: stem up for
upright, stem down for inverted, on its side for sideways. So the berry's own
axis is known in each chunk up to mount sloppiness, and the only real unknown
is how far the berry was turned about that axis.

That reduces upright against inverted to one angle, and either of them against
sideways to two. One and two angle searches can be swept exhaustively and
plotted, and a real registration then shows up as a clear peak rather than a
best-of-many number that has to be taken on trust.

Writes reports/capture_geometry.json with, per chunk and per camera group, the
fitted ring centre, ring axis, ring radius and the residual of the circle fit,
plus every camera centre so the fit can be redone or checked outside Metashape.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r dump_capture_geometry.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import berry_common as bc  # noqa: E402

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

bc.add_user_packages()

import numpy as np  # noqa: E402
import Metashape  # noqa: E402

REPORT = os.path.join(bc.WORK, "reports", "capture_geometry.json")
WANTED_SUFFIX = "_A_nomask_highonly"


def fit_ring(P):
    """Fit a plane and a circle to camera centres on a turntable ring.

    The plane normal is the turntable axis. Its sign is left as the smaller
    eigenvector direction; callers resolve the sign, since a ring alone cannot
    say which way is up.
    """
    c = P.mean(axis=0)
    u, s, vt = np.linalg.svd(P - c)
    axis = vt[2]
    # In-plane coordinates, to fit the circle centre properly rather than
    # assuming the centroid is on the axis.
    e1, e2 = vt[0], vt[1]
    x = (P - c) @ e1
    y = (P - c) @ e2
    A = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0], sol[1]
    radius = float(np.sqrt(max(sol[2] + cx * cx + cy * cy, 1e-12)))
    centre = c + cx * e1 + cy * e2
    resid = np.abs(np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - radius)
    return {
        "centre": centre.tolist(),
        "axis": axis.tolist(),
        "radius": radius,
        "plane_thickness": float(s[2] / np.sqrt(len(P))),
        "circle_residual_mean": float(resid.mean()),
        "circle_residual_max": float(resid.max()),
    }


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=True, ignore_lock=True)

    out = {}
    for chunk in doc.chunks:
        if not chunk.label.endswith(WANTED_SUFFIX):
            continue
        T = chunk.transform.matrix
        entry = {"label": chunk.label, "groups": {}, "cameras": {}}
        by_group = {}
        for cam in chunk.cameras:
            if not cam.transform or not cam.enabled:
                continue
            centre = T.mulp(cam.center)
            g = cam.group.label if cam.group else "none"
            by_group.setdefault(g, []).append([centre.x, centre.y, centre.z])
            entry["cameras"][cam.label] = {
                "group": g,
                "centre": [centre.x, centre.y, centre.z],
            }

        print(f"\n=== {chunk.label} ===")
        for g, pts in sorted(by_group.items()):
            P = np.asarray(pts)
            if len(P) < 5:
                print(f"  ring {g}: only {len(P)} cameras, skipped")
                continue
            fit = fit_ring(P)
            fit["cameras"] = len(P)
            entry["groups"][g] = fit
            print(
                f"  ring {g}: {len(P)} cameras, radius {fit['radius']:.4f}, "
                f"axis {np.round(fit['axis'], 4)}"
            )
            print(
                f"           circle residual mean {fit['circle_residual_mean']:.5f} "
                f"({fit['circle_residual_mean']/fit['radius']*100:.2f}% of radius), "
                f"plane thickness {fit['plane_thickness']:.5f}"
            )

        # The two rings of one remount share a turntable, so their axes must
        # agree. Disagreement means the fit, or the capture, is not what is
        # assumed here, and everything downstream would inherit that.
        axes = [np.asarray(f["axis"]) for f in entry["groups"].values()]
        if len(axes) == 2:
            d = abs(float(np.dot(axes[0], axes[1])))
            ang = np.degrees(np.arccos(min(d, 1.0)))
            entry["ring_axis_disagreement_deg"] = ang
            verdict = "consistent" if ang < 3 else "SUSPECT"
            print(f"  the two ring axes differ by {ang:.2f} deg -> {verdict}")
        out[chunk.label] = entry

    with open(REPORT, "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nWROTE", REPORT)
    print("DONE")


main()
