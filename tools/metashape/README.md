# Berry photogrammetry scripts

Replayable pipeline for the Pinchard's bakeapple reconstruction documented in [`docs/SCANNING.md`](../../docs/SCANNING.md).

Frames, the Metashape project, point clouds, and mesh exports stay on disk. They are not in this repo. Layout (Drive archive `BERRY/BERRY-04/`, or a local copy of that package):

```
TIFF-CHUNK-01/   TIFF-CHUNK-02/   TIFF-CHUNK-03/
metashape/berry04_three_chunks.psx
```

Photo paths in the `.psx` are relative to that folder. Set `BERRY_ROOT` to it when running scripts. Default if unset: `/Users/adamsimms/Desktop/BERRY`. The Drive archive of the same layout is `My Drive/BERRY/provenance/`.

## Two runtimes

Metashape Pro 2.3.2 scripts (the `step_*` files that import `Metashape`):

```
/Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_a_import.py
```

Open3D scripts (registration, cloud combine, inspection). Use the venv that has Open3D installed, not Metashape's bundled Python:

```
/Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python icp_constrained.py
```

## Order

| Step | Script | What it does |
|------|--------|----------------|
| Masks | `make_berry_masks.py` | Chroma-threshold berry masks for every frame |
| A | `step_a_import.py` | Import three remount chunks, attach masks, detect markers |
| B | `step_b_quality.py`, `step_b2_patch.py` | Image quality gate |
| D | `step_d_align_variants.py`, `step_d2_refine.py`, `step_d3_tune.py` | Per-remount alignment, high rings only |
| Clouds | `step_e3_cloud.py` | Export berry-only clouds |
| Register | `dump_capture_geometry.py`, `icp_constrained.py` | Turntable-constrained shape registration |
| F1 | `step_f1_apply_transform.py` | Put inverted into the upright frame |
| F2–F4 | `step_f2_depth.py`, `step_f4_cloud.py` | Depth maps and dense clouds per remount |
| Combine | `combine_clouds.py` | Merge clouds outside Metashape |
| F5–F8 | `step_f5_mesh.py` … `step_f8_texture.py` | Mesh, clean, mask check, texture |
| F9 | `step_f9_sideways.py` … `step_f9e_verify.py` | Register sideways, then exclude on quality |
| G | `step_g1_sideways_place.py` … `compare_meshes.py` | Regional include test (did not ship) |
| H | `step_h1_scale.py` | Scale to 2.50 cm widest |

`list_chunks.py`, `inspect_mesh.py`, and `render_model.py` are inspection helpers, not pipeline steps.

## License

Software in this folder is MIT. See [`LICENSE.md`](../../LICENSE.md).
