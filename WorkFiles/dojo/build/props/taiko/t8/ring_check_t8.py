"""t8 (judge r7 items 1-2): the ring hardware measured on a built drum mesh (the exported FBX by default, or a .blend's
SM_DKP_Taiko_Drum with --blend): the +Y handle's loose parts (plate, rivets, washer, boss, ring), each projected
through the photo's fitted camera (t7/photo_cam.py, the judge's head-aligned frame) -> pixel extents, plus the
intersecting triangle pairs between the parts and with the barrel, and the ring's nearest distances to each part.

Run: blender -b -t 4 --factory-startup --python ring_check_t8.py -- [--blend PATH] [--out JSON]
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t8"
sys.path.insert(0, str(HERE.parent / "t7"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "props" / "taiko"))
import photo_cam as PC  # noqa: E402
import taiko_uv as UVL  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else HERE / "ring_check.json"
if "--blend" in ARGS:
    bpy.ops.wm.open_mainfile(filepath=ARGS[ARGS.index("--blend") + 1])
    drum = bpy.data.objects["SM_DKP_Taiko_Drum"]
    src = "blend " + ARGS[ARGS.index("--blend") + 1]
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fbx = ROOT / "Exports" / "DojoKit" / "Props" / "taiko" / "SM_DKP_Taiko_Drum.fbx"
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    drum = next(o for o in bpy.data.objects if o.name.endswith("Drum_LOD0"))
    src = "fbx " + str(fbx)
me = drum.data
M = drum.matrix_world
V = np.array([tuple(M @ v.co) for v in me.vertices])
F = [list(p.vertices) for p in me.polygons]
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
comp = np.array([find(i) for i in range(len(V))])
parts = {}
for i, c in enumerate(comp):
    parts.setdefault(c, []).append(i)
S = UVL.DRUM_SCALE
res = {"source": src}
hw = []
for c, idx in parts.items():
    P = V[idx]
    ctr = 0.5 * (P.min(0) + P.max(0))
    ext = P.max(0) - P.min(0)
    if ctr[1] > 0.6 and abs(ctr[0]) < 0.3 and abs(ctr[2]) < 0.3 and ext.max() < 0.5:
        hw.append(dict(c=c, n=len(idx), ctr=ctr, ext=ext))
barrel = max(parts.items(), key=lambda kv: len(kv[1]))[0]


def label(d):
    e = d["ext"] * 1000
    if e.max() > 400:
        return "plate"
    if 150 < e.max() < 220:
        return "ring" if e[1] > 12 and d["n"] < 1000 else "washer"
    if 25 < e.max() < 45:
        return "rivet"
    if 55 < e.max() < 90:
        return "boss"
    return "other"


face_part = np.array([comp[f[0]] for f in F])
named = {}
for d in hw:
    d["name"] = label(d)
    named.setdefault(d["name"], []).append(d)
res["parts"] = {k: [dict(n=d["n"], ext_mm=[round(float(x) * 1000, 1) for x in d["ext"]],
                         ctr_m=[round(float(x), 4) for x in d["ctr"]]) for d in v] for k, v in named.items()}


def px(idx):
    uv = PC.project_design(V[idx] / S)
    return [round(float(uv[:, 0].min()), 1), round(float(uv[:, 0].max()), 1),
            round(float(uv[:, 1].min()), 1), round(float(uv[:, 1].max()), 1)]


res["photo_px_u0_u1_v0_v1"] = {k: [px(parts[d["c"]]) for d in v] for k, v in named.items()}
if "ring" in named:
    r = res["photo_px_u0_u1_v0_v1"]["ring"][0]
    res["ring_photo_px"] = {"top_v": r[2], "bottom_v": r[3], "height_px": round(r[3] - r[2], 1),
                            "left_u": r[0], "right_u": r[1],
                            "centre": [round(0.5 * (r[0] + r[1]), 1), round(0.5 * (r[2] + r[3]), 1)],
                            "judge_target_rows": [572, 672], "photo_rows_judge_r7": [572, 674]}
for k in ("plate", "washer", "boss"):
    if k in named:
        r = res["photo_px_u0_u1_v0_v1"][k][0]
        res[k + "_photo_centre_px"] = [round(0.5 * (r[0] + r[1]), 1), round(0.5 * (r[2] + r[3]), 1)]


def bvh(c):
    fids = np.where(face_part == c)[0]
    return BVHTree.FromPolygons([tuple(v) for v in V], [F[i] for i in fids])


trees = {}
for k, v in named.items():
    for j, d in enumerate(v):
        trees["%s%d" % (k, j)] = bvh(d["c"])
trees["barrel"] = bvh(barrel)
keys = sorted(trees)
ov = {}
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        n = len(trees[keys[i]].overlap(trees[keys[j]]))
        if n:
            ov[keys[i] + "-" + keys[j]] = n
res["intersecting_pairs"] = ov
if "ring" in named:
    ring_idx = parts[named["ring"][0]["c"]]
    near = {}
    for k in keys:
        if k.startswith("ring"):
            continue
        best = 9.0
        for i in ring_idx:
            loc, _n, _f, d = trees[k].find_nearest(tuple(V[i]), 0.1)
            if loc is not None and d < best:
                best = d
        near[k] = round(best * 1000, 2)
    res["ring_nearest_mm"] = near
    res["ring_vertices"] = len(ring_idx)
OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
print("RINGCHECK", json.dumps(res))
