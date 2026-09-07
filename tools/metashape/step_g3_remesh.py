"""Step G3: rebuild the mesh with sideways included, to see if it helps.

The filter in step_g2 already predicts it will not. Only 69 of 960 cells
reached the standard upright and inverted set, no cell gained coverage that
was previously empty, and the cloud grew 4.7%. So a third measurement arrives
over about 7% of the surface and nowhere else.

Building it anyway, because a prediction is cheaper than a measurement and
worth less. If the rebuilt mesh is not measurably better, that is a result:
sideways was correctly registered and still had nothing to add, which is worth
knowing for the next capture.

Work happens in a copy of the merged chunk, so the mesh that is already
textured and exported cannot be lost to this experiment.

Env:
    BERRY_G3_FACES=high    face count target
    BERRY_G3_FORCE=1       rebuild even if the copy already has a mesh

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_g3_remesh.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import berry_common as bc  # noqa: E402

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

bc.add_user_packages()

import Metashape  # noqa: E402

SOURCE = "merged_up_inv"
TARGET = "merged_up_inv_sw"
CLOUD = os.path.join(bc.WORK, "clouds", "merged_up_inv_sw_dense.ply")
EXPORT = os.path.join(bc.WORK, "exports", "merged_up_inv_sw_clean.ply")
REPORT = os.path.join(bc.WORK, "reports", "step_g3_remesh.json")

FACES = {"high": Metashape.FaceCount.HighFaceCount,
         "medium": Metashape.FaceCount.MediumFaceCount}[
    os.environ.get("BERRY_G3_FACES", "high")]
FORCE = os.environ.get("BERRY_G3_FORCE") == "1"
MIN_COMPONENT = 1000


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    if not os.path.exists(CLOUD):
        print(f"no {CLOUD}; run step_g2 first")
        return

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)

    src = next((c for c in doc.chunks if c.label == SOURCE), None)
    if src is None:
        print(f"no chunk {SOURCE}")
        return
    chunk = next((c for c in doc.chunks if c.label == TARGET), None)
    if chunk is None:
        print(f"copying {SOURCE} -> {TARGET}, so the finished mesh is safe")
        chunk = src.copy()
        chunk.label = TARGET
        doc.save()
    else:
        print(f"reusing {TARGET}")

    if chunk.model is not None and not FORCE:
        print(f"{TARGET} already has a mesh. BERRY_G3_FORCE=1 to rebuild.")
    else:
        print(f"\nimporting {os.path.basename(CLOUD)}...")
        t0 = time.time()
        chunk.importPointCloud(path=CLOUD, replace_asset=True)
        print(f"  imported in {(time.time()-t0)/60:.1f} min")

        print("building the model...")
        t0 = time.time()
        chunk.buildModel(
            surface_type=Metashape.Arbitrary,
            source_data=Metashape.PointCloudData,
            face_count=FACES,
            interpolation=Metashape.EnabledInterpolation,
        )
        print(f"  {len(chunk.model.faces)} faces in "
              f"{(time.time()-t0)/60:.1f} min")
        doc.save()

    model = chunk.model
    f0 = len(model.faces)
    model.removeComponents(MIN_COMPONENT)
    model.fixTopology()
    model.closeHoles(level=30)
    print(f"\ncleanup: {f0} -> {len(model.faces)} faces, "
          f"{len(model.vertices)} vertices")
    doc.save()

    fmt = getattr(Metashape, "ModelFormatPLY", None)
    chunk.exportModel(path=EXPORT, format=fmt, binary=True,
                      save_texture=False, save_uv=False, save_normals=True,
                      save_colors=True, save_cameras=False,
                      save_markers=False)
    mb = round(os.path.getsize(EXPORT) / 1e6, 1)
    print(f"exported {os.path.basename(EXPORT)} ({mb} MB)")

    with open(REPORT, "w") as fh:
        json.dump({"chunk": TARGET, "cloud": CLOUD,
                   "faces": len(model.faces),
                   "vertices": len(model.vertices),
                   "export": EXPORT, "mb": mb}, fh, indent=2)
    print("WROTE", REPORT)
    print("\nNext: compare_meshes.py")
    print("DONE")


main()
