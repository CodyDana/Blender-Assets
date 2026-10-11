"""SMG01 W3a: LOD1-3 into the asset blend, surfaced (headless Blender, after build_smg.py --stage lod 1..3):

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_lods.py

1. brings collections SMG01_LOD1..3 in from scratch/SMG01_LOD<k>.blend (replacing any earlier copy);
2. triangulates every LOD part as the LOD0 parts were (smg_uv: loop triangles, bmesh fallback, gunlib.uvbl
   fix_degenerates, lone needle wedges collapsed);
3. UV0 (the rifle_uv LOD step on the W2 islands, scratch/uv/islands_full.npz): every LOD face takes the island of its
   best-matching LOD0 face (same part; LOD3: same set) and each corner the island's chart projection (pulled onto the
   island's footprint), or the closest island point's UV when the face projects off it; overlapping LOD triangles per
   (LOD, set) collapse the smaller one to its centre (qa_check ignores zero-area UVs). The LOD0 maps stay valid;
4. visibility per LOD face = that of its assigned LOD0 face (W2 islands.npz) -> hidden sliver / edge-on faces get flat
   normals (smg_uv.flatten_hidden's rule; no geometry move);
5. UV1 per LOD (smg_uv1lib.author: the W2 lightmap method on that LOD's parts, gun + magazine) and UD4 at 64 / 128 px;
6. UD1-UD3 on every LOD part.
Writes scratch/uv/lod_uv_report.json, scratch/uv/lod_vis.npz, scratch/uv/uv1_lod<k>.npz; saves the blend.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SCRATCH, BLEND, PARTS_COLL, CODE  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import smg_surface as SS  # noqa: E402
import smg_uv1lib as U1  # noqa: E402
import smg_ud4 as UD4  # noqa: E402
from gunlib import uvchart as UC  # noqa: E402
from gunlib import uvbl as UB  # noqa: E402
from gunlib import ud as UD  # noqa: E402
from gunlib import tspace as TS  # noqa: E402

OUT = SCRATCH / "uv"
LODS = (1, 2, 3)
import os  # noqa: E402
DIAG = bool(os.environ.get("SMG_LODS_DIAG"))
DIAG_ROWS = {}
SNAP_ALL = bool(os.environ.get("SMG_LODS_SNAP"))


def log(*a):
    print("[SMG01-lods]", *a, flush=True)


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def bring_lods():
    for lv in LODS:
        name = f"{CODE}_LOD{lv}"
        old = bpy.data.collections.get(name)
        if old is not None:
            for o in list(old.objects):
                d = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                if d is not None and d.users == 0:
                    bpy.data.meshes.remove(d)
            bpy.data.collections.remove(old)
        with bpy.data.libraries.load(str(SCRATCH / f"{CODE}_LOD{lv}.blend"), link=False) as (df, dt):
            dt.collections = [c for c in df.collections if c == name]
        col = dt.collections[0]
        bpy.context.scene.collection.children.link(col)
        col.hide_render = True
        for o in col.objects:
            o.hide_render = True
    log("LOD collections in:", [c.name for c in bpy.data.collections if c.name.startswith(f"{CODE}_LOD")])


# ---------------------------------------------------------------------------------- triangulation (smg_uv's rules)
def lone_wedges(ob, max_deg=0.1, short_mm=0.3, max_turn_deg=20.0):
    """smg_uv.lone_wedges (W2 UD3 rule), verbatim: a needle wedge alone in its tangent group loses its short edge."""
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
            continue
        nbB = {e.other_vert(Bv) for e in Bv.link_edges}
        nbC = {e.other_vert(Cv) for e in Cv.link_edges}
        if len(nbB & nbC) != 2:
            continue
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


def flip_slivers(ob, max_deg=0.5, coplanar_deg=0.5):
    """UD3 at the coarse LODs: a sliver triangle (a corner < max_deg: the coarse outlines' long fan triangles) whose
    longest edge it shares with a COPLANAR neighbour (dihedral < coplanar_deg) has that edge flipped when both new
    triangles' smallest corner beats the old smallest corner (a Delaunay flip on a flat region: the surface, its
    outline and its normals do not change). Each new corner keeps its vertex's corner normal from the old pair."""
    import bmesh
    import math as _m
    me = ob.data
    cn = np.empty(len(me.loops) * 3)
    me.corner_normals.foreach_get("vector", cn)
    cn = cn.reshape(-1, 3)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    nidx = bm.loops.layers.int.new("_cn_src")
    for f in bm.faces:
        for l in f.loops:
            l[nidx] = l.index
    def min_ang(P):
        out = 180.0
        for i in range(3):
            a, b = P[(i + 1) % 3] - P[i], P[(i + 2) % 3] - P[i]
            if a.length == 0 or b.length == 0:
                return 0.0
            out = min(out, _m.degrees(a.angle(b)))
        return out
    flipped = 0
    for f in list(bm.faces):
        if not f.is_valid or len(f.verts) != 3:
            continue
        P = [v.co for v in f.verts]
        a0 = min_ang(P)
        if a0 >= max_deg:
            continue
        e = max(f.edges, key=lambda e: e.calc_length())
        if len(e.link_faces) != 2:
            continue
        g = e.link_faces[0] if e.link_faces[1] is f else e.link_faces[1]
        if len(g.verts) != 3 or _m.degrees(f.normal.angle(g.normal, 0.0)) >= coplanar_deg:
            continue
        a1 = min(a0, min_ang([v.co for v in g.verts]))
        u, v = e.verts
        p = next(x for x in f.verts if x not in (u, v))
        q = next(x for x in g.verts if x not in (u, v))
        if bm.edges.get((p, q)) is not None:
            continue
        n1 = min_ang([p.co, q.co, u.co])
        n2 = min_ang([p.co, q.co, v.co])
        if min(n1, n2) <= a1 + 1e-6:
            continue
        src = {}
        for ff in (f, g):
            for l in ff.loops:
                src.setdefault(l.vert, l[nidx])
        r = bmesh.ops.rotate_edges(bm, edges=[e], use_ccw=False)
        for ne in r.get("edges", []):
            for ff in ne.link_faces:
                for l in ff.loops:
                    if l.vert in src:
                        l[nidx] = src[l.vert]
        flipped += 1
    if flipped:
        src_of = {}
        bm.faces.ensure_lookup_table()
        bm.to_mesh(me)
        lay = me.attributes.get("_cn_src")
        idx = np.empty(len(me.loops), np.int64)
        lay.data.foreach_get("value", idx)
        me.attributes.remove(lay)
        me.normals_split_custom_set(cn[idx].tolist())
        me.update()
    else:
        pass
    bm.free()
    if not flipped and me.attributes.get("_cn_src") is not None:
        me.attributes.remove(me.attributes.get("_cn_src"))
    return flipped


