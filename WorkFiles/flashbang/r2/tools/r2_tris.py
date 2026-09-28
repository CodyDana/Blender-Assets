import sys, collections
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from props_lib import flashbang_geom as G
from props_lib.flashbang_spec import FLASHBANG as S
for lod in range(3):
    mb, info = G.build_lod(S, lod)
    c = collections.Counter(); ci = collections.Counter()
    for f in mb.faces:
        c[f.part] += len(f.v) - 2
        ci[f.island.rsplit('_', 1)[0] if f.island.endswith(('_a', '_b')) else f.island] += len(f.v) - 2
    print("LOD", lod, mb.tri_count(), dict(c))
    print("   ", sorted(ci.items(), key=lambda x: -x[1]))
