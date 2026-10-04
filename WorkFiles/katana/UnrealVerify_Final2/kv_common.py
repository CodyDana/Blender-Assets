"""Shared constants for the INDEPENDENT Unreal + fit verifier of SM_Katana + SM_Katana_Saya (role: unreal-fit verifier).
Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Final2 (read-only model). Nothing here edits Exports or Scripts.
"""
import hashlib
import os
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "katana" / "UnrealVerify_Final2"
EXP = PROJ / "Exports" / "Katana"
MESHES = ("SM_Katana", "SM_Katana_Saya")
SHIPPED_SHA = {
    "SM_Katana": "114c79f43f6654669c06f0684bb52a0a5aff5cae3799c1de2eab4a771e420cf7",
    "SM_Katana_Saya": "d97bd9b74b30d36b0e3ff5780f3a85da38040df58c4c352d1d70207dae8d63de",
}


def dest():
    d = os.environ.get("KV_DEST")
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


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}
