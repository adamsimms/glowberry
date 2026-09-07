"""Fold the three re-exported frames into the project and disable B_2750.

B_2254, B_2255 and B_2256 were truncated on first export and excluded from
Step A. They have been re-exported and now read fine, so they join the sideways
NO-TARGETS ring: added to the chunk, put in the right camera group, bound to the
chunk's single calibration group, masked, and quality-scored.

B_2750 is disabled. It is the only genuinely defocused frame in the set, and a
lone outlier at 0.317 against its own ring's p10 of 0.635. The other 18 frames
scoring below 0.5 were checked at native resolution and are sharp; the quality
metric is confounded by how much textured berry a view presents.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_b2_patch.py
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

import Metashape  # noqa: E402

MASK_DIR = os.path.join(bc.WORK, "masks")
REPORT = os.path.join(bc.WORK, "reports", "step_b2.json")

NEW_FRAMES = ["B_2254", "B_2255", "B_2256"]
TARGET_CHUNK = "sideways"
TARGET_GROUP = "m5_notargets"
TARGET_DIR = os.path.join(bc.BERRY, "TIFF-CHUNK-03", "-5", "NO-TARGETS")

DISABLE = {"upright": ["B_2750"]}


def quality_of(cam):
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

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    print("opened", bc.PROJECT)

    report = {}
    chunks = {c.label: c for c in doc.chunks}

    # --- add the re-exported frames -------------------------------------
    chunk = chunks[TARGET_CHUNK]
    existing = {c.label for c in chunk.cameras}
    to_add = []
    for name in NEW_FRAMES:
        if name in existing:
            print(f"{name}: already in chunk, skipping")
            continue
        path = os.path.join(TARGET_DIR, f"{name}.tif")
        if not bc.is_valid_photo(path):
            print(f"{name}: STILL INVALID, refusing to add")
            continue
        to_add.append(path)

    if to_add:
        before_keys = {c.key for c in chunk.cameras}
        chunk.addPhotos(to_add)
        added = [c for c in chunk.cameras if c.key not in before_keys]
        print(f"added {len(added)}: {[c.label for c in added]}")

        group = next(
            (g for g in chunk.camera_groups if g.label == TARGET_GROUP), None
        )
        if group is None:
            group = chunk.addCameraGroup()
            group.label = TARGET_GROUP
        sensor = chunk.sensors[0]
        for cam in added:
            cam.group = group
            cam.sensor = sensor
        print(f"assigned to group '{TARGET_GROUP}' and the single calibration group")

        doc.save()

        chunk.generateMasks(
            path=os.path.join(MASK_DIR, "{filename}_mask.png"),
            masking_mode=Metashape.MaskingModeFile,
            mask_operation=Metashape.MaskOperationReplacement,
            cameras=[c.key for c in added],
        )
        for cam in added:
            print(f"  {cam.label}: mask={'yes' if cam.mask else 'NO'}")

        chunk.analyzeImages(filter_mask=True, cameras=[c.key for c in added])
        for cam in added:
            print(f"  {cam.label}: quality={quality_of(cam)}")

        report["added"] = {
            c.label: {
                "mask": c.mask is not None,
                "quality": quality_of(c),
                "group": c.group.label if c.group else None,
            }
            for c in added
        }
        doc.save()
    else:
        report["added"] = {}

    # --- collapse calibration groups ------------------------------------
    # addPhotos creates a fresh sensor for the incoming frames. Reassigning the
    # cameras is not enough: the now-unused sensor stays on the chunk and shows
    # up as a second calibration group, which would solve its own intrinsics.
    report["sensor_cleanup"] = {}
    for chunk in doc.chunks:
        if len(chunk.sensors) <= 1:
            continue
        primary = chunk.sensors[0]
        for cam in chunk.cameras:
            cam.sensor = primary
        orphans = [s for s in list(chunk.sensors) if s != primary]
        for s in orphans:
            chunk.remove(s)
        report["sensor_cleanup"][chunk.label] = {
            "removed": len(orphans),
            "now": len(chunk.sensors),
        }
        print(
            f"{chunk.label}: removed {len(orphans)} orphan sensor(s), "
            f"now {len(chunk.sensors)} calibration group"
        )
    doc.save()

    # --- disable the defocused frame ------------------------------------
    report["disabled"] = {}
    for chunk_label, labels in DISABLE.items():
        ch = chunks[chunk_label]
        for cam in ch.cameras:
            if cam.label in labels:
                cam.enabled = False
                report["disabled"][cam.label] = {
                    "chunk": chunk_label,
                    "quality": quality_of(cam),
                    "reason": "defocused; lone outlier in its ring",
                }
                print(f"disabled {chunk_label}/{cam.label} (q={quality_of(cam)})")

    doc.save()

    # --- final state -----------------------------------------------------
    print("\n=== project state ===")
    totals = {"cameras": 0, "enabled": 0, "masked": 0}
    state = {}
    for chunk in doc.chunks:
        cams = chunk.cameras
        masked = sum(1 for c in cams if c.mask is not None)
        enabled = sum(1 for c in cams if c.enabled)
        groups = {}
        for c in cams:
            g = c.group.label if c.group else "ungrouped"
            groups[g] = groups.get(g, 0) + 1
        state[chunk.label] = {
            "cameras": len(cams),
            "enabled": enabled,
            "masked": masked,
            "disabled": [c.label for c in cams if not c.enabled],
            "groups": groups,
            "markers": len(chunk.markers),
            "sensors": len(chunk.sensors),
        }
        totals["cameras"] += len(cams)
        totals["enabled"] += enabled
        totals["masked"] += masked
        print(
            f"{chunk.label}: {len(cams)} cameras, {enabled} enabled, "
            f"{masked} masked, {len(chunk.markers)} markers, "
            f"{len(chunk.sensors)} calib group(s)"
        )
        print(f"   groups: {groups}")
        if state[chunk.label]["disabled"]:
            print(f"   disabled: {state[chunk.label]['disabled']}")

    report["state"] = state
    report["totals"] = totals
    print(f"\nTOTALS: {totals}")

    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=2)
    print("WROTE", REPORT)
    print("DONE")


main()
