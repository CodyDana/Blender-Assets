"""TEST ONLY: re-export the shipped heels LODs with apply_scale_options=FBX_SCALE_ALL (Blender headless, blend NOT saved).

The shipped SK_SnowFlowerHeels.fbx (export_fbx kind="garment", FBX_SCALE_UNITS) imports into UE 5.8 with a root bone of
local scale 100 and child translations in metres. Component-space bind positions are right (so the gates pass), but a
Leader Pose / Copy Pose follower on her body (root scale 1) is shrunk 100x. This writes the same objects through the same
pipeline call with only that one override, to WorkFiles/SnowFlowerHeels/ue/test_export/, so the Unreal check can prove the
fix. Nothing under Exports/ is touched.

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend --factory-startup --python Scripts/SnowFlowerHeels/hc_test_export_scaleall.py
"""
import json
import os
import sys

sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline.export_fbx import export_fbx  # noqa: E402

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/ue/test_export"
os.makedirs(OUT, exist_ok=True)
report = {}
for name in ("SK_SnowFlowerHeels", "SK_SnowFlowerHeels_LOD1", "SK_SnowFlowerHeels_LOD2"):
    r = export_fbx(OUT + "/" + name + ".fbx", [name], kind="garment", sidecar=False, apply_scale_options="FBX_SCALE_ALL")
    report[name] = {"filepath": r["filepath"], "warnings": r["warnings"],
                    "apply_scale_options": r["settings"]["apply_scale_options"]}
with open(OUT + "/test_export.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1, default=str)
print("HC_TEST_EXPORT", json.dumps(report))
