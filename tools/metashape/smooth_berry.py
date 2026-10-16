"""Look-dev: packed spheres on the scanned berry.

Working look is 12 lumps. k is join depth. Spheres contain the berry centre,
so every ray hits, the fruit stays one piece, and a join is the crease where
two far-hits meet. Vertices stay those of the scan; only radius changes.

Does not touch models/provenance/. Overwrites models/smooth/.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python \\
        tools/metashape/smooth_berry.py
"""

import os
import sys

import numpy as np
import open3d as o3d

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_PLY = os.path.join(
    os.path.expanduser("~/Desktop/BERRY/metashape/exports"),
    "merged_up_inv_clean.ply",
)
OUT_DIR = os.path.join(ROOT, "models", "smooth")

# Same 12 lumps as the working look. k is join depth (higher = deeper).
# 0.48 is as deep as this method goes while the berry centre stays inside.
STRENGTHS = {
    "mild":   {"min_sep_deg": 26.0, "k": 0.42},
    "medium": {"min_sep_deg": 26.0, "k": 0.45},
    "strong": {"min_sep_deg": 26.0, "k": 0.48},
}


def fit_centre(V):
    A = np.hstack([2.0 * V, np.ones((len(V), 1))])
    b = np.sum(V ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def bin_radius(u, r, nz=72, nphi=144):
    """Equal-area cells so a dense patch does not dominate peak finding."""
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
    """Local maxima of binned radius, one per neighbourhood on the sphere."""
    cos_n = np.cos(np.radians(nhood_deg))
    dots = ub @ ub.T
    peaks = []
    for i in range(len(ub)):
        near = np.flatnonzero(dots[i] > cos_n)
        if i == near[np.argmax(rb[near])]:
            peaks.append(i)
    return np.asarray(peaks, dtype=int)


def nms_peaks(ub, rb, peak_idx, min_sep_deg):
    """Keep the highest lumps that are at least min_sep_deg apart."""
    order = peak_idx[np.argsort(rb[peak_idx])[::-1]]
    cos_sep = np.cos(np.radians(min_sep_deg))
    keep = []
    for i in order:
        if keep:
            if np.any(ub[keep] @ ub[i] > cos_sep):
                continue
        keep.append(i)
    return np.asarray(keep, dtype=int)


def tweak_lumps(dirs, peak_r):
    """Keep the 12 lumps. Move two that read wrong in the working look.

    2 is the bottom-right hang: lift it to the other basal lumps.
    5 is the left-side wing: pull it into the pack and slightly in.
    """
    dirs = np.array(dirs, dtype=float, copy=True)
    peak_r = np.array(peak_r, dtype=float, copy=True)

    az = np.arctan2(dirs[2, 1], dirs[2, 0])
    el = np.radians(-30.0)
    dirs[2] = (
        np.cos(el) * np.cos(az),
        np.cos(el) * np.sin(az),
        np.sin(el),
    )
    peak_r[2] *= 0.94

    others = np.delete(np.arange(len(dirs)), 5)
    nn = others[np.argsort(dirs[others] @ dirs[5])[-2:]]
    mean = dirs[nn].mean(axis=0)
    mean /= np.linalg.norm(mean)
    d = 0.55 * dirs[5] + 0.45 * mean
    dirs[5] = d / np.linalg.norm(d)
    peak_r[5] *= 0.84
    return dirs, peak_r


def place_spheres(c, dirs, peak_r, k):
    """Sphere through each peak, centre on the peak ray, berry centre inside."""
    k = float(np.clip(k, 0.02, 0.48))
    centres = c + (k * peak_r)[:, None] * dirs
    radii = (1.0 - k) * peak_r
    return centres, radii


def radial_union(c, u, centres, radii):
    """Far intersection of each ray with the union of spheres.

    Every sphere contains c, so every ray hits every sphere. The outer
    envelope is max t_far. That is a crease where two spheres meet, a round
    cap where one wins.
    """
    offset = c[None, :] - centres
    B = 2.0 * u @ offset.T
    C = np.sum(offset ** 2, axis=1) - radii ** 2
    disc = np.maximum(B ** 2 - 4.0 * C[None, :], 0.0)
    t_far = 0.5 * (-B + np.sqrt(disc))
    return t_far.max(axis=1)


def colour_by_radius(V):
    c = V.mean(axis=0)
    r = np.linalg.norm(V - c, axis=1)
    lo, hi = np.percentile(r, 2), np.percentile(r, 98)
    t = np.clip((r - lo) / max(hi - lo, 1e-9), 0, 1)
    dark = np.array([0.35, 0.08, 0.04])
    light = np.array([0.95, 0.55, 0.18])
    return (1 - t)[:, None] * dark + t[:, None] * light


def apply(mesh, c, u, r, ub, rb, peak_idx, spec):
    kept = nms_peaks(ub, rb, peak_idx, spec["min_sep_deg"])
    dirs, peak_r = tweak_lumps(ub[kept], rb[kept])
    centres, radii = place_spheres(c, dirs, peak_r, spec["k"])
    r_hat = radial_union(c, u, centres, radii)
    r_hat = np.maximum(r_hat, 0.35 * r.mean())
    V2 = c + u * r_hat[:, None]
    out = o3d.geometry.TriangleMesh()
    out.vertices = o3d.utility.Vector3dVector(V2)
    out.triangles = mesh.triangles
    out.vertex_colors = o3d.utility.Vector3dVector(colour_by_radius(V2))
    out.compute_vertex_normals()
    return out, len(kept)


def render_strip(meshes, labels, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    fig, axes = plt.subplots(2, len(meshes), figsize=(4.2 * len(meshes), 8.2),
                             dpi=110)
    if len(meshes) == 1:
        axes = np.array(axes).reshape(2, 1)

    def view_basis(az, el):
        a, e = np.radians(az), np.radians(el)
        view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a),
                         np.sin(e)])
        x = np.cross([0, 0, 1.0], view)
        x /= max(np.linalg.norm(x), 1e-9)
        y = np.cross(view, x)
        return view, x, y

    for col, (mesh, label) in enumerate(zip(meshes, labels)):
        V = np.asarray(mesh.vertices)
        F = np.asarray(mesh.triangles)
        mesh.compute_triangle_normals()
        N = np.asarray(mesh.triangle_normals)
        C = np.asarray(mesh.vertex_colors)
        face_col = C[F].mean(axis=1)
        centre = V.mean(axis=0)
        tri_c = V[F].mean(axis=1)
        for row, (az, el) in enumerate(((0, 8), (0, -55))):
            view, x, y = view_basis(az, el)
            facing = N @ view > 0
            idx = np.flatnonzero(facing)
            if len(idx) == 0:
                continue
            idx = idx[np.argsort((tri_c[idx] - centre) @ view)]
            lit = np.clip(N[idx] @ view, 0.08, 1.0) ** 0.75
            cols = np.clip(face_col[idx] * lit[:, None] * 1.12, 0, 1)
            pts = V[F[idx]] - centre
            polys = np.stack([pts @ x, pts @ y], axis=-1)
            ax = axes[row][col]
            ax.add_collection(PolyCollection(
                polys, facecolors=cols, edgecolors="none",
                antialiaseds=False))
            lim = np.abs(polys).max() * 1.06
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_aspect("equal")
            ax.axis("off")
            if row == 0:
                ax.set_title(label, fontsize=11)
    fig.suptitle(
        "Packed spheres, hard joins. Front (top), underside (bottom).")
    fig.tight_layout()
    fig.savefig(path)
    print("wrote", path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(SRC_PLY):
        sys.exit(f"no source mesh at {SRC_PLY}")
    src = o3d.io.read_triangle_mesh(SRC_PLY)
    V = np.asarray(src.vertices)
    c, R = fit_centre(V)
    v = V - c
    r = np.linalg.norm(v, axis=1)
    u = v / np.maximum(r[:, None], 1e-12)
    ub, rb = bin_radius(u, r)
    peak_idx = find_peaks(ub, rb)
    print(f"source {len(src.triangles)} faces, fitted radius {R:.5f}")
    print(f"binned local maxima: {len(peak_idx)}")

    original = o3d.geometry.TriangleMesh(src)
    original.vertex_colors = o3d.utility.Vector3dVector(colour_by_radius(V))
    labels = ["provenance"]
    meshes = [original]

    for name, spec in STRENGTHS.items():
        out, n = apply(src, c, u, r, ub, rb, peak_idx, spec)
        print(f"\n=== {name}: {n} drupelets, k {spec['k']}, "
              f"sep {spec['min_sep_deg']:.0f} deg ===")
        ply = os.path.join(OUT_DIR, f"berry_{name}.ply")
        glb = os.path.join(OUT_DIR, f"berry_{name}.glb")
        o3d.io.write_triangle_mesh(ply, out, write_vertex_colors=True)
        o3d.io.write_triangle_mesh(glb, out, write_vertex_colors=True)
        print(f"  wrote {os.path.basename(glb)}")
        labels.append(name)
        meshes.append(out)

    render_strip(meshes, labels, os.path.join(OUT_DIR, "compare.png"))
    print("DONE")


if __name__ == "__main__":
    main()