def triangulate(objs, rep):
    for o in objs:
        keep = o.data.copy()
        UB.triangulate_as_looptris(o)
        if UB.nonmanifold_edges(o) > UB.nonmanifold_edges_of(keep):
            bad = o.data
            o.data = keep
            bpy.data.meshes.remove(bad)
            UB.triangulate_keep_normals(o)
            rep.setdefault("bmesh_split", []).append(o.name)
        else:
            bpy.data.meshes.remove(keep)
        w, r = UB.fix_degenerates(o)
        if w or r:
            rep.setdefault("degenerates_fixed", {})[o.name] = [int(w), int(r)]
        # (LODs: apex < 0.25 deg, neighbours turn <= 20 deg; LOD0 used 0.1) moves <= 0.15 mm, seen from >= 2.4 m
        lw = lone_wedges(o, max_deg=0.25, max_turn_deg=20.0)
        if lw:
            rep.setdefault("lone_wedges_collapsed", {})[o.name] = lw
        nf = flip_slivers(o)
        if nf:
            rep.setdefault("sliver_edges_flipped", {})[o.name] = nf


def flatten_hidden(ob, pm, vis, max_deg=1.0, edge_on_dot=0.5):
    """smg_uv.flatten_hidden (W2 UD3 rule), verbatim: hidden sliver / edge-on faces get flat corner normals."""
    me = ob.data
    nl = len(me.loops)
    cn = np.empty(nl * 3, np.float32)
    me.corner_normals.foreach_get("vector", cn)
    cn = cn.reshape(-1, 3).astype(np.float64)
    fn = pm.fn
    P3 = pm.V[pm.loop_v]
    ang = np.full(pm.nf, 180.0)
    amin = np.zeros(pm.nf, np.int64)
    best = np.full(pm.nf, 180.0)
    for j in range(3):
        a_ = P3[pm.ps + (j + 1) % 3] - P3[pm.ps + j]
        b_ = P3[pm.ps + (j + 2) % 3] - P3[pm.ps + j]
        aj = np.degrees(np.arctan2(np.linalg.norm(np.cross(a_, b_), axis=1), np.einsum("ij,ij->i", a_, b_)))
        ang = np.minimum(ang, aj)
        upd = aj < best
        best[upd], amin[upd] = aj[upd], j
    dmin = np.min(np.abs(np.einsum("ij,ij->i", cn, fn[pm.loop_f])).reshape(-1, 3), axis=1)
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


