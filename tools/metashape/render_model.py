"""Render the finished berry from several angles, to look at it.

Every check so far has been a number or an unwrap. Those establish that the
registration holds and that the mesh agrees with the photographs, but they do
not show whether the thing looks like a cloudberry, which is the only test the
artist actually cares about.

Tries Open3D's offscreen renderer first, for real shaded views with the
texture. That depends on Filament working headless, so there is a fallback
that shades the mesh from vertex colours and a simple light, which needs
nothing but numpy and matplotlib.

Run:
    /Users/adamsimms/Desktop/BERRY/metashape/.venv-icp/bin/python render_model.py
"""

import os

import numpy as np
import open3d as o3d

WORK = "/Users/adamsimms/Desktop/BERRY/metashape"
OBJ = os.path.join(WORK, "exports", "berry_merged_up_inv.obj")
CLEAN = os.path.join(WORK, "exports", "merged_up_inv_clean.ply")
OUT = os.path.join(WORK, "icp", "berry_render.png")

VIEWS = [("front", 0, 0), ("right", 90, 0), ("back", 180, 0),
         ("left", 270, 0), ("top", 0, 80), ("bottom", 0, -80)]


def load_mesh():
    for path in (OBJ, CLEAN):
        if not os.path.exists(path):
            continue
        mesh = o3d.io.read_triangle_mesh(path, enable_post_processing=True)
        if len(mesh.triangles):
            print(f"loaded {os.path.basename(path)}: {len(mesh.triangles)} "
                  f"faces, textured: {bool(mesh.textures)}, "
                  f"vertex colours: {mesh.has_vertex_colors()}")
            return mesh, path
    raise SystemExit("no mesh found")


def try_offscreen(mesh):
    """Real shaded renders with the texture, if Filament runs headless."""
    try:
        from open3d.visualization import rendering
        r = rendering.OffscreenRenderer(700, 700)
    except Exception as e:
        print(f"offscreen renderer unavailable ({type(e).__name__}: {e})")
        return None

    try:
        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        if mesh.textures:
            mat.albedo_img = mesh.textures[0]
        r.scene.add_geometry("berry", mesh, mat)
        r.scene.scene.set_sun_light([-0.3, -0.3, -0.8], [1, 1, 1], 90000)
        r.scene.scene.enable_sun_light(True)
        r.scene.set_background([1, 1, 1, 1])

        c = mesh.get_center()
        radius = np.linalg.norm(
            np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())) / 2
        images = []
        for name, az, el in VIEWS:
            a, e = np.radians(az), np.radians(el)
            eye = c + radius * 3.0 * np.array(
                [np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
            up = [0, 0, 1] if abs(el) < 89 else [0, 1, 0]
            r.setup_camera(45.0, c, eye, up)
            images.append((name, np.asarray(r.render_to_image())))
        return images
    except Exception as e:
        print(f"offscreen rendering failed ({type(e).__name__}: {e})")
        return None


def shade_fallback(mesh):
    """Flat-shade triangles by their normals, coloured from vertex colours."""
    mesh.compute_vertex_normals()
    V = np.asarray(mesh.vertices)
    F = np.asarray(mesh.triangles)
    N = np.asarray(mesh.triangle_normals)
    C = (np.asarray(mesh.vertex_colors) if mesh.has_vertex_colors()
         else np.tile([0.85, 0.45, 0.2], (len(V), 1)))
    face_col = C[F].mean(axis=1)
    centre = V.mean(axis=0)
    tri_centre = V[F].mean(axis=1)

    out = []
    for name, az, el in VIEWS:
        a, e = np.radians(az), np.radians(el)
        view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
        # Screen basis
        up = np.array([0, 0, 1.0]) if abs(el) < 89 else np.array([0, 1.0, 0])
        x = np.cross(up, view)
        x /= np.linalg.norm(x)
        y = np.cross(view, x)

        facing = N @ view > 0
        idx = np.flatnonzero(facing)
        depth = (tri_centre[idx] - centre) @ view
        idx = idx[np.argsort(depth)]        # far to near

        lit = np.clip(N[idx] @ view, 0.05, 1.0) ** 0.8
        cols = np.clip(face_col[idx] * lit[:, None] * 1.15, 0, 1)
        pts = V[F[idx]] - centre
        out.append((name, pts @ x, pts @ y, cols))
    return out


def main():
    mesh, path = load_mesh()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    images = try_offscreen(mesh)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10.4), dpi=110)

    if images is not None:
        for ax, (name, img) in zip(axes.ravel(), images):
            ax.imshow(img)
            ax.set_title(name)
            ax.axis("off")
        note = "textured, offscreen render"
    else:
        print("falling back to normal shading from vertex colours")
        for ax, (name, sx, sy, cols) in zip(axes.ravel(), shade_fallback(mesh)):
            polys = np.stack([sx, sy], axis=-1)
            ax.add_collection(PolyCollection(
                polys, facecolors=cols, edgecolors="none", antialiaseds=False))
            lim = np.abs(polys).max() * 1.05
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_aspect("equal")
            ax.set_title(name)
            ax.axis("off")
        note = "shaded from vertex colours"

    fig.suptitle(f"Merged berry, upright + inverted ({note})")
    fig.tight_layout()
    fig.savefig(OUT)
    print("wrote", OUT)
    print("DONE")


main()
