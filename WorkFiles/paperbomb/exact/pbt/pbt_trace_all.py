"""Trace every group, score every element, optionally save the JSON.
usage: python pbt_trace_all.py [--only a,b] [--norefine] [--out path] [--scores path]"""
import os, sys, json, time, argparse
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
from props_lib import paperbomb_trace as PT
ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--norefine", action="store_true")
ap.add_argument("--out", default=""); ap.add_argument("--scores", default="")
a = ap.parse_args()
t = time.time()
data, fields, L = PT.trace_all(only=[s for s in a.only.split(",") if s] or None, refine=not a.norefine)
print("total %.1f s   unassigned ink px %s" % (time.time() - t, data["unassigned_ink_px"]))
if a.out:
    h = PT.save_traced(data, a.out); print("saved", a.out, h, os.path.getsize(a.out))
if a.scores:
    json.dump({"scores": data["scores"], "groups": [{k: v for k, v in g.items() if k not in ("curves_mm", "strokes_mm")} for g in data["groups"]]},
              open(a.scores, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
