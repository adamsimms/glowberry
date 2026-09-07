"""Step D part 3: lower the residual without losing any aligned camera.

step_d2_refine.py showed the trade directly: gradual selection cut rms from
2.79 px to 0.39 px but dropped aligned cameras from 116 to 97, because it
deletes the weak tie points that were the only support holding the low-ring
cameras in the solution.

The artist chose to keep every camera that aligned. So instead of applying
fixed thresholds and accepting whatever falls out, this walks each criterion
from loose to tight and keeps the tightest setting that costs no cameras:

  1. Incremental alignCameras(reset_alignment=False) first, which is free and
     recovered 15 cameras on upright. That sets the camera count to protect.
  2. For each criterion, try thresholds loose to tight. Each attempt runs on a
     copy, so a rejected attempt costs nothing. Accept while the camera count
     holds and the residual improves; stop that criterion at the first loss,
     since tighter can only be worse.

Chunk copies act as snapshots because removePoints cannot be undone. Rejected
trials are deleted to keep the project small.

Result per remount: <source>_tuned, with every camera from the incremental
pass still aligned at the best residual reachable without sacrifice.

BERRY_TUNE_SLACK allows a stated number of cameras to be sacrificed, so the
cost of the marginal low-ring cameras can be measured rather than argued about.
Slack 0 is the artist's keep-everything choice; running it again at slack 2
prices those last two cameras in residual.

BERRY_TUNE_RINGS restricts a chunk to named camera groups before tuning, so the
high-rings-only architecture can be priced on the same footing. Matching has
already run across all frames, so dropping the low rings needs no rematch.

Env:
    BERRY_TUNE_SOURCES=upright_A_nomask,inverted_A_nomask,sideways_A_nomask
    BERRY_TUNE_SLACK=0        cameras allowed to be lost
    BERRY_TUNE_RINGS=40,15    keep only these camera groups (default: all)
    BERRY_TUNE_SUFFIX=_tuned  output chunk suffix
    BERRY_TUNE_FORCE=1

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_d3_tune.py
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

SOURCES = [
    s for s in os.environ.get(
        "BERRY_TUNE_SOURCES",
        "upright_A_nomask,inverted_A_nomask,sideways_A_nomask",
    ).split(",") if s
]
FORCE = os.environ.get("BERRY_TUNE_FORCE") == "1"
SLACK = int(os.environ.get("BERRY_TUNE_SLACK", "0"))
SUFFIX = os.environ.get("BERRY_TUNE_SUFFIX", "_tuned")
RINGS = [s for s in os.environ.get("BERRY_TUNE_RINGS", "").split(",") if s]
REPORT = os.path.join(bc.WORK, "reports", "step_d3_tune.json")

# Loose to tight. The ladder stops at the first threshold that costs a camera.
LADDER = [
    ("ReconstructionUncertainty", [50, 30, 20, 15, 10]),
    ("ProjectionAccuracy", [20, 12, 8, 5, 3]),
    ("ReprojectionError", [2.0, 1.0, 0.7, 0.5, 0.3]),
]
RMS_TOLERANCE = 1.02  # reject a pass that makes the residual worse


def filter_class():
    for name in ("TiePoints", "PointCloud"):
        holder = getattr(Metashape, name, None)
        if holder is not None and hasattr(holder, "Filter"):
            return holder.Filter
    return None


def n_points(chunk):
    tp = chunk.tie_points
    if tp is None or tp.points is None:
        return 0
    return sum(1 for p in tp.points if p.valid)


def aligned(chunk):
    return sum(1 for c in chunk.cameras if c.enabled and c.transform)


def rings(chunk):
    out = {}
    for cam in chunk.cameras:
        if not cam.enabled:
            continue
        label = cam.group.label if cam.group else "ungrouped"
        d = out.setdefault(label, [0, 0])
        d[1] += 1
        if cam.transform:
            d[0] += 1
    return {k: f"{v[0]}/{v[1]}" for k, v in sorted(out.items())}


def rms_px(chunk):
    """RMS reprojection error over valid tie point projections."""
    tp = chunk.tie_points
    if tp is None or tp.points is None:
        return None
    points, projections = tp.points, tp.projections
    point_ids = [-1] * len(tp.tracks)
    for pid, p in enumerate(points):
        point_ids[p.track_id] = pid

    sq_sum = 0.0
    n = 0
    for camera in chunk.cameras:
        if not camera.transform:
            continue
        for proj in projections[camera]:
            pid = point_ids[proj.track_id]
            if pid < 0 or not points[pid].valid:
                continue
            reproj = camera.project(points[pid].coord)
            if reproj is None:
                continue
            err = (reproj - proj.coord).norm()
            sq_sum += err * err
            n += 1
    return round((sq_sum / n) ** 0.5, 4) if n else None


def tune(doc, source, label):
    Filter = filter_class()
    if Filter is None:
        print("  no tie point Filter class available, cannot tune")
        return None

    best = source.copy()
    best.label = label

    if RINGS:
        drop = [
            c for c in best.cameras
            if c.group is None or c.group.label not in RINGS
        ]
        print(f"  restricting to rings {RINGS}: removing {len(drop)} cameras")
        for c in drop:
            best.remove(c)
        # Rebalance the bundle over what is left before measuring anything.
        best.optimizeCameras(adaptive_fitting=True)
    doc.save()

    # Free cameras first: this sets the count we then refuse to go below.
    todo = [c for c in best.cameras if c.enabled and not c.transform]
    if todo:
        print(f"  incremental align on {len(todo)} unaligned cameras")
        best.alignCameras(
            cameras=[c.key for c in todo],
            adaptive_fitting=True,
            reset_alignment=False,
        )
        doc.save()

    start_aligned = aligned(best)
    floor = start_aligned - SLACK
    best_rms = rms_px(best)
    history = [{
        "stage": "baseline",
        "aligned": start_aligned,
        "points": n_points(best),
        "rms_px": best_rms,
        "rings": rings(best),
    }]
    print(
        f"  baseline: aligned={start_aligned} points={n_points(best)} "
        f"rms={best_rms}"
    )
    print(f"    rings: {history[0]['rings']}")
    print(f"  camera floor set at {floor} (slack {SLACK}); no pass may go below it")

    accepted = []
    for criterion_name, thresholds in LADDER:
        criterion = getattr(Filter, criterion_name, None)
        if criterion is None:
            print(f"  {criterion_name}: not available, skipping")
            continue
        for thr in thresholds:
            trial = best.copy()
            trial.label = f"{label}__trial"
            f = Filter()
            f.init(trial, criterion=criterion)
            before = n_points(trial)
            f.removePoints(thr)
            after = n_points(trial)
            if after == before:
                doc.remove(trial)
                continue
            if after == 0:
                print(f"  {criterion_name} thr={thr:g}: would empty the cloud, stop")
                doc.remove(trial)
                break
            trial.optimizeCameras(adaptive_fitting=True)
            n = aligned(trial)
            r = rms_px(trial)

            if n < floor:
                print(
                    f"  {criterion_name} thr={thr:g}: REJECT, aligned {n} < "
                    f"floor {floor} (would drop {floor - n} camera(s))"
                )
                doc.remove(trial)
                break
            if r is not None and best_rms is not None and r > best_rms * RMS_TOLERANCE:
                print(
                    f"  {criterion_name} thr={thr:g}: REJECT, rms worsened "
                    f"{best_rms} -> {r}"
                )
                doc.remove(trial)
                break

            print(
                f"  {criterion_name} thr={thr:g}: accept, points {before} -> "
                f"{after}, rms {best_rms} -> {r}, aligned {n}"
            )
            doc.remove(best)
            best = trial
            best.label = label
            best_rms = r
            accepted.append({
                "criterion": criterion_name, "threshold": thr,
                "points": after, "rms_px": r, "aligned": n,
            })
            doc.save()
        history.append({
            "stage": f"after_{criterion_name}",
            "aligned": aligned(best),
            "points": n_points(best),
            "rms_px": best_rms,
            "rings": rings(best),
        })

    doc.save()
    return {
        "history": history, "accepted": accepted, "floor": floor,
        "slack": SLACK, "start_aligned": start_aligned,
        "final_rms": best_rms, "final_aligned": aligned(best),
        "final_points": n_points(best), "final_rings": rings(best),
    }


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)

    report = {}
    if os.path.exists(REPORT):
        try:
            report = json.load(open(REPORT))
        except Exception:
            report = {}

    for name in SOURCES:
        src = next((c for c in doc.chunks if c.label == name), None)
        if src is None:
            print(f"\n{name}: NO SUCH CHUNK, skipping")
            continue
        label = f"{name}{SUFFIX}"

        existing = next((c for c in doc.chunks if c.label == label), None)
        if existing is not None and label in report and not FORCE:
            print(f"\n{label}: already tuned, skipping")
            continue
        if existing is not None:
            doc.remove(existing)
        for stale in [c for c in doc.chunks if c.label.endswith("__trial")]:
            doc.remove(stale)

        print(f"\n=== tuning {name} -> {label} ===")
        t0 = time.time()
        res = tune(doc, src, label)
        if res is None:
            continue
        res["minutes"] = round((time.time() - t0) / 60, 2)
        report[label] = res
        with open(REPORT, "w") as fh:
            json.dump(report, fh, indent=2)
        print(
            f"  FINAL aligned={res['final_aligned']} points={res['final_points']} "
            f"rms={res['final_rms']} ({res['minutes']} min)"
        )
        print(f"    rings: {res['final_rings']}")

    print("\n=== SUMMARY ===")
    for label, r in report.items():
        h0 = r["history"][0]
        print(
            f"{label:34} aligned={r['final_aligned']:>3} (floor {r['floor']})  "
            f"rms {h0['rms_px']} -> {r['final_rms']}  "
            f"points {h0['points']} -> {r['final_points']}"
        )
        print(f"{'':34} rings: {r['final_rings']}")
    print("WROTE", REPORT)
    print("DONE")


main()
