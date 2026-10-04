"""t8 (judge r7 item 3): the solid-bead skirt on the exported drum LOD0: per skirt island (the collar-material loose
parts below the collar lathe), its self-intersecting triangle pairs (pairs sharing no vertex), its intersecting pairs
with the lacquered barrel, and the collar UV range (U < 0 wrapped onto the strip's white end in t7).

Run: blender -b -t 4 --factory-startup --python skirt_check_t8.py
"""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t8" / "skirt_check.json"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT / "Exports" / "DojoKit" / "Props" / "taiko" / "SM_DKP_Taiko_Drum.fbx"))
o = next(ob for ob in bpy.data.objects if ob.name.endswith("Drum_LOD0"))
me = o.data
M = o.matrix_world
V = [M @ v.co for v in me.vertices]
mats = [m.name for m in me.materials]
col_i = [i for i, n in enumerate(mats) if "Collar" in n]
lac_i = [i for i, n in enumerate(mats) if "Lacquer" in n]
parent = list(range(len(V)))


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


for e in me.edges:
    a, b = find(e.vertices[0]), find(e.vertices[1])
    if a != b:
        parent[a] = b
polys = list(me.polygons)
isl = {}
for p in polys:
    if p.material_index in col_i:
        isl.setdefault(find(p.vertices[0]), []).append(p.index)
uvl = me.uv_layers[0].data
res = {"islands": []}
lac = [list(p.vertices) for p in polys if p.material_index in lac_i]
lac_bvh = BVHTree.FromPolygons(V, lac)
for c, fids in isl.items():
    xs = [abs(V[v].x) for f in fids for v in polys[f].vertices]
    F = [list(polys[f].vertices) for f in fids]
    b = BVHTree.FromPolygons(V, F)
    self_pairs = [(i, j) for i, j in b.overlap(b) if i < j and not set(F[i]) & set(F[j])]
    us = [uvl[li].uv[0] for f in fids for li in polys[f].loop_indices]
    res["islands"].append({"faces": len(fids), "x_abs_min_max": [round(min(xs), 4), round(max(xs), 4)],
                           "self_intersecting_pairs": len(self_pairs),
                           "barrel_intersecting_pairs": len(b.overlap(lac_bvh)),
                           "uv0_u_min_max": [round(min(us), 4), round(max(us), 4)]})
res["islands"].sort(key=lambda d: -d["faces"])
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("SKIRTCHECK", json.dumps(res))
