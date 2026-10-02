"""Ninja character port, DemoGame_1 -> DojoLab: byte copy of the C++ sources and the content closure (no Unreal).

READ ONLY on DemoGame_1 (plain file reads; git LFS objects read from .git/lfs/objects). Never overwrites a DojoLab file:
every destination is asserted absent first (a re-run that finds an identical file at the destination counts it as
'already' and moves on; a different file there is an error and stops the run).

    py -3 -B port_copy.py check      # verify every source sha256 against closure.json, every destination absent/identical
    py -3 -B port_copy.py cpp        # copy the C++ files (closure.json -> cpp, actions copy*)
    py -3 -B port_copy.py content    # copy the 510 'copy' packages (core + feature_only)

Writes build/copy_log_<mode>.json with every file, its sha256 and bytes.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NC = HERE.parent
CLOSURE = NC / "survey" / "closure.json"
OUT = NC / "build"
DEMO = Path("C:/Users/Cody/Documents/Unreal Projects/DemoGame_1")
DOJO = Path("C:/Users/Cody/Documents/Unreal Projects/DojoLab")
PRIVATE = ("playerfemale", "hiyuki", "2b", "_private", "catwalk", "/mocap/")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def lfs_path(oid: str) -> Path:
    return DEMO / ".git" / "lfs" / "objects" / oid[:2] / oid[2:4] / oid


def plan_content(cl):
    items = []
    for pkg, v in cl["packages"].items():
        if v["status"] != "copy":
            continue
        low = pkg.lower()
        if any(t in low for t in PRIVATE):
            raise SystemExit(f"private path in the copy set: {pkg}")
        for f in v["files"]:
            rel = f["file"]
            if not rel.lower().endswith((".uasset", ".umap")):
                raise SystemExit(f"non-package file in the copy set: {rel}")
            if pkg in cl["overrides"]:
                src = lfs_path(cl["overrides"][pkg]["oid"])
                origin = f"lfs:{cl['overrides'][pkg]['oid']}"
            else:
                src = DEMO / rel
                origin = "working tree"
            items.append({"package": pkg, "copy_class": v.get("copy_class"), "src": src, "dst": DOJO / rel,
                          "rel": rel, "sha256": f["sha256"], "bytes": f["bytes"], "origin": origin})
    return items


def plan_cpp(cl):
    items = []
    for c in cl["cpp"]:
        if not c["action"].startswith("copy"):
            continue
        items.append({"package": None, "copy_class": c["action"], "src": DEMO / c["file"], "dst": DOJO / c["dest"],
                      "rel": c["dest"], "sha256": c["sha256"], "bytes": c["bytes"], "origin": c["file"]})
    return items


def run(mode):
    cl = json.loads(CLOSURE.read_text(encoding="utf-8"))
    items = plan_cpp(cl) if mode == "cpp" else plan_content(cl) if mode == "content" else plan_cpp(cl) + plan_content(cl)
    log = {"mode": mode, "files": [], "errors": [], "counts": {}}
    copied = already = 0
    total = 0
    for it in items:
        rec = {k: (str(v) if isinstance(v, Path) else v) for k, v in it.items()}
        if not it["src"].is_file():
            log["errors"].append(f"missing source {it['src']}")
            continue
        s = sha(it["src"])
        rec["src_sha256_now"] = s
        if s != it["sha256"]:
            log["errors"].append(f"source changed since the survey: {it['rel']} {s} != {it['sha256']}")
            continue
        if it["dst"].exists():
            d = sha(it["dst"])
            if d == s:
                rec["result"] = "already"
                already += 1
            else:
                log["errors"].append(f"destination exists and differs: {it['dst']} ({d})")
                continue
        elif mode != "check":
            it["dst"].parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(it["src"], it["dst"])
            d = sha(it["dst"])
            if d != s:
                log["errors"].append(f"copy hash mismatch {it['dst']}")
                continue
            rec["result"] = "copied"
            copied += 1
        else:
            rec["result"] = "absent (ok to copy)"
        total += it["bytes"]
        log["files"].append(rec)
    log["counts"] = {"planned": len(items), "ok": len(log["files"]), "copied": copied, "already": already,
                     "errors": len(log["errors"]), "bytes": total}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"copy_log_{mode}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(json.dumps(log["counts"]))
    for e in log["errors"][:40]:
        print("ERROR", e)
    return 0 if not log["errors"] else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else "check"))
