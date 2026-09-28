"""Round 2 painter iteration on a DEV build (never the shipped exports): re-run the painter on cached LOD0 bakes,
write the maps into the dev build's Textures, reload them and render the reference row + close-ups.
    blender -b --factory-startup DEV/Assets/Flashbang.blend --python r2_paint_iter.py -- DEV OUT [spp] [views]
"""
import importlib
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts"))
sys.path.insert(0, str(P / "Scripts/props"))
sys.dont_write_bytecode = True
argv = sys.argv[sys.argv.index("--") + 1:]
DEV = Path(argv[0]).resolve()
OUT = Path(argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
spp = int(argv[2]) if len(argv) > 2 else 64
views = argv[3].split(",") if len(argv) > 3 else ["row", "p1", "p2", "p3", "p4"]
assert "Exports" not in str(DEV).split("WorkFiles")[0][-10:] and "WorkFiles" in str(DEV), DEV

import build_flashbang as BF                        # noqa: E402
from props_lib import flashbang_paint as FP         # noqa: E402
from props_lib import flashbang_geom as G           # noqa: E402
from props_lib import flashbang_gallery as GAL      # noqa: E402
from props_lib.flashbang_spec import FLASHBANG as S  # noqa: E402

BF.EXPORTS = DEV / "Exports"
BF.TEXTURES = BF.EXPORTS / "Textures"
BF.RECOLOUR = BF.TEXTURES / "Recolour"
BF.BUILD_WORK = DEV / "build"
cache = DEV / "build" / "bakes_lod0.npz"
lod0 = bpy.data.objects.get("SM_Flashbang_LOD0")
t0 = time.time()
if cache.is_file():
    z = np.load(cache)
    bk = {k: z[k] for k in z.files}
else:
    bk = FP.bake_inputs(lod0, S.atlas_px, samples=16, log=print)
    np.savez(cache, **bk)
FP.bake_inputs = lambda *a, **k: bk
builders = [G.build_lod(S, i)[0] for i in range(len(S.lods))]
for mb in builders:
    importlib.import_module("props_lib.flashbang_blender").fix_island_handedness(mb)
packing = G.pack_islands(builders, S.atlas_px, S.padding_px)
report = {}
objs = {"assembled": [lod0]}
paths, maps = BF.stage_textures(S, objs, packing, None, report, quick=True)
print("paint stats", json.dumps(report["textures"]["paint"]))
fresh = {}
for key in ("BC", "ORM", "N"):
    im = bpy.data.images.load(str(paths[key]), check_existing=False)
    im.colorspace_settings.name = "sRGB" if key == "BC" else "Non-Color"
    fresh[f"T_Flashbang_{key}"] = im
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    for nd in mat.node_tree.nodes:
        if nd.type == "TEX_IMAGE" and nd.image is not None:
            for k, im in fresh.items():
                if nd.image.name.startswith(k):
                    nd.image = im
print(f"maps in {time.time() - t0:.1f}s")
if "row" in views:
    GAL.render_row(lod0, OUT / "row.png", None, samples=spp)
    m = GAL.row_metrics(str(OUT / "row.png"))
    (OUT / "row_metrics.json").write_text(json.dumps(m, indent=1))
    for v in ("v1", "v2", "v3", "v4"):
        print(v, "paint ref", m[v]["paint_p10_p50_p90_ref"], "ours", m[v]["paint_p10_p50_p90_ours"])
    print("bg", m["background_p50_ref"], m["background_p50_ours"])
for k in ("p1", "p2", "p3", "p4"):
    if k in views:
        GAL.render_closeup(lod0, k, OUT / f"{k}.png", samples=spp)
(OUT / "paint_stats.json").write_text(json.dumps(report["textures"]["paint"], indent=1))
print(f"done in {time.time() - t0:.1f}s")
