"""b2_sym_measure.py - PRIVATE / DO NOT SHIP. Asymmetry metrics of a 2B rig blend (read-only, never saves the blend).

  blender -b <rig blend> -P b2_sym_measure.py -- <out.json> [mirror_map.npy]

Skin: per vertex |p - M p_twin| (topological twin, M: x -> -x), mean / p95 / max overall and per region, midline |x|,
best-fit sagittal planes (whole skin and per region). Skeleton: joint asymmetry. Head parts / garments: symmetric
chamfer distance (every vertex to the nearest vertex of the mirrored mesh), per part.
If mirror_map.npy exists it is reused (it is topological, so it is valid for every blend with this skin topology);
otherwise it is computed and written there.
"""
import bpy, os, sys, json
import numpy as np
from mathutils.kdtree import KDTree
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_sym_lib import *  # noqa


def chamfer(P, Q):
    """mean/p95/max of the distance from every point of P to the nearest point of Q (and back)."""
    kd = KDTree(len(Q))
    for i, q in enumerate(Q):
        kd.insert(Vector(q), i)
    kd.balance()
    d1 = np.array([kd.find(Vector(p))[2] for p in P])
    kd2 = KDTree(len(P))
    for i, p in enumerate(P):
        kd2.insert(Vector(p), i)
    kd2.balance()
    d2 = np.array([kd2.find(Vector(q))[2] for q in Q])
    return np.concatenate([d1, d2])


def measure_blend(mv_path=None):
    skin = bpy.data.objects["SK_2B_Body"]
    me = skin.data
    X = co_array(me)
    mv = None
    if mv_path and os.path.exists(mv_path):
        mv = np.load(mv_path)
        if len(mv) != len(X):
            mv = None
    info = {}
    if mv is None:
        t = time.time()
        mm = mirror_map(me, 0.95, 1.35)
        mv = mm["mv"]
        info = {"med_err_m": mm["med_err"], "seeds_tried": mm["seeds_tried"], "secs": round(time.time() - t, 1)}
        if mv_path:
            np.save(mv_path, mv)
    arm = bpy.data.objects["root"]
    order = [b.name for b in arm.data.bones]
    W = weights_matrix(skin, order)
    vsrc = vert_src(me)
    reg = skin_regions(X, W, order, vsrc)
    R = {"mirror_map": info}
    R["skin"], d = measure_skin(X, mv, reg)
    R["skin_planes"] = {"all": plane_report(X, mv)}
    for r in ("face", "neck", "torso", "breasts", "pelvis", "legs", "arms"):
        R["skin_planes"][r] = plane_report(X, mv, reg == r)
    R["bones"] = bone_asym(arm)
    # head parts per material, garments per material: chamfer of mesh vs its mirror image
    for on in ("SK_2B_HeadParts", "SK_2B_Garments"):
        o = bpy.data.objects[on]
        G = co_array(o.data)
        mats = [m.name for m in o.data.materials]
        pm = np.zeros(len(o.data.polygons), dtype=int); o.data.polygons.foreach_get("material_index", pm)
        out = {}
        for k, mname in enumerate(mats):
            vs = sorted({v for p, mi in zip(o.data.polygons, pm) if mi == k for v in p.vertices})
            if not vs:
                continue
            P = G[vs]
            out[mname] = stats(chamfer(P, P * M3))
            out[mname]["centroid_x_mm"] = round(float(P[:, 0].mean()) * 1000, 3)
        R[on] = out
    gar = bpy.data.objects["SK_2B_Garments"]
    under_i = [m.name for m in gar.data.materials].index("M_2B_Underwear")
    R["garment_clearance"] = garment_clearance(me, gar, under_i)
    R["skin_under_garments"] = skin_poke(me, gar)
    R["eyes_vs_lids"] = eye_lid_check(me, bpy.data.objects["SK_2B_HeadParts"])
    R["feet"] = feet_check(X, reg, arm)
    R["height_m"] = float(X[:, 2].max() - X[:, 2].min())
    R["min_z_m"] = float(X[:, 2].min())
    return R, X, mv, reg, d


if __name__ == "__main__":
    a = argv()
    R, X, mv, reg, d = measure_blend(a[1] if len(a) > 1 else None)
    R["blend"] = bpy.data.filepath
    save_json(a[0], R)
    np.save(os.path.splitext(a[0])[0] + "_err.npy", d)
    log(json.dumps({k: R[k] for k in ("mirror_map", "skin", "skin_planes")}, indent=0)[:6000])
