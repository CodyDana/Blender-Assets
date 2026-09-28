"""b2_sym_check_girth.py - PRIVATE / DO NOT SHIP. Independent checker, round 2 (read-only, never saves any blend).

  blender -b 2B_private_rig_sym.blend -P b2_sym_check_girth.py -- <abs out json>

Map-free limb girth: for each limb bone and side, vertices whose dominant weight is that bone, binned in 5 sections
along the bone axis (head -> child head); mean radial distance from the axis. Before = step C1 rig (its own armature),
after = sym blend. Also closed-surface volume and area, and per-face area ratio vs the before geometric partner
(nearest face centroid on the mirrored before surface, map-free).
"""
import bpy, sys, json
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private"
RIG = OUT + "/2B_private_rig.blend"
M3 = np.array([-1.0, 1.0, 1.0])
SEGS = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot", "clavicle": "upperarm"}
MIDS = {"neck_01": "neck_02", "neck_02": "head", "spine_05": "neck_01"}


def co(me):
    a = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", a); return a.reshape(-1, 3)


def dom_bone(obj, names):
    gi = {g.index: g.name for g in obj.vertex_groups}
    dom = []
    for v in obj.data.vertices:
        best = None; bw = -1
        for g in v.groups:
            if g.weight > bw and gi.get(g.group) in names:
                bw = g.weight; best = gi[g.group]
        dom.append(best)
    return np.array(dom, dtype=object)


def vol_area(X, polys):
    V = 0.0; A = 0.0
    for p in polys:
        P = X[list(p)]
        for k in range(1, len(p) - 1):
            a, b, c = P[0], P[k], P[k + 1]
            V += a @ np.cross(b, c) / 6.0
            A += np.linalg.norm(np.cross(b - a, c - a)) / 2
    return V, A


def girth(X, dom, bones, bn, child):
    h = np.array(bones[bn].head_local); t = np.array(bones[child].head_local)
    L = np.linalg.norm(t - h); ax = (t - h) / L
    sel = dom == bn
    v = X[sel] - h; s = v @ ax; r = np.linalg.norm(v - s[:, None] * ax, axis=1)
    out = []
    for k in range(5):
        m = (s >= k * L / 5) & (s < (k + 1) * L / 5)
        out.append(round(float(r[m].mean()) * 1000, 2) if m.any() else None)
    return {"n": int(sel.sum()), "mean_mm": round(float(r.mean()) * 1000, 2), "sections_mm": out}


