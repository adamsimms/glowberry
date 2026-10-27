# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "manifold3d",
#                 "scikit-image", "pymeshlab"]
# ///
"""Peak point of each drupelet of the picked berry, in the frame of the
100 mm files (berry_ref_* and ready_v17/*: base at z = 0, centred).

Renders use these to tell drupelets apart (colour per drupelet).

Writes models/print/v17_drupelet_peaks.json.

Run:
    uv run tools/mesh/drupelet_points.py
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from berry_tiers import VARIANTS, build, deform, deform_points  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "models", "print", "v17_drupelet_peaks.json")
HEIGHT_MM = 100.0


def main():
    spec = VARIANTS["a_studio_v17_subtle"]
    raw, _, (C, B, A, X), _ = build(spec, HEIGHT_MM, voxel=HEIGHT_MM / 500)
    frame = (raw.vertices[:, 2].min(), np.ptp(raw.vertices[:, 2]))
    plain = deform(raw.copy(), spec, frame)
    scale = HEIGHT_MM / plain.extents[2]
    b = plain.bounds * scale
    shift = np.array([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    peaks = C[:-1] + A[:-1, :1] * B[:-1, 0]  # drop the core
    peaks = deform_points(peaks, spec, frame) * scale + shift
    with open(OUT, "w") as f:
        json.dump({"frame": "100 mm files, base at z=0, centred", "peaks_mm": np.round(peaks, 3).tolist()}, f)
    print(f"{len(peaks)} peaks -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