def qa_overlaps(TT, st, eps=1e-5):
    """UV0 overlaps as qa_check reads them on the twin (float32, the set's U tile)."""
    t0 = (TT + np.array([SS.TILE_OF_SET[st], 0.0])).astype(np.float32).astype(np.float64)
    return UC.overlap_pairs(t0, eps, qa=True)


def ud3(me):
    c = TS.collapsed(me, "UV0", unreal=False)
    z = TS.float32_zero_corners(me, "UV0")
    e = TS.edge_on_corners(me, "UV0")
    return {"collapsed": int(len(c)), "float32_zero_corners": int(len(z)), "edge_on_corners": int(len(e))}


# ---------------------------------------------------------------------------------- UV0 overlap clearing (W3)
QA_EPS = 1e-5
UV_MIN_EDGE = 5.0e-5           # a UV triangle's longest edge never below this (float32 UVs on the twin's tiles
                               # 1..2 / -1..0 resolve 1.2e-7: a smaller triangle's tangent frame degrades)
UV_MIN_HEIGHT = 4.0e-6         # ... and its height over its longest edge never below this (32 ulps on the tiles)
ZERO_COPY_EDGE = 1.2e-4        # a zero-area UV face becomes a copy of its 3D shape this long (0.5 texel at 4096)


def _area2(T):
    return (T[..., 1, 0] - T[..., 0, 0]) * (T[..., 2, 1] - T[..., 0, 1]) - \
        (T[..., 2, 0] - T[..., 0, 0]) * (T[..., 1, 1] - T[..., 0, 1])


def _sat_one(t, C, eps=QA_EPS):
    """Bool per triangle of C (n, 3, 2): overlaps triangle t (3, 2) under qa_check.uv_overlap_sat's rules (touching =
    apart; degenerate C ignored)."""
    if not len(C):
        return np.zeros(0, bool)
    keep = np.abs(_area2(C)) > 1e-12
    lo, hi = t.min(0), t.max(0)
    cmin, cmax = C.min(1), C.max(1)
    sep = np.any(hi <= cmin + eps, axis=1) | np.any(cmax <= lo + eps, axis=1)
    for k in range(3):                                   # the axes of t
        e = t[(k + 1) % 3] - t[k]
        ax = np.array([-e[1], e[0]])
        n = np.linalg.norm(ax)
        if n == 0:
            continue
        ax = ax / n
        pa = t @ ax
        pb = C @ ax
        sep |= (pa.max() <= pb.min(1) + eps) | (pb.max(1) <= pa.min() + eps)
    for k in range(3):                                   # the axes of every C
        e = C[:, (k + 1) % 3] - C[:, k]
        ax = np.stack([-e[:, 1], e[:, 0]], axis=-1)
        n = np.linalg.norm(ax, axis=1, keepdims=True)
        ax = ax / np.where(n == 0, 1.0, n)
        pa = ax @ t.T                                    # (n, 3)
        pb = np.einsum("pij,pj->pi", C, ax)
        sep |= (pa.max(1) <= pb.min(1) + eps) | (pb.max(1) <= pa.min(1) + eps)
    return keep & ~sep


def _shape_copy(P3, edge, sign):
    """A 2D copy of a 3D triangle (its own plane), longest edge = edge, UV winding sign (+1 / -1), centred on 0."""
    a, b, c = P3
    L = [np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)]
    k = int(np.argmax(L))
    p0, p1, p2 = (a, b, c) if k == 0 else ((b, c, a) if k == 1 else (c, a, b))
    u = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-12)
    w = np.cross(u, np.cross(p2 - p0, u))
    w = w / max(np.linalg.norm(w), 1e-12)
    Q = np.array([[0.0, 0.0], [np.linalg.norm(p1 - p0), 0.0],
                  [(p2 - p0) @ u, max((p2 - p0) @ w, 0.4 * L[k])]])
    Q *= edge / max(Q[1, 0], 1e-12)
    Q -= Q.mean(0)
    order = [0, 1, 2] if k == 0 else ([2, 0, 1] if k == 1 else [1, 2, 0])
    R = Q[order]
    if np.sign(_area2(R[None])[0]) != sign:
        R = R[[0, 2, 1]]
    return R


