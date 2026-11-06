"""Preview of a PLY with per-vertex colour, as the colour sits in the file.

Neutral light, Standard view transform (no tone curve), so the colours shown
are the file's own. Not a prediction of a translucent print.

    Blender -b --factory-startup -P tools/blender/render_vertex_colour.py -- IN.ply OUT_PREFIX [SIZE]

Writes OUT_PREFIX_{side,three_q,tip,bottom}.png.
"""

import sys

import bpy
import mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
PLY, PREFIX = argv[0], argv[1]
SIZE = int(argv[2]) if len(argv) > 2 else 900
VIEWS = {"side": (1, -0.6, 0.15), "three_q": (0.7, -0.7, 0.45),
         "tip": (0.1, -0.2, 0.97), "bottom": (0.15, -0.25, -0.95)}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.ply_import(filepath=PLY)
ob = bpy.context.selected_objects[0]
bpy.ops.object.shade_smooth()
mat = bpy.data.materials.new("m")
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
col = nt.nodes.new("ShaderNodeVertexColor")
col.layer_name = ob.data.color_attributes[0].name
nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.4
ob.data.materials.append(mat)

bb = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
ctr = sum(bb, mathutils.Vector()) / 8
size = max((bb[6] - bb[0])[:])

sc = bpy.context.scene
try:
    sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    sc.render.engine = "BLENDER_EEVEE"
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.world = bpy.data.worlds.new("w")
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.92, 0.92, 0.92, 1)
sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = size * 1.15
sc.collection.objects.link(cam)
sc.camera = cam
key = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
key.data.energy = 2.0
sc.collection.objects.link(key)

for name, d in VIEWS.items():
    v = mathutils.Vector(d).normalized()
    cam.location = ctr + v * size * 3
    cam.rotation_euler = (-v).to_track_quat("-Z", "Y").to_euler()
    key.rotation_euler = ((-v + mathutils.Vector((0.4, 0.3, -0.6))).to_track_quat("-Z", "Y")).to_euler()
    sc.render.filepath = f"{PREFIX}_{name}.png"
    bpy.ops.render.render(write_still=True)
