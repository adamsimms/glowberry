"""Step E3: build a berry point cloud per remount and export it for ICP.

Texture-based registration failed, so the remounts will be registered on shape
instead. That needs one point cloud per remount, in each chunk's own arbitrary
coordinate system, containing the berry and as little else as possible.

Deliberately built at downscale=4 (medium). These clouds exist only to solve a
7-parameter similarity transform, and ICP does not benefit from detail that
costs an hour per chunk. The high-quality mesh comes after the merge, once
there is a single solved block worth spending time on.

uniform_sampling is off. Its default 0.1 spacing is expressed in chunk units,
which are arbitrary here and differ between chunks by about 1.4x, so it would
decimate the three clouds inconsistently and bias the registration.

The masks should confine the cloud to the berry. That is checked rather than
assumed: if the reported extent is close to the tie point cloud extent, the
cloud still contains turntable and targets and must be cropped before ICP.

Env:
    BERRY_DENSE_CHUNKS=upright_A_nomask_highonly,...
    BERRY_DENSE_DOWNSCALE=4
    BERRY_DENSE_FORCE=1

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_e3_cloud.py
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

import Metashape  # noqa: E402

DEFAULT_CHUNKS = [
    "upright_A_nomask_highonly",
    "inverted_A_nomask_highonly",
    "sideways_A_nomask_highonly",
]
CHUNKS = [
    s for s in os.environ.get(
        "BERRY_DENSE_CHUNKS", ",".join(DEFAULT_CHUNKS)
    ).split(",") if s
]
DOWNSCALE = int(os.environ.get("BERRY_DENSE_DOWNSCALE", "4"))
FORCE = os.environ.get("BERRY_DENSE_FORCE") == "1"

OUT_DIR = os.path.join(bc.WORK, "clouds")
REPORT = os.path.join(bc.WORK, "reports", "step_e3_cloud.json")


def ply_format():
    for name in ("PointCloudFormatPLY", "PointCloudFormatPly"):
        f = getattr(Metashape, name, None)
        if f is not None:
            return f
    return None


def tie_extent(chunk):
    tp = chunk.tie_points
    if tp is None or tp.points is None:
        return None
    coords = [p.coord for p in tp.points if p.valid]
    if not coords:
        return None
    mins = [min(c[i] for c in coords) for i in range(3)]
    maxs = [max(c[i] for c in coords) for i in range(3)]
    return [round(maxs[i] - mins[i], 4) for i in range(3)]


def cloud_of(chunk):
    pc = getattr(chunk, "point_cloud", None)
    if pc is not None:
        return pc
    clouds = getattr(chunk, "point_clouds", None)
    return clouds[0] if clouds else None


def cloud_info(chunk):
    """Point count and extent of the built cloud, if exposed by this build."""
    pc = cloud_of(chunk)
    if pc is None:
        return None, None
    n = getattr(pc, "point_count", None)
    box = getattr(pc, "bounds", None) or getattr(pc, "bbox", None)
    if box is None:
        return n, None
    try:
        size = box.max - box.min
        return n, [round(size.x, 4), round(size.y, 4), round(size.z, 4)]
    except Exception:
        return n, None


def main():
    bc.ensure_dirs()
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))
    print("downscale:", DOWNSCALE)

    fmt = ply_format()
    if fmt is None:
        print("no PLY point cloud format available; cannot export for ICP")
        return

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)

    # The failed registration copies are dead weight; drop them.
    for stale in [c for c in doc.chunks if c.label.endswith("_reg")]:
        print(f"removing failed registration chunk {stale.label}")
        doc.remove(stale)
    doc.save()

    report = {}
    if os.path.exists(REPORT):
        try:
            report = json.load(open(REPORT))
        except Exception:
            report = {}

    for name in CHUNKS:
        chunk = next((c for c in doc.chunks if c.label == name), None)
        if chunk is None:
            print(f"\n{name}: NO SUCH CHUNK, skipping")
            continue

        out_ply = os.path.join(OUT_DIR, f"{name}.ply")
        if os.path.exists(out_ply) and not FORCE:
            print(f"\n{name}: {out_ply} exists, skipping")
            continue

        cams = [c for c in chunk.cameras if c.enabled and c.transform]
        masked = sum(1 for c in cams if c.mask is not None)
        print(f"\n=== {name}: {len(cams)} aligned cameras, {masked} masked ===")
        tie_ext = tie_extent(chunk)
        print(f"  tie point extent (berry + targets + turntable): {tie_ext}")

        t0 = time.time()
        chunk.buildDepthMaps(downscale=DOWNSCALE, filter_mode=Metashape.MildFiltering)
        t_depth = time.time() - t0
        print(f"  buildDepthMaps: {t_depth/60:.1f} min")
        doc.save()

        t0 = time.time()
        chunk.buildPointCloud(
            source_data=Metashape.DepthMapsData,
            point_colors=True,
            point_confidence=True,
            uniform_sampling=False,
        )
        t_cloud = time.time() - t0
        print(f"  buildPointCloud: {t_cloud/60:.1f} min")
        doc.save()

        n, ext = cloud_info(chunk)
        print(f"  points: {n}, extent: {ext}")
        if ext and tie_ext:
            # Masks worked if the cloud is much smaller than the whole scene.
            ratio = max(ext) / max(tie_ext)
            print(f"  cloud/scene size ratio: {ratio:.3f}")
            if ratio > 0.6:
                print(
                    "  WARNING: cloud is nearly scene sized, so masks did not "
                    "confine it to the berry. Crop before ICP."
                )
            else:
                print("  masks confined the cloud; berry only, good for ICP")

        chunk.exportPointCloud(
            path=out_ply,
            source_data=Metashape.PointCloudData,
            format=fmt,
            binary=True,
            save_point_color=True,
            save_point_normal=True,
            save_point_confidence=True,
        )
        size_mb = (
            round(os.path.getsize(out_ply) / 1e6, 1)
            if os.path.exists(out_ply) else None
        )
        print(f"  exported {out_ply} ({size_mb} MB)")

        report[name] = {
            "cameras": len(cams),
            "masked": masked,
            "downscale": DOWNSCALE,
            "tie_extent": tie_ext,
            "cloud_points": n,
            "cloud_extent": ext,
            "depth_min": round(t_depth / 60, 2),
            "cloud_min": round(t_cloud / 60, 2),
            "ply": out_ply,
            "ply_mb": size_mb,
        }
        with open(REPORT, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        doc.save()

    print("\n=== SUMMARY ===")
    for name, r in report.items():
        print(
            f"{name:34} {r['cloud_points']} pts  extent {r['cloud_extent']}  "
            f"{r['ply_mb']} MB  ({r['depth_min']}+{r['cloud_min']} min)"
        )
    print("WROTE", REPORT)
    print("DONE")


main()
