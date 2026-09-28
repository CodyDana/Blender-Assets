"""Diagnostic only (not shipped): split each LOD by material into its own FBX (pipeline settings) to find
which part makes Unreal warn about nearly zero tangents.  blender -b BLEND --python co_diag_export.py -- TAG"""
import bpy, sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline.export_fbx import base_settings
tag = sys.argv[sys.argv.index("--") + 1]
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/closeout/diag_tangent"
src = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("SM_BlackHat_LOD")]
for o in src:
    for mi in (0, 1):
        me = o.data.copy()
        import bmesh
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != mi], context='FACES')
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(f"SM_Diag_{tag}_{o.name[-4:]}_{mi}", me)
        bpy.context.scene.collection.objects.link(ob)
        ob.matrix_world = o.matrix_world.copy()
        for x in bpy.data.objects: x.select_set(False)
        ob.select_set(True); bpy.context.view_layer.objects.active = ob
        s = base_settings("static"); s["filepath"] = f"{OUT}/{ob.name}.fbx"
        bpy.ops.export_scene.fbx(**s)
print("DIAG EXPORT DONE")
