"""Generate berry-only masks for every frame, written as PNG files.

Approach
--------
The berry is the only orange, saturated object in an otherwise neutral scene,
so hue plus saturation isolates it regardless of turntable rotation. Two extra
constraints make it robust:

1. The camera is fixed within a ring, so the berry occupies a near-constant
   image position. Each ring gets an anchor (median berry centroid over sample
   frames) and component selection is tied to that anchor. Without this, frames
   where a target card occludes the berry can latch onto the violet fringe along
   the paper edge or onto warm noise in the shadow under the turntable.
2. Candidate blobs must be berry-plausible in size and aspect.

Polarity is verified by probe_mask_polarity.py: white keeps, black masks out.

Masks are written to a temp path and renamed into place, so an existing file
always means a complete file and the run is safely resumable.

Env knobs:
    BERRY_MASK_LIMIT=n   process only the first n frames per ring (smoke test)
    BERRY_MASK_RINGS=a,b restrict to ring keys, e.g. "upright/40,upright/m5"
    BERRY_MASK_FORCE=1   regenerate masks that already exist

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r make_berry_masks.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import berry_common as bc  # noqa: E402

bc.add_user_packages()

import numpy as np  # noqa: E402
import Metashape  # noqa: E402

SUB = 8  # analysis subsample factor for locating the berry
ANCHOR_SAMPLES = 8
ANCHOR_RADIUS = 180  # analysed px; ~1440 px full res
MIN_W, MAX_W = 25, 220  # analysed px, berry width plausibility
MAX_ASPECT = 2.6
BBOX_MARGIN = 24  # analysed px added around the bbox before full-res refine
MASK_DIR = os.path.join(bc.WORK, "masks")
REPORT = os.path.join(bc.WORK, "reports", "mask_generation.json")

LIMIT = int(os.environ.get("BERRY_MASK_LIMIT", "0")) or None
ONLY = [s for s in os.environ.get("BERRY_MASK_RINGS", "").split(",") if s]
FORCE = os.environ.get("BERRY_MASK_FORCE") == "1"


# Long run watched through a log file, so make progress visible as it happens
# rather than in 8 KB block-buffered bursts.
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass


def load_rgb(path):
    img = Metashape.Image.open(path)
    rgb = img.convert("RGB", "U8")
    arr = np.frombuffer(rgb.tostring(), dtype=np.uint8).reshape(
        rgb.height, rgb.width, 3
    )
    return arr, rgb.width, rgb.height


def blob_candidates(small):
    """All berry-plausible components in the subsampled frame."""
    raw = bc.berry_pixels(small, np)
    if not raw.any():
        return []
    _, labelled = bc.largest_component(raw, np)
    out = []
    ids, counts = np.unique(labelled[labelled > 0], return_counts=True)
    for lid, cnt in zip(ids.tolist(), counts.tolist()):
        if cnt < 200:  # too small to be the berry at 1/8
            continue
        ys, xs = np.nonzero(labelled == lid)
        w = int(xs.max() - xs.min() + 1)
        h = int(ys.max() - ys.min() + 1)
        if not (MIN_W <= w <= MAX_W) or not (MIN_W <= h <= MAX_W):
            continue
        if max(w, h) / max(min(w, h), 1) > MAX_ASPECT:
            continue
        out.append(
            {
                "n": int(cnt),
                "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                "wh": [w, h],
                "centroid": [float(xs.mean()), float(ys.mean())],
            }
        )
    return out


def ring_anchor(photos):
    """Median berry centroid across evenly spaced sample frames."""
    n = min(ANCHOR_SAMPLES, len(photos))
    idx = [int(round(i * (len(photos) - 1) / max(n - 1, 1))) for i in range(n)]
    pts = []
    for i in idx:
        try:
            arr, _, _ = load_rgb(photos[i])
            cands = blob_candidates(arr[::SUB, ::SUB])
            if cands:
                best = max(cands, key=lambda c: c["n"])
                pts.append(best["centroid"])
        except Exception:
            continue
    if not pts:
        return None
    a = np.array(pts)
    return [float(np.median(a[:, 0])), float(np.median(a[:, 1]))]


def refine_full(arr, bbox_small):
    """Full-resolution berry mask inside the located bounding box."""
    h, w = arr.shape[:2]
    x0 = max(0, (bbox_small[0] - BBOX_MARGIN) * SUB)
    y0 = max(0, (bbox_small[1] - BBOX_MARGIN) * SUB)
    x1 = min(w, (bbox_small[2] + BBOX_MARGIN + 1) * SUB)
    y1 = min(h, (bbox_small[3] + BBOX_MARGIN + 1) * SUB)

    patch = arr[y0:y1, x0:x1]
    keep = bc.berry_pixels(patch, np)

    # Fill single-pixel pits and close the drupelet boundary slightly so the
    # silhouette is not eaten away by specular highlights on the surface.
    for _ in range(2):
        padded = np.pad(keep, 1, mode="constant", constant_values=False)
        neigh = (
            padded[:-2, 1:-1].astype(np.uint8)
            + padded[2:, 1:-1]
            + padded[1:-1, :-2]
            + padded[1:-1, 2:]
        )
        keep = keep | (neigh >= 3)

    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y0:y1, x0:x1][keep] = 255
    return mask, int(keep.sum()), [x0, y0, x1, y1]


def main():
    bc.ensure_dirs()
    os.makedirs(MASK_DIR, exist_ok=True)
    print("Metashape", Metashape.app.version, "| numpy", np.__version__)
    print(f"sat>{bc.BERRY_SAT} hue[{bc.BERRY_HUE_LO},{bc.BERRY_HUE_HI}] sub={SUB}")
    if LIMIT:
        print(f"SMOKE TEST: first {LIMIT} frames per ring")
    if ONLY:
        print(f"restricted to rings: {ONLY}")

    report = {"rings": {}, "flagged": []}
    t_start = time.time()
    total = 0

    for r_label, r_dir, ring_label, ring_sub, photos in bc.all_rings():
        key = f"{r_label}/{ring_label}"
        if ONLY and key not in ONLY:
            continue
        if not photos:
            report["rings"][key] = {"error": "no photos"}
            continue

        anchor = ring_anchor(photos)
        if anchor is None:
            report["rings"][key] = {"error": "no anchor found"}
            report["flagged"].append(f"{key}: NO ANCHOR")
            print(f"{key}: NO ANCHOR, skipping")
            continue
        print(f"\n{key}: anchor={[round(v,1) for v in anchor]} n={len(photos)}")

        work = photos[:LIMIT] if LIMIT else photos
        ring_out = {"anchor": anchor, "n_photos": len(photos), "frames": {}}

        for path in work:
            name = os.path.splitext(os.path.basename(path))[0]
            out_png = os.path.join(MASK_DIR, f"{name}_mask.png")
            if not FORCE and os.path.exists(out_png):
                ring_out["frames"][name] = {"skipped": "already exists"}
                continue
            t0 = time.time()
            try:
                arr, w, h = load_rgb(path)
                cands = blob_candidates(arr[::SUB, ::SUB])
                if not cands:
                    ring_out["frames"][name] = {"error": "no candidate blob"}
                    report["flagged"].append(f"{key}/{name}: no blob")
                    print(f"  {name}: NO BLOB")
                    continue

                def dist(c):
                    return (
                        (c["centroid"][0] - anchor[0]) ** 2
                        + (c["centroid"][1] - anchor[1]) ** 2
                    ) ** 0.5

                near = [c for c in cands if dist(c) <= ANCHOR_RADIUS]
                if not near:
                    ring_out["frames"][name] = {
                        "error": "no blob near anchor",
                        "nearest": round(min(dist(c) for c in cands), 1),
                    }
                    report["flagged"].append(f"{key}/{name}: off-anchor")
                    print(f"  {name}: OFF-ANCHOR (nearest {min(dist(c) for c in cands):.0f})")
                    continue

                chosen = max(near, key=lambda c: c["n"])
                mask, npx, box = refine_full(arr, chosen["bbox"])

                # Write then rename, so a half-written PNG never looks complete
                # to a resumed run.
                tmp_png = out_png + ".tmp.png"
                mimg = Metashape.Image.fromstring(
                    mask.tobytes(), w, h, "I", "U8"
                )
                mimg.save(tmp_png)
                os.replace(tmp_png, out_png)

                ring_out["frames"][name] = {
                    "px_full": npx,
                    "bbox_small": chosen["bbox"],
                    "wh_small": chosen["wh"],
                    "dist_to_anchor": round(dist(chosen), 1),
                    "refine_box_full": box,
                    "secs": round(time.time() - t0, 2),
                }
                total += 1
                print(
                    f"  {name}: {chosen['wh']} px_full={npx} "
                    f"d={dist(chosen):.0f} {time.time()-t0:.1f}s"
                )
            except Exception as exc:
                ring_out["frames"][name] = {"error": repr(exc)}
                report["flagged"].append(f"{key}/{name}: {exc}")
                print(f"  {name}: ERROR {exc}")

        report["rings"][key] = ring_out

    report["total_masks"] = total
    report["elapsed_s"] = round(time.time() - t_start, 1)
    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=2)

    print(f"\nmasks written: {total} in {report['elapsed_s']}s")
    print(f"flagged: {len(report['flagged'])}")
    for f in report["flagged"][:40]:
        print("  ", f)
    print("WROTE", REPORT)
    print("DONE")


main()
