"""Unreal degenerate rule at FORM time (gates UD1-UD2, SMG_BUILD_PLAN 14.2; gunlib 0.2.0).

The AR-01 lesson (RIFLE_REPORT 9-10, U5 / U10): micro bevel and boolean run-out strips made Unreal 5.8 drop 4,584
triangles at import and log zero tangents, and three post-process fixes broke other gates. From the SMG on, every part
generator checks its own output here, at every LOD, before the part is accepted; nothing patches export meshes.

UD1  ``unreal_drops`` = 0: the faces Unreal's static FBX import drops (|cross of two edges|^2 < 1e-8 cm^4 in float32,
     i.e. area < 0.005 mm^2; gunlib.tspace.unreal_drops, measured equal to Unreal's own counts on SM_AR01); and the
     2x margin: min triangle area >= 0.01 mm^2.
UD2  micro strips / needles: 0 edges < 0.05 mm; 0 triangles whose height over their longest edge is < 0.02 mm; 0
     strip polygons narrower than 0.1 mm (a stored quad / n-gon whose area / longest edge < 0.1 mm: a bevel or
     run-out strip; thin triangles are judged by the needle rule, their count under 0.1 mm is information).
Zero-tangent risk at form time (no UVs yet; UD3 measures MikkTSpace once UV0 exists), per MikkTSpace tangent group
(a vertex's corners sharing one corner normal): a group whose every corner is a needle (< ``NEEDLE_CORNER_DEG``:
MikkTSpace weights a corner by its angle and a float32 angle near 0 drops out, tspace category A) or whose every face
is seen edge-on by the group's normal (|face normal . corner normal| < 0.1, category C). ``zero_tangent_risk`` = 0 is
part of the UD2 pass (check_object; check_np has no normals and reports needle triangles as information).

Two entry points: ``check_np(V_mm, T)`` (plain numpy on a triangle soup, e.g. a gate npz) and ``check_object(ob)``
(inside Blender: the evaluated mesh in mm, plus Unreal's own polygon fan rule and the corner-normal test).
``gate(reports)`` folds per-object reports into the UD1 / UD2 gate records.
"""
from __future__ import annotations

from typing import Dict, Iterable

import numpy as np

UNREAL_DROP_MM2 = 0.005          # Unreal 5.8 static import (Remove Degenerates on, the default)
MIN_AREA_MM2 = 0.01              # UD1: 2x margin
MIN_EDGE_MM = 0.05               # UD2
MIN_HEIGHT_MM = 0.02             # UD2: needle height over the longest edge
MIN_STRIP_MM = 0.1               # UD2: bevel / run-out strip width
NEEDLE_CORNER_DEG = 0.5          # zero-tangent risk: a corner this sharp gets ~no MikkTSpace weight in float32
EDGE_ON_DOT = 0.1


def _tri_metrics(V, T):
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    cr = np.cross(B - A, C - A)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    L = np.stack([np.linalg.norm(B - A, axis=1), np.linalg.norm(C - B, axis=1), np.linalg.norm(A - C, axis=1)], 1)
    longest = L.max(1)
    height = 2.0 * area / np.maximum(longest, 1e-30)
    # Unreal's rule in float32 centimetres (cross of (b - c, a - c))
    Vc = (V * 0.1).astype(np.float32)
    a, b, c = Vc[T[:, 0]], Vc[T[:, 1]], Vc[T[:, 2]]
    crc = np.cross(b - c, a - c).astype(np.float64)
    drop = (crc ** 2).sum(1) < 1e-8

    def ang(p, q, r):
        u, v = q - p, r - p
        return np.degrees(np.arctan2(np.linalg.norm(np.cross(u, v), axis=1), (u * v).sum(1)))
    corner = np.minimum(np.minimum(ang(A, B, C), ang(B, C, A)), ang(C, A, B))
    return area, L, height, drop, corner


