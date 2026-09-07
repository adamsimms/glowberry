"""Step D part 1: per-remount alignment, two masking variants, then compare.

Two ways to align a remount, run as separate chunk copies so they can be
compared on identical input:

  A "nomask"  filter_mask=False, mask_tiepoints=False, filter_stationary_points=True
              Targets and turntable surface generate tie points. The static wall
              and table are removed by stationary-point filtering. This mirrors
              the known-good 40-frame test that aligned 40/40.

  B "mask"    filter_mask=True, mask_tiepoints=False, filter_stationary_points=False
              Tie points come from berry texture only. The targets contribute
              through their already-detected marker projections.

mask_tiepoints defaults to True in the API and MUST be False for both variants.
For variant A it would apply masks that variant is meant to ignore. For variant
B it is actively destructive: with a tight mask on a small object viewed from
many angles, a 3D point near the silhouette projects outside the mask in other
views and is discarded, so nearly every tie point is removed. Measured on 12
frames of upright/40: mask_tiepoints=True gave 0 points and 0 aligned, while
mask_tiepoints=False gave 1365 points and 12/12 aligned.

Do not set keypoint_limit_per_mpx=0 hoping to mean "unlimited". It suppresses
track clusters and yields 0 points.

All four rings are aligned in one pass per chunk, with per-ring aligned counts
reported. keep_keypoints=True preserves the option to subalign later without a
full rematch.

The three imported chunks are left untouched as pristine sources; work happens
on copies labelled <remount>_A_nomask and <remount>_B_mask.

Env:
    BERRY_P2_REMOUNTS=upright,inverted,sideways   default: upright
    BERRY_P2_VARIANTS=A,B                         default: A,B

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_d_align_variants.py
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

REPORT = os.path.join(bc.WORK, "reports", "step_d_variants.json")

REMOUNTS = [
    s for s in os.environ.get("BERRY_P2_REMOUNTS", "upright").split(",") if s
]
VARIANTS = [s for s in os.environ.get("BERRY_P2_VARIANTS", "A,B").split(",") if s]
FORCE = os.environ.get("BERRY_P2_FORCE") == "1"

# From the known-good 40-frame baseline on this capture setup.
KEYPOINT_LIMIT = 60000
TIEPOINT_LIMIT = 10000

VARIANT_PARAMS = {
    "A": {
        "suffix": "A_nomask",
        "match": dict(
            downscale=1,
            generic_preselection=True,
            reference_preselection=False,
            filter_mask=False,
            mask_tiepoints=False,
            filter_stationary_points=True,
            keypoint_limit=KEYPOINT_LIMIT,
            tiepoint_limit=TIEPOINT_LIMIT,
            keep_keypoints=True,
        ),
    },
    "B": {
        "suffix": "B_mask",
        "match": dict(
            downscale=1,
            generic_preselection=False,  # a ~700 px subject vanishes at preselection scale
            reference_preselection=False,
            filter_mask=True,
            mask_tiepoints=False,
            filter_stationary_points=False,
            keypoint_limit=KEYPOINT_LIMIT,
            tiepoint_limit=TIEPOINT_LIMIT,
            keep_keypoints=True,
        ),
    },
}


def reprojection_stats(chunk):
    """RMS and max reprojection error over all valid tie point projections."""
    tp = chunk.tie_points
    if tp is None:
        return None
    points = tp.points
    projections = tp.projections
    if not points:
        return None

    point_ids = [-1] * len(tp.tracks)
    for pid, p in enumerate(points):
        point_ids[p.track_id] = pid

    sq_sum = 0.0
    n = 0
    worst = 0.0
    for camera in chunk.cameras:
        if not camera.transform:
            continue
        for proj in projections[camera]:
            pid = point_ids[proj.track_id]
            if pid < 0:
                continue
            point = points[pid]
            if not point.valid:
                continue
            try:
                reproj = camera.project(point.coord)
            except Exception:
                continue
            if reproj is None:
                continue
            err = (reproj - proj.coord).norm()
            sq_sum += err * err
            n += 1
            worst = max(worst, err)
    if not n:
        return None
    return {
        "rms_px": round((sq_sum / n) ** 0.5, 4),
        "max_px": round(worst, 3),
        "projections": n,
        "tie_points": len(points),
    }


def per_ring_aligned(chunk):
    out = {}
    for cam in chunk.cameras:
        ring = cam.group.label if cam.group else "ungrouped"
        d = out.setdefault(ring, {"enabled": 0, "aligned": 0, "failed": []})
        if not cam.enabled:
            continue
        d["enabled"] += 1
        if cam.transform:
            d["aligned"] += 1
        else:
            d["failed"].append(cam.label)
    return out


def marker_stats(chunk):
    out = {}
    for m in chunk.markers:
        obs = sum(1 for _c, p in m.projections.items() if p is not None)
        out[m.label] = obs
    return out


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))
    print("remounts:", REMOUNTS, "variants:", VARIANTS)

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)

    report = {}
    if os.path.exists(REPORT):
        try:
            report = json.load(open(REPORT))
        except Exception:
            report = {}

    for remount in REMOUNTS:
        source = next((c for c in doc.chunks if c.label == remount), None)
        if source is None:
            print(f"{remount}: NO SUCH CHUNK, skipping")
            continue

        for v in VARIANTS:
            spec = VARIANT_PARAMS[v]
            label = f"{remount}_{spec['suffix']}"

            existing = next((c for c in doc.chunks if c.label == label), None)
            # Resume on a recorded aligned result, not on tie_points being
            # non-None: a failed match still leaves a tie_points object behind.
            done = report.get(label, {}).get("aligned", 0) > 0
            if done and not FORCE:
                print(f"\n{label}: already aligned, skipping")
                continue
            if existing is not None and (FORCE or not done):
                print(f"  discarding previous {label}")
                doc.remove(existing)
                existing = None

            print(f"\n=== {label} ===")
            print("  params:", json.dumps(spec["match"]))
            chunk = existing if existing is not None else source.copy()
            chunk.label = label
            doc.save()

            enabled = [c for c in chunk.cameras if c.enabled]
            print(f"  matching {len(enabled)} enabled cameras")

            t0 = time.time()
            chunk.matchPhotos(**spec["match"])
            t_match = time.time() - t0
            print(f"  matchPhotos: {t_match/60:.1f} min")
            doc.save()

            t0 = time.time()
            chunk.alignCameras(adaptive_fitting=True)
            t_align = time.time() - t0
            print(f"  alignCameras: {t_align/60:.1f} min")
            doc.save()

            rings = per_ring_aligned(chunk)
            aligned = sum(r["aligned"] for r in rings.values())
            total = sum(r["enabled"] for r in rings.values())
            rep = reprojection_stats(chunk)

            entry = {
                "params": spec["match"],
                "match_min": round(t_match / 60, 2),
                "align_min": round(t_align / 60, 2),
                "aligned": aligned,
                "enabled": total,
                "aligned_pct": round(100.0 * aligned / max(total, 1), 1),
                "rings": rings,
                "reprojection": rep,
                "markers": marker_stats(chunk),
                "meta": {
                    k: chunk.meta[k]
                    for k in list(chunk.meta.keys())
                    if "sigma" in k.lower() or "error" in k.lower()
                },
            }
            report[label] = entry

            print(f"  ALIGNED {aligned}/{total} ({entry['aligned_pct']}%)")
            for ring, r in sorted(rings.items()):
                flag = "" if r["aligned"] == r["enabled"] else "  <-- gaps"
                print(
                    f"    {ring:14} {r['aligned']:>3}/{r['enabled']:<3}{flag}"
                )
                if r["failed"]:
                    print(f"        failed: {r['failed']}")
            print(f"  reprojection: {rep}")
            if entry["meta"]:
                print(f"  meta: {entry['meta']}")

            with open(REPORT, "w") as fh:
                json.dump(report, fh, indent=2)
            doc.save()

    print("\n=== SUMMARY ===")
    for label, e in report.items():
        rep = e.get("reprojection") or {}
        print(
            f"{label:26} {e['aligned']:>3}/{e['enabled']:<3} "
            f"({e['aligned_pct']:>5.1f}%)  rms={rep.get('rms_px','-')}  "
            f"tie={rep.get('tie_points','-')}  "
            f"match={e['match_min']}min align={e['align_min']}min"
        )
    print("WROTE", REPORT)
    print("DONE")


main()
