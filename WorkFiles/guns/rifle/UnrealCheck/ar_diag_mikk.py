import bpy, sys, json, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
from gunlib import tspace as TS
d = json.loads((HERE / "ar_fbxa_ntb.json").read_text())
for f in sorted((HERE / "tanexp").glob("*.fbx")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(f))
    ob = [o for o in bpy.data.objects if o.type == "MESH"][0]; me = ob.data
    sc = ob.matrix_world.to_scale()[0] * 100.0
    m = TS.mikk_float32(me, "UV0", scale=sc)
    ue = d.get("ue_" + f.stem, {})
    print("MK", f.stem, "pred_zero", int((m < 1e-6).sum()), "pred_lt1e-4", int((m < 1e-4).sum()), "ue_zero", ue.get("zero_tangent"))
