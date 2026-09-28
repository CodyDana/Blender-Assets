"""b2_sym_twistprobe.py - PRIVATE / DO NOT SHIP. Read-only probe (never saves a blend): how far is each skin vertex's
topological twin rotated around the local bone axis (the "twisted map" the checker found on the upper arms)?

  blender -b WorkFiles/Characters/2B_private/2B_private_rig.blend -P Scripts/Characters/b2_sym_twistprobe.py -- <abs out json>

Per bone (dominant-bone vertex sets, her left side for pairs), per axial bin: median signed twin angle about the
averaged bone axis direction through each side's own ring centroid, its spread, radii of p / mirrored twin / chord average / de-twisted average, map error before and
after de-twisting by the bin median.
"""
import bpy, os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_sym_lib import *  # noqa
from b2_sym_twist import bone_axes, cyl, rot_about  # noqa


def ring_centres(P, c, a, nb=8):
    """centroid of the ring per axial bin: (bin centre t, centroids)."""
    t = (P - c) @ a
    e = np.linspace(np.percentile(t, 1), np.percentile(t, 99) + 1e-9, nb + 1)
    tc = []; cc = []
    for k in range(nb):
        m = (t >= e[k]) & (t < e[k + 1])
        if m.sum() >= 8:
            tc.append((e[k] + e[k + 1]) / 2); cc.append(P[m].mean(axis=0))
    return np.array(tc), np.array(cc)


def main():
    outp = argv()[0]
    assert os.path.isabs(outp)
    skin = bpy.data.objects["SK_2B_Body"]; me = skin.data; arm = bpy.data.objects["root"]
    order = [b.name for b in arm.data.bones]
    X = co_array(me)
    cap = np.load(CHECKS + "/c1_sink_capture.npz")
    Xn = X - (cap["post"] - cap["pre"]) * float(cap["k"])
    mv = np.load(CHECKS + "/mirror_map.npy")
    Q = Xn[mv] * M3
    W = weights_matrix(skin, order)
    dom = np.array(order)[W.argmax(axis=1)]
    axes = bone_axes(arm)
    res = {}
    for n in ("pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "clavicle_l",
              "upperarm_l", "lowerarm_l", "thigh_l", "calf_l"):
        sel = (dom == n) & ((Xn[:, 0] > 0) | (mv == np.arange(len(Xn))) if n.endswith("_l") else (dom == n))
        sel = np.nonzero(sel)[0]
        if len(sel) < 30:
            continue
        c, a, L = axes[n]
        # ring-centre frames: each side's rings are centred on their own centroid (the bone need not be centred in the
        # skin): p about the centroid of its own ring, the mirrored twin about the mirror of its ring's centroid
        full = np.nonzero(dom == n)[0] if not n.endswith("_l") else np.nonzero(dom == n)[0]
        fullr = np.nonzero(dom == other(n))[0]
        tP0 = (Xn[sel] - c) @ a
        cP = ring_centres(Xn[full], c, a); cQ = ring_centres(Xn[fullr] * M3, c, a)
        CP = np.array([np.interp(tP0, cP[0], cP[1][:, k]) for k in range(3)]).T
        tQ0 = (Q[sel] - c) @ a
        CQ = np.array([np.interp(tQ0, cQ[0], cQ[1][:, k]) for k in range(3)]).T
        tP, rP, angP = cyl(Xn[sel] - CP + c, c, a)
        tQ, rQ, angQ = cyl(Q[sel] - CQ + c, c, a)
        dang = (angQ - angP + np.pi) % (2 * np.pi) - np.pi
        tt = (tP + tQ) / 2
        nb = 6
        edges = np.linspace(tt.min(), tt.max() + 1e-9, nb + 1)
        bins = []
        for k in range(nb):
            m = (tt >= edges[k]) & (tt < edges[k + 1])
            if m.sum() < 8:
                continue
            th = float(np.median(dang[m]))
            P = Xn[sel[m]] - CP[m] + c; Qm = Q[sel[m]] - CQ[m] + c
            chord = (P + Qm) / 2
            Qd = rot_about(Qm, c, a, -th)
            det = rot_about((P + Qd) / 2, c, a, th / 2)
            bins.append({"t_mm": round(float((edges[k] + edges[k + 1]) / 2) * 1000, 1), "n": int(m.sum()),
                         "twist_deg_median": round(math.degrees(th), 2),
                         "twist_deg_iqr": [round(math.degrees(float(np.percentile(dang[m], 25))), 1), round(math.degrees(float(np.percentile(dang[m], 75))), 1)],
                         "r_p_mm": round(float(rP[m].mean()) * 1000, 2), "r_twin_mm": round(float(rQ[m].mean()) * 1000, 2),
                         "r_chord_mm": round(float(cyl(chord, c, a)[1].mean()) * 1000, 2),
                         "r_detwist_mm": round(float(cyl(det, c, a)[1].mean()) * 1000, 2),
                         "map_err_mm": round(float(np.linalg.norm(P - Qm, axis=1).mean()) * 1000, 2),
                         "map_err_detwist_mm": round(float(np.linalg.norm(P - Qd, axis=1).mean()) * 1000, 2),
                         "ring_centre_offset_mm": round(float(np.linalg.norm(CP[m] - CQ[m], axis=1).mean()) * 1000, 2)})
        res[n] = {"n": int(len(sel)), "len_mm": round(L * 1000, 1), "bins": bins}
        log(n, len(sel), [(b["twist_deg_median"], b["twist_deg_iqr"], b["r_p_mm"], b["r_chord_mm"], b["r_detwist_mm"], b["map_err_mm"], b["map_err_detwist_mm"], b["ring_centre_offset_mm"]) for b in bins])
    save_json(outp, res)


main()
