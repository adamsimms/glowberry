"""Clay render of the raw scan beside the print-ready variants, headless.

    Blender -b --factory-startup -P render_compare_blender.py -- OUT.png RAW.glb A.stl B.stl ...

Each object is scaled to the same height and set on a row. Two views: front
(top row) and underside (bottom row).
"""

import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out_png, paths = args[0], args[1:]
HEIGHT, GAP = 100.0, 30.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def import_one(path):
    before = set(scene.objects)
    if path.lower().endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.wm.stl_import(filepath=path)
    new = [o for o in scene.objects if o not in before and o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in new:
        o.select_set(True)
    bpy.context.view_layer.objects.active = new[0]
    if len(new) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.data.materials.clear()
    s = HEIGHT / obj.dimensions.z
    obj.scale = (s, s, s)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.location = (0, 0, 0)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


objs = [import_one(p) for p in paths]
step = max(o.dimensions.x for o in objs) + GAP
for i, o in enumerate(objs):
    o.location.x = (i - (len(objs) - 1) / 2) * step

scene.render.engine = "BLENDER_WORKBENCH"
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "SINGLE"
shading.single_color = (0.85, 0.42, 0.18)
shading.show_cavity = True
shading.cavity_type = "WORLD"
scene.render.resolution_x = 520 * len(objs)
scene.render.resolution_y = 560
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w")
scene.display.shading.background_type = "VIEWPORT"

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = step * len(objs)
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

base = out_png.rsplit(".", 1)[0]
for label, el in (("front", 8.0), ("under", -55.0)):
    e = math.radians(el)
    d = Vector((0, -math.cos(e), math.sin(e)))
    cam.location = d * 1000.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{base}_{label}.png"
    bpy.ops.render.render(write_still=True)
    print("RENDER_OK", scene.render.filepath)
