"""Fresh-process check of the exported stair-path FBX bytes (track 9): re-import every
Exports/DojoKit/StoneKit/SM_DKT_Stair_*.fbx into an empty scene, and record per file: render meshes (LOD names),
UCX hulls keyed to the render node name, material slots, triangle counts and the LOD0 bounding box, against the
catalog. Blender-side only (no Unreal in this run).
Run: blender -b --factory-startup --python Scripts/dojo/stonekit/verify_stairs_fbx.py
Out: WorkFiles/dojo/build/stonekit/stairs/fbx_verify.json
"""
import json
import re
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "Exports" / "DojoKit" / "StoneKit"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
cat = json.loads((WORK / "kit_catalog.json").read_text(encoding="utf-8"))["pieces"]
out, bad = {}, []
ALL = "--all" in sys.argv          # f1: every SM_DKT_* file of both tracks -> stonekit/fbx_verify_f1.json
for fbx in sorted(EXP.glob("SM_DKT_*.fbx" if ALL else "SM_DKT_Stair_*.fbx")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    base = fbx.stem
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    render = [o for o in meshes if not o.name.startswith("UCX_")]
    ucx = [o for o in meshes if o.name.startswith("UCX_")]
    lod0 = next((o for o in render if o.name in (base, f"{base}_LOD0")), None)
    key_ok = all(re.match(rf"^UCX_{re.escape(lod0.name if lod0 else base)}_\d\d$", u.name) for u in ucx)
    rec = {"render_nodes": sorted(o.name for o in render), "ucx": len(ucx), "ucx_keyed_to_render_node": key_ok,
           "tris": {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in render},
           "slots": sorted({m.name for o in render for m in o.data.materials if m}),
           "uv_layers": sorted({uv.name for o in render for uv in o.data.uv_layers}),
           "has_wear_colours": any(len(o.data.color_attributes) > 0 for o in render)}
    if lod0 is not None:
        ws = [lod0.matrix_world @ v.co for v in lod0.data.vertices]
        size = [round(max(p[i] for p in ws) - min(p[i] for p in ws), 3) for i in range(3)]
        rec["lod0_size_m"] = size
        want = cat.get(base, {}).get("size_m")
        if want:
            rec["size_matches_catalog"] = all(abs(a - b) < 0.01 for a, b in zip(size, want))
    c = cat.get(base, {})
    rec["expected_lods"] = 1 if c.get("nanite") else 3
    rec["ok"] = (lod0 is not None and key_ok and len(ucx) == len(c.get("ucx", [])) * 1
                 and len(render) == rec["expected_lods"] and rec.get("size_matches_catalog", False))
    if not rec["ok"]:
        bad.append(base)
    out[base] = rec
    print("FBX", base, "ok" if rec["ok"] else "CHECK", rec["render_nodes"], "ucx", rec["ucx"], flush=True)
res = {"files": len(out), "not_ok": bad, "pieces": out}
(WORK / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "fbx_verify_f1.json") if ALL
 else WORK / "stairs" / "fbx_verify.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("FBX VERIFY", len(out), "files,", len(bad), "to check:", bad, flush=True)
