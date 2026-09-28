"""Diagnostic only: whole LOD meshes, each its own FBX (pipeline settings); and vertices shared by both materials."""
import bpy, sys, json
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline.export_fbx import base_settings
tag = sys.argv[sys.argv.index("--") + 1]
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/closeout/diag_tangent"
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("SM_BlackHat_LOD")]:
    me = o.data
    vm = {}
    for p in me.polygons:
        for v in p.vertices: vm.setdefault(v, set()).add(p.material_index)
    shared = [v for v, s in vm.items() if len(s) > 1]
    print("SHARED", tag, o.name, len(shared), [tuple(round(c * 1000, 1) for c in me.vertices[v].co) for v in shared[:6]])
    ob = bpy.data.objects.new(f"SM_Diag_{tag}_{o.name[-4:]}_all", me.copy())
    bpy.context.scene.collection.objects.link(ob); ob.matrix_world = o.matrix_world.copy()
    for x in bpy.data.objects: x.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    s = base_settings("static"); s["filepath"] = f"{OUT}/{ob.name}.fbx"
    bpy.ops.export_scene.fbx(**s)
