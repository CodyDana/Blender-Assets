"""Shared constants for the INDEPENDENT Unreal + fit verifier of SM_Katana + SM_Katana_Saya (role: unreal-fit verifier).
Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Indep (read-only model). Nothing here edits Exports or Scripts.
"""
import hashlib
import os
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "katana" / "UnrealVerify_Indep"
EXP = PROJ / "Exports" / "Katana"
MESHES = ("SM_Katana", "SM_Katana_Saya")
SHIPPED_SHA = {
    "SM_Katana": "da401f782ca648ca234f6030dff36c1fddf49821139cc903173f5be05890162e",
    "SM_Katana_Saya": "f40651c62504d00efd942c75aea676ddc74ce3d1c351fadd4471ad3787000622",
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
