"""Step F2: merge the upright and inverted chunks into one block.

Runs only after verify_common_frame.py passes. That gate reported 100% combined
coverage, a 48.5% shared band, and the same fitted radius from either remount
alone to within 0.00%, so the two are in one frame and describe one berry.

Choices that matter, from the signature this build actually exposes rather
than the 2.2 docs:

  chunks takes chunk keys, not chunk objects and not positional indices. The
  signature says list[int], which is ambiguous, and the two differ in this
  project: upright_A_nomask_highonly sits at index 19 but has key 88. Passing
  positions selected an unrelated tuned chunk, reported "Merging 1 chunks" and
  died on "Null tie points". The keys are resolved back to labels and printed
  before the call, so a wrong identifier cannot pass silently.

  merge_tiepoints=False, and copy_depth_maps=True to compensate. Merging tie
  points is not available here: it looks for image pairs between the chunks
  and fails with "Empty pairs list", since the two remounts share no matches,
  which is the whole reason registration had to be solved on shape. Leaving
  the merged chunk without tie points would normally break buildDepthMaps,
  which picks neighbours by counting shared tie points, so step_f2 built the
  depth maps per remount beforehand and they are carried in finished. Fusion
  into one surface then happens geometrically in the common frame, joined by
  the registration rather than by imaginary shared features.

  merge_markers=False deliberately. Each remount used a different physical set
  of coded targets, so equal marker numbers across chunks are different points
  in space. Merging them would invent correspondences and drag the block.

  copy_masks=True, since the berry masks are what keep the background out of
  the depth maps.

No optimizeCameras, here or later. The two blocks share no tie points, so
their relative pose is held solely by the transform step_f1 applied. A bundle
adjustment would be free to drift them apart, and would quietly undo the
registration while reporting a lower residual.

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f2_merge.py
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

import numpy as np  # noqa: E402
import Metashape  # noqa: E402

UPRIGHT = "upright_A_nomask_highonly"
INVERTED = "inverted_A_nomask_highonly"
MERGED = "merged_up_inv"
FORCE = os.environ.get("BERRY_MERGE_FORCE") == "1"
# With merge_assets off, only one chunk's per-camera assets came across: 38 of
# 75 depth maps and 76 of 150 masks, all from upright. Each source chunk now
# holds two depth map sets, downscale 4 from the earlier cloud build and
# downscale 2 from step_f2, and only the default one travelled.
MERGE_ASSETS = os.environ.get("BERRY_MERGE_ASSETS", "1") == "1"

# Berry in world coordinates, from the combined sphere fit in the gate.
BERRY_CENTRE = np.array([-0.1001, 0.4213, -7.39])
BERRY_RADIUS = 0.10004
REGION_RADII = 2.5   # half-size of the region, in berry radii


def to_np(M):
    a = np.asarray(M, dtype=float)
    return a if a.ndim == 2 else a.reshape(4, 4)


def depth_maps_present(chunk):
    """How many cameras actually carry a depth map.

    Worth counting rather than assuming. Only about half the solved cameras
    produced one: ring 15 frames were dropped as having "no neighbors",
    because the gradual selection behind the _highonly alignment culled tie
    points until those cameras no longer shared the 50 common points
    buildDepthMaps requires. Coverage survives that, since the two remounts
    still cover the whole sphere, but the merge should not silently proceed on
    zero.
    """
    dm = getattr(chunk, "depth_maps", None)
    if dm is None:
        return 0
    n = 0
    for cam in chunk.cameras:
        try:
            if dm[cam] is not None:
                n += 1
        except Exception:
            pass
    return n


def describe(chunk, indent="  "):
    cams = [c for c in chunk.cameras if c.transform]
    enabled = [c for c in cams if c.enabled]
    masked = sum(1 for c in chunk.cameras if c.mask is not None)
    tp = chunk.tie_points
    npts = len(tp.points) if tp is not None and tp.points is not None else 0
    depths = depth_maps_present(chunk)
    groups = {}
    for c in chunk.cameras:
        g = c.group.label if c.group else "none"
        groups[g] = groups.get(g, 0) + 1
    print(f"{indent}{len(chunk.cameras)} cameras, {len(cams)} solved, "
          f"{len(enabled)} enabled, {masked} masked, {npts} tie points")
    print(f"{indent}{depths} cameras with depth maps")
    print(f"{indent}groups: {dict(sorted(groups.items()))}")
    return len(cams), masked, depths


def set_region(chunk):
    """Box the region on the berry, in chunk-internal coordinates."""
    T = to_np(chunk.transform.matrix)
    scale = float(np.linalg.norm(T[:3, 0]))
    inv = np.linalg.inv(T)
    c = inv @ np.append(BERRY_CENTRE, 1.0)
    half = BERRY_RADIUS * REGION_RADII / scale
    chunk.region.center = Metashape.Vector([float(c[0]), float(c[1]), float(c[2])])
    chunk.region.size = Metashape.Vector([2 * half] * 3)
    chunk.region.rot = Metashape.Matrix.Diag([1, 1, 1])
    print(f"  region centred on the berry, half-size {half:.4f} internal units "
          f"({REGION_RADII:g} berry radii)")


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)

    existing = next((c for c in doc.chunks if c.label == MERGED), None)
    if existing is not None:
        if not FORCE:
            print(f"{MERGED} already exists. Set BERRY_MERGE_FORCE=1 to rebuild.")
            return
        print(f"removing previous {MERGED}")
        doc.remove(existing)
        doc.save()

    by_label = {c.label: c for c in doc.chunks}
    for label in (UPRIGHT, INVERTED):
        if label not in by_label:
            print(f"missing chunk {label}")
            return

    source_depths = 0
    for label in (UPRIGHT, INVERTED):
        c = by_label[label]
        print(f"\n=== {label} (key {c.key}) ===")
        _, _, d = describe(c)
        source_depths += d
    if source_depths == 0:
        print("\nABORT: neither source chunk has depth maps, so there is "
              "nothing for copy_depth_maps to carry. Run step_f2_depth.py "
              "first.")
        return

    keys = [by_label[UPRIGHT].key, by_label[INVERTED].key]
    resolved = [c.label for c in doc.chunks if c.key in keys]
    print(f"\nmerging keys {keys}, which resolve to {resolved}")
    if sorted(resolved) != sorted([UPRIGHT, INVERTED]):
        print("  ABORT: keys do not resolve to the two intended chunks")
        return

    before = set(id(c) for c in doc.chunks)
    doc.mergeChunks(
        chunks=keys,
        copy_masks=True,
        merge_tiepoints=False,
        merge_markers=False,
        copy_depth_maps=True,
        copy_point_clouds=False,
        copy_models=False,
        merge_assets=MERGE_ASSETS,
    )

    new = [c for c in doc.chunks if id(c) not in before]
    if not new:
        print("mergeChunks produced no new chunk")
        return
    merged = new[-1]
    merged.label = MERGED
    print(f"\n=== {MERGED} ===")
    cams, masked, depths = describe(merged)

    expect = sum(
        len([c for c in by_label[l].cameras if c.transform])
        for l in (UPRIGHT, INVERTED)
    )
    if cams != expect:
        print(f"  WARNING: {cams} solved cameras, expected {expect}")
    else:
        print(f"  all {cams} solved cameras carried over")
    if masked < cams:
        print(f"  WARNING: only {masked} cameras have masks; the texture would "
              f"pick up background")
    if depths < source_depths:
        print(f"  WARNING: {depths} depth maps carried over but the sources "
              f"held {source_depths}; the mesh would be built on less than "
              f"was computed")
    else:
        print(f"  all {depths} depth maps carried over from the two remounts")

    set_region(merged)
    doc.save()
    print("\nsaved. Next: step_f3_mesh.py (depth maps at downscale=2, no "
          "optimizeCameras)")
    print("DONE")


main()
