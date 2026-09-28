"""Dump the Blender side of the Unreal gates from Assets/Armory/ArmoryKit.blend (read-only; nothing is saved):

- the world AABB (metres) of every Assembly instance, keyed by its layout.json index (objects are named <piece>__<nnn>),
- every kit piece's material slot names (the Unreal assignment is by slot name), triangle count and UCX count.

Run: blender -b --factory-startup Assets/Armory/ArmoryKit.blend --python Scripts/armory/unreal/blender_bounds.py
Out: WorkFiles/armory/build/unreal/blender_bounds.json
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ak_common as C  # noqa: E402

layout = C.load_layout()
inst_out = {}
# exterior stage: the SM_AKX_ pieces live in AssemblyExterior / KitExterior
ASM = [o for c in ("Assembly", "AssemblyExterior") if c in bpy.data.collections for o in bpy.data.collections[c].objects]
KIT = [o for c in ("Kit", "KitExterior") if c in bpy.data.collections for o in bpy.data.collections[c].objects]
for o in ASM:
    if "__" not in o.name or o.type != "MESH":
        continue
    piece, n = o.name.rsplit("__", 1)
    n = int(n)
    # exterior stage: Unreal's actor bounds are the mesh's LOCAL box rotated (a loose box for yaws that are not multiples
    # of 90 deg: stepping stones, rocks, moss mounds), so compare with the rotated local bound_box corners (identical to
    # the vertex extremes for the room's 0 / 90 / 180 / 270 deg pieces)
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    bmin = [min(p[i] for p in pts) for i in range(3)]
    bmax = [max(p[i] for p in pts) for i in range(3)]
    lay = layout["instances"][n]
    inst_out[n] = {"piece": piece, "name": o.name, "min": bmin, "max": bmax,
                   "layout_piece_matches": lay["piece"] == piece}
pieces = {}
for o in KIT:
    if o.type != "MESH" or o.name.startswith("UCX_"):
        continue
    pieces[o.name] = {"slots": [s.material.name if s.material else None for s in o.material_slots],
                      "tris": sum(len(p.vertices) - 2 for p in o.data.polygons),
                      "ucx": sorted(c.name for c in o.children if c.name.startswith("UCX_"))}
res = {"blend": bpy.data.filepath, "instances": {str(k): inst_out[k] for k in sorted(inst_out)},
       "n_instances": len(inst_out), "n_layout_instances": len(layout["instances"]),
       "all_pieces_match_layout": all(v["layout_piece_matches"] for v in inst_out.values()), "pieces": pieces}
C.write_json(C.BLENDER_BOUNDS, res)
print("BLENDER_BOUNDS", len(inst_out), "instances,", len(pieces), "pieces, match", res["all_pieces_match_layout"])