def check_np(V_mm, T, name: str = "") -> Dict:
    """UD1 / UD2 numbers on a triangle soup (vertices in mm)."""
    V = np.asarray(V_mm, float)
    T = np.asarray(T, int).reshape(-1, 3)
    if not len(T):
        return {"name": name, "triangles": 0, "unreal_drops": 0, "pass_ud1": True, "pass_ud2": True}
    area, L, height, drop, corner = _tri_metrics(V, T)
    edges = np.sort(np.r_[T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]], axis=1)
    edges = np.unique(edges, axis=0)
    el = np.linalg.norm(V[edges[:, 0]] - V[edges[:, 1]], axis=1)
    rep = {"name": name, "triangles": int(len(T)), "unreal_drops": int(drop.sum()),
           "min_area_mm2": round(float(area.min()), 6), "tris_under_0.01mm2": int((area < MIN_AREA_MM2).sum()),
           "min_edge_mm": round(float(el.min()), 5), "edges_under_0.05mm": int((el < MIN_EDGE_MM).sum()),
           "min_height_mm": round(float(height.min()), 5), "needles_under_0.02mm": int((height < MIN_HEIGHT_MM).sum()),
           "thin_tris_under_0.1mm_info": int((height < MIN_STRIP_MM).sum()),
           "min_corner_deg": round(float(corner.min()), 4),
           "needle_corner_tris_info": int((corner < NEEDLE_CORNER_DEG).sum())}
    rep["pass_ud1"] = rep["unreal_drops"] == 0 and rep["tris_under_0.01mm2"] == 0
    rep["pass_ud2"] = rep["edges_under_0.05mm"] == 0 and rep["needles_under_0.02mm"] == 0
    return rep


def check_object(ob, name: str = None) -> Dict:
    """UD1 / UD2 on a Blender mesh object (evaluated; world scale; mm), with Unreal's polygon rule
    (tspace.unreal_drops on the polygons as stored) and the edge-on corner-normal test."""
    from . import bl
    from .tspace import unreal_drops
    V, T = bl.tris_np(ob)
    rep = check_np(V, T, name or ob.name)
    me = ob.data
    rep["unreal_drops_polygons"] = int(len(unreal_drops(ob)))
    # strip faces measured on the stored polygons (a bevel strip is often a quad): width = area / longest edge
    s = float(ob.matrix_world.to_scale()[0]) * 1000.0
    strips = 0
    where = []
    Mw = np.array(ob.matrix_world)
    for p in me.polygons:
        if len(p.vertices) < 4:
            continue
        vs = [me.vertices[i].co for i in p.vertices]
        longest = max((vs[i] - vs[(i + 1) % len(vs)]).length for i in range(len(vs))) * s
        if longest > 0 and p.area * s * s / longest < MIN_STRIP_MM:
            strips += 1
            if len(where) < 8:
                c = Mw @ np.r_[np.array(p.center), 1.0]
                where.append([round(float(x) * 1000.0, 3) for x in c[:3]] + [round(p.area * s * s / longest, 4)])
    rep["strip_polygons_under_0.1mm"] = strips
    if where:
        rep["strip_polygons_at_mm_width"] = where
    # zero-tangent risk by MikkTSpace tangent GROUP (a vertex's corners sharing one corner normal; UVs do not exist yet,
    # UD3 adds them): a group whose every corner is a needle (angle < NEEDLE_CORNER_DEG) gets ~no weight in float32
    # (tspace category A); a group whose every face is seen edge-on by the group's normal (|face n . corner n| <
    # EDGE_ON_DOT) projects to a line (category C). A lone thin triangle in a group with a healthy corner is no risk.
    try:
        nl = len(me.loops)
        fn = np.empty(len(me.polygons) * 3)
        me.polygons.foreach_get("normal", fn)
        fn = fn.reshape(-1, 3)
        ls = np.empty(len(me.polygons), np.int64)
        lt = np.empty(len(me.polygons), np.int64)
        me.polygons.foreach_get("loop_start", ls)
        me.polygons.foreach_get("loop_total", lt)
        LV = np.empty(nl, np.int64)
        me.loops.foreach_get("vertex_index", LV)
        Vl = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", Vl)
        Vl = Vl.reshape(-1, 3)
        CN = np.array([c.vector[:] for c in me.corner_normals], float)
        face = np.repeat(np.arange(len(lt)), lt)
        nxt = np.empty(nl, np.int64)
        prv = np.empty(nl, np.int64)
        for f, (a0, n) in enumerate(zip(ls, lt)):
            idx = np.arange(a0, a0 + n)
            nxt[idx] = np.roll(idx, -1)
            prv[idx] = np.roll(idx, 1)
        e1 = Vl[LV[nxt]] - Vl[LV]
        e2 = Vl[LV[prv]] - Vl[LV]
        ang = np.degrees(np.arctan2(np.linalg.norm(np.cross(e1, e2), axis=1), (e1 * e2).sum(1)))
        dot = np.abs((fn[face] * CN).sum(1))
        key = np.c_[LV, np.round(CN * 1e4)]
        _, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.ravel()
        gmax_ang = np.zeros(inv.max() + 1)
        np.maximum.at(gmax_ang, inv, ang)
        gmax_dot = np.zeros(inv.max() + 1)
        np.maximum.at(gmax_dot, inv, dot)
        rep["needle_groups"] = int((gmax_ang < NEEDLE_CORNER_DEG).sum())
        rep["edge_on_groups"] = int((gmax_dot < EDGE_ON_DOT).sum())
        rep["edge_on_corners_info"] = int((dot < EDGE_ON_DOT).sum())
    except Exception as e:  # noqa: BLE001
        rep["needle_groups"] = rep["edge_on_groups"] = None
        rep["group_error"] = str(e)
    rep["zero_tangent_risk"] = int((rep["needle_groups"] or 0) + (rep["edge_on_groups"] or 0))
    rep["pass_ud1"] = rep["pass_ud1"] and rep["unreal_drops_polygons"] == 0
    rep["pass_ud2"] = rep["edges_under_0.05mm"] == 0 and rep["needles_under_0.02mm"] == 0 and strips == 0 and         rep["zero_tangent_risk"] == 0 and rep.get("needle_groups") is not None
    return rep


