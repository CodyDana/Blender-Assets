"""Compare the heels mesh's reference pose with her body's: translation, rotation AND scale per bone (commandlet, saves nothing).
Writes WorkFiles/SnowFlowerHeels/ue/refpose_<RUN>.json."""
import json
import math
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
rep = {"status": "failed", "errors": []}


def locals_of(mesh):
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh)
    out = {}
    for i in range(comp.get_num_bones()):
        n = str(comp.get_bone_name(i))
        t = comp.get_ref_pose_transform(i)
        out[n] = t
    return out


try:
    heels = locals_of(unreal.load_asset("/Game/HeelsCheck/%s/SK_SnowFlowerHeels" % RUN))
    body = locals_of(unreal.load_asset("/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh"))
    rows = []
    for n, tb in body.items():
        th = heels.get(n)
        if th is None:
            rows.append({"bone": n, "missing": True})
            continue
        qa, qb = th.rotation, tb.rotation
        dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
        rows.append({"bone": n, "dt_cm": (th.translation - tb.translation).length(),
                     "drot_deg": math.degrees(2 * math.acos(min(1.0, dot))),
                     "scale_heels": [th.scale3d.x, th.scale3d.y, th.scale3d.z], "scale_body": [tb.scale3d.x, tb.scale3d.y, tb.scale3d.z]})
    rows.sort(key=lambda r: -(r.get("drot_deg", 0) + r.get("dt_cm", 0) + abs(r.get("scale_heels", [1])[0] - 1)))
    rep["worst"] = rows[:15]
    rep["key"] = [r for r in rows if r["bone"] in ("root", "pelvis", "foot_l", "ball_l", "calf_twist_01_l", "foot_r")]
    rep["max_drot_deg"] = max(r.get("drot_deg", 0) for r in rows)
    rep["max_dt_cm"] = max(r.get("dt_cm", 0) for r in rows)
    rep["scales_not_one"] = [r["bone"] for r in rows if "scale_heels" in r and any(abs(s - 1) > 1e-4 for s in r["scale_heels"])][:20]
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/refpose_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
