"""SR-01 pack-colours stage: build (or rebuild) the short-path mirror root the pack build runs from, the SMG01 way.

    py -3 -B WorkFiles/guns/sniper/pack/make_mirror.py [--mirror DIR] [--remove]

Mirror (default C:/Users/Cody/AppData/Local/Temp/claude/sr01pk):
    Scripts/unreal/materials   COPY of the main checkout's bytes (LF where main has LF: the other items' constants record
                               those sha256s), then this branch's material_spec.json and maps/derive_constants_sr01.py
    Scripts/pipeline           COPY of the main checkout's bytes (np_meshes imports pipeline.ue_import_sockets)
    Scripts/props, Scripts/shuriken          junctions to main (the texture importers)
    Exports/<item>             junctions to main's Exports/<item>, for every item except Guns
    Exports/Guns/<gun>         junctions to main's Exports/Guns/<gun> (AR01, SMG01, ...), except
    Exports/Guns/SR01          junction to THIS worktree's Exports/Guns/SR01 (this worktree's AR01 FBXs are LFS pointers)
    WorkFiles/shuriken         junction to main (the validation project ShurikenValidation.uproject)
    WorkFiles/guns             junction to THIS worktree's WorkFiles/guns (capture / analysis outputs land here)
    WorkFiles/materials        a real folder (build logs and results; copied out by run_pack_build.sh)
Nothing tracked in the main checkout changes. The materials lock is a fixed absolute path (Scripts/pipeline/lock.py), so
the mirror's run_build.sh takes the real lock.

Checks (stop with exit 1 on the first that fails; results in WorkFiles/guns/sniper/pack/mirror_check.json):
  M1 the main checkout has no uncommitted change under Scripts/unreal/materials, Scripts/pipeline and the two importers
  M2 main's material_spec.json == WorkFiles/guns/sniper/materials/material_spec_before_sr01.json (JSON equality)
  M3 this branch changed nothing else in the pack code (every other file equal to main's, line endings ignored)
  M4 every other item's texture (import_textures_katana_1003.json) and mesh (import_meshes_smg01_1013b.json) seen
     through the mirror has the sha256 of the last build's import record
Junctions are removed with os.rmdir / os.unlink only (never recursed into), so --remove cannot delete a target.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[3]
MAIN = Path("C:/Users/Cody/Desktop/Blender_Projects")
DEFAULT = Path("C:/Users/Cody/AppData/Local/Temp/claude/sr01pk")
REC_TEX = MAIN / "WorkFiles/materials/build/import_textures_katana_1003.json"
REC_MESH = WT / "WorkFiles/guns/smg/materials/build/import_meshes_smg01_1013b.json"
BEFORE = WT / "WorkFiles/guns/sniper/materials/material_spec_before_sr01.json"
BRANCH_FILES = ("material_spec.json", "maps/derive_constants_sr01.py")
IMPORTERS = ("Scripts/props/props_lib/ue_import_textures.py", "Scripts/shuriken/ue_import_textures.py")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def is_link(p):
    p = Path(p)
    return p.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(p))


def remove(p):
    p = Path(p)
    if is_link(p):
        os.rmdir(p) if p.is_dir() else os.unlink(p)
    elif p.is_dir():
        for c in p.iterdir():
            remove(c)
        os.rmdir(p)
    elif p.exists():
        os.unlink(p)


def junction(link, target):
    link, target = Path(link), Path(target)
    if not target.is_dir():
        raise SystemExit(f"junction target missing: {target}")
    link.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link).replace("/", "\\"), str(target).replace("/", "\\")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"mklink /J {link} -> {target} failed: {r.stdout} {r.stderr}")


def fail(res, out, msg):
    res["passed"] = False
    res["stopped_at"] = msg
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("STOP:", msg)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", default=str(DEFAULT))
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    R = Path(a.mirror)
    if R.exists():
        remove(R)
    if a.remove:
        print(f"removed {R}")
        return
    out = HERE / "mirror_check.json"
    res = {"mirror": R.as_posix(), "main": MAIN.as_posix(), "worktree": WT.as_posix()}
    # M1
    paths = ["Scripts/unreal/materials", "Scripts/pipeline", *IMPORTERS]
    st = subprocess.run(["git", "-C", str(MAIN), "status", "--porcelain", "--", *paths], capture_output=True, text=True)
    res["M1_main_clean"] = {"dirty": st.stdout.splitlines(), "pass": st.returncode == 0 and not st.stdout.strip()}
    if not res["M1_main_clean"]["pass"]:
        fail(res, out, f"M1: the main checkout has uncommitted changes in the pack code: {st.stdout.strip()[:400]}")
    # M2
    main_spec = json.loads((MAIN / "Scripts/unreal/materials/material_spec.json").read_text(encoding="utf-8"))
    branch_spec = json.loads((WT / "Scripts/unreal/materials/material_spec.json").read_text(encoding="utf-8"))
    res["M2_main_spec_is_before"] = main_spec == json.loads(BEFORE.read_text(encoding="utf-8"))
    res["M2_main_spec_is_branch_spec"] = main_spec == branch_spec  # the branch already merged
    if not (res["M2_main_spec_is_before"] or res["M2_main_spec_is_branch_spec"]):
        fail(res, out, "M2: main's material_spec.json is neither material_spec_before_sr01.json nor this branch's spec: "
                       "someone else edited it; merge main, re-run add_sr01_to_spec.py (delete the before-file first) "
                       "and re-derive")
    # M3
    mm, wm = MAIN / "Scripts/unreal/materials", WT / "Scripts/unreal/materials"
    files = lambda r: {p.relative_to(r).as_posix() for p in r.rglob("*")  # noqa: E731
                       if p.is_file() and "__pycache__" not in p.parts}
    fm, fw = files(mm), files(wm)
    def same(f):
        a_, b_ = (mm / f).read_bytes(), (wm / f).read_bytes()
        if b_.startswith(b"version https://git-lfs"):  # an unsmudged LFS pointer in the worktree: compare its oid
            oid = [ln.split(b":", 1)[1].strip() for ln in b_.splitlines() if ln.startswith(b"oid sha256:")]
            return bool(oid) and oid[0].decode() == hashlib.sha256(a_).hexdigest()
        return a_.replace(b"\r\n", b"\n") == b_.replace(b"\r\n", b"\n")

    diff = sorted(f for f in fm & fw if f not in BRANCH_FILES and not same(f))
    extra = sorted(fw - fm - set(BRANCH_FILES))
    missing = sorted(fm - fw)
    res["M3_branch_code_additions_only"] = {"differs": diff, "only_in_branch": extra, "only_in_main": missing,
                                            "pass": not (diff or extra or missing)}
    if not res["M3_branch_code_additions_only"]["pass"]:
        fail(res, out, f"M3: the branch's pack code differs from main beyond the spec and derive_constants_sr01.py: "
                       f"{diff + extra + missing}")
    # build the mirror
    shutil.copytree(mm, R / "Scripts/unreal/materials", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(MAIN / "Scripts/pipeline", R / "Scripts/pipeline", ignore=shutil.ignore_patterns("__pycache__"))
    for f in BRANCH_FILES:
        shutil.copyfile(wm / f, R / "Scripts/unreal/materials" / f)
    for d in ("props", "shuriken"):
        junction(R / "Scripts" / d, MAIN / "Scripts" / d)
    for d in sorted(p for p in (MAIN / "Exports").iterdir() if p.is_dir() and p.name != "Guns"):
        junction(R / "Exports" / d.name, d)
    for d in sorted(p for p in (MAIN / "Exports/Guns").iterdir() if p.is_dir() and p.name != "SR01"):
        junction(R / "Exports/Guns" / d.name, d)
    junction(R / "Exports/Guns/SR01", WT / "Exports/Guns/SR01")
    junction(R / "WorkFiles/shuriken", MAIN / "WorkFiles/shuriken")
    junction(R / "WorkFiles/guns", WT / "WorkFiles/guns")
    (R / "WorkFiles/materials/build/logs").mkdir(parents=True, exist_ok=True)
    copied = {f: sha(R / "Scripts/unreal/materials" / f) for f in BRANCH_FILES}
    res["branch_files_in_mirror_sha256"] = copied
    # M4
    bad, n = [], 0
    for v in json.loads(REC_TEX.read_text(encoding="utf-8"))["textures"].values():
        if v["png"].startswith("Exports/Guns/SR01/"):
            continue
        n += 1
        p = R / v["png"]
        if not p.is_file() or sha(p) != v["sha256"]:
            bad.append(v["png"])
    for v in json.loads(REC_MESH.read_text(encoding="utf-8"))["meshes"].values():
        n += 1
        p = R / v["fbx"]
        if not p.is_file() or sha(p) != v["fbx_sha256"]:
            bad.append(v["fbx"])
    res["M4_other_items_equal_last_import"] = {"checked": n, "differs": bad, "pass": not bad,
                                              "records": [REC_TEX.as_posix(), REC_MESH.as_posix()]}
    if bad:
        fail(res, out, f"M4: other items' exports differ from the last build's import records (another chat's work in "
                       f"progress in the main checkout?): {bad[:10]}")
    res["passed"] = True
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"mirror ready at {R} (M1-M4 pass, {n} other-item files checked)")


if __name__ == "__main__":
    main()
