"""Shared helpers for the armory_hall sync tools (plain Python 3 + numpy; no Unreal, no Blender).

Run every tool from the repo root (C:/Users/Cody/Desktop/Blender_Projects):  py -3 -B WorkFiles/shared/armory_hall/tools/<tool>.py
Frames (SYNC.md section 2): metres; hall-local origin = the centre door threshold at finished floor level;
  hall-local = armory + (-6, 0, 0);  DojoLab world = hall-local + (22, 24, 0.5);  ArmoryLab world = hall-local + (6, 0, 0).
"""
import hashlib
import json
import math
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
SH = ROOT / "WorkFiles" / "shared" / "armory_hall"
TOOLS = SH / "tools"
ARMORY_BUILD = ROOT / "WorkFiles" / "armory" / "build"
EXPORTS_AK = ROOT / "Exports" / "ArmoryKit"
EXPORTS_HALL = ROOT / "Exports" / "DojoKit" / "Hall"
ARMORYLAB = Path("C:/Users/Cody/Documents/Unreal Projects/ArmoryLab")     # files read only, never opened in Unreal
DOJOLAB = Path("C:/Users/Cody/Documents/Unreal Projects/DojoLab")
ARMORY_TO_HALL = (-6.0, 0.0, 0.0)
HALL_TO_DOJO = (22.0, 24.0, 0.5)
HALL_TO_ARMORYLAB = (6.0, 0.0, 0.0)
TOL = 0.012
LOCK_ASSET = "ArmoryHall"
SHARED_JSONS = ("interior_layout", "lights_design", "hall_shell_layout", "interface", "shell_materials")
# files whose sha256 the manifest records (a change to any of them without a manifest bump fails check_sync)
SHARED_FILES = ("SYNC.md", "interior_layout.json", "lights_design.json", "hall_shell_layout.json", "interface.json",
                "shell_materials.json", "shell_masters.json", "tools/ahcommon.py", "tools/fbxlite.py",
                "tools/regen_interior.py", "tools/bump_manifest.py", "tools/check_sync.py", "tools/master_snapshot.py",
                "tools/ue_armorylab_shell.py")
# rev 4 (SYNC.md 3 "which revisions need a sync"): shared files that no Unreal sync reads (docs and plain-Python check /
# bookkeeping tools; the layout jsons they write are listed on their own). A bump that changes only these needs no
# project re-sync. tools/ue_armorylab_shell.py is read by the ArmoryLab sync only. Everything else (every other shared
# file, every FBX / texture / material entry, the shell master graph) needs both projects re-synced.
NO_SYNC_FILES = ("SYNC.md", "tools/ahcommon.py", "tools/fbxlite.py", "tools/regen_interior.py", "tools/bump_manifest.py",
                 "tools/check_sync.py", "tools/master_snapshot.py")
ARMORYLAB_ONLY_FILES = ("tools/ue_armorylab_shell.py",)
PROJECTS = ("DojoLab", "ArmoryLab")


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jdump(p, obj):
    """The folder's one JSON style (indent 1, UTF-8, trailing newline): a re-write of unchanged data is byte-identical."""
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def r4(v):
    return [round(float(x), 4) for x in v]


def a2h(p, dz=0.0):
    return r4((p[0] + ARMORY_TO_HALL[0], p[1] + ARMORY_TO_HALL[1], p[2] + ARMORY_TO_HALL[2] + dz))


def h2w(p):
    return r4((p[0] + HALL_TO_DOJO[0], p[1] + HALL_TO_DOJO[1], p[2] + HALL_TO_DOJO[2]))


def bbox_a2h(b, dz=0.0):
    return a2h(b[0:3], dz) + a2h(b[3:6], dz)


def today():
    return date.today().isoformat()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")


def shared():
    return {k: jload(SH / f"{k}.json") for k in SHARED_JSONS + ("manifest",) if (SH / f"{k}.json").exists()}


def lock_held(agent="claude"):
    """True when `agent` holds the ArmoryHall lock (Scripts/pipeline/lock.py)."""
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L   # noqa: PLC0415
    try:
        L.assert_owner(LOCK_ASSET, agent)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"LOCK: {exc}")
        return False


def placed_shell(H):
    """The shell instances that stand in the hall: instances_existing 'kept*' + instances_new not 'removed*'."""
    out = []
    for i in H["instances_existing"]:
        if str(i["status"]).startswith("kept"):
            out.append(i)
    for i in H["instances_new"]:
        if not str(i.get("status", "")).startswith("removed"):
            out.append(i)
    return out


def intrusion_boxes(F):
    boxes = []
    for s in F["envelope"]["shell_intrusions"]:
        boxes.append((s["what"], s["x"], s["y"], s["z"]))
        if "mirror" in s:
            mx = [float(v) for v in s["mirror"].split("[")[1].rstrip("]").split(",")]
            boxes.append((s["what"] + " (mirror)", mx, s["y"], s["z"]))
    return boxes


def rotz(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return v @ np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]).T


_MESH_CACHE = {}


def fbx_meshes(path):
    sys.path.insert(0, str(TOOLS))
    import fbxlite   # noqa: PLC0415
    key = (str(path), Path(path).stat().st_mtime_ns)
    if key not in _MESH_CACHE:
        _MESH_CACHE[key] = fbxlite.meshes(path)[0]
    return _MESH_CACHE[key]


def piece_box_local(path, render_only=False):
    ms = fbx_meshes(path)
    v = np.vstack([m for k, m in ms.items() if not (render_only and k.startswith("UCX_"))])
    return v.min(0), v.max(0)


def git_short(path):
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h", "--", str(path)], capture_output=True,
                           text=True, timeout=20)
        return r.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None
