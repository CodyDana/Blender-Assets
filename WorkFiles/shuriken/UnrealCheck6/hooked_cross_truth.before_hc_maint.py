"""Blender-side truth for the hooked cross's Unreal handedness gate (library 3.9).  READ ONLY, never saves.

    blender.exe -b --factory-startup --python-exit-code 3 --python hooked_cross_truth.py

Re-imports the SHIPPED Exports/Shuriken/SM_Shuriken_HookedCross.fbx (these exact bytes: SHA-256 recorded) in an
empty factory-startup scene, bakes each node's world matrix into a copy of its mesh (the FBX importer puts the unit
scale on the object), and
  * dumps LOD0's vertex positions (Blender metres) - uc6_common.handedness_check compares Unreal's saved LOD0 with
    them through the importer's documented axis conversion (and, as a negative control, with their mirror);
  * runs shuriken_lib.outline_plate.handedness_gate on every re-imported LOD (the +Z face of what the FBX carries)
    and the negative control (the same outline mirrored must fail).
Writes hooked_cross_truth.json next to this file.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck6"
sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))
sys.path.insert(0, str(PROJ / "Scripts"))

import build_hooked_cross as B  # noqa: E402
from shuriken_lib.outline_plate import handedness_gate, handedness_negative_control  # noqa: E402

MESH = "SM_Shuriken_HookedCross"
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    o = B.SPEC.outline()
    out = {"fbx": str(FBX), "fbx_sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(),
           "blender": bpy.app.version_string, "nodes": sorted(ob.name for ob in bpy.data.objects), "lods": {}}
    for i in range(3):
        src = bpy.data.objects[f"{MESH}_LOD{i}"]
        mesh = src.data.copy()
        mesh.transform(src.matrix_world)
        baked = bpy.data.objects.new(f"TRUTH_LOD{i}", mesh)
        bpy.context.scene.collection.objects.link(baked)
        bpy.context.view_layer.update()
        gate = handedness_gate(baked, o)
        rec = {"passed": gate["passed"], "checks": gate["checks"], "arms": gate["arms"],
               "matrix_world_determinant": round(src.matrix_world.to_3x3().determinant(), 9)}
        if i == 0:
            out["lod0_vertices_m"] = [[round(c, 9) for c in v.co] for v in mesh.vertices]
            rec["negative_control"] = handedness_negative_control(baked, o)
        out["lods"][f"LOD{i}"] = rec
    out["handedness_gate_passed"] = all(r["passed"] and r["matrix_world_determinant"] > 0.0 for r in out["lods"].values()) \
        and out["lods"]["LOD0"]["negative_control"]["caught"]
    (HERE / "hooked_cross_truth.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("HOOKED_CROSS_TRUTH_DONE", out["handedness_gate_passed"])


main()
