# Provenance berry

Scaled GLB of the Pinchard's bakeapple reconstructed for Glowberry ([#52](https://github.com/adamsimms/glowberry/issues/52)). 2.50 cm at the widest point. Upright plus inverted remounts. Metres.

This is the public ancestor file. Method: [`docs/SCANNING.md`](../../docs/SCANNING.md).

`records/` holds the run records from that pipeline: `reports/` has one JSON per step of [`tools/metashape/`](../../tools/metashape/) (alignment, reprojection error, coverage, scale check, mesh comparison), the source of the figures in `SCANNING.md`; `icp/` has the registration transforms that merge the upright and inverted remounts. Paths inside are relative to `BERRY_ROOT`.

The Metashape project, TIFFs and raw frames are not in this repo. They live in the project's off-site media storage, `30 STUDIO/32 PROJECTS/GLOWBERRY/04-ARTWORK/PROVENANCE-SCAN/`; scripts read a local working copy through `BERRY_ROOT` (see [`tools/metashape/README.md`](../../tools/metashape/README.md)).
