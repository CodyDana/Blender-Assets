"""SHA-256 of every file the Unreal check imports (3.11, the kunai blade section).

    py hash_inputs.py <out.json>

Every Exports/Shuriken/*.fbx, *.sockets.json and Exports/Shuriken/Textures/T_*_*.png (the set ue_import_textures.py
imports: non-recursive, so Textures/Recolour is not included), plus the six frozen forms' expected hashes from
WorkFiles/kunai/blade_section/prep/frozen_six_sha256.json compared where they overlap.  Run before and after the
Unreal passes: the two files must be equal (the passes read these exact bytes).
"""
import hashlib
import json
import sys
import time
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
EXP = PROJ / "Exports" / "Shuriken"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


files = sorted(list(EXP.glob("*.fbx")) + list(EXP.glob("*.sockets.json")) + list((EXP / "Textures").glob("T_*_*.png")))
out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "files": {str(p.relative_to(PROJ)).replace("\\", "/"): sha(p)
                                                                 for p in files}}
frozen_path = PROJ / "WorkFiles" / "kunai" / "blade_section" / "prep" / "frozen_six_sha256.json"
try:
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    flat = {path: rec["sha256"] for form in frozen["forms"].values() for path, rec in form.items()}
    mism = [rel for rel, fv in flat.items() if rel in out["files"] and out["files"][rel] != fv]
    out["frozen_six_overlap_checked"] = sum(1 for rel in flat if rel in out["files"])
    out["frozen_six_mismatches"] = mism
except Exception as exc:  # noqa: BLE001
    out["frozen_six_error"] = f"{type(exc).__name__}: {exc}"
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print("HASH_INPUTS", len(out["files"]), "files; frozen overlap", out.get("frozen_six_overlap_checked"),
      "mismatches", out.get("frozen_six_mismatches"))
