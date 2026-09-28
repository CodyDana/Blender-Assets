import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import bpy, numpy as np
from pathlib import Path
from props_lib import fan_refview as RV, fan_look as LK
from props_lib.fan_spec import FAN
W = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/tune"); W.mkdir(exist_ok=True)
ref = LK.load_png(r"C:/Users/Cody/Desktop/Blender_Projects/References/Fan/fan2.png")[..., :3].astype(np.float64)
arm = bpy.data.objects["root"]; fan = bpy.data.objects["SK_Fan"]
for o in bpy.data.objects:
    if o.type == "MESH": o.hide_render = o is not fan
configs = json.loads(sys.argv[sys.argv.index("--") + 1])
for name, cfg in configs.items():
    RV.REF_LIGHTS = [tuple(l) for l in cfg["lights"]]
    RV.REF_WORLD = cfg["world"]
    res = RV.render_reference([fan], FAN, W, W / f"{name}.png", samples=32, movers=[arm])
    ren = LK.load_png(W / f"{name}.png")[..., :3].astype(np.float64)
    fid = RV.fidelity(ref, ren, res["alpha"], FAN)
    print(name, {k: (v["render_lin_p10_50_90"], v["reference_lin_p10_50_90"]) for k, v in fid["tones"].items()}, flush=True)
