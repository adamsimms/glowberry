"""Step F8: texture the merged mesh from the original frames and export it.

Textures from both remounts at once, which is the reason the merge was done
inside Metashape rather than just meshing the combined cloud outside: the
merged chunk holds all 150 solved cameras with their masks, so every part of
the surface can be textured from whichever remount actually saw it.

The colour masks are used, not the model ones. The comparison in step_f7 put
their agreement at IoU 0.91 with the model silhouette 6% larger in area, so
the colour masks are the tighter of the two, and a mask that overshoots the
berry invites background pixels into the texture along the silhouette.

downscale=1, against the default of 2. The berry spans roughly 700 px in a
frame, so it is small in the image to begin with and there is no resolution to
give away.

Exports OBJ with a texture file and GLB with the texture embedded. Note the
model is in the project's arbitrary units: nothing in this capture fixes
absolute size, since the remounts share no markers and no scale bar was
measured. A single caliper reading would fix it later without redoing any of
this.

Env:
    BERRY_TEXTURE_SIZE=8192
    BERRY_TEXTURE_DOWNSCALE=1
    BERRY_TEXTURE_FORCE=1

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f8_texture.py
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

MERGED = "merged_up_inv"
EXPORT_DIR = os.path.join(bc.WORK, "exports")
REPORT = os.path.join(bc.WORK, "reports", "step_f8_texture.json")

TEXTURE_SIZE = int(os.environ.get("BERRY_TEXTURE_SIZE", "8192"))
TEXTURE_DOWNSCALE = int(os.environ.get("BERRY_TEXTURE_DOWNSCALE", "1"))
FORCE = os.environ.get("BERRY_TEXTURE_FORCE") == "1"


def model_format(*names):
    for n in names:
        f = getattr(Metashape, n, None)
        if f is not None:
            return n, f
    return None, None


def main():
    bc.ensure_dirs()
    os.makedirs(EXPORT_DIR, exist_ok=True)
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    chunk = next((c for c in doc.chunks if c.label == MERGED), None)
    if chunk is None:
        print(f"no chunk {MERGED}")
        return
    model = chunk.model
    if model is None:
        print("no model; run step_f5 and step_f6 first")
        return

    cams = [c for c in chunk.cameras if c.transform and c.enabled]
    masked = sum(1 for c in chunk.cameras if c.mask is not None)
    print(f"\n{MERGED}: {len(model.faces)} faces, {len(cams)} cameras, "
          f"{masked} masked")

    if model.textures and not FORCE:
        print("already textured. Set BERRY_TEXTURE_FORCE=1 to redo.")
    else:
        print(f"\n=== building UVs ({TEXTURE_SIZE} px) ===")
        t0 = time.time()
        chunk.buildUV(
            mapping_mode=Metashape.MappingMode.GenericMapping,
            page_count=1,
            texture_size=TEXTURE_SIZE,
        )
        print(f"  {(time.time()-t0)/60:.1f} min")

        print(f"\n=== building texture (downscale {TEXTURE_DOWNSCALE}) ===")
        t0 = time.time()
        chunk.buildTexture(
            blending_mode=Metashape.BlendingMode.NaturalBlending,
            texture_size=TEXTURE_SIZE,
            downscale=TEXTURE_DOWNSCALE,
            fill_holes=True,
            ghosting_filter=True,
            texture_type=Metashape.Model.TextureType.DiffuseMap,
            source_data=Metashape.ImagesData,
        )
        mins = (time.time() - t0) / 60
        doc.save()
        print(f"  {mins:.1f} min, {len(chunk.model.textures)} texture page(s)")

    out = {}
    for ext, names in (
        ("obj", ("ModelFormatOBJ",)),
        ("glb", ("ModelFormatGLTF", "ModelFormatGLB")),
    ):
        name, fmt = model_format(*names)
        if fmt is None:
            print(f"  no exporter for {ext}")
            continue
        path = os.path.join(EXPORT_DIR, f"berry_merged_up_inv.{ext}")
        chunk.exportModel(
            path=path, format=fmt, binary=True, save_texture=True,
            save_uv=True, save_normals=True, save_colors=True,
            save_cameras=False, save_markers=False,
            embed_texture=(ext == "glb"),
        )
        mb = round(os.path.getsize(path) / 1e6, 1) if os.path.exists(path) else None
        print(f"  exported {os.path.basename(path)} via {name} ({mb} MB)")
        out[ext] = {"path": path, "mb": mb}

    with open(REPORT, "w") as fh:
        json.dump({
            "chunk": MERGED, "faces": len(chunk.model.faces),
            "cameras": len(cams), "masked": masked,
            "texture_size": TEXTURE_SIZE, "downscale": TEXTURE_DOWNSCALE,
            "exports": out,
            "units": "arbitrary project units; absolute scale not established",
        }, fh, indent=2, default=str)
    print("WROTE", REPORT)
    print("DONE")


main()