def gate(reports: Iterable[Dict], label: str = "") -> list:
    """UD1 / UD2 gate records over per-object reports."""
    reps = list(reports)
    bad1 = [r["name"] for r in reps if not r["pass_ud1"]]
    bad2 = [r["name"] for r in reps if not r["pass_ud2"]]
    tot = lambda k: int(sum(r.get(k) or 0 for r in reps))                         # noqa: E731
    mn = lambda k: min((r[k] for r in reps if r.get(k) is not None), default=None)  # noqa: E731
    sfx = f" ({label})" if label else ""
    return [
        {"name": "UD1 Unreal degenerate rule" + sfx,
         "value": {"objects": len(reps), "unreal_drops": int(sum(max(r.get("unreal_drops") or 0, r.get("unreal_drops_polygons") or 0)
                                           for r in reps)),
                   "tris_under_0.01mm2": tot("tris_under_0.01mm2"), "min_area_mm2": mn("min_area_mm2"),
                   "failing": bad1},
         "threshold": "unreal_drops = 0 (area < 0.005 mm2, float32 cm); min triangle area >= 0.01 mm2",
         "pass": not bad1},
        {"name": "UD2 micro strips / needles / zero-tangent risk" + sfx,
         "value": {"edges_under_0.05mm": tot("edges_under_0.05mm"), "min_edge_mm": mn("min_edge_mm"),
                   "needles_under_0.02mm": tot("needles_under_0.02mm"),
                   "strip_polygons_under_0.1mm": tot("strip_polygons_under_0.1mm"),
                   "needle_groups": tot("needle_groups"), "edge_on_groups": tot("edge_on_groups"),
                   "failing": bad2},
         "threshold": "0 edges < 0.05 mm; 0 triangles < 0.02 mm high; 0 strip polygons < 0.1 mm wide; 0 tangent groups "
                      "(vertex + corner normal) all of needle corners (< %.1f deg) or all edge-on (|n.n| < %.1f)"
                      % (NEEDLE_CORNER_DEG, EDGE_ON_DOT),
         "pass": not bad2}]


