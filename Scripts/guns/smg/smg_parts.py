"""SMG01 form stage: the part registry and the Blender builders (import inside Blender for build_all).

Every part is real geometry in frame M (mm) from smg_spec.json (SMG_BUILD_PLAN 4.1): closed solids, moving parts
separate with their bone / joint, butt joints with a 0.02 mm modelled gap, every opening cut with its wall, edges broken
by process class, UD-safe generators (gunlib.ud runs on every part as it is built).

Three build kinds:
  PartDef (gunlib.parts)   the plain path: solids, unions, cutters, recipe, post cutters (gunlib.parts.build_part)
  Comp (parts.Comp)        pieces each edge-broken (and cut by its own cutters) before the union (build_comp)
  Ops (below)              an explicit operation list for the mouldings (union / intersect / diff / weighted bevels /
                           draft deform), built by build_ops
ORDER fixes the object order of the triangle dump and the build report.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from smg_common import CODE, SPEC, GRIP, SCRATCH, PARTS_COLL
import os
DEBUG_OPS = os.environ.get("SMG_DEBUG_OPS", "")
WN_WEIGHT = 100                     # weighted normals: the largest face dominates (flat faces stay flat next to bevels)

ORDER = ("upper_receiver", "lower_receiver", "grip_cover", "bolt_rails", "top_rail", "rail_screws", "lower_rail",
         "sight_rear_base", "sight_rear_leaf", "sight_rear_pin", "sight_front_base", "sight_front_leaf",
         "sight_front_pin", "barrel", "muzzle_device", "bolt", "charging_handle", "charging_slide", "selector",
         "trigger", "trigger_axle", "mag_release", "mag_release_pin", "pins_fasteners", "hinge_axle", "stock_frame",
         "stock_latch_button", "stock_latch_bolt", "butt_pad", "magazine", "magazine_follower", "magazine_floor_plate")


@dataclass
class Ops:
    """A part built by an explicit operation list. ops: [(kind, payload)], kind in
    union / intersect / diff (payload: list of Mesh), bevel (w, seg, angle), bevel_w (w, seg, pred),
    bevel_wc (w, seg, pred convex-aware), deform (fn(V_M) -> V_M), clean ()."""
    name: str
    base: Any
    ops: list
    bone: str = "body"
    cls: str = "P-round"
    slot: str = "M_SMG01_Furniture"
    joint: Optional[Dict[str, Any]] = None
    spec_id: Optional[str] = None
    smooth_deg: float = 30.0
    wn: bool = True


def _record(ob, bone, cls, slot, joint, spec_id, recipe):
    rec = {"bone": bone, "class": cls, "slot": slot, "joint": joint or {"type": "butt", "gap_mm": [0.01, 0.05]},
           "spec_id": spec_id or ob.name, "recipe": recipe}
    ob["gun_part"] = json.dumps(rec)


def _ud(ob):
    from gunlib.parts import _ud_summary
    return _ud_summary(ob)


def _deform(ob, fn, offset):
    me = ob.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3) * 1000.0 + np.asarray(offset, float)
    V = fn(V)
    me.vertices.foreach_set("co", ((V - np.asarray(offset, float)) * 0.001).reshape(-1))
    me.update()


# (W1 realism round 2) Flat faces shade flat. The big flat faces come out of the booleans, bevel clamping and the UD
# repair (collapses move vertices up to 0.35 mm) very slightly warped: the receiver's front face round the barrel collar
# and the eyelet measured 75 triangles whose normals spread 2.1 deg, and bl.weighted_normals (which triangulates the
# n-gons first, so its FACE_AREA weight sees thin triangles that lose to the bevel strips) left 24 corners 0.7-9.9 deg
# off: the shading fans streaks across the face (judges: radial streaks from the hole on the front face). Each large
# flat region is grown from a seed face (>= 20 mm2) over neighbours within 3.0 deg of the seed's normal and 0.6 mm of
# its plane (the front face's upper band is warped up to 0.5 mm round the eyelet; seed-relative, so a gently curved
# surface cannot creep in transitively); a region of >= 100 mm2 with area / perimeter >= 1.5 mm (never a bevel
# strip) has every corner set to its area-weighted plane normal and its boundary edges at >= 10 deg marked sharp (the neighbours keep theirs). Thin slivers lying on the plane join within 8 deg (a
# 0.08 mm vertex offset tilts a 1.1 mm wide sliver 4 deg). The geometry is not moved. (The streaks the judges saw were
# mostly the traced front edge's zig-zag strips: smg_geom.MASTER_POLYS.)
FLAT_SLIVER_DEG = 8.0
FLAT_SEED_MM2, FLAT_MIN_AREA_MM2, FLAT_MIN_THICK_MM, FLAT_SHARP_DEG, FLAT_TOL_DEG, FLAT_TOL_MM = (20.0, 100.0, 1.5,
                                                                                                10.0, 3.0, 0.6)


def _flatten_planar(ob):
    import math as _m
    from collections import deque
    me = ob.data
    nP, nL, nE, nV = len(me.polygons), len(me.loops), len(me.edges), len(me.vertices)
    if nP == 0:
        return 0
    cn = np.empty(nL * 3)
    me.corner_normals.foreach_get("vector", cn)
    cn = cn.reshape(-1, 3)
    pn = np.empty(nP * 3)
    me.polygons.foreach_get("normal", pn)
    pn = pn.reshape(-1, 3)
    pa = np.empty(nP)
    me.polygons.foreach_get("area", pa)
    pa = pa * 1e6                                              # mm2
    pc = np.empty(nP * 3)
    me.polygons.foreach_get("center", pc)
    pc = pc.reshape(-1, 3) * 1000.0                            # mm (object space)
    ls = np.empty(nP, int)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(nP, int)
    me.polygons.foreach_get("loop_total", lt)
    le = np.empty(nL, int)
    me.loops.foreach_get("edge_index", le)
    lv = np.empty(nL, int)
    me.loops.foreach_get("vertex_index", lv)
    lp = np.repeat(np.arange(nP), lt)
    ev = np.empty(nE * 2, int)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    co = np.empty(nV * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) * 1000.0
    ef = [[] for _ in range(nE)]
    for k in range(nL):
        ef[le[k]].append(lp[k])
    fe = [le[ls[i]:ls[i] + lt[i]] for i in range(nP)]
    fv = [lv[ls[i]:ls[i] + lt[i]] for i in range(nP)]
    cos_tol = _m.cos(_m.radians(FLAT_TOL_DEG))
    cos_sliver = _m.cos(_m.radians(FLAT_SLIVER_DEG))
    # slivers (longest edge / area > 3 per mm, under 8 mm2) tilt several degrees on a 0.08 mm vertex offset: they join
    # within FLAT_SLIVER_DEG when every vertex lies on the seed's plane (the bevel strips' 22.5 deg never do)
    thin = np.zeros(nP, bool)
    for i in range(nP):
        if pa[i] < 8.0:
            P_ = co[fv[i]]
            emax = max(float(np.linalg.norm(P_[k] - P_[(k + 1) % len(P_)])) for k in range(len(P_)))
            thin[i] = emax / max(pa[i], 1e-9) > 3.0
    owner = np.full(nP, -1)
    regions = []
    for f in np.argsort(-pa):
        if pa[f] < FLAT_SEED_MM2:
            break
        if owner[f] >= 0:
            continue
        n0, p0 = pn[f], pc[f]
        reg = [f]
        owner[f] = len(regions)
        q = deque([f])
        while q:
            a = q.popleft()
            for e in fe[a]:
                for g in ef[e]:
                    if owner[g] >= 0:
                        continue
                    if pn[g] @ n0 < cos_tol and not (pn[g] @ n0 >= cos_sliver and thin[g]):
                        continue
                    if np.max(np.abs((co[fv[g]] - p0) @ n0)) > FLAT_TOL_MM:
                        continue
                    owner[g] = len(regions)
                    reg.append(g)
                    q.append(g)
        regions.append(reg)
    sel = []
    for r, reg in enumerate(regions):
        area = float(pa[reg].sum())
        if area < FLAT_MIN_AREA_MM2:
            continue
        per = 0.0
        for a in reg:
            for e in fe[a]:
                fs = ef[e]
                if not (len(fs) == 2 and owner[fs[0]] == owner[fs[1]]):
                    per += float(np.linalg.norm(co[ev[e, 0]] - co[ev[e, 1]]))
        if area / max(per, 1e-9) >= FLAT_MIN_THICK_MM:
            sel.append(r)
    if not sel:
        return 0
    plane = {}
    for r in sel:
        reg = regions[r]
        n = (pn[reg] * pa[reg][:, None]).sum(0)
        plane[r] = n / np.linalg.norm(n)
    pn = np.empty(nP * 3)
    me.polygons.foreach_get("normal", pn)
    pn = pn.reshape(-1, 3)
    sharp_cos = _m.cos(_m.radians(FLAT_SHARP_DEG))
    att = me.attributes.get("sharp_edge")
    if att is None:
        att = me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    sh = np.zeros(nE, bool)
    att.data.foreach_get("value", sh)
    selset = set(sel)
    for e in range(nE):
        fs = ef[e]
        if len(fs) != 2 or owner[fs[0]] == owner[fs[1]]:
            continue
        if (owner[fs[0]] in selset or owner[fs[1]] in selset) and pn[fs[0]] @ pn[fs[1]] < sharp_cos:
            sh[e] = True
    att.data.foreach_set("value", sh)
    for i in range(nP):
        if owner[i] in selset:
            cn[ls[i]:ls[i] + lt[i]] = plane[owner[i]]
    me.normals_split_custom_set([tuple(v) for v in cn])
    me.update()
    return len(sel)


def build_ops(o: Ops, coll, offset):
    import bpy
    from gunlib import bl
    t0 = time.time()
    ob = o.base.to_object(o.name, coll, offset, smooth_deg=o.smooth_deg)
    bl.clean(ob)
    steps = []
    for kind, pay in o.ops:
        if kind in ("union", "intersect", "diff"):
            meshes = [m for m in pay if m is not None]
            if not meshes:
                continue
            op = {"union": "UNION", "intersect": "INTERSECT", "diff": "DIFFERENCE"}[kind]
            if kind == "intersect":
                for m in meshes:                       # one by one (an intersection with a collection = with the union)
                    bl.boolean(ob, m, "INTERSECT", offset=offset)
            else:
                # one by one: a collection operand set whose members touch each other coplanar breaks EXACT (measured on
                # the lower receiver: 711 multi-face edges batched, 0 one by one)
                for k, m in enumerate(meshes):
                    bl.boolean(ob, m, op, offset=offset)
                    bl.clean(ob)
                    if DEBUG_OPS == "seq":
                        r = bl.manifold_report(ob)
                        print("    [seq] %s %s #%d  tris %d shells %d bnd %d multi %d" % (
                            o.name, kind, k, r["triangles"], r["shells"], r["boundary_edges"],
                                                                        r["multi_face_edges"]), flush=True)
            bl.clean(ob)
            steps.append(f"{kind} x{len(meshes)}")
        elif kind == "bevel":
            w, seg, ang = pay
            bl.bevel(ob, w, seg, ang)
            steps.append(f"bevel {w}/{seg}/{ang}")
        elif kind == "bevel_w":
            w, seg, pred = pay
            n = bl.bevel_weighted(ob, w, seg, pred, offset)
            steps.append(f"bevel_w {w}/{seg} ({n} edges)")
        elif kind == "bevel_wc":
            w, seg, pred = pay
            n = bl.bevel_weighted_convex(ob, w, seg, pred, offset)
            steps.append(f"bevel_wc {w}/{seg} ({n} edges)")
        elif kind == "deform":
            _deform(ob, pay, offset)
            steps.append("deform")
        elif kind == "clean":
            bl.clean(ob)
        else:
            raise ValueError(kind)
        if DEBUG_OPS:
            V = np.empty(len(ob.data.vertices) * 3)
            ob.data.vertices.foreach_get("co", V)
            V = V.reshape(-1, 3) * 1000.0 + np.asarray(offset, float)
            rep = bl.manifold_report(ob)
            print("  [ops] %s %-26s tris %6d bnd %3d multi %3d shells %2d  X %.1f..%.1f Y %.1f..%.1f Z %.1f..%.1f" % (
                o.name, steps[-1] if steps else kind, rep["triangles"], rep["boundary_edges"], rep["multi_face_edges"],
                rep["shells"], V[:, 0].min(), V[:, 0].max(), V[:, 1].min(), V[:, 1].max(), V[:, 2].min(),
                V[:, 2].max()), flush=True)
            if DEBUG_OPS == "keep":
                cp = ob.copy()
                cp.data = ob.data.copy()
                cp.name = f"_dbg_{o.name}_{len(steps):02d}"
                coll.objects.link(cp)
    bl.finish(ob)
    if DEBUG_OPS:
        r_ = bl.manifold_report(ob)
        print("  [ops] %s after finish: tris %d bnd %d multi %d" % (o.name, r_["triangles"], r_["boundary_edges"],
                                                                r_["multi_face_edges"]), flush=True)
    fix = _repair(ob)
    if DEBUG_OPS:
        r_ = bl.manifold_report(ob)
        print("  [ops] %s after repair: tris %d bnd %d multi %d %s" % (o.name, r_["triangles"], r_["boundary_edges"],
                                                                   r_["multi_face_edges"], fix), flush=True)
    if o.wn:
        bl.weighted_normals(ob, weight=WN_WEIGHT, clear_custom=True)
        _flatten_planar(ob)
    else:
        bl.mark_sharp(ob, o.smooth_deg)
    _record(ob, o.bone, o.cls, o.slot, o.joint, o.spec_id, steps)
    rep = dict(bl.manifold_report(ob))
    rep["ud_repair"] = fix
    rep["ud"] = _ud(ob)
    ob["gun_part_ud"] = json.dumps(rep["ud"])
    rep["seconds"] = round(time.time() - t0, 2)
    ob["gun_part_report"] = json.dumps(rep)
    return ob


def build_comp(c, coll, offset):
    """Pieces = (Mesh, recipe) or (Mesh, recipe, cutters): each piece cut by its own cutters and edge-broken BEFORE the
    union (seams stay sharp, no bevel / boolean run-out strip), then the global cutters."""
    import bpy
    from gunlib import bl
    t0 = time.time()
    objs = []
    for k, pc in enumerate(c.pieces):
        m, recipe = pc[0], pc[1]
        cuts = list(pc[2]) if len(pc) > 2 else []
        ob = m.to_object(c.name if k == 0 else f"_{c.name}_piece{k}", coll, offset, smooth_deg=c.smooth_deg)
        bl.clean(ob)
        if cuts:
            bl.boolean_many(ob, cuts, "DIFFERENCE", offset=offset)
            bl.clean(ob)
        for step in recipe:
            if len(step) == 4 and step[2] == "WC":
                bl.bevel_weighted_convex(ob, step[0], step[1], step[3], offset)
            elif len(step) == 4:
                bl.bevel_weighted(ob, step[0], step[1], step[3], offset)
            else:
                bl.bevel(ob, step[0], step[1], step[2])
        objs.append(ob)
    ob = objs[0]
    for other in objs[1:]:
        bl.boolean(ob, other, "UNION", offset=offset)
        bpy.data.objects.remove(other, do_unlink=True)
    if c.cutters:
        bl.boolean_many(ob, list(c.cutters), "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.finish(ob)
    fix = _repair(ob)
    bl.weighted_normals(ob, weight=WN_WEIGHT, clear_custom=True)
    _flatten_planar(ob)
    _record(ob, c.bone, c.cls, c.slot, c.joint, c.spec_id, "composite: per-piece cuts + breaks, then unions")
    rep = dict(bl.manifold_report(ob))
    rep["ud_repair"] = fix
    rep["ud"] = _ud(ob)
    ob["gun_part_ud"] = json.dumps(rep["ud"])
    rep["seconds"] = round(time.time() - t0, 2)
    ob["gun_part_report"] = json.dumps(rep)
    return ob


def _repair(ob):
    """gunlib.ud.repair inside the part's own build (UD1-UD2 at form time), before the weighted normals."""
    from gunlib import ud as UD
    r0 = UD.check_object(ob)
    if r0["pass_ud1"] and r0["edges_under_0.05mm"] == 0 and r0["needles_under_0.02mm"] == 0 and             r0.get("strip_polygons_under_0.1mm", 0) == 0:
        return {"needed": False}
    out = UD.repair(ob, rounds=30)          # relaxed_final moved vertices up to 0.6 mm: B3 rows broke (not used)
    out["needed"] = True
    out["area_flip"] = _area_flip(ob)
    return out


