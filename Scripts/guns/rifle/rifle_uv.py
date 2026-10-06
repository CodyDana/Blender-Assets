"""AR-01 stage 3a: UVs for every LOD (headless Blender):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_uv.py

0. triangulates every part of every LOD (quads BEAUTY, custom normals kept): the export is triangles anyway, so the
   UVs, the bake's tangent frame and Unreal's MikkTSpace see the same triangles;
1. brings the LOD1-3 parts in from scratch/AR01_LOD<k>.blend (build_rifle --stage lod) as collections AR01_LOD1..3;
2. per LOD0 face: openness (can any ray escape, in any of 4 configurations: rest, bolt back, magazine out, selector
   down) -> hidden faces are class E; the other faces get their class from rifle_surface.face_class;
3. per LOD0 part: projection charts -> islands (gunlib.uvchart), overlapping islands split;
4. per set: the size (Metal: the smallest of 2048 / 4096 that holds the class floors at the fill minimum), one pack
   of all LOD0 islands, the island transforms; UV0 written on the LOD0 parts (each set in 0..1: the skeletal
   layout; the static twin's tile offsets are applied by the game stage);
5. every LOD1-3 face takes the island of its best-matching LOD0 face (same part; LOD3: same set) and each of its
   corners takes the UV of the closest point ON THAT ISLAND's LOD0 triangles, so a LOD face always samples the
   texels painted for the same surface and never reaches into a neighbour island;
6. report: densities per class, fill, islands, splits, LOD UV0 overlaps per set -> WorkFiles/guns/rifle/scratch/uv/
   (uv_report.json, islands.npz) and Assets/Guns/AR01.blend saved.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, BLEND, GRIP  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import rifle_surface as RS  # noqa: E402
from gunlib import uvchart as UC  # noqa: E402
from gunlib import uvbl as UB  # noqa: E402
from gunlib import rasterpack as RPK  # noqa: E402
from gunlib import fit as F  # noqa: E402

OUT = SCRATCH / "uv"
# the static twin's U tile per set (rifle_game.TILE) and the smallest UV1 square (rifle_game.UV1_REGIONS): the overlap
# checks run on what qa_check will read: float32 UVs shifted to the tile, and the same scaled into the UV1 square
TILE_OF_SET = {"Metal": 0.0, "Furniture": 1.0, "Mag": -1.0}
UV1_MIN_SCALE = 0.375


def qa_views(TT, st):
    """The UV triangles as qa_check reads them on the twin: UV0 (float32, tile-shifted) and UV1 (scaled, float32)."""
    t0 = (TT + np.array([TILE_OF_SET[st], 0.0])).astype(np.float32).astype(np.float64)
    t1 = (TT * UV1_MIN_SCALE).astype(np.float32).astype(np.float64)
    return t0, t1


def qa_overlaps(TT, st, eps):
    t0, t1 = qa_views(TT, st)
    a = UC.overlap_pairs(t0, eps, qa=True)
    b = UC.overlap_pairs(t1, eps, qa=True)
    if not len(b):
        return a
    if not len(a):
        return b
    return np.unique(np.vstack([a, b]), axis=0)
OUT.mkdir(parents=True, exist_ok=True)


def log(*a):
    print("[AR01-uv]", *a, flush=True)


def assert_lock():
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def bring_lods():
    for lv in (1, 2, 3):
        name = f"AR01_LOD{lv}"
        old = bpy.data.collections.get(name)
        if old is not None:
            for o in list(old.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(old)
        src = SCRATCH / f"AR01_LOD{lv}.blend"
        with bpy.data.libraries.load(str(src), link=False) as (df, dt):
            dt.collections = [c for c in df.collections if c == name]
        col = dt.collections[0]
        bpy.context.scene.collection.children.link(col)
        col.hide_render = True
        for o in col.objects:
            o.hide_render = True
    log("LOD collections in:", [c.name for c in bpy.data.collections if c.name.startswith("AR01_LOD")])


def frame_for(name, pm):
    if name in RS.MAG_ARC_PARTS:
        c = np.array(RS.MAG_ARC_C_M) - np.array(RS.GRIP_M)
        fr = UC.cyl_frame(c, (0.0, 1.0, 0.0), RS.MAG_ARC_U0)
        fr["polar_caps"] = True
        return fr
    if name in RS.CYL_PARTS:
        lo, hi = pm.V.min(0), pm.V.max(0)
        c = np.array([0.0, 0.5 * (lo[1] + hi[1]), 0.5 * (lo[2] + hi[2])])
        if name in ("barrel", "muzzle_brake"):
            c = np.array([0.0, 0.0, RS.BORE_Z_B])
        return UC.cyl_frame(c, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    if name in RS.FRAME_ROT_Y:
        return UC.box_frame(UC.rot_y(RS.FRAME_ROT_Y[name]))
    return UC.box_frame()


def visibility(parts, pms):
    """Per part: bool per face (some ray escapes in some configuration)."""
    names = list(parts)
    rec = {n: part_rec(parts[n]) for n in names}
    bolt_mm = rec.get("bolt_carrier", {}).get("joint", {}).get("travel_mm", 103.25)
    piv_sel = np.array([282.8, 0.0, -7.8]) - np.array(RS.GRIP_M)
    configs = {"rest": {}, "bolt_back": {"bolt_carrier": F.trans_matrix([-1, 0, 0], bolt_mm)},
               "mag_out": {"magazine": None, "magazine_floor_plate": None},
               "selector_down": {"selector": F.rot_matrix(piv_sel, [0, 1, 0], 32.0)}}
    vis = {n: np.zeros(pms[n].nf, bool) for n in names}
    for cname, moves in configs.items():
        t0 = time.time()
        use = [n for n in names if not (n in moves and moves[n] is None)]
        mats = [moves.get(n) for n in use]
        tree = UB.bvh_of_meshes([pms[n] for n in use], mats)
        nvis = 0
        for n, M in zip(use, mats):
            pm = pms[n]
            todo = ~vis[n]
            if not todo.any():
                continue
            C, N = pm.fc[todo], pm.fn[todo]
            if M is not None:
                M = np.asarray(M, float)
                C = (np.c_[C, np.ones(len(C))] @ M.T)[:, :3]
                N = N @ M[:3, :3].T
            o = UB.openness(C, N, tree)
            idx = np.nonzero(todo)[0]
            vis[n][idx[o > 0]] = True
            nvis += int((o > 0).sum())
        log("visibility", cname, "newly visible", nvis, "%.1fs" % (time.time() - t0))
    return vis


def main():
    assert_lock()
    t0 = time.time()
    bring_lods()
    ntri = 0
    for cn in ("AR01_Parts", "AR01_LOD1", "AR01_LOD2", "AR01_LOD3"):
        for o in bpy.data.collections[cn].objects:
            if o.type == "MESH":
                # the loop triangles every form gate measured (G5 holds); where they overlap or repeat a vertex
                # (a concave n-gon's fill: dropping one leaves a 3-face edge) the part falls back to the bmesh split
                keep = o.data.copy()
                UB.triangulate_as_looptris(o)
                if UB.nonmanifold_edges(o) > UB.nonmanifold_edges_of(keep):
                    bad = o.data
                    o.data = keep
                    bpy.data.meshes.remove(bad)
                    UB.triangulate_keep_normals(o)
                    log("loop-triangle split not manifold, bmesh split used:", o.name)
                else:
                    bpy.data.meshes.remove(keep)
                w, r = UB.fix_degenerates(o)       # qa: no 3-face edges from micron edges, no needle triangles
                if w or r:
                    log("degenerates fixed", o.name, "welded", w, "rotated", r)
                ntri += 1
    log("triangulated", ntri, "objects")
    parts = {o.name: o for o in bpy.data.collections["AR01_Parts"].objects if o.type == "MESH"}
    pms = {n: UB.part_mesh(o) for n, o in parts.items()}
    sets_of = {n: RS.SLOT_SET[part_rec(o)["slot"]] for n, o in parts.items()}
    vis = visibility(parts, pms)
    # ---------------------------------------------------------------- islands per LOD0 part
    isl = {}            # part -> dict(keys, luv, lab, cls, frame, base)
    gid = 0
    report = {"parts": {}, "sets": {}}
    for n, pm in pms.items():
        st = sets_of[n]
        zM = pm.fc[:, 2] + RS.GRIP_M[2]
        cls = np.array([RS.CLASS_CODE[RS.face_class(n, st, z, nz, v)]
                        for z, nz, v in zip(zM, pm.fn[:, 2], vis[n])])
        fr = frame_for(n, pm)
        r = UC.make_islands(pm, fr, cls)
        r["cls"] = cls
        r["frame"] = fr
        r["base"] = gid
        r["theta_face"] = UC.face_theta(pm, fr)
        nl = int(r["lab"].max()) + 1
        gid += nl
        isl[n] = r
        report["parts"][n] = {"set": st, "faces": int(pm.nf), "islands": nl, "split_islands": int(r["n_split"]),
                              "rect_cuts": int(r["n_rect_cuts"]), "absorbed_faces": int(r["absorbed_faces"]),
                              "overlaps_left": int(r["overlaps_left"]), "hidden_faces": int((~vis[n]).sum()),
                              "class_faces": {RS.CODE_CLASS[c]: int((cls == c).sum()) for c in np.unique(cls)}}
    log("islands", gid, "in %.1fs" % (time.time() - t0))
    # ---------------------------------------------------------------- LOD faces -> LOD0 islands (assignment)
    lod_objs = {}
    for lv in (1, 2, 3):
        for o in bpy.data.collections[f"AR01_LOD{lv}"].objects:
            lod_objs[o.name] = (lv, o)
    idx_part = {n: UB.FaceIndex([pms[n]]) for n in pms}
    idx_set = {}
    for st in RS.SETS:
        names = [n for n in pms if sets_of[n] == st]
        idx_set[st] = (names, UB.FaceIndex([pms[n] for n in names]))
    lod_map = {}
    for on, (lv, o) in lod_objs.items():
        base = on[: -len(f"_LOD{lv}")]
        pm = UB.part_mesh(o)
        tgt_part = np.empty(pm.nf, object)
        tgt_face = np.zeros(pm.nf, np.int64)
        dist = np.zeros(pm.nf)
        if lv < 3 and base in pms:
            ix = idx_part[base]
            for f in range(pm.nf):
                _, g, d = ix.best(pm.fc[f], pm.fn[f])
                tgt_part[f], tgt_face[f], dist[f] = base, g, d
            st = sets_of[base]
        else:
            st = RS.lod3_set(base)
            names, ix = idx_set[st]
            for f in range(pm.nf):
                mk, g, d = ix.best(pm.fc[f], pm.fn[f])
                tgt_part[f], tgt_face[f], dist[f] = names[mk], g, d
        lod_map[on] = {"lv": lv, "pm": pm, "part": tgt_part, "face": tgt_face, "set": st,
                       "dist_p95": float(np.percentile(dist, 95)) if len(dist) else 0.0}
    log("LOD faces assigned in %.1fs" % (time.time() - t0))
    # ---------------------------------------------------------------- per set: size, pack, write
    island_of_face = {n: isl[n]["base"] + isl[n]["lab"] for n in pms}
    aff_all = {}
    sizes = {}
    for st, cfg in RS.SETS.items():
        names = [n for n in pms if sets_of[n] == st]
        if not names:
            continue
        # texel need at the class floors (band minimum), visible faces only (E at its floor)
        need = 0.0
        for n in names:
            pm, r = pms[n], isl[n]
            for c in np.unique(r["cls"]):
                a = float(pm.farea[r["cls"] == c].sum())                 # mm^2
                dmin = cfg["bands"][RS.CODE_CLASS[c]][0] / 10.0           # px per mm
                need += a * dmin * dmin
        size = None
        for S in cfg["sizes"]:
            if need <= cfg["fill_min"] * S * S:
                size = S
                break
        if size is None:
            size = cfg["sizes"][-1]
        sizes[st] = {"size": size, "texels_needed_at_class_floors": round(need), "capacity_at_fill_min":
                     {str(S): round(cfg["fill_min"] * S * S) for S in cfg["sizes"]}}
        ref = max(cfg["classes"].values())
        ids, tris = [], []
        gmeta = {}
        for n in names:
            pm, r = pms[n], isl[n]
            lab = r["lab"]
            T, tf = pm.tris()
            for li in np.unique(lab):
                faces = np.nonzero(lab == li)[0]
                c = int(np.bincount(r["cls"][faces]).argmax())
                k = cfg["classes"][RS.CODE_CLASS[c]] / ref
                iid = int(r["base"] + li)
                ids.append(iid)
                tris.append(r["luv"][T[lab[tf] == li]] * k)
                gmeta[iid] = {"part": n, "cls": RS.CODE_CLASS[c], "k": k, "faces": faces}
        tp0 = time.time()
        # density ceiling: px/cm of class c = 10 x scale x k_c (charts in mm), so the scale is capped at
        # min_c(DENSITY_CEIL x band top_c / (10 k_c))
        cap = min(RS.DENSITY_CEIL * cfg["bands"][c][1] / (10.0 * cfg["classes"][c] / ref) for c in cfg["classes"])
        res = RPK.pack(tris, size, cfg["gap_px"][size], cfg["cell_px"][size], iters=8, scale_hi=cap)
        sizes[st]["scale_cap_px_per_unit"] = round(cap, 4)
        log("pack", st, size, "islands", len(ids), "fill %.3f" % res["fill"], "%.1fs" % (time.time() - tp0))
        for iid, A in zip(ids, res["affine"]):
            aff_all[iid] = (A, gmeta[iid]["k"])
        sizes[st]["pack"] = {"packer": "gunlib.rasterpack", "scale_px_per_unit": res["scale"],
                             "gap_px": res["gap_px"], "cell_px": res["cell_px"], "packed_fill": round(res["fill"], 4)}
        sizes[st]["islands"] = len(ids)
        sizes[st]["meta"] = {iid: {"part": v["part"], "cls": v["cls"]} for iid, v in gmeta.items()}
    # ---------------------------------------------------------------- write UV0 (LOD0 + LODs) and measure
    stats = {st: {} for st in RS.SETS}
    for n, o in parts.items():
        pm, r = pms[n], isl[n]
        uv = np.zeros((len(pm.loop_v), 2))
        isl_f = island_of_face[n]
        for iid in np.unique(isl_f):
            A, k = aff_all[int(iid)]
            ls = np.isin(pm.loop_f, np.nonzero(isl_f == iid)[0])
            uv[ls] = UC.apply_affine(A, r["luv"][ls] * k)
        UB.write_uv(o, "UV0", uv, first=True)
        st = sets_of[n]
        S = sizes[st]["size"]
        ua = UC.uv_area(uv, pm)
        dens = np.sqrt(ua * S * S / np.maximum(pm.farea, 1e-12)) * 10.0        # px/cm
        for c in np.unique(r["cls"]):
            sel = r["cls"] == c
            d = stats[st].setdefault(RS.CODE_CLASS[c], {"area": [], "dens": [], "uv": 0.0})
            d["area"].append(pm.farea[sel])
            d["dens"].append(dens[sel])
            d["uv"] += float(ua[sel].sum())
        o["uv_islands"] = json.dumps({"base": int(r["base"]), "n": int(r["lab"].max()) + 1})
    # LOD1-3 corners: projected with their island's chart (affine inside the island: no folds) when the projection
    # lands on the island's LOD0 footprint; otherwise snapped to the closest island point (its UV), so no LOD corner
    # ever leaves its island
    lod_overlaps = {}
    uv0_of = {n: np.array([d.uv[:] for d in parts[n].data.uv_layers["UV0"].data]) for n in parts}
    snaps, foot = {}, {}
    n_proj = n_snap = n_collapsed_off = 0
    off_by_lod = {1: 0, 2: 0, 3: 0}
    faces_by_lod = {1: 0, 2: 0, 3: 0}
    snap_dev = []
    for on, m in lod_map.items():
        pm = m["pm"]
        faces_by_lod[m["lv"]] += pm.nf
        uv = np.zeros((len(pm.loop_v), 2))
        for f in range(pm.nf):
            tp, g0 = m["part"][f], int(m["face"][f])
            r = isl[tp]
            iid = int(island_of_face[tp][g0])
            faces_i = np.nonzero(island_of_face[tp] == iid)[0]
            if iid not in snaps:
                snaps[iid] = UB.IslandSnap(pms[tp], faces_i, uv0_of[tp])
                foot[iid] = UB.footprint_tree(pms[tp], faces_i, r["luv"])
            key = int(r["keys"][g0])
            s0 = pms[tp].ps[g0]
            th = UC.unwrapped_theta(r["frame"], key, r["luv"][s0:s0 + 3])
            s, t = pm.ps[f], pm.pt[f]
            P = pm.V[pm.loop_v[s:s + t]]
            puv = UC.project_loops(P, np.full(t, key), r["frame"], np.full(t, th))
            A, k = aff_all[iid]
            cen = puv.mean(0)
            if UB.inside(foot[iid], cen):
                # corners off the island's footprint move toward the face centre until they are on it (a convex
                # pull: the face keeps its orientation and stays inside its island)
                for j in range(t):
                    q = puv[j]
                    if not UB.inside(foot[iid], q):
                        lo_, hi_ = 0.0, 1.0
                        for _ in range(12):
                            mid = 0.5 * (lo_ + hi_)
                            if UB.inside(foot[iid], cen + mid * (q - cen)):
                                lo_ = mid
                            else:
                                hi_ = mid
                        puv[j] = cen + lo_ * (q - cen)
                        n_snap += 1
                    else:
                        n_proj += 1
                uv[s:s + t] = UC.apply_affine(A, puv * k)
            else:
                # the face's centre projects off the island (a coarse LOD surface away from the LOD0 one): each corner
                # takes the closest island point's UV (on the face's own side of any seam); folds this makes are
                # collapsed by the overlap pass below
                uc, dd = snaps[iid].uv_at(pm.fc[f])
                for jj in range(t):
                    uv[s + jj], _ = snaps[iid].uv_near(P[jj], uc)
                snap_dev.append(dd)
                n_collapsed_off += 1
                off_by_lod[m["lv"]] += 1
        UB.write_uv(lod_objs[on][1], "UV0", uv, first=True)
        m["uv01"] = uv
    report["lod_corners"] = {"projected": n_proj, "pulled_in": n_snap, "faces_off_island_snapped": n_collapsed_off,
                             "off_island_by_lod": {f"LOD{k}": [v, faces_by_lod[k]] for k, v in off_by_lod.items()}}
    if snap_dev:
        report["lod_snap_distance_mm"] = {"p50": round(float(np.percentile(snap_dev, 50)), 3),
                                          "p95": round(float(np.percentile(snap_dev, 95)), 3),
                                          "max": round(float(np.max(snap_dev)), 3)}
    # LOD UV0 overlaps per (LOD, set) (the twin joins a LOD's parts and gives each set its own U tile, so qa_check's
    # uv_no_overlap sees exactly these groups): where two LOD triangles still overlap (two LOD surfaces that pull onto
    # the same island area), the smaller triangle collapses to its centre (it samples one texel; qa_check ignores
    # degenerate UV triangles). Counted in the report.
    collapsed = {}
    for lv in (1, 2, 3):
        for st in RS.SETS:
            ent = [(on, m) for on, m in lod_map.items() if m["lv"] == lv and m["set"] == st]
            if not ent:
                continue
            n_col = 0
            for _ in range(60):
                Ts, refs = [], []
                for on, m in ent:
                    T, tf = m["pm"].tris()
                    Ts.append(m["uv01"][T])
                    refs += [(on, int(f)) for f in tf]
                TT = np.vstack(Ts)
                pr = qa_overlaps(TT, st, 0.5e-5)
                if not len(pr):
                    break
                area = 0.5 * np.abs((TT[:, 1, 0] - TT[:, 0, 0]) * (TT[:, 2, 1] - TT[:, 0, 1])
                                    - (TT[:, 2, 0] - TT[:, 0, 0]) * (TT[:, 1, 1] - TT[:, 0, 1]))
                kill = set()
                for a, b in pr:
                    if a in kill or b in kill:
                        continue
                    kill.add(int(a if area[a] <= area[b] else b))
                for t in kill:
                    on, f = refs[t]
                    m = lod_map[on]
                    s0, n0 = m["pm"].ps[f], m["pm"].pt[f]
                    m["uv01"][s0:s0 + n0] = m["uv01"][s0:s0 + n0].mean(0)
                n_col += len(kill)
            collapsed[f"LOD{lv}/{st}"] = n_col
    for on, m in lod_map.items():
        UB.write_uv(lod_objs[on][1], "UV0", m["uv01"], first=True)
    report["lod_overlap_collapsed_faces"] = collapsed
    for lv in (1, 2, 3):
        for st in RS.SETS:
            Ts = []
            for on, m in lod_map.items():
                if m["lv"] != lv or m["set"] != st:
                    continue
                T, tf = m["pm"].tris()
                Ts.append(m["uv01"][T])
            if Ts:
                lod_overlaps[f"LOD{lv}/{st}"] = int(len(qa_overlaps(np.vstack(Ts), st, 1e-5)))
    # mirrored (flipped) UV triangles on LOD0 and the UV0 range of every LOD's parts (the skeletal layout: 0..1)
    flipped, umin, umax = 0, np.array([9.0, 9.0]), np.array([-9.0, -9.0])
    for n, o in parts.items():
        pm = pms[n]
        uv = np.array([d.uv[:] for d in o.data.uv_layers["UV0"].data])
        T, tf = pm.tris()
        U = uv[T]
        sa = (U[:, 1, 0] - U[:, 0, 0]) * (U[:, 2, 1] - U[:, 0, 1]) - (U[:, 2, 0] - U[:, 0, 0]) * (U[:, 1, 1] - U[:, 0, 1])
        flipped += int((sa < -1e-14).sum())
        umin, umax = np.minimum(umin, uv.min(0)), np.maximum(umax, uv.max(0))
    for on, m in lod_map.items():
        umin, umax = np.minimum(umin, m["uv01"].min(0)), np.maximum(umax, m["uv01"].max(0))
    report["lod0_flipped_uv_triangles"] = flipped
    report["uv0_range_all_lods"] = {"min": umin.round(5).tolist(), "max": umax.round(5).tolist()}
    # LOD0 overlaps per set
    lod0_overlaps = {}
    for st in RS.SETS:
        Ts = []
        for n, o in parts.items():
            if sets_of[n] != st:
                continue
            pm = pms[n]
            uv = np.array([d.uv[:] for d in o.data.uv_layers["UV0"].data])
            T, tf = pm.tris()
            Ts.append(uv[T])
        if Ts:
            lod0_overlaps[st] = int(len(qa_overlaps(np.vstack(Ts), st, 1e-5)))   # qa_check's own rules (UV0 + UV1)
    # ---------------------------------------------------------------- report
    out_sets = {}
    for st, d in stats.items():
        if st not in sizes:
            continue
        S = sizes[st]["size"]
        cls_rep = {}
        tot_uv = 0.0
        for c, v in d.items():
            a = np.concatenate(v["area"])
            de = np.concatenate(v["dens"])
            o = np.argsort(de)
            cw = np.cumsum(a[o]) / max(a.sum(), 1e-12)
            q = lambda p: float(de[o][min(np.searchsorted(cw, p), len(o) - 1)])   # noqa: E731
            band = RS.SETS[st]["bands"][c]
            med = q(0.5)
            cls_rep[c] = {"area_cm2": round(float(a.sum()) / 100.0, 1), "px_per_cm_p5": round(q(0.05), 1),
                          "px_per_cm_median": round(med, 1), "px_per_cm_p95": round(q(0.95), 1), "band": band,
                          "floor_ok": med >= band[0], "uniform_p5_p95_within_25pct": bool(q(0.05) >= 0.75 * med and q(0.95) <= 1.25 * med),
                          "over_band_top": round(med / band[1], 2)}
            tot_uv += v["uv"]
        out_sets[st] = dict(sizes[st], fill=round(tot_uv, 4), classes=cls_rep)
        out_sets[st].pop("meta", None)
    report["sets"] = out_sets
    report["lod0_uv0_overlap_pairs"] = lod0_overlaps
    report["lod_uv0_overlap_pairs"] = lod_overlaps
    report["lod_assign_dist_p95_mm"] = {on: round(m["dist_p95"], 3) for on, m in lod_map.items()}
    report["seconds"] = round(time.time() - t0, 1)
    (OUT / "uv_report.json").write_text(json.dumps(report, indent=1))
    np.savez_compressed(OUT / "islands.npz", **{f"{n}__cls": isl[n]["cls"] for n in isl},
                        **{f"{n}__isl": island_of_face[n] for n in isl})
    (OUT / "sets.json").write_text(json.dumps({st: {"size": v["size"], "slot": RS.SETS[st]["slot"],
                                                    "meta": {str(k): vv for k, vv in v["meta"].items()}}
                                               for st, v in sizes.items()}, indent=0))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log("sets", json.dumps({k: {"size": v["size"], "fill": v["fill"]} for k, v in out_sets.items()}))
    log("UV_DONE %.1fs" % (time.time() - t0))


main()
