"""DEV: build LOD0 (clay) and render the reference top row with one camera, four copies at given yaws.
blender -b --factory-startup --python fb_clay_row.py -- out.png [yaw1 yaw2 yaw3 yaw4] [samples]"""
import sys, math
from pathlib import Path
P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts")); sys.path.insert(0, str(P / "Scripts/props"))
import bpy, numpy as np
from props_lib import flashbang_geom as G, flashbang_blender as FB, flashbang_look as LK
from props_lib.flashbang_spec import FLASHBANG as S

a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]
yaws = [float(x) for x in a[1:5]] if len(a) >= 5 else [-134.0, 51.0, 41.0, -27.0]
samples = int(a[5]) if len(a) > 5 else 48
bpy.ops.wm.read_factory_settings(use_empty=True)
mbs = [G.build_lod(S, l)[0] for l in range(1)]
for mb in mbs:
    FB.fix_island_handedness(mb)
pk = G.pack_islands(mbs)
clay = LK.clay_material()
ob = FB.to_blender(mbs[0], pk, "SM_Flashbang_LOD0", materials=[clay, clay])
objs = {"v1": [ob]}
for v in ("v2", "v3", "v4"):
    o2 = ob.copy()
    bpy.context.scene.collection.objects.link(o2)
    objs[v] = [o2]
LK.setup_cycles(samples)
rig = LK.Rig()
LK.studio(rig)
cam, info = LK.row_camera(rig)
print("camera", info)
LK.place_row(objs, dict(zip(("v1", "v2", "v3", "v4"), yaws)))
LK.render(out)
