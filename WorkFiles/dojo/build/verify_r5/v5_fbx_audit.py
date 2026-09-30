"""VERIFY r5 (independent verifier), Blender side, read-only: re-import every exported FBX the showcase layout names and
every SM_*.fbx in the dojo export folders; record UCX hulls (names, count), LODs, triangles per LOD, material slots and
local boxes (LOD0 and all-LOD union). Also opens nothing else and saves nothing.
Run: blender -b --factory-startup --python WorkFiles/dojo/build/verify_r5/v5_fbx_audit.py
Out: WorkFiles/dojo/build/verify_r5/fbx_audit.json
"""
import json
import re
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "verify_r5"
L = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text(encoding="utf-8"))
EXP = ROOT / "Exports" / "DojoKit"


def strip(n):
    return re.sub(r"\.\d{3}$", "", n)


def box(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]


def vbox(objs):
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    return [[round(min(p[i] for p in pts), 5) for i in range(3)], [round(max(p[i] for p in pts), 5) for i in range(3)]]


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def audit(fbx, piece):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    objs = list(bpy.data.objects)
    ucx = sorted(strip(o.name) for o in objs if o.name.startswith("UCX_"))
    meshes = [o for o in objs if o.type == "MESH" and not o.name.startswith("UCX_")]
    lods = sorted([o for o in meshes if re.search(r"_LOD\d+$", strip(o.name))], key=lambda o: strip(o.name))
    main = lods or [o for o in meshes if strip(o.name) == piece]
    base = piece + ("_LOD0" if lods else "")
    ucx_ok = all(re.fullmatch(re.escape("UCX_" + base) + r"_\d\d", u) for u in ucx)
    empties = sorted(strip(o.name) for o in objs if o.type == "EMPTY")
    lod0 = main[0] if main else None
    return {"fbx": str(fbx), "ucx": ucx, "n_ucx": len(ucx), "ucx_names_ok": ucx_ok, "lods": len(main),
            "lod_names": [strip(o.name) for o in main], "tris": [tris(o) for o in main],
            "slots": [strip(s.material.name) if s.material else None for s in lod0.material_slots] if lod0 else [],
            "lod0_vbox": vbox([lod0]) if lod0 else None, "all_lod_vbox": vbox(main) if main else None,
            "other_meshes": sorted(strip(o.name) for o in meshes if o not in main), "empties": empties}


res = {"pieces": {}, "unlisted_exports": []}
for piece, p in sorted(L["pieces"].items()):
    f = Path(p["fbx"])
    if not f.exists():
        res["pieces"][piece] = {"error": f"missing {f}"}
        continue
    try:
        res["pieces"][piece] = audit(f, piece)
    except Exception as e:  # noqa: BLE001
        res["pieces"][piece] = {"error": repr(e)}
listed = {Path(p["fbx"]).resolve() for p in L["pieces"].values()}
for f in sorted(EXP.rglob("SM_*.fbx")):
    if f.resolve() not in listed:
        res["unlisted_exports"].append(str(f.relative_to(EXP)))
res["n_pieces"] = len(res["pieces"])
res["n_errors"] = sum(1 for v in res["pieces"].values() if "error" in v)
(OUT / "fbx_audit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("FBX_AUDIT_DONE", res["n_pieces"], "errors", res["n_errors"], "unlisted", len(res["unlisted_exports"]))

