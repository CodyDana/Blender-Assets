"""Actual metal width across each point vs radius: tip apex, taper slope (=tip angle)."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, imglib as L
OUT = os.path.dirname(os.path.abspath(__file__))
lum = np.load(os.path.join(OUT,"lum.npy")); bgl = np.load(os.path.join(OUT,"bg_lum.npy")); tex = np.load(os.path.join(OUT,"tex.npy"))
res = json.load(open(os.path.join(OUT,"results.json")))
C = np.array(res["centre_px"]); span = res["span_px"]
H, W = lum.shape
def metal(p):
    if not (1 <= p[0] < W-2 and 1 <= p[1] < H-2): return False
    lu = L.bilinear(lum, np.array([p[0]]), np.array([p[1]]))[0]
    b = L.bilinear(bgl, np.array([p[0]]), np.array([p[1]]))[0]
    tx = L.bilinear(tex, np.array([p[0]]), np.array([p[1]]))[0]
    if lu > b - 0.11: return False
    if tx < 0.008: return False
    if lu > 0.30 and tx < 0.012: return False
    return True
print("%-8s %6s %6s %6s | width (px) at r = R-60..R+5 ; apex r ; taper slope -> tip angle" % ("tip","R_virt","angle","clip"))
for v in res["tips"]:
    X = np.array(v["X"]); R = v["r_virtual"]
    ax = (X - C)/np.linalg.norm(X - C); per = np.array([-ax[1], ax[0]])
    rs, ws = [], []
    for r in np.arange(R-80, R+8, 1.0):
        Q = C + r*ax
        hit = [s for s in np.arange(-70, 70.01, 0.5) if metal(Q + s*per)]
        if not hit: w = 0.0
        else:
            # contiguous run containing (or nearest) s=0
            arr = np.array(hit); 
            br = np.where(np.diff(arr) > 1.0)[0]
            segs = np.split(arr, br+1)
            seg = min(segs, key=lambda s_: min(abs(s_.min()), abs(s_.max())) if not (s_.min() <= 0 <= s_.max()) else -1)
            w = float(seg.max() - seg.min())
        rs.append(r); ws.append(w)
    rs = np.array(rs); ws = np.array(ws)
    nz = ws > 2
    apex = rs[nz].max() if nz.any() else float("nan")
    m = (ws > 10) & (ws < 90)
    slope = np.polyfit(rs[m], ws[m], 1)[0] if m.sum() > 5 else float("nan")
    angle = 2*math.degrees(math.atan(-slope/2)) if np.isfinite(slope) else float("nan")
    clip = "IMG-EDGE" if (X + 0*ax)[1] > H-6 or apex > R-1 else ""
    print("%-8s %6.1f %6.2f %6s | apex r %6.1f (%.0f px inside virtual, %.4f span) slope %+.3f -> angle %5.2f" %
          (v["name"], R, v["angle"], clip, apex, R-apex, (R-apex)/span, slope, angle))
    print("        widths: " + " ".join("%.0f" % w for w in ws[::5]))
