"""Shared constants for the INDEPENDENT Unreal + fit verifier of SM_Katana + SM_Katana_Saya (role: unreal-fit verifier).
Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Final (read-only model). Nothing here edits Exports or Scripts.
"""
import hashlib
import os
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "katana" / "UnrealVerify_Final"
EXP = PROJ / "Exports" / "Katana"
MESHES = ("SM_Katana", "SM_Katana_Saya")
SHIPPED_SHA = {
    "SM_Katana": "4c27cd00bec0e80502ff4e314d5f7f121f2640a2ffca5607708e4cea79d0c818",
    "SM_Katana_Saya": "841e5d3bd389aacdf9ab3765ec5584fa2e5279d6fe1adfe63217fe2a961c87de",
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
