"""Step F2: build depth maps in each source chunk, before merging.

Order matters, and it is the opposite of the obvious one. Depth maps have to be
built per remount and then carried into the merged chunk, rather than built
after merging, because of how mergeChunks behaves on chunks that share no
matches:

  merge_tiepoints=True  fails with "Empty pairs list". Merging tie point
                        clouds looks for image pairs between the chunks, and
                        the two remounts have none. That absence is the whole
                        reason registration had to be solved on shape.

  merge_tiepoints=False leaves the merged chunk with no tie points at all, and
                        buildDepthMaps chooses each camera's neighbours by
                        counting shared tie points. With none it reports "no
                        neighbors" for every camera and builds nothing, the
                        same wall the ring 15 experiment hit.

Building here sidesteps both. Each source chunk keeps its own tie points, so
neighbour selection works normally within a remount, and step_f3 then merges
with copy_depth_maps=True. Fusion into one surface happens geometrically, in
the common frame, which is exactly what is wanted: the two remounts should be
joined by the registration, not by imaginary shared features.

downscale=2, not 1. Independent camera rings agree on the surface to 0.85% of
radius, so the finest scale would mostly resolve that disagreement rather than
real drupelet detail. Set BERRY_DEPTH_DOWNSCALE=1 to compare if the mesh looks
soft.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f2_depth.py
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

CHUNKS = ["upright_A_nomask_highonly", "inverted_A_nomask_highonly"]
DOWNSCALE = int(os.environ.get("BERRY_DEPTH_DOWNSCALE", "2"))
FORCE = os.environ.get("BERRY_DEPTH_FORCE") == "1"
REPORT = os.path.join(bc.WORK, "reports", "step_f2_depth.json")

FILTER = {
    "mild": Metashape.MildFiltering,
    "moderate": Metashape.ModerateFiltering,
    "aggressive": Metashape.AggressiveFiltering,
}[os.environ.get("BERRY_DEPTH_FILTER", "mild")]


def depth_count(chunk):
    dm = getattr(chunk, "depth_maps", None)
    if dm is None:
        return 0
    try:
        return len(dm)
    except Exception:
        return -1


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))
    print(f"downscale {DOWNSCALE}, filtering {FILTER}")

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

        done = report.get(label, {}).get("downscale") == DOWNSCALE
        if done and not FORCE:
            print(f"\n{label}: depth maps already at downscale {DOWNSCALE}, "
                  f"skipping")
            continue

        cams = [c for c in chunk.cameras if c.enabled and c.transform]
        masked = sum(1 for c in chunk.cameras if c.mask is not None)
        print(f"\n=== {label}: {len(cams)} solved cameras, {masked} masked ===")

        t0 = time.time()
        chunk.buildDepthMaps(downscale=DOWNSCALE, filter_mode=FILTER)
        mins = (time.time() - t0) / 60
        n = depth_count(chunk)
        print(f"  built {n} depth maps in {mins:.1f} min")
        if n == 0:
            print("  WARNING: no depth maps, so nothing will carry into the "
                  "merge")
        doc.save()

        report[label] = {
            "downscale": DOWNSCALE,
            "filter": str(FILTER),
            "cameras": len(cams),
            "depth_maps": n,
            "minutes": round(mins, 2),
        }
        with open(REPORT, "w") as fh:
            json.dump(report, fh, indent=2, default=str)

    print("\n=== SUMMARY ===")
    for label, r in report.items():
        print(f"{label:34} {r['depth_maps']} depth maps at downscale "
              f"{r['downscale']} ({r['minutes']} min)")
    print("WROTE", REPORT)
    print("\nNext: step_f3_merge.py (copy_depth_maps=True, merge_tiepoints=False)")
    print("DONE")


main()
