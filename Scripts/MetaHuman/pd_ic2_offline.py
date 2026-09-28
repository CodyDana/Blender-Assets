"""pd_ic2_offline.py -- round-2 independent integrity check, offline parts (plain Python, no Unreal, writes only under
WorkFiles/MetaHuman/player_default/integrity_check_r2/).

usage: py Scripts/MetaHuman/pd_ic2_offline.py files      -> ic2_files.json
  * Exports/JinMuWon_v2 + Assets/JinMuWon_v2 (+ Assets/JinMuWon_v2.blend) vs the Backups manifest (SHA-256), and
    any file under those trees modified after the manifest was written
  * MetaHuman content folder listing, scratch folder on disk, protected + PD SHA-256
  * files the round-2 fixer created/modified (WorkFiles/MetaHuman/player_default, Scripts/MetaHuman) since 17:20
  * 'Saving package' / 'SavePackage' lines in every round-2 engine log
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_default/integrity_check_r2"
PDW = ROOT / "WorkFiles/MetaHuman/player_default"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content"
MH = CONTENT / "Characters/MetaHumans"
MANIFEST = ROOT / "Backups/JinMuWon_v2_skin_nails_2026-09-25/manifest.json"
PROTECTED = ["MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase"]
EXPECT = {"MH_PlayerBase": "63CC39C027798F900489B5499C7E2C99A91F38B7763A459C59478832E425D962",
          "MH_PlayerBase_FaceA": "7A05F69439BFCDE199AA9D56D36EFF5EF38E1AD4E59950A2421285F89AA1C26E",
          "MH_PlayerBase_FaceB": "98DF93A45E0EC0A13B4531E8BC4CBF791E0702B3ED7EE8237C36094CB33F456C",
          "MH_PlayerBase_FaceC": "088D38ADF89B331CB324E51A6DCE9C4FC559468222EC886DC3FB9CE6E83C04F7",
          "MH_MaleBase": "0852D29A4C0659C514AC1190D319E1BA6CD427B127F3A7BC4541E1A200CE5E9B",
          "MH_PlayerDefault": "F2BEB285F85993F542B6B077ADE904B4BE45C3B9A1BF02C3ACF3578D2440D52C"}
ROUND2_START = datetime.datetime(2026, 9, 25, 17, 20, 0)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime(p: Path) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(p.stat().st_mtime)


def files_check() -> dict:
    res: dict = {"checked_local": datetime.datetime.now().isoformat(timespec="seconds")}
    # ---- JinMuWon_v2 vs manifest ----
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    created = datetime.datetime.fromisoformat(man["created"]).replace(tzinfo=None)
    rows, bad = [], []
    for f in man["files"]:
        src = f["source"].replace("\\", "/")
        if not (src.startswith("Assets/JinMuWon_v2") or src.startswith("Exports/JinMuWon_v2")):
            continue
        p = ROOT / src
        if not p.exists():
            bad.append({"source": src, "problem": "missing"})
            continue
        h = sha(p)
        ok = h.lower() == f["sha256"].lower() and p.stat().st_size == f["bytes"]
        rows.append({"source": src, "ok": ok})
        if not ok:
            bad.append({"source": src, "problem": "hash/size differs", "got": h, "want": f["sha256"]})
    res["jinmuwon_manifest_files_checked"] = len(rows)
    res["jinmuwon_manifest_mismatches"] = bad
    newer = []
    listed = {f["source"].replace("\\", "/").lower() for f in man["files"]}
    for base in (ROOT / "Exports/JinMuWon_v2", ROOT / "Assets/JinMuWon_v2"):
        for p in base.rglob("*"):
            if p.is_file() and mtime(p) > created:
                newer.append({"path": str(p.relative_to(ROOT)), "mtime": mtime(p).isoformat(timespec="seconds"),
                              "in_manifest": str(p.relative_to(ROOT)).replace("\\", "/").lower() in listed})
    top = ROOT / "Assets/JinMuWon_v2.blend"
    if top.exists() and mtime(top) > created:
        newer.append({"path": str(top.relative_to(ROOT)), "mtime": mtime(top).isoformat(timespec="seconds")})
    res["jinmuwon_files_modified_after_manifest"] = newer
    res["manifest_created"] = man["created"]
    # ---- MetaHuman content + scratch ----
    res["metahuman_dir"] = [{"name": p.name, "bytes": p.stat().st_size, "mtime": mtime(p).isoformat(timespec="seconds")}
                            for p in sorted(MH.iterdir())]
    res["scratch_folder_on_disk"] = (CONTENT / "PlayerDefault").exists()
    res["content_files_modified_since_round2"] = [
        {"path": str(p.relative_to(CONTENT)), "mtime": mtime(p).isoformat(timespec="seconds")}
        for p in CONTENT.rglob("*") if p.is_file() and mtime(p) > ROUND2_START]
    hashes = {n: sha(MH / f"{n}.uasset").upper() for n in PROTECTED + ["MH_PlayerDefault"]}
    res["sha256"] = hashes
    res["sha256_match_expected"] = {n: hashes[n] == EXPECT[n] for n in hashes}
    # ---- round-2 files ----
    created_files = []
    for base in (PDW, ROOT / "Scripts/MetaHuman"):
        for p in base.rglob("*"):
            if p.is_file() and mtime(p) > ROUND2_START and "integrity_check_r2" not in str(p) \
                    and "pd_ic2_" not in p.name and "__pycache__" not in str(p):
                created_files.append(str(p.relative_to(ROOT)))
    res["round2_files_n"] = len(created_files)
    dirs: dict = {}
    for f in created_files:
        d = str(Path(f).parent)
        dirs[d] = dirs.get(d, 0) + 1
    res["round2_files_by_dir"] = dirs
    res["round2_top_level_files"] = sorted(f for f in created_files if Path(f).parent in (Path("WorkFiles/MetaHuman/player_default"), Path("Scripts/MetaHuman")))
    # ---- saves in round-2 engine logs ----
    saves = {}
    pat = re.compile(r"(Saving package|SavePackage|Save=|LogSavePackage|Saved package|OnPackageSaved)", re.I)
    for log in sorted(PDW.glob("engine_r2_*.log")):
        hits = []
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if pat.search(line) and "Display" not in line[:0]:
                    hits.append(line.strip()[:220])
        saves[log.name] = hits[:40]
    res["engine_log_save_lines"] = saves
    return res


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "files"
    if mode == "files":
        res = files_check()
        (OUT / "ic2_files.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in res.items() if k not in ("metahuman_dir", "round2_top_level_files")},
                         indent=1)[:12000])


if __name__ == "__main__":
    main()
