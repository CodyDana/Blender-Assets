#!/usr/bin/env python
"""SM_BlackHat regression snapshot (post_black_hat: the close-out build, library 1.2.1, FBX 719248e4..., 2026-09-26)
and frozen-asset proof.

    python compare_black_hat.py            (any Python 3; stdlib only; PYTHONUTF8=1 on Windows)
    python compare_black_hat.py --write    (re-snapshot: ONLY when a new black hat build is accepted)

1. BLACK HAT: every line of SHA256SUMS.txt (the live Assets / Exports / Renders / Scripts /
   References / WorkFiles files, project-relative) re-hashed against the live project AND against
   the copy kept in this folder.
2. FROZEN ASSETS: every line of the three frozen lists, all of them, hashed live:
     shuriken    WorkFiles/shuriken/regression/post_kunai_plain/SHA256SUMS.txt (78 lines, snapshot-
                 relative: Shuriken.blend -> Assets/, export/ -> Exports/Shuriken/, textures/ ->
                 Exports/Shuriken/Textures/, scripts/ -> Scripts/shuriken/, *_report.json ->
                 WorkFiles/shuriken/); each line is also checked against the snapshot's own copy
     smoke bomb  WorkFiles/smokebomb/regression/post_smoke_bomb/SHA256SUMS.txt (30, project-relative)
     paper bomb  WorkFiles/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt (6, project-relative)
Writes compare_result.json next to this file; exit code 0 only if everything matches.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[3]
SUMS = HERE / "SHA256SUMS.txt"

TRACKED = ["Assets/BlackHat.blend", "Exports/BlackHat", "Renders/BlackHat", "Scripts/props/build_black_hat.py",
           "Scripts/props/props_lib/blackhat_atlas.py", "Scripts/props/props_lib/blackhat_camera.py",
           "Scripts/props/props_lib/blackhat_gallery.py", "Scripts/props/props_lib/blackhat_geom.py",
           "Scripts/props/props_lib/blackhat_look.py", "Scripts/props/props_lib/blackhat_paint.py",
           "Scripts/props/props_lib/blackhat_spec.py", "References/BlackHat",
           "WorkFiles/blackhat/blackhat_report.json", "WorkFiles/blackhat/BLACKHAT_REPORT.md",
           "WorkFiles/blackhat/UnrealCheck/verification_summary.json"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files():
    out = []
    for t in TRACKED:
        p = PROJ / t
        if p.is_dir():
            out += sorted(q for q in p.rglob("*") if q.is_file() and "__pycache__" not in q.parts)
        elif p.is_file():
            out.append(p)
    return [q.relative_to(PROJ).as_posix() for q in out]


def read_sums(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            rows.append((parts[0], parts[-1].lstrip("*")))
    return rows


def write():
    rows = []
    for rel in files():
        dst = HERE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJ / rel, dst)
        rows.append(f"{sha(PROJ / rel)} *{rel}")
    SUMS.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} lines")


def shuriken_live(rel):
    if rel == "Shuriken.blend":
        return PROJ / "Assets" / "Shuriken.blend"
    if rel.startswith("export/"):
        return PROJ / "Exports" / "Shuriken" / rel[7:]
    if rel.startswith("textures/"):
        p = PROJ / "Exports" / "Shuriken" / "Textures" / rel[9:]
        return p if p.is_file() else PROJ / "Exports" / "Shuriken" / rel[9:]
    if rel.startswith("scripts/"):
        return PROJ / "Scripts" / "shuriken" / rel[8:]
    if rel.endswith("_report.json"):
        return PROJ / "WorkFiles" / "shuriken" / rel
    return None


def check(rows, live_of, snap_dir=None):
    res = {"lines": len(rows), "live_ok": 0, "live_failed": [], "snapshot_copy_ok": None}
    snap_ok = 0
    for want, rel in rows:
        p = live_of(rel)
        if p is not None and p.is_file() and sha(p) == want:
            res["live_ok"] += 1
        else:
            res["live_failed"].append(rel)
        if snap_dir is not None:
            q = snap_dir / rel
            snap_ok += int(q.is_file() and sha(q) == want)
    if snap_dir is not None:
        res["snapshot_copy_ok"] = snap_ok
    res["all_ok"] = not res["live_failed"] and (snap_dir is None or snap_ok == len(rows))
    return res


def main():
    if "--write" in sys.argv:
        write()
    wf = PROJ / "WorkFiles"
    shu = wf / "shuriken" / "regression" / "post_kunai_plain"
    out = {"black_hat": check(read_sums(SUMS), lambda r: PROJ / r, HERE),
           "frozen": {
               "shuriken": check(read_sums(shu / "SHA256SUMS.txt"), shuriken_live, shu),
               "smokebomb": check(read_sums(wf / "smokebomb" / "regression" / "post_smoke_bomb" / "SHA256SUMS.txt"),
                                  lambda r: PROJ / r),
               "paperbomb": check(read_sums(wf / "paperbomb" / "paused_2026-09-21" / "SHA256SUMS_exports.txt"),
                                  lambda r: PROJ / r)}}
    untracked_now = sorted(set(files()) - {r for _, r in read_sums(SUMS)})
    out["black_hat"]["live_files_not_in_snapshot"] = untracked_now
    out["all_ok"] = (out["black_hat"]["all_ok"] and not untracked_now
                     and all(v["all_ok"] for v in out["frozen"].values()))
    (HERE / "compare_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"black_hat": {k: out["black_hat"][k] for k in ("lines", "live_ok", "snapshot_copy_ok")},
                      "frozen": {k: {kk: v[kk] for kk in ("lines", "live_ok", "snapshot_copy_ok")}
                                 for k, v in out["frozen"].items()}, "all_ok": out["all_ok"]}))
    return 0 if out["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
