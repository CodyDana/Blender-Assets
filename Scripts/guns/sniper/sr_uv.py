"""SR01 W2a: UVs of the LOD0 parts (headless Blender; the AR-01's rifle_uv.py method, LOD1-3 follow in W3):

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_uv.py

0. triangulates every part (quads BEAUTY via the loop triangles, custom normals kept; the export is triangles, so the
   UVs, the bake's tangent frame and Unreal's MikkTSpace see the same triangles);
1. per face: visibility (can any ray escape in ANY configuration: rest, every B3 joint at its ends (bolt and charging
   handle back, the lever locked, trigger pulled, selector SAFE / AUTO, paddle pressed, latch pressed, stock folded,
   sights folded) and the magazine out); the magazine's faces are judged on the magazine ALONE (it is its own asset);
   hidden faces are class E, the rest get their class from sr_surface.face_class;
2. per part: projection charts -> islands (gunlib.uvchart), overlapping islands split, over-long islands split;
3. per set: the smallest power of two that holds the class floors at the fill minimum, one raster pack
   (gunlib.rasterpack) of the set's islands, every class at its packing ratio, the scale capped at 1.25 x each band
   top; UV0 written (each set in 0..1: the skeletal layout; the twin's tiles are applied when it is joined);
4. report (densities per class, fill, islands, overlaps, mirrored triangles) -> scratch/uv/ (uv_report.json,
   islands.npz, islands_full.npz for the W3 LOD transfer, sets.json); Assets/Guns/SR01.blend saved.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_surface import ROOT, SCRATCH, WBLEND as BLEND, COLL as PARTS_COLL  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sr_surface as SS  # noqa: E402
import sr_uvproj as UP  # noqa: E402
from gunlib import uvchart as UC  # noqa: E402
from gunlib import uvbl as UB  # noqa: E402
from gunlib import rasterpack as RPK  # noqa: E402
from gunlib import fit as F  # noqa: E402

WEDGES = {}
COLLAPSED = {}
OUT = SCRATCH / "uv"
OUT.mkdir(parents=True, exist_ok=True)
LONG_FRAC = 0.80


def log(*a):
    print("[SR01-uv]", *a, flush=True)


def assert_lock():
    from pipeline import lock as L
    L.assert_owner("SR01", "claude")


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def frame_for(name, pm):
    if name in SS.CYL:
        c, w, u0 = SS.CYL[name]
        return UC.cyl_frame(np.array(c, float), w, u0)
    return UC.box_frame()


def configs():
    """Visibility configurations: rest + every B3 joint at its far end(s) (+ pre-poses) + the magazine out."""
    # SR01: the sr_motion poses (frame M mm) as frame-B matrices on the part meshes' coordinates
    import sr_motion as MO
    out = {"rest": {}}
    if SS.TARGET != "gun":
        return out
    out["mag_out"] = {n: None for n in SS.MAG_PARTS}
    bones = {o.name: part_rec(o).get("bone") for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"}
    G = np.array(SS.GRIP_M, float)

    def toB(Mm):
        Tm, Tp = np.eye(4), np.eye(4)
        Tm[:3, 3], Tp[:3, 3] = -G, G
        return Tm @ Mm @ Tp

    def pose(fn):
        o = {}
        for n, b in bones.items():
            M = fn(b)
            if M is not None:
                o[n] = toB(M)
        return o
    out["bolt_open_back"] = pose(lambda b: MO.bolt(MO.BOLT_ROT, MO.BOLT_TRAVEL) if b == "bolt" else None)
    out["bolt_open"] = pose(lambda b: MO.bolt(MO.BOLT_ROT, 0.0) if b == "bolt" else None)
    out["trigger_pulled"] = pose(lambda b: MO.trigger(6.0) if b == "trigger" else None)
    out["safety_fire"] = pose(lambda b: MO.selector(-12.0) if b == "selector" else None)
    out["release_pressed"] = pose(lambda b: MO.mag_release(-4.5) if b == "mag_release" else None)
    for dz in MO.RISER:
        out[f"riser@{dz:g}"] = pose(lambda b, dz=dz: MO.riser(dz) if b == "cheek_riser" else None)

    def bip(b, cant, ext, fold=90.0):
        if b == "bipod":
            return MO.cant(cant)
        for s in ("l", "r"):
            if b == f"bipod_leg_{s}":
                return MO.leg(s, fold, cant)
            if b == f"bipod_leg_{s}_ext":
                return MO.leg_ext(s, fold, ext, cant)
        return None
    for cant in (-15.0, 0.0, 15.0):
        out[f"bipod_deployed_ext76_cant{cant:g}"] = pose(lambda b, c=cant: bip(b, c, 76.0))
    out["bipod_deployed_ext0"] = pose(lambda b: bip(b, 0.0, 0.0))
    out["bipod_folded_ext76"] = pose(lambda b: bip(b, 0.0, 76.0, 0.0))
    return out


def visibility(parts, pms):
    """Per part: bool per face (some ray escapes in some configuration). Gun parts: the gun's configurations (the
    magazine seated except in mag_out). Magazine parts: the magazine alone."""
    names = list(parts)
    gun = [n for n in names if n not in SS.MAG_PARTS]
    mag = [n for n in names if n in SS.MAG_PARTS]
    vis = {n: np.zeros(pms[n].nf, bool) for n in names}

    def run(cname, use, moves, test):
        t0 = time.time()
        mats = [moves.get(n) for n in use]
        tree = UB.bvh_of_meshes([pms[n] for n in use], mats)
        nvis = 0
        for n, M in zip(use, mats):
            if n not in test:
                continue
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
    for cname, moves in configs().items():
        use = [n for n in names if not (n in moves and moves[n] is None)]
        run(cname, use, moves, set(gun))
    if mag:
        run("magazine_alone", mag, {}, set(mag))
    return vis


def lone_wedges(ob, max_deg=0.1, short_mm=0.3, max_turn_deg=20.0):
    """UD3 (W2): a needle wedge triangle (a corner < max_deg, its short edge < short_mm) whose apex is ALONE in its
    tangent group (every other face at the apex turns > 25 deg from it: a separate normal group) gets a zero MikkTSpace
    tangent in Unreal (float32 corner angle 0) whatever its UVs. Such a wedge loses its short edge (the two base vertices
    merge at its midpoint, a move <= short_mm / 2) when the link condition holds and no surviving face turns by more
    than max_turn_deg: the AR-01 UV stage's fix_degenerates rule (micron welds, needle rotations) extended to this
    case. Returns [(face centre mm, short edge mm)]."""
    import bmesh
    import math as _m
    k = 0.001
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    done = []
    for f in list(bm.faces):
        if not f.is_valid or len(f.verts) != 3:
            continue
        vs = list(f.verts)
        P = [v.co.copy() for v in vs]
        ang = []
        for i in range(3):
            a, b = P[(i + 1) % 3] - P[i], P[(i + 2) % 3] - P[i]
            ang.append(_m.degrees(a.angle(b)) if a.length > 0 and b.length > 0 else 0.0)
        i = int(np.argmin(ang))
        if ang[i] >= max_deg:
            continue
        A, Bv, Cv = vs[i], vs[(i + 1) % 3], vs[(i + 2) % 3]
        if (Bv.co - Cv.co).length >= short_mm * k:
            continue
        n = f.normal
        if any(g is not f and g.normal.dot(n) > _m.cos(_m.radians(25.0)) for g in A.link_faces):
            continue                                         # the apex has a same-normal neighbour: not alone
        nbB = {e.other_vert(Bv) for e in Bv.link_edges}
        nbC = {e.other_vert(Cv) for e in Cv.link_edges}
        if len(nbB & nbC) != 2:
            continue                                         # link condition
        mid = (Bv.co + Cv.co) * 0.5
        ok = True
        for v in (Bv, Cv):
            for g in v.link_faces:
                if g is f or (Bv in g.verts and Cv in g.verts):
                    continue
                co = [mid if w in (Bv, Cv) else w.co for w in g.verts]
                nn = (co[1] - co[0]).cross(co[2] - co[0])
                if nn.length < 1e-14 or nn.normalized().dot(g.normal) < _m.cos(_m.radians(max_turn_deg)):
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue
        c = (P[0] + P[1] + P[2]) / 3.0
        done.append(([round(x * 1000.0, 2) for x in c], round((Bv.co - Cv.co).length * 1000.0, 3)))
        bmesh.ops.pointmerge(bm, verts=[Bv, Cv], merge_co=mid)
    if done:
        bm.to_mesh(ob.data)
        ob.data.update()
    bm.free()
    return done


def flatten_hidden(ob, pm, vis, max_deg=1.0, edge_on_dot=0.5):
    """UD3 (W2), with NO geometry move: a face no ray reaches in any configuration (class E) that is a sliver (a corner
    < max_deg) or is seen edge-on by one of its corner normals (|n_face . n_corner| < edge_on_dot: a hidden ledge
    sharing a visible wall's smooth normal) gets FLAT corner normals (its own face normal), its edges marked sharp so
    the visible neighbours keep theirs. In MikkTSpace such a corner then has its true angle (a 0.2 deg wedge apex
    passes float32's 0.1 deg; an edge-on corner is no longer edge-on). Hidden faces are never seen: a no-op for the
    look. Returns the number of faces flattened."""
    me = ob.data
    nl = len(me.loops)
    cn = np.empty(nl * 3, np.float32)
    me.corner_normals.foreach_get("vector", cn)
    cn = cn.reshape(-1, 3).astype(np.float64)
    fn = pm.fn
    P3 = pm.V[pm.loop_v]
    ang = np.full(pm.nf, 180.0)
    for j in range(3):
        a_ = P3[pm.ps + (j + 1) % 3] - P3[pm.ps + j]
        b_ = P3[pm.ps + (j + 2) % 3] - P3[pm.ps + j]
        ang = np.minimum(ang, np.degrees(np.arctan2(np.linalg.norm(np.cross(a_, b_), axis=1),
                                                    np.einsum("ij,ij->i", a_, b_))))
    dmin = np.min(np.abs(np.einsum("ij,ij->i", cn, fn[pm.loop_f])).reshape(-1, 3), axis=1)
    # a sliver only when its needle corner is ALREADY alone in its normal group (flattening a sliver that shares its
    # corner normal with a neighbour would isolate it) and its true angle clears float32's 0.1 deg once flat
    amin = np.zeros(pm.nf, np.int64)
    best = np.full(pm.nf, 180.0)
    for j in range(3):
        a_ = P3[pm.ps + (j + 1) % 3] - P3[pm.ps + j]
        b_ = P3[pm.ps + (j + 2) % 3] - P3[pm.ps + j]
        aj = np.degrees(np.arctan2(np.linalg.norm(np.cross(a_, b_), axis=1), np.einsum("ij,ij->i", a_, b_)))
        upd = aj < best
        best[upd], amin[upd] = aj[upd], j
    lv = pm.loop_v
    alone = np.zeros(pm.nf, bool)
    for f in np.nonzero((~vis) & (ang < max_deg) & (ang >= 0.12))[0]:
        l0 = pm.ps[f] + amin[f]
        same = np.nonzero(lv == lv[l0])[0]
        same = same[same != l0]
        alone[f] = not np.any(np.abs(cn[same] @ cn[l0]) > 0.9999)
    sel = (~vis) & (alone | (dmin < edge_on_dot))
    if not sel.any():
        return 0
    ls = np.isin(pm.loop_f, np.nonzero(sel)[0])
    cn[ls] = fn[pm.loop_f[ls]]
    sharp = me.attributes.get("sharp_edge") or me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    sv = np.zeros(len(me.edges), bool)
    sharp.data.foreach_get("value", sv)
    le = np.empty(nl, np.int64)
    me.loops.foreach_get("edge_index", le)
    sv[le[ls]] = True
    sharp.data.foreach_set("value", sv)
    me.normals_split_custom_set(cn.tolist())
    return int(sel.sum())


def triangulate(objs):
    n = 0
    for o in objs:
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
        w, r = UB.fix_degenerates(o)
        if w or r:
            log("degenerates fixed", o.name, "welded", w, "rotated", r)
        lw = lone_wedges(o)
        if lw:
            COLLAPSED[o.name] = lw
            log("lone needle wedges collapsed", o.name, lw)
        n += 1
    log("triangulated", n, "objects")


def _hull(P):
    """2D convex hull (monotone chain), counter-clockwise."""
    P = np.unique(np.round(P, 9), axis=0)
    if len(P) < 3:
        return P
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def half(pts):
        h = []
        for p in pts:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) -
                                   (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(P[::-1])
    return np.array(lo[:-1] + up[:-1])


def min_rect_rotation(T):
    """2x2 rotation that turns an island (triangles (n, 3, 2)) to its minimum-area bounding rectangle (rotating
    calipers over the hull edges; a rotation, never a mirror). A slanted strip on a diagonal chart otherwise packs by
    its diagonal bounding box (the raster packer needs its whole window empty)."""
    H = _hull(T.reshape(-1, 2))
    if len(H) < 3:
        return np.eye(2)
    E = np.roll(H, -1, axis=0) - H
    ang = np.unique(np.mod(np.arctan2(E[:, 1], E[:, 0]), np.pi / 2.0))
    best, bR = None, np.eye(2)
    for a in ang:
        c, s_ = np.cos(-a), np.sin(-a)
        R = np.array([[c, -s_], [s_, c]])
        Q = H @ R.T
        ar = float(np.prod(Q.max(0) - Q.min(0)))
        if best is None or ar < best - 1e-9:
            best, bR = ar, R
    return bR


def pack_set(st, names, pms, isl):
    cfg = SS.SETS[st]
    need = 0.0
    for n in names:
        pm, r = pms[n], isl[n]
        for c in np.unique(r["cls"]):
            a = float(pm.farea[r["cls"] == c].sum())
            dmin = cfg["bands"][SS.CODE_CLASS[c]][0] / 10.0
            need += a * dmin * dmin
    size = next((S for S in cfg["sizes"] if need <= cfg["fill_min"] * S * S), cfg["sizes"][-1])
    info = {"size": size, "texels_needed_at_class_floors": round(need),
            "capacity_at_fill_min": {str(S): round(cfg["fill_min"] * S * S) for S in cfg["sizes"]}}
    ref = max(cfg["classes"].values())
    ids, tris, gmeta = [], [], {}
    for n in names:
        pm, r = pms[n], isl[n]
        lab = r["lab"]
        T, tf = pm.tris()
        for li in np.unique(lab):
            faces = np.nonzero(lab == li)[0]
            c = int(np.bincount(r["cls"][faces]).argmax())
            k = cfg["classes"][SS.CODE_CLASS[c]] / ref
            iid = int(r["base"] + li)
            ids.append(iid)
            Ti = r["luv"][T[lab[tf] == li]] * k
            Rm = min_rect_rotation(Ti)
            tris.append(Ti @ Rm.T)
            gmeta[iid] = {"part": n, "cls": SS.CODE_CLASS[c], "k": k, "R": Rm}
    cap = min(SS.DENSITY_CEIL * cfg["bands"][c][1] / (10.0 * cfg["classes"][c] / ref) for c in cfg["classes"])
    ext = [float(np.max(t.reshape(-1, 2).max(0) - t.reshape(-1, 2).min(0))) for t in tris]
    top = np.argsort(ext)[::-1][:6]
    info["longest_islands"] = [{"part": gmeta[ids[i]]["part"], "cls": gmeta[ids[i]]["cls"], "extent_units":
                                round(ext[i], 1), "triangles": int(len(tris[i]))} for i in top]
    log("longest", st, info["longest_islands"])
    import os
    if os.environ.get("SR01_UV_DUMP"):              # debug: the packer's input for offline tests
        np.savez_compressed(OUT / f"pack_in_{st}.npz", n=len(tris), **{f"t{i}": t for i, t in enumerate(tris)},
                            meta=json.dumps({"size": size, "gap": cfg["gap_px"][size], "cell": cfg["cell_px"][size],
                                             "cap": cap, "parts": [gmeta[i]["part"] for i in ids],
                                             "cls": [gmeta[i]["cls"] for i in ids]}))
    t0 = time.time()
    res = RPK.pack(tris, size, cfg["gap_px"][size], cfg["cell_px"][size], iters=10, scale_hi=cap, refine=40)
    log("pack", st, size, "islands", len(ids), "fill %.3f" % res["fill"], "%.1fs" % (time.time() - t0))
    info["scale_cap_px_per_unit"] = round(cap, 4)
    info["pack"] = {"packer": "gunlib.rasterpack", "scale_px_per_unit": res["scale"], "gap_px": res["gap_px"],
                    "cell_px": res["cell_px"], "packed_fill": round(res["fill"], 4)}
    info["islands"] = len(ids)
    # the island's rotation folded into its affine: uv = A' (luv x k) with A' = [A_lin R | A_t]
    aff = {}
    for iid, A in zip(ids, res["affine"]):
        Rm = gmeta[iid].pop("R")
        aff[iid] = (np.c_[A[:, :2] @ Rm, A[:, 2]], gmeta[iid]["k"])
    return info, aff, gmeta


def main():
    assert_lock()
    t0 = time.time()
    objs = [o for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"]
    triangulate(objs)
    parts = {o.name: o for o in objs}
    pms = {n: UB.part_mesh(o) for n, o in parts.items()}
    sets_of = {n: SS.SLOT_SET[part_rec(o)["slot"]] for n, o in parts.items()}
    vis = visibility(parts, pms)
    for n, o in parts.items():
        k_ = flatten_hidden(o, pms[n], vis[n])
        if k_:
            WEDGES[n] = k_
    log("hidden sliver / edge-on faces given flat normals", WEDGES)
    # ---------------------------------------------------------------- classes, then each set's size
    report = {"parts": {}, "sets": {}}
    cls_of = {}
    for n, pm in pms.items():
        PM = pm.fc + np.array(SS.GRIP_M)
        cls_of[n] = np.array([SS.CLASS_CODE[SS.face_class(n, sets_of[n], p, nn, v)]
                              for p, nn, v in zip(PM, pm.fn, vis[n])])
    # sliver faces (a corner under 1 deg: boolean run-outs, long fan triangles) take the class of the face across
    # their longest edge, so they join that face's island: a sliver alone in its UV / normal group at a needle corner
    # gets no MikkTSpace tangent in Unreal (UD3); inside its neighbour's island the group carries the neighbour's angle
    adopted, sliver_of = {}, {}
    for n, pm in pms.items():
        P3 = pm.V[pm.loop_v]
        ang = np.full(pm.nf, 180.0)
        Lmax = np.zeros(pm.nf)
        jmax = np.zeros(pm.nf, np.int64)
        for j in range(3):
            a_ = P3[pm.ps + (j + 1) % 3] - P3[pm.ps + j]
            b_ = P3[pm.ps + (j + 2) % 3] - P3[pm.ps + j]
            aj = np.degrees(np.arctan2(np.linalg.norm(np.cross(a_, b_), axis=1), np.einsum("ij,ij->i", a_, b_)))
            ang = np.minimum(ang, aj)
            Lj = np.linalg.norm(a_, axis=1)                       # edge j -> j+1
            upd = Lj > Lmax
            Lmax[upd], jmax[upd] = Lj[upd], j
        key, lf, la, lb = pm.edges()
        emap = {}
        for e, (k0, k1) in enumerate(map(tuple, key)):
            emap.setdefault((k0, k1), []).append(int(lf[e]))
        cnt = 0
        for f in np.nonzero(ang < 1.0)[0]:
            j = int(jmax[f])
            v0, v1 = int(pm.loop_v[pm.ps[f] + j]), int(pm.loop_v[pm.ps[f] + (j + 1) % 3])
            nb = [g for g in emap.get((min(v0, v1), max(v0, v1)), []) if g != f]
            if nb and cls_of[n][nb[0]] != cls_of[n][f]:
                cls_of[n][f] = cls_of[n][nb[0]]
                cnt += 1
        if cnt:
            adopted[n] = cnt
        sliver_of[n] = ang < 1.0
    report["sliver_class_adopted"] = adopted
    report["hidden_faces_flat_normals"] = WEDGES
    report["lone_needle_wedges_collapsed"] = COLLAPSED
    log("sliver faces adopting their neighbour's class", adopted)
    size_of = {}
    for st, cfg in SS.SETS.items():
        need = 0.0
        for n in pms:
            if sets_of[n] != st:
                continue
            for c in np.unique(cls_of[n]):
                dmin = cfg["bands"][SS.CODE_CLASS[c]][0] / 10.0
                need += float(pms[n].farea[cls_of[n] == c].sum()) * dmin * dmin
        size_of[st] = next((S for S in cfg["sizes"] if need <= cfg["fill_min"] * S * S), cfg["sizes"][-1])
    log("set sizes", size_of)
    # a SINGLE face longer than the atlas allows at its class (a triangulated full-length strip: the top rail's flank
    # and base strips are one triangle pair 303 mm long, one triangle's centre behind X 400 = class B) caps the whole
    # set's pack scale and no island split can help: such a face drops to the next class whose texels it fits
    # (reported; the faces seen at ADS -- tooth tops, slot edges -- are short and keep their class)
    # the scale each set needs for its fill minimum with a perfect pack (s_t = S sqrt(fill_min / sum(area k^2)), capped
    # at the density ceiling): islands are split, and single faces demoted, against what fits at THAT scale
    s_target = {}
    for st, cfg in SS.SETS.items():
        ref = max(cfg["classes"].values())
        cap = min(SS.DENSITY_CEIL * cfg["bands"][c][1] / (10.0 * cfg["classes"][c] / ref) for c in cfg["classes"])
        tot = sum(float(pms[n].farea[cls_of[n] == c].sum()) * (cfg["classes"][SS.CODE_CLASS[c]] / ref) ** 2
                  for n in pms if sets_of[n] == st for c in np.unique(cls_of[n]))
        S = size_of[st]
        s_target[st] = min(cap, 1.05 * S * np.sqrt(cfg["fill_min"] / max(tot, 1e-9)))
    log("target scales px/unit", {k: round(v, 3) for k, v in s_target.items()})
    demoted = {}
    for n, pm in pms.items():
        st = sets_of[n]
        cfg = SS.SETS[st]
        ref = max(cfg["classes"].values())
        lim = 0.97 * size_of[st] / s_target[st]
        P3 = pm.V[pm.loop_v]
        L = np.zeros(pm.nf)
        for j in range(3):
            a_ = P3[pm.ps + j]
            b_ = P3[pm.ps + (j + 1) % 3]
            L = np.maximum(L, np.linalg.norm(a_ - b_, axis=1))
        order = [c for c in "ABCDE" if c in cfg["classes"]]
        cls = cls_of[n]
        for f in np.nonzero(L > lim * 0.5)[0]:
            c = SS.CODE_CLASS[int(cls[f])]
            i = order.index(c)
            while i < len(order) - 1 and L[f] * cfg["classes"][order[i]] / ref > lim:
                i += 1
            if order[i] != c:
                demoted.setdefault(n, []).append([c, order[i], round(float(L[f]), 1), round(float(pm.farea[f]), 1)])
                cls[f] = SS.CLASS_CODE[order[i]]
    report["long_faces_demoted"] = {n: {"faces": len(v), "area_mm2": round(sum(x[3] for x in v), 1),
                                        "examples": v[:4]} for n, v in demoted.items()}
    log("long faces demoted", json.dumps(report["long_faces_demoted"])[:600])
    # ---------------------------------------------------------------- islands per part
    isl, gid = {}, 0
    for n, pm in pms.items():
        st = sets_of[n]
        cls = cls_of[n]
        fr = frame_for(n, pm)
        r = UC.make_islands(pm, fr, cls)
        n_slant = UP.reproject_slanted(pm, r, fr, cls, skip=sliver_of[n])
        cfg = SS.SETS[st]
        ref = max(cfg["classes"].values())
        cap = min(SS.DENSITY_CEIL * cfg["bands"][c][1] / (10.0 * cfg["classes"][c] / ref) for c in cfg["classes"])
        # (the AR-01 used the largest allowed size here; at the set's own size an island longer than the atlas caps
        # the pack scale -- the SMG's top rail did at 2048, fill 0.36)
        lim_units = LONG_FRAC * size_of[st] / s_target[st]

        P3 = pm.V[pm.loop_v]
        Lf = np.zeros(pm.nf)
        for j in range(3):
            Lf = np.maximum(Lf, np.linalg.norm(P3[pm.ps + j] - P3[pm.ps + (j + 1) % 3], axis=1))

        def limit_of(Fc, cls=cls, cfg=cfg, ref=ref, lim_units=lim_units, Lf=Lf):
            # (an island as long as its longest single face is never split: halving a full-length quad strip only
            # makes two equally long triangle islands with twice the bounding area)
            c = int(np.bincount(cls[Fc]).argmax())
            return max(lim_units / (cfg["classes"][SS.CODE_CLASS[c]] / ref), 1.02 * float(Lf[Fc].max()))
        r["lab"], n_long = UC.split_long(pm, r["lab"], r["luv"], limit_of)
        r["cls"], r["frame"], r["base"] = cls, fr, gid
        nl = int(r["lab"].max()) + 1
        gid += nl
        isl[n] = r
        report["parts"][n] = {"set": st, "faces": int(pm.nf), "islands": nl, "split_islands": int(r["n_split"]),
                              "rect_cuts": int(r["n_rect_cuts"]), "long_splits": int(n_long),
                              "slanted_faces_on_diagonal_charts": n_slant,
                              "absorbed_faces": int(r["absorbed_faces"]), "overlaps_left": int(r["overlaps_left"]),
                              "hidden_faces": int((~vis[n]).sum()),
                              "class_faces": {SS.CODE_CLASS[c]: int((cls == c).sum()) for c in np.unique(cls)}}
    log("islands", gid, "in %.1fs" % (time.time() - t0))
    # ---------------------------------------------------------------- per set: size, pack, write
    island_of_face = {n: isl[n]["base"] + isl[n]["lab"] for n in pms}
    aff_all, sizes = {}, {}
    for st in SS.SETS:
        names = [n for n in pms if sets_of[n] == st]
        if not names:
            continue
        info, aff, gmeta = pack_set(st, names, pms, isl)
        aff_all.update(aff)
        info["meta"] = gmeta
        sizes[st] = info
    stats = {st: {} for st in SS.SETS}
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
            d = stats[st].setdefault(SS.CODE_CLASS[c], {"area": [], "dens": [], "uv": 0.0, "parts": {}})
            d["area"].append(pm.farea[sel])
            d["dens"].append(dens[sel])
            d["uv"] += float(ua[sel].sum())
            d["parts"][n] = [float(np.median(dens[sel])), float(pm.farea[sel].sum()) / 100.0]
        o["uv_islands"] = json.dumps({"base": int(r["base"]), "n": int(r["lab"].max()) + 1})
    # ---------------------------------------------------------------- checks: overlaps per set (qa rules), mirrored
    def qa_overlaps(TT, st, eps=1e-5):
        t0_ = (TT + np.array([SS.TILE_OF_SET[st], 0.0])).astype(np.float32).astype(np.float64)
        return UC.overlap_pairs(t0_, eps, qa=True)
    lod0_overlaps, flipped = {}, 0
    umin, umax = np.array([9.0, 9.0]), np.array([-9.0, -9.0])
    for st in SS.SETS:
        Ts = []
        for n, o in parts.items():
            if sets_of[n] != st:
                continue
            pm = pms[n]
            uv = np.array([d.uv[:] for d in o.data.uv_layers["UV0"].data])
            T, tf = pm.tris()
            U = uv[T]
            Ts.append(U)
            sa = (U[:, 1, 0] - U[:, 0, 0]) * (U[:, 2, 1] - U[:, 0, 1]) - \
                (U[:, 2, 0] - U[:, 0, 0]) * (U[:, 1, 1] - U[:, 0, 1])
            flipped += int((sa < -1e-14).sum())
            umin, umax = np.minimum(umin, uv.min(0)), np.maximum(umax, uv.max(0))
        if Ts:
            lod0_overlaps[st] = int(len(qa_overlaps(np.vstack(Ts), st)))
    report["lod0_flipped_uv_triangles"] = flipped
    report["uv0_range"] = {"min": umin.round(5).tolist(), "max": umax.round(5).tolist()}
    report["lod0_uv0_overlap_pairs"] = lod0_overlaps
    # ---------------------------------------------------------------- report
    out_sets = {}
    for st, d in stats.items():
        if st not in sizes:
            continue
        cls_rep, tot_uv = {}, 0.0
        for c, v in d.items():
            a = np.concatenate(v["area"])
            de = np.concatenate(v["dens"])
            o = np.argsort(de)
            cw = np.cumsum(a[o]) / max(a.sum(), 1e-12)

            def q(p, de=de, o=o, cw=cw):
                return float(de[o][min(np.searchsorted(cw, p), len(o) - 1)])
            band = SS.SETS[st]["bands"][c]
            med = q(0.5)
            cls_rep[c] = {"area_cm2": round(float(a.sum()) / 100.0, 1), "px_per_cm_p5": round(q(0.05), 1),
                          "px_per_cm_median": round(med, 1), "px_per_cm_p95": round(q(0.95), 1), "band": band,
                          "floor_ok": med >= band[0],
                          "within_15pct_p5_median": bool(q(0.05) >= 0.85 * med),
                          "uniform_p5_p95_within_25pct": bool(q(0.05) >= 0.75 * med and q(0.95) <= 1.25 * med),
                          "over_band_top": round(med / band[1], 2),
                          "parts_median_px_cm_area_cm2": {k: [round(x, 1), round(y, 2)] for k, (x, y) in
                                                          v["parts"].items()}}
            tot_uv += v["uv"]
        out_sets[st] = dict(sizes[st], fill=round(tot_uv, 4), classes=cls_rep)
        out_sets[st].pop("meta", None)
    report["sets"] = out_sets
    report["visibility_configs"] = list(configs().keys()) + ["magazine_alone"]
    report["seconds"] = round(time.time() - t0, 1)
    (OUT / "uv_report.json").write_text(json.dumps(report, indent=1, default=float))
    np.savez_compressed(OUT / "islands.npz", **{f"{n}__cls": isl[n]["cls"] for n in isl},
                        **{f"{n}__vis": vis[n] for n in isl},
                        **{f"{n}__isl": island_of_face[n] for n in isl})
    # everything the W3 LOD transfer needs (the rifle_uv LOD step): per part keys, loop UVs (mm), labels, base; per
    # island the affine and class factor
    full = {}
    for n in isl:
        full[f"{n}__keys"] = isl[n]["keys"]
        full[f"{n}__luv"] = isl[n]["luv"]
        full[f"{n}__lab"] = isl[n]["lab"]
        full[f"{n}__base"] = np.array([isl[n]["base"]])
    ids = np.array(sorted(aff_all))
    full["aff_ids"] = ids
    full["aff_A"] = np.array([aff_all[i][0] for i in ids])
    full["aff_k"] = np.array([aff_all[i][1] for i in ids])
    np.savez_compressed(OUT / "islands_full.npz", **full)
    (OUT / "sets.json").write_text(json.dumps({st: {"size": v["size"], "slot": SS.SETS[st]["slot"],
                                                    "meta": {str(k): {"part": vv["part"], "cls": vv["cls"]}
                                                             for k, vv in v["meta"].items()}}
                                               for st, v in sizes.items()}, indent=0))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log("sets", json.dumps({k: {"size": v["size"], "fill": v["fill"]} for k, v in out_sets.items()}))
    log("UV_DONE %.1fs" % (time.time() - t0))


main()