AREA_MARGIN_MM2 = 0.0125                     # UD1 asks >= 0.01 mm2: a 25 % margin over it


def _area_flip(ob, lim=AREA_MARGIN_MM2, rounds=8):
    """Sub-margin triangles (< lim mm2) left by the repair, removed WITHOUT moving a vertex (W1b fix round, UD1):
    (a) a sliver lying flat in its surface (3 consecutive points of a cut arc, an ear) gets the edge it shares with a
        coplanar neighbour flipped when both new triangles are larger than the old smaller one, keep their
        orientation and clear the needle height (the surface is unchanged: the same plane, other diagonals);
    (b) a folded sliver (its normal against its neighbours': a repair collapse folded it over) loses its shortest edge,
        collapsed under the link condition only when no surviving face turns by more than 30 deg, the move <= 0.35 mm.
    Each round is kept only when the manifold report stays as clean. Returns the counts."""
    import bmesh
    import bpy
    from gunlib import bl
    from gunlib import ud as UD
    k2 = 1e-6                                 # mm2 -> m2
    out = {"flipped": 0, "collapsed": 0, "left": None}
    base = bl.manifold_report(ob)

    def tri_area(a, b, c):
        return 0.5 * (b - a).cross(c - a).length

    for _ in range(rounds):
        snap = ob.data.copy()
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.normal_update()
        small = [f for f in bm.faces if len(f.verts) == 3 and f.calc_area() < lim * k2]
        if not small:
            bm.free()
            bpy.data.meshes.remove(snap)
            break
        nf = nc = 0
        folded = []
        for f in small:
            if not f.is_valid:
                continue
            a0 = f.calc_area()
            nbr = [g for e in f.edges for g in e.link_faces if g is not f]
            if nbr and sum(1 for g in nbr if f.normal.dot(g.normal) < -0.5) >= 2:
                folded.append(f)
                continue
            best = None
            for e in sorted(f.edges, key=lambda e: -e.calc_length()):
                if len(e.link_faces) != 2:
                    continue
                g = e.link_faces[0] if e.link_faces[1] is f else e.link_faces[1]
                if len(g.verts) != 3 or f.normal.dot(g.normal) < 0.99995:
                    continue
                v = [x for x in f.verts if x not in e.verts][0]
                w = [x for x in g.verts if x not in e.verts][0]
                p, q = e.verts
                n = f.normal
                t1 = (v.co, p.co, w.co)
                t2 = (v.co, w.co, q.co)
                ok = True
                areas = []
                for t in (t1, t2):
                    cr = (t[1] - t[0]).cross(t[2] - t[0])
                    ar = 0.5 * cr.length
                    if ar <= 0:
                        ok = False
                        break
                    # orientation: both new triangles on the same side as the old pair (a convex quad)
                    if abs(cr.normalized().dot(n)) < 0.9999:
                        ok = False
                        break
                    L = max((t[1] - t[0]).length, (t[2] - t[1]).length, (t[0] - t[2]).length)
                    if 2.0 * ar / L < UD.MIN_HEIGHT_MM * 1e-3 or (w.co - v.co).length < UD.MIN_EDGE_MM * 1e-3:
                        ok = False
                        break
                    areas.append(ar)
                if not ok:
                    continue
                # the quad must be convex: v and w on opposite sides of the line p-q, p and q on opposite sides of v-w
                s1 = (q.co - p.co).cross(v.co - p.co).dot(n) * (q.co - p.co).cross(w.co - p.co).dot(n)
                s2 = (w.co - v.co).cross(p.co - v.co).dot(n) * (w.co - v.co).cross(q.co - v.co).dot(n)
                if s1 >= 0 or s2 >= 0:
                    continue
                gain = min(areas)
                if gain > max(a0, lim * k2) or (gain > a0 * 1.5 and gain > min(a0, g.calc_area())):
                    if best is None or gain > best[0]:
                        best = (gain, e)
            if best is not None:
                r = bmesh.ops.rotate_edges(bm, edges=[best[1]], use_ccw=False)
                if r.get("edges"):
                    nf += 1
        # folded slivers: collapse their shortest edge (link condition, surviving faces turn < 30 deg)
        es = [min(f.edges, key=lambda e: e.calc_length()) for f in folded if f.is_valid]
        if es:
            nc = UD._safe_collapse(bm, es, min_dot=0.866, max_len_mm=0.35)
        if not (nf or nc):
            # (c) a corner sliver no flip can widen (where a bevel round meets a cut, its neighbours not coplanar):
            # one of its edges (shortest first, <= 0.5 mm: the move <= 0.25) collapsed, surviving faces turn < 41 deg.
            # Only for what still fails UD1 itself (< 0.0101 mm2): a collapse moves a vertex, and on a curved contact
            # face (a press-fit bore, 0.02 to its pin) any move breaks the contact (measured: the rear sight's pin bore)
            rest = [f for f in bm.faces if f.is_valid and len(f.verts) == 3 and f.calc_area() < 0.0101 * k2]
            es = [e for f in rest for e in f.edges]
            if es:
                nc = UD._safe_collapse(bm, es, min_dot=0.75, max_len_mm=0.5)
        if not (nf or nc):
            bm.free()
            bpy.data.meshes.remove(snap)
            break
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
        r = bl.manifold_report(ob)
        if r["boundary_edges"] > base["boundary_edges"] or r["multi_face_edges"] > base["multi_face_edges"] or \
                r["wire_edges"] > base["wire_edges"]:
            bad = ob.data
            ob.data = snap
            bpy.data.meshes.remove(bad)
            break
        bpy.data.meshes.remove(snap)
        out["flipped"] += nf
        out["collapsed"] += nc
    V, T = bl.tris_np(ob)
    A, B, Cc = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    ar = 0.5 * np.linalg.norm(np.cross(B - A, Cc - A), axis=1)
    out["left"] = int((ar < lim).sum())
    out["min_area_mm2"] = round(float(ar.min()), 6) if len(ar) else None
    return out


