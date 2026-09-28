"""PlayerBase: read the source rig's joint positions from the player_base COPY (read-only, never saves) and
write them in UE conform-input space (cm, soles at Z=0, face +Y) for comparison with the MetaHuman bones.

    blender -b WorkFiles/MetaHuman/player_base/src_Human_copy.blend --factory-startup \
        --python Scripts/MetaHuman/pb_source_joints.py -- <out_json>
"""
import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline import lock
lock.assert_owner("JinMuWon_v2", "claude")

import json
import math
import os

import bpy

COPY_DIR = os.path.normcase(os.path.abspath(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base"))
if os.path.normcase(os.path.dirname(os.path.abspath(bpy.data.filepath))) != COPY_DIR:
    raise SystemExit(f"Refusing to run on {bpy.data.filepath}: only the player_base copy is allowed")

out_json = sys.argv[sys.argv.index("--") + 1]
GROUND_M = 0.0206514373421669  # the conform FBX was moved down by this (pb_export_report.json)

arm = bpy.data.objects["Armature"]
arm.data.pose_position = "REST"
bpy.context.view_layer.update()


def ue(p):
    # Blender m (face -Y) -> conform-input UE cm (face +Y): x, -y, z - ground
    return [round(p.x * 100.0, 3), round(-p.y * 100.0, 3), round((p.z - GROUND_M) * 100.0, 3)]


names = {}
for b in arm.data.bones:
    names[b.name] = b
want = {}
for side, s in (("L", "l"), ("R", "r")):
    for mpfb, key in (("upperarm01", "upperarm"), ("lowerarm01", "lowerarm"), ("wrist", "hand"),
                      ("upperleg01", "thigh"), ("lowerleg01", "calf"), ("foot", "foot"), ("clavicle", "clavicle"),
                      ("shoulder01", "shoulder01")):
        n = f"{mpfb}.{side}"
        if n in names:
            want[f"{key}_{s}"] = ue(arm.matrix_world @ names[n].head_local)
for n in ("root", "spine05", "spine01", "neck01", "neck03", "head"):
    if n in names:
        want[n] = ue(arm.matrix_world @ names[n].head_local)
    tail_key = n + "_tail"
    if n == "head" and n in names:
        want[tail_key] = ue(arm.matrix_world @ names[n].tail_local)


def d(a, b):
    return math.dist(want[a], want[b])


meas = {}
if "upperarm_l" in want and "upperarm_r" in want:
    meas["shoulder_width_joints"] = round(d("upperarm_l", "upperarm_r"), 2)
if "thigh_l" in want and "thigh_r" in want:
    meas["hip_joint_width"] = round(d("thigh_l", "thigh_r"), 2)
for s in ("l", "r"):
    try:
        meas[f"upperarm_{s}"] = round(d(f"upperarm_{s}", f"lowerarm_{s}"), 2)
        meas[f"forearm_{s}"] = round(d(f"lowerarm_{s}", f"hand_{s}"), 2)
        meas[f"arm_{s}_shoulder_elbow_wrist"] = round(meas[f"upperarm_{s}"] + meas[f"forearm_{s}"], 2)
        meas[f"thigh_{s}"] = round(d(f"thigh_{s}", f"calf_{s}"), 2)
        meas[f"shin_{s}"] = round(d(f"calf_{s}", f"foot_{s}"), 2)
        meas[f"leg_{s}_hip_knee_ankle"] = round(meas[f"thigh_{s}"] + meas[f"shin_{s}"], 2)
    except KeyError as exc:
        meas[f"missing_{s}"] = str(exc)

res = {"source": bpy.data.filepath, "bones_ue_cm": want, "measures": meas,
       "bone_names_available": sorted(n for n in names if any(k in n for k in
                                      ("arm", "leg", "wrist", "foot", "neck", "head", "spine", "clav", "shoulder")))}
with open(out_json, "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1)
print(json.dumps(meas, indent=1))
