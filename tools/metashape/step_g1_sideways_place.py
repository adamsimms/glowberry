"""Step G1: put sideways into the merged frame and build its cloud to match.

The pose came from step_f9d and was checked in step_f9e: four independent
starts converged on it, it stands 1.33x clear of the best genuinely different
solution, 47.5% of its points fall inside the mesh so the centring is right,
and a scale sweep peaks at 0.99 so the size is right. What it is not is clean.
Measured against the mesh the same way as the other two, sideways puts 47.6%
of its points within 2% of radius where upright and inverted manage 83.5% and
84.3%, which is roughly three times the surface noise.

That is why this step only places and rebuilds. Filtering by region, and the
decision about what actually goes into the mesh, is step_g2.

Frames, composed the same way step_f1 did for inverted. exportPointCloud and
exportModel each wrote in their chunk's world frame, and the registration
scripts mapped those into a normalised frame (turntable axis on +z, berry
centred, unit radius), recording the matrix used. So:

    A = inv(pre_mesh) @ T_winner @ pre_sideways

takes sideways world coordinates to merged world coordinates, and a chunk
transform maps chunk-internal to world, so A composes onto the old one.

The scale A carries is checked, not trusted: it must land near
r_mesh / r_sideways = 0.10163 / 0.13904, and a composition error shows up here
before any time is spent on depth maps.

The existing sideways cloud is downscale 4, from step_e3. This rebuilds at
downscale 2 so it is directly comparable to the two already in the mesh,
rather than contributing at a different resolution.

Expect about half the cameras to yield depth maps. Ring 15 came out with "no
neighbors" for both other remounts, because the gradual selection that tightened
these alignments left those cameras below the 50 shared tie points that
neighbour selection needs.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_g1_sideways_place.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import berry_common as bc  # noqa: E402

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

bc.add_user_packages()

import numpy as np  # noqa: E402
import Metashape  # noqa: E402

SIDEWAYS = "sideways_A_nomask_highonly"
REFINE = os.path.join(bc.WORK, "reports", "step_f9d_refine.json")
OUT = os.path.join(bc.WORK, "clouds", f"{SIDEWAYS}_dense2_common.ply")
REPORT = os.path.join(bc.WORK, "reports", "step_g1_sideways.json")
STAMP = "berry_registered_to"
# Three separate switches. FORCE alone used to gate the transform and the
# assets together, which made rebuilding a cloud require unlocking the guard
# against applying the registration twice.
FORCE = os.environ.get("BERRY_SW_FORCE") == "1"                # transform
REBUILD_DEPTH = os.environ.get("BERRY_SW_REBUILD_DEPTH") == "1"
REBUILD_CLOUD = os.environ.get("BERRY_SW_REBUILD_CLOUD") == "1"

DOWNSCALE = int(os.environ.get("BERRY_DEPTH_DOWNSCALE", "2"))
EXPECTED_SCALE = 0.10163 / 0.13904
SCALE_TOL = 0.05


def to_ms(M):
    return Metashape.Matrix([[float(x) for x in row] for row in M])


def to_np(M):
    a = np.asarray(M, dtype=float)
    return a if a.ndim == 2 else a.reshape(4, 4)


def scale_of(M):
    return float(np.linalg.norm(to_np(M)[:3, 0]))


def asset_count(asset, chunk=None):
    """Best-effort count for a depth map or point cloud asset.

    Never raises. Two runs of this step were lost to counting: DepthMaps
    supports neither len() nor iteration, and PointCloud has no .points. A
    progress number is not worth discarding six minutes of depth maps, so
    every access is guarded and -1 means unknown.
    """
    if asset is None:
        return 0
    try:
        return len(asset)
    except Exception:
        pass
    for attr in ("point_count", "Points", "points", "size"):
        try:
            v = getattr(asset, attr)
            return len(v) if hasattr(v, "__len__") else int(v)
        except Exception:
            continue
    if chunk is not None:
        try:
            return sum(1 for c in chunk.cameras if asset[c] is not None)
        except Exception:
            pass
    return -1


def meta_get(meta, key):
    try:
        return meta[key] or None
    except Exception:
        return None


def ply_format():
    for name in ("PointCloudFormatPLY", "PointCloudFormatPly"):
        f = getattr(Metashape, name, None)
        if f is not None:
            return f
    return None


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    with open(REFINE) as fh:
        rep = json.load(fh)
    win = rep["winner"]
    A = (np.linalg.inv(np.asarray(rep["pre_mesh"], float))
         @ np.asarray(win["transform"], float)
         @ np.asarray(rep["pre_sideways"], float))

    print(f"\npose being applied: stem {win['stem_deg']:.0f} deg, spin "
          f"{win['spin_deg']:.0f} deg, tilt {win['tilt_deg']:+.0f} deg")
    print(f"  reached from {rep['starts_in_winning_basin']} of "
          f"{len(rep['candidates'])} independent starts, "
          f"{rep['isolation']:.2f}x clear of the best rival, "
          f"rmse {win['rmse']*100:.2f}% of radius")

    s = scale_of(A)
    print(f"\nsideways -> merged world transform, scale {s:.5f} "
          f"(expected {EXPECTED_SCALE:.5f} from the fitted radii)")
    if abs(s - EXPECTED_SCALE) / EXPECTED_SCALE > SCALE_TOL:
        print(f"  ABORT: that is "
              f"{abs(s-EXPECTED_SCALE)/EXPECTED_SCALE*100:.1f}% off, so the "
              f"composition is wrong. Not touching the project.")
        return
    print("  scale agrees with the fitted radii; composition looks right")

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    chunk = next((c for c in doc.chunks if c.label == SIDEWAYS), None)
    if chunk is None:
        print(f"no chunk {SIDEWAYS}")
        return

    already = meta_get(chunk.meta, STAMP)
    if already and not FORCE:
        print(f"\n{SIDEWAYS} is already registered to {already}; applying "
              f"again would double it. BERRY_SW_FORCE=1 to override.")
    else:
        before = scale_of(chunk.transform.matrix)
        chunk.transform.matrix = to_ms(A) * chunk.transform.matrix
        chunk.meta[STAMP] = "merged_up_inv"
        print(f"\n{SIDEWAYS}: chunk scale {before:.5f} -> "
              f"{scale_of(chunk.transform.matrix):.5f}")
        doc.save()
        print("  transform applied and saved")

    cams = [c for c in chunk.cameras if c.enabled and c.transform]
    masked = sum(1 for c in chunk.cameras if c.mask is not None)
    print(f"\n=== {SIDEWAYS}: {len(cams)} solved cameras, {masked} masked ===")

    t0 = time.time()
    if chunk.depth_maps is not None and not REBUILD_DEPTH:
        print(f"depth maps already present, reusing them "
              f"(BERRY_SW_REBUILD_DEPTH=1 to rebuild)")
    else:
        print(f"building depth maps at downscale {DOWNSCALE}...")
        chunk.buildDepthMaps(downscale=DOWNSCALE,
                             filter_mode=Metashape.MildFiltering)
        doc.save()      # persist before the next step can fail
    n_depth = asset_count(chunk.depth_maps, chunk)
    print(f"  {n_depth} depth maps in {(time.time()-t0)/60:.1f} min")
    if n_depth == 0:
        print("  ABORT: no depth maps, nothing to contribute")
        return

    print("building the dense cloud...")
    t0 = time.time()
    if chunk.point_cloud is not None and not REBUILD_CLOUD:
        print("  a dense cloud already exists; reusing it "
              "(BERRY_SW_REBUILD_CLOUD=1 to rebuild from the new depth maps)")
    else:
        chunk.buildPointCloud(point_colors=True, uniform_sampling=False)
    doc.save()          # save before anything that might raise
    n_pts = asset_count(chunk.point_cloud, chunk)
    print(f"  {n_pts} points in {(time.time()-t0)/60:.1f} min")

    fmt = ply_format()
    chunk.exportPointCloud(
        path=OUT, source_data=Metashape.PointCloudData, format=fmt,
        binary=True, save_point_color=True, save_point_normal=True,
    )
    mb = round(os.path.getsize(OUT) / 1e6, 1) if os.path.exists(OUT) else None
    print(f"  exported {os.path.basename(OUT)} ({mb} MB), already in the "
          f"merged frame")

    with open(REPORT, "w") as fh:
        json.dump({
            "chunk": SIDEWAYS, "pose": win, "transform_to_merged": A.tolist(),
            "scale": s, "expected_scale": EXPECTED_SCALE,
            "downscale": DOWNSCALE, "cameras": len(cams),
            "depth_maps": n_depth, "points": n_pts, "ply": OUT, "ply_mb": mb,
        }, fh, indent=2, default=str)
    print("WROTE", REPORT)
    print("\nNext: step_g2_sideways_filter.py")
    print("DONE")


main()