def build_one(item, coll, offset):
    from gunlib.parts import PartDef, build_part
    from gunlib import bl
    from parts import Comp
    if isinstance(item, PartDef):
        ob = build_part(item, coll, offset)
        r = json.loads(ob.get("gun_part_ud", "{}"))
        if not (r.get("pass_ud1") and r.get("pass_ud2")):
            _repair(ob)
        if item.wn:
            bl.weighted_normals(ob, weight=WN_WEIGHT, clear_custom=True)
            _flatten_planar(ob)
        ob["gun_part_ud"] = json.dumps(_ud(ob))
        return ob
    if isinstance(item, Comp):
        return build_comp(item, coll, offset)
    if isinstance(item, Ops):
        return build_ops(item, coll, offset)
    raise TypeError(type(item))


GROUPS = ("receiver", "rails", "sights", "front", "mechanism", "stock", "magazine")


def provider(group) -> Callable:
    """group -> callable returning a list of builds (each build's name is its object name); imported lazily."""
    import importlib
    if group == "rails":
        from parts import rails
        return lambda: rails.top_rail()[0] + rails.rail_screws() + rails.lower_rail()[0]
    if group == "sights":
        from parts import sights
        return lambda: sights.rear_sight() + sights.front_sight()
    mod = {"receiver": "receiver", "front": "front", "mechanism": "mechanism", "stock": "stock",
           "magazine": "magazine"}[group]
    return importlib.import_module(f"parts.{mod}").build_all


