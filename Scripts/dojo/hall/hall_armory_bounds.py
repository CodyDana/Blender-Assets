"""HALL + ARMORY round (2026-10-01), DojoLab stage, Blender side (headless): refresh
WorkFiles/dojo/build/showcase/blender_bounds.json for the composed layout_showcase.json (the Unreal level gate compares
every placed actor with these boxes).

- Piece meta (bbox_lod0 / bbox_all_lods / tris / slots / UCX): kept from the existing file for every piece it already
  lists, EXCEPT the pieces this round built or rebuilt (layout piece 'hall_armory' tag; incl. the rebuilt
  SM_DGB_Boundary_1v1), which are imported fresh from their exported FBX (compose_showcase.import_piece's recipe).
- Instance boxes: recomputed for EVERY layout instance from the meta and the instance matrix (compose_showcase.matrix_of:
  T @ R_xyz @ S), so moved instances get their new boxes. Unchanged instances are cross-checked against the old file
  (max deviation reported; must be <= 1e-4 m).

Run: blender -b --factory-startup --python Scripts/dojo/hall/hall_armory_bounds.py
"""
import json
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
SC = ROOT / "WorkFiles" / "dojo" / "build" / "showcase"
OUT_REP = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "ue" / "bounds_report.json"
# FIX round (2026-10-01): extra pieces to re-read from their FBX (a rebuilt existing piece, e.g. SM_DKH_RoofLower_Front)
# and the report path:  blender ... --python hall_armory_bounds.py -- [--report <json>] [<piece> ...]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--report" in ARGS:
    k = ARGS.index("--report")
    OUT_REP = Path(ARGS[k + 1])
    ARGS = ARGS[:k] + ARGS[k + 2:]
EXTRA_FRESH = set(ARGS)


def strip(name):
    return re.sub(r"\.\d{3}$", "", name)


def world_bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def union(boxes):
    return ([min(b[0][i] for b in boxes) for i in range(3)], [max(b[1][i] for b in boxes) for i in range(3)])


def rnd(v, n=5):
    return [round(float(x), n) for x in v]


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def import_piece(piece, fbx):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH" and not o.name.startswith("UCX_")]
    lods = sorted([o for o in meshes if re.search(r"_LOD\d+$", strip(o.name))], key=lambda o: o.name)
    main = next((o for o in meshes if strip(o.name) == piece), None)
    if lods:
        main = next(o for o in lods if strip(o.name).endswith("_LOD0"))
    if main is None:
        raise RuntimeError(f"{fbx}: no mesh named {piece}")
    bpy.context.view_layer.update()
    lod_boxes = [world_bbox(o) for o in (lods or [main])]
    ucx = [o for o in new if o.name.startswith("UCX_")]
    ub = union([world_bbox(o) for o in ucx]) if ucx else None
    meta = {"slots": [strip(s.material.name) if s.material else None for s in main.material_slots],
            "tris": tri_count(main), "lod_tris": [tri_count(o) for o in (lods or [main])], "lods": len(lods or [main]),
            "ucx": sorted(strip(o.name) for o in ucx), "n_ucx": len(ucx),
            "vcol": [a.name for a in main.data.color_attributes],
            "bbox_lod0": [rnd(lod_boxes[0][0]), rnd(lod_boxes[0][1])],
            "bbox_all_lods": [rnd(union(lod_boxes)[0]), rnd(union(lod_boxes)[1])],
            "ucx_bbox": [rnd(ub[0]), rnd(ub[1])] if ub else None}
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return meta


def matrix_of(i):
    return (Matrix.Translation(Vector(i["loc"])) @ Euler([math.radians(a) for a in i["rot_xyz_deg"]], "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal(Vector(list(i["scale"]) + [1.0])))


def box(mw, b):
    w = [mw @ Vector((x, y, z)) for x in (b[0][0], b[1][0]) for y in (b[0][1], b[1][1]) for z in (b[0][2], b[1][2])]
    return rnd([min(p[k] for p in w) for k in range(3)]), rnd([max(p[k] for p in w) for k in range(3)])


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    L = json.loads((SC / "layout_showcase.json").read_text(encoding="utf-8"))
    old = json.loads((SC / "blender_bounds.json").read_text(encoding="utf-8"))
    meta = dict(old["pieces"])
    fresh = sorted(p for p, v in L["pieces"].items() if v.get("hall_armory") or p not in meta or p in EXTRA_FRESH)
    rep = {"fresh_pieces": {}, "warnings": []}
    for p in fresh:
        m = import_piece(p, L["pieces"][p]["fbx"])
        if p in meta:
            rep["fresh_pieces"][p] = {"old_bbox_lod0": meta[p]["bbox_lod0"], "new_bbox_lod0": m["bbox_lod0"]}
        else:
            rep["fresh_pieces"][p] = {"new_bbox_lod0": m["bbox_lod0"]}
        if m["slots"] != L["pieces"][p].get("slots", m["slots"]):
            rep["warnings"].append(f"{p}: slots {m['slots']} != layout {L['pieces'][p].get('slots')}")
        meta[p] = m
    inst, dev, n_cmp = {}, 0.0, 0
    for n, i in enumerate(L["instances"]):
        mw = matrix_of(i)
        b0 = box(mw, meta[i["piece"]]["bbox_lod0"])
        ba = box(mw, meta[i["piece"]]["bbox_all_lods"])
        e = {"piece": i["piece"], "min": b0[0], "max": b0[1], "min_all_lods": ba[0], "max_all_lods": ba[1]}
        if i.get("removed"):
            e["removed"] = i["removed"]
        inst[str(n)] = e
        o = old["instances"].get(str(n))
        unchanged = (o is not None and o["piece"] == i["piece"] and i["piece"] not in fresh
                     and n not in L["hall_armory_round"]["moved"])
        if unchanged:
            d = max(abs(a - b) for a, b in zip(o["min"] + o["max"], e["min"] + e["max"]))
            dev = max(dev, d)
            n_cmp += 1
    res = {"blend": "computed from the exported FBX + layout_showcase.json (hall_armory_bounds.py, 2026-10-01)",
           "instances": inst, "n_instances": len(inst), "pieces": meta}
    (SC / "blender_bounds.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    rep.update({"n_instances": len(inst), "n_unchanged_compared": n_cmp, "max_dev_unchanged_m": round(dev, 6),
                "passed": dev <= 1e-4 and not rep["warnings"]})
    OUT_REP.parent.mkdir(parents=True, exist_ok=True)
    OUT_REP.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("HA_BOUNDS", json.dumps({k: v for k, v in rep.items() if k != "fresh_pieces"}), flush=True)


main()
