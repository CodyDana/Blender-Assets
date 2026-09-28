"""b2_sym_gate.py - PRIVATE / DO NOT SHIP. Volume / girth gates of the symmetry build (read-only, never saves a blend).

  blender -b WorkFiles/Characters/2B_private/2B_private_rig_sym.blend -P Scripts/Characters/b2_sym_gate.py -- <abs out json>

Compares the opened (after) blend with the read-only step C1 rig (before, linked in):
  * limb girth: mean radial distance of the skin from the bone axis (head -> chain child head), per bone and in 5
    sections along it (dominant-bone vertex sets), before L / before R / after; gate: whole-bone mean within 3 % of
    the before L/R mean (the worst section is reported as info)
  * signed skin volume and total area; gate: volume change < 0.5 %
  * faces that shrank below 0.7 x the smaller of their before pair (topological face twin); gate: 0
  * area change per region
"""
import bpy, os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_sym_lib import *  # noqa
from b2_sym_twist import child_head  # noqa

SEGS = ("upperarm", "lowerarm", "thigh", "calf", "clavicle", "hand", "foot")


def girth(X, W, order, arm, n, nsec=5):
    B = arm.bones
    h = np.array(B[n].head_local); t = child_head(B, n)
    L = np.linalg.norm(t - h); ax = (t - h) / L
    sel = W.argmax(axis=1) == order.index(n)
    P = X[sel] - h
    along = P @ ax
    rad = np.linalg.norm(P - along[:, None] * ax, axis=1)
    secs = []
    for k in range(nsec):
        m = (along >= k * L / nsec) & (along < (k + 1) * L / nsec)
        secs.append(float(rad[m].mean()) if m.sum() > 5 else None)
    return float(rad.mean()), secs


def volume(X, polys):
    v = 0.0
    for p in polys:
        for k in range(1, len(p) - 1):
            v += float(np.dot(X[p[0]], np.cross(X[p[k]], X[p[k + 1]]))) / 6
    return v


def areas(X, polys):
    A = np.zeros(len(polys))
    for i, p in enumerate(polys):
        P = X[list(p)]; nrm = np.zeros(3)
        for k in range(1, len(p) - 1):
            nrm += np.cross(P[k] - P[0], P[k + 1] - P[0])
        A[i] = np.linalg.norm(nrm) / 2
    return A


