"""Senbon Unreal verifier - independent Blender truth of the SHIPPED FBX bytes (fresh factory Blender, one import per
file).  Per FBX: every object (type, parent), triangles / vertices per mesh, bounds in cm (Blender frame), material
slots, UV layers; every LOD's and the UCX's world vertices (cm) saved as .npy for the offline comparison with Unreal.
Run: blender -b --factory-startup --python sv_blender_truth.py
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

sys.dont_write_bytecode = True
PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
EXP = PROJ / "Exports" / "Senbon"
OUT = PROJ / "WorkFiles" / "senbon" / "UnrealVerify"
TR = OUT / "truth"
TR.mkdir(exist_ok=True)
NAMES = ["SM_Senbon_Needle", "SM_Senbon_Heavy"]
res = {"blender": bpy.app.version_string}
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
            d["bounds_cm"] = [w.min(0).round(5).tolist(), w.max(0).round(5).tolist()]
            d["max_x_vertex_cm"] = w[int(w[:, 0].argmax())].round(5).tolist()
            d["min_x_vertex_cm"] = w[int(w[:, 0].argmin())].round(5).tolist()
            np.save(TR / f"{name}__{o.name}.npy", w)
        elif o.type == "EMPTY":
            d["loc_world_cm"] = [round(v * 100.0, 5) for v in o.matrix_world.translation]
        objs[o.name] = d
    rec["objects"] = objs
    lods = sorted(k for k in objs if objs[k]["type"] == "MESH" and "_LOD" in k and not k.startswith("UCX_"))
    rec["lod_names"] = lods
    rec["lod_tris"] = [objs[k]["tris"] for k in lods]
    rec["lod_verts"] = [objs[k]["verts"] for k in lods]
    rec["ucx"] = sorted(k for k in objs if k.startswith("UCX_"))
    rec["empties"] = sorted(k for k in objs if objs[k]["type"] == "EMPTY")
    res[name] = rec
(OUT / "truth_fbx.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("SV_TRUTH_DONE")
