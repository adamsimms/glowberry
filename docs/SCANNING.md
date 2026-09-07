# Glowberry — scanning (photogrammetry of the provenance berry)

Process note and result for the photogrammetry spike ([#52](https://github.com/adamsimms/glowberry/issues/52)): a Pinchard's Island bakeapple captured and reconstructed as the **ancestor file**. Companion to [`BRIEF.md`](BRIEF.md) and [`MATERIALS.md`](MATERIALS.md).

The concept frame is in the issue: the ancestor is born where picking still means return, and Montreal only rematerializes it. This doc records what was captured, what came out, and what the method cost, so the next capture is cheaper than this one was.

---

## Result

A closed, textured mesh of one berry, at measured scale.

| | |
|---|---|
| Mesh | 598,265 faces, 298,150 vertices |
| Topology | one component (99.99% of faces), 61 boundary edges of 897,424 |
| Size | 2.50 cm at the widest point, 2.38 x 2.34 x 2.02 cm |
| Volume / area | 5.02 cm3 / 29.98 cm2 |
| Texture | 8192 px, from the frames at full resolution |
| Surface relief | 8.2% of radius, standard deviation |
| Exports | OBJ + GLB, in metres |

Scale comes from **one caliper reading** of 2.5 cm across the widest point. Nothing in the capture fixes absolute size on its own, so treat this as good to a few percent, not to the digit: calipers compress a soft berry, and the reading depends on how the jaws are turned. As a cross check, the volume implies a sphere 2.12 cm across, slightly under the 2.5 cm measured, which is what a lumpy berry should do.

**Go / no-go: go.** Photogrammetry is a viable provenance path for a single berry. It is not a path to photoreal fidelity at 6 ft, which was never the claim; the raw scan is the archive twin and the ancestor, not the production mesh.

**Descendant locked 2026-09-07.** The 6 ft production body is built from this scan: a cleaned, manifold descendant scaled up, replacing the independently modelled 500 mm mesh as the default body ([`BRIEF.md`](BRIEF.md) §6, [#16](https://github.com/adamsimms/glowberry/issues/16)). The raw mesh above is unchanged in role. What changed is that the monument is no longer allowed to be an unrelated model: public application text now says the sculpture is printed from a scan of a berry picked at Pinchard's Island.

---

## What was captured

446 frames, three remounts of the same berry, so that the parts a mount hides in one orientation are seen in another.

| Remount | Frames | Rings |
|---|---|---|
| Upright | 144 | 40 deg, 15 deg, plus two low rings |
| Inverted | 151 | same |
| Sideways | 151 | same |

Six coded targets were placed with each remount. This turned out not to help (see below).

---

## What shipped, and what did not

The mesh is built from **upright and inverted only**, 150 cameras. Those two are complementary: between them they cover 99.3% of the sphere, and where they overlap they agree to a median of 1.98% of radius.

Sideways was registered successfully but **excluded**. Its camera solution was in fact the best of the three (0.2370 px against upright's 0.2466), but its reconstructed surface is about three times noisier: measured identically against the mesh, upright and inverted put 83.5% and 84.3% of their points within 2% of radius, where sideways manages 47.6%.

Held to the standard the other two set, sideways qualified over 69 of 960 surface cells, added coverage in **none** of them, and rebuilding with it moved the surface by 0.129% of radius while raising relief noise from 8.21% to 8.40%. So it was dropped, and the two-remount mesh ships.

Two independent checks say the shipped mesh is right rather than merely self-consistent:

- Projecting the mesh silhouette back into 20 frames from both rings matches the colour masks at **IoU 0.91**, with the model silhouette 6% larger in area. This tests the mesh against the photographs, not against its own reprojection error.
- Reconstructing each remount separately and fitting a sphere gives the same radius from each, and the ratio of berry radius to camera ring radius agrees to 1% across all three remounts.

---

## What the method cost, and what to do differently

These are the findings worth carrying to the next capture. Most of the time went here, not into meshing.

**1. Mount so the berry's axis is parallel to the turntable axis.** Upright and inverted register from a single unknown angle, because the mount fixes everything else, and that one angle can be swept exhaustively. "On its side" fixes nothing: it leaves the tilt free, and the berry actually sat about 30 degrees off. Searching without that extra angle looked like a berry that could not be registered at all. It was a wrong assumption, not bad data.

**2. Share the targets across remounts, or measure a scale bar.** Six coded targets were used per remount but **different targets each time**, so no marker ID appeared in two remounts and there was nothing to register against. Registration had to be solved on shape instead, outside Metashape, and absolute scale had to come from a caliper afterwards. Repeating the same targets, visible in every remount, would have removed both problems.

**3. Two complementary remounts are enough.** 99.3% coverage came from upright plus inverted. A third orientation only pays for itself if it is as clean as the first two.

**4. Cross-polarize.** The one plausible cause of the sideways noise that remains untested is specular highlight and translucency: glossy drupelet faces reflect differently as they turn, which defeats stereo matching. The issue's own kit list already suggests a polarizer, and this result is an argument for it rather than against.

**5. Tightening alignment starves the low rings.** Gradual selection dropped reprojection error to about 0.24 px, but left the low-elevation cameras below the 50 shared tie points that neighbour selection needs, so they produced no depth maps at all. The surface is built from the 40 deg ring only. Coverage survived because the remounts complement each other, but the accuracy and the redundancy pull against each other here.

### Metashape notes (2.3.2)

Four behaviours cost real time and are not obvious from the documentation:

- `mergeChunks` takes chunk **keys**, not positional indices. Passing indices silently merges the wrong chunks.
- `merge_tiepoints=True` fails with `Empty pairs list` when the chunks share no image pairs, which is exactly the case that shape registration exists to solve.
- Depth map **sets** do not survive a merge from two chunks: both arrive under the same internal key and one overwrites the other. Fuse each chunk to a cloud separately, combine outside, and import the single cloud back.
- `MaskingModeFile` replaces the 2.2-era import path, and `Model.area()` reports in chunk-internal units, so it does not change when the chunk transform is scaled.

---

## Files

Replayable scripts live in [`tools/metashape/`](../tools/metashape/README.md). Each step file carries its reasoning in the module docstring.

The public ancestor is [`models/provenance/berry_merged_up_inv_cm.glb`](../models/provenance/berry_merged_up_inv_cm.glb) (metres, 2.50 cm widest).

The 446 TIFFs and the Metashape project are not in this repo. They live in Google Drive **`BERRY/provenance/`**, with `TIFF-CHUNK-01/02/03` next to `metashape/berry04_three_chunks.psx`. Photo paths are relative to that folder. Hasselblad RAWs for this capture remain in `BERRY/BERRY-04/`.
