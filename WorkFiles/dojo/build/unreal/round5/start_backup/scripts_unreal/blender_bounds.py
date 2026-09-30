"""Dump the Blender side of the DojoLab gates from Assets/Dojo/DojoGreybox.blend (read-only; nothing is saved):
the world AABB (metres) of every Assembly instance keyed by its layout.json index (objects are <piece>__<nnn>), and every
kit piece's material slot names, triangle count and UCX hull names.

Run: blender -b --factory-startup Assets/Dojo/DojoGreybox.blend --python Scripts/dojo/unreal/blender_bounds.py
Out: WorkFiles/dojo/build/unreal/blender_bounds.json
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dj_common as C  # noqa: E402

layout = C.load_layout()
inst_out = {}
for o in bpy.data.collections["Assembly"].objects:
    if "__" not in o.name or o.type != "MESH":
        continue
    piece, n = o.name.rsplit("__", 1)
    n = int(n)
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    inst_out[n] = {"piece": piece, "min": [min(p[i] for p in pts) for i in range(3)],
                   "max": [max(p[i] for p in pts) for i in range(3)],
                   "layout_piece_matches": layout["instances"][n]["piece"] == piece}
pieces = {}
for o in bpy.data.collections["Kit"].objects:
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
