"""Step F7: regenerate masks from the mesh and compare them to the colour ones.

This closes out the masking decision to do both: colour-threshold masks were
built for all 446 frames up front, and the plan was always to regenerate from
the mesh once one existed and compare.

The comparison is worth more than a choice of mask. The colour masks come from
the photographs alone, by hue and saturation, and know nothing about geometry.
A model mask is the mesh's silhouette projected into the same camera. Their
overlap is therefore an independent check that the merged mesh agrees with the
images: a mesh that were wrongly registered or inflated would project a
silhouette that the colour masks disagree with, in a way that no amount of
internal reprojection error would reveal.

So the intersection over union per camera is read as a mesh check, not just a
mask diff. High agreement across cameras from both remounts means the surface
is right in both. Systematically smaller model masks would mean the mesh is
eroded, larger would mean it is inflated.

Colour masks are saved before being replaced, so the comparison is possible
and the originals are recoverable.

Env:
    BERRY_MASK_SAMPLES=10   cameras per remount to compare
    BERRY_MASK_APPLY=0      1 to keep the model masks, 0 to restore colour ones

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f7_masks.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import berry_common as bc  # noqa: E402

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

bc.add_user_packages()

import numpy as np  # noqa: E402
import Metashape  # noqa: E402

MERGED = "merged_up_inv"
SAMPLES = int(os.environ.get("BERRY_MASK_SAMPLES", "10"))
APPLY = os.environ.get("BERRY_MASK_APPLY", "0") == "1"
# Restore the saved colour masks and do nothing else, for recovering after a
# failed restore without regenerating the model masks.
RESTORE_ONLY = os.environ.get("BERRY_MASK_RESTORE_ONLY") == "1"
SAVE_DIR = os.path.join(bc.WORK, "masks_colour_backup")
REPORT = os.path.join(bc.WORK, "reports", "step_f7_masks.json")
DOWNSCALE = 4  # comparison only; full resolution adds nothing to an IoU


def mask_array(cam, downscale=DOWNSCALE):
    """Boolean mask for a camera, downscaled, or None."""
    if cam.mask is None:
        return None
    img = cam.mask.image()
    if downscale > 1:
        img = img.resize(img.width // downscale, img.height // downscale)
    buf = np.frombuffer(img.convert("RGB", "U8").tostring(), dtype=np.uint8)
    a = buf.reshape(img.height, img.width, 3)
    return a[:, :, 0] > 127


def restore_colour(chunk, doc):
    """Put the saved colour masks back on any camera that has a backup.

    The mask has to be loaded into a Mask object before it is assigned.
    Assigning an empty Mask first and loading through cam.mask reads back None.
    """
    restored = 0
    for cam in chunk.cameras:
        p = os.path.join(SAVE_DIR, f"{cam.label}_colour_mask.png")
        if not os.path.exists(p):
            continue
        m = Metashape.Mask()
        m.load(p)
        cam.mask = m
        restored += 1
    doc.save()
    return restored


def main():
    bc.ensure_dirs()
    os.makedirs(SAVE_DIR, exist_ok=True)
    print("Metashape", Metashape.app.version)

    if RESTORE_ONLY:
        doc = Metashape.Document()
        doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
        chunk = next((c for c in doc.chunks if c.label == MERGED), None)
        if chunk is None:
            print(f"no chunk {MERGED}")
            return
        print(f"restore only: put back {restore_colour(chunk, doc)} colour "
              f"masks")
        print("DONE")
        return

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    chunk = next((c for c in doc.chunks if c.label == MERGED), None)
    if chunk is None:
        print(f"no chunk {MERGED}")
        return
    if chunk.model is None:
        print("no model to project; run step_f5/f6 first")
        return

    solved = [c for c in chunk.cameras if c.transform and c.enabled]
    print(f"{MERGED}: {len(solved)} solved cameras, "
          f"{sum(1 for c in chunk.cameras if c.mask is not None)} masked")

    # Sample evenly across both remounts, by camera group, so the check covers
    # upright and inverted rather than whichever happens to sort first.
    groups = {}
    for c in solved:
        groups.setdefault(c.group.label if c.group else "none", []).append(c)
    sample = []
    for g, cams in sorted(groups.items()):
        step = max(1, len(cams) // max(1, SAMPLES))
        sample.extend(cams[::step][:SAMPLES])
    print(f"comparing {len(sample)} cameras across groups "
          f"{sorted(groups)}")

    print("\nsaving colour masks before they are replaced...")
    colour = {}
    for cam in sample:
        m = mask_array(cam)
        if m is None:
            continue
        colour[cam.label] = m
        path = os.path.join(SAVE_DIR, f"{cam.label}_colour_mask.png")
        if not os.path.exists(path):
            cam.mask.image().save(path)
    print(f"  {len(colour)} colour masks captured")

    print("\ngenerating masks from the model...")
    chunk.generateMasks(
        masking_mode=Metashape.MaskingMode.MaskingModeModel,
        mask_operation=Metashape.MaskOperation.MaskOperationReplacement,
        cameras=[c for c in sample],
    )
    doc.save()

    rows = []
    for cam in sample:
        if cam.label not in colour:
            continue
        a = colour[cam.label]
        b = mask_array(cam)
        if b is None or b.shape != a.shape:
            continue
        inter = np.logical_and(a, b).sum()
        union = np.logical_or(a, b).sum()
        if union == 0:
            continue
        rows.append({
            "camera": cam.label,
            "group": cam.group.label if cam.group else "none",
            "iou": float(inter / union),
            "colour_px": int(a.sum()),
            "model_px": int(b.sum()),
            "model_over_colour": float(b.sum() / max(a.sum(), 1)),
        })

    if not rows:
        print("no comparable pairs")
        return

    iou = np.array([r["iou"] for r in rows])
    ratio = np.array([r["model_over_colour"] for r in rows])
    print(f"\n=== mesh silhouette vs colour mask, {len(rows)} cameras ===")
    print(f"  IoU:   median {np.median(iou):.4f}, min {iou.min():.4f}, "
          f"max {iou.max():.4f}")
    print(f"  model area / colour area: median {np.median(ratio):.4f} "
          f"(1.0 means the same size)")
    for r in sorted(rows, key=lambda r: r["iou"])[:5]:
        print(f"    worst: {r['camera']} (ring {r['group']}) IoU "
              f"{r['iou']:.4f}, area ratio {r['model_over_colour']:.3f}")

    med = float(np.median(iou))
    medr = float(np.median(ratio))
    if med > 0.9:
        verdict = ("the mesh silhouette matches the photographs closely, so "
                   "the merged surface is confirmed against the images")
    elif med > 0.75:
        verdict = ("broad agreement, with edge differences; acceptable but "
                   "worth looking at the worst cameras")
    else:
        verdict = ("poor agreement: the mesh does not project to where the "
                   "berry actually is in these frames")
    print(f"  VERDICT: {verdict}")
    if medr < 0.93:
        print("  the model masks are systematically smaller, so the mesh is "
              "eroded relative to the real silhouette")
    elif medr > 1.07:
        print("  the model masks are systematically larger, so the mesh is "
              "inflated relative to the real silhouette")

    if not APPLY:
        print("\nrestoring the colour masks (BERRY_MASK_APPLY=1 to keep model "
              "masks)...")
        print(f"  restored {restore_colour(chunk, doc)} masks")
    else:
        print("\nkeeping the model masks on the sampled cameras")

    with open(REPORT, "w") as fh:
        json.dump({
            "chunk": MERGED, "cameras_compared": len(rows),
            "iou_median": med, "iou_min": float(iou.min()),
            "area_ratio_median": medr, "applied": APPLY,
            "per_camera": rows,
        }, fh, indent=2)
    print("WROTE", REPORT)
    print("DONE")


main()
