"""ROUND 6 OUTSIDE track: re-import the EXPORTED ridge FBX bytes in a fresh Blender process and measure the loop normals
(do the custom 'toward the compound' normals survive the pipeline export?) plus the silhouette numbers.
Run: blender -b --factory-startup --python Scripts/dojo/outside/checks/ox_fbx_normals.py
Out: WorkFiles/dojo/build/round6/build/checks/fbx_ridge_normals.json"""
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "Exports" / "DojoKit" / "Outside"
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "round6" / "build" / "checks" / "fbx_ridge_normals.json"
res = {}
for k in range(1, 5):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(EXP / f"SM_DKX_Ridge{k}.fbx"))
    ob = next(o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("UCX_"))
    me = ob.data
    mw = ob.matrix_world
    R = mw.to_3x3()
    worst_dot, worst_z, n = 1.0, [9.0, -9.0], 0
    for li in range(0, len(me.loops), 7):
        v = me.vertices[me.loops[li].vertex_index].co
        p = mw @ v
        nrm = (R @ me.corner_normals[li].vector).normalized()
        inward = -p.copy()                  # the pivot is the compound centre (CX, CY, 0)
        inward.z = 0.0
        inward.normalize()
        dh = (nrm.x * inward.x + nrm.y * inward.y) / max(1e-9, math.hypot(nrm.x, nrm.y))
        worst_dot = min(worst_dot, dh)
        worst_z = [min(worst_z[0], nrm.z), max(worst_z[1], nrm.z)]
        n += 1
    res[f"SM_DKX_Ridge{k}"] = {"loops_sampled": n, "min_horizontal_cos_to_the_centre": round(worst_dot, 5),
                               "normal_z_range": [round(worst_z[0], 4), round(worst_z[1], 4)],
                               "tris": sum(len(pl.vertices) - 2 for pl in me.polygons)}
    print("FBXN", k, res[f"SM_DKX_Ridge{k}"], flush=True)
res["passed"] = all(v["min_horizontal_cos_to_the_centre"] > 0.999 and 0.18 < v["normal_z_range"][0]
                    and v["normal_z_range"][1] < 0.23 for v in res.values())
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("FBXN passed", res["passed"])
