import bpy, json, sys
import numpy as np
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Final2")
import kv_common as C
for name in C.MESHES:
    for src in (C.EXP / f"{name}.fbx",):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(src))
        for ob in sorted(bpy.data.objects, key=lambda o: o.name):
            if ob.name.startswith("UCX_"):
                M = np.array(ob.matrix_world)
                V = np.array([tuple(v.co) for v in ob.data.vertices]) @ M[:3, :3].T * 100 + M[:3, 3] * 100
                # z-extent of the hull along x near the blade (all), and at the centre line
                print("HZ", ob.name, "z", V[:, 2].min().round(3), V[:, 2].max().round(3), "x", V[:, 0].min().round(3), V[:, 0].max().round(3), "y", V[:, 1].min().round(3), V[:, 1].max().round(3))
