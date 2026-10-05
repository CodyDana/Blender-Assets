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

import bpy
import numpy as np

from . import bl
from .mesh import Mesh

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


def build_part(p: PartDef, coll, offset) -> "bpy.types.Object":
    t0 = time.time()
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
        if len(step) == 4:                      # (width, segments, "W", predicate) weighted pass
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
           "recipe": [[s[0], s[1], s[2] if len(s) == 3 else "weighted"] for s in p.recipe]}
    ob["gun_part"] = json.dumps(rec)
    p.report = bl.manifold_report(ob)
    p.report["seconds"] = round(time.time() - t0, 2)
    p.obj = ob
    return ob


def part_record(ob) -> Dict[str, Any]:
    return json.loads(ob["gun_part"]) if "gun_part" in ob else {}
