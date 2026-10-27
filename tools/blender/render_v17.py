"""Presentation renders of the picked berry (v17) at full size, for applications.

Headless Blender (Cycles, or EEVEE for the turntable). The berry is the
plain v17 mesh scaled to 1.83 m (6 ft), coloured with the print gradient
(amber #F79523 at the base to red-orange #ED541F at the tip), with a thin
translucent shell so a light inside reads through it.

Modes:
- hero: transparent background with a soft shadow, for layouts
- studio: seamless grey backdrop
- night: dark scene, berry lit from inside
- day: the night framing in daylight, on a seamless sky blue backdrop
- turntable: studio look, one full turn as numbered PNG frames

    Blender -b --factory-startup -P tools/blender/render_v17.py -- MODE OUT [SIZE] [SAMPLES]

OUT is a PNG path, or a folder for the turntable.
"""

import json
import math
import os
import sys

import bpy
import mathutils
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT = argv[0], argv[1]
SIZE = int(argv[2]) if len(argv) > 2 else 3000
SAMPLES = int(argv[3]) if len(argv) > 3 else 256

ROOT = __file__.rsplit("/tools/", 1)[0]
MESH = f"{ROOT}/models/print/berry_ref_a_studio_v17_subtle_100mm.stl"
# Lit from inside, the real hollow print (wall 1.5 mm at drupelet centres to
# 3 mm at grooves, at 100 mm) makes the seams read darker, as printed.
HOLLOW = f"{ROOT}/models/print/ready_v17/2_cloudberry_resin_100mm_hollow_smooth.stl"
HEIGHT_M = 1.83
PEAKS = f"{ROOT}/models/print/v17_drupelet_peaks.json"
# Less toy-like: colour varies per drupelet, slightly less saturated, faint
# cell texture under the surface, gloss on the domes and matte in the folds.
NATURAL = os.environ.get("GB_NATURAL", "1") == "1"
BASE, TIP = (247, 149, 35), (237, 84, 31)
WALL_M = 0.02


def lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

bpy.ops.wm.stl_import(filepath=HOLLOW if MODE == "night" else MESH)
berry = bpy.context.selected_objects[0]
berry.name = "berry"
s = HEIGHT_M / berry.dimensions.z
mm_to_m = s
berry.scale = (s, s, s)
bpy.ops.object.transform_apply(scale=True)
bb = [berry.matrix_world @ mathutils.Vector(c) for c in berry.bound_box]
lo = mathutils.Vector([min(v[i] for v in bb) for i in range(3)])
hi = mathutils.Vector([max(v[i] for v in bb) for i in range(3)])
offset = mathutils.Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
berry.location -= offset
bpy.ops.object.transform_apply(location=True)
bpy.ops.object.shade_smooth()

# Gradient as a colour attribute, eased like the print files but unbanded.
me = berry.data
attr = me.color_attributes.new("grad", "FLOAT_COLOR", "POINT")
co = np.empty(len(me.vertices) * 3)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)
t = np.clip(co[:, 2] / HEIGHT_M, 0, 1)
t = t * t * (3 - 2 * t)
srgb = (1 - t)[:, None] * np.array(BASE, float) + t[:, None] * np.array(TIP, float)
if NATURAL:
    # Each drupelet a little lighter or darker and a little more amber or
    # more red; the seams between them fall in the grooves.
    peaks = np.array(json.load(open(PEAKS))["peaks_mm"]) * mm_to_m - np.array(offset)
    # Soft weights by distance to each peak, so a drupelet assigned to the
    # wrong peak fades instead of showing a hard edge.
    d2 = ((co[:, None, :] - peaks[None]) ** 2).sum(axis=2)
    sig = float(os.environ.get("GB_VAR_SOFT", 0.12))
    w = np.exp(-(d2 - d2.min(axis=1, keepdims=True)) / sig ** 2)
    w /= w.sum(axis=1, keepdims=True)
    rng = np.random.default_rng(int(os.environ.get("GB_SEED", 7)))
    value = 1 + float(os.environ.get("GB_VAR_VALUE", 0.14)) * (rng.random(len(peaks)) - 0.5)
    hue = float(os.environ.get("GB_VAR_HUE", 0.5)) * (rng.random(len(peaks)) - 0.5)
    srgb = srgb * (w @ value)[:, None] + (w @ hue)[:, None] * (np.array(TIP, float) - np.array(BASE, float))
    # A touch less saturated than the print colours, closer to real fruit.
    lum = srgb @ np.array([0.2126, 0.7152, 0.0722])
    srgb = srgb + float(os.environ.get("GB_DESAT", 0.12)) * (lum[:, None] - srgb)
