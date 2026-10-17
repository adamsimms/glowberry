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

## Print-ready test files (2026-10-17)

Closed, single-body STLs at 100 mm tall, for desk test prints ([#61](https://github.com/adamsimms/glowberry/issues/61)). They are not the production body ([#16](https://github.com/adamsimms/glowberry/issues/16)).

| File | Method | Mean / p95 deviation from scan (% of radius) |
|---|---|---|
| `berry_detail_100mm.stl` | Voxel remesh, light smoothing | 0.46 / 0.84 |
| `berry_clean_100mm.stl` | Voxel remesh, medium smoothing | 0.74 / 2.03 |
| `berry_smooth_100mm.stl` | Robust spherical-harmonic fit, degree 12 | 2.22 / 6.39 |
| `berry_lumps_100mm.stl` | Packed-spheres look-dev, closed | stylized, not measured |
| `berry_lumps_sharp_100mm.stl` | Same 12 spheres, exact boolean union | stylized, not measured |
| `berry_lumps_groove_100mm.stl` | Same 12 spheres, smooth union, ~1.2 mm groove | stylized, not measured |

The look-dev joins zigzag because it moved the scan's irregular vertices onto the sphere union. The sharp and groove files rebuild the union from the 12 spheres themselves (recovered exactly from `berry_medium.glb`), so joins are clean curves. Rebuild with `uv run tools/mesh/lumps_clean.py [--groove-mm N]`.

`berry_organic_{light,medium}_100mm.stl` sit between sharp, groove, and smooth: a 0.6 mm groove, then each vertex pulled 25% or 45% of the way toward the scan's own surface (robust spherical-harmonic fit, degree 20, registered to the lumps by ICP). The unevenness comes from the berry, not from added noise. `berry_organic_medium_skin_100mm.stl` adds a faint procedural skin texture (0.15 mm at 100 mm), which is an aesthetic choice and does not survive at 1 to 2 in. Rebuild with `uv run tools/mesh/lumps_organic.py`; resize with `tools/mesh/resize.py --widest-mm`.

`berry_seams_{wander,wander_strong,wander_scan}_100mm.stl` keep every drupelet an exact sphere and change only a band around each seam (masked by the gap between the two nearest sphere distances). Seams drift sideways along slow curves and the groove width varies (procedural, invented). `wander_scan` also lets seams sink, never rise, where the scan sits lower. `wander_70` / `wander_50` / `wander_30` are gentler steps of `wander` (percent of its sideways drift), made after `wander` was picked but judged to wander too much. Rebuild with `uv run tools/mesh/lumps_seams.py [--only NAME ...]`. `wander_50` was picked.

`berry_texture_{vesicles,skin,nub,flesh,inner_cutaway}_100mm.stl` add flesh texture to `wander_50`, faded to zero near seams so the seams stay as picked. The scan's photo texture shows a faint cellular, frosted pattern under the drupelet skin and small dark style specks; vesicles and skin follow the first, the nub dimple at each drupelet's tip interprets the second (the specks' exact position is not resolvable). Depths are 0.02 to 0.35 mm at 100 mm, so they read at 100 mm on a resin printer and vanish at 1 to 2 in on FDM. `inner_cutaway` is a mock for the lit 6 ft shell: smooth outside, cells thinning the inside wall, cut in half. Rebuild with `uv run tools/mesh/lumps_texture.py [--only NAME ...]`. Of these, only skin worked; `skin_60`, `skin_35`, `skin_broad`, and `skin_fine` are quieter versions of the same pattern. `skin_35` was picked for resin (about ±0.025 mm, near the resin limit). `skin_fdm_min` is the smallest version an FDM print can show: broad layer only at about ±0.1 mm, since the fine layer is narrower than a 0.4 mm nozzle can draw.

Slicer-ready test set (2026-10-17) in `models/print/ready/`, built by `uv run tools/mesh/print_prep.py`:

| File | Printer | Prep |
|---|---|---|
| `resin_skin35_100mm.stl` | Resin | Hollow, 2 mm wall, two 3 mm drain holes, label "35" |
| `resin_plain_100mm.stl` | Resin | Hollow, same, label "0" (control, no skin) |
| `resin_plain_true_size_25mm.stl` | Resin | Solid, label "0" |
| `fdm_skin_min_100mm.stl` | FDM | 1 mm flat at the stem end, label "F" |
| `fdm_plain_2in.stl` | FDM | 0.6 mm flat, label "0" |

Hollowing cuts each 100 mm resin print from about 408 cm3 to 54 cm3. Labels are mirrored to read from below. Skin is tested at 100 mm only; it is tuned in millimetres and vanishes when scaled down, so the small prints carry no skin.

Full-colour files (2026-10-17) in `models/print/colour/`, built by `uv run tools/mesh/colour_files.py`: a designed vertical gradient (amber `#FFB02E` at the top to orange `#E86A17` at the base, not taken from the scan) and solid amber and solid orange, each at 100 mm hollow (`skin_35`), 2 in, and true size. Format is 3MF with a per-vertex colour group (checked in strict mode with lib3mf); the gradient files also come as zipped VRML. Translucency is not in the file; request colour-tinted translucent (PolyJet) or opaque when ordering. Test prints are orange or amber from the start, never grey.

What automation can and cannot do here: the underside of the scan (inverted remount) is clean and shows the drupelets. The upper half is noisy, and that noise is as deep as the drupelets, so no single smoothing strength removes one and keeps the other. Light smoothing keeps the noise; heavy smoothing turns it into pits; the spherical-harmonic fit removes both and leaves soft lumps. A clean drupelet surface at 6 ft (about 73x scale, where 1 mm of scan noise becomes 7 cm) needs a sculpting pass, using the clean underside and the 446 source photographs as reference.

Screened Poisson reconstruction aborts on this scan above depth 6 in both PyMeshLab and Open3D, so the closed surface comes from Blender's voxel remesher.

Files are local (`models/print/`, gitignored). Rebuild with `uv run tools/mesh/print_ready.py [--height-mm N]`.

---

## Files

Replayable scripts live in [`tools/metashape/`](../tools/metashape/README.md). Each step file carries its reasoning in the module docstring. Print-ready descendants come from [`tools/mesh/print_ready.py`](../tools/mesh/print_ready.py).

The public ancestor is [`models/provenance/berry_merged_up_inv_cm.glb`](../models/provenance/berry_merged_up_inv_cm.glb) (metres, 2.50 cm widest).

The 446 TIFFs and the Metashape project are not in this repo. They live in Google Drive **`BERRY/provenance/`**, with `TIFF-CHUNK-01/02/03` next to `metashape/berry04_three_chunks.psx`. Photo paths are relative to that folder.
