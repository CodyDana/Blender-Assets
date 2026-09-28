import bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="C:/Users/Cody/Desktop/Blender_Projects/Exports/Flashbang/SM_Flashbang.fbx")
o = bpy.data.objects["SM_Flashbang_LOD0"]
v = np.array([(o.matrix_world @ x.co)[:] for x in o.data.vertices]) * 1000
r = np.hypot(v[:, 0], v[:, 1])
for z0 in range(0, 168, 3):
    s = (v[:, 2] >= z0) & (v[:, 2] < z0 + 3)
    if s.any():
        print("M2Z", z0, "rmax %.2f" % r[s].max(), "rmed %.2f" % np.median(r[s]), "x[%.1f,%.1f] y[%.1f,%.1f]" % (v[s, 0].min(), v[s, 0].max(), v[s, 1].min(), v[s, 1].max()))
print("M2B", v.min(0), v.max(0))
