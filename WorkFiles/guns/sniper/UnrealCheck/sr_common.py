"""Shared constants for the SR01 W5 Unreal verification (adapted copy of WorkFiles/guns/smg/UnrealCheck/sm_common.py;
the SMG / AR-01 files stay untouched). Nothing here edits Exports or Scripts.
ROOT is derived from this file's location (the worktree), so the bytes checked are the worktree's Exports.
"""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXP = ROOT / "Exports" / "Guns" / "SR01"
EXP_AR = ROOT / "Exports" / "Guns" / "AR01"
SPEC = ROOT / "WorkFiles" / "guns" / "sniper" / "sr01_spec.json"
SPEC_SMG = ROOT / "WorkFiles" / "guns" / "smg" / "smg_spec.json"   # read only: its AR01_shipped ABP row
GATES = ROOT / "WorkFiles" / "guns" / "sniper" / "gates"
SK = "SK_SR01"
SM = "SM_SR01"
MAG = "SM_SR01_Mag"
SCOPE = "SM_Att_Scope_LongRange"
# the AR-01's verified import in the same project (stage 8, bytes unchanged since): U2b drives both guns
AR_DEST = "/Game/GunCheck/AR01_1009b"
AR_SKEL = AR_DEST + "/SK_AR01_Skeleton"
ABP_NAME = "ABP_Gun_LongGun"


def dest():
    d = os.environ.get("SR_DEST")
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
    return json.loads((EXP / "SK_SR01.skeletal.json").read_text(encoding="utf-8"))


def sidecar_ar():
    return json.loads((EXP_AR / "SK_AR01.skeletal.json").read_text(encoding="utf-8"))


def sidecar(name):
    return json.loads((EXP / f"{name}.sockets.json").read_text(encoding="utf-8"))


def scope_offset_cm():
    """the scope's Mount sits at Rail_Top + mount_offset_slots x slot pitch along +X (sidecar gun.scope; A1)."""
    g = sidecar_sk()["gun"]["scope"]
    return g["mount_offset_slots"] * g["slot_pitch_mm"] / 10.0


def abp_tables():
    """U2b: each gun's angle table in ONE convention (degrees about the bone's Blender axis, Blender sign; the bolt in cm),
    detent array [SAFE, SEMI-slot, AUTO-slot]. SR01 from its shipped sidecar abp_angle_table: a bolt action with two
    detents (SAFE -12, FIRE 0: FIRE fills both fire slots), the bolt ROTATES -60 deg about X before it slides 88 mm, and the
    cheek riser (+12 mm, a sniper-only bone that SK_AR01_Skeleton lacks: the missing-bone probe). AR-01 from the SMG spec's
    AR01_shipped row (see the SMG harness): detents 0 / 16 / 32 = SAFE / AUTO / SEMI; release -10 deg; bolt 103.25 mm."""
    t = sidecar_sk()["abp_angle_table"]
    d = t["selector_deg"]
    sr = {"bolt_cm": t["bolt_mm"][1] / 10.0, "bolt_rot_deg": t["bolt_rotate_deg"][1], "trigger_deg": t["trigger_deg"][1],
          "release_deg": t["release_deg"][0], "selector_deg": [d["SAFE"], d["FIRE"], d["FIRE"]],
          "riser_cm": t["riser_mm"][1] / 10.0}
    spec = json.loads(SPEC_SMG.read_text(encoding="utf-8"))
    ar = spec["bones"]["abp_inputs"]["AR01_shipped"]
    sd = ar["selector_detents_deg"]
    ar01 = {"bolt_cm": 10.325, "bolt_rot_deg": 0.0, "trigger_deg": ar["trigger_pull"][1], "release_deg": -ar["mag_release"][1],
            "selector_deg": [sd[0], sd[2], sd[1]], "riser_cm": 1.2}
    return {"SR01": sr, "AR01": ar01}


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
