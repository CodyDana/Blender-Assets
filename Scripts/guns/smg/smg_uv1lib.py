"""SMG01 authored lightmap UV1 as a function (W3): the W2 method of smg_uv1.py (projection charts with depth layers per
part, the LM_KEEP largest charts packed at 64 px with 2 px padding by smg_lmpack, every other face a zero-area UV1 at
the nearest packed host face that faces the same way) for ANY set of objects with per-face visibility: each LOD1-3 of
the twin (gun + merged magazine) and the shipped magazine alone (SM_SMG01_Mag LOD0-3). UD4 is measured on the npz
this writes (smg_ud4.measure). Import inside Blender.
"""
from __future__ import annotations

import numpy as np
from mathutils.kdtree import KDTree

import smg_surface as SS
import smg_lmpack as LMP
from gunlib import uvchart as UC
from gunlib import uvbl as UB

LM_SIZE, LM_GAP = 64, 2
LM_LAYERS, LM_MIN_LAYER_MM2 = 3, 150.0
LM_KEEP, LM_MIN_KEEP_MM2 = 90, 250.0
HOST_COS = 0.3


def base_name(n):
    for k in (1, 2, 3):
        if n.endswith(f"_LOD{k}"):
            return n[: -len(f"_LOD{k}")]
    return n


