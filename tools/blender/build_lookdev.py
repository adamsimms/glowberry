"""Build a Blender look-dev scene: ghost scan + packed grape icospheres.

Run:
    /Applications/Blender.app/Contents/MacOS/Blender --background \\
        --python tools/blender/build_lookdev.py

Imports the provenance GLB, recentres it, scales it so the berry is about a
metre across, then seats ~10 icospheres on the main lumps. Grapes stay as
separate objects you can grab. BerryUnion is a boolean of the pack.

Does not touch models/provenance/.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLY = os.path.join(
    os.path.expanduser("~/Desktop/BERRY/metashape/exports"),
    "merged_up_inv_clean.ply",
)
GLB = os.path.join(ROOT, "models", "provenance", "berry_merged_up_inv_cm.glb")
REF_DIR = os.path.join(ROOT, "sketchpad", "lookdev")
BLEND_OUT = os.path.join(ROOT, "sketchpad", "lookdev", "berry_lookdev.blend")
GLB_OUT = os.path.join(ROOT, "models", "smooth", "berry_blender.glb")
PNG_OUT = os.path.join(ROOT, "models", "smooth", "berry_blender.png")

TARGET_WIDEST = 1.0
MIN_SEP_DEG = 34.0
K = 0.62
PACK = 1.55


def log(msg):
    print(msg, flush=True)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in list(bpy.data.collections):
        if coll.name not in {"Collection", "Scene Collection"}:
            bpy.data.collections.remove(coll)


def collection(name):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    scene_col = bpy.context.scene.collection
    if col.name not in scene_col.children:
        scene_col.children.link(col)
    return col


def link(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def mat(name, colour):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.45
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def world_verts(obj):
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def import_ghost():
    ply = PLY if os.path.exists(PLY) else GLB
    if ply.endswith(".ply"):
        bpy.ops.wm.ply_import(filepath=ply)
    else:
        bpy.ops.import_scene.gltf(filepath=ply)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("gltf import produced no mesh")
    ghost = max(meshes, key=lambda o: len(o.data.vertices))
    bpy.ops.object.select_all(action="DESELECT")
    ghost.select_set(True)
    bpy.context.view_layer.objects.active = ghost
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    verts = world_verts(ghost)
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    zs = [v.z for v in verts]
    widest = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    cz = sum(zs) / len(zs)
    log(f"imported widest {widest:.4f} m, {len(verts)} verts, centre "
        f"({cx:.4f}, {cy:.4f}, {cz:.4f})")

    bpy.context.scene.cursor.location = Vector((cx, cy, cz))
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    ghost.location = (0.0, 0.0, 0.0)
    scale = TARGET_WIDEST / max(widest, 1e-9)
    ghost.scale = (scale, scale, scale)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    gv = world_verts(ghost)
    log(f"recentred widest {max(v.length for v in gv)*2:.4f} m")

    ghost.parent = None
    ghost.name = "provenance_ghost"
    ghost.display_type = "WIRE"
    ghost.hide_render = True
    ghost.hide_select = True
    ghost.hide_viewport = True
    ghost.show_in_front = False
    ghost.data.materials.clear()
    ghost.data.materials.append(mat("GhostWire", (0.18, 0.14, 0.12)))
    link(ghost, collection("Ghost"))

    keep = {ghost}
    for o in list(bpy.context.scene.objects):
        if o not in keep and o.type not in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(o, do_unlink=True)
    return ghost, scale, Vector((cx, cy, cz))


def fit_centre(verts):
    # Sphere fit via least squares, same as the scan scripts.
    import numpy as np
    V = np.array([[v.x, v.y, v.z] for v in verts], dtype=np.float64)
    A = np.hstack([2.0 * V, np.ones((len(V), 1))])
    b = np.sum(V ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, V


def find_grapes(V, c):
    import numpy as np
    v = V - c
    r = np.linalg.norm(v, axis=1)
    u = v / np.maximum(r[:, None], 1e-12)
    phi = np.arctan2(u[:, 1], u[:, 0])
    nz, nphi = 48, 96
    zi = np.clip(((u[:, 2] + 1) / 2 * nz).astype(int), 0, nz - 1)
    pi_ = np.clip(((phi + np.pi) / (2 * np.pi) * nphi).astype(int), 0, nphi - 1)
    cell = zi * nphi + pi_
    order = np.argsort(cell)
    cell_s, r_s, u_s = cell[order], r[order], u[order]
    edges = np.flatnonzero(np.diff(cell_s)) + 1
    groups = np.split(np.arange(len(cell_s)), edges)
    rb = np.array([r_s[g].mean() for g in groups])
    ub = np.array([u_s[g].mean(axis=0) for g in groups])
    ub /= np.maximum(np.linalg.norm(ub, axis=1, keepdims=True), 1e-12)

    cos_n = math.cos(math.radians(14.0))
    dots = ub @ ub.T
    peak_idx = []
    for i in range(len(ub)):
        near = (dots[i] > cos_n).nonzero()[0]
        if i == near[rb[near].argmax()]:
            peak_idx.append(i)
    peak_idx = np.asarray(peak_idx)
    order = peak_idx[np.argsort(rb[peak_idx])[::-1]]
    cos_sep = math.cos(math.radians(MIN_SEP_DEG))
    keep = []
    for i in order:
        if keep and (ub[keep] @ ub[i] > cos_sep).any():
            continue
        keep.append(i)
    dirs = ub[keep]
    peak_r = rb[keep]
    centres = c + (K * peak_r)[:, None] * dirs
    radii = (1.0 - K) * peak_r * PACK
    return centres, radii


def add_grapes(centres, radii):
    grape_col = collection("Grapes")
    m = mat("GrapeFlesh", (0.92, 0.42, 0.12))
    grapes = []
    for i, (loc, radius) in enumerate(zip(centres, radii)):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=96,
            ring_count=48,
            radius=float(radius),
            location=(float(loc[0]), float(loc[1]), float(loc[2])),
        )
        obj = bpy.context.object
        obj.name = f"grape_{i:02d}"
        obj.data.materials.clear()
        obj.data.materials.append(m)
        obj.display_type = "WIRE"
        obj.hide_render = True
        bpy.ops.object.shade_smooth()
        link(obj, grape_col)
        grapes.append(obj)
        if i == 0:
            log(f"grape_00 has {len(obj.data.vertices)} verts")
    return grapes


def add_union(grapes, centres, radii):
    col = collection("Union")
    src = grapes[0]
    union = src.copy()
    union.data = src.data.copy()
    union.name = "BerryUnion"
    union.data.name = "BerryUnion"
    union.display_type = "SOLID"
    union.hide_render = False
    union.hide_viewport = False
    union.hide_set(False)
    union.data.materials.clear()
    union.data.materials.append(mat("UnionFlesh", (0.95, 0.48, 0.14)))
    link(union, col)
    bpy.context.view_layer.objects.active = union
    union.select_set(True)
    n0 = len(union.data.vertices)
    loc = union.matrix_world.translation
    log(f"union at {tuple(round(x, 3) for x in loc)}")
    ops = collection("GrapeOps")
    for g in grapes[1:]:
        if g.name not in ops.objects:
            ops.objects.link(g)
    mod = union.modifiers.new("pack", "BOOLEAN")
    mod.operation = "UNION"
    applied = False
    if hasattr(mod, "operand_type"):
        try:
            mod.operand_type = "COLLECTION"
            mod.collection = ops
            for solver in ("MANIFOLD", "EXACT", "FLOAT"):
                try:
                    mod.solver = solver
                    break
                except TypeError:
                    continue
            bpy.ops.object.modifier_apply(modifier=mod.name)
            applied = True
            log("boolean collection union")
        except Exception as e:
            log(f"collection boolean failed: {e}")
            try:
                union.modifiers.remove(mod)
            except Exception:
                pass
    if not applied:
        for i, g in enumerate(grapes[1:], start=1):
            m = union.modifiers.new(name=f"union_{i:02d}", type="BOOLEAN")
            m.operation = "UNION"
            m.object = g
            for solver in ("MANIFOLD", "EXACT", "FLOAT"):
                try:
                    m.solver = solver
                    break
                except TypeError:
                    continue
            bpy.ops.object.modifier_apply(modifier=m.name)
    log(f"union verts {n0} -> {len(union.data.vertices)}")
    _clean_boolean_mesh(union)
    _mark_join_lines(union)
    bpy.ops.object.shade_smooth()
    for p in union.data.polygons:
        p.use_smooth = True
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(60.0))
    except TypeError:
        pass
    log(f"union cage {len(union.data.vertices)} verts, sharp join lines")
    return union


def _clean_boolean_mesh(union):
    bpy.ops.object.select_all(action="DESELECT")
    union.select_set(True)
    bpy.context.view_layer.objects.active = union
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        try:
            bpy.ops.mesh.merge_by_distance(threshold=0.0002)
        except Exception:
            try:
                bpy.ops.mesh.remove_doubles(threshold=0.0002)
            except Exception:
                pass
        try:
            bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
        except Exception:
            pass
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        log("cleaned boolean mesh")
    except Exception as e:
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        log(f"boolean cleanup skipped: {e}")


def _mark_join_lines(union):
    """Mark sphere-intersection loops sharp so they read as lines, not a melt."""
    bpy.ops.object.select_all(action="DESELECT")
    union.select_set(True)
    bpy.context.view_layer.objects.active = union
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(32.0))
        bpy.ops.mesh.mark_sharp()
        bpy.ops.object.mode_set(mode="OBJECT")
        log("marked join lines sharp")
    except Exception as e:
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        log(f"join mark skipped: {e}")


def bevel_joins(union, offset=0.012):
    """Turn boolean intersection loops into a readable crease."""
    bpy.ops.object.select_all(action="DESELECT")
    union.select_set(True)
    bpy.context.view_layer.objects.active = union
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_mode(type="EDGE")
        try:
            bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(22.0))
        except TypeError:
            bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.bevel(
            offset_type="OFFSET",
            offset=offset,
            segments=3,
            profile=0.28,
            affect="EDGES",
        )
        bpy.ops.object.mode_set(mode="OBJECT")
        log("bevelled sharp join edges")
    except Exception as e:
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        log(f"bevel skipped: {e}")


def define_joins(union, centres, radii, depth=0.028):
    """Pull vertices that sit on two grapes inward so every join is a groove."""
    import numpy as np
    mw = union.matrix_world
    imw = mw.inverted()
    C = np.asarray(centres, dtype=np.float64)
    R = np.asarray(radii, dtype=np.float64)
    sigma = 0.022 * float(np.mean(R))
    mesh = union.data
    try:
        mesh.calc_normals()
    except Exception:
        pass
    pulled = 0
    for v in mesh.vertices:
        p = np.array(mw @ v.co, dtype=np.float64)
        d = np.abs(np.linalg.norm(p - C, axis=1) - R)
        two = np.partition(d, 1)[:2]
        w = math.exp(-((two[0] ** 2 + two[1] ** 2) / (2.0 * sigma ** 2)))
        if w < 0.35:
            continue
        n = Vector(v.normal)
        if n.length < 1e-8:
            continue
        # Inward along the surface normal (valleys already point in).
        delta = -n.normalized() * (depth * w)
        v.co = imw @ (mw @ v.co + delta)
        pulled += 1
    mesh.update()
    log(f"deepened {pulled} join vertices")


def import_color_source(photo_centre, scale):
    """Textured scan, same frame as the ghost, used only to steal colour."""
    if not os.path.exists(GLB):
        return None
    bpy.ops.import_scene.gltf(filepath=GLB)
    meshes = [o for o in bpy.context.scene.objects
              if o.type == "MESH" and o.name != "provenance_ghost"
              and not o.name.startswith("grape")
              and o.name != "BerryUnion"]
    if not meshes:
        return None
    src = max(meshes, key=lambda o: len(o.data.vertices))
    bpy.ops.object.select_all(action="DESELECT")
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    src.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.scene.cursor.location = photo_centre
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    src.location = (0.0, 0.0, 0.0)
    src.scale = (scale, scale, scale)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    src.name = "color_source"
    src.hide_render = True
    src.hide_viewport = True
    src.hide_select = True
    link(src, collection("Ghost"))
    log(f"color source {len(src.data.vertices)} verts")
    return src


def _blur_vertex_colours(mesh, colours, iterations=10):
    """Kill the blotchy nearest-texel look so hue reads as flesh, not pixels."""
    import numpy as np
    n = len(mesh.vertices)
    adj = [[] for _ in range(n)]
    for e in mesh.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    out = colours
    for _ in range(iterations):
        nxt = out.copy()
        for i, nbrs in enumerate(adj):
            if not nbrs:
                continue
            nxt[i] = 0.35 * out[i] + 0.65 * out[nbrs].mean(axis=0)
        out = nxt
    return np.clip(out, 0.0, 1.0)


def paint_from_scan(union, source, centres, radii):
    """Brighter orange at the stem, darker orange toward the crown."""
    import numpy as np
    mesh = union.data
    n = len(mesh.vertices)
    mw = union.matrix_world
    C = np.asarray(centres, dtype=np.float64)
    R = np.asarray(radii, dtype=np.float64)
    sigma = 0.34 * float(np.mean(R))
    zs = np.zeros(n, dtype=np.float64)
    crease = np.zeros(n, dtype=np.float64)
    for i, v in enumerate(mesh.vertices):
        p = np.array(mw @ v.co, dtype=np.float64)
        zs[i] = p[2]
        d = np.abs(np.linalg.norm(p - C, axis=1) - R)
        two = np.partition(d, 1)[:2]
        crease[i] = math.exp(-float(two[1]) / max(sigma, 1e-6))
    crease = _blur_vertex_colours(
        mesh, np.repeat(crease[:, None], 3, axis=1), iterations=6
    )[:, 0]
    log(f"height z {zs.min():.3f} .. {zs.max():.3f}, "
        f"crease mean {crease.mean():.3f} max {crease.max():.3f}")
    # Crease mask only. Height colour lives in the shader so it cannot contour.
    if "Col" in mesh.color_attributes:
        mesh.color_attributes.remove(mesh.color_attributes["Col"])
    attr = mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    try:
        mesh.color_attributes.active_color = attr
    except Exception:
        pass
    for i in range(n):
        c = float(np.clip(crease[i], 0.0, 1.0))
        attr.data[i].color = (c, c, c, 1.0)
    log("wrote join mask")
    return float(zs.min()), float(zs.max())


def flesh_material(z_min, z_max):
    """Crown, side, and stem colours from the photo rings. Smooth world-Z ramp."""
    m = bpy.data.materials.new("BakeappleFlesh")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeMapRange")
    cr = nt.nodes.new("ShaderNodeValToRGB")
    mix_j = nt.nodes.new("ShaderNodeMixRGB")
    col = nt.nodes.new("ShaderNodeVertexColor")
    for key in ("layer_name", "item_name", "attribute_name"):
        if hasattr(col, key):
            setattr(col, key, "Col")
            break
    nt.links.new(geom.outputs["Position"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Value"])
    span = max(float(z_max - z_min), 1e-6)
    ramp.inputs["From Min"].default_value = float(z_min) - 0.12 * span
    ramp.inputs["From Max"].default_value = float(z_max) + 0.08 * span
    ramp.inputs["To Min"].default_value = 0.0
    ramp.inputs["To Max"].default_value = 1.0
    try:
        ramp.clamp = False
    except Exception:
        pass
    try:
        ramp.interpolation_type = "SMOOTHSTEP"
    except Exception:
        pass
    nt.links.new(ramp.outputs["Result"], cr.inputs["Factor"])
    # Upright -5 / inverted 40: paler golden stem. 15 deg: side orange. 40 deg: deep crown.
    cr.color_ramp.interpolation = "EASE"
    cr.color_ramp.elements[0].position = 0.0
    cr.color_ramp.elements[0].color = (0.42, 0.12, 0.035, 1.0)
    cr.color_ramp.elements[1].position = 1.0
    cr.color_ramp.elements[1].color = (0.30, 0.042, 0.022, 1.0)
    mid = cr.color_ramp.elements.new(0.48)
    mid.color = (0.38, 0.072, 0.028, 1.0)
    fac_in = "Factor" if "Factor" in mix_j.inputs else "Fac"
    if "Color" in col.outputs:
        try:
            sep_c = nt.nodes.new("ShaderNodeSeparateColor")
        except Exception:
            sep_c = nt.nodes.new("ShaderNodeSeparateRGB")
        nt.links.new(col.outputs["Color"], sep_c.inputs[0])
        nt.links.new(sep_c.outputs[0], mix_j.inputs[fac_in])
    nt.links.new(cr.outputs["Color"], mix_j.inputs["Color1"])
    mix_j.inputs["Color2"].default_value = (0.22, 0.035, 0.018, 1.0)
    nt.links.new(mix_j.outputs["Color"], bsdf.inputs["Base Color"])
    if "Subsurface Color" in bsdf.inputs:
        nt.links.new(mix_j.outputs["Color"], bsdf.inputs["Subsurface Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    def set_in(name, value):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
    set_in("Roughness", 0.38)
    set_in("Specular IOR Level", 0.4)
    set_in("Coat Weight", 0.14)
    set_in("Coat Roughness", 0.28)
    set_in("Subsurface Weight", 0.22)
    if "Subsurface Radius" in bsdf.inputs:
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.12, 0.04)
    if "Subsurface Scale" in bsdf.inputs:
        bsdf.inputs["Subsurface Scale"].default_value = 0.06
    try:
        bsdf.subsurface_method = "RANDOM_WALK"
    except Exception:
        pass
    return m


def add_ref_plane(path, name, location, rotation, height):
    if not os.path.exists(path):
        log(f"skip missing ref {path}")
        return None
    img = bpy.data.images.load(path)
    asp = img.size[0] / max(img.size[1], 1)
    bpy.ops.mesh.primitive_plane_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (height * asp, height, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    obj.data.materials.append(m)
    link(obj, collection("Refs"))
    obj.hide_render = True
    return obj


def setup_view(union):
    cam_data = bpy.data.cameras.new("LookdevCam")
    cam = bpy.data.objects.new("LookdevCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    verts = [union.matrix_world @ v.co for v in union.data.vertices]
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    zs = [v.z for v in verts]
    acc = Vector((0, 0, 0))
    for v in verts:
        acc += v
    target = acc / max(len(verts), 1)
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    log(f"union span {span:.3f} m")
    cam.location = target + Vector((0.10 * span, -2.35 * span, 0.28 * span))
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = 50

    bpy.context.scene.render.engine = "CYCLES"
    cycles = bpy.context.scene.cycles
    cycles.samples = 96
    cycles.use_denoising = True
    try:
        bpy.context.scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    bpy.context.scene.render.resolution_x = 1400
    bpy.context.scene.render.resolution_y = 900
    bpy.context.scene.render.filepath = PNG_OUT
    bpy.context.scene.render.film_transparent = False

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.62, 0.58, 0.52, 1)
        bg.inputs[1].default_value = 0.55

    key = bpy.data.lights.new("Key", "AREA")
    key.energy = 48
    key.size = 2.8
    key_ob = bpy.data.objects.new("Key", key)
    key_ob.location = (0.7, -2.1, 0.45)
    key_ob.rotation_euler = (1.1, 0.08, 0.25)
    bpy.context.scene.collection.objects.link(key_ob)

    fill = bpy.data.lights.new("Fill", "AREA")
    fill.energy = 38
    fill.size = 3.6
    fill_ob = bpy.data.objects.new("Fill", fill)
    fill_ob.location = (0.1, -1.0, -0.7)
    bpy.context.scene.collection.objects.link(fill_ob)

    bounce = bpy.data.lights.new("Bounce", "AREA")
    bounce.energy = 22
    bounce.size = 3.0
    bounce_ob = bpy.data.objects.new("Bounce", bounce)
    bounce_ob.location = (0.3, 1.5, 0.15)
    bpy.context.scene.collection.objects.link(bounce_ob)

    try:
        union.cycles.shadow_terminator_offset = 0.45
        union.cycles.shadow_terminator_geometry_offset = 0.15
    except Exception:
        pass

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                space.shading.type = "RENDERED"
                space.shading.use_scene_world = True
                space.shading.use_scene_lights = True


def main():
    if not os.path.exists(GLB) and not os.path.exists(PLY):
        sys.exit(f"missing provenance mesh")
    clear_scene()
    ghost, scale, photo_centre = import_ghost()
    verts = world_verts(ghost)
    c, V = fit_centre(verts)
    centres, radii = find_grapes(V, c)
    log(f"seated {len(centres)} grapes, scene scale {scale:.3f}")
    grapes = add_grapes(centres, radii)
    union = add_union(grapes, centres, radii)
    source = import_color_source(photo_centre, scale)
    z_min, z_max = paint_from_scan(union, source, centres, radii)
    union.data.materials.clear()
    union.data.materials.append(flesh_material(z_min, z_max))
    add_ref_plane(
        os.path.join(REF_DIR, "ref_40.jpg"),
        "ref_40",
        location=(1.55, 0.0, 0.35),
        rotation=(math.pi / 2, 0.0, math.pi / 2),
        height=1.15,
    )
    add_ref_plane(
        os.path.join(REF_DIR, "ref_15.jpg"),
        "ref_15",
        location=(-1.55, 0.0, 0.1),
        rotation=(math.pi / 2, 0.0, -math.pi / 2),
        height=1.15,
    )
    add_ref_plane(
        os.path.join(REF_DIR, "ref_c01_m5.jpg"),
        "ref_m5",
        location=(0.0, 1.7, 0.0),
        rotation=(math.pi / 2, 0.0, math.pi),
        height=1.05,
    )
    setup_view(union)
    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    os.makedirs(os.path.dirname(GLB_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

    bpy.ops.object.select_all(action="DESELECT")
    union.hide_set(False)
    union.select_set(True)
    bpy.context.view_layer.objects.active = union
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        use_selection=True,
        export_format="GLB",
        export_apply=True,
    )
    bpy.ops.render.render(write_still=True)
    log(f"wrote {BLEND_OUT}")
    log(f"wrote {GLB_OUT}")
    log(f"wrote {PNG_OUT}")


if __name__ == "__main__":
    main()
