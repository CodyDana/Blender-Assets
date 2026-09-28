"""Trace pilot: does the traced throat still let the sword in?  (mouth_clears_guard)

Sword = the round-1 sword (snapshot SnowFlower_Game_v4.blend, LOD0/1/2) placed exactly as the r1 fit placed it
(sheath_build/fit/fit.json R, t; exported by tp_plug.py to work/sword_*_S.npz, mm, sheath frame).
Checks, against the traced throat LOD0 (pilot blend) and the traced HIGH poly:
    1. static: no triangle of any sword LOD intersects the throat;
    2. draw: the sword slid out along its own axis (the Mouth socket's draw axis) 0..160 mm in 2 mm steps never
       intersects the throat;
    3. clearance: smallest distance from the sword's in-mouth vertices (z > mouth plane) to the throat surface, and
       from the guard's leaf body to the throat.
Also reports the traced mouth opening (ring inner) and the r1 cavity-size claim ~65 x 38 mm.
    blender -b --factory-startup --python tp_fitcheck.py"""
import bpy, json, math, sys
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
PILOT = ROOT + "/WorkFiles/SnowFlower/v4/trace_pilot"
WORK = PILOT + "/work"
fit = json.load(open(ROOT + "/WorkFiles/SnowFlower/v4/sheath_build/fit/fit.json"))
R = np.array(fit["R"]); axis = R @ np.array([0, 0, 1.0])          # sword +Z (toward the tip) in the sheath frame
Z_MOUTH = (31.0 - 304.0) * 0.687


def bvh_from_blend(path, name):
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [name]
    o = dst.objects[0]
    me = o.data
    V = np.array([v.co[:] for v in me.vertices]) * 1000.0
    Mw = np.array(o.matrix_world)
    V = (np.c_[V, np.ones(len(V))] @ Mw.T)[:, :3]
    me.calc_loop_triangles()
    T = np.array([lt.vertices[:] for lt in me.loop_triangles], int)
    return V, T


def bvh(V, T):
    return BVHTree.FromPolygons([Vector(v) for v in V], [tuple(t) for t in T], all_triangles=True)


res = {"sword_source": "r1 snapshot SnowFlower_Game_v4.blend LOD0-2, placed with sheath_build/fit/fit.json (R, t)",
       "mouth_plane_z_mm": Z_MOUTH, "results": {}}
targets = {"throat_LOD0": bvh_from_blend(PILOT + "/SnowFlower_Sheath_TracePilot.blend", "SM_SnowFlower_Throat_TP_LOD0"),
           "throat_HIGH": bvh_from_blend(WORK + "/tp_high.blend", "TP_Throat_HIGH")}
swords = {}
for lv in (0, 1, 2):
    d = np.load(WORK + f"/sword_SM_SnowFlower_LOD{lv}_S.npz")
    swords[lv] = (d["V"], d["T"])
ok_all = True
for tn, (TV, TT) in targets.items():
    tb = bvh(TV, TT)
    r = {}
    for lv, (SV, ST) in swords.items():
        hits_static = len(bvh(SV, ST).overlap(tb))
        worst = 0; first_hit = None
        for d in np.arange(1.0, 161.0, 2.0):
            sv = SV - axis * d                     # slide out of the mouth (toward the grip)
            n = len(bvh(sv, ST).overlap(tb))
            if n and first_hit is None:
                first_hit = float(d)
            worst = max(worst, n)
        inm = SV[SV[:, 2] > Z_MOUTH]
        dmin = min((tb.find_nearest(Vector(p))[3] for p in inm), default=None)
        # guard leaf body = hilt points above the mouth plane within 20 mm of it
        guard = SV[(SV[:, 2] <= Z_MOUTH) & (SV[:, 2] > Z_MOUTH - 20)]
        gmin = min((tb.find_nearest(Vector(p))[3] for p in guard), default=None)
        r[f"LOD{lv}"] = {"static_overlapping_pairs": hits_static, "draw_overlapping_pairs_max": worst,
                         "draw_first_hit_mm": first_hit, "min_dist_in_mouth_vertices_mm": dmin,
                         "min_dist_guard_to_throat_mm": gmin}
        ok_all &= hits_static == 0 and worst == 0
        print("[TP-FIT]", tn, f"LOD{lv}", r[f"LOD{lv}"], flush=True)
    res["results"][tn] = r
rp = json.load(open(WORK + "/ring_profile.json"))
res["mouth_ring_inner_mm"] = {"half_x": rp["ring_in"][0], "half_y": rp["ring_in"][1], "superellipse_p": rp["p"],
                              "full": [2 * rp["ring_in"][0], 2 * rp["ring_in"][1]]}
res["mouth_clears_guard"] = bool(ok_all)
json.dump(res, open(PILOT + "/fit_check.json", "w"), indent=1, default=float)
print("[TP-FIT] mouth_clears_guard", ok_all)
