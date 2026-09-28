"""UnrealCheck11 probe (read-only): does ProceduralMeshLibrary.get_section_from_static_mesh read a saved static
mesh's render data in the commandlet, and does it log a Warning when Allow CPU Access is off?  Reads the builder's
already-saved /Game/ShurikenCheck6/HookedCross1/SM_Shuriken_HookedCross; saves nothing.
"""
import json
from pathlib import Path

import unreal

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck11_HookedCrossVerify\probe\probe_render_read.json")
mesh = unreal.load_asset("/Game/ShurikenCheck6/HookedCross1/SM_Shuriken_HookedCross")
rep = {"allow_cpu_access": bool(mesh.get_editor_property("allow_cpu_access"))}
res = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
rep["result_type"] = str(type(res))
rep["result_len"] = len(res) if isinstance(res, (tuple, list)) else None
if isinstance(res, (tuple, list)):
    rep["parts"] = [str(type(p)) + ":" + str(len(p)) for p in res]
    v = res[0]
    rep["v0"] = [v[0].x, v[0].y, v[0].z]
rot = unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0)
f = unreal.MathLibrary.get_forward_vector(rot)
r = unreal.MathLibrary.get_right_vector(rot)
u = unreal.MathLibrary.get_up_vector(rot)
rep["top_cam"] = {"forward": [f.x, f.y, f.z], "right": [r.x, r.y, r.z], "up": [u.x, u.y, u.z]}
OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
unreal.log("UC11_PROBE_DONE")