c = np.clip(srgb, 0, 255) / 255
c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
attr.data.foreach_set("color", np.hstack([c, np.ones((len(c), 1))]).astype(np.float32).ravel())

if MODE != "night":
    solid = berry.modifiers.new("shell", "SOLIDIFY")
    solid.thickness = WALL_M
    solid.offset = -1.0

mat = bpy.data.materials.new("berry")
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
col = nt.nodes.new("ShaderNodeVertexColor")
col.layer_name = "grad"
nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.3
if MODE == "night":
    # Less gloss, so glowing drupelets do not mirror into the creases.
    bsdf.inputs["Roughness"].default_value = 0.45
    # Grooves read darker when lit from inside (the print files thicken the
    # wall there): scale the colour down where ambient occlusion finds a fold.
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = float(os.environ.get("GB_GROOVE_DIST", 0.15))
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(ao.outputs["AO"], inv.inputs[1])
    amt = nt.nodes.new("ShaderNodeMath")
    amt.operation = "MULTIPLY"
    amt.inputs[1].default_value = float(os.environ.get("GB_GROOVE", 1.0))
    nt.links.new(inv.outputs[0], amt.inputs[0])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "SUBTRACT"
    fac.inputs[0].default_value = 1.0
    nt.links.new(amt.outputs[0], fac.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0, 0, 0, 1)
    nt.links.new(fac.outputs[0], mix.inputs["Factor"])
    # Light scattered through the shell drifts to red; a lighter scattering
    # colour keeps the glow amber.
    lift = nt.nodes.new("ShaderNodeMix")
    lift.data_type = "RGBA"
    lift.inputs["Factor"].default_value = float(os.environ.get("GB_LIFT", 0.35))
    lift.inputs["B"].default_value = (1, 0.85, 0.6, 1)
    nt.links.new(col.outputs["Color"], lift.inputs["A"])
    nt.links.new(lift.outputs["Result"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
bsdf.inputs["Subsurface Weight"].default_value = float(os.environ.get("GB_SSS", 0.6 if MODE == "night" else 0.25))
bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.75, 0.35) if MODE == "night" else (1.0, 0.5, 0.18)
bsdf.inputs["Subsurface Scale"].default_value = float(os.environ.get("GB_SSS_SCALE", 0.01 if MODE == "night" else 0.015))
# Day highlights are broader and gentler: less coat, and a rougher one.
bsdf.inputs["Coat Weight"].default_value = float(os.environ.get("GB_COAT", {"night": 0.1, "day": 0.25}.get(MODE, 0.35)))
bsdf.inputs["Coat Roughness"].default_value = 0.22 if MODE == "day" else 0.12
if NATURAL:
    # Faint juice-sac cells under the skin: a soft cell pattern about 3 cm
    # across at full size, as a slight bump and a slight darkening.
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "SMOOTH_F1"
    vor.inputs["Scale"].default_value = float(os.environ.get("GB_CELL", 30.0))
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = float(os.environ.get("GB_CELL_BUMP", 0.12))
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    shade = nt.nodes.new("ShaderNodeMapRange")
    shade.inputs["To Min"].default_value = 1.0
    shade.inputs["To Max"].default_value = 1.0 - float(os.environ.get("GB_CELL_SHADE", 0.08))
    nt.links.new(vor.outputs["Distance"], shade.inputs["Value"])
    darken = shade.outputs["Result"]
    # Optional narrow crease mask from the mesh's own concavity (Cycles only).
    # Off by default: the seams read better as soft red lines than dark ones.
    crease_to = float(os.environ.get("GB_CREASE", 1.0))
    if crease_to < 1.0:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        crease = nt.nodes.new("ShaderNodeMapRange")
        crease.inputs["From Min"].default_value = float(os.environ.get("GB_CREASE_LO", 0.44))
        crease.inputs["From Max"].default_value = 0.5
        crease.inputs["To Min"].default_value = crease_to
        crease.inputs["To Max"].default_value = 1.0
        nt.links.new(geo.outputs["Pointiness"], crease.inputs["Value"])
        both = nt.nodes.new("ShaderNodeMath")
        both.operation = "MULTIPLY"
        nt.links.new(shade.outputs["Result"], both.inputs[0])
        nt.links.new(crease.outputs["Result"], both.inputs[1])
        darken = both.outputs["Value"]
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    base_in = bsdf.inputs["Base Color"].links[0].from_socket
    nt.links.new(base_in, mul.inputs["A"])
    nt.links.new(darken, mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
    # Gloss on the domes, matte in the folds.
    gao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    gao.inputs["Distance"].default_value = 0.12
    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.65
    rough.inputs["To Max"].default_value = 0.33 if MODE == "day" else 0.28
    nt.links.new(gao.outputs["AO"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
me.materials.append(mat)


def area(name, loc, target, size, energy, colour=(1, 1, 1), shadow=True):
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    light.data.size = size
    light.data.energy = energy
    light.data.color = colour
    light.location = loc
    light.data.use_shadow = shadow
    light.rotation_euler = (mathutils.Vector(target) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(light)
    return light


def material(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def floor(size=40.0):
    bpy.ops.mesh.primitive_plane_add(size=size)
    return bpy.context.active_object


def cyclorama(rgb, back=4.0, radius=3.0, half_w=14.0):
    """Floor that curves up into a back wall, no visible horizon."""
    prof = [(-14.0, 0.0), (back, 0.0)]
    prof += [(back + radius * math.sin(p), radius - radius * math.cos(p))
             for p in [math.radians(a) for a in range(4, 91, 4)]]
    prof.append((back + radius, 14.0))
    verts = [(x, y, z) for y, z in prof for x in (-half_w, half_w)]
    faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(prof) - 1)]
    me = bpy.data.meshes.new("cyc")
    me.from_pydata(verts, [], faces)
    cyc = bpy.data.objects.new("cyc", me)
    sc.collection.objects.link(cyc)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(material("cyc", rgb))
    return cyc


def glow_backdrop(rgb, low, high, strength, screen=False):
    """Cyclorama that glows on its own, `low` on the floor fading to `high`
    up the wall (or, with `screen`, from the bottom of the frame to the top,
    so it stays level across the frame), so the gradient is smooth; it still
    catches the berry's light and shadow. Returns the backdrop's BSDF node."""
    cn = cyclorama(rgb).data.materials[0].node_tree
    cb = next(n for n in cn.nodes if n.type == "BSDF_PRINCIPLED")
    ctc = cn.nodes.new("ShaderNodeTexCoord")
    sep = cn.nodes.new("ShaderNodeSeparateXYZ")
    cn.links.new(ctc.outputs["Window" if screen else "Object"], sep.inputs["Vector"])
    zr = cn.nodes.new("ShaderNodeMapRange")
    zr.inputs["From Max"].default_value = 1.0 if screen else 7.0
    cn.links.new(sep.outputs["Y" if screen else "Z"], zr.inputs["Value"])
    grad = cn.nodes.new("ShaderNodeMix")
    grad.data_type = "RGBA"
    grad.inputs["A"].default_value = (*low, 1)
    grad.inputs["B"].default_value = (*high, 1)
    cn.links.new(zr.outputs["Result"], grad.inputs["Factor"])
    cn.links.new(grad.outputs["Result"], cb.inputs["Emission Color"])
    cb.inputs["Emission Strength"].default_value = strength
    return cb


cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50


def aim(az_deg, el_deg, dist, target_z=0.9):
    az, el = math.radians(az_deg), math.radians(el_deg)
    target = mathutils.Vector((0, 0, target_z))
    cam.location = target + dist * mathutils.Vector((math.sin(az) * math.cos(el),
                                                     -math.cos(az) * math.cos(el), math.sin(el)))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()


sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
except Exception:
    pass
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
# Neutral transform keeps the berry's amber and orange hues (AgX pulls
# saturated orange toward salmon).
sc.view_settings.view_transform = "Khronos PBR Neutral"
sc.view_settings.exposure = float(os.environ.get("GB_EXPOSURE", -2.7 if MODE == "night" else -2.6))
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.world = bpy.data.worlds.new("w")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]

if MODE in ("hero", "studio", "turntable"):
    bg.inputs["Color"].default_value = (0.6, 0.62, 0.65, 1)
    bg.inputs["Strength"].default_value = 0.25
    area("key", (-3.0, -3.5, 3.6), (0, 0, 0.9), 3.0, 2200)
    area("fill", (3.5, -2.5, 1.8), (0, 0, 0.9), 4.0, 600, shadow=False)
    area("rim", (1.5, 3.5, 3.0), (0, 0, 1.2), 2.0, 1500, (1.0, 0.92, 0.85), shadow=False)
    aim(-30, 8, 5.6)
    if MODE == "hero":
        sc.render.film_transparent = True
        f = floor()
        f.is_shadow_catcher = True
    else:
        cyclorama((0.42, 0.42, 0.43))
        aim(-30, 8, 5.8)
    if MODE == "turntable":
        sc.render.engine = "BLENDER_EEVEE"
        sc.eevee.taa_render_samples = SAMPLES
        sc.eevee.use_raytracing = True
        sc.render.image_settings.color_mode = "RGB"
        sc.frame_start, sc.frame_end = 1, 96
        # Constant speed, so the loop has no ease at the seam.
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
        berry.rotation_euler = (0, 0, 0)
        berry.keyframe_insert("rotation_euler", index=2, frame=1)
        berry.rotation_euler = (0, 0, 2 * math.pi)
        berry.keyframe_insert("rotation_euler", index=2, frame=97)
elif MODE == "night":
    # Seamless dark navy backdrop: the floor curves up into the wall, so the
    # dark blue continues behind the berry with no horizon.
    bg.inputs["Color"].default_value = (0.006, 0.009, 0.02, 1)
    bg.inputs["Strength"].default_value = 1.0
    # Navy fading darker upward.
    glow_backdrop((0.02, 0.025, 0.04), (0.03, 0.06, 0.17), (0.008, 0.014, 0.045),
                  float(os.environ.get("GB_BACK", 1.0)))
    glow = bpy.data.objects.new("glow", bpy.data.lights.new("glow", "POINT"))
    glow.data.energy = 450
    glow.data.shadow_soft_size = 0.3
    glow.data.color = (1.0, 0.93, 0.78)
    glow.location = (0, 0, 0.85)
    sc.collection.objects.link(glow)
    area("moon", (2.5, 4.0, 4.0), (0, 0, 1.0), 3.0, float(os.environ.get("GB_MOON", 900)), (0.65, 0.75, 1.0))
elif MODE == "day":
    # The night composition in daylight: a soft sky blue backdrop, deeper
    # toward the top of the frame and hazier toward the floor, under a sky
    # and a hazy sun.
    sky = (0.55, 0.72, 1.0)
    bg.inputs["Color"].default_value = (*sky, 1)
    bg.inputs["Strength"].default_value = float(os.environ.get("GB_SKY", 1.5))
    back = float(os.environ.get("GB_BACK", 3.2))
    # The backdrop's own colour is a clear blue, so sunlight on it and its
    # shadow read as sky; the glow adds haze, lighter toward the floor.
    alb = np.array((0.16, 0.33, 0.6))
    cb = glow_backdrop(tuple(alb), (0.53, 0.6, 0.6), (0.15, 0.25, 0.22), 1.0, screen=True)
    cb.inputs["Roughness"].default_value = 1.0
    cb.inputs["Specular IOR Level"].default_value = 0.0
    cn = cb.id_data
    grad = cb.inputs["Emission Color"].links[0].from_socket

    # From the upper left and a little in front, so the shadow falls to the
    # right of the berry where the camera sees it.
    az, el = math.radians(-75), math.radians(50)
    to_sun = mathutils.Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    sun_e = float(os.environ.get("GB_SUN", 16.0))
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = sun_e
    sun.data.angle = math.radians(30)
    sun.data.color = (1.0, 0.97, 0.92)
    sun.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(sun)

    # The sun lights the floor more than the wall. The backdrop glows more
    # where the sun reaches it less, so the sweep stays even and only the
    # berry's shadow shows.
    geo = cn.nodes.new("ShaderNodeNewGeometry")
    dot = cn.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = to_sun
    cn.links.new(geo.outputs["Normal"], dot.inputs[0])
    lit = cn.nodes.new("ShaderNodeMath")
    lit.operation = "MAXIMUM"
    lit.inputs[1].default_value = 0.0
    cn.links.new(dot.outputs["Value"], lit.inputs[0])
    short = cn.nodes.new("ShaderNodeMath")
    short.operation = "SUBTRACT"
    short.inputs[0].default_value = to_sun.z
    cn.links.new(lit.outputs[0], short.inputs[1])
    comp = cn.nodes.new("ShaderNodeVectorMath")
    comp.operation = "SCALE"
    comp.inputs[0].default_value = tuple(alb * sun_e * np.array(sun.data.color) / math.pi)
    cn.links.new(short.outputs[0], comp.inputs["Scale"])
    level = cn.nodes.new("ShaderNodeVectorMath")
    level.operation = "SCALE"
    level.inputs["Scale"].default_value = back
    cn.links.new(grad, level.inputs[0])
    total = cn.nodes.new("ShaderNodeVectorMath")
    total.operation = "ADD"
    cn.links.new(level.outputs[0], total.inputs[0])
    cn.links.new(comp.outputs[0], total.inputs[1])
    cn.links.new(total.outputs[0], cb.inputs["Emission Color"])
    # Seen by the camera at full strength; it lights the berry less, so the
    # pale glow does not wash out the orange.
    lp = cn.nodes.new("ShaderNodeLightPath")
    seen = cn.nodes.new("ShaderNodeMapRange")
    seen.inputs["To Min"].default_value = 0.3
    seen.inputs["To Max"].default_value = 1.0
    cn.links.new(lp.outputs["Is Camera Ray"], seen.inputs["Value"])
    cn.links.new(seen.outputs["Result"], cb.inputs["Emission Strength"])

    # Soft fill on the berry only, so it does not mark the backdrop.
    fill = area("fill", (3.5, -2.5, 1.8), (0, 0, 0.9), 5.0, float(os.environ.get("GB_FILL", 2000)), (0.9, 0.95, 1.0), shadow=False)
    only = bpy.data.collections.new("berry_only")
    only.objects.link(berry)
    fill.light_linking.receiver_collection = only
if MODE in ("night", "day"):
    sc.render.resolution_x, sc.render.resolution_y = SIZE, int(SIZE * 2 / 3)
    sc.render.image_settings.color_mode = "RGB"
    # Low camera so the horizon and sky sit behind the upper berry.
    aim(-25, 3, 6.6, 1.0)
    cam.data.lens = 42

if MODE == "turntable":
    sc.render.filepath = OUT.rstrip("/") + "/frame_"
    bpy.ops.render.render(animation=True)
else:
    sc.render.filepath = OUT
    if os.environ.get("GB_BORDER"):
        # Test a region only: "xmin,xmax,ymin,ymax" as fractions.
        x0, x1, y0, y1 = (float(v) for v in os.environ["GB_BORDER"].split(","))
        sc.render.use_border, sc.render.use_crop_to_border = True, True
        sc.render.border_min_x, sc.render.border_max_x = x0, x1
        sc.render.border_min_y, sc.render.border_max_y = y0, y1
    bpy.ops.render.render(write_still=True)
