import bpy, sys, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
from gunlib import tspace as TS
for f in sorted((HERE / "tanexp").glob("TV0*.fbx")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(f))
    ob = [o for o in bpy.data.objects if o.type == "MESH"][0]; me = ob.data
    UV, LV, V, CN = TS._arrays(me, "UV0")
    fn = np.array([p.normal[:] for p in me.polygons]); face = np.repeat(np.arange(len(me.polygons)), 3)
    dot = np.abs((fn[face] * CN).sum(1))
    print("EO", f.stem, "corners", len(LV), "edge-on<5deg", int((dot < 0.087).sum()), "<2deg", int((dot < 0.035).sum()))