def main():
    outp = argv()[0]
    assert os.path.isabs(outp)
    body = bpy.data.objects["SK_2B_Body"]; me = body.data; arm = bpy.data.objects["root"]
    assert bpy.data.filepath.replace("\\", "/") != RIG_BLEND
    order = [b.name for b in arm.data.bones]
    X1 = co_array(me)
    W1 = weights_matrix(body, order)
    with bpy.data.libraries.load(RIG_BLEND, link=True) as (src, dst):
        dst.objects = ["SK_2B_Body", "root"]
    body0, arm0 = dst.objects
    X0 = co_array(body0.data)
    W0 = weights_matrix(body0, order)
    mv = np.load(CHECKS + "/mirror_map.npy")
    polys = [tuple(p.vertices) for p in me.polygons]
    assert len(X0) == len(X1)
    res = {"girth_mm": {}, "gates": {}}
    worst = 0.0; worst_sec = 0.0
    for seg in SEGS:
        row = {}
        g = {}
        for s in ("l", "r"):
            g[("before", s)] = girth(X0, W0, order, arm0.data, f"{seg}_{s}")
            g[("after", s)] = girth(X1, W1, order, arm.data, f"{seg}_{s}")
        ref = (g[("before", "l")][0] + g[("before", "r")][0]) / 2
        aft = g[("after", "l")][0]
        row["before_l_mean"] = round(g[("before", "l")][0] * 1000, 2); row["before_r_mean"] = round(g[("before", "r")][0] * 1000, 2)
        row["after_mean"] = round(aft * 1000, 2)
        row["after_vs_before_lr_mean_pct"] = round((aft / ref - 1) * 100, 2)
        sec = []
        for k in range(5):
            b = [g[("before", s)][1][k] for s in ("l", "r")]
            a = g[("after", "l")][1][k]
            if None in b or a is None:
                sec.append(None); continue
            sec.append(round((a / (sum(b) / 2) - 1) * 100, 2))
        row["sections_after_vs_before_pct"] = sec
        row["sections_before_l"] = [None if v is None else round(v * 1000, 2) for v in g[("before", "l")][1]]
        row["sections_before_r"] = [None if v is None else round(v * 1000, 2) for v in g[("before", "r")][1]]
        row["sections_after"] = [None if v is None else round(v * 1000, 2) for v in g[("after", "l")][1]]
        res["girth_mm"][seg] = row
        if seg in ("upperarm", "lowerarm", "thigh", "calf"):
            worst = max(worst, abs(row["after_vs_before_lr_mean_pct"]))
            worst_sec = max(worst_sec, *[abs(v) for v in sec if v is not None])
    v0 = volume(X0, polys); v1 = volume(X1, polys)
    A0 = areas(X0, polys); A1 = areas(X1, polys)
    fkey = {frozenset(p): i for i, p in enumerate(polys)}
    ftw = np.array([fkey[frozenset(mv[list(p)].tolist())] for p in polys])
    shr = A1 < 0.7 * np.minimum(A0, A0[ftw])
    fdom = np.array([np.bincount(W1[list(p)].argmax(axis=1)).argmax() for p in polys])
    by = {}
    for i in np.nonzero(shr)[0]:
        by[order[fdom[i]]] = by.get(order[fdom[i]], 0) + 1
    reg = skin_regions(X1, W1, order, vert_src(me))
    freg = np.array([reg[p[0]] for p in polys])
    reg_area = {}
    for r in sorted(set(freg.tolist())):
        m = freg == r
        a0 = float(((A0[m] + A0[ftw][m]) / 2).sum()); a1 = float(A1[m].sum())
        reg_area[r] = {"before_pair_mean_m2": round(a0, 5), "after_m2": round(a1, 5), "change_pct": round((a1 / a0 - 1) * 100, 2)}
    res["volume_l"] = {"before": round(v0 * 1000, 4), "after": round(v1 * 1000, 4), "change_pct": round((v1 / v0 - 1) * 100, 3)}
    res["area_m2"] = {"before": round(float(A0.sum()), 5), "after": round(float(A1.sum()), 5),
                      "change_pct": round((float(A1.sum()) / float(A0.sum()) - 1) * 100, 3)}
    res["area_by_region_vs_before_pair_mean"] = reg_area
    ratio = A1 / np.maximum(np.minimum(A0, A0[ftw]), 1e-12)
    res["face_area_ratio_vs_smaller_before_pair"] = {"min": round(float(ratio.min()), 4), "p0.1": round(float(np.percentile(ratio, 0.1)), 4),
                                                     "p1": round(float(np.percentile(ratio, 1)), 4)}
    fc = np.array([X1[list(p)].mean(axis=0) for p in polys])
    res["shrunk_faces_below_0.7"] = {"total": int(shr.sum()), "by_bone": dict(sorted(by.items(), key=lambda kv: -kv[1])),
                                     "faces": [{"face": int(i), "centre_m": [round(float(x), 4) for x in fc[i]],
                                                "ratio": round(float(ratio[i]), 3), "region": str(freg[i]),
                                                "before_area_mm2": [round(float(A0[i]) * 1e6, 3), round(float(A0[ftw[i]]) * 1e6, 3)],
                                                "after_area_mm2": round(float(A1[i]) * 1e6, 3)} for i in np.nonzero(shr)[0]]}
    res["gates"] = {"limb_girth_worst_abs_pct": round(worst, 2), "limb_girth_within_3pct": worst <= 3.0,
                    "info_limb_section_worst_abs_pct": round(worst_sec, 2),
                    "volume_change_under_0.5pct": abs(v1 / v0 - 1) < 0.005,
                    "no_face_below_0.7": int(shr.sum()) == 0}
    res["gates"]["all_pass"] = all(res["gates"][k] for k in ("limb_girth_within_3pct", "volume_change_under_0.5pct", "no_face_below_0.7"))
    save_json(outp, res)
    log("gate", json.dumps(res["gates"]), json.dumps(res["volume_l"]), json.dumps(res["shrunk_faces_below_0.7"]))
    for seg, row in res["girth_mm"].items():
        log(seg, row["after_vs_before_lr_mean_pct"], row["sections_after_vs_before_pct"])


main()
