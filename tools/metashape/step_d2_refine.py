"""Step D part 2: recover unaligned cameras and tighten the solution.

Variant A aligned the two high rings perfectly (40: 38/38, 15: 37/37) but left
the low rings short (m5: 21/39, m5_notargets: 5/29) at rms 2.79 px. Low rings
see the wall and the targets edge-on, so once stationary points are filtered
they have little to match on.

Order matters here. Incremental alignment runs first, because gradual selection
would delete the weak tie points the stragglers depend on:

  1. alignCameras(cameras=unaligned, reset_alignment=False)
     Incremental pass. Existing matches and solved geometry act as a prior, so
     cameras that failed from a cold start can still resolve.
  2. Gradual selection and reoptimisation, moderate thresholds, each followed
     by optimizeCameras: reconstruction uncertainty, then projection accuracy,
     then reprojection error.
  3. One more incremental pass, now against the tightened solution.

Every stage is measured so a stage that makes things worse is visible rather
than silently accepted. Nothing is destructive: work happens on a copy named
<source>_refined.

Env:
    BERRY_REFINE_SOURCE=upright_A_nomask
    BERRY_REFINE_FORCE=1

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_d2_refine.py
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

SOURCE = os.environ.get("BERRY_REFINE_SOURCE", "upright_A_nomask")
FORCE = os.environ.get("BERRY_REFINE_FORCE") == "1"
REPORT = os.path.join(bc.WORK, "reports", "step_d2_refine.json")

# Moderate thresholds. This is a small object with ~39k points, so aggressive
# filtering would strip the low rings of what little support they have.
RECON_UNCERTAINTY = 15.0
PROJ_ACCURACY = 5.0
REPROJ_ERROR = 0.5
MAX_REMOVE_FRAC = 0.5  # refuse a filter pass that would delete over half


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


def reprojection_stats(chunk):
    tp = chunk.tie_points
    if tp is None or tp.points is None:
        return None
    points, projections = tp.points, tp.projections
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
            if pid < 0 or not points[pid].valid:
                continue
            reproj = camera.project(points[pid].coord)
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
        "points": len(points),
    }


def rings(chunk):
    out = {}
    for cam in chunk.cameras:
        if not cam.enabled:
            continue
        label = cam.group.label if cam.group else "ungrouped"
        d = out.setdefault(label, {"enabled": 0, "aligned": 0, "failed": []})
        d["enabled"] += 1
        if cam.transform:
            d["aligned"] += 1
        else:
            d["failed"].append(cam.label)
    return out


def snapshot(chunk, stage):
    r = rings(chunk)
    aligned = sum(v["aligned"] for v in r.values())
    total = sum(v["enabled"] for v in r.values())
    rep = reprojection_stats(chunk) or {}
    sigma = None
    keys = list(chunk.meta.keys())
    if "OptimizeCameras/sigma0" in keys:
        sigma = chunk.meta["OptimizeCameras/sigma0"]
    snap = {
        "stage": stage,
        "aligned": aligned,
        "enabled": total,
        "points": n_points(chunk),
        "rms_px": rep.get("rms_px"),
        "max_px": rep.get("max_px"),
        "sigma0": sigma,
        "rings": {k: f"{v['aligned']}/{v['enabled']}" for k, v in sorted(r.items())},
    }
    print(
        f"  [{stage}] aligned={aligned}/{total} points={snap['points']} "
        f"rms={snap['rms_px']} max={snap['max_px']} sigma0={sigma}"
    )
    print(f"      rings: {snap['rings']}")
    return snap


def unaligned(chunk):
    return [c for c in chunk.cameras if c.enabled and not c.transform]


def incremental(chunk, doc, stage):
    todo = unaligned(chunk)
    if not todo:
        print(f"  [{stage}] nothing unaligned")
        return 0
    print(f"  [{stage}] incremental align on {len(todo)} cameras")
    t0 = time.time()
    chunk.alignCameras(
        cameras=[c.key for c in todo],
        adaptive_fitting=True,
        reset_alignment=False,
    )
    gained = len(todo) - len(unaligned(chunk))
    print(f"      +{gained} in {(time.time()-t0)/60:.1f} min")
    doc.save()
    return gained


def gradual(chunk, doc, criterion_name, threshold):
    Filter = filter_class()
    if Filter is None:
        print("  no tie point Filter class, skipping gradual selection")
        return None
    criterion = getattr(Filter, criterion_name, None)
    if criterion is None:
        print(f"  no criterion {criterion_name}, skipping")
        return None

    before = n_points(chunk)
    f = Filter()
    f.init(chunk, criterion=criterion)
    # Never let one pass gut the cloud; back the threshold off instead.
    thr = threshold
    for _ in range(6):
        vals = [v for v in f.values if v > thr]
        if before and len(vals) / before > MAX_REMOVE_FRAC:
            thr *= 1.5
            continue
        break
    f.selectPoints(thr)
    doomed = sum(1 for p in chunk.tie_points.points if p.selected and p.valid)
    if before and doomed / before > MAX_REMOVE_FRAC:
        print(
            f"  [{criterion_name}] would remove {doomed}/{before}, over "
            f"{int(MAX_REMOVE_FRAC*100)}% cap, skipping"
        )
        return None
    f.removePoints(thr)
    after = n_points(chunk)
    chunk.optimizeCameras(adaptive_fitting=True)
    doc.save()
    print(
        f"  [{criterion_name}] thr={thr:g} removed {before-after} "
        f"({before} -> {after})"
    )
    return {"criterion": criterion_name, "threshold": thr, "before": before, "after": after}


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)

    src = next((c for c in doc.chunks if c.label == SOURCE), None)
    if src is None:
        print(f"no chunk {SOURCE}")
        return

    label = f"{SOURCE}_refined"
    existing = next((c for c in doc.chunks if c.label == label), None)
    if existing is not None:
        if not FORCE:
            print(f"{label} exists; set BERRY_REFINE_FORCE=1 to redo")
            return
        doc.remove(existing)

    print(f"\n=== refining {SOURCE} -> {label} ===")
    chunk = src.copy()
    chunk.label = label
    doc.save()

    history = [snapshot(chunk, "start")]

    incremental(chunk, doc, "pass1")
    history.append(snapshot(chunk, "after_incremental_1"))

    filters = []
    for name, thr in (
        ("ReconstructionUncertainty", RECON_UNCERTAINTY),
        ("ProjectionAccuracy", PROJ_ACCURACY),
        ("ReprojectionError", REPROJ_ERROR),
    ):
        res = gradual(chunk, doc, name, thr)
        if res:
            filters.append(res)
            history.append(snapshot(chunk, f"after_{name}"))

    incremental(chunk, doc, "pass2")
    history.append(snapshot(chunk, "final"))

    report = {}
    if os.path.exists(REPORT):
        try:
            report = json.load(open(REPORT))
        except Exception:
            report = {}
    report[label] = {"history": history, "filters": filters}
    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=2)
    doc.save()

    print("\n=== PROGRESSION ===")
    for h in history:
        print(
            f"{h['stage']:26} {h['aligned']:>3}/{h['enabled']:<3} "
            f"points={h['points']:>6} rms={h['rms_px']} max={h['max_px']}"
        )
    last = history[-1]
    print(f"\nfinal rings: {last['rings']}")
    print("WROTE", REPORT)
    print("DONE")


main()
