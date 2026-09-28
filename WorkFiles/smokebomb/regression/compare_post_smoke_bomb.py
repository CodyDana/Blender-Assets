"""compare_post_smoke_bomb.py - snapshot and regression check for SM_SmokeBomb (final pass, 2026-09-25).

    python compare_post_smoke_bomb.py snapshot   copy the shipped smoke bomb (blend, exports, renders,
                                                 report, modules) into post_smoke_bomb/ and write
                                                 post_smoke_bomb/SHA256SUMS.txt
    python compare_post_smoke_bomb.py compare    re-hash the LIVE files against:
        * post_smoke_bomb/SHA256SUMS.txt          (the smoke bomb itself, as snapshotted)
        * WorkFiles/shuriken/regression/post_kunai_plain/SHA256SUMS.txt   (the frozen shuriken pack:
          blend, exports, textures, build scripts, reports)
        * WorkFiles/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt    (the paused paper bomb)
      and write post_smoke_bomb/compare_result.json.  Exit 1 on any mismatch.
Standard library only (system Python is fine: PYTHONUTF8=1).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
SNAP = Path(__file__).resolve().parent / "post_smoke_bomb"
SMOKE = {
    "Assets/SmokeBomb.blend": PROJECT / "Assets" / "SmokeBomb.blend",
    "Exports/SmokeBomb": PROJECT / "Exports" / "SmokeBomb",
    "Renders/SmokeBomb": PROJECT / "Renders" / "SmokeBomb",
    "WorkFiles/smokebomb/smokebomb_report.json": PROJECT / "WorkFiles" / "smokebomb" / "smokebomb_report.json",
    "Scripts/props/build_smoke_bomb.py": PROJECT / "Scripts" / "props" / "build_smoke_bomb.py",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def smoke_files():
    out = {}
    for rel, p in SMOKE.items():
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    out[str(Path(rel) / f.relative_to(p)).replace("\\", "/")] = f
        elif p.is_file():
            out[rel] = p
    for f in sorted((PROJECT / "Scripts" / "props" / "props_lib").glob("smokebomb_*.py")):
        out["Scripts/props/props_lib/" + f.name] = f
    out["Scripts/props/props_lib/ue_import_textures.py"] = PROJECT / "Scripts/props/props_lib/ue_import_textures.py"
    return out


def check_sums(sums: Path, resolve) -> dict:
    res = {"file": str(sums.relative_to(PROJECT)), "checked": 0, "ok": 0, "mismatch": [], "missing": []}
    for line in sums.read_text(encoding="utf8").splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        want, rel = parts[0], parts[-1].lstrip("*")
        p = resolve(rel)
        if p is None:
            continue
        res["checked"] += 1
        if not p.is_file():
            res["missing"].append(rel)
        elif sha(p) == want:
            res["ok"] += 1
        else:
            res["mismatch"].append(rel)
    res["all_ok"] = res["checked"] > 0 and res["ok"] == res["checked"]
    return res


def shuriken_path(rel: str):
    if rel == "Shuriken.blend":
        return PROJECT / "Assets" / "Shuriken.blend"
    if rel.startswith("export/"):
        return PROJECT / "Exports" / "Shuriken" / rel[len("export/"):]
    if rel.startswith("textures/"):
        p = PROJECT / "Exports" / "Shuriken" / "Textures" / rel[len("textures/"):]
        return p if p.is_file() else PROJECT / "Exports" / "Shuriken" / rel[len("textures/"):]
    if rel.startswith("scripts/"):
        return PROJECT / "Scripts" / "shuriken" / rel[len("scripts/"):]
    if rel.endswith("_report.json"):
        return PROJECT / "WorkFiles" / "shuriken" / rel
    return None


def snapshot():
    if SNAP.exists():
        shutil.rmtree(SNAP)
    SNAP.mkdir(parents=True)
    lines = []
    for rel, p in smoke_files().items():
        dst = SNAP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        lines.append(f"{sha(p)} *{rel}")
    (SNAP / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"snapshot: {len(lines)} files -> {SNAP}")


def compare() -> int:
    res = {
        "smoke_bomb_vs_snapshot": check_sums(SNAP / "SHA256SUMS.txt", lambda rel: PROJECT / rel),
        "shuriken_vs_post_kunai_plain": check_sums(
            PROJECT / "WorkFiles/shuriken/regression/post_kunai_plain/SHA256SUMS.txt", shuriken_path),
        "paperbomb_vs_paused": check_sums(
            PROJECT / "WorkFiles/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt", lambda rel: PROJECT / rel),
    }
    res["all_ok"] = all(v["all_ok"] for v in res.values() if isinstance(v, dict))
    (SNAP / "compare_result.json").write_text(json.dumps(res, indent=2), encoding="utf8")
    for k, v in res.items():
        if isinstance(v, dict):
            print(f"{k}: {v['ok']}/{v['checked']} ok, mismatch {v['mismatch']}, missing {v['missing']}")
    print("ALL OK" if res["all_ok"] else "MISMATCH")
    return 0 if res["all_ok"] else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "compare"
    if mode == "snapshot":
        snapshot()
        sys.exit(compare())
    sys.exit(compare())
