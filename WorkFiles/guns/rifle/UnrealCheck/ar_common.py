"""Shared constants for the AR-01 stage-8 Unreal verification (adapted copy of WorkFiles/katana/UnrealVerify_Final2/
kv_common.py; the katana files stay untouched). Nothing here edits Exports or Scripts.
ROOT is derived from this file's location (the worktree), so the bytes checked are the worktree's Exports.
"""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXP = ROOT / "Exports" / "Guns" / "AR01"
SPEC = ROOT / "WorkFiles" / "guns" / "rifle" / "rifle_spec.json"
SK = "SK_AR01"
SM = "SM_AR01"
MAG = "SM_AR01_Mag"
CLIPS = ("A_AR01_Fire", "A_AR01_Charge", "A_AR01_Reload", "A_AR01_ReloadEmpty", "A_AR01_Selector")


def dest():
    d = os.environ.get("AR_DEST")
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
    return json.loads((EXP / "SK_AR01.skeletal.json").read_text(encoding="utf-8"))


def sidecar(name):
    return json.loads((EXP / f"{name}.sockets.json").read_text(encoding="utf-8"))


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
