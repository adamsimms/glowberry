"""Extruded text as a closed mesh, headless in Blender (Blender's built-in font).

Called by print_prep.py.

    Blender -b --factory-startup -P text_blender.py -- OUT.stl TEXT
"""

import sys

import bpy

out, text = sys.argv[sys.argv.index("--") + 1:][:2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.text_add()
obj = bpy.context.active_object
obj.data.body = text
obj.data.align_x = "CENTER"
obj.data.align_y = "CENTER"
obj.data.extrude = 0.5
obj.data.fill_mode = "BOTH"
bpy.ops.object.convert(target="MESH")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=1e-5)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.wm.stl_export(filepath=out, export_selected_objects=True, ascii_format=False)
print("TEXT_OK", len(obj.data.polygons))
