import sys, collections
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
from props_lib import flashbang_geom as G
from props_lib.flashbang_spec import FLASHBANG
for lod in range(3):
    mb, info = G.build_lod(FLASHBANG, lod)
    c = collections.Counter()
    for f in mb.faces:
        c[f.island.rsplit("_", 1)[0] if f.island.endswith(("_a", "_b")) else f.island] += len(f.v) - 2
    print("LOD", lod, mb.tri_count(), sorted(c.items(), key=lambda kv: -kv[1]))
