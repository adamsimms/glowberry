"""Inspect the merged mesh, above all for a seam at the remount hand-off.

Two remounts were joined by a registration solved on shape, so the specific
failure to look for is a step where upright's surface gives way to inverted's.
A global misregistration would already have shown up in the coverage gates; a
local one shows up here and nowhere else.

The unwrap is the test that targets it. Vertices are plotted by longitude and
latitude and coloured by how far they sit from the mean radius, so a
registration step appears as a horizontal discontinuity: colour that jumps
across a line of latitude rather than varying smoothly. Real drupelet relief
looks like smooth blobs, and noise looks like speckle, so the three are
distinguishable by eye.

Also reports watertightness, boundary edges and connected components, since an
interpolated mesh over a 99.3% covered sphere should be one closed piece with
at most a small patch where the two mount holes overlapped.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python inspect_mesh.py
"""

import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
OUT_DIR = os.path.join(WORK, "icp")
# Prefer the cleaned mesh when it exists, so a rerun after step_f6 reports on
# what will actually be textured.
MESH = os.environ.get("BERRY_INSPECT_MESH") or next(
    p for p in (
        os.path.join(WORK, "exports", "merged_up_inv_clean.ply"),
        os.path.join(WORK, "exports", "merged_up_inv_untextured.ply"),
    ) if os.path.exists(p)
)


def fit_sphere(pts):
    A = np.hstack([2.0 * pts, np.ones((len(pts), 1))])
    b = np.sum(pts ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 1e-12)))


def main():
    print("inspecting", os.path.basename(MESH))
    mesh = o3d.io.read_triangle_mesh(MESH)
    mesh.compute_vertex_normals()
    V = np.asarray(mesh.vertices)
    F = np.asarray(mesh.triangles)
    print(f"{len(F)} faces, {len(V)} vertices")

    # Count boundary edges, to say how open the surface actually is. An edge
    # used by one triangle is a border; a closed surface has none.
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e = np.sort(e, axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    border = int((counts == 1).sum())
    print(f"boundary edges: {border} of {len(counts)} unique edges "
          f"({border/len(counts)*100:.3f}%)")

    # is_self_intersecting is quadratic and took most of a nine minute run
    # without changing any decision here, so it is left out.
    print(f"watertight: {mesh.is_watertight()}, "
          f"edge manifold: {mesh.is_edge_manifold()}")

    labels, counts, _ = mesh.cluster_connected_triangles()
    counts = np.asarray(counts)
    order = np.argsort(counts)[::-1]
    print(f"connected components: {len(counts)}; largest holds "
          f"{counts[order[0]]/len(F)*100:.2f}% of faces")
    if len(counts) > 1:
        print(f"  next largest: {counts[order[1]]} faces "
              f"({counts[order[1]]/len(F)*100:.3f}%) -> loose fragments")

    centre, radius = fit_sphere(V)
    print(f"sphere fit: radius {radius:.5f}, centre {np.round(centre, 4)}")

    v = V - centre
    r = np.linalg.norm(v, axis=1)
    lon = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    lat = np.degrees(np.arcsin(np.clip(v[:, 2] / r, -1, 1)))
    dev = (r - radius) / radius * 100
    print(f"radial deviation: mean {dev.mean():+.2f}%, sd {dev.std():.2f}%, "
          f"p1 {np.percentile(dev,1):+.1f}%, p99 {np.percentile(dev,99):+.1f}%")

    # A seam would make the mean radius jump between adjacent latitude bands,
    # so scan for the largest such step. Drupelet relief varies smoothly and
    # should not produce a sharp one.
    edges = np.arange(-90, 91, 3)
    band = np.digitize(lat, edges) - 1
    means, mids = [], []
    for k in range(len(edges) - 1):
        sel = band == k
        if sel.sum() > 50:
            means.append(dev[sel].mean())
            mids.append((edges[k] + edges[k + 1]) / 2)
    means, mids = np.asarray(means), np.asarray(mids)
    steps = np.abs(np.diff(means))
    worst = int(np.argmax(steps))
    print(f"\nlargest jump in mean radius between neighbouring 3 deg bands: "
          f"{steps[worst]:.2f}% of radius at latitude "
          f"{mids[worst]:.0f} to {mids[worst+1]:.0f}")
    print(f"typical band-to-band change: {np.median(steps):.2f}%")
    if steps[worst] > 4 * max(np.median(steps), 1e-6):
        print("  that stands out from the rest; inspect the unwrap at that "
              "latitude for a registration step")
    else:
        print("  no band stands out, so no obvious seam in mean radius")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 9), dpi=110)
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax = fig.add_subplot(gs[0, :])
    s = np.random.default_rng(0).choice(len(V), min(120000, len(V)), replace=False)
    im = ax.scatter(lon[s], lat[s], c=dev[s], s=1.0, cmap="RdBu_r",
                    vmin=-20, vmax=20)
    ax.set_xlabel("longitude (deg)")
    ax.set_ylabel("latitude (deg)")
    ax.set_title("Merged mesh unwrapped: radial deviation. A seam would be a "
                 "horizontal colour discontinuity")
    plt.colorbar(im, ax=ax, fraction=0.025, label="% of radius")

    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(mids, means, lw=1.4)
    ax2.set_xlabel("latitude (deg)")
    ax2.set_ylabel("mean deviation (%)")
    ax2.set_title("Mean radius by latitude band")
    ax2.grid(alpha=0.3)

    ax3 = fig.add_subplot(gs[1, 1])
    ax3.hist(dev, bins=160)
    ax3.set_xlabel("radial deviation (% of radius)")
    ax3.set_title("Distribution of relief")

    fig.tight_layout()
    p = os.path.join(OUT_DIR, "mesh_inspect.png")
    fig.savefig(p)
    print("\nwrote", p)
    print("DONE")


main()
