# Primitive fitting on the traced contour: edge lines, tips, hub circle, hole circle, junction notches,
# width profiles, bevel-band profiles. Writes results.json.
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = np.load(os.path.join(OUT, "contours.npz"))
seg = np.load(os.path.join(OUT, "seg.npz"))
L, S = seg["L"], seg["S"]
H, W = L.shape
outer = c["outer"].copy(); hc = c["hole"].copy()
n = len(outer)
onborder = (outer[:, 1] >= H - 1) | (outer[:, 1] <= 0) | (outer[:, 0] <= 0) | (outer[:, 0] >= W - 1)

hole = fit_circle(hc)
C0 = np.array([hole["cx"], hole["cy"]])
d = outer - C0; r = np.hypot(*d.T)
k = 7
rs = np.convolve(np.r_[r[-k:], r, r[:k]], np.ones(2 * k + 1) / (2 * k + 1), 'valid')
w = 150
peaks = [i for i in range(n) if rs[i] == max(rs[(i + j) % n] for j in range(-w, w + 1)) and rs[i] > np.percentile(rs, 80)]
mins = [i for i in range(n) if rs[i] == min(rs[(i + j) % n] for j in range(-w, w + 1))]
assert len(peaks) == 6 and len(mins) == 6, (peaks, mins)

def cidx(a, b):
    """contour indices from a to b inclusive going forward (wrapping)."""
    if b >= a: return np.arange(a, b + 1)
    return np.r_[np.arange(a, n), np.arange(0, b + 1)]

# pair each tip with the minimum before and after it along the contour
res = dict(image=dict(w=W, h=H), hole_fit_trace=hole)
points = []
mins_sorted = sorted(mins)
for t in peaks:
    before = max([m for m in mins_sorted if m < t], default=mins_sorted[-1])
    after = min([m for m in mins_sorted if m > t], default=mins_sorted[0])
    points.append(dict(tip_idx=t, min_before=before, min_after=after))

R_hub0 = float(np.median(r[mins]))
def edge_fit(idx, rtip, lo_frac=0.15, hi_frac=0.92):
    rr = r[idx]
    rlo = R_hub0 + lo_frac * (rtip - R_hub0); rhi = R_hub0 + hi_frac * (rtip - R_hub0)
    sel = idx[(rr > rlo) & (rr < rhi) & ~onborder[idx]]
    cen, dirv, rms, mx = fit_line(outer[sel])
    return sel, cen, dirv, rms, mx

for p in points:
    t = p["tip_idx"]
    rtip = r[t]
    sideA = cidx(p["min_before"], t)   # contour before tip
    sideB = cidx(t, p["min_after"])
    for name, idx in (("A", sideA), ("B", sideB)):
        sel, cen, dirv, rms, mx = edge_fit(idx, rtip)
        # orient direction from root toward tip
        if np.dot(outer[t] - cen, dirv) < 0: dirv = -dirv
        p[name] = dict(sel=sel, cen=cen, dir=dirv, rms=rms, maxres=mx, n=len(sel), all_idx=idx)
    tipg = line_intersect(p["A"]["cen"], p["A"]["dir"], p["B"]["cen"], p["B"]["dir"])
    p["tip_geo"] = tipg
    ang = np.degrees(np.arccos(np.clip(np.dot(-p["A"]["dir"], -p["B"]["dir"]), -1, 1)))
    p["tip_angle"] = float(ang)
    bis = -(p["A"]["dir"] + p["B"]["dir"]); bis /= np.linalg.norm(bis)  # from tip toward centre
    p["axis"] = bis
    # outward normals for each edge (pointing away from the point axis)
    for name in ("A", "B"):
        dv = p[name]["dir"]; nv = np.array([-dv[1], dv[0]])
        mid = p[name]["cen"]
        # axis point at same distance
        proj = tipg + np.dot(mid - tipg, bis) * bis
        if np.dot(mid - proj, nv) < 0: nv = -nv
        p[name]["nrm"] = nv

# ---- hub circle from exposed arcs: contour points in each gap far from both adjacent edge lines
def dist_line(P, cen, dirv, nrm):
    return (P - cen) @ nrm
pts_by_gap = []
order = sorted(range(6), key=lambda i: points[i]["tip_idx"])
for gi in range(6):
    pa = points[order[gi]]; pb = points[order[(gi + 1) % 6]]
    idx = cidx(pa["tip_idx"], pb["tip_idx"])
    P = outer[idx]
    da = dist_line(P, pa["B"]["cen"], pa["B"]["dir"], pa["B"]["nrm"])
    db = dist_line(P, pb["A"]["cen"], pb["A"]["dir"], pb["A"]["nrm"])
    rr = r[idx]
    sel = idx[(da > 12) & (db > 12) & (rr < R_hub0 + 40)]
    pts_by_gap.append(dict(idx=sel, between=(order[gi], order[(gi + 1) % 6])))
allarc = np.concatenate([g["idx"] for g in pts_by_gap])
hub = fit_circle(outer[allarc])
CH = np.array([hub["cx"], hub["cy"]])
for g in pts_by_gap:
    P = outer[g["idx"]]
    g["fit_free"] = fit_circle(P) if len(P) > 10 else None
    rr = np.hypot(*(P - CH).T)
    g["r_fixed_centre"] = float(rr.mean()); g["r_fixed_sd"] = float(rr.std()); g["n"] = len(P)
    g["ang_span_deg"] = float(np.ptp(np.unwrap(np.arctan2(-(P - CH)[:, 1], (P - CH)[:, 0]))) * 180 / np.pi)

# ---- tip circle
tips = np.array([p["tip_geo"] for p in points])
tipc = fit_circle(tips)

res["hub_fit_all_arcs"] = hub
res["tip_circle_fit"] = tipc
json.dump(dict(), open(os.devnull, "w"))
np.save(os.path.join(OUT, "tmp_points.npy"), np.array([0]))
import pickle
pickle.dump(dict(points=points, gaps=pts_by_gap, hub=hub, hole=hole, tipc=tipc, C0=C0, R_hub0=R_hub0, peaks=peaks, mins=mins), open(os.path.join(OUT, "fit.pkl"), "wb"))

print("hole", {k: round(v, 3) for k, v in hole.items() if isinstance(v, float)})
print("hub ", {k: round(v, 3) for k, v in hub.items() if isinstance(v, float)}, "n", len(allarc))
print("tipc", {k: round(v, 3) for k, v in tipc.items() if isinstance(v, float)})
for i, p in enumerate(points):
    print(i, "tip_idx", p["tip_idx"], "tip_geo", p["tip_geo"].round(1), "pix", outer[p["tip_idx"]], "angle", round(p["tip_angle"], 2),
          "A rms/max/n", round(p["A"]["rms"], 2), round(p["A"]["maxres"], 2), p["A"]["n"],
          "B rms/max/n", round(p["B"]["rms"], 2), round(p["B"]["maxres"], 2), p["B"]["n"])
for g in pts_by_gap:
    ff = g["fit_free"]
    print("gap", g["between"], "n", g["n"], "span", round(g["ang_span_deg"], 1), "r@hubC", round(g["r_fixed_centre"], 2), "+-", round(g["r_fixed_sd"], 2),
          "free", None if ff is None else (round(ff["cx"], 1), round(ff["cy"], 1), round(ff["r"], 1), round(ff["rms"], 2)))
