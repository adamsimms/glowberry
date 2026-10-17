"""Voxel-remesh a mesh into one closed surface, headless in Blender.

Called by print_ready.py. Voxel size is a fraction of the largest extent.

    Blender -b --factory-startup -P voxel_remesh_blender.py -- IN OUT FRACTION
"""

import sys

import bpy

src, dst, frac = sys.argv[sys.argv.index("--") + 1:][:3]
frac = float(frac)

bpy.ops.wm.read_factory_settings(use_empty=True)
if src.lower().endswith((".glb", ".gltf")):
    bpy.ops.import_scene.gltf(filepath=src)
else:
    bpy.ops.wm.ply_import(filepath=src)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

obj.data.remesh_voxel_size = max(obj.dimensions) * frac
obj.data.use_remesh_fix_poles = True
bpy.ops.object.voxel_remesh()

bpy.ops.wm.ply_export(filepath=dst, export_selected_objects=True,
                      export_uv=False, export_normals=False, export_colors="NONE",
                      apply_modifiers=True, ascii_format=False)
print("VOXEL_OK", len(obj.data.polygons))
