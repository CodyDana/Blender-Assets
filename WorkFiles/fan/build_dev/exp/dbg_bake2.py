import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import bpy, numpy as np
from props_lib import fan_look as LK, fan_geom as G, fan_fold as FF
from props_lib.fan_spec import FAN
LK.reset_scene()
fs = FF.FoldSolver(FAN)
mb, info, _ = G.build_lod(FAN, 0, fs.tpl)
front = mb.subset([t for t in range(len(mb.T)) if mb.TLAY[t] != "back"])
mats = [LK.plain_material(f"M_{k}") for k in range(3)]
ob = LK.mesh_object(front, "__AO_Fan", mats)
print("polys", len(ob.data.polygons), "verts", len(ob.data.vertices))
bpy.context.scene.world = bpy.data.worlds.new("w")
try:
    out = LK.bake_ao(ob, {0: 256, 1: 256, 2: 64}, samples=4)
    print({k: v.mean() for k, v in out.items()})
except Exception as e:
    print("ERR", e)
