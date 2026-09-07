"""Step F6: clean the merged mesh into one closed surface.

The mesh from the combined cloud is 96.78% a single component plus about 900
small fragments, and it is not watertight. All three fixes exist on the model
in this build, so the cleanup happens in place and the mesh keeps its link to
the chunk holding the cameras and masks that will texture it.

Order matters. Fragments go first, because closing holes before removing them
would stitch fragments to the surface and make them permanent. Topology is
fixed next, since closeHoles needs sane edges to work from. Holes close last.

Holes are worth closing rather than leaving: the two remounts cover 99.3% of
the sphere between them, so what remains is small, and it is where the two
mount points happened to overlap. Interpolating across a gap that small is
honest; there is real surface on all sides of it.

Smoothing is off by default. The berry's drupelet relief is the subject, and
at 8.2% of radius standard deviation there is not much margin between relief
and smoothing it away. Set BERRY_SMOOTH to a strength to try it.

Env:
    BERRY_MIN_COMPONENT=1000   drop components smaller than this many faces
    BERRY_CLOSE_HOLES=30       closeHoles level, 0 to skip
    BERRY_SMOOTH=0             smoothModel strength, 0 to skip

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f6_clean.py
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

MERGED = "merged_up_inv"
EXPORT = os.path.join(bc.WORK, "exports", "merged_up_inv_clean.ply")
REPORT = os.path.join(bc.WORK, "reports", "step_f6_clean.json")

MIN_COMPONENT = int(os.environ.get("BERRY_MIN_COMPONENT", "1000"))
CLOSE_HOLES = int(os.environ.get("BERRY_CLOSE_HOLES", "30"))
SMOOTH = float(os.environ.get("BERRY_SMOOTH", "0"))


def stats(model, label):
    f, v = len(model.faces), len(model.vertices)
    print(f"  {label}: {f} faces, {v} vertices")
    return f, v


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    chunk = next((c for c in doc.chunks if c.label == MERGED), None)
    if chunk is None:
        print(f"no chunk {MERGED}")
        return
    model = chunk.model
    if model is None:
        print("no model; run step_f5_mesh.py first")
        return

    print(f"\n=== {MERGED} mesh cleanup ===")
    f0, v0 = stats(model, "as built")
    steps = {"as_built": {"faces": f0, "vertices": v0}}

    if MIN_COMPONENT > 0:
        model.removeComponents(MIN_COMPONENT)
        f, v = stats(model, f"after dropping components under {MIN_COMPONENT} faces")
        steps["components_removed"] = {
            "threshold": MIN_COMPONENT, "faces": f, "vertices": v,
            "faces_removed": f0 - f,
        }
        print(f"    removed {f0-f} faces ({(f0-f)/f0*100:.2f}%)")

    try:
        model.fixTopology()
        f, v = stats(model, "after fixTopology")
        steps["topology_fixed"] = {"faces": f, "vertices": v}
    except Exception as e:
        print(f"  fixTopology failed: {e}")

    if CLOSE_HOLES > 0:
        before = len(model.faces)
        model.closeHoles(level=CLOSE_HOLES)
        f, v = stats(model, f"after closeHoles(level={CLOSE_HOLES})")
        steps["holes_closed"] = {
            "level": CLOSE_HOLES, "faces": f, "vertices": v,
            "faces_added": f - before,
        }
        print(f"    added {f-before} faces to close gaps")

    if SMOOTH > 0:
        chunk.smoothModel(strength=SMOOTH, fix_borders=True)
        model = chunk.model
        f, v = stats(model, f"after smoothModel(strength={SMOOTH})")
        steps["smoothed"] = {"strength": SMOOTH, "faces": f, "vertices": v}

    try:
        vol = model.volume()
        area = model.area()
        print(f"\n  closed surface: volume {vol:.6g}, area {area:.6g}")
        steps["volume"] = vol
        steps["area"] = area
    except Exception as e:
        print(f"\n  volume unavailable ({e}); the mesh is probably still open")

    doc.save()
    fmt = getattr(Metashape, "ModelFormatPLY", None)
    chunk.exportModel(
        path=EXPORT, format=fmt, binary=True, save_texture=False,
        save_uv=False, save_normals=True, save_colors=True,
        save_cameras=False, save_markers=False,
    )
    mb = round(os.path.getsize(EXPORT) / 1e6, 1) if os.path.exists(EXPORT) else None
    print(f"  exported {os.path.basename(EXPORT)} ({mb} MB)")

    with open(REPORT, "w") as fh:
        json.dump(steps, fh, indent=2, default=str)
    print("WROTE", REPORT)
    print("\nNext: inspect, then step_f7_texture.py")
    print("DONE")


main()