def main():
    outp = sys.argv[sys.argv.index("--") + 1]
    body = bpy.data.objects["SK_2B_Body"]; arm = bpy.data.objects["root"]
    X1 = co(body.data)
    polys = [tuple(p.vertices) for p in body.data.polygons]
    with bpy.data.libraries.load(RIG, link=True) as (src, dst):
        dst.objects = ["SK_2B_Body", "root"]
    b0, a0 = dst.objects
    X0 = co(b0.data)
    names = [b.name for b in arm.data.bones]
    d1 = dom_bone(body, names); d0 = dom_bone(b0, names)
    res = {"girth": {}}
    for seg, ch in list(SEGS.items()):
        for s in ("l", "r"):
            bn = f"{seg}_{s}"; cn = f"{ch}_{s}"
            res["girth"][bn] = {"before": girth(X0, d0, a0.data.bones, bn, cn), "after": girth(X1, d1, arm.data.bones, bn, cn)}
    for bn, cn in MIDS.items():
        res["girth"][bn] = {"before": girth(X0, d0, a0.data.bones, bn, cn), "after": girth(X1, d1, arm.data.bones, bn, cn)}
    summ = {}
    for bn, g in res["girth"].items():
        if bn.endswith("_r"):
            continue
        base = bn[:-2] if bn.endswith("_l") else bn
        if bn.endswith("_l"):
            bl = g["before"]; br = res["girth"][base + "_r"]["before"]; al = g["after"]; ar = res["girth"][base + "_r"]["after"]
            bm = (bl["mean_mm"] + br["mean_mm"]) / 2
            secs = []
            for k in range(5):
                vals = [bl["sections_mm"][k], br["sections_mm"][k]]
                if None in vals or al["sections_mm"][k] is None:
                    secs.append(None); continue
                secs.append(round((al["sections_mm"][k] / (sum(vals) / 2) - 1) * 100, 2))
            summ[base] = {"mean_pct_vs_before_LR_mean": round((al["mean_mm"] / bm - 1) * 100, 2),
                          "after_L_vs_R_mm": [al["mean_mm"], ar["mean_mm"]], "section_pct": secs}
        else:
            summ[base] = {"mean_pct": round((g["after"]["mean_mm"] / g["before"]["mean_mm"] - 1) * 100, 2),
                          "section_pct": [None if (a is None or b is None) else round((a / b - 1) * 100, 2)
                                          for a, b in zip(g["after"]["sections_mm"], g["before"]["sections_mm"])]}
    res["summary"] = summ
    V0, A0 = vol_area(X0, polys); V1, A1 = vol_area(X1, polys)
    res["volume_L"] = [round(V0 * 1000, 4), round(V1 * 1000, 4), round((V1 / V0 - 1) * 100, 3)]
    res["area_m2"] = [round(A0, 5), round(A1, 5), round((A1 / A0 - 1) * 100, 3)]
    # map-free face area ratio: each after face vs the before face with nearest centroid, and vs the before face
    # nearest to its mirrored centroid (the other side's partner), both geometric
    def fstats(X):
        C = np.zeros((len(polys), 3)); A = np.zeros(len(polys))
        for i, p in enumerate(polys):
            P = X[list(p)]; C[i] = P.mean(0)
            n = np.zeros(3)
            for k in range(1, len(p) - 1):
                n += np.cross(P[k] - P[0], P[k + 1] - P[0])
            A[i] = np.linalg.norm(n) / 2
        return C, A
    C0, Ar0 = fstats(X0); C1, Ar1 = fstats(X1)
    kd = KDTree(len(C0))
    for i, c in enumerate(C0):
        kd.insert(Vector(c), i)
    kd.balance()
    j_same = np.array([kd.find(Vector(c))[1] for c in C1])
    j_mir = np.array([kd.find(Vector(c * M3))[1] for c in C1])
    lo = np.minimum(Ar0[j_same], Ar0[j_mir]); hi = np.maximum(Ar0[j_same], Ar0[j_mir])
    rlo = Ar1 / np.maximum(lo, 1e-14); rhi = Ar1 / np.maximum(hi, 1e-14)
    # same-index (topological) ratio too
    rs = Ar1 / np.maximum(Ar0, 1e-14)
    res["face_area_geo"] = {"lt_0.7x_min_geo_pair": int((rlo < 0.7).sum()), "gt_1.4x_max_geo_pair": int((rhi > 1.4).sum()),
                            "same_index_ratio_p1_p99": [round(float(np.percentile(rs, 1)), 3), round(float(np.percentile(rs, 99)), 3)],
                            "same_index_lt_0.6": int((rs < 0.6).sum()), "same_index_gt_1.6": int((rs > 1.6).sum()),
                            "worst_shrunk": [[int(i), round(float(rlo[i]), 3), [round(float(v), 4) for v in C1[i]], round(float(Ar1[i] * 1e6), 2)]
                                             for i in np.argsort(rlo)[:10]]}
    # per-region same-index ratio for arms
    upper = np.isin(d1, ["upperarm_l", "upperarm_r"])
    fdom = np.array([d1[p[0]] for p in polys], dtype=object)
    for bn in ("upperarm_l", "upperarm_r", "lowerarm_l", "thigh_l", "calf_l", "neck_01", "neck_02", "spine_05", "head"):
        m = fdom == bn
        res.setdefault("area_by_bone_pct", {})[bn] = round((Ar1[m].sum() / Ar0[m].sum() - 1) * 100, 2)
    json.dump(res, open(outp, "w"), indent=1)
    print("[girth]", json.dumps({"summary": summ, "vol": res["volume_L"], "area": res["area_m2"], "fa": {k: v for k, v in res["face_area_geo"].items() if k != "worst_shrunk"},
                                 "area_by_bone": res["area_by_bone_pct"]}))


main()