def locate(ob, k: int = 20) -> Dict:
    """Where the UD failures sit (mm, the object's world frame): centroids of the triangles Unreal drops or that fall
    under the margin / needle rules, and the midpoints of micro edges. A generator's debug aid."""
    from . import bl
    V, T = bl.tris_np(ob)
    if not len(T):
        return {}
    area, L, height, drop, corner = _tri_metrics(V, T)
    bad = np.nonzero(drop | (area < MIN_AREA_MM2) | (height < MIN_HEIGHT_MM))[0]
    c = V[T[bad]].mean(1)
    edges = np.unique(np.sort(np.r_[T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]], axis=1), axis=0)
    el = np.linalg.norm(V[edges[:, 0]] - V[edges[:, 1]], axis=1)
    me_ = edges[el < MIN_EDGE_MM]
    return {"bad_triangles": int(len(bad)), "at": np.round(c[:k], 3).tolist(),
            "micro_edges": int(len(me_)), "edges_at": np.round(0.5 * (V[me_[:k, 0]] + V[me_[:k, 1]]), 3).tolist()}




def _needle_faces(bm, height_mm, k=0.001, corner_deg=0.6):
    """Triangles under the needle height rule, or with a corner under corner_deg (MikkTSpace needle-corner risk)."""
    import math as _m
    res = []
    ck = _m.radians(corner_deg)
    for f in bm.faces:
        if len(f.verts) != 3 or not f.is_valid:
            continue
        es = sorted(f.edges, key=lambda e: e.calc_length())
        lng = es[-1].calc_length()
        if lng <= 0:
            continue
        bad = 2.0 * f.calc_area() / lng < height_mm * k
        if not bad:
            for lp in f.loops:
                if lp.calc_angle() < ck:
                    bad = True
                    break
        if bad:
            res.append((f, es))
    return res


def _safe_collapse(bm, edges, min_dot=0.9, max_len_mm=0.25):
    """Collapse edges one by one to their midpoints, each only when it keeps the mesh a manifold (the link condition:
    the two end vertices share exactly the neighbours opposite the edge) and flips no neighbouring face (the normal
    turns by less than acos(min_dot)). Returns the number collapsed."""
    import bmesh
    n = 0
    for e in sorted(set(edges), key=lambda e: e.calc_length() if e.is_valid else 1e9):
        if not e.is_valid or len(e.link_faces) != 2 or e.calc_length() > max_len_mm * 0.001:
            continue
        a, b = e.verts
        na = {x for le in a.link_edges for x in le.verts if x is not a}
        nb = {x for le in b.link_edges for x in le.verts if x is not b}
        opp = set()
        for f in e.link_faces:
            if len(f.verts) != 3:
                opp = None
                break
            opp |= {v for v in f.verts if v is not a and v is not b}
        if opp is None or (na & nb) != opp:
            continue
        m = (a.co + b.co) * 0.5
        ok = True
        for v in (a, b):
            for f in v.link_faces:
                if f in e.link_faces:
                    continue
                vs = [m if (x is a or x is b) else x.co for x in f.verts]
                if len(vs) < 3:
                    continue
                nn = (vs[1] - vs[0]).cross(vs[2] - vs[0])
                if nn.length < 1e-18:
                    ok = False
                    break
                nn.normalize()
                if nn.dot(f.normal) < min_dot:
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue
        bmesh.ops.pointmerge(bm, verts=[a, b], merge_co=m)
        n += 1
    return n


