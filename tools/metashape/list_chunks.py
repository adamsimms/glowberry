"""List every chunk in the project with its measured state.

Ground truth check before the merge. Reads the project rather than any report
file, so a stale or wrongly cached report cannot pass unnoticed.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r list_chunks.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import berry_common as bc  # noqa: E402

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

bc.add_user_packages()

import Metashape  # noqa: E402


def n_points(chunk):
    tp = chunk.tie_points
    if tp is None or tp.points is None:
        return 0
    return sum(1 for p in tp.points if p.valid)


def rms_px(chunk):
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
    return " ".join(f"{k}:{v[0]}/{v[1]}" for k, v in sorted(out.items()))


def main():
    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=True, ignore_lock=True)
    print(f"{len(doc.chunks)} chunks in {bc.PROJECT}\n")
    print(
        f"{'chunk':34} {'cams':>5} {'align':>6} {'off':>4} {'points':>7} "
        f"{'rms':>7} {'sens':>5}  rings"
    )
    for c in doc.chunks:
        cams = len(c.cameras)
        en = [x for x in c.cameras if x.enabled]
        al = sum(1 for x in en if x.transform)
        print(
            f"{c.label:34} {cams:>5} {al:>6} {cams-len(en):>4} "
            f"{n_points(c):>7} {str(rms_px(c)):>7} {len(c.sensors):>5}  "
            f"{rings(c)}"
        )
    print("\nDONE")


main()
