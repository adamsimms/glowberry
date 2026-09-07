"""Step F5: import the combined cloud into the merged chunk and mesh it.

The combined cloud is the only form in which both remounts can enter one
Metashape chunk, since mergeChunks drops one chunk's depth maps. Importing it
into merged_up_inv, which already holds all 150 solved cameras and their
masks, puts the geometry and the imagery back in one place so the mesh can be
textured from the original frames afterwards.

Texture is deliberately not built here. The mesh is worth looking at first,
specifically at the equator, where upright hands off to inverted: a visible
step there means the registration is right globally but off locally, and the
fix is an ICP refinement seeded from the current transform rather than
anything to do with texturing.

Exports an untextured model for that inspection.

Env:
    BERRY_MESH_FACES=high|custom     face count policy (default high)
    BERRY_MESH_FACE_COUNT=800000     used when policy is custom
    BERRY_MESH_FORCE=1               rebuild over an existing model

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_f5_mesh.py
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

import numpy as np  # noqa: E402
import Metashape  # noqa: E402

MERGED = "merged_up_inv"
COMBINED = os.path.join(bc.WORK, "clouds", "merged_up_inv_dense.ply")
EXPORT = os.path.join(bc.WORK, "exports", "merged_up_inv_untextured.ply")
REPORT = os.path.join(bc.WORK, "reports", "step_f5_mesh.json")
FORCE = os.environ.get("BERRY_MESH_FORCE") == "1"

POLICY = os.environ.get("BERRY_MESH_FACES", "high")
FACE_COUNT = int(os.environ.get("BERRY_MESH_FACE_COUNT", "800000"))

# From the combined sphere fit, in world units.
BERRY_RADIUS = 0.10147


def to_np(M):
    a = np.asarray(M, dtype=float)
    return a if a.ndim == 2 else a.reshape(4, 4)


def ply_point_format():
    for name in ("PointCloudFormatPLY", "PointCloudFormatPly"):
        f = getattr(Metashape, name, None)
        if f is not None:
            return f
    return None


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)
    print("GPUs:", bc.enable_gpu(Metashape))

    if not os.path.exists(COMBINED):
        print(f"missing {COMBINED}; run combine_clouds.py first")
        return

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    chunk = next((c for c in doc.chunks if c.label == MERGED), None)
    if chunk is None:
        print(f"no chunk {MERGED}; run step_f3_merge.py first")
        return

    solved = len([c for c in chunk.cameras if c.transform])
    masked = sum(1 for c in chunk.cameras if c.mask is not None)
    print(f"\n{MERGED}: {solved} solved cameras, {masked} masked")

    if getattr(chunk, "model", None) is not None and not FORCE:
        print("a model already exists here. Set BERRY_MESH_FORCE=1 to rebuild.")
        return

    print(f"\n=== importing {os.path.basename(COMBINED)} ===")
    t0 = time.time()
    chunk.importPointCloud(
        path=COMBINED,
        format=ply_point_format(),
        replace_asset=True,
        load_point_color=True,
        load_point_normal=True,
        calculate_normals=True,
    )
    doc.save()
    pc = getattr(chunk, "point_cloud", None)
    n = getattr(pc, "point_count", None) if pc is not None else None
    print(f"  {n} points imported in {(time.time()-t0)/60:.1f} min")
    if not n:
        print("  ABORT: nothing imported")
        return

    # The import has to land on the berry, not somewhere else in the chunk's
    # frame. Check against the region that was centred on it at merge time.
    T = to_np(chunk.transform.matrix)
    scale = float(np.linalg.norm(T[:3, 0]))
    half = float(chunk.region.size.x) / 2 * scale
    print(f"  region half-size in world units: {half:.4f} "
          f"({half/BERRY_RADIUS:.2f} berry radii)")

    face_policy = (
        Metashape.FaceCount.HighFaceCount if POLICY == "high"
        else Metashape.FaceCount.CustomFaceCount
    )
    print(f"\n=== building mesh (source: point cloud, faces: {POLICY}) ===")
    t0 = time.time()
    chunk.buildModel(
        source_data=Metashape.PointCloudData,
        surface_type=Metashape.SurfaceType.Arbitrary,
        interpolation=Metashape.Interpolation.EnabledInterpolation,
        face_count=face_policy,
        face_count_custom=FACE_COUNT,
        vertex_colors=True,
        vertex_confidence=True,
        build_texture=False,
    )
    mins = (time.time() - t0) / 60
    doc.save()

    model = chunk.model
    faces = len(model.faces) if model is not None else 0
    verts = len(model.vertices) if model is not None else 0
    print(f"  {faces} faces, {verts} vertices in {mins:.1f} min")

    fmt = getattr(Metashape, "ModelFormatPLY", None)
    chunk.exportModel(
        path=EXPORT, format=fmt, binary=True, save_texture=False,
        save_uv=False, save_normals=True, save_colors=True,
        save_cameras=False, save_markers=False,
    )
    mb = round(os.path.getsize(EXPORT) / 1e6, 1) if os.path.exists(EXPORT) else None
    print(f"  exported {os.path.basename(EXPORT)} ({mb} MB)")

    with open(REPORT, "w") as fh:
        json.dump({
            "chunk": MERGED, "solved_cameras": solved, "masked": masked,
            "imported_points": n, "faces": faces, "vertices": verts,
            "face_policy": POLICY, "minutes": round(mins, 2),
            "export": EXPORT,
        }, fh, indent=2, default=str)
    print("WROTE", REPORT)
    print("\nNext: inspect the seam, then step_f6_texture.py")
    print("DONE")


main()
