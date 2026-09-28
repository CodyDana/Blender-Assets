# Perpendicular intensity/saturation profiles across each fitted edge line, hub arcs and hole, averaged along the edge.
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seg = np.load(os.path.join(OUT, "seg.npz")); L, S = seg["L"], seg["S"]
a = np.load(os.path.join(OUT, "roppo_rgb.npy"))
Hh, Ww = L.shape
F = pickle.load(open(os.path.join(OUT, "fit.pkl"), "rb"))
points, hub, hole = F["points"], F["hub"], F["hole"]
CH = np.array([hub["cx"], hub["cy"]]); R = hub["r"]
def bil(img, x, y):
    x = np.clip(x, 0, Ww - 1.001); y = np.clip(y, 0, Hh - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
offs = np.arange(-30, 20.01, 0.5)   # negative = inside the piece, positive = outside
def edge_profile(p, s, f0, f1, nst=40):
    e = p[s]; tip = p["tip_geo"]
    # root point: line/hub-circle intersection nearest the tip side
    cen, d = e["cen"], e["dir"]
    # solve |cen + t d - CH| = R
    b = np.dot(cen - CH, d); cc = np.dot(cen - CH, cen - CH) - R * R
    t_root = -b + np.sqrt(b * b - cc)  # larger root toward tip (d points to tip)
    root = cen + t_root * d
    t_tip = np.dot(tip - cen, d)
    ts = np.linspace(t_root + f0 * (t_tip - t_root), t_root + f1 * (t_tip - t_root), nst)
    P = cen[None] + ts[:, None] * d[None]
    X = P[:, None, 0] + offs[None, :] * e["nrm"][0]; Y = P[:, None, 1] + offs[None, :] * e["nrm"][1]
    ok = (Y.max(1) < Hh - 2)
    return bil(L, X, Y)[ok], bil(S, X, Y)[ok], root
rows = []
for i, p in enumerate(points):
    for s in ("A", "B"):
        for (f0, f1, tag) in ((0.1, 0.45, "inner"), (0.45, 0.8, "outer"), (0.1, 0.9, "all")):
            Lp, Sp, root = edge_profile(p, s, f0, f1)
            Lm, Sm = np.median(Lp, 0), np.median(Sp, 0)
            rows.append(dict(point=i, side=s, part=tag, nrm=p[s]["nrm"].tolist(), L=Lm.tolist(), S=Sm.tolist(), root=root.tolist(), n=len(Lp)))
pickle.dump(dict(offs=offs, rows=rows), open(os.path.join(OUT, "bands.pkl"), "wb"))
def show(r):
    sel = (offs >= -22) & (offs <= 12) & (np.abs(offs * 2 % 2) < 1e-9)
    print(f"pt{r['point']}{r['side']} {r['part']:5s} nrm({r['nrm'][0]:+.2f},{r['nrm'][1]:+.2f}) n{r['n']}")
    print("   off:", " ".join(f"{o:4.0f}" for o in offs[sel]))
    print("   L  :", " ".join(f"{v:4.2f}" for v in np.array(r['L'])[sel]))
    print("   S  :", " ".join(f"{v:4.2f}" for v in np.array(r['S'])[sel]))
for r in rows:
    if r["part"] == "all": show(r)
# hub arcs and hole: radial profiles (outward normal = away from material)
th = np.radians(np.arange(0, 360, 0.5))
roffs = offs
def radial(Cx, Cy, Rr, sign, angs):
    X = Cx + (Rr + sign * roffs[None, :]) * np.cos(angs)[:, None]; Y = Cy - (Rr + sign * roffs[None, :]) * np.sin(angs)[:, None]
    return bil(L, X, Y), bil(S, X, Y)
# hub arcs: use gap point angles
for g in F["gaps"]:
    c = np.load(os.path.join(OUT, "contours.npz"))["outer"][g["idx"]]
    ang = np.arctan2(-(c[:, 1] - CH[1]), c[:, 0] - CH[0])
    angs = np.linspace(np.percentile(ang, 20), np.percentile(ang, 80), 30) if np.ptp(ang) < np.pi else None
    if angs is None: continue
    Lp, Sp = radial(CH[0], CH[1], R, +1, angs)
    r = dict(point="hub", side=str(g["between"]), part="arc", nrm=[0, 0], L=np.median(Lp, 0).tolist(), S=np.median(Sp, 0).tolist(), n=len(angs))
    show(r)
# hole: material is outside the hole; outward normal of material points toward hole centre -> sign -1
for lo, hi, tag in ((20, 160, "hole top(lit?)"), (200, 340, "hole bottom"), (160, 200, "hole left"), (-20, 20, "hole right")):
    angs = np.radians(np.linspace(lo, hi, 60))
    Lp, Sp = radial(hole["cx"], hole["cy"], hole["r"], -1, angs)
    show(dict(point="hole", side=tag, part="", nrm=[0, 0], L=np.median(Lp, 0).tolist(), S=np.median(Sp, 0).tolist(), n=len(angs)))
