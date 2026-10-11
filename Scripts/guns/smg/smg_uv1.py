"""SMG01 W2a': the authored lightmap UV1 of the LOD0 parts (headless Blender, after smg_uv.py; plan Q13, gate UD4):

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_uv1.py

A 625 mm gun on a 64 px lightmap has ~1 cm texels (at the pack's scale ~3 cm), so a lightmap chart per UV0 island
(5,500) or per connected piece (1,700) cannot hold 2 px padding. Method:
1. PROJECTION charts per part: the part's frame (box keys / cylinder side + caps) on its visible faces; faces that
   overlap inside one projection go to depth layers (greedy by area; each layer is a chart; extra layers past 3 or
   under 150 mm2 are 'small');
2. the LM_KEEP largest charts (each >= LM_MIN_KEEP_MM2) are packed, ONE raster pack at 64 px with 2 px padding
   (smg_lmpack: gunlib.rasterpack's method with an unclipped conservative raster and a square padding ring, i.e. the
   UD4 measure itself);
3. every other visible face (pins, screws, sight leaves, small layers: sub-texel at 64 px) takes a ZERO-AREA UV1 at
   the centre of the nearest packed host face that faces the same way (within 72 deg): it reads the lightmap texel of
   the surface it sits on and takes no texel itself (no overlap; qa_check's overlap rule ignores zero-area UVs);
   hidden faces (class E, no ray reaches them in any configuration) the same;
4. UD4 measured right after (smg_ud4.py on scratch/uv/uv1_lod0.npz: conservative raster at 64 and 128 px, 2 px).
Writes UV1 on every part, scratch/uv/uv1_lod0.npz, scratch/uv/uv1_report.json; saves the blend.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SCRATCH, BLEND, PARTS_COLL  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402

import smg_surface as SS  # noqa: E402
from gunlib import uvchart as UC  # noqa: E402
from gunlib import uvbl as UB  # noqa: E402
import smg_lmpack as LMP  # noqa: E402

OUT = SCRATCH / "uv"
LM_SIZE, LM_GAP = 64, 2
LM_LAYERS, LM_MIN_LAYER_MM2 = 3, 150.0
LM_KEEP, LM_MIN_KEEP_MM2 = 90, 250.0
HOST_COS = 0.3


def log(*a):
    print("[SMG01-uv1]", *a, flush=True)


def frame_for(name, pm):
    if name in SS.CYL_X:
        return UC.cyl_frame(np.array([0.0, 0.0, SS.BORE_Z_B]), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    if name in SS.CYL_Z:
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


def main():
    from pipeline import lock as L
    L.assert_owner("SMG01", "claude")
    t0 = time.time()
    parts = {o.name: o for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"}
    pms = {n: UB.part_mesh(o) for n, o in parts.items()}
    isl = np.load(OUT / "islands.npz")
    vis = {n: isl[f"{n}__vis"].astype(bool) for n in parts}
    cand = []                   # (area mm2, part, label)
    luvs, labs = {}, {}
    for n, pm in pms.items():
        luv, lab = charts_of(n, pm, vis[n])
        luvs[n], labs[n] = luv, lab
        for g in np.unique(lab[lab >= 0]):
            a = float(pm.farea[lab == g].sum())
            small_layer = (g % 100) >= LM_LAYERS or ((g % 100) > 0 and a < LM_MIN_LAYER_MM2)
            cand.append((a if not small_layer else 0.0, n, int(g)))
    cand.sort(key=lambda t: -t[0])
    keep = [c for c in cand[:LM_KEEP] if c[0] >= LM_MIN_KEEP_MM2]
    log("charts", len(cand), "kept", len(keep), "smallest kept %.0f mm2" % keep[-1][0])
    charts = []
    for a, n, g in keep:
        T, tf = pms[n].tris()
        charts.append(luvs[n][T[labs[n][tf] == g]])
    tp = time.time()
    res = LMP.pack(charts, LM_SIZE, LM_GAP)
    log("pack", len(charts), "charts, fill %.4f, scale %.5f px/mm, %.1fs" % (res["fill"], res["scale"],
                                                                        time.time() - tp))
    uv1 = {n: np.full((len(pm.loop_v), 2), np.nan) for n, pm in pms.items()}
    chart_of = {n: np.full(pm.nf, -1, np.int64) for n, pm in pms.items()}
    for k, ((a, n, g), A) in enumerate(zip(keep, res["affine"])):
        pm = pms[n]
        fs = np.nonzero(labs[n] == g)[0]
        ls = np.isin(pm.loop_f, fs)
        uv1[n][ls] = UC.apply_affine(A, luvs[n][ls])
        chart_of[n][fs] = k
    # host faces: every face of a packed chart (frame B mm centres, normals, the UV1 of its centre)
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
    hosted = {"visible_faces": 0, "visible_area_mm2": 0.0, "hidden_faces": 0, "max_host_distance_mm": 0.0}
    dists = []
    for n, pm in pms.items():
        todo = np.nonzero(chart_of[n] < 0)[0]
        for f in todo:
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
    hosted["visible_area_fraction"] = round(hosted["visible_area_mm2"] / vis_area, 4)
    hosted["host_distance_mm_p50_p95_max"] = [round(float(np.percentile(dists, q)), 2) for q in (50, 95)] + \
        [round(float(np.max(dists)), 2)] if dists else []
    hosted.pop("max_host_distance_mm")
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
    np.savez_compressed(OUT / "uv1_lod0.npz", tris=T1, chart=np.concatenate(C1))
    ovl = int(len(UC.overlap_pairs(T1.astype(np.float32).astype(np.float64), 1e-5, qa=True)))
    rep = {"method": __doc__.split("Method:")[1].split("Writes")[0].strip(), "size_px": LM_SIZE,
           "pack_ring_cells": LM_GAP, "charts_total": len(cand), "charts_packed": len(keep),
           "smallest_packed_mm2": round(keep[-1][0], 1), "fill": round(res["fill"], 4),
           "scale_px_per_mm": res["scale"], "hosted": hosted, "overlap_pairs_qa": ovl,
           "range": {"min": T1.reshape(-1, 2).min(0).round(5).tolist(), "max": T1.reshape(-1, 2).max(0).round(5).tolist()},
           "seconds": round(time.time() - t0, 1)}
    (OUT / "uv1_report.json").write_text(json.dumps(rep, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log(json.dumps({k: v for k, v in rep.items() if k != "method"}))
    log("UV1_DONE")


main()