def clear_set(ent, st, island_of_face, pms, uv0_of):
    """Every UV0 triangle of one (LOD, set) made overlap-free under qa_check's rules with a positive area: (1) a
    zero-area face becomes a 0.25-texel copy of its 3D shape at its UV centroid; (2) each face of an overlapping pair
    (the smaller one) shrinks about its centroid (halvings while its longest edge stays >= UV_MIN_EDGE) and, if still
    covered, moves (the shrunken copy) outward in growing steps to the first clear spot whose centre lies on its own
    LOD0 island (so it keeps sampling the texels painted for its surface)."""
    rec = {"zero_area_copies": 0, "shrunk": 0, "moved": 0, "unresolved": 0}
    T_all, refs, loops_of = [], [], []
    for on, m in ent:
        pm = m["pm"]
        T, tf = pm.tris()
        T_all.append(m["uv01"][T])
        refs += [(on, int(f)) for f in tf]
        loops_of += [(m, int(pm.ps[f]), int(pm.pt[f])) for f in tf]
    TT = np.vstack(T_all)
    a2 = _area2(TT)
    sgn = 1.0 if (a2 > 0).sum() >= (a2 < 0).sum() else -1.0
    A3 = np.concatenate([m["pm"].farea for on, m in ent])        # 3D face areas (mm2), triangle order
    rho = np.abs(a2) / np.maximum(A3, 1e-9)
    rho_med = float(np.median(rho[rho > 0])) if (rho > 0).any() else 1.0

    def stretched(i):
        """A LOD face whose UV is > 4 x the set's median density: its corners snapped onto far-apart island points
        (a coarse face across several LOD0 islands), so its UV triangle spans other islands: IT gets fixed."""
        return abs(_area2(TT[i][None])[0]) / max(A3[i], 1e-9) > 4.0 * rho_med

    def put(i, tri):
        mm, s0, n0 = loops_of[i]
        mm["uv01"][s0:s0 + n0] = tri
        TT[i] = tri
    # (2) a UV triangle that is a point or a line, also in float32 on the twin's tiles (u + 1 / u - 1 resolve 1.2e-7):
    # its height over its longest edge under UV_MIN_HEIGHT
    Lmax = np.max(np.linalg.norm(TT - np.roll(TT, 1, axis=1), axis=2), axis=1)
    degen = (np.abs(a2) <= 1e-12) | (np.abs(a2) / np.maximum(Lmax, 1e-12) < UV_MIN_HEIGHT)
    for i in np.nonzero(degen)[0]:
        mm, s0, n0 = loops_of[i]
        P3 = mm["pm"].V[mm["pm"].loop_v[s0:s0 + n0]]
        tri = TT[i].mean(0) + _shape_copy(P3, ZERO_COPY_EDGE, sgn)
        tri = tri + np.clip(tri.min(0), 1e-4, None) - tri.min(0)          # kept inside 0..1
        tri = tri - np.clip(tri.max(0) - (1.0 - 1e-4), 0.0, None)
        put(i, tri)
        rec["zero_area_copies"] += 1
    isl_tris = {}

    def on_island(i, c):
        on, f = refs[i]
        mm = loops_of[i][0]
        tp, g0 = mm["part"][f], int(mm["face"][f])
        iid = int(island_of_face[tp][g0])
        if iid not in isl_tris:
            pm0 = pms[tp]
            fs = np.nonzero(island_of_face[tp] == iid)[0]
            isl_tris[iid] = uv0_of[tp][np.array([np.arange(pm0.ps[x], pm0.ps[x] + 3) for x in fs])]
        U = isl_tris[iid]
        cc = np.broadcast_to(c, U[:, 0].shape)
        d1 = _area2(np.stack([cc, U[:, 0], U[:, 1]], 1))
        d2 = _area2(np.stack([cc, U[:, 1], U[:, 2]], 1))
        d3 = _area2(np.stack([cc, U[:, 2], U[:, 0]], 1))
        return bool(np.any(((d1 >= 0) & (d2 >= 0) & (d3 >= 0)) | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))))

    def covered(i, tri):
        lo, hi = tri.min(0) - 1e-3, tri.max(0) + 1e-3
        cmin, cmax = TT.min(1), TT.max(1)
        near = np.nonzero(np.all(cmax >= lo, axis=1) & np.all(cmin <= hi, axis=1))[0]
        near = near[near != i]
        return bool(_sat_one(tri, TT[near]).any())

    done = set()
    for _ in range(40):
        pr = qa_overlaps(TT, st, 0.5e-5)
        if not len(pr):
            break
        ar = np.abs(_area2(TT))
        todo = []
        for a, b in pr:
            a, b = int(a), int(b)
            if a in done and b in done:
                continue
            sa, sb = stretched(a), stretched(b)
            if sa != sb and not (a in done if sa else b in done):
                todo.append(a if sa else b)
            else:
                todo.append(b if (a in done or (b not in done and ar[b] < ar[a])) else a)
        if not todo:
            break
        for i in dict.fromkeys(todo):
            if not covered(i, TT[i]):
                continue
            tri = TT[i].copy()
            c = tri.mean(0)
            while covered(i, tri):
                L = float(np.max(np.linalg.norm(tri - np.roll(tri, 1, 0), axis=1)))
                if L * 0.5 < UV_MIN_EDGE:
                    break
                tri = c + 0.5 * (tri - c)
            if not covered(i, tri):
                put(i, tri)
                rec["shrunk"] += 1
                done.add(i)
                continue
            L = float(np.max(np.linalg.norm(tri - np.roll(tri, 1, 0), axis=1)))
            placed = False
            for need_island, radii in ((True, (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256)),
                                       (False, (1, 2, 3, 4, 6, 8, 12, 16, 24, 32))):
                for r in radii:
                    for ang in np.radians(np.arange(0, 360, 15)):
                        c2 = c + r * L * np.array([np.cos(ang), np.sin(ang)])
                        t2 = tri - c + c2
                        if t2.min() < 1e-4 or t2.max() > 1.0 - 1e-4:
                            continue
                        if (not need_island or on_island(i, c2)) and not covered(i, t2):
                            put(i, t2)
                            placed = True
                            break
                    if placed:
                        break
                if placed:
                    rec["moved" if need_island else "moved_next_to_island"] = \
                        rec.get("moved" if need_island else "moved_next_to_island", 0) + 1
                    break
            if not placed:
                rec["unresolved"] += 1
                lo_, hi_ = tri.min(0) - 1e-3, tri.max(0) + 1e-3
                cmin, cmax = TT.min(1), TT.max(1)
                near = np.nonzero(np.all(cmax >= lo_, axis=1) & np.all(cmin <= hi_, axis=1))[0]
                near = near[near != i]
                hit = near[_sat_one(tri, TT[near])]
                rec.setdefault("unresolved_faces", []).append(
                    {"face": refs[i], "L": L, "uv": np.round(tri, 7).tolist(),
                     "covered_by": [[refs[h][0], refs[h][1], float(abs(_area2(TT[h][None])[0]))] for h in hit[:4]],
                     "on_island_at_centre": on_island(i, c)})
            done.add(i)
    # last resort for a pair left (both handled once): the stretched one, else the larger, shrinks about its centroid
    for _ in range(20):
        pr = qa_overlaps(TT, st, 0.5e-5)
        if not len(pr):
            break
        ar = np.abs(_area2(TT))
        for a, b in pr:
            a, b = int(a), int(b)
            sa, sb = stretched(a), stretched(b)
            i = (a if sa else b) if sa != sb else (a if ar[a] >= ar[b] else b)
            tri = TT[i].copy()
            c = tri.mean(0)
            while covered(i, tri):
                L = float(np.max(np.linalg.norm(tri - np.roll(tri, 1, 0), axis=1)))
                if L * 0.5 < UV_MIN_EDGE:
                    break
                tri = c + 0.5 * (tri - c)
            put(i, tri)
            rec["last_resort_shrunk"] = rec.get("last_resort_shrunk", 0) + 1
    return rec


