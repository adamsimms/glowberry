"""Step A: build the project, import the three remounts, attach masks, find markers.

Creates berry04_three_chunks.psx with one chunk per remount (upright, inverted,
sideways), a camera group per ring so later steps can address the NO-TARGETS
pass directly, a single calibration group per chunk, the colour-derived masks
attached from disk, and 12-bit circular targets detected.

Masks are attached with generateMasks(masking_mode=MaskingModeFile) because
Chunk.importMasks does not exist in 2.3.x.

Markers are detected with filter_mask=False on purpose: the masks hide
everything except the berry, and the targets sit outside it.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_a_import.py
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
REPORT = os.path.join(bc.WORK, "reports", "step_a.json")
MARKER_TOLERANCE = 50  # matches the known-good 40-frame baseline


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    if os.path.exists(bc.PROJECT):
        print(f"REFUSING: project already exists at {bc.PROJECT}")
        print("Move or delete it first if you intend to rebuild from scratch.")
        return

    doc = Metashape.Document()
    doc.save(bc.PROJECT)  # save early so later doc.save() calls are cheap
    print("project:", bc.PROJECT)

    report = {"project": bc.PROJECT, "chunks": {}}

    for r_label, r_dir in bc.REMOUNTS:
        chunk = doc.addChunk()
        chunk.label = r_label
        c_report = {"rings": {}, "source": r_dir}
        print(f"\n=== chunk {r_label} ({r_dir}) ===")

        for ring_label, ring_sub in bc.RINGS:
            photos = bc.ring_photos(r_dir, ring_sub)
            if not photos:
                c_report["rings"][ring_label] = {"error": "no photos"}
                continue

            # Metashape keeps chunk.cameras sorted by label, and each ring's
            # frame numbers are lower than the previous ring's, so new cameras
            # land at the front rather than the end. Slicing by index assigns
            # the wrong cameras to the wrong ring group; diff on keys instead.
            before_keys = {c.key for c in chunk.cameras}
            chunk.addPhotos(photos)
            added = [c for c in chunk.cameras if c.key not in before_keys]

            # One camera group per ring, so the NO-TARGETS pass stays addressable.
            group = chunk.addCameraGroup()
            group.label = ring_label
            for cam in added:
                cam.group = group

            c_report["rings"][ring_label] = {
                "offered": len(photos),
                "added": len(added),
                "labels": sorted(c.label for c in added),
            }
            print(f"  ring {ring_label}: offered {len(photos)}, added {len(added)}")
            if len(added) != len(photos):
                got = {c.label for c in added}
                missing = [
                    os.path.basename(p)
                    for p in photos
                    if os.path.splitext(os.path.basename(p))[0] not in got
                ]
                c_report["rings"][ring_label]["missing"] = missing
                print(f"    NOT ADDED: {missing}")

        # Force a single calibration group: same body, lens, and distance
        # throughout, so the bundle should solve one shared calibration.
        sensors = chunk.sensors
        c_report["sensors_before"] = len(sensors)
        if len(sensors) > 1:
            primary = sensors[0]
            for cam in chunk.cameras:
                cam.sensor = primary
            for extra in list(sensors)[1:]:
                chunk.remove(extra)
        c_report["sensors_after"] = len(chunk.sensors)
        print(
            f"  calibration groups: {c_report['sensors_before']} -> "
            f"{c_report['sensors_after']}"
        )

        c_report["cameras"] = len(chunk.cameras)
        doc.save()

        # Attach masks from disk.
        print("  attaching masks from", MASK_DIR)
        template = os.path.join(MASK_DIR, "{filename}_mask.png")
        try:
            chunk.generateMasks(
                path=template,
                masking_mode=Metashape.MaskingModeFile,
                mask_operation=Metashape.MaskOperationReplacement,
            )
        except Exception as exc:
            print("  generateMasks(File) raised:", exc)
            c_report["mask_error"] = repr(exc)

        with_mask = [c for c in chunk.cameras if c.mask is not None]
        without = [c.label for c in chunk.cameras if c.mask is None]
        c_report["masked"] = len(with_mask)
        c_report["unmasked"] = without
        print(f"  masks attached: {len(with_mask)}/{len(chunk.cameras)}")
        if without:
            print(f"  UNMASKED: {without}")

        # Disable cameras with no mask: unmasked frames would drag whole-frame
        # background into matching, which is the failure mode masks exist to stop.
        for cam in chunk.cameras:
            if cam.mask is None:
                cam.enabled = False
        c_report["disabled"] = without

        doc.save()

        # Only the targeted rings carry targets. Running detection over the
        # NO-TARGETS pass costs a full 100 MP decode per frame to find nothing.
        targeted = [
            c.key
            for c in chunk.cameras
            if c.group is not None and c.group.label != "m5_notargets"
        ]
        print(
            f"  detecting 12-bit circular targets on {len(targeted)} targeted "
            f"frames (tolerance={MARKER_TOLERANCE})"
        )
        chunk.detectMarkers(
            target_type=Metashape.TargetType.CircularTarget12bit,
            tolerance=MARKER_TOLERANCE,
            filter_mask=False,
            cameras=targeted,
        )
        marks = {}
        for m in chunk.markers:
            marks[m.label] = sum(
                1 for cam, proj in m.projections.items() if proj is not None
            )
        c_report["markers"] = marks
        print(f"  markers: {len(marks)} -> {marks}")

        report["chunks"][r_label] = c_report
        doc.save()

    doc.save()

    totals = {
        "cameras": sum(c.get("cameras", 0) for c in report["chunks"].values()),
        "masked": sum(c.get("masked", 0) for c in report["chunks"].values()),
        "disabled": sum(
            len(c.get("disabled", [])) for c in report["chunks"].values()
        ),
    }
    report["totals"] = totals

    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=2)

    print("\n=== TOTALS ===")
    print(json.dumps(totals, indent=2))
    print("WROTE", REPORT)
    print("DONE")


main()
