"""Butt-plate butt-gap check (headless Blender, read-only on a dev build blend):

    blender -b <bp_<tag>.blend> --factory-startup --python parts/butt_plate_gaps.py -- --json <out.json>

For the pairs plate|stock and screws|plate: overlapping triangle pairs (BVHTree.overlap, world space) and the minimum
distance from either object's vertices to the other's surface (mm; frame B is metres). Rule: 0 overlaps, modelled gaps
0.01-0.05 mm where parts butt.
"""
from __future__ import annotations

import json
import sys

import bpy
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[argv.index("--json") + 1]


def tree(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    mw = ob.matrix_world
    V = [mw @ v.co for v in me.vertices]
    F = [tuple(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return BVHTree.FromPolygons(V, F, epsilon=0.0), V


def pair(a, b):
    ta, va = tree(bpy.data.objects[a])
    tb, vb = tree(bpy.data.objects[b])
    ov = ta.overlap(tb)
    d = []
    for V, T in ((va, tb), (vb, ta)):
        for v in V:
            hit = T.find_nearest(v, 0.002)
            if hit[0] is not None:
                d.append(hit[3])
    return {"overlapping_face_pairs": len(ov), "min_vertex_distance_mm": round(min(d) * 1000.0, 4) if d else None}


rep = {"plate|stock": pair("butt_plate", "buttstock"), "screws|plate": pair("butt_screws", "butt_plate")}
open(out, "w").write(json.dumps(rep, indent=1))
print("[bpgaps]", rep)
