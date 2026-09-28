"""Group-C items the user approved on 2026-09-28: "delete the snowflower failed passes and metahuman screenshots".
Snow Flower: the failed look-match round 1 + trace pilot (C06) and the v4 bake caches (C07, .npy only).
MetaHuman: capture/screenshot PNGs only (C05); every .json (bones, recipes, faces) and other file stays; the private
Hiyuki test folder and anything written in the last 24 h are skipped (other chats work there)."""
import json
import os
import time

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
now = time.time()
out, skipped = [], []


def add(p):
    if os.path.isfile(p):
        out.append({"id": "C", "path": os.path.abspath(p), "bytes": os.path.getsize(p)})
        return
    s = 0
    for dp, _, fn in os.walk(p):
        for f in fn:
            try:
                s += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    out.append({"id": "C", "path": os.path.abspath(p), "bytes": s})


for d in ("WorkFiles/SnowFlower/v4/lookmatch", "WorkFiles/SnowFlower/v4/trace_pilot"):
    if os.path.isdir(os.path.join(ROOT, d)):
        add(os.path.join(ROOT, d))
for d in ("WorkFiles/SnowFlower/v4/sword_build/bake", "WorkFiles/SnowFlower/v4/sheath_build/bake"):
    base = os.path.join(ROOT, d)
    for dp, _, fn in os.walk(base):
        for f in fn:
            if f.endswith(".npy"):
                add(os.path.join(dp, f))

mh = os.path.join(ROOT, "WorkFiles/MetaHuman")
for dp, dn, fn in os.walk(mh):
    rel = os.path.relpath(dp, mh).replace(os.sep, "/").lower()
    if "hiyuki" in rel:
        dn[:] = []
        continue
    for f in fn:
        if not f.lower().endswith(".png"):
            continue
        p = os.path.join(dp, f)
        if now - os.path.getmtime(p) < 24 * 3600:
            skipped.append(p)
            continue
        add(p)

json.dump(out, open(ROOT + "/WorkFiles/cleanup/recycle_list_c.json", "w", encoding="utf-8"), indent=0)
print(len(out), "entries", round(sum(o["bytes"] for o in out) / 2**30, 2), "GiB; skipped recent PNGs:", len(skipped))
