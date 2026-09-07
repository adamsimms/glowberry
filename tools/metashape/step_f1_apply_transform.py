"""Step F1: put the inverted chunk into the upright chunk's frame.

The registration was solved outside Metashape, on exported point clouds, by
sweeping the one angle the turntable geometry leaves free. This brings that
result back into the project by rewriting the inverted chunk's transform, so
the two remounts share a coordinate system and can be merged.

Frames, since getting this wrong is the easiest way to waste an hour of
meshing on nonsense. exportPointCloud wrote each PLY in its chunk's world
frame, and icp_constrained.py then mapped each cloud into a normalised frame
(turntable axis on +z, berry centred, unit radius) with a matrix it recorded
as that chunk's pre-transform. So:

    A = inv(pre_upright) @ T_pair @ pre_inverted

maps inverted world coordinates to upright world coordinates, where
T_pair @ pre_inverted is what the JSON stores as
transform_ply_to_upright_frame. A chunk transform maps chunk-internal to
world, so the new one is A composed onto the old.

The scale A carries is checked rather than trusted: it must come out near
r_upright / r_inverted, which is 0.6855 from the fitted radii, and that in
turn should sit near the 0.67 the camera rings and target constellation
independently suggested. Three methods agreeing is the only reason to believe
an absolute scale here, since the remounts share no markers.

Applying this twice would silently double the transform, so the chunk is
stamped in its meta and a second run refuses unless BERRY_MERGE_FORCE=1.

Exports both clouds in the new common frame for verification. It does not
merge; verify first, then run step_f2_merge.py.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f1_apply_transform.py
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

UPRIGHT = "upright_A_nomask_highonly"
INVERTED = "inverted_A_nomask_highonly"
TRANSFORMS = os.path.join(bc.WORK, "icp", "constrained_transforms.json")
OUT_DIR = os.path.join(bc.WORK, "clouds")
STAMP = "berry_registered_to"
FORCE = os.environ.get("BERRY_MERGE_FORCE") == "1"

# From the fitted radii, r_upright / r_inverted. Anything far from this means
# the composition is wrong, not that the berry changed size.
EXPECTED_SCALE = 0.6855
SCALE_TOL = 0.05


def ply_format():
    for name in ("PointCloudFormatPLY", "PointCloudFormatPly"):
        f = getattr(Metashape, name, None)
        if f is not None:
            return f
    return None


def to_ms(M):
    return Metashape.Matrix([[float(x) for x in row] for row in M])


def to_np(M):
    """Metashape.Matrix -> 4x4 numpy. np.asarray flattens it to 16 elements."""
    a = np.asarray(M, dtype=float)
    return a if a.ndim == 2 else a.reshape(4, 4)


def scale_of(M):
    """Uniform scale factor of a similarity transform."""
    return float(np.linalg.norm(to_np(M)[:3, 0]))


def meta_get(meta, key):
    """Read a chunk meta key. Metashape.MetaData indexes but has no .get."""
    try:
        return meta[key] or None
    except Exception:
        return None


def probe_merge_api():
    """Print the installed mergeChunks signature.

    The 2.3.2 API has already diverged from the 2.2 docs in this project
    (importMasks and MaskSource both gone), so the next step reads the
    signature rather than assuming it.
    """
    print("\n=== Document.mergeChunks as installed ===")
    fn = getattr(Metashape.Document, "mergeChunks", None)
    if fn is None:
        print("  MISSING: no Document.mergeChunks in this build")
        return
    doc_s = (fn.__doc__ or "").strip()
    print(" ", doc_s if doc_s else "(no docstring)")


def main():
    bc.ensure_dirs()
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Metashape", Metashape.app.version)

    with open(TRANSFORMS) as fh:
        rep = json.load(fh)
    pair = rep["pairs"]["inverted_to_upright"]
    pre_up = np.asarray(rep["upright_pre_transform"], float)
    to_up_frame = np.asarray(pair["transform_ply_to_upright_frame"], float)
    A = np.linalg.inv(pre_up) @ to_up_frame

    print(f"\nregistration being applied: sweep peak "
          f"{pair['sweep_peak_angle_deg']:.0f} deg, score "
          f"{pair['sweep_peak_score']:.4f} against median "
          f"{pair['sweep_median']:.4f}, ICP fitness {pair['icp_fitness']:.4f} "
          f"at {pair['icp_inlier_rmse']*100:.2f}% of radius")

    s = scale_of(A)
    print(f"\ninverted -> upright world transform, scale {s:.5f} "
          f"(expected {EXPECTED_SCALE:.4f})")
    if abs(s - EXPECTED_SCALE) > SCALE_TOL:
        print(
            f"  ABORT: scale is {abs(s-EXPECTED_SCALE)/EXPECTED_SCALE*100:.1f}% "
            f"off the value the fitted radii imply, so the composition is "
            f"wrong. Not touching the project."
        )
        return
    print("  scale agrees with the fitted radii; composition looks right")

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    up = next((c for c in doc.chunks if c.label == UPRIGHT), None)
    inv = next((c for c in doc.chunks if c.label == INVERTED), None)
    if up is None or inv is None:
        print(f"missing chunk: upright={up is not None} inverted={inv is not None}")
        return

    already = meta_get(inv.meta, STAMP)
    if already and not FORCE:
        print(f"\n{INVERTED} is already registered to {already}. Applying the "
              f"transform again would double it. Set BERRY_MERGE_FORCE=1 to "
              f"override.")
    else:
        before = to_np(inv.transform.matrix)
        inv.transform.matrix = to_ms(A) * inv.transform.matrix
        after = to_np(inv.transform.matrix)
        inv.meta[STAMP] = UPRIGHT
        print(f"\n{INVERTED}: chunk scale {scale_of(before):.5f} -> "
              f"{scale_of(after):.5f}")
        print(f"{UPRIGHT}:  chunk scale {scale_of(up.transform.matrix):.5f}")
        doc.save()
        print("  transform applied and saved")

    fmt = ply_format()
    if fmt is None:
        print("no PLY format available; cannot export for verification")
        return
    print("\n=== exporting both clouds in the common frame ===")
    for chunk in (up, inv):
        out = os.path.join(OUT_DIR, f"{chunk.label}_common.ply")
        chunk.exportPointCloud(
            path=out, source_data=Metashape.PointCloudData, format=fmt,
            binary=True, save_point_color=True, save_point_normal=True,
        )
        mb = round(os.path.getsize(out) / 1e6, 1) if os.path.exists(out) else None
        print(f"  {chunk.label} -> {os.path.basename(out)} ({mb} MB)")

    probe_merge_api()
    print("\nNext: verify with verify_common_frame.py, then step_f2_merge.py")
    print("DONE")


main()
