"""Step B: score image quality on the berry, not the background.

analyzeImages(filter_mask=True) is the whole point here: the berry is roughly
0.3% of an 11656x8742 frame, so an unmasked quality score would essentially
measure the sharpness of a blank wall. With the mask applied the score reflects
the subject.

Reports the distribution per chunk and ring and lists cameras below Agisoft's
0.5 guideline as candidates. Disables nothing: dropping frames from a thin ring
can open an angular gap, so that is a user decision.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_b_quality.py
"""

import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import berry_common as bc  # noqa: E402

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

bc.add_user_packages()

import Metashape  # noqa: E402

REPORT = os.path.join(bc.WORK, "reports", "step_b.json")
LOW_THRESHOLD = 0.5  # Agisoft's stated guideline for disabling a frame


def quality_of(cam):
    """Image/Quality as float, or None.

    Camera.meta is a Metashape.MetaData object, which supports item access but
    has no .get, and stores values as strings.
    """
    try:
        raw = cam.meta["Image/Quality"]
    except Exception:
        return None
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    if not os.path.exists(bc.PROJECT):
        print("NO PROJECT at", bc.PROJECT)
        return

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    print("opened", bc.PROJECT)

    report = {"threshold": LOW_THRESHOLD, "chunks": {}}

    for chunk in doc.chunks:
        todo = [c for c in chunk.cameras if quality_of(c) is None]
        if todo:
            print(
                f"\n=== {chunk.label}: analyzing {len(todo)}/"
                f"{len(chunk.cameras)} frames ==="
            )
            # Score every camera, including the disabled one, so the report is
            # complete; enabling decisions stay with the user.
            chunk.analyzeImages(filter_mask=True, cameras=[c.key for c in todo])
            doc.save()
        else:
            print(f"\n=== {chunk.label}: already scored, reusing ===")

        rings = {}
        for cam in chunk.cameras:
            ring = cam.group.label if cam.group is not None else "ungrouped"
            q = quality_of(cam)
            if q is None:
                rings.setdefault(ring, {}).setdefault("missing", []).append(cam.label)
                continue
            rings.setdefault(ring, {}).setdefault("scores", {})[cam.label] = q

        c_report = {}
        for ring, data in rings.items():
            scores = data.get("scores", {})
            if not scores:
                c_report[ring] = {"missing": data.get("missing", [])}
                continue
            v = sorted(scores.values())
            low = sorted(
                (n, round(s, 3)) for n, s in scores.items() if s < LOW_THRESHOLD
            )
            c_report[ring] = {
                "n": len(v),
                "min": round(v[0], 3),
                "p10": round(v[max(0, int(0.10 * len(v)) - 1)], 3),
                "median": round(st.median(v), 3),
                "max": round(v[-1], 3),
                "below_threshold": low,
                "missing": data.get("missing", []),
            }
            print(
                f"  {ring:14} n={len(v):>3} min={v[0]:.3f} "
                f"med={st.median(v):.3f} max={v[-1]:.3f} "
                f"below_{LOW_THRESHOLD}={len(low)}"
            )
            if low:
                print(f"      candidates: {low}")

        report["chunks"][chunk.label] = c_report

    doc.save()

    # Overall picture
    allv = []
    total_low = 0
    for cd in report["chunks"].values():
        for rd in cd.values():
            if "n" in rd:
                allv.append(rd["median"])
                total_low += len(rd["below_threshold"])
    report["summary"] = {
        "ring_medians": allv,
        "total_below_threshold": total_low,
    }

    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=2)
    print(f"\ntotal frames below {LOW_THRESHOLD}: {total_low}")
    print("WROTE", REPORT)
    print("DONE")


main()
