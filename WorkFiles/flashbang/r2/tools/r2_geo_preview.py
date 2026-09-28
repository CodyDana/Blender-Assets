"""Round 2 geometry preview (no bakes): LOD0 from the CURRENT props_lib with flat per-LOOK materials, rendered in the
reference row camera + the four close-ups + an alpha row.  Blender headless:
    blender -b --factory-startup --python r2_geo_preview.py -- OUTDIR [samples] [lod]
"""
import importlib
import sys
from pathlib import Path

import bpy
import numpy as np

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts"))
sys.path.insert(0, str(P / "Scripts/props"))
sys.dont_write_bytecode = True
from props_lib import flashbang_geom as G          # noqa: E402
from props_lib import flashbang_blender as FB      # noqa: E402
from props_lib import flashbang_look as LK         # noqa: E402
from props_lib import flashbang_gallery as GAL     # noqa: E402
from props_lib.flashbang_spec import FLASHBANG as S  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
out = Path(argv[0])
out.mkdir(parents=True, exist_ok=True)
spp = int(argv[1]) if len(argv) > 1 else 48
lod = int(argv[2]) if len(argv) > 2 else 0
only = argv[3].split(",") if len(argv) > 3 else ["row", "alpha", "p1", "p2", "p3", "p4"]

bpy.ops.wm.read_factory_settings(use_empty=True)
mb, info = G.build_lod(S, lod)
packing = G.pack_islands([mb], 2048, 16)
COL = {0: ((0.075, 0.078, 0.036), 0.0, 0.5), 1: ((0.045, 0.042, 0.038), 1.0, 0.45),
       2: ((0.55, 0.40, 0.20), 1.0, 0.38), 3: ((0.02, 0.019, 0.018), 1.0, 0.6),
       4: ((0.07, 0.066, 0.06), 1.0, 0.42), 5: ((0.06, 0.056, 0.05), 1.0, 0.35), 6: ((0.05, 0.046, 0.04), 1.0, 0.5)}
mats = []
for k in range(7):
    m = bpy.data.materials.new(f"L{k}")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    c, met, r = COL[k]
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Metallic"].default_value = met
    b.inputs["Roughness"].default_value = r
    mats.append(m)
o = FB.to_blender(mb, packing, "SM_Flashbang", materials=mats[:2])
o.data.materials.clear()
for m in mats:
    o.data.materials.append(m)
lk = np.empty(len(o.data.polygons), np.int32)
o.data.attributes["fb_look"].data.foreach_get("value", lk)
o.data.polygons.foreach_set("material_index", lk)
o.data.update()
print("TRIS", mb.tri_count())
if "row" in only:
    GAL.render_row(o, out / "geo_row.png", None, samples=spp)
if "alpha" in only:
    GAL.render_row_alpha(o, out / "geo_row_alpha.png")
for k in ("p1", "p2", "p3", "p4"):
    if k in only:
        GAL.render_closeup(o, k, out / f"geo_{k}.png", samples=spp)
