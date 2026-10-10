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
                        print("    [seq] %s %s #%d  bnd %d multi %d" % (o.name, kind, k, r["boundary_edges"],
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
    fix = _repair(ob)
    if o.wn:
        bl.weighted_normals(ob, weight=WN_WEIGHT, clear_custom=True)
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
