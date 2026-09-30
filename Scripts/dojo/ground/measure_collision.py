"""Kit 2 collision check: for every SM_DKG_ piece in the Kit collection of Assets/Dojo/DojoGround.blend, cast rays
straight down on a 1 cm - 12.5 cm grid (by piece size) onto the render mesh and onto its UCX hulls, and report where
the collision top floats above the visible top (float) or sits below it (sink). Pieces without UCX (dressing) are
listed as such. Writes WorkFiles/dojo/build/ground/collision_check.json.

Run: blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/measure_collision.py
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "ground" / "collision_check.json"


def tree(obj):
    me = obj.data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


def top(tr, x, y):
    hit = tr.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)), 10.0)
    return None if hit[0] is None else hit[0].z


def main():
    kit = bpy.data.collections["Kit"]
    res = {}
    for o in sorted(kit.objects, key=lambda q: q.name):
        if o.type != "MESH" or not o.name.startswith("SM_"):
            continue
        hulls = [c for c in o.children if c.name.startswith("UCX_")]
        if not hulls:
            res[o.name] = {"ucx": 0, "note": "no collision (dressing, spec 5.3)"}
            continue
        vis = tree(o)
        hts = [tree(h) for h in hulls]
        xs = [v.co.x for v in o.data.vertices]
        ys = [v.co.y for v in o.data.vertices]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        step = 0.01 if span <= 2.1 else 0.05 if span <= 6 else 0.125
        fl, sk, n = [], [], 0
        worst = None
        x = min(xs) + step / 2
        while x < max(xs):
            y = min(ys) + step / 2
            while y < max(ys):
                zv = top(vis, x, y)
                zh = [z for z in (top(t, x, y) for t in hts) if z is not None]
                if zv is not None and zh:
                    d = max(zh) - zv
                    n += 1
                    fl.append(d)
                    if worst is None or abs(d) > abs(worst[2]):
                        worst = (round(x, 3), round(y, 3), round(d, 4))
                y += step
            x += step
        res[o.name] = {"ucx": len(hulls), "samples": n, "grid_m": step,
                       "float_max_m": round(max(fl), 4) if fl else None,
                       "sink_max_m": round(max(0.0, -min(fl)), 4) if fl else None,
                       "float_gt_5mm_pct": round(100 * sum(1 for d in fl if d > 0.005) / len(fl), 2) if fl else None,
                       "worst_xy_gap": worst}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(k, json.dumps(v))


main()
