"""A SECOND Blender process re-imports the shipped FBX and counts what is really in it."""
import hashlib
import json
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
FBX = PROJ / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower_Sheath.fbx"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX))
out = {"fbx": str(FBX), "sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(), "nodes": {}}
for o in bpy.data.objects:
    entry = {"type": o.type, "parent": o.parent.name if o.parent else None}
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        entry["triangles"] = len(o.data.loop_triangles)
        entry["vertices"] = len(o.data.vertices)
        entry["uv_layers"] = [u.name for u in o.data.uv_layers]
        entry["materials"] = [m.name for m in o.data.materials if m]
    out["nodes"][o.name] = entry
(PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealCheck_Sheath" / "blender_fbx_counts.json").write_text(json.dumps(out, indent=2))
print("FBX_COUNTS", json.dumps({k: v.get("triangles") for k, v in out["nodes"].items()}))
