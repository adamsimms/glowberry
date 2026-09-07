"""Step F9c: is the sideways berry a different shape, or just a noisier scan?

This is the question the sweep cannot answer. Sideways refuses to register, but
that has two very different explanations, and they lead to opposite actions:

  noisier scan  -> the shape is the same and the match is recoverable, by
                   rescanning or by matching at a coarser scale
  different shape -> the berry deformed between mounts, in which case no
                   rotation can ever fit and sideways should be abandoned

Telling them apart normally needs the orientation solved first, which is
exactly what fails. The way around it is a rotation-invariant descriptor.
Expanding the surface radius r(theta, phi) in spherical harmonics gives a power
spectrum, one number per degree, and rotating the object redistributes power
within a degree but never between degrees. So two clouds of the same object
must share a spectrum whatever their orientations, and two different shapes
will not.

Low degrees carry gross form: degree 2 is how far from round, degree 3 to 6 is
the drupelet lobing. High degrees carry fine detail, and noise piles up there.
That split is what separates the two explanations:

  same low degrees, higher tail  -> same berry, noisier scan
  different low degrees          -> genuinely different shape

Upright and inverted act as the control. They registered successfully at 1.30%
RMSE, so they are known to be the same shape, and the gap between their spectra
sets how much difference this method reports for two scans that do agree.
Sideways is then judged against that gap rather than against zero.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python step_f9c_shape.py
"""

import json
import os

import numpy as np
import open3d as o3d
from scipy.special import sph_harm_y

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
CLOUD_DIR = os.path.join(WORK, "clouds")
MESH = os.path.join(WORK, "exports", "merged_up_inv_clean.ply")
OUT = os.path.join(WORK, "icp", "shape_spectrum.png")
REPORT = os.path.join(WORK, "reports", "step_f9c_shape.json")

LMAX = 8        # partial coverage cannot constrain much beyond this
RIDGE = 1e-4    # per-cell penalty, scaled by degree squared in spectrum()
SUBJECTS = [
    ("upright", os.path.join(CLOUD_DIR, "upright_A_nomask_highonly.ply")),
    ("inverted", os.path.join(CLOUD_DIR, "inverted_A_nomask_highonly.ply")),
    ("sideways", os.path.join(CLOUD_DIR, "sideways_A_nomask_highonly.ply")),
    ("merged mesh", MESH),
]


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def real_basis(theta, phi, lmax):
    """Real spherical harmonics up to lmax, as columns."""
    cols, index = [], []
    for l in range(lmax + 1):
        for m in range(-l, l + 1):
            y = sph_harm_y(l, abs(m), theta, phi)
            if m == 0:
                v = y.real
            elif m > 0:
                v = np.sqrt(2.0) * (-1) ** m * y.real
            else:
                v = np.sqrt(2.0) * (-1) ** m * y.imag
            cols.append(v)
            index.append(l)
    return np.column_stack(cols), np.asarray(index)


