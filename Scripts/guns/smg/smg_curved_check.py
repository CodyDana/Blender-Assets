"""SMG01 W4b close-up r2: does the SHADING follow the curved surfaces? (headless Blender, read-only)

    blender -b --factory-startup <blend> --python Scripts/guns/smg/smg_curved_check.py -- --out <json>

For every part (objects carrying gun_part_report) the large regions are grown exactly as smg_parts._flatten_planar
grows them (seed >= 20 mm2, neighbours within 3 deg and 0.6 mm of the seed's plane) and classified with
smg_parts._curved_region (the deviation field's linear fit: R^2 >= 0.8, span >= 1.5 deg). For each CURVED region the
script compares the spread of the faces' SHADING normals (the mean of each face's corner normals) with the spread of
their GEOMETRIC normals (max angle from the area-weighted mean): a curved surface flattened into one plane shades with
ratio ~0 (the r1 'bands'), a smoothly shaded one ~1. Writes per-part rows and the area-weighted ratio.
"""
from __future__ import annotations

import json
import math
import sys
from collections import deque
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import smg_parts as SP  # noqa: E402


def regions(me):
    nP, nL, nE, nV = len(me.polygons), len(me.loops), len(me.edges), len(me.vertices)
    pn = np.empty(nP * 3)
    me.polygons.foreach_get("normal", pn)
    pn = pn.reshape(-1, 3)
    pa = np.empty(nP)
    me.polygons.foreach_get("area", pa)
    pa *= 1e6
    pc = np.empty(nP * 3)
    me.polygons.foreach_get("center", pc)
    pc = pc.reshape(-1, 3) * 1000.0
    ls = np.empty(nP, int)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(nP, int)
    me.polygons.foreach_get("loop_total", lt)
    le = np.empty(nL, int)
    me.loops.foreach_get("edge_index", le)
    lv = np.empty(nL, int)
    me.loops.foreach_get("vertex_index", lv)
    lp = np.repeat(np.arange(nP), lt)
    co = np.empty(nV * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) * 1000.0
    cn = np.empty(nL * 3)
    me.corner_normals.foreach_get("vector", cn)
    cn = cn.reshape(-1, 3)
    ef = [[] for _ in range(nE)]
    for k in range(nL):
        ef[le[k]].append(lp[k])
    fe = [le[ls[i]:ls[i] + lt[i]] for i in range(nP)]
    fv = [lv[ls[i]:ls[i] + lt[i]] for i in range(nP)]
    cos_tol = math.cos(math.radians(SP.FLAT_TOL_DEG))
    cos_sl = math.cos(math.radians(SP.FLAT_SLIVER_DEG))
    thin = np.zeros(nP, bool)
    for i in range(nP):
        if pa[i] < 8.0:
            P_ = co[fv[i]]
            emax = max(float(np.linalg.norm(P_[k] - P_[(k + 1) % len(P_)])) for k in range(len(P_)))
            thin[i] = emax / max(pa[i], 1e-9) > 3.0
    owner = np.full(nP, -1)
    regs = []
    for f in np.argsort(-pa):
        if pa[f] < SP.FLAT_SEED_MM2:
            break
        if owner[f] >= 0:
            continue
        n0, p0 = pn[f], pc[f]
        reg = [f]
        owner[f] = len(regs)
        q = deque([f])
        while q:
            a = q.popleft()
            for e in fe[a]:
                for g in ef[e]:
                    if owner[g] >= 0:
                        continue
                    if pn[g] @ n0 < cos_tol and not (pn[g] @ n0 >= cos_sl and thin[g]):
                        continue
                    if np.max(np.abs((co[fv[g]] - p0) @ n0)) > SP.FLAT_TOL_MM:
                        continue
                    owner[g] = len(regs)
                    reg.append(g)
                    q.append(g)
        regs.append(reg)
    sn = np.zeros((nP, 3))
    for i in range(nP):
        v = cn[ls[i]:ls[i] + lt[i]].mean(0)
        sn[i] = v / max(np.linalg.norm(v), 1e-12)
    return regs, pn, pa, pc, sn


def spread(N, w):
    n0 = (N * w[:, None]).sum(0)
    n0 /= np.linalg.norm(n0)
    return float(np.degrees(np.arccos(np.clip(N @ n0, -1.0, 1.0))).max())


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = Path(argv[argv.index("--out") + 1])
    rows, tot_w, tot_r = {}, 0.0, 0.0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or "gun_part_report" not in ob or "_LOD" in ob.name:
            continue                                      # LOD0 parts (a W3 blend also carries the LOD1-3 parts)
        regs, pn, pa, pc, sn = regions(ob.data)
        rr = []
        for reg in regs:
            if pa[reg].sum() < SP.FLAT_MIN_AREA_MM2:
                continue
            cv, met = SP._curved_region(reg, pn, pa, pc)
            if not cv:
                continue
            r = np.asarray(reg)
            g = spread(pn[r], pa[r])
            s = spread(sn[r], pa[r])
            ratio = s / max(g, 1e-9)
            area = float(pa[r].sum())
            rr.append({"area_mm2": round(area, 1), "geometric_spread_deg": round(g, 2),
                       "shading_spread_deg": round(s, 2), "ratio": round(ratio, 3), **met})
            tot_w += area
            tot_r += area * min(ratio, 1.5)
        if rr:
            rows[ob.name] = rr
    res = {"curved_regions": sum(len(v) for v in rows.values()),
           "curved_area_mm2": round(tot_w, 1),
           "area_weighted_shading_ratio": round(tot_r / max(tot_w, 1e-9), 3),
           "by_part": rows}
    out.write_text(json.dumps(res, indent=1))
    print("[curved_check]", res["curved_regions"], res["curved_area_mm2"], res["area_weighted_shading_ratio"])


main()
