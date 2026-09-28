"""Expand the audit's group-A items into concrete paths for the Recycle Bin (read-only; writes recycle_list.json)."""
import glob
import json
import os
import time

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
d = json.load(open(ROOT + "/WorkFiles/cleanup/cleanup_audit.json", encoding="utf-8"))
now = time.time()
# small tool scripts the audit said to keep inside otherwise-deletable folders
KEEP_CHILD = {"WorkFiles/smokebomb/rewind/wind": {"wd_tools"}, "WorkFiles/smokebomb/final_pass": {"tools"}}
# areas other chats are working in: never touch their .pyc either
ACTIVE = ("Scripts/dojo", "Scripts/armory", "Scripts/garments", "Scripts/MetaHuman", "Scripts/SnowFlowerHeels",
          "Exports/DojoKit", "Exports/ArmoryKit", "Assets/Armory", "Assets/Garments", "WorkFiles/dojo",
          "WorkFiles/armory", "WorkFiles/MetaHuman", "Exports/CharacterLab", "WorkFiles/world")


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def walk_stats(p):
    if os.path.isfile(p):
        return os.path.getsize(p), os.path.getmtime(p)
    s, m = 0, os.path.getmtime(p)
    for dp, _, fn in os.walk(p):
        for f in fn:
            try:
                st = os.stat(os.path.join(dp, f))
                s += st.st_size
                m = max(m, st.st_mtime)
            except OSError:
                pass
    return s, m


paths, skipped = [], []
for it in d["items"]:
    if it["group"] != "A":
        continue
    ext = it.get("ext")
    for pre in it["prefixes"]:
        full = os.path.join(ROOT, pre) if pre else ROOT
        if ext:
            if os.path.isfile(full):
                if any(full.endswith(e) for e in ext):
                    paths.append((it["id"], full))
                continue
            base = full if os.path.isdir(full) else os.path.dirname(full)
            for dp, dn, fn in os.walk(base):
                for skip in (".git", "Content", "DerivedDataCache", "Intermediate", "Saved"):
                    if skip in dn and ext == [".pyc"]:
                        dn.remove(skip)
                r = rel(dp)
                for f in fn:
                    if not any(f.endswith(e) for e in ext):
                        continue
                    fp = os.path.join(dp, f)
                    if r.startswith(ACTIVE) or now - os.path.getmtime(fp) < 6 * 3600:
                        skipped.append(rel(fp))
                        continue
                    paths.append((it["id"], fp))
        elif os.path.isdir(full) and pre in KEEP_CHILD:
            for c in os.listdir(full):
                if c not in KEEP_CHILD[pre]:
                    paths.append((it["id"], os.path.join(full, c)))
        elif os.path.exists(full):
            paths.append((it["id"], full))
        else:
            paths += [(it["id"], x) for x in glob.glob(full + "*")]

dirs = [os.path.abspath(p) for _, p in paths if os.path.isdir(p)]
final, seen = [], set()
for i, p in paths:
    a = os.path.abspath(p)
    if a in seen or any(a != dd and a.startswith(dd + os.sep) for dd in dirs):
        continue
    seen.add(a)
    final.append((i, a))

out, tot, recent = [], 0, []
for i, p in final:
    s, m = walk_stats(p)
    tot += s
    if now - m < 3 * 3600:
        recent.append(rel(p))
    out.append({"id": i, "path": p, "bytes": s})
json.dump(out, open(ROOT + "/WorkFiles/cleanup/recycle_list.json", "w", encoding="utf-8"), indent=0)
print(len(out), "entries", round(tot / 2**30, 2), "GiB; pyc skipped (active/recent):", len(skipped))
print("recent (<3h):", recent)
print("largest GiB:", round(max(o["bytes"] for o in out) / 2**30, 2))
