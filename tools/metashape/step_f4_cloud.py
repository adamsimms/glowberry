"""Step F4: fuse each remount's depth maps to a point cloud and export it.

Needed because mergeChunks will not carry depth maps from two chunks. Both
sets are created with key 0, so one overwrites the other and the merged chunk
ended up with 37 of the 75 depth maps. Masks merged fine; depth maps did not.

So each remount is fused in its own chunk, where its depth maps live, and the
two clouds are exported in the shared frame that step_f1 established. They are
then combined outside and imported back as a single cloud for the mesh, which
is the one representation Metashape will accept from both remounts at once.

uniform_sampling stays off. Its default 0.1 spacing is in chunk units, which
are arbitrary and differ between these two chunks by 0.6855, so it would thin
the two clouds by different amounts and bias the surface toward whichever was
sampled more densely.

Only about half the cameras in each chunk have depth maps, all from ring 40.
Ring 15 frames were dropped by buildDepthMaps as having no neighbours, because
the gradual selection behind the _highonly alignment culled tie points below
the 50 shared points it needs. Coverage survives: the two remounts still cover
the full sphere between them.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f4_cloud.py
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

CHUNKS = ["upright_A_nomask_highonly", "inverted_A_nomask_highonly"]
OUT_DIR = os.path.join(bc.WORK, "clouds")
REPORT = os.path.join(bc.WORK, "reports", "step_f4_cloud.json")
FORCE = os.environ.get("BERRY_CLOUD_FORCE") == "1"
SUFFIX = "_dense2"


def ply_format():
    for name in ("PointCloudFormatPLY", "PointCloudFormatPly"):
        f = getattr(Metashape, name, None)
        if f is not None:
            return f
    return None


def depth_count(chunk):
    dm = getattr(chunk, "depth_maps", None)
    if dm is None:
        return 0
    n = 0
    for cam in chunk.cameras:
        try:
            if dm[cam] is not None:
                n += 1
        except Exception:
            pass
    return n


def main():
    bc.ensure_dirs()
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    fmt = ply_format()
    if fmt is None:
        print("no PLY format available")
        return

    report = {}
    if os.path.exists(REPORT):
        try:
            report = json.load(open(REPORT))
        except Exception:
            report = {}

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)

    for label in CHUNKS:
        chunk = next((c for c in doc.chunks if c.label == label), None)
        if chunk is None:
            print(f"\n{label}: NO SUCH CHUNK")
            continue

        out_ply = os.path.join(OUT_DIR, f"{label}{SUFFIX}.ply")
        if os.path.exists(out_ply) and not FORCE:
            print(f"\n{label}: {os.path.basename(out_ply)} exists, skipping")
            continue

        nd = depth_count(chunk)
        print(f"\n=== {label}: fusing {nd} depth maps ===")
        if nd == 0:
            print("  no depth maps; run step_f2_depth.py first")
            continue

        t0 = time.time()
        chunk.buildPointCloud(
            source_data=Metashape.DepthMapsData,
            point_colors=True,
            point_confidence=True,
            uniform_sampling=False,
            keep_depth=True,
            replace_asset=True,
        )
        mins = (time.time() - t0) / 60
        doc.save()

        pc = getattr(chunk, "point_cloud", None)
        n = getattr(pc, "point_count", None) if pc is not None else None
        print(f"  {n} points in {mins:.1f} min")

        chunk.exportPointCloud(
            path=out_ply, source_data=Metashape.PointCloudData, format=fmt,
            binary=True, save_point_color=True, save_point_normal=True,
        )
        mb = round(os.path.getsize(out_ply) / 1e6, 1)
        print(f"  exported {os.path.basename(out_ply)} ({mb} MB)")

        report[label] = {
            "depth_maps": nd, "points": n, "minutes": round(mins, 2),
            "ply": out_ply, "ply_mb": mb,
        }
        with open(REPORT, "w") as fh:
            json.dump(report, fh, indent=2, default=str)

    print("\n=== SUMMARY ===")
    for label, r in report.items():
        print(f"{label:34} {r['points']} points from {r['depth_maps']} "
              f"depth maps ({r['minutes']} min)")
    print("\nNext: combine_clouds.py, then step_f5_mesh.py")
    print("DONE")


main()
