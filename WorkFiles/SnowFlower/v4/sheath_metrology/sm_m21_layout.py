# sm_m21: labelled layout overlay (DEBUG, NEVER SHIP)
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); H, W = a.shape[:2]
dbg = a[..., :3].copy() * 0.75 + 0.25
prof = np.array(json.load(open(os.path.join(HERE, "sm_s01.json")))["profile"])
edge = {int(r[0]): (int(r[1]), int(r[2])) for r in prof}
spec = json.load(open(os.path.join(os.path.dirname(HERE), "sheath_spec.json")))
def hline(y, x0, x1, c): dbg[y, x0:x1] = c; dbg[min(y + 1, H - 1), x0:x1] = c
cols = {"fit": (1, 0.5, 0), "band": (0, 0.8, 1), "facet": (1, 1, 0), "bl": (1, 0, 1), "vine": (1, 0, 0), "pod": (0, 1, 0)}
for y in (31, 41, 81, 143, 167): hline(y, 400, 620, cols["fit"])
for y in (287, 321): hline(y, 400, 620, cols["band"])
for y in (1265, 1293, 1388, 1496): hline(y, 400, 620, cols["fit"])
for y in range(169, 1250, 2):
    if 286 <= y <= 322: continue
    l, r = edge[y]; c = (l + r) / 2; hw = (r - l) / 2
    for uu in (-0.51, 0.51): dbg[y, int(round(c + uu * hw))] = cols["facet"]
path = np.array(json.load(open(os.path.join(HERE, "sm_s17.json")))["path"])
for y in range(167, 1262):
    dbg[y, int(round(np.interp(y, path[:, 0], path[:, 1])))] = cols["vine"]
rows = {r["row"]: r for r in spec["rows"]}
circ = [(b["row"], b["x"], b["diameter_px"] / 2, cols["bl"]) for b in rows["open blossoms on the vine (5 petals, stamen)"]["value"]]
circ += [(87, 505, 30, cols["bl"]), (300, 504, 25, cols["bl"]), (1330, 505, 27, cols["bl"]), (820, 506, 9, cols["pod"]), (919, 501, 9, cols["pod"])]
tt = np.linspace(0, 2 * np.pi, 120)
for y, x, r, c in circ:
    dbg[np.clip((y + r * np.sin(tt)).astype(int), 0, H - 1), np.clip((x + r * np.cos(tt)).astype(int), 0, W - 1)] = c
save_png(dbg[0:1536, 330:690], "DEBUG_NEVER_SHIP_sheath_layout_LABELLED.png", 1)
print("ok")
