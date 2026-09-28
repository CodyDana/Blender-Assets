# Width profile of each point along its axis (hub centre frame) and local edge angles.
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = np.load(os.path.join(OUT, "contours.npz")); outer = c["outer"]
F = pickle.load(open(os.path.join(OUT, "fit.pkl"), "rb"))
points, hub = F["points"], F["hub"]
CH = np.array([hub["cx"], hub["cy"]]); R = hub["r"]
H = 1047
n = len(outer)
def side_profile(idx, a, ap):
    P = outer[idx]
    keep = P[:, 1] < H - 1
    P = P[keep]
    rho = (P - CH) @ a; q = (P - CH) @ ap
    o = np.argsort(rho)
    return rho[o], q[o]
out = []
for i, p in enumerate(points):
    a = p["tip_geo"] - CH; a /= np.linalg.norm(a)
    ap = np.array([-a[1], a[0]])
    rA, qA = side_profile(p["A"]["all_idx"], a, ap)
    rB, qB = side_profile(p["B"]["all_idx"], a, ap)
    rho_tip_pix = float(((outer[p["tip_idx"]] - CH) @ a))
    grid = np.arange(300, rho_tip_pix, 10.0)
    # for each rho, lateral position of each side (median of points within +-1.5)
    def q_at(rr, qq, g):
        m = np.abs(rr - g) < 1.5
        return np.median(qq[m]) if m.any() else np.nan
    wA = np.array([q_at(rA, qA, g) for g in grid]); wB = np.array([q_at(rB, qB, g) for g in grid])
    width = np.abs(wA - wB)
    ctr = (wA + wB) / 2
    # local half-angle by windowed slope (40 px windows)
    loc = []
    for g0 in np.arange(300, rho_tip_pix - 20, 40.0):
        m = (grid >= g0) & (grid < g0 + 40) & ~np.isnan(width)
        if m.sum() >= 3:
            s = np.polyfit(grid[m], width[m], 1)[0]
            loc.append((float(g0), float(np.degrees(2 * np.arctan(abs(s) / 2)))))
    print(f"point {i} rho_tip_pix {rho_tip_pix:.1f}  axis_deg {np.degrees(np.arctan2(-a[1], a[0])):.1f}")
    print("   rho  :", " ".join(f"{g:5.0f}" for g in grid))
    print("   width:", " ".join(f"{v:5.1f}" for v in width))
    print("   ctr  :", " ".join(f"{v:5.1f}" for v in ctr))
    print("   local included angle per 40px window:", [(int(g), round(v, 1)) for g, v in loc])
    out.append(dict(point=i, rho_tip_pix=rho_tip_pix, grid=grid.tolist(), width=width.tolist(), local=loc))
pickle.dump(out, open(os.path.join(OUT, "widthprof.pkl"), "wb"))
