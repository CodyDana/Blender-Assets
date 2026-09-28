"""Stage 17: track each rib boundary (dark line between bare ribs) from the leaf edge down toward the pivot in the polar image,
then fit theta_b(r) = theta_k + deg(asin(h/r)) with h constant (boundary = straight line offset h from a ray through the rivet).
Gives each boundary's ray angle theta_k and its perpendicular offset h (px) from the rivet."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
E = json.load(open(os.path.join(OUT, "fm_s10_spacingfit.json")))
cfg = {2: dict(start=E['2_ribmin']['values'], rtop=138, rbot=40), 1: dict(start=E['1_ribmin']['values'], rtop=175, rbot=40)}
res = {}
for i in (2, 1):
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy")); L = P @ LUMW.astype(np.float32)
    th = -20 + 0.1*np.arange(L.shape[1])
    # smooth rows slightly in r
    Ls = L.copy(); Ls[1:-1] = (L[:-2] + L[1:-1] + L[2:])/3
    tracks = []
    for t_start in cfg[i]['start']:
        cur = t_start; pts = []
        for r in range(cfg[i]['rtop'], cfg[i]['rbot'], -2):
            j = int(round((cur+20)*10)); w = 12 if r > 80 else 18
            seg = Ls[r, j-w:j+w+1]
            if len(seg) < 2*w+1: break
            # local minimum closest to the prediction, weighted by depth
            base = np.convolve(seg, np.ones(9)/9, 'same')
            k = int(np.argmin(seg - 0.5*base + 0.002*np.abs(np.arange(-w, w+1))))
            cur = th[j-w+k]; pts.append((r, float(cur)))
        pts = np.array(pts)
        if len(pts) < 10: continue
        r = pts[:, 0]; t = pts[:, 1]
        # fit t = tk + deg(asin(h/r)) by grid on h
        best = None
        for h in np.arange(-25, 25.01, 0.25):
            model = np.degrees(np.arcsin(np.clip(h/r, -1, 1)))
            tk = np.median(t - model); rr = t - model - tk
            e = float(np.sqrt(np.mean(rr**2)))
            if best is None or e < best[0]: best = (e, h, tk)
        tracks.append(dict(start=t_start, theta_k=round(float(best[2]), 2), h_px=float(best[1]), rms_deg=round(best[0], 3),
                           t_at_r=[[int(a), round(b, 1)] for a, b in pts[::5]]))
    res[i] = tracks
json.dump(res, open(os.path.join(OUT, "fm_s17_ribtrack.json"), "w"), indent=0)
for i in (2, 1):
    print(f"FAN{i}")
    for tr in res[i]:
        print(f"  start {tr['start']:6.1f}  theta_k {tr['theta_k']:7.2f}  h {tr['h_px']:6.2f}  rms {tr['rms_deg']:.3f}   samples {tr['t_at_r']}")
