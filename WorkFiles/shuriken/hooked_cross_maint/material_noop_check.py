"""Proof that the 3.9.1 M_Shuriken_Master change (run-out taper mode, the hooked-cross maintenance) is an exact no-op on
the five frozen forms.  Copied from hooked_cross/material_noop_check.py (the 3.9 proof); OLD is now the 3.9.0 library
as shipped by the hooked-cross build (hooked_cross_maint/scripts_before, identical to regression/post_hooked_cross/scripts).

The GPU bake is not bit-reproducible run to run, so a pack rebuild's maps cannot tell a material change from bake
noise.  This check removes the noise: in ONE process it bakes each frozen form's LOD0 (from the regression snapshot
WorkFiles/shuriken/regression/post_spike_maint/Shuriken.blend, the five frozen forms' baseline) with the 3.9.0 material
(built by the pre-maintenance library copy's own build_material) and with the live 3.9.1 material, on the CPU
(deterministic), and compares the float pixels bit for bit.  Nothing is saved.

    blender -b WorkFiles/shuriken/regression/post_spike_maint/Shuriken.blend --factory-startup \
        --python WorkFiles/shuriken/hooked_cross_maint/material_noop_check.py -- <out.json> [size]
"""
import importlib.util
import json
import sys
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))
sys.path.insert(0, str(PROJ / "Scripts"))

import shuriken_lib  # noqa: E402  (3.9, the live library)
from shuriken_lib import bake as B  # noqa: E402
from shuriken_lib.material import build_material  # noqa: E402

OLD_LIB = PROJ / "WorkFiles" / "shuriken" / "hooked_cross_maint" / "scripts_before" / "shuriken_lib"


def load_old():
    spec = importlib.util.spec_from_file_location("old_shuriken_lib", OLD_LIB / "__init__.py",
                                                  submodule_search_locations=[str(OLD_LIB)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["old_shuriken_lib"] = mod
    spec.loader.exec_module(mod)
    return mod


argv = sys.argv[sys.argv.index("--") + 1:]
out_path = Path(argv[0])
size = int(argv[1]) if len(argv) > 1 else 512
forms = ["SM_Shuriken_FourPoint", "SM_Shuriken_EightPoint", "SM_Shuriken_SquarePlate", "SM_Shuriken_SixPoint",
         "SM_Shuriken_Spike"]
old = load_old()
B._bake_device = lambda scene: (setattr(scene.cycles, "device", "CPU"), "CPU")[1]   # deterministic
saved = bpy.data.materials["M_Shuriken_Master"]
saved.name = "M_Shuriken_Master_saved_in_snapshot"
old_mat = old.material.build_material()           # a fresh "M_Shuriken_Master" from the 3.8.1 library
old_mat.name = "M_Shuriken_Master_3_9_0"
new_mat = build_material()                        # a fresh "M_Shuriken_Master" from the live 3.9 library
result = {"library_new": shuriken_lib.VERSION, "library_old": old.VERSION, "size": size, "device": "CPU",
          "snapshot": str(bpy.data.filepath), "old_library": str(OLD_LIB),
          "nodes": {"old": len(old_mat.node_tree.nodes), "new": len(new_mat.node_tree.nodes)}, "forms": {}}


def bake_all(obj, mat):
    obj.data.materials[0] = mat
    maps = {}
    with B._alone(obj):
        for channel in ("Base Color", "Roughness", "Metallic"):
            img = B._new_image(f"__noop_{channel}", size, data=channel != "Base Color")
            B._bake_channel(obj, mat, channel, img)
            maps[channel] = np.array(img.pixels[:], dtype=np.float32)
            bpy.data.images.remove(img)
        img = B._new_image("__noop_N", size, data=True)
        B._bake(obj, mat, img, "NORMAL", B.NORMAL_SAMPLES, normal_space="TANGENT",
                normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z")
        maps["Normal"] = np.array(img.pixels[:], dtype=np.float32)
        bpy.data.images.remove(img)
    return maps


for mesh in forms:
    obj = bpy.data.objects[f"{mesh}_LOD0"]
    keep = obj.data.materials[0]
    a = bake_all(obj, old_mat)
    b = bake_all(obj, new_mat)
    obj.data.materials[0] = keep
    rec = {}
    for k in a:
        d = np.abs(a[k].astype(np.float64) - b[k].astype(np.float64))
        rec[k] = {"bitwise_identical": bool(np.array_equal(a[k], b[k])), "max_abs": float(d.max()),
                  "values_differing": int((d > 0).sum()), "mean": float(a[k].mean())}
    result["forms"][mesh] = rec
    print("NOOP", mesh, {k: v["bitwise_identical"] for k, v in rec.items()}, flush=True)
result["all_bitwise_identical"] = all(v["bitwise_identical"] for r in result["forms"].values() for v in r.values())
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("NOOP_ALL", result["all_bitwise_identical"])
