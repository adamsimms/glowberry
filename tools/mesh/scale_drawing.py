# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "pillow", "scikit-image", "matplotlib"]
# ///
"""Scale drawing of the picked berry (v17) at full size, for applications.

Front, side and top outlines with overall dimensions in feet-inches and
metres, and a 1.75 m figure for scale. Outlines come from rasterising the
projected mesh and tracing its edge.

Writes models/renders/v17/glowberry_v17_scale_drawing.{png,pdf}.

Run:
    uv run tools/mesh/scale_drawing.py [--height-m 1.83]
"""

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from skimage.measure import find_contours  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MESH = os.path.join(ROOT, "models", "print", "berry_ref_a_studio_v17_subtle_100mm.stl")
OUT = os.path.join(ROOT, "models", "renders", "v17", "glowberry_v17_scale_drawing")
AMBER, RED, INK, GREY = "#F79523", "#ED541F", "#2b2622", "#b9b4ae"
PX_PER_M = 1200

# A plain standing figure, 1 unit tall (outline, centred on x = 0).
FIGURE = [(-0.035, 1.0), (0.035, 1.0), (0.06, 0.96), (0.055, 0.9), (0.03, 0.87), (0.12, 0.84),
          (0.14, 0.78), (0.13, 0.52), (0.1, 0.52), (0.1, 0.75), (0.085, 0.5), (0.075, 0.02),
          (0.095, 0.0), (0.02, 0.0), (0.012, 0.47), (-0.012, 0.47), (-0.02, 0.0), (-0.095, 0.0),
          (-0.075, 0.02), (-0.085, 0.5), (-0.1, 0.75), (-0.1, 0.52), (-0.13, 0.52), (-0.14, 0.78),
          (-0.12, 0.84), (-0.03, 0.87), (-0.055, 0.9), (-0.06, 0.96)]


def ft_in(m):
    inches = m / 0.0254
    ft, rem = divmod(round(inches), 12)
    return f"{ft} ft {rem} in"


def outline(P2):
    """Largest traced outline of points P2 (n x 2, metres) under the mesh faces."""
    lo = P2.min(axis=0) - 0.05
    size = np.ceil((P2.max(axis=0) - lo + 0.05) * PX_PER_M).astype(int)
    img = Image.new("L", tuple(size), 0)
    d = ImageDraw.Draw(img)
    pix = (P2 - lo) * PX_PER_M
    for tri in FACES:
        d.polygon([tuple(pix[i]) for i in tri], fill=255)
    c = max(find_contours(np.asarray(img).T / 255.0, 0.5), key=len)
    return c / PX_PER_M + lo


def dim(ax, a, b, off, text, vertical=False):
    (x0, y0), (x1, y1) = a, b
    if vertical:
        xs = [x0 + off] * 2
        ax.annotate("", (xs[0], y0), (xs[1], y1), arrowprops=dict(arrowstyle="<->", lw=0.8, color=INK))
        ax.text(xs[0] + 0.05, (y0 + y1) / 2, text, rotation=90, va="center", ha="left", fontsize=8, color=INK)
    else:
        ys = [y0 + off] * 2
        ax.annotate("", (x0, ys[0]), (x1, ys[1]), arrowprops=dict(arrowstyle="<->", lw=0.8, color=INK))
        ax.text((x0 + x1) / 2, ys[0] - 0.08, text, ha="center", va="top", fontsize=8, color=INK)


def main():
    global FACES
    ap = argparse.ArgumentParser()
    ap.add_argument("--height-m", type=float, default=1.83)
    args = ap.parse_args()
    m = trimesh.load(MESH)
    m.apply_scale(args.height_m / m.extents[2])
    m.apply_translation(-np.array([*m.bounds.mean(axis=0)[:2], m.bounds[0][2]]))
    FACES = m.faces
    V = m.vertices
    W, D, H = m.extents

    views = {"Front": outline(V[:, [0, 2]]), "Side": outline(V[:, [1, 2]]), "Top": outline(V[:, [0, 1]])}

    # One axes and one scale for all three views, laid out left to right.
    fig, ax = plt.subplots(figsize=(15, 5.6))
    ax.set_aspect("equal")
    ax.axis("off")
    x = 0.0
    f = np.array(FIGURE) * 1.75
    f[:, 0] += x
    ax.add_patch(Polygon(f, closed=True, fc=GREY, ec="none"))
    ax.text(x, -0.14, "Figure 1.75 m\n(5 ft 9 in)", ha="center", va="top", fontsize=7, color=INK)
    x += 0.55
    for name, c in views.items():
        c = c.copy()
        c[:, 0] += x - c[:, 0].min()
        top = name == "Top"
        if top:
            c[:, 1] += 0.0 - c[:, 1].min()
        ax.add_patch(Polygon(c, closed=True, fc=RED if top else AMBER, ec=INK, lw=1.0, alpha=0.85))
        x0, x1 = c[:, 0].min(), c[:, 0].max()
        y0, y1 = c[:, 1].min(), c[:, 1].max()
        span = W if name in ("Front", "Top") else D
        dim(ax, (x0, y0), (x1, y0), -0.14, f"{ft_in(span)} ({span:.2f} m)")
        tall = D if top else H
        dim(ax, (x1, y0), (x1, y1), 0.12, f"{ft_in(tall)} ({tall:.2f} m)", vertical=True)
        if not top:
            ax.plot([x0 - 0.25, x1 + 0.25], [0, 0], color=INK, lw=0.8)
        ax.text(x0, max(y1, H) + 0.12, name + (" (from above)" if top else ""), fontsize=9, color=INK)
        x = x1 + 0.75
    ax.set_xlim(-0.4, x - 0.3)
    ax.set_ylim(-0.6, max(H, D) + 0.35)
    fig.suptitle("Glowberry: proposed sculpture, scale drawing (all views at the same scale)",
                 x=0.02, ha="left", fontsize=11, color=INK)
    fig.text(0.02, 0.02, "Cloudberry form, translucent shell lit from inside. Overall size "
             f"{ft_in(W)} x {ft_in(D)} x {ft_in(H)} tall ({W:.2f} x {D:.2f} x {H:.2f} m).",
             fontsize=8, color=INK)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT + ".png", dpi=220, facecolor="white")
    fig.savefig(OUT + ".pdf", facecolor="white")
    print(f"{W:.3f} x {D:.3f} x {H:.3f} m -> {os.path.relpath(OUT, ROOT)}.png/.pdf")


if __name__ == "__main__":
    main()