def frame_for(name, pm):
    b = base_name(name)
    if b in SS.CYL_X:
        return UC.cyl_frame(np.array([0.0, 0.0, SS.BORE_Z_B]), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    if b in SS.CYL_Z:
        return UC.cyl_frame(np.array([SS.HINGE_AXIS_B[0], SS.HINGE_AXIS_B[1], 0.0]), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
    return UC.box_frame()


def charts_of(n, pm, vis):
    """Projection charts with depth layers: (loop UVs (mm), face label (-1 hidden))."""
    fr = frame_for(n, pm)
    keys = UC.chart_keys(pm, fr)
    luv = UC.loop_uv(pm, keys, fr)
    lab = np.where(vis, keys, -1).astype(np.int64)
    T, tf = pm.tris()
    U = luv[T]
    layer = np.zeros(pm.nf, np.int64)
    for key in np.unique(lab[lab >= 0]):
        fsel = np.nonzero(lab == key)[0]
        tsel = np.nonzero(np.isin(tf, fsel))[0]
        pr = UC.overlap_pairs(U[tsel], 1e-4)
        if not len(pr):
            continue
        fa, fb = tf[tsel[pr[:, 0]]], tf[tsel[pr[:, 1]]]
        m = fa != fb
        conf = {}
        for x, y in zip(fa[m].tolist(), fb[m].tolist()):
            conf.setdefault(x, set()).add(y)
            conf.setdefault(y, set()).add(x)
        placed = set()
        for f in sorted(conf, key=lambda f: -pm.farea[f]):
            used = {int(layer[g]) for g in conf[f] if g in placed}
            L = 0
            while L in used:
                L += 1
            layer[f] = L
            placed.add(f)
    lab = np.where(lab >= 0, lab * 100 + np.minimum(layer, 99), -1)
    return luv, lab


def author(parts, vis, keep=LM_KEEP, min_keep_mm2=LM_MIN_KEEP_MM2):
    """parts: {name: object}; vis: {name: bool per face}. Writes UV1 (index 1) on every object; returns (report, tris
    (n, 3, 2) of every triangle's UV1, chart id per triangle) for UD4."""
    pms = {n: UB.part_mesh(o) for n, o in parts.items()}
    cand, luvs, labs = [], {}, {}
    for n, pm in pms.items():
        luv, lab = charts_of(n, pm, vis[n])
        luvs[n], labs[n] = luv, lab
        for g in np.unique(lab[lab >= 0]):
            a = float(pm.farea[lab == g].sum())
            small_layer = (g % 100) >= LM_LAYERS or ((g % 100) > 0 and a < LM_MIN_LAYER_MM2)
            cand.append((a if not small_layer else 0.0, n, int(g)))
    cand.sort(key=lambda t: -t[0])
    kept = [c for c in cand[:keep] if c[0] >= min_keep_mm2]
    if not kept:                                   # a tiny object set: its largest chart alone
        kept = cand[:1]
    charts = []
    for a, n, g in kept:
        T, tf = pms[n].tris()
        charts.append(luvs[n][T[labs[n][tf] == g]])
    res = LMP.pack(charts, LM_SIZE, LM_GAP)
    uv1 = {n: np.full((len(pm.loop_v), 2), np.nan) for n, pm in pms.items()}
    chart_of = {n: np.full(pm.nf, -1, np.int64) for n, pm in pms.items()}
    for k, ((a, n, g), A) in enumerate(zip(kept, res["affine"])):
        pm = pms[n]
        fs = np.nonzero(labs[n] == g)[0]
        ls = np.isin(pm.loop_f, fs)
        uv1[n][ls] = UC.apply_affine(A, luvs[n][ls])
        chart_of[n][fs] = k
    hc, hn, huv = [], [], []
    for n, pm in pms.items():
        fs = np.nonzero(chart_of[n] >= 0)[0]
        if not len(fs):
            continue
        hc.append(pm.fc[fs])
        hn.append(pm.fn[fs])
        u = np.add.reduceat(uv1[n], pm.ps)[fs] / pm.pt[fs][:, None]
        huv.append(u)
    hc, hn, huv = np.vstack(hc), np.vstack(hn), np.vstack(huv)
    kd = KDTree(len(hc))
    for i, c in enumerate(hc):
        kd.insert(c.tolist(), i)
    kd.balance()
    hosted = {"visible_faces": 0, "visible_area_mm2": 0.0, "hidden_faces": 0}
    dists = []
    for n, pm in pms.items():
        for f in np.nonzero(chart_of[n] < 0)[0]:
            hits = kd.find_n(pm.fc[f].tolist(), 12)
            pick = None
            for co, i, d in hits:
                if float(hn[i] @ pm.fn[f]) >= HOST_COS:
                    pick = (i, d)
                    break
            if pick is None:
                pick = (hits[0][1], hits[0][2])
            s, t = pm.ps[f], pm.pt[f]
            uv1[n][s:s + t] = huv[pick[0]]
            if vis[n][f]:
                hosted["visible_faces"] += 1
                hosted["visible_area_mm2"] += float(pm.farea[f])
                dists.append(pick[1])
            else:
                hosted["hidden_faces"] += 1
    vis_area = sum(float(pms[n].farea[vis[n]].sum()) for n in pms)
    hosted["visible_area_fraction"] = round(hosted["visible_area_mm2"] / max(vis_area, 1e-9), 4)
    hosted["host_distance_mm_p50_p95_max"] = ([round(float(np.percentile(dists, q)), 2) for q in (50, 95)] +
                                              [round(float(np.max(dists)), 2)]) if dists else []
    for n, o in parts.items():
        UB.write_uv(o, "UV1", uv1[n])
        me = o.data
        me.uv_layers.active = me.uv_layers["UV0"]
        try:
            me.uv_layers["UV0"].active_render = True
        except Exception:  # noqa: BLE001
            pass
        assert me.uv_layers[0].name == "UV0" and me.uv_layers[1].name == "UV1", [l.name for l in me.uv_layers]
    T1, C1 = [], []
    for n, pm in pms.items():
        T, tf = pm.tris()
        T1.append(uv1[n][T])
        C1.append(chart_of[n][tf])
    T1 = np.vstack(T1)
    C1 = np.concatenate(C1)
    ovl = int(len(UC.overlap_pairs(T1.astype(np.float32).astype(np.float64), 1e-5, qa=True)))
    rep = {"size_px": LM_SIZE, "pack_ring_cells": LM_GAP, "charts_total": len(cand), "charts_packed": len(kept),
           "smallest_packed_mm2": round(kept[-1][0], 1), "fill": round(res["fill"], 4),
           "scale_px_per_mm": res["scale"], "hosted": hosted, "overlap_pairs_qa": ovl,
           "range": {"min": T1.reshape(-1, 2).min(0).round(5).tolist(),
                     "max": T1.reshape(-1, 2).max(0).round(5).tolist()}}
    return rep, T1, C1
