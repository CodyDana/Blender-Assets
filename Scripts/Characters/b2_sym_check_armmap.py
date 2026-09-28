"""b2_sym_check_armmap.py - PRIVATE / DO NOT SHIP. Independent checker: is the builder's topological mirror map right on
the arms of the BEFORE (step C1) skin?  Read-only (opens the step C1 rig blend, never saves).

  blender -b 2B_private_rig.blend -P b2_sym_check_armmap.py -- <abs out json>

Per region: |p - M p_map| (builder map) vs distance from p to the mirrored surface (map-free). If the map is right, the
two agree to within the local sliding; a map rotated around a limb gives |p - M p_map| >> surface distance.
Also: the angular offset of the twin around the limb axis (upperarm / lowerarm / thigh / calf).
"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private"
M3 = np.array([-1.0, 1.0, 1.0])
CHILD = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot", "clavicle": "upperarm", "hand": "middle_01"}


def co(me):
    a = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", a); return a.reshape(-1, 3)


def main():
    outp = sys.argv[sys.argv.index("--") + 1]
    body = bpy.data.objects["SK_2B_Body"]; me = body.data; arm = bpy.data.objects["root"]
    X = co(me)
    mv = np.load(OUT + "/checks_sym/mirror_map.npy")
    polys = [tuple(p.vertices) for p in me.polygons]
    tree = BVHTree.FromPolygons([Vector(c) for c in X * M3], polys)
    ds = np.array([tree.find_nearest(Vector(p))[3] for p in X])
    dm = np.linalg.norm(X - X[mv] * M3, axis=1)
    names = [b.name for b in arm.data.bones]
    gi = {g.index: names.index(g.name) for g in body.vertex_groups if g.name in names}
    W = np.zeros((len(X), len(names)))
    for v in me.vertices:
        for g in v.groups:
            if g.group in gi:
                W[v.index, gi[g.group]] = g.weight
    dom = np.array(names)[W.argmax(1)]
    res = {}
    B = arm.data.bones
    for seg in ("upperarm", "lowerarm", "hand", "thigh", "calf", "clavicle", "spine_05", "neck_01", "head", "pelvis"):
        for s in (("l",) if seg in CHILD else ("",)):
            bn = f"{seg}_{s}" if s else seg
            sel = dom == bn
            r = {"n": int(sel.sum()), "map_err_mean_mm": round(float(dm[sel].mean()) * 1000, 2), "map_err_p95_mm": round(float(np.percentile(dm[sel], 95)) * 1000, 2),
                 "surface_err_mean_mm": round(float(ds[sel].mean()) * 1000, 2), "surface_err_p95_mm": round(float(np.percentile(ds[sel], 95)) * 1000, 2)}
            if seg in CHILD:
                h = np.array(B[bn].head_local); t = np.array(B[f"{CHILD[seg]}_l"].head_local)
                ax = (t - h) / np.linalg.norm(t - h)
                # twin (right side) mirrored into the left frame
                Q = X[mv[sel]] * M3
                P = X[sel]
                def ang(Pp):
                    v = Pp - h; v = v - (v @ ax)[:, None] * ax
                    return v
                vp = ang(P); vq = ang(Q)
                # signed angle about ax
                c = np.cross(vp, vq) @ ax; dd = (vp * vq).sum(1)
                a = np.degrees(np.arctan2(c, dd))
                r["twin_twist_deg_median"] = round(float(np.median(a)), 2)
                r["twin_twist_deg_p5_p95"] = [round(float(np.percentile(a, 5)), 2), round(float(np.percentile(a, 95)), 2)]
                r["radius_l_mm"] = round(float(np.linalg.norm(vp, axis=1).mean()) * 1000, 2)
                r["radius_twin_mm"] = round(float(np.linalg.norm(vq, axis=1).mean()) * 1000, 2)
                r["radius_avg_mm"] = round(float(np.linalg.norm(ang((P + Q) / 2), axis=1).mean()) * 1000, 2)
            res[bn] = r
    json.dump(res, open(outp, "w"), indent=1)
    print("[armmap]", json.dumps(res))


main()
