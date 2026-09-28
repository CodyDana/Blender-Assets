import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import bpy, numpy as np
import verify_fan as V
from props_lib import fan_look as LK, fan_fold as FF
LK.reset_scene()
objs = V.import_fbx(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/dev1/Exports/Fan/SK_Fan.fbx")
arm = next(o for o in objs if o.type == "ARMATURE"); mesh = next(o for o in objs if o.type == "MESH")
print("arm", arm.name, arm.matrix_world, "mesh", mesh.matrix_world, mesh.parent)
P0 = V.rest_positions(mesh)
Q = V.world_positions(mesh)
print("rest vs evaluated max diff mm", np.abs(P0 - Q).max())
print("P0 bounds", P0.min(0), P0.max(0))
b = arm.data.bones
print([ (x.name, x.parent.name if x.parent else None, tuple(round(v,4) for v in x.head_local)) for x in b][:4], [(x.name, x.parent.name if x.parent else None) for x in b][27:30])