def build_all(only=None, tag=None, coll_name=PARTS_COLL, groups=None):
    """Build every part (or the names in only) into coll_name; export the triangles (scratch/<tag>_tris.npz) and the
    build report, objects in ORDER."""
    from gunlib import bl
    coll = bl.collection(coll_name)
    built = {}
    report = {}
    for gname in GROUPS:
        if groups and gname not in groups:
            continue
        items = provider(gname)()
        for it in items:
            if only and it.name not in only:
                continue
            t0 = time.time()
            ob = build_one(it, coll, GRIP)
            built[ob.name] = ob
            print("[%s] built %-22s %6.1fs" % (CODE, ob.name, time.time() - t0), flush=True)
    names = [n for n in ORDER if n in built] + sorted(n for n in built if n not in ORDER)
    objs = [built[n] for n in names]
    for ob in objs:
        rep = bl.manifold_report(ob)
        try:
            rep["ud"] = json.loads(ob.get("gun_part_ud", "{}"))
        except Exception:  # noqa: BLE001
            pass
        report[ob.name] = rep
        print("[%s] part %-22s tris %6d  boundary %d  multi %d  shells %d  UD %s/%s" % (
            CODE, ob.name, rep["triangles"], rep["boundary_edges"], rep["multi_face_edges"], rep["shells"],
            rep.get("ud", {}).get("pass_ud1"), rep.get("ud", {}).get("pass_ud2")), flush=True)
    tag = tag or ("form" if not only else "form_partial")
    if objs:
        bl.export_npz(objs, SCRATCH / f"{tag}_tris.npz", GRIP, [o.name for o in objs])
    (SCRATCH / f"{tag}_build_report.json").write_text(json.dumps(report, indent=1, default=str))
    print("[%s] total tris" % CODE, sum(r["triangles"] for r in report.values()))
    return objs, report
