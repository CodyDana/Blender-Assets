"""Round 4: where is there NO surface at grade inside the wall? The ground kit left holes where the grey-box buildings
stood (its panels stop at the grey-box footprints, e.g. Y 27.5 in front of the outbuildings); the round-4 buildings do
not fill exactly the same footprints, so the sky shows through where neither covers (the white-lilac strips in the
first round-4 captures). Rays straight down from +0.30 m over a 5 cm grid, X -1..45, Y -1..37, against every placed
render mesh whose world box starts below +0.30 (ground, footings, floors, building bases); a ray that hits nothing
within 0.55 m is a hole. Inside a closed building a ray starting inside a wall or base hits its inner faces, so only
open-air holes are reported.
Run: blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python <this> [-- --out <name>]
Out: WorkFiles/dojo/build/unreal/round4/checks/ground_holes_r4[_<name>].json
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAG = A[A.index("--out") + 1] if "--out" in A else ""
L = json.loads((WORK / "showcase" / "layout_showcase.json").read_text(encoding="utf-8"))
verts, polys = [], []
used = 0
for n, i in enumerate(L["instances"]):
    o = bpy.data.objects.get(f"{i['piece']}__{n:04d}")
    if o is None or i["collision_class"] == "boundary" or i["piece"] in ("SM_DGB_Ground_Outside",):
        continue
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    if min(p.z for p in bb) > 0.30 or max(p.x for p in bb) < -1.2 or min(p.x for p in bb) > 45.2 \
            or max(p.y for p in bb) < -1.2 or min(p.y for p in bb) > 37.2:
        continue
    mw = o.matrix_world
    base = len(verts)
    verts += [mw @ v.co for v in o.data.vertices]
    polys += [[base + k for k in p.vertices] for p in o.data.polygons]
    used += 1
bvh = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
STEP = 0.05
holes = []
nx, ny = int(46 / STEP), int(38 / STEP)
for a in range(nx):
    x = -1.0 + (a + 0.5) * STEP
    for b in range(ny):
        y = -1.0 + (b + 0.5) * STEP
        hit = bvh.ray_cast(Vector((x, y, 0.30)), Vector((0, 0, -1)), 0.55)
        if hit[0] is None:
            holes.append((round(x, 3), round(y, 3)))
# cluster 4-connected cells into boxes
cells = {(round((x + 1.0) / STEP - 0.5), round((y + 1.0) / STEP - 0.5)) for x, y in holes}
seen, boxes = set(), []
for c in sorted(cells):
    if c in seen:
        continue
    stack, comp = [c], []
    seen.add(c)
    while stack:
        p = stack.pop()
        comp.append(p)
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (p[0] + d[0], p[1] + d[1])
            if q in cells and q not in seen:
                seen.add(q)
                stack.append(q)
    xs = [p[0] for p in comp]
    ys = [p[1] for p in comp]
    boxes.append({"x": [round(-1.0 + min(xs) * STEP, 3), round(-1.0 + (max(xs) + 1) * STEP, 3)],
                  "y": [round(-1.0 + min(ys) * STEP, 3), round(-1.0 + (max(ys) + 1) * STEP, 3)],
                  "cells": len(comp), "area_m2": round(len(comp) * STEP * STEP, 3)})
boxes.sort(key=lambda b: -b["cells"])
res = {"grid_m": STEP, "meshes_used": used, "n_hole_cells": len(holes), "hole_area_m2": round(len(holes) * STEP * STEP, 3),
       "clusters": boxes}
out = WORK / "unreal" / "round4" / "f1" / "json" / (f"ground_holes_r4_{TAG}.json" if TAG else "ground_holes_r4.json")
out.write_text(json.dumps(res, indent=1), encoding="utf-8")
for b in boxes[:40]:
    print("HOLE", b)
print("GROUND_HOLES cells", len(holes), "area", res["hole_area_m2"], "clusters", len(boxes))
