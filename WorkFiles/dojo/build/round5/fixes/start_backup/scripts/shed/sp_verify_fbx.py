"""Round 4: verify the exported shed / pavilion FBX bytes in a FRESH Blender process (the house rule: check the exact
exported files, not the build scene). Per FBX: import it alone into an empty scene, then compare against the layout
json: LOD0 triangle count, UCX hull count and names (UCX_<node>_NN / UCX_<base>_LOD0_NN), the LOD count, material slot
names, and the LOD0 bounds in piece-local metres against the build's bounds (from the kit blend's Kit object).

Run: blender -b --factory-startup --python Scripts/dojo/shed/sp_verify_fbx.py
Out: WorkFiles/dojo/build/shed_pavilion/checks/fbx_verify.json
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
SPW = ROOT / "WorkFiles" / "dojo" / "build" / "shed_pavilion"


def blend_bounds(blend, names):
    out = {}
    with bpy.data.libraries.load(str(blend), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    for o in dst.objects:
        if o is None:
            continue
        vs = [Vector(c) for c in o.bound_box]
        out[o.name] = [min(v[i] for v in vs) for i in range(3)] + [max(v[i] for v in vs) for i in range(3)]
        bpy.data.objects.remove(o, do_unlink=True)
    return out


res, ok_all = {}, True
for asset, blend in (("shed", "DojoShed.blend"), ("pavilion", "DojoPavilion.blend")):
    L = json.loads((SPW / f"layout_{asset}.json").read_text(encoding="utf-8"))
    E = json.loads((SPW / asset / "export_report.json").read_text(encoding="utf-8"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ref_bb = blend_bounds(ROOT / "Assets" / "Dojo" / blend, set(L["pieces"]))
    for name, pc in L["pieces"].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path = ROOT / pc["fbx"]
        bpy.ops.import_scene.fbx(filepath=str(path))
        objs = list(bpy.data.objects)
        meshes = [o for o in objs if o.type == "MESH" and not o.name.startswith("UCX_")]
        ucx = sorted(o.name for o in objs if o.name.startswith("UCX_"))
        lods = sorted(m.name for m in meshes)
        lod0 = next((m for m in meshes if m.name.endswith("_LOD0")), None) or (meshes[0] if meshes else None)
        tris = sum(len(p.vertices) - 2 for p in lod0.data.polygons) if lod0 else 0
        mw = lod0.matrix_world
        vs = [mw @ v.co for v in lod0.data.vertices]
        bb = [min(v[i] for v in vs) for i in range(3)] + [max(v[i] for v in vs) for i in range(3)]
        rb = ref_bb.get(name)
        err = max(abs(a - b) for a, b in zip(bb, rb)) if rb else None
        want_ucx = pc["ucx"]
        ucx_names_ok = all(u.startswith(f"UCX_{lod0.name}_") for u in ucx) if lod0 else False
        slots = sorted({m.name.split(".")[0] for m in lod0.data.materials}) if lod0 else []
        r = {"fbx": pc["fbx"], "lods_in_file": len(meshes), "lods_expected": E[name]["lods"], "lod0": lod0.name,
             "tris": tris, "tris_expected": pc["tris"], "ucx": len(ucx), "ucx_expected": want_ucx,
             "ucx_names_ok": ucx_names_ok, "bounds_err_m": round(err, 5) if err is not None else None,
             "slots": slots, "slots_expected": sorted(pc["slots"])}
        r["ok"] = (r["lods_in_file"] == r["lods_expected"] and tris == pc["tris"] and len(ucx) == want_ucx
                   and ucx_names_ok and err is not None and err < 0.001 and slots == sorted(pc["slots"]))
        ok_all &= r["ok"]
        res[name] = r
        print("VERIFY", name, r["ok"], tris, len(ucx), r["bounds_err_m"], flush=True)
out = {"passed": ok_all, "pieces": res}
(SPW / "checks").mkdir(parents=True, exist_ok=True)
(SPW / "checks" / "fbx_verify.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("FBX_VERIFY passed", ok_all)
