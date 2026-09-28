import bpy
sc=bpy.context.scene
for vl in sc.view_layers: print("VL", vl.name, vl.material_override, vl.use_pass_combined)
print("SC", sc.name, [s.name for s in bpy.data.scenes], sc.render.engine)
