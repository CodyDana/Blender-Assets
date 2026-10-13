"""Shared constants for the SMG01 W5 Unreal verification (adapted copy of WorkFiles/guns/rifle/UnrealCheck/ar_common.py;
the AR-01 files stay untouched). Nothing here edits Exports or Scripts.
ROOT is derived from this file's location (the worktree), so the bytes checked are the worktree's Exports.
"""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXP = ROOT / "Exports" / "Guns" / "SMG01"
EXP_AR = ROOT / "Exports" / "Guns" / "AR01"
SPEC = ROOT / "WorkFiles" / "guns" / "smg" / "smg_spec.json"
GATES = ROOT / "WorkFiles" / "guns" / "smg" / "gates"
SK = "SK_SMG01"
SM = "SM_SMG01"
MAG = "SM_SMG01_Mag"
# the AR-01's verified import in the same project (stage 8, bytes unchanged since): U2b drives both guns
AR_DEST = "/Game/GunCheck/AR01_1009b"
AR_SKEL = AR_DEST + "/SK_AR01_Skeleton"
ABP_NAME = "ABP_Gun_LongGun"


def dest():
    d = os.environ.get("SM_DEST")
    if d:
        return d
    return (HERE / "content_path.txt").read_text(encoding="utf-8").strip()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def all_hashes():
    out = {}
    for p in sorted(EXP.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(EXP)).replace("\\", "/")] = sha(p)
    return out


def sidecar_sk():
    return json.loads((EXP / "SK_SMG01.skeletal.json").read_text(encoding="utf-8"))


def sidecar_ar():
    return json.loads((EXP_AR / "SK_AR01.skeletal.json").read_text(encoding="utf-8"))


def sidecar(name):
    return json.loads((EXP / f"{name}.sockets.json").read_text(encoding="utf-8"))


def abp_tables():
    """U2b: each gun's angle table in ONE convention (degrees about the bone's Blender axis, Blender sign; the bolt in cm),
    detent order SAFE / SEMI / AUTO. SMG01 from its shipped sidecar gun.abp_angle_table; AR-01 from the spec's
    AR01_shipped row (its sidecar predates the table; the bytes stay unchanged): detents 0 / 16 / 32 are SAFE / AUTO / SEMI
    (rifle_clips: safe (0) -> auto (16) -> semi (32)); its catch value + = rot_y(-value) (rifle_clips.basis_from), so the
    catch's release is -10 deg about Y; the bolt travel is the rig report's 103.25 mm."""
    t = sidecar_sk()["gun"]["abp_angle_table"]
    d = t["selector_detents_deg"]
    semi = next(v for k, v in d.items() if k.startswith("SEMI"))
    smg = {"bolt_cm": t["bolt_mm"][1] / 10.0, "trigger_deg": t["trigger_pull"][1], "release_deg": t["mag_release"][1],
           "selector_deg": [d["SAFE"], semi, d["AUTO"]], "stock_fold_deg": sidecar_sk()["gun"]["stock_states"]["folded_deg"]}
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    ar = spec["bones"]["abp_inputs"]["AR01_shipped"]
    sd = ar["selector_detents_deg"]
    ar01 = {"bolt_cm": 10.325, "trigger_deg": ar["trigger_pull"][1], "release_deg": -ar["mag_release"][1],
            "selector_deg": [sd[0], sd[2], sd[1]], "stock_fold_deg": 180.0}
    return {"SMG01": smg, "AR01": ar01}


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