def spectrum(points, lmax=LMAX):
    """Rotation-invariant power per degree of the radius function."""
    c, R = fit_sphere(points)
    v = points - c
    r = np.linalg.norm(v, axis=1)
    u = v / r[:, None]
    r = r / R

    theta = np.arccos(np.clip(u[:, 2], -1, 1))
    phi = np.arctan2(u[:, 1], u[:, 0])

    # Bin onto an equal-area grid before fitting, so a patch that happens to
    # carry more points does not pull the fit toward itself. Coverage differs
    # a lot between these clouds, which would otherwise skew the comparison.
    nz, nphi = 60, 120
    zi = np.clip(((u[:, 2] + 1) / 2 * nz).astype(int), 0, nz - 1)
    pi_ = np.clip(((phi + np.pi) / (2 * np.pi) * nphi).astype(int), 0, nphi - 1)
    cell = zi * nphi + pi_
    order = np.argsort(cell)
    cell, r_s = cell[order], r[order]
    th_s, ph_s = theta[order], phi[order]
    edges = np.flatnonzero(np.diff(cell)) + 1
    groups = np.split(np.arange(len(cell)), edges)

    rb = np.array([r_s[g].mean() for g in groups])
    tb = np.array([th_s[g].mean() for g in groups])
    pb = np.array([ph_s[g].mean() for g in groups])
    filled = len(groups) / (nz * nphi) * 100

    # Ridge, not plain least squares. These clouds cover 68% to 99% of the
    # sphere, and an unregularised fit over a gap swings wildly to fill it:
    # the first run reported 84641% relief for the 68% cloud against 31% for
    # the 99% one, ranked purely by coverage. The penalty rises with degree,
    # since it is the fine detail that a gap cannot constrain.
    B, index = real_basis(tb, pb, lmax)
    lam = RIDGE * len(rb) * (1.0 + index.astype(float) ** 2)
    coef = np.linalg.solve(B.T @ B + np.diag(lam), B.T @ rb)
    resid = rb - B @ coef
    power = np.array([np.sum(coef[index == l] ** 2) for l in range(lmax + 1)])
    return {
        "radius": R, "cells": len(groups), "coverage_pct": filled,
        "power": power, "mean_radius": float(coef[0] * B[0, 0] / max(B[0, 0], 1e-9)),
        "residual_pct": float(np.std(resid) * 100),
        "shape_pct": float(np.sqrt(power[2:].sum()) * 100),
    }


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    results = {}
    for name, path in SUBJECTS:
        if not os.path.exists(path):
            print(f"missing {path}")
            continue
        if path.endswith("_clean.ply"):
            pts = np.asarray(o3d.io.read_triangle_mesh(path).vertices)
        else:
            pts = np.asarray(o3d.io.read_point_cloud(path).points)
        s = spectrum(pts)
        results[name] = s
        print(f"{name:<12} {len(pts):>7} pts, {s['cells']:>5} cells "
              f"({s['coverage_pct']:.0f}% of sphere), "
              f"relief {s['shape_pct']:.2f}% of radius, "
              f"fine detail {s['residual_pct']:.2f}%")

    # Normalise each spectrum by its own degree-2-and-up total, so the
    # comparison is of shape, not of how much overall relief survived a
    # particular scan's smoothing.
    def shape_vec(s):
        p = s["power"][2:]
        return p / max(p.sum(), 1e-12)

    names = [n for n, _ in SUBJECTS if n in results]
    print(f"\n=== distance between shape spectra (lower is more alike) ===")
    ref = "merged mesh"
    dists = {}
    for a in names:
        for b in names:
            if a >= b:
                continue
            d = float(np.abs(shape_vec(results[a]) - shape_vec(results[b])).sum())
            dists[f"{a} vs {b}"] = d
    for k, v in sorted(dists.items(), key=lambda kv: kv[1]):
        print(f"  {k:<28} {v:.4f}")

    def pair(a, b):
        return dists.get(f"{a} vs {b}", dists.get(f"{b} vs {a}"))

    # Two controls. The first is two partial scans of the same berry that did
    # register. The second is upright against a mesh it is literally half of,
    # so it should score near zero; if it does not, the method is measuring
    # coverage rather than shape and no verdict is safe.
    control = pair("upright", "inverted")
    control2 = pair("upright", "merged mesh")
    control3 = pair("inverted", "merged mesh")
    tested = [v for k, v in dists.items() if "sideways" in k and v is not None]
    worst = max(tested) if tested else None
    print(f"\ncontrols, all known to be the same berry:")
    print(f"  upright vs inverted           {control:.4f}  "
          f"(two partial scans that did register)")
    print(f"  upright vs merged mesh        {control2:.4f}  "
          f"(a scan against a mesh built from it)")
    print(f"  inverted vs merged mesh       {control3:.4f}  "
          f"(likewise)")
    ceiling = max(control, control2, control3)
    print(f"sideways against the others:    "
          f"{', '.join(f'{v:.4f}' for v in tested)}")
    print(f"\nThe controls span up to {ceiling:.4f} for scans of one "
          f"unchanged berry, so that is the floor for calling anything "
          f"different.")

    same_shape = worst is not None and worst < 1.5 * ceiling
    print()
    if same_shape:
        print("  VERDICT: the same shape. Sideways sits within the spread "
              "that two agreeing scans already show, so the berry did not "
              "deform and the failure is in the scan, not the object.")
    else:
        print("  VERDICT: a different shape. Sideways departs further than "
              "two agreeing scans do, so the berry itself changed between "
              "mounts and no rotation can register it.")

    fine = {n: results[n]["residual_pct"] for n in names}
    print(f"\nfine detail, where noise collects: "
          f"{', '.join(f'{n} {v:.2f}%' for n, v in fine.items())}")
    if fine.get("sideways", 0) > 1.4 * max(
            fine.get("upright", 0), fine.get("inverted", 0)):
        print("  sideways carries clearly more fine-scale variation than "
              "either scan that worked, which is the signature of a noisier "
              "reconstruction rather than a changed object.")

    with open(REPORT, "w") as fh:
        json.dump({
            "lmax": LMAX,
            "subjects": {k: {kk: (vv.tolist() if hasattr(vv, "tolist") else vv)
                             for kk, vv in v.items()}
                         for k, v in results.items()},
            "spectrum_distances": dists,
            "control_upright_vs_inverted": control,
            "control_upright_vs_mesh": control2,
            "control_inverted_vs_mesh": control3,
            "control_ceiling": ceiling,
            "same_shape": bool(same_shape),
        }, fh, indent=2)
    print("WROTE", REPORT)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), dpi=110)
    deg = np.arange(2, LMAX + 1)
    for n in names:
        axes[0].plot(deg, shape_vec(results[n]), "o-", label=n, alpha=0.85)
    axes[0].set_xlabel("spherical harmonic degree")
    axes[0].set_ylabel("share of relief power")
    axes[0].set_title("Shape spectra. Same object means same curve,\n"
                      "whatever the orientation")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].bar(range(len(names)),
                [results[n]["residual_pct"] for n in names],
                tick_label=names, color="tab:orange", alpha=0.85)
    axes[1].set_ylabel("% of radius")
    axes[1].set_title("Fine-scale variation left after the fit,\n"
                      "where scan noise collects")
    axes[1].grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(OUT)
    print("wrote", OUT)
    print("DONE")


main()
