"""Prove the frozen items' exports are unchanged (read-only; system Python, hashlib only).

    py -3 -B WorkFiles/flashbang/regression/frozen_check.py [--out file.json]

1. Every file under Exports/{Shuriken,SmokeBomb,BlackHat,PaperBomb,Fan} and Scripts/unreal/materials against the
   snapshot taken at the START of the flashbang build (pre_flashbang/SHA256SUMS.txt): identical, none missing, and
   any new file listed.
2. The CURRENT per-item baselines:
     shuriken + kunai  WorkFiles/shuriken/regression/post_blade_section/SHA256SUMS.txt (export/, textures/)
     paper bomb        WorkFiles/paperbomb/regression/post_paper_bomb/SHA256SUMS.txt (export/)
     fan (+ its pack)  WorkFiles/fan/regression/post_fan/SHA256SUMS.txt (Exports/* lines only)
Exit 0 = all identical.
"""
import hashlib
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[3]
FROZEN_DIRS = ["Exports/Shuriken", "Exports/SmokeBomb", "Exports/BlackHat", "Exports/PaperBomb", "Exports/Fan",
               "Scripts/unreal/materials"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_sums(path):
    out = []
    for line in Path(path).read_text(encoding="utf8").replace("\r", "").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            out.append((parts[0], parts[1].lstrip("*").strip()))
    return out


def check(pairs, resolve):
    ok, bad = 0, []
    for h, rel in pairs:
        p = resolve(rel)
        if p is None:
            continue
        if not p.is_file():
            bad.append(("MISSING", str(p.relative_to(P))))
        elif sha(p) != h:
            bad.append(("DIFF", str(p.relative_to(P))))
        else:
            ok += 1
    return {"identical": ok, "differing_or_missing": bad}


def main():
    res = {}
    pre = P / "WorkFiles/flashbang/regression/pre_flashbang/SHA256SUMS.txt"
    pairs = read_sums(pre)
    res["vs_pre_flashbang"] = check(pairs, lambda r: P / r)
    known = {r for _, r in pairs}
    new = []
    for d in FROZEN_DIRS:
        for f in sorted((P / d).rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                rel = f.relative_to(P).as_posix()
                if rel not in known:
                    new.append(rel)
    res["vs_pre_flashbang"]["new_files"] = new

    def shu(rel):
        if rel.startswith("export/"):
            return P / "Exports/Shuriken" / rel[7:]
        if rel.startswith("textures/"):
            q = P / "Exports/Shuriken/Textures" / rel[9:]
            return q if q.is_file() else P / "Exports/Shuriken" / rel[9:]
        return None
    res["kunai_post_blade_section"] = check(
        read_sums(P / "WorkFiles/shuriken/regression/post_blade_section/SHA256SUMS.txt"), shu)
    res["paperbomb_post_paper_bomb"] = check(
        read_sums(P / "WorkFiles/paperbomb/regression/post_paper_bomb/SHA256SUMS.txt"),
        lambda r: (P / "Exports/PaperBomb" / r[7:]) if r.startswith("export/") else None)
    res["fan_post_fan_exports"] = check(
        read_sums(P / "WorkFiles/fan/regression/post_fan/SHA256SUMS.txt"),
        lambda r: (P / r) if r.startswith("Exports/") else None)
    res["all_identical_vs_pre"] = (not res["vs_pre_flashbang"]["differing_or_missing"])
    res["current_baselines_diffs"] = {k: res[k]["differing_or_missing"] for k in
                                      ("kunai_post_blade_section", "paperbomb_post_paper_bomb", "fan_post_fan_exports")}
    txt = json.dumps(res, indent=2)
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(txt, encoding="utf8")
    print(txt)
    return 0 if res["all_identical_vs_pre"] else 1


if __name__ == "__main__":
    sys.exit(main())
