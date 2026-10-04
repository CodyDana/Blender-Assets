"""t2 (2026-10-02): the drum seated in the felt-lined saddle, as measured sections of the EXPORTED meshes.
Imports SM_DKP_Taiko_Drum.fbx and SM_DKP_Taiko_Stand.fbx (LOD0), places the drum at the layout's DRUM_Z, cuts both with
the planes x = 0.465 / 0.48 / 0.52 / 0.56 / 0.575 (near the beam faces, the felt edges and centre) and writes the section segments per
part (barrel, felt, wood) to section_t2.json; draw_section_t2.py draws them.
Run: blender -b --factory-startup --python section_t2.py"""
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
EXP = ROOT / "Exports" / "DojoKit" / "Props" / "taiko"
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t2" / "section_t2.json"
DRUM_Z = 1.25
bpy.ops.wm.read_factory_settings(use_empty=True)
parts = {}
for name in ("Drum", "Stand"):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(EXP / f"SM_DKP_Taiko_{name}.fbx"))
    parts[name] = next(o for o in set(bpy.data.objects) - before if o.type == "MESH" and o.name.endswith("LOD0")
                       and not o.name.startswith("UCX"))
res = {}
for xc in (0.465, 0.48, 0.52, 0.56, 0.575):
    segs = {"barrel": [], "felt": [], "wood": []}
    for name, o in parts.items():
        bm = bmesh.new()
        bm.from_mesh(o.data)
        M = o.matrix_world.copy()
        bm.transform(M)
        if name == "Drum":
            bm.transform(__import__("mathutils").Matrix.Translation((0, 0, DRUM_Z)))
        mats = [m.name if m else "" for m in o.data.materials]
        for f in bm.faces:
            vs = [v.co for v in f.verts]
            pts = []
            for a, b in zip(vs, vs[1:] + vs[:1]):
                da, db = a.x - xc, b.x - xc
                if (da < 0) != (db < 0):
                    t = da / (da - db)
                    pts.append(a + (b - a) * t)
            if len(pts) != 2:
                continue
            m = mats[f.material_index]
            key = "barrel" if name == "Drum" else ("felt" if m.startswith("M_DKP_Taiko_Hide") else "wood")
            if name == "Drum" and min(p.z for p in pts) > DRUM_Z - 0.3:
                continue
            segs[key].append([[round(pts[0].y, 6), round(pts[0].z, 6)], [round(pts[1].y, 6), round(pts[1].z, 6)]])
        bm.free()
    res[f"x{xc:.3f}"] = segs
OUT.write_text(json.dumps(res), encoding="utf-8")
print("SECTION", {k: {kk: len(vv) for kk, vv in v.items()} for k, v in res.items()})
