"""Step H1: put the model into real units, from one caliper reading.

Nothing in this capture fixes absolute size. The three remounts share no
markers, no scale bar was measured, and the camera rings only ever gave
ratios between chunks, never a length. So the model has been carried in
arbitrary project units the whole way, which is fine for shape and useless for
anything physical.

The measurement is 2.5 cm across at the widest point, taken with calipers.
Calipers between parallel jaws read the largest distance across the object in
some direction, so the matching quantity in the mesh is its maximum width over
all directions, computed here on the convex hull because only hull vertices
can be extremal and the full mesh has 298,150 of them.

One reading fixes scale but says nothing about how much of the error it
carries. A caliper on a soft berry compresses it slightly and finds a maximum
that depends on how the jaws are turned, so treat the result as good to a few
percent, not to the digit. Volume is printed as a cross check: if it looks
wrong for a cloudberry, the reading or the axis it was taken along is worth
revisiting before anything downstream depends on it.

Scaling the chunk transform moves cameras with the mesh, which keeps the
project self-consistent. Texture is unaffected, so the exports are rewritten
without rebuilding it.

Env:
    BERRY_WIDTH_CM=2.5
    BERRY_SCALE_FORCE=1

Run:
    /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -r step_h1_scale.py
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

import numpy as np  # noqa: E402
import Metashape  # noqa: E402

CHUNK = "merged_up_inv"
EXPORT_DIR = os.path.join(bc.WORK, "exports")
REPORT = os.path.join(bc.WORK, "reports", "step_h1_scale.json")
STAMP = "berry_scaled_width_cm"

WIDTH_CM = float(os.environ.get("BERRY_WIDTH_CM", "2.5"))
FORCE = os.environ.get("BERRY_SCALE_FORCE") == "1"


def to_ms(M):
    return Metashape.Matrix([[float(x) for x in row] for row in M])


def to_np(M):
    a = np.asarray(M, dtype=float)
    return a if a.ndim == 2 else a.reshape(4, 4)


def meta_get(meta, key):
    try:
        return meta[key] or None
    except Exception:
        return None


def world_vertices(chunk):
    """Model vertices in world coordinates."""
    T = to_np(chunk.transform.matrix)
    V = np.array([[v.coord.x, v.coord.y, v.coord.z]
                  for v in chunk.model.vertices], dtype=float)
    return (T[:3, :3] @ V.T).T + T[:3, 3]


def caliper_width(V, n_dirs=4000):
    """Largest distance across the shape, over all directions.

    The extremal pair always lies on the convex hull, but scipy is not in
    Metashape's bundled Python, and a random subsample can miss the pair
    entirely, which silently understates the width and so overstates the
    scale. Instead every candidate is collected by taking the furthest vertex
    in each of many directions: any hull vertex is extremal in some direction,
    so a dense enough set of directions catches the pair, and the exhaustive
    comparison then runs over a few thousand candidates rather than 298,150.
    """
    rng = np.random.default_rng(0)
    d = rng.normal(size=(n_dirs, 3))
    d /= np.linalg.norm(d, axis=1)[:, None]
    proj = V @ d.T
    cand = np.unique(np.concatenate([proj.argmax(axis=0),
                                     proj.argmin(axis=0)]))
    H = V[cand]
    dist = np.linalg.norm(H[:, None, :] - H[None, :, :], axis=-1)
    i, j = np.unravel_index(np.argmax(dist), dist.shape)
    return float(dist[i, j]), H[i], H[j], len(H)


def faces_of(chunk):
    return np.array([[f.vertices[0], f.vertices[1], f.vertices[2]]
                     for f in chunk.model.faces], dtype=int)


def volume_and_area(chunk, V):
    """Volume by the divergence theorem, and area by triangle sum.

    Both from world vertices. Model.area() reports in chunk-internal units,
    which do not change when the chunk transform is scaled, so converting it
    with a scale factor double counts any scaling already applied.
    """
    F = faces_of(chunk)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vol = float(abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)
    area = float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2.0)
    return vol, area


def main():
    bc.ensure_dirs()
    print("Metashape", Metashape.app.version)

    doc = Metashape.Document()
    doc.open(bc.PROJECT, read_only=False, ignore_lock=True)
    chunk = next((c for c in doc.chunks if c.label == CHUNK), None)
    if chunk is None or chunk.model is None:
        print(f"no mesh in chunk {CHUNK}")
        return

    already = meta_get(chunk.meta, STAMP)
    if already and not FORCE:
        print(f"\n{CHUNK} is already scaled to {already} cm wide. Scaling "
              f"again would compound it. BERRY_SCALE_FORCE=1 to override.")
        return

    V = world_vertices(chunk)
    width, pa, pb, n_hull = caliper_width(V)
    print(f"\nmesh: {len(V)} vertices, {n_hull} on the convex hull")
    print(f"widest span in project units: {width:.6f}")

    factor = (WIDTH_CM / 100.0) / width
    print(f"\nmeasured width {WIDTH_CM} cm, so the scale factor is "
          f"{factor:.6g} (project units to metres)")

    chunk.transform.matrix = to_ms(np.diag([factor, factor, factor, 1.0])) \
        * chunk.transform.matrix
    chunk.meta[STAMP] = str(WIDTH_CM)
    doc.save()

    V2 = world_vertices(chunk)
    w2, _, _, _ = caliper_width(V2)
    vol_m3, area_m2 = volume_and_area(chunk, V2)
    vol_cm3 = vol_m3 * 1e6
    area_cm2 = area_m2 * 1e4
    ext = V2.max(axis=0) - V2.min(axis=0)

    print(f"\n=== in real units ===")
    print(f"  widest span:      {w2*100:.2f} cm  (target {WIDTH_CM})")
    print(f"  bounding extents: {ext[0]*100:.2f} x {ext[1]*100:.2f} x "
          f"{ext[2]*100:.2f} cm")
    print(f"  volume:           {vol_cm3:.2f} cm3")
    print(f"  surface area:     {area_cm2:.2f} cm2")

    sphere_equiv = (6 * vol_cm3 / np.pi) ** (1 / 3)
    print(f"\n  cross check: a sphere of that volume would be "
          f"{sphere_equiv:.2f} cm across, against the {WIDTH_CM} cm measured. "
          f"A lumpy berry reads a little wider than its volume implies, so "
          f"these should be close but not equal.")
    if not 0.7 < sphere_equiv / WIDTH_CM < 1.0:
        print(f"  WARNING: those disagree more than a berry's lumpiness "
              f"explains. Worth re-checking the caliper reading, or which "
              f"axis it was taken along, before relying on this scale.")

    print("\n=== re-exporting at real scale (texture unchanged) ===")
    out = {}
    for ext_name, names in (("obj", ("ModelFormatOBJ",)),
                            ("glb", ("ModelFormatGLTF", "ModelFormatGLB"))):
        fmt = next((getattr(Metashape, n) for n in names
                    if getattr(Metashape, n, None) is not None), None)
        if fmt is None:
            continue
        path = os.path.join(EXPORT_DIR, f"berry_merged_up_inv_cm.{ext_name}")
        chunk.exportModel(path=path, format=fmt, binary=True,
                          save_texture=True, save_uv=True, save_normals=True,
                          save_colors=True, save_cameras=False,
                          save_markers=False,
                          embed_texture=(ext_name == "glb"))
        mb = round(os.path.getsize(path) / 1e6, 1)
        print(f"  {os.path.basename(path)} ({mb} MB)")
        out[ext_name] = {"path": path, "mb": mb}

    with open(REPORT, "w") as fh:
        json.dump({
            "measured_width_cm": WIDTH_CM,
            "width_project_units": width,
            "scale_factor_to_metres": factor,
            "width_cm_after": w2 * 100,
            "extents_cm": (ext * 100).tolist(),
            "volume_cm3": vol_cm3,
            "area_cm2": area_cm2,
            "sphere_equivalent_diameter_cm": sphere_equiv,
            "exports": out,
            "caveat": "one caliper reading, on a compressible berry; "
                      "treat as good to a few percent",
        }, fh, indent=2, default=str)
    print("WROTE", REPORT)
    print("DONE")


main()
