"""Check heel_pose.json with Unreal's own math (CharacterLab commandlet, -nullrhi, saves nothing).

    powershell -ExecutionPolicy Bypass -File Scripts/garments/run_ue_characterlab.ps1 \
        -Script Scripts/SnowFlowerHeels/ue_verify_heel_pose.py -Tag heels_pose_verify

Reads the female body mesh's reference skeleton from the asset (read only), replaces the local transforms of the
posed bones (pelvis, thigh/calf/foot/ball l+r) with heel_pose.json's ``local_posed`` values, composes component space
with unreal.Transform, and checks:

* the posed ankle (foot_*) lands where Blender put it (``posed_ankle_head_m``, mirrored to cm),
* the shoe's heel-tip and ball-sole floor points (bone-local constants) land on the floor (z = 0),
* the barefoot contacts, composed from the REST skeleton, are on the floor too,
* Unreal's Quat->Rotator agrees with the rotators the Blender script wrote.

Writes WorkFiles/SnowFlowerHeels/ue_verify_heel_pose.json.
"""
import json
import math
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
POSE = ROOT + "/WorkFiles/SnowFlowerHeels/heel_pose.json"
OUT = ROOT + "/WorkFiles/SnowFlowerHeels/ue_verify_heel_pose.json"
BODY = "/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh"
report = {"status": "failed", "errors": []}


def tf(location, xyzw):
    x, y, z, w = xyzw
    return unreal.Transform(unreal.Vector(*location), unreal.Quat(x, y, z, w).rotator(), unreal.Vector(1, 1, 1))


def vec(v):
    return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


try:
    pose = json.load(open(POSE, encoding="utf-8"))
    mesh = unreal.load_asset(BODY)
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    if hasattr(comp, "set_skinned_asset_and_update"):
        comp.set_skinned_asset_and_update(mesh)
    else:
        comp.set_skeletal_mesh_asset(mesh)
    local_rest, parent = {}, {}
    for index in range(comp.get_num_bones()):
        name = str(comp.get_bone_name(index))
        p = str(comp.get_parent_bone(name))
        parent[name] = None if p in ("None", "") else p
        local_rest[name] = comp.get_ref_pose_transform(index)
    local_posed = dict(local_rest)
    for name, entry in pose["ue_bones"].items():
        lp = entry["local_posed"]
        local_posed[name] = tf(lp["location_cm"], lp["rotation_xyzw"])

    def compose(locals_):
        cache = {}

        def cs(name):
            if name not in cache:
                cache[name] = locals_[name] if parent[name] is None else locals_[name].multiply(cs(parent[name]))
            return cache[name]
        return cs

    cs_rest, cs_pose = compose(local_rest), compose(local_posed)
    checks = {}
    worst = 0.0
    for side, contacts in pose["ue_contacts_local_cm"].items():
        foot, ball = "foot_" + side, "ball_" + side
        ankle_bl = pose["solve"]["per_foot"][side]["posed_ankle_head_m"]
        ankle_expected = unreal.Vector(ankle_bl[0] * 100.0, -ankle_bl[1] * 100.0, ankle_bl[2] * 100.0)
        ankle_ue = cs_pose(foot).translation
        heel_tip = cs_pose(foot).transform_location(unreal.Vector(*contacts["shoe_heel_tip_floor_in_foot_cm"]))
        ball_sole = cs_pose(ball).transform_location(unreal.Vector(*contacts["shoe_ball_sole_floor_in_ball_cm"]))
        ball_sole_f = cs_pose(foot).transform_location(unreal.Vector(*contacts["shoe_ball_sole_floor_in_foot_cm"]))
        bare_heel = cs_rest(foot).transform_location(unreal.Vector(*contacts["barefoot_heel_contact_in_foot_cm"]))
        bare_ball = cs_rest(ball).transform_location(unreal.Vector(*contacts["barefoot_ball_contact_in_ball_cm"]))
        pelvis_rest, pelvis_pose = cs_rest("pelvis").translation, cs_pose("pelvis").translation
        entry = {
            "ankle_ue_cm": vec(ankle_ue), "ankle_blender_cm": vec(ankle_expected),
            "ankle_delta_mm": round((ankle_ue - ankle_expected).length() * 10.0, 4),
            "shoe_heel_tip_cm": vec(heel_tip), "shoe_ball_sole_cm (ball local)": vec(ball_sole),
            "shoe_ball_sole_cm (foot local)": vec(ball_sole_f),
            "barefoot_heel_contact_rest_cm": vec(bare_heel), "barefoot_ball_contact_rest_cm": vec(bare_ball),
            "pelvis_lift_cm": round(pelvis_pose.z - pelvis_rest.z, 4),
        }
        worst = max(worst, entry["ankle_delta_mm"], abs(heel_tip.z) * 10.0, abs(ball_sole.z) * 10.0)
        checks[side] = entry
    rot = {}
    rot_worst = 0.0
    for name, entry in pose["ue_bones"].items():
        q = entry["local_posed"]["rotation_xyzw"]
        r = unreal.Quat(*q).rotator()
        mine = entry["local_posed"]["rotator"]
        qa = unreal.Rotator(roll=mine["roll"], pitch=mine["pitch"], yaw=mine["yaw"]).quaternion()
        qb = unreal.Quat(*q)
        # robust small-angle distance (acos near 1 turns 1e-6 quaternion rounding into ~0.1 deg)
        sign = 1.0 if (qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w) >= 0.0 else -1.0
        chord = math.sqrt((qa.x - sign * qb.x) ** 2 + (qa.y - sign * qb.y) ** 2 + (qa.z - sign * qb.z) ** 2
                          + (qa.w - sign * qb.w) ** 2)
        angle = math.degrees(4.0 * math.asin(min(1.0, chord / 2.0)))
        rot[name] = {"ue_rotator": [round(r.roll, 4), round(r.pitch, 4), round(r.yaw, 4)],
                     "blender_rotator": [mine["roll"], mine["pitch"], mine["yaw"]], "same_rotation_within_deg": round(angle, 5)}
        rot_worst = max(rot_worst, angle)
    report.update({"checks": checks, "rotators": rot, "worst_position_error_mm": round(worst, 4),
                   "worst_rotator_mismatch_deg": round(rot_worst, 5),
                   "pass": worst < 0.5 and rot_worst < 0.01, "status": "ok"})
except Exception:  # noqa: BLE001
    report["errors"].append(traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    unreal.log("[heels] verify status " + report["status"])
