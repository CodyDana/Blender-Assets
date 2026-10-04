"""Finaliser check: triangle-triangle overlaps between the tsuka parts (LOD0 + LOD1) from the build's parts.pkl.
cord A vs cord B, cords vs kashira / fuchi / menuki / mekugi / eyelets. Writes final/tsuka_overlaps.json."""
import json, pickle, sys
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "Katana"))
parts = pickle.load(open(ROOT / "WorkFiles/katana/build/parts.pkl", "rb"))


def bvh(mb, pred=None):
    V = [tuple(v) for v in mb.verts]
    F = []
    for fi, f in enumerate(mb.faces):
        if pred and not pred(mb.fisl[fi]):
            continue
        for k in range(1, len(f) - 1):
            F.append((f[0], f[k], f[k + 1]))
    return BVHTree.FromPolygons(V, F), np.array(mb.verts), F


out = {}
for lv in ("lod0", "lod1"):
    P = parts[lv]
    A, VA, FA = bvh(P["cords"], lambda s: s.startswith("cordA"))
    B, VB, FB = bvh(P["cords"], lambda s: s.startswith("cordB"))
    res = {}
    pairs = A.overlap(B)
    zs = sorted({round(float(np.mean([VA[i][2] for i in FA[a]])), 1) for a, b in pairs})
    res["cordA_vs_cordB"] = {"pairs": len(pairs), "z": zs[:40]}
    C_, VC, FC = bvh(P["cords"])
    for other in ("kashira", "fuchi", "menuki", "mekugi", "eyelets"):
        if other not in P:
            continue
        O, VO, FO = bvh(P[other])
        pr = C_.overlap(O)
        zs = sorted({round(float(np.mean([VC[i][2] for i in FC[a]])), 1) for a, b in pr})
        res[f"cords_vs_{other}"] = {"pairs": len(pr), "z": zs[:40]}
    out[lv] = res
(ROOT / "WorkFiles/katana/final/tsuka_overlaps.json").write_text(json.dumps(out, indent=1))
print("TSUKA_OVERLAPS", json.dumps(out))
