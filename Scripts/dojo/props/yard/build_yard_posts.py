"""ROUND 4 FIX f1 (2026-09-29): the SAND-FIELD CORNER POST (its own asset, SM_DKP_Yard_CornerPost), placed at the four
outer corners of the two raked sand fields (the whole judge's delta 9: dojo1_reference1 shows a short dark timber post
at each outer field corner, dojo1_reference2 the far pair; the path-side corners have none in either overview).

Size (measured on dojo1_reference1: about 0.6 m tall, 0.18-0.2 m square against the 13 m field): a 0.18 m square timber
post, +0.60 above grade (0.12 m buried in a granite collar flush with the gravel), chamfered arrises, a shallow pyramid
top; the shared library's TimberAged + Granite (nothing forked). Collision: one box (thin: blocks the pawn, ignores the
camera and visibility, R8).

Run: blender -b --factory-startup --python Scripts/dojo/props/yard/build_yard_posts.py [-- --no-export]
Out: Exports/DojoKit/Props/yard/SM_DKP_Yard_CornerPost.fbx (+ sidecar), WorkFiles/dojo/build/props/yard/
     {layout_yard.json, layout_yard_checks.json, qa_report.json}
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
for p_ in (ROOT / "Scripts", ROOT / "Scripts" / "dojo", ROOT / "Scripts" / "dojo" / "roof",
           ROOT / "Scripts" / "dojo" / "materials"):
    sys.path.insert(0, str(p_))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import kit1_geo as K  # noqa: E402
import dojo_materials as djm  # noqa: E402
from kit_mesh import Piece, cbox, geo_to_object, add_uv1, fix_lod, TA, GR  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "yard"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Props" / "yard"
NAME = "SM_DKP_Yard_CornerPost"
W, H, BURY = 0.18, 0.60, 0.12
FIELDS = [(8.0, 21.0, 2.0, 19.0), (23.0, 36.0, 2.0, 19.0)]     # the ground kit's two sand fields (X0, X1, Y0, Y1)
OFF = 0.13                                                     # post centre outside the field corner (clear of the kerb)


def post():
    p = Piece(NAME, "thin", "Props/Yard",
              "sand-field corner post (dojo1_reference1 / 2): a 0.18 m square dark timber post +0.60 m, chamfered, a "
              "shallow pyramid top, set in a granite collar flush with the gravel; placed at the fields' outer corners",
              pivot=(0.0, 0.0, 0.0))
    p.local = True
    g = p.g
    h = W / 2
    cbox(g, -h, h, -h, h, -BURY, H - 0.04, TA, ch=0.012)
    top = [Vector((-h + 0.012, -h + 0.012, H - 0.04)), Vector((h - 0.012, -h + 0.012, H - 0.04)),
           Vector((h - 0.012, h - 0.012, H - 0.04)), Vector((-h + 0.012, h - 0.012, H - 0.04))]
    apex = Vector((0.0, 0.0, H))
    g.add(top + [apex], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], TA, None)
    cbox(g, -0.15, 0.15, -0.15, 0.15, -0.06, 0.012, GR, ch=0.01)       # granite collar at grade
    p.hull_box(-h, h, -h, h, 0.0, H)
    p.wear = True
    p.extra = {"size": [W, W, H], "buried": BURY}
    return p


def instances():
    out = []
    for (x0, x1, y0, y1), outer_x in zip(FIELDS, (0, 1)):
        xo = (x0 - OFF) if outer_x == 0 else (x1 + OFF)
        for yc in (y0 - OFF, y1 + OFF):
            out.append({"piece": NAME, "loc": [round(xo, 4), round(yc, 4), 0.0], "rot_z": 0.0, "kit": "yard",
                        "folder": "Props/Yard", "collision_class": "thin"})
    return out


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    p = post()
    o, bad = geo_to_object(p, kit)
    djm.bake_wear(o)
    tris = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    OUT.mkdir(parents=True, exist_ok=True)
    add_uv1(o)
    r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25, overlap_method="sat")
    waive = {"uv0_tile_range", "uv_no_overlap"}
    hard = [c for c in r["checks"] if not c["passed"] and c["name"] not in waive]
    (OUT / "qa_report.json").write_text(json.dumps({NAME: {"hard_fails": hard, "tris": tris}}, indent=1, default=str),
                                        encoding="utf-8")
    print("QA yard", len(hard), [c["name"] for c in hard], flush=True)
    exp = {}
    if not hard and "--no-export" not in ARGS:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        ex = export_fbx(str(EXPORT_DIR / f"{NAME}.fbx"), [o], kind="static", sidecar=False)
        exp = {"lods": 1, "tris": tris, "warnings": ex["warnings"]}
    L = {"date": "2026-09-29", "stage": "round 4 fix f1: sand-field corner posts (whole judge delta 9)",
         "units": "m, grey-box world frame (X east, Y north, Z up; Unreal (x*100, -y*100, z*100), yaw = -rot_z)",
         "pieces": {NAME: {"class": "thin", "folder": "Props/Yard", "note": p.note, "ucx": len(p.hulls), "tris": tris,
                           "slots": [m.name for m in o.data.materials], "nanite": False, "kit": "yard",
                           "fbx": f"Exports/DojoKit/Props/yard/{NAME}.fbx", "pivot_world": None, "extra": p.extra}},
         "instances": instances(), "replaces_greybox": [], "export": exp,
         "numbers": {"fields": FIELDS, "offset_outside_corner_m": OFF, "post": [W, W, H]}}
    (OUT / "layout_yard.json").write_text(json.dumps(L, indent=1), encoding="utf-8")
    (OUT / "layout_yard_checks.json").write_text(json.dumps({"walk_routes": {}}, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "Assets" / "Dojo" / "DojoYardPosts.blend"))
    print("YARD done", tris, bad, flush=True)


if __name__ == "__main__":
    main()
