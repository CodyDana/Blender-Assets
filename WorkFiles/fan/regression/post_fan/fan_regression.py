"""The fan's regression snapshot and compare (pure Python, no numpy: runs with the system ``py -3``).

    py -3 WorkFiles/fan/regression/fan_regression.py snapshot <dir>      write <dir>/SHA256SUMS.txt + manifest.json
    py -3 WorkFiles/fan/regression/fan_regression.py compare <old_dir> [<new_dir>]
                                                                        compare a snapshot with another or with NOW

SCOPES
    frozen      everything the fan job must never change: the other items' blends, exports and renders, the shuriken
                scripts, the other props' builders and libraries, the static pipeline's existing modules. Compare:
                every file identical, nothing missing; new files are listed (there must be none).
    materials   Scripts/unreal/materials (the fan's Integrate phase may ADD files and change only the listed ones) and
                the materials job's outputs in WorkFiles/materials (additions only).
    fan         the fan's own deliverables (Assets/Fan.blend, Exports/Fan, Renders/Fan, the fan modules and build
                script, References/Fan): recorded, reported as changed / added / removed.
Out of bounds and never read: Exports/BlackCloak, JinMuWon, MH_* assets, anything another agent owns.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
FROZEN = ["Assets/Shuriken.blend", "Assets/SmokeBomb.blend", "Assets/BlackHat.blend", "Assets/PaperBomb.blend",
          "Exports/Shuriken", "Exports/SmokeBomb", "Exports/BlackHat", "Exports/PaperBomb",
          "Renders/Shuriken", "Renders/SmokeBomb", "Renders/BlackHat", "Renders/PaperBomb",
          "Scripts/shuriken",
          "Scripts/props/build_black_hat.py", "Scripts/props/build_smoke_bomb.py", "Scripts/props/build_paper_bomb.py",
          "Scripts/pipeline/__init__.py", "Scripts/pipeline/export_fbx.py", "Scripts/pipeline/qa_check.py",
          "Scripts/pipeline/helpers.py", "Scripts/pipeline/textures.py", "Scripts/pipeline/lock.py",
          "Scripts/pipeline/ue_import_sockets.py", "Scripts/pipeline/garment_qa.py", "Scripts/pipeline/garment_helpers.py",
          "Scripts/pipeline/test_pipeline.py", "Scripts/pipeline/test_qa_negative.py", "Scripts/pipeline/test_garment.py",
          "Scripts/pipeline/skeletal_prop.py"]
MATERIALS = ["Scripts/unreal/materials", "WorkFiles/materials"]
FAN = ["Assets/Fan.blend", "Exports/Fan", "Renders/Fan", "Scripts/props/build_fan.py", "Scripts/props/verify_fan.py",
       "References/Fan", "WorkFiles/fan/FAN_REPORT.md"]
#: materials files the Integrate phase is allowed to CHANGE (everything else there: identical or new)
MATERIALS_MAY_CHANGE = {"Scripts/unreal/materials/material_spec.json", "Scripts/unreal/materials/np_spec.py",
                        "Scripts/unreal/materials/np_meshes.py", "Scripts/unreal/materials/np_verify.py",
                        "Scripts/unreal/materials/np_masters.py", "Scripts/unreal/materials/np_dump.py",
                        "Scripts/unreal/materials/np_render.py",
                        # the fan's own NEW files (not in the materials job's baseline)
                        "Scripts/unreal/materials/np_skeletal.py", "Scripts/unreal/materials/maps/derive_constants_fan.py"}
#: materials-job outputs a build run rewrites by design (logs and the importer self-test)
MATERIALS_REWRITTEN = ("WorkFiles/materials/build/logs/", "WorkFiles/materials/build/_importer_selftest_empty")


def _files(rel: str):
    p = PROJECT / rel
    if p.is_file():
        yield rel
    elif p.is_dir():
        for q in sorted(p.rglob("*")):
            if q.is_file() and "__pycache__" not in q.parts:
                yield q.relative_to(PROJECT).as_posix()
    for q in ():
        yield q


def _props_libs():
    for q in sorted((PROJECT / "Scripts/props/props_lib").glob("*.py")):
        rel = q.relative_to(PROJECT).as_posix()
        yield ("fan" if q.name.startswith("fan_") else "frozen"), rel


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def take() -> dict:
    out = {"frozen": {}, "materials": {}, "fan": {}}
    for scope, rels in (("frozen", FROZEN), ("materials", MATERIALS), ("fan", FAN)):
        for rel in rels:
            for f in _files(rel):
                out[scope][f] = sha(PROJECT / f)
    for scope, f in _props_libs():
        out[scope][f] = sha(PROJECT / f)
    return out


def snapshot(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    snap = take()
    lines = [f"{h} *{f}" for scope in ("frozen", "materials", "fan") for f, h in sorted(snap[scope].items())]
    (d / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    man = {"taken": time.strftime("%Y-%m-%dT%H:%M:%S"), "counts": {k: len(v) for k, v in snap.items()}, "files": snap}
    (d / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps(man["counts"]))


def compare(old: dict, new: dict) -> dict:
    res = {}
    for scope in ("frozen", "materials", "fan"):
        a, b = old["files"][scope], new[scope] if "files" not in new else new["files"][scope]
        changed = sorted(f for f in a if f in b and a[f] != b[f])
        removed = sorted(f for f in a if f not in b)
        added = sorted(f for f in b if f not in a)
        res[scope] = {"identical": sum(1 for f in a if f in b and a[f] == b[f]), "changed": changed,
                      "removed": removed, "added": added}
    m = res["materials"]
    m["changed_allowed"] = [f for f in m["changed"] if f in MATERIALS_MAY_CHANGE or f.startswith(MATERIALS_REWRITTEN)]
    m["changed_NOT_allowed"] = [f for f in m["changed"] if f not in m["changed_allowed"]]
    res["gates"] = {"frozen_identical_nothing_added": not (res["frozen"]["changed"] or res["frozen"]["removed"]
                                                           or res["frozen"]["added"]),
                    "materials_only_additions_and_allowed_changes": not (m["changed_NOT_allowed"] or m["removed"])}
    res["passed"] = all(res["gates"].values())
    return res


def materials_code_vs_baseline() -> dict:
    """Scripts/unreal/materials against the materials job's own final snapshot
    (WorkFiles/materials/regression/post_materials/SHA256SUMS.txt, taken before any fan work)."""
    base = PROJECT / "WorkFiles/materials/regression/post_materials/SHA256SUMS.txt"
    want = {}
    for line in base.read_text(encoding="utf-8").splitlines():
        h, f = line.split(maxsplit=1)
        f = f.lstrip("*").replace("./Scripts_unreal_materials/", "Scripts/unreal/materials/")
        if f.startswith("Scripts/unreal/materials/"):
            want[f] = h
    now = {f: sha(PROJECT / f) for f in _files("Scripts/unreal/materials")}
    changed = sorted(f for f in want if f in now and now[f] != want[f])
    return {"baseline": base.relative_to(PROJECT).as_posix(), "baseline_files": len(want),
            "identical": sum(1 for f in want if now.get(f) == want[f]), "changed": changed,
            "changed_NOT_allowed": [f for f in changed if f not in MATERIALS_MAY_CHANGE],
            "missing": sorted(f for f in want if f not in now), "added": sorted(f for f in now if f not in want)}


def main(argv):
    if argv[0] == "snapshot":
        snapshot(Path(argv[1]))
        return 0
    if argv[0] == "compare":
        old = json.loads((Path(argv[1]) / "manifest.json").read_text(encoding="utf-8"))
        new = json.loads((Path(argv[2]) / "manifest.json").read_text(encoding="utf-8")) if len(argv) > 2 else take()
        res = compare(old, new)
        mc = materials_code_vs_baseline()
        res["materials_code_vs_post_materials"] = mc
        res["gates"]["materials_code_only_allowed_changes"] = not (mc["changed_NOT_allowed"] or mc["missing"])
        res["passed"] = all(res["gates"].values())
        print(json.dumps(res, indent=1))
        return 0 if res["passed"] else 1
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
