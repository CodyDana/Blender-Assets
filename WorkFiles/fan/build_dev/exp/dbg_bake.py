import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import bpy, numpy as np
from props_lib import fan_look as LK, fan_geom as G, fan_fold as FF
from props_lib.fan_spec import FAN
LK.reset_scene()
fs = FF.FoldSolver(FAN)
mb, info, _ = G.build_lod(FAN, 2, fs.tpl)
mats = [LK.plain_material(f"M_{k}") for k in range(3)]
ob = LK.mesh_object(mb, "__AO_Fan", mats)
print("hide_render", ob.hide_render, "visible", ob.visible_get(), "in vl", ob.name in bpy.context.view_layer.objects)
bpy.context.scene.world = bpy.data.worlds.new("w")
try:
    out = LK.bake_ao(ob, {0: 256, 1: 256, 2: 64}, samples=4)
    print({k: v.mean() for k, v in out.items()})
except Exception as e:
    print("ERR", e)
    print("selected", [o.name for o in bpy.context.selected_objects], bpy.context.active_object)
