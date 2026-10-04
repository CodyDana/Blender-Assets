"""A SECOND Blender process re-imports the shipped saya FBX and records what is really in it (triangles per LOD,
LOD0 bounds in cm and the bounds-sphere radius the screen sizes use)."""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
FBX = PROJ / "Exports" / "Katana" / "SM_Katana_Saya.fbx"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX))
out = {"fbx": str(FBX), "sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(), "nodes": {}}
allv = []
for o in bpy.data.objects:
    entry = {"type": o.type, "parent": o.parent.name if o.parent else None}
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        entry["triangles"] = len(o.data.loop_triangles)
        entry["vertices"] = len(o.data.vertices)
        entry["uv_layers"] = [u.name for u in o.data.uv_layers]
        entry["materials"] = [m.name for m in o.data.materials if m]
        if not o.name.startswith("UCX_"):
            V = np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]) * 100.0
            entry["bbox_min_cm"] = V.min(axis=0).round(4).tolist()
            entry["bbox_max_cm"] = V.max(axis=0).round(4).tolist()
            if "LOD0" in o.name:
                c = 0.5 * (V.min(axis=0) + V.max(axis=0))
                out["lod0_size_cm"] = (V.max(axis=0) - V.min(axis=0)).round(4).tolist()
                out["lod0_radius_from_box_centre_cm"] = float(np.linalg.norm(V - c, axis=1).max())
                out["lod0_box_half_diagonal_cm"] = float(np.linalg.norm(V.max(axis=0) - c))
    out["nodes"][o.name] = entry
(PROJ / "WorkFiles" / "katana" / "UnrealCheck_Saya" / "blender_fbx_counts.json").write_text(json.dumps(out, indent=2))
print("FBX_COUNTS", json.dumps({k: v.get("triangles") for k, v in out["nodes"].items()}))
