# sm_m07: sword reference (design sheet) - front view blade profile, side view thickness, overall landmarks
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sword"); L = lum(a)
H, W = L.shape
res = {}
def view_profile(x0, x1, y0, y1, thr=0.90):
    out = []
    for y in range(y0, y1):
        m = L[y, x0:x1] < thr
        rs = [(s + x0, e + x0) for s, e in runs(m) if e - s + 1 >= 2]
        out.append((y, rs))
    return out
# front view: full column range 180-380, all rows
fv = view_profile(180, 380, 0, H)
rows = [y for y, rs in fv if rs]
print("front view fg rows", rows[0], rows[-1])
for y, rs in fv[::10]:
    if rs:
        print("F y %4d" % y, rs)
res["front"] = [(y, rs) for y, rs in fv if rs]
sv = view_profile(420, 560, 0, H)
rows = [y for y, rs in sv if rs]
print("side view fg rows", rows[0], rows[-1])
for y, rs in sv[::10]:
    if rs:
        print("S y %4d" % y, rs)
res["side"] = [(y, rs) for y, rs in sv if rs]
bv = view_profile(600, 800, 0, H)
rows = [y for y, rs in bv if rs]
print("back view fg rows", rows[0], rows[-1])
res["back"] = [(y, rs) for y, rs in bv if rs]
json.dump(res, open(os.path.join(HERE, "sm_s07.json"), "w"))
