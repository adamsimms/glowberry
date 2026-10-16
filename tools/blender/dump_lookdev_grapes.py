"""Dump ~10 grape centres from the scaled provenance GLB.

Used by build_lookdev.py. Does not touch models/provenance/.
"""

import json
import os

import numpy as np
import open3d as o3d

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GLB = os.path.join(ROOT, "models", "provenance", "berry_merged_up_inv_cm.glb")
OUT = os.path.join(ROOT, "sketchpad", "lookdev", "grapes.json")

MIN_SEP_DEG = 34.0
K = 0.74
PACK = 1.18


def fit_centre(V):
    A = np.hstack([2.0 * V, np.ones((len(V), 1))])
    b = np.sum(V ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def bin_radius(u, r, nz=72, nphi=144):
    phi = np.arctan2(u[:, 1], u[:, 0])
    zi = np.clip(((u[:, 2] + 1) / 2 * nz).astype(int), 0, nz - 1)
    pi_ = np.clip(((phi + np.pi) / (2 * np.pi) * nphi).astype(int), 0, nphi - 1)
    cell = zi * nphi + pi_
    order = np.argsort(cell)
    cell, r_s, u_s = cell[order], r[order], u[order]
    edges = np.flatnonzero(np.diff(cell)) + 1
    groups = np.split(np.arange(len(cell)), edges)
    rb = np.array([r_s[g].mean() for g in groups])
    ub = np.array([u_s[g].mean(axis=0) for g in groups])
    ub /= np.maximum(np.linalg.norm(ub, axis=1, keepdims=True), 1e-12)
    return ub, rb


def find_peaks(ub, rb, nhood_deg=14.0):
    cos_n = np.cos(np.radians(nhood_deg))
    dots = ub @ ub.T
    peaks = []
    for i in range(len(ub)):
        near = np.flatnonzero(dots[i] > cos_n)
        if i == near[np.argmax(rb[near])]:
            peaks.append(i)
    return np.asarray(peaks, dtype=int)


def nms_peaks(ub, rb, peak_idx, min_sep_deg):
    order = peak_idx[np.argsort(rb[peak_idx])[::-1]]
    cos_sep = np.cos(np.radians(min_sep_deg))
    keep = []
    for i in order:
        if keep and np.any(ub[keep] @ ub[i] > cos_sep):
            continue
        keep.append(i)
    return np.asarray(keep, dtype=int)


def main():
    mesh = o3d.io.read_triangle_mesh(GLB)
    V = np.asarray(mesh.vertices)
    c, R = fit_centre(V)
    v = V - c
    r = np.linalg.norm(v, axis=1)
    u = v / np.maximum(r[:, None], 1e-12)
    ub, rb = bin_radius(u, r)
    kept = nms_peaks(ub, rb, find_peaks(ub, rb), MIN_SEP_DEG)
    dirs = ub[kept]
    peak_r = rb[kept]
    centres = c + (K * peak_r)[:, None] * dirs
    radii = (1.0 - K) * peak_r * PACK
    widest = float(np.ptp(V, axis=0).max())
    grapes = [
        {"location": centres[i].tolist(), "radius": float(radii[i])}
        for i in range(len(kept))
    ]
    payload = {
        "glb": GLB,
        "centre": c.tolist(),
        "fit_radius": R,
        "widest": widest,
        "k": K,
        "pack": PACK,
        "min_sep_deg": MIN_SEP_DEG,
        "grapes": grapes,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"{len(grapes)} grapes, widest {widest*100:.2f} cm, wrote {OUT}")


if __name__ == "__main__":
    main()
