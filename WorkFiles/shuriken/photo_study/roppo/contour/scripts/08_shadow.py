# Per-edge outer end of the saturated (ground-bevel) band vs the Otsu boundary; fit a cast-shadow model
# offset(n) = c0 - Ls * max(0, n . s) over the 12 point edges.
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = pickle.load(open(os.path.join(OUT, "bands.pkl"), "rb"))
offs = B["offs"]
edges = []
for r in B["rows"]:
    if r["part"] != "all": continue
    Sv = np.array(r["S"]); Lv = np.array(r["L"])
    Sbg = np.median(Sv[offs >= 8]); inner = (offs >= -24) & (offs <= 0)
    pk = Sv[inner].max(); half = Sbg + 0.5 * (pk - Sbg)
    # outermost crossing of half level going outward from the band peak
    ipk = np.flatnonzero(inner)[np.argmax(Sv[inner])]
    j = ipk
    while j < len(offs) - 1 and Sv[j + 1] >= half: j += 1
    # linear interp between j and j+1
    x = offs[j] + (Sv[j] - half) / max(Sv[j] - Sv[j + 1], 1e-9) * (offs[j + 1] - offs[j])
    # L-ramp width: offsets where L goes from face+10% to bg-10% of (bg-face) outside band
    Lbg = np.median(Lv[offs >= 10]); Lface = np.median(Lv[offs <= -20])
    lo = Lface + 0.1 * (Lbg - Lface); hi = Lface + 0.9 * (Lbg - Lface)
    k_hi = np.flatnonzero((Lv >= hi))[0]
    # outermost position still below lo going outward from S-peak
    edges.append(dict(point=r["point"], side=r["side"], nrm=r["nrm"], s_half=float(x), s_peak_off=float(offs[ipk]),
                      s_peak=float(pk), s_bg=float(Sbg), L_bg=float(Lbg), L_face=float(Lface), L90_off=float(offs[k_hi])))
best = None
for th in np.arange(0, 360, 1.0):
    s = np.array([np.cos(np.radians(th)), np.sin(np.radians(th))])  # image coords (y down)
    X = np.array([max(0.0, np.dot(e["nrm"], s)) for e in edges]); y = np.array([e["s_half"] for e in edges])
    A = np.c_[np.ones_like(X), -X]
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    rr = y - A @ sol; sse = float((rr ** 2).sum())
    if best is None or sse < best[0]: best = (sse, th, sol, rr)
sse, th, sol, rr = best
print(f"shadow model: dir (image, y down) {th:.0f} deg, c0 {sol[0]:.2f}, Ls {sol[1]:.2f}, rms resid {np.sqrt(sse/len(edges)):.2f}")
for e, q in zip(edges, rr):
    print(f"pt{e['point']}{e['side']} nrm({e['nrm'][0]:+.2f},{e['nrm'][1]:+.2f}) S_half {e['s_half']:+.2f} S_peak@{e['s_peak_off']:+.1f} ({e['s_peak']:.2f}) L90@{e['L90_off']:+.1f} resid {q:+.2f}")
lit = [e["s_half"] for e, in zip(edges) if max(0, np.dot(e["nrm"], [np.cos(np.radians(th)), np.sin(np.radians(th))])) < 0.05]
print("lit-edge s_half values", np.round(lit, 2), "median", np.median(lit))
pickle.dump(dict(edges=edges, shadow_dir_deg=float(th), c0=float(sol[0]), Ls=float(sol[1]), rms=float(np.sqrt(sse / len(edges))), lit_s_half=[float(v) for v in lit]),
            open(os.path.join(OUT, "shadow.pkl"), "wb"))
