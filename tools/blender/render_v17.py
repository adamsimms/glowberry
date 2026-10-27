"""Presentation renders of the picked berry (v17) at full size, for applications.

Headless Blender (Cycles, or EEVEE for the turntable). The berry is the
plain v17 mesh scaled to 1.83 m (6 ft), coloured with the print gradient
(amber #F79523 at the base to red-orange #ED541F at the tip), with a thin
translucent shell so a light inside reads through it.

Modes:
- hero: transparent background with a soft shadow, for layouts
- studio: seamless grey backdrop
- night: dark scene, berry lit from inside
- turntable: studio look, one full turn as numbered PNG frames

    Blender -b --factory-startup -P tools/blender/render_v17.py -- MODE OUT [SIZE] [SAMPLES]

OUT is a PNG path, or a folder for the turntable.
"""

import math
import os
import sys

import bpy
import mathutils

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
berry.scale = (s, s, s)
bpy.ops.object.transform_apply(scale=True)
bb = [berry.matrix_world @ mathutils.Vector(c) for c in berry.bound_box]
lo = mathutils.Vector([min(v[i] for v in bb) for i in range(3)])
hi = mathutils.Vector([max(v[i] for v in bb) for i in range(3)])
berry.location -= mathutils.Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
bpy.ops.object.transform_apply(location=True)
bpy.ops.object.shade_smooth()

# Gradient as a colour attribute, eased like the print files but unbanded.
me = berry.data
attr = me.color_attributes.new("grad", "FLOAT_COLOR", "POINT")
for i, v in enumerate(me.vertices):
    t = min(max(v.co.z / HEIGHT_M, 0.0), 1.0)
    t = t * t * (3 - 2 * t)
    attr.data[i].color = [lin(BASE[k] * (1 - t) + TIP[k] * t) for k in range(3)] + [1.0]

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
bsdf.inputs["Coat Weight"].default_value = float(os.environ.get("GB_COAT", 0.1 if MODE == "night" else 0.35))
bsdf.inputs["Coat Roughness"].default_value = 0.12
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
    # Dusk just after sunset: physical sky with the sun a few degrees below
    # the horizon, behind and to the left of the berry.
    wn = sc.world.node_tree
    sky = wn.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(float(os.environ.get("GB_SUN_EL", -4.0)))
    sky.sun_rotation = math.radians(150)
    wn.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = float(os.environ.get("GB_SKY", 5.0))
    f = floor(400.0)
    gm = material("ground", (0.05, 0.055, 0.04), 0.8)
    gnt = gm.node_tree
    noise = gnt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    bump = gnt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    gnt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    gb = next(n for n in gnt.nodes if n.type == "BSDF_PRINCIPLED")
    gnt.links.new(bump.outputs["Normal"], gb.inputs["Normal"])
    f.data.materials.append(gm)
    glow = bpy.data.objects.new("glow", bpy.data.lights.new("glow", "POINT"))
    glow.data.energy = 450
    glow.data.shadow_soft_size = 0.3
    glow.data.color = (1.0, 0.93, 0.78)
    glow.location = (0, 0, 0.85)
    sc.collection.objects.link(glow)
    area("moon", (2.5, 4.0, 4.0), (0, 0, 1.0), 3.0, float(os.environ.get("GB_MOON", 900)), (0.65, 0.75, 1.0))
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
    bpy.ops.render.render(write_still=True)