def main():
    from pipeline import lock as L
    L.assert_owner(CODE, "claude")
    t0 = time.time()
    rep = {"stage": "W3a LODs: triangulation, UV0 transfer, visibility, UV1, UD"}
    bring_lods()
    lod_objs = {}
    for lv in LODS:
        objs = [o for o in bpy.data.collections[f"{CODE}_LOD{lv}"].objects if o.type == "MESH"]
        tri = {}
        triangulate(objs, tri)
        rep[f"triangulate_LOD{lv}"] = tri
        for o in objs:
            lod_objs[o.name] = (lv, o)
    log("triangulated", len(lod_objs), "LOD objects")
    # ---------------------------------------------------------------- the LOD0 islands (W2)
    parts = {o.name: o for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"}
    pms = {n: UB.part_mesh(o) for n, o in parts.items()}
    full = np.load(OUT / "islands_full.npz")
    isl0 = np.load(OUT / "islands.npz")
    aff = {int(i): (A, float(k)) for i, A, k in zip(full["aff_ids"], full["aff_A"], full["aff_k"])}
    isl = {}
    for n, pm in pms.items():
        r = {"keys": full[f"{n}__keys"], "luv": full[f"{n}__luv"], "lab": full[f"{n}__lab"],
             "base": int(full[f"{n}__base"][0]), "frame": U1.frame_for(n, pm)}
        assert len(r["lab"]) == pm.nf and len(r["luv"]) == len(pm.loop_v), f"{n}: islands do not match the mesh"
        isl[n] = r
    vis0 = {n: isl0[f"{n}__vis"].astype(bool) for n in pms}
    sets_of = {n: SS.SLOT_SET[part_rec(o)["slot"]] for n, o in parts.items()}
    island_of_face = {n: isl[n]["base"] + isl[n]["lab"] for n in pms}
    uv0_of = {n: np.array([d.uv[:] for d in parts[n].data.uv_layers["UV0"].data]) for n in parts}
    # ---------------------------------------------------------------- assignment
    idx_part = {n: UB.FaceIndex([pms[n]]) for n in pms}
    idx_set = {}
    for st in SS.SETS:
        names = [n for n in pms if sets_of[n] == st]
        idx_set[st] = (names, UB.FaceIndex([pms[n] for n in names]))
    lod_map = {}
    for on, (lv, o) in lod_objs.items():
        base = on[: -len(f"_LOD{lv}")]
        pm = UB.part_mesh(o)
        tp = np.empty(pm.nf, object)
        tf = np.zeros(pm.nf, np.int64)
        dist = np.zeros(pm.nf)
        if lv < 3 and base in pms:
            ix = idx_part[base]
            for f in range(pm.nf):
                _, g, d = ix.best(pm.fc[f], pm.fn[f])
                tp[f], tf[f], dist[f] = base, g, d
            st = sets_of[base]
        else:
            st = SS.SLOT_SET[part_rec(o)["slot"]]
            names, ix = idx_set[st]
            for f in range(pm.nf):
                mk, g, d = ix.best(pm.fc[f], pm.fn[f])
                tp[f], tf[f], dist[f] = names[mk], g, d
        lod_map[on] = {"lv": lv, "pm": pm, "part": tp, "face": tf, "set": st, "ob": o,
                       "dist_p95": float(np.percentile(dist, 95)) if len(dist) else 0.0}
    log("LOD faces assigned in %.1fs" % (time.time() - t0))
    # ---------------------------------------------------------------- UV0 (the rifle_uv LOD step)
    snaps, foot = {}, {}
    n_proj = n_snap = n_off = 0
    off_by_lod = {k: 0 for k in LODS}
    faces_by_lod = {k: 0 for k in LODS}
    snap_dev = []
    for on, m in lod_map.items():
        pm = m["pm"]
        faces_by_lod[m["lv"]] += pm.nf
        uv = np.zeros((len(pm.loop_v), 2))
        for f in range(pm.nf):
            tpn, g0 = m["part"][f], int(m["face"][f])
            r = isl[tpn]
            iid = int(island_of_face[tpn][g0])
            if iid not in snaps:
                faces_i = np.nonzero(island_of_face[tpn] == iid)[0]
                snaps[iid] = UB.IslandSnap(pms[tpn], faces_i, uv0_of[tpn])
                foot[iid] = UB.footprint_tree(pms[tpn], faces_i, r["luv"])
            key = int(r["keys"][g0])
            s0 = pms[tpn].ps[g0]
            th = UC.unwrapped_theta(r["frame"], key, r["luv"][s0:s0 + 3])
            s, t = pm.ps[f], pm.pt[f]
            P = pm.V[pm.loop_v[s:s + t]]
            puv = UC.project_loops(P, np.full(t, key), r["frame"], np.full(t, th))
            A, k = aff[iid]
            cen = puv.mean(0)
            if not SNAP_ALL and UB.inside(foot[iid], cen):
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
                uc, dd = snaps[iid].uv_at(pm.fc[f])
                for jj in range(t):
                    uv[s + jj], _ = snaps[iid].uv_near(P[jj], uc)
                snap_dev.append(dd)
                n_off += 1
                off_by_lod[m["lv"]] += 1
        m["uv01"] = uv
    rep["lod_corners"] = {"projected": n_proj, "pulled_in": n_snap, "faces_off_island_snapped": n_off,
                          "off_island_by_lod": {f"LOD{k}": [v, faces_by_lod[k]] for k, v in off_by_lod.items()}}
    if snap_dev:
        rep["lod_snap_distance_mm"] = {q: round(float(np.percentile(snap_dev, p)), 3) for q, p in
                                       (("p50", 50), ("p95", 95))}
        rep["lod_snap_distance_mm"]["max"] = round(float(np.max(snap_dev)), 3)
    # overlaps (qa_check uv_no_overlap on the twin reads each set on its tile): (a) per object, gunlib.lodfix relaxes
    # fold-overs and separates overlapping corners (welded loops move together); (b) any pair left: the smaller
    # triangle SHRINKS about its own centroid (its corners unwelded, halving its size up to 10 times) until it is clear.
    # Nothing collapses to a point or a line: a zero-area UV triangle gets no MikkTSpace frame in Unreal (UD3)
    from gunlib import lodfix
    fixes = {}
    for on, m in lod_map.items():
        UB.write_uv(m["ob"], "UV0", m["uv01"], first=True)
        a = lodfix.relax_uv_foldovers(m["ob"])
        b = lodfix.fix_uv_overlaps(m["ob"], rounds=60)
        if a["flipped_before"] or b["overlaps_before"]:
            fixes[on] = {**a, **b}
        m["uv01"] = np.array([d.uv[:] for d in m["ob"].data.uv_layers["UV0"].data], float)
    rep["lodfix_per_object"] = fixes
    shrunk, overlaps = {}, {}
    for lv in LODS:
        for st in SS.SETS:
            ent = [(on, m) for on, m in lod_map.items() if m["lv"] == lv and m["set"] == st]
            if ent:
                shrunk[f"LOD{lv}/{st}"] = clear_set(ent, st, island_of_face, pms, uv0_of)
                Ts = [m["uv01"][m["pm"].tris()[0]] for on, m in ent]
                overlaps[f"LOD{lv}/{st}"] = int(len(qa_overlaps(np.vstack(Ts), st, 1e-5)))
    if DIAG:
        (OUT / "lod_overlap_diag.json").write_text(json.dumps(DIAG_ROWS))
        log("DIAG written", overlaps, shrunk)
        return
    for on, m in lod_map.items():
        UB.write_uv(m["ob"], "UV0", m["uv01"], first=True)
    rep["lod_overlap_shrunk_faces"] = shrunk
    collapsed = shrunk
    rep["lod_uv0_overlap_pairs"] = overlaps
    umin = np.min([m["uv01"].min(0) for m in lod_map.values()], axis=0)
    umax = np.max([m["uv01"].max(0) for m in lod_map.values()], axis=0)
    rep["uv0_range_lods"] = {"min": umin.round(5).tolist(), "max": umax.round(5).tolist()}
    rep["lod_assign_dist_p95_mm"] = {on: round(m["dist_p95"], 3) for on, m in lod_map.items()}
    log("UV0 written; overlaps", overlaps, "shrunk", shrunk)
    # ---------------------------------------------------------------- visibility, hidden-face normals
    vis = {}
    flat = {}
    for on, m in lod_map.items():
        v = np.array([vis0[p][int(f)] for p, f in zip(m["part"], m["face"])], bool)
        vis[on] = v
        k_ = flatten_hidden(m["ob"], m["pm"], v)
        if k_:
            flat[on] = k_
    rep["hidden_faces_flat_normals"] = flat
    # UD3 (float32 MikkTSpace): a sliver whose corners still get no angle weight (a visible 0.25 mm bevel run-out at
    # LOD1) takes flat normals on its three corners (smg_uv.flatten_hidden's move, for visible slivers: sub-pixel at
    # the LOD's distance; no geometry move)
    f32 = {}
    for on, m in lod_map.items():
        me = m["ob"].data
        z = TS.float32_zero_corners(me, "UV0")
        if not len(z):
            continue
        pm = UB.part_mesh(m["ob"])
        faces = np.unique(pm.loop_f[z])
        P3 = pm.V[pm.loop_v]
        ang = np.full(pm.nf, 180.0)
        for j in range(3):
            a_ = P3[pm.ps + (j + 1) % 3] - P3[pm.ps + j]
            b_ = P3[pm.ps + (j + 2) % 3] - P3[pm.ps + j]
            ang = np.minimum(ang, np.degrees(np.arctan2(np.linalg.norm(np.cross(a_, b_), axis=1),
                                                        np.einsum("ij,ij->i", a_, b_))))
        faces = faces[ang[faces] < 1.0]
        if not len(faces):
            continue
        hv = np.ones(pm.nf, bool)
        hv[faces] = False                      # flatten_hidden flattens the faces marked not-visible that qualify
        k_ = flatten_hidden(m["ob"], pm, hv, max_deg=1.0, edge_on_dot=1.01)
        f32[on] = {"faces": faces.tolist(), "flattened": k_}
        # a corner still flagged (its true in-plane angle is under the float32 limit itself): its normal tilts toward
        # its two edges' mean direction until the projected corner angle reaches 0.15 deg (that one corner of a
        # sub-pixel sliver; nothing else moves)
        z = TS.float32_zero_corners(me, "UV0")
        if len(z):
            cn = np.empty(len(me.loops) * 3)
            me.corner_normals.foreach_get("vector", cn)
            cn = cn.reshape(-1, 3)
            tilts = []
            for li in z:
                f = int(pm.loop_f[li])
                s0 = pm.ps[f]
                j = int(li - s0)
                P = pm.V[pm.loop_v[s0 + j]]
                e1 = pm.V[pm.loop_v[s0 + (j + 1) % 3]] - P
                e2 = pm.V[pm.loop_v[s0 + (j + 2) % 3]] - P
                d = e1 / np.linalg.norm(e1) + e2 / np.linalg.norm(e2)
                d /= max(np.linalg.norm(d), 1e-12)
                n0 = cn[li] / np.linalg.norm(cn[li])
                for tdeg in range(5, 86, 5):
                    t = np.radians(tdeg)
                    n1 = np.cos(t) * n0 + np.sin(t) * d
                    n1 /= np.linalg.norm(n1)
                    a1 = e1 - n1 * (e1 @ n1)
                    a2 = e2 - n1 * (e2 @ n1)
                    ang = np.degrees(np.arctan2(np.linalg.norm(np.cross(a1, a2)), a1 @ a2))
                    if ang >= 0.15:
                        cn[li] = n1
                        tilts.append(tdeg)
                        break
            me.normals_split_custom_set(cn.tolist())
            f32[on]["corner_tilts_deg"] = tilts
    # an edge-on corner group (its every face seen edge-on by the corner normal: a narrow side face carrying its
    # neighbour's shading normal; tspace fix C): the flagged corners tilt toward their own face normal until
    # |n . n_face| >= 0.15 (one corner of a narrow face; nothing else moves)
    for on, m in lod_map.items():
        me = m["ob"].data
        e = TS.edge_on_corners(me, "UV0")
        if not len(e):
            continue
        pm = UB.part_mesh(m["ob"])
        cn = np.empty(len(me.loops) * 3)
        me.corner_normals.foreach_get("vector", cn)
        cn = cn.reshape(-1, 3)
        tilts = []
        for li in e:
            fn = pm.fn[int(pm.loop_f[li])]
            n0 = cn[li] / np.linalg.norm(cn[li])
            for tdeg in range(2, 61, 2):
                t = np.radians(tdeg)
                side = fn - n0 * (fn @ n0)
                side = side / max(np.linalg.norm(side), 1e-12)
                n1 = np.cos(t) * n0 + np.sin(t) * side
                if abs(n1 @ fn) >= 0.15:
                    cn[li] = n1
                    tilts.append(tdeg)
                    break
        me.normals_split_custom_set(cn.tolist())
        f32.setdefault(on, {})["edge_on_tilts_deg"] = tilts
    rep["float32_sliver_flat_normals"] = f32
    np.savez_compressed(OUT / "lod_vis.npz", **{on: v for on, v in vis.items()})
    # ---------------------------------------------------------------- UV1 per LOD + UD4
    rep["uv1"], rep["ud4"] = {}, {}
    for lv in LODS:
        objs = {on: m["ob"] for on, m in lod_map.items() if m["lv"] == lv}
        r1, T1, C1 = U1.author(objs, {on: vis[on] for on in objs})
        np.savez_compressed(OUT / f"uv1_lod{lv}.npz", tris=T1, chart=C1)
        rows = [UD4.measure(T1.astype(np.float64), C1, R, 2) for R in (64, 128)]
        rep["uv1"][f"LOD{lv}"] = r1
        rep["ud4"][f"LOD{lv}"] = {"rows": rows, "pass": all(r["pass"] for r in rows)}
        log("UV1 LOD%d" % lv, json.dumps({k: r1[k] for k in ("charts_packed", "fill", "overlap_pairs_qa")}),
            "UD4", [r["pass"] for r in rows])
    # ---------------------------------------------------------------- UD1-UD3 per LOD part
    ud = {}
    for on, m in lod_map.items():
        o = m["ob"]
        r = UD.check_object(o)
        rec = {"ud1_drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"],
               "edges_under_0.05mm": r["edges_under_0.05mm"], "needles_under_0.02mm": r["needles_under_0.02mm"],
               "strip_polygons_under_0.1mm": r.get("strip_polygons_under_0.1mm", 0),
               "triangles": len(o.data.polygons), "layers": [l.name for l in o.data.uv_layers]}
        rec.update(ud3(o.data))
        ud[on] = rec
    rep["ud_parts"] = ud
    for lv in LODS:
        P = [v for k, v in ud.items() if lod_map[k]["lv"] == lv]
        rep[f"ud_LOD{lv}"] = {"ud1_drops": sum(p["ud1_drops"] for p in P),
                              "min_area_mm2": min(p["min_area_mm2"] for p in P),
                              "ud2": {k: sum(p[k] for p in P) for k in ("edges_under_0.05mm", "needles_under_0.02mm",
                                                                        "strip_polygons_under_0.1mm")},
                              "ud3": {k: sum(p[k] for p in P) for k in ("collapsed", "float32_zero_corners",
                                                                        "edge_on_corners")},
                              "layers_ok": all(p["layers"][:2] == ["UV0", "UV1"] for p in P),
                              "triangles": sum(p["triangles"] for p in P)}
        log("UD LOD%d" % lv, json.dumps(rep[f"ud_LOD{lv}"]))
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "lod_uv_report.json").write_text(json.dumps(rep, indent=1, default=float))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log("LODS_DONE %.1fs" % (time.time() - t0))


main()
