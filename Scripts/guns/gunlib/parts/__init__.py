"""Part registry and the per-part Blender pipeline (import inside Blender).

A part = closed solid(s) in frame M (mm) + boolean unions/cuts + process bevels + weighted normals, with its bone,
joint (clearance-table row, GUN_BUILDING_STUDY 3.7), pivot/axis/limits, material slot and process class stored as
custom properties on the object (``gun_part`` JSON), so the motion sweep, the rig stage and the gates read the same
record.

Bevel recipes by process class (GUN_BUILDING_STUDY 3.1, widths in mm, segments at LOD0):
  M-chamfer 0.45 / 1, M-round 1.0 / 3, S-bend (outer bend) 1.6 / 3 then cut edges 0.25 / 1, S-cut 0.25 / 1,
  C-fillet 1.2 / 3, W-round 2.0 / 3. A recipe is a list of passes (width, segments, angle limit); later passes use
  a larger angle limit so they do not re-bevel the rounded rings of the earlier pass.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from ..mesh import Mesh

RECIPES = {
    "M-chamfer": [(0.45, 1, 30.0)],
    "M-chamfer-front": [(0.7, 1, 30.0)],
    "M-round": [(1.0, 3, 30.0)],
    "S-bend": [(1.6, 3, 50.0), (0.25, 1, 40.0)],
    "S-cut": [(0.25, 1, 30.0)],
    "C-fillet": [(1.2, 3, 30.0)],
    "W-round": [(2.0, 3, 30.0)],
    "W-round-small": [(1.2, 3, 30.0)],
    "none": [],
}


class PartDef:
    def __init__(self, name: str, solids: Sequence[Mesh], bone="body", cls="M-chamfer", slot="M_AR01_Metal",
                 cutters: Sequence[Mesh] = (), unions: Sequence[Mesh] = (), joint: Optional[Dict[str, Any]] = None,
                 recipe=None, smooth_deg=30.0, post_cutters: Sequence[Mesh] = (), wn=True, spec_id=None):
        self.name = name
        self.solids = list(solids)
        self.bone = bone
        self.cls = cls
        self.slot = slot
        self.cutters = list(cutters)
        self.unions = list(unions)
        self.post_cutters = list(post_cutters)
        self.joint = joint or {"type": "butt", "gap_mm": [0.01, 0.05]}
        self.recipe = RECIPES[cls] if recipe is None else recipe
        self.smooth_deg = smooth_deg
        self.wn = wn
        self.spec_id = spec_id or name
        self.obj = None
        self.report: Dict[str, Any] = {}
        self.section_intersect_pre: List[Mesh] = []      # base := base INTERSECT union(these), before unions
        self.post_recipe = []                             # bevel passes after post_cutters


SMALL_FEATURE_MM = {2: 14.0}          # LOD2+: unions / cutters whose box diagonal is under this are left out
#: gunlib 0.2.0 wire-in (SMG_BUILD_PLAN 4.1 / 14 UD1-UD2): every built part checks its own output (gunlib.ud) at the
#: LOD it was built for; the summary goes to its report (``p.report["ud"]``) and the object (``gun_part_ud``)
UD_CHECK = True


def _ud_summary(ob):
    from .. import ud
    r = ud.check_object(ob)
    keys = ("unreal_drops", "unreal_drops_polygons", "min_area_mm2", "edges_under_0.05mm", "needles_under_0.02mm",
            "strip_polygons_under_0.1mm", "needle_groups", "edge_on_groups", "pass_ud1", "pass_ud2")
    return {k: r.get(k) for k in keys}


def _lod_filter(meshes):
    """At gunlib.lod level >= 2 drop small boolean features (pins, pin holes, tiny slots and bumps: under ~1 px at the
    LOD2 switch distance); the texture painted from LOD0 still shows them."""
    from .. import lod as _lod
    lim = SMALL_FEATURE_MM.get(min(_lod.LEVEL, 2))
    if not lim:
        return list(meshes)
    out = []
    for m in meshes:
        V = m.verts() if isinstance(m, Mesh) else None
        if V is not None and len(V) and float(np.linalg.norm(V.max(0) - V.min(0))) < lim:
            continue
        out.append(m)
    return out


def build_part(p: PartDef, coll, offset) -> "bpy.types.Object":
    import bpy                      # lazy: PartDef itself is plain Python (numpy sweeps import the part modules)
    from .. import bl
    t0 = time.time()
    p.unions, p.cutters, p.post_cutters = _lod_filter(p.unions), _lod_filter(p.cutters), _lod_filter(p.post_cutters)
    base = Mesh()
    for s in p.solids:
        base.extend(s)
    ob = base.to_object(p.name, coll, offset, smooth_deg=p.smooth_deg)
    if p.section_intersect_pre:
        sec = p.section_intersect_pre[0].to_object("_sec", coll, offset)
        if len(p.section_intersect_pre) > 1:
            bl.boolean_many(sec, p.section_intersect_pre[1:], "UNION", offset=offset)
        bl.boolean(ob, sec, "INTERSECT")
        bpy.data.objects.remove(sec, do_unlink=True)
    if p.unions:
        bl.boolean_many(ob, p.unions, "UNION", offset=offset)
    if p.cutters:
        bl.boolean_many(ob, p.cutters, "DIFFERENCE", offset=offset)
    bl.clean(ob)
    for step in p.recipe:
        if len(step) == 4 and step[2] == "WC":  # (width, segments, "WC", pred) convex-aware weighted pass (0.2.0)
            bl.bevel_weighted_convex(ob, step[0], step[1], step[3], offset)
        elif len(step) == 4:                    # (width, segments, "W", predicate) weighted pass
            bl.bevel_weighted(ob, step[0], step[1], step[3], offset)
        else:
            bl.bevel(ob, step[0], step[1], step[2])
    if p.post_cutters:
        bl.boolean_many(ob, p.post_cutters, "DIFFERENCE", offset=offset)
        bl.clean(ob)
    for step in p.post_recipe:
        bl.bevel(ob, step[0], step[1], step[2])
    bl.finish(ob)
    if p.wn:
        bl.weighted_normals(ob)
    else:
        bl.mark_sharp(ob, p.smooth_deg)
    rec = {"bone": p.bone, "class": p.cls, "slot": p.slot, "joint": p.joint, "spec_id": p.spec_id,
           "recipe": [[s[0], s[1], s[2] if len(s) == 3 else ("weighted_convex" if s[2] == "WC" else "weighted")]
                      for s in p.recipe]}
    ob["gun_part"] = json.dumps(rec)
    p.report = bl.manifold_report(ob)
    if UD_CHECK:
        p.report["ud"] = _ud_summary(ob)
        ob["gun_part_ud"] = json.dumps(p.report["ud"])
    p.report["seconds"] = round(time.time() - t0, 2)
    p.obj = ob
    return ob


def part_record(ob) -> Dict[str, Any]:
    return json.loads(ob["gun_part"]) if "gun_part" in ob else {}


class BuildCtx:
    """What a part module's build(spec, ctx) builds into: the collection, the frame offset (frame M -> B, mm) and an
    optional set of registry keys to build (None = all). make() turns a provider into Blender objects:

      provider() -> PartDef or tuple of PartDefs   built with build_part (the tuple's parts share the key)
      provider(coll, offset) -> object             a custom builder (explicit boolean steps)
    """

    def __init__(self, coll, offset, spec=None, only=None):
        self.coll = coll
        self.offset = offset
        self.spec = spec
        self.only = set(only) if only else None
        self.built: Dict[str, list] = {}

    def wants(self, key: str) -> bool:
        return self.only is None or key in self.only

    def make(self, key: str, provider) -> list:
        if not self.wants(key):
            return []
        r = provider() if provider.__code__.co_argcount == 0 else None
        if r is None:
            objs = [provider(self.coll, self.offset)]
        else:
            objs = [build_part(q, self.coll, self.offset) for q in (r if isinstance(r, tuple) else (r,))]
        self.built[key] = objs
        return objs


def build_composite(name: str, pieces, coll, offset, bone="body", cls="M-chamfer", slot="M_Metal",
                    cutters: Sequence[Mesh] = (), joint: Optional[Dict[str, Any]] = None, spec_id=None,
                    smooth_deg=30.0, wn=True):
    """gunlib 0.2.0: a part made of pieces that are each edge-broken BEFORE they are united (a leaf plate + its head
    + ears; a clamp base + its cheeks). ``pieces`` = [(Mesh, recipe)], the recipe as build_part's (angle passes or
    (w, seg, "W" / "WC", pred) weighted passes). The union seams stay sharp and every bevel strip is cut across, never
    along, so no bevel / boolean run-out strip forms (the AR-01's U5 / U10 lesson; gates UD1-UD2). Then the cutters
    (bores, windows), the final clean, weighted normals and the gun_part record. Returns the object."""
    import bpy
    from .. import bl
    t0 = time.time()
    objs = []
    for k, (m, recipe) in enumerate(pieces):
        ob = m.to_object(name if k == 0 else f"_{name}_piece{k}", coll, offset, smooth_deg=smooth_deg)
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
    if cutters:
        bl.boolean_many(ob, _lod_filter(cutters), "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.finish(ob)
    if wn:
        bl.weighted_normals(ob)
    else:
        bl.mark_sharp(ob, smooth_deg)
    rec = {"bone": bone, "class": cls, "slot": slot, "joint": joint or {"type": "butt", "gap_mm": [0.01, 0.05]},
           "spec_id": spec_id or name, "recipe": "composite: per-piece breaks, then unions (gunlib.parts.build_composite)"}
    ob["gun_part"] = json.dumps(rec)
    rep = dict(bl.manifold_report(ob))
    if UD_CHECK:
        rep["ud"] = _ud_summary(ob)
        ob["gun_part_ud"] = json.dumps(rep["ud"])
    rep["seconds"] = round(time.time() - t0, 2)
    ob["gun_part_report"] = json.dumps(rep)
    return ob
