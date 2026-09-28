"""TEST ONLY: re-export the shipped heels LODs from a CENTIMETRE scene (Blender headless; the blend is NOT saved).

Why: the shipped FBX is written in metres (FBX UnitScaleFactor 100). Unreal converts metres to cm by putting scale 100 on
the top node, which for a garment is the "root" bone, and keeps the child bones' local translations in metres. The bind
pose in component space is still right (the gates pass), but a Leader Pose / Copy Pose follower on her body (root scale 1)
is drawn 100x too small. FBX_SCALE_ALL does not change that (tested: identical file). The known-good recipe is a cm file:
scene unit scale 0.01, armature + meshes scaled x100 and applied, then the pipeline's own garment settings.

Writes WorkFiles/SnowFlowerHeels/ue/test_export_cm/SK_SnowFlowerHeels*.fbx. Exports/ is not touched; the pipeline's
_validate_scene (unit scale must be 1.0) is bypassed on purpose because this is the experiment that shows what it should
allow.

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend --factory-startup --python Scripts/SnowFlowerHeels/hc_test_export_cm.py
"""
import json
import os
import sys

import bpy

sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline.export_fbx import base_settings  # noqa: E402

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/ue/test_export_cm"
os.makedirs(OUT, exist_ok=True)
NAMES = ("SK_SnowFlowerHeels", "SK_SnowFlowerHeels_LOD1", "SK_SnowFlowerHeels_LOD2")
arm = bpy.data.objects["root"]
meshes = [bpy.data.objects[n] for n in NAMES]
for o in bpy.data.objects:
    o.hide_select = False
    o.hide_set(False)
for c in bpy.data.collections:
    c.hide_select = False
bpy.context.view_layer.update()
scene = bpy.context.scene
scene.unit_settings.scale_length = 0.01
before = {m.name: [list(v) for v in (m.bound_box[0], m.bound_box[6])] for m in meshes}
bpy.ops.object.select_all(action="DESELECT")
arm.scale = (100.0, 100.0, 100.0)
bpy.context.view_layer.update()
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.select_all(action="DESELECT")
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
report = {"scene_scale_length": scene.unit_settings.scale_length, "arm_scale": list(arm.scale),
          "mesh_scales": {m.name: list(m.matrix_world.to_scale()) for m in meshes},
          "bbox_before_local": before, "bbox_after_local": {m.name: [list(m.bound_box[0]), list(m.bound_box[6])] for m in meshes},
          "files": {}}
settings = base_settings("garment")
for m in meshes:
    bpy.ops.object.select_all(action="DESELECT")
    m.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = "%s/%s.fbx" % (OUT, m.name)
    res = bpy.ops.export_scene.fbx(filepath=path, **settings)
    report["files"][m.name] = {"path": path, "result": list(res), "bytes": os.path.getsize(path)}
with open(OUT + "/test_export_cm.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1, default=str)
print("HC_TEST_EXPORT_CM", json.dumps(report)[:2000])
