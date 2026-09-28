"""Independent Blender truth of the SHIPPED FBX bytes (fresh factory Blender, one import per file).

For each of the four FBX: every object (type, name, parent), per-mesh triangle and vertex counts, world bounds in cm,
and LOD0 / UCX vertex arrays (cm, Blender frame) for the offline comparison with Unreal's read-back.
Run: blender -b --factory-startup --python uv_blender_truth.py
"""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
EXP = PROJ / "Exports" / "Flashbang"
OUT = PROJ / "WorkFiles" / "flashbang" / "UnrealVerify_claude"
NAMES = ["SM_Flashbang", "SM_Flashbang_Body", "SM_Flashbang_PullRing", "SM_Flashbang_Lever"]
res = {}
for name in NAMES:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    fbx = EXP / f"{name}.fbx"
    rec = {"sha256": hashlib.sha256(fbx.read_bytes()).hexdigest()}
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    bpy.context.view_layer.update()
    objs = {}
    for o in bpy.data.objects:
        d = {"type": o.type, "parent": o.parent.name if o.parent else None}
        if o.type == "MESH":
            me = o.data
            mw = np.array(o.matrix_world)
            co = np.empty(len(me.vertices) * 3, np.float64)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            w = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3] * 100.0  # cm
            d["verts"] = len(me.vertices)
            d["tris"] = int(sum(len(p.vertices) - 2 for p in me.polygons))
            d["polys"] = len(me.polygons)
            d["materials"] = [s.material.name if s.material else None for s in o.material_slots]
            d["uv_layers"] = [u.name for u in me.uv_layers]
            d["bounds_cm"] = [w.min(0).round(4).tolist(), w.max(0).round(4).tolist()]
            d["loose_verts"] = int(len(me.vertices) - len({i for p in me.polygons for i in p.vertices}))
            if o.name.endswith("_LOD0") or o.name.startswith("UCX_"):
                np.save(OUT / f"truth_{name}__{o.name}.npy", w)
        elif o.type == "EMPTY":
            d["loc_world_cm"] = [round(v * 100.0, 4) for v in o.matrix_world.translation]
        objs[o.name] = d
    rec["objects"] = objs
    rec["lod_tris"] = [objs[k]["tris"] for k in sorted(objs) if "_LOD" in k and objs[k]["type"] == "MESH"
                       and not k.startswith("UCX_")]
    rec["ucx"] = sorted(k for k in objs if k.startswith("UCX_"))
    res[name] = rec
(OUT / "truth_fbx.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("UV_TRUTH_DONE")