def repair(ob, edge_mm: float = MIN_EDGE_MM, height_mm: float = MIN_HEIGHT_MM, strip_mm: float = MIN_STRIP_MM,
           rounds: int = 10, flat_deg: float = 0.5, relaxed_final: bool = False) -> Dict:
    """Generator-side cleanup (gunlib 0.2.1, SMG W1b): remove what Unreal would drop or mangle BEFORE the part is
    accepted, inside the part's own build (never on export meshes). Rounds of sub-steps, each kept only when the
    manifold report (boundary / multi-face / wire edges) is no worse than before it:
      weld   vertices closer than 0.6 x edge_mm;
      flat   limited dissolve of coplanar faces (< flat_deg) and collinear vertices, re-triangulated (beauty): the
             T-junction slivers booleans leave on flat faces (first round only);
      flip   needle triangles (height over the longest edge < height_mm): flip that edge into a convex neighbour;
      tjunc  needles whose apex lies on the longest edge (a T-junction on a crease): split the edge there and merge
             the apex into it;
      short  collapse (one by one, link condition + no flipped face) edges under edge_mm, the short sides of strips
             narrower than strip_mm, the remaining needles' and the sub-margin (< MIN_AREA_MM2) triangles' shortest edges.
    Call it before the weighted normals. Returns the counts per sub-step."""
    import math as _m
    import bmesh
    import bpy
    from . import bl
    k = 0.001
    base = bl.manifold_report(ob)
    worst = (base["boundary_edges"], base["multi_face_edges"], base["wire_edges"])
    out = {"rounds": 0, "crumbs": 0, "weld": 0, "short": 0, "flat": 0, "flip": 0, "tjunc": 0, "undone": []}

    def step(name, fn):
        snap = ob.data.copy()
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        n = fn(bm)
        if not n:
            bm.free()
            bpy.data.meshes.remove(snap)
            return 0
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
        r = bl.manifold_report(ob)
        if r["boundary_edges"] > worst[0] or r["multi_face_edges"] > worst[1] or r["wire_edges"] > worst[2]:
            bad = ob.data
            ob.data = snap
            bpy.data.meshes.remove(bad)
            out["undone"].append(name)
            return 0
        bpy.data.meshes.remove(snap)
        out[name] += n
        return n

    def crumbs(bm):
        """Shells of a few faces under 1 mm across (boolean crumbs: a cutter's tip grazing a face): deleted."""
        bm.faces.index_update()
        seen, kill = set(), []
        for f in bm.faces:
            if f.index in seen:
                continue
            comp, st = [], [f]
            seen.add(f.index)
            while st:
                g = st.pop()
                comp.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen:
                            seen.add(h.index)
                            st.append(h)
            if len(comp) <= 12:
                co = [v.co for g in comp for v in g.verts]
                ext = max(max(c[i] for c in co) - min(c[i] for c in co) for i in range(3))
                if ext < 1.0 * k:
                    kill += comp
        if kill:
            bmesh.ops.delete(bm, geom=list(set(kill)), context="FACES")
            loose = [v for v in bm.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="VERTS")
        return len(kill)

    def weld(bm):
        n0 = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.6 * edge_mm * k)
        return n0 - len(bm.verts)

    def flat(bm):
        nf = len(bm.faces)
        bmesh.ops.dissolve_limit(bm, angle_limit=_m.radians(flat_deg), use_dissolve_boundaries=False,
                                 verts=bm.verts, edges=bm.edges)
        ng = [f for f in bm.faces if len(f.verts) > 3]
        if ng:
            bmesh.ops.triangulate(bm, faces=ng, quad_method="BEAUTY", ngon_method="BEAUTY")
        return 1 if (nf != len(bm.faces) or ng) else 0

    def flip(bm):
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        fl = []
        for f, es in _needle_faces(bm, height_mm):
            e = es[-1]
            if len(e.link_faces) != 2:
                continue
            g = e.link_faces[0] if e.link_faces[1] == f else e.link_faces[1]
            if len(g.verts) != 3 or f.normal.dot(g.normal) < 0.5:
                continue
            v = [x for x in f.verts if x not in e.verts][0]
            w = [x for x in g.verts if x not in e.verts][0]
            nrm = f.normal + g.normal
            nrm.normalize()
            d = w.co - v.co
            if d.cross(e.verts[0].co - v.co).dot(nrm) * d.cross(e.verts[1].co - v.co).dot(nrm) < 0:
                fl.append(e)
        fl = list(set(fl))
        if fl:
            bmesh.ops.rotate_edges(bm, edges=fl, use_ccw=False)
        return len(fl)

    def tjunc(bm):
        """A needle whose apex lies on its longest edge (a T-junction on a crease, where a flip would fold the
        surface): split that edge at the apex's projection and merge the apex into the new vertex (the apex moves by
        the needle's height, < height_mm)."""
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        n = 0
        for f, es in _needle_faces(bm, height_mm):
            if not f.is_valid:
                continue
            e = es[-1]
            if not e.is_valid or len(e.link_faces) != 2:
                continue
            a, b = e.verts
            c = [x for x in f.verts if x is not a and x is not b]
            if len(c) != 1:
                continue
            c = c[0]
            ab = b.co - a.co
            L2 = ab.dot(ab)
            if L2 <= 0:
                continue
            t = (c.co - a.co).dot(ab) / L2
            if not (0.02 < t < 0.98):
                continue
            h = (a.co + ab * t - c.co).length
            if h > 2.0 * height_mm * k:
                continue
            ne, nv = bmesh.utils.edge_split(e, a, t)
            bmesh.ops.pointmerge(bm, verts=[c, nv], merge_co=nv.co.copy())
            n += 1
        return n

    def short(bm):
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        es = [e for e in bm.edges if e.calc_length() < edge_mm * k]
        es += [es_[0] for f, es_ in _needle_faces(bm, height_mm)]
        lim = MIN_AREA_MM2 * k * k * 1.05
        tiny = [f for f in bm.faces if len(f.verts) == 3 and f.calc_area() < lim]
        es += [min(f.edges, key=lambda e: e.calc_length()) for f in tiny]
        n = _safe_collapse(bm, es)
        if not n:                                            # fallback: any edge of a leftover offender
            es2 = [e for f, es_ in _needle_faces(bm, height_mm) for e in es_[1:]]
            es2 += [e for f in bm.faces if f.is_valid and len(f.verts) == 3 and f.calc_area() < lim for e in f.edges]
            n = _safe_collapse(bm, es2, min_dot=0.8)
        return n

    def relaxed(bm):
        """(relaxed_final, gunlib 0.2.1) the residue the rounds leave: triangles under MIN_AREA_MM2 and needle-corner
        triangles (a corner under 0.6 deg) lose their shortest edge, collapsed under the link condition with a looser
        turn limit (normals within 45 deg) and up to 0.6 mm long."""
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        lim = MIN_AREA_MM2 * k * k * 1.05
        es = []
        for f in bm.faces:
            if not f.is_valid or len(f.verts) != 3:
                continue
            small = f.calc_area() < lim
            needle = any(lp.calc_angle() < _m.radians(NEEDLE_CORNER_DEG) for lp in f.loops)
            if small or needle:
                es.append(min(f.edges, key=lambda e: e.calc_length()))
        n = _safe_collapse(bm, es, min_dot=0.7, max_len_mm=0.6)
        if not n:                            # a sub-margin sliver whose short edges all exceed 0.6: any of its edges
            es2 = [e for f in bm.faces if f.is_valid and len(f.verts) == 3 and f.calc_area() < lim for e in f.edges]
            n = _safe_collapse(bm, es2, min_dot=0.5, max_len_mm=1.2)
        return n

    for r in range(rounds):
        n = (step("crumbs", crumbs) if r == 0 else 0) + step("weld", weld) + (step("flat", flat) if r == 0 else 0) + step("flip", flip) + step("tjunc", tjunc) +             step("short", short)
        out["rounds"] = r + 1
        if not n:
            break
    if relaxed_final:
        out["relaxed"] = 0
        for _ in range(6):
            if not step("relaxed", relaxed):
                break
    bl.triangulate_ngons(ob)
    return out
