"""Stage 18: straight-line fit of each tracked rib boundary in image space, then least-squares convergence point C and a
common signed edge offset h (distance C->line). Compares C with the rivet highlight centroid."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json")))
res = {}
for i in (2, 1):
    cx, cy = S2[str(i)]["rivet_bright_centroid"]
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy")); L = P @ LUMW.astype(np.float32)
    Ls = L.copy(); Ls[1:-1] = (L[:-2] + L[1:-1] + L[2:])/3
    th = -20 + 0.1*np.arange(L.shape[1])
    T = json.load(open(os.path.join(OUT, "fm_s17_ribtrack.json")))[str(i)]
    rtop = 138 if i == 2 else 175
    lines = []
    for tr in T:
        if tr['rms_deg'] > 0.6: continue
        cur = tr['start']; pts = []
        for r in range(rtop, 50, -1):
            j = int(round((cur+20)*10)); w = 10 if r > 80 else 15
            seg = Ls[r, j-w:j+w+1]; base = np.convolve(seg, np.ones(9)/9, 'same')
            k = int(np.argmin(seg - 0.5*base + 0.002*np.abs(np.arange(-w, w+1))))
            cur = th[j-w+k]
            pts.append((cx + r*np.cos(np.radians(cur)), cy - r*np.sin(np.radians(cur))))
        pts = np.array(pts)
        c0 = pts.mean(0); U, S, Vt = np.linalg.svd(pts - c0); d = Vt[0]; n = np.array([-d[1], d[0]])
        # orient normal so that it points toward increasing theta (counter-clockwise around the rivet, y-down image)
        radial = c0 - np.array([cx, cy]); tang = np.array([radial[1], -radial[0]])  # ccw in y-up == this in y-down
        if np.dot(n, tang) < 0: n = -n
        rms = float(np.sqrt(np.mean(((pts - c0) @ n)**2)))
        lines.append(dict(n=n.tolist(), d=float(n @ c0), rms_px=round(rms, 3), start=tr['start']))
    A = np.array([[l['n'][0], l['n'][1], -1.0] for l in lines]); b = np.array([l['d'] for l in lines])
    sol, *_ = np.linalg.lstsq(A, b, rcond=None); Cx, Cy, h = sol
    resid = A @ sol - b
    # also: C with h fixed at 0
    sol0, *_ = np.linalg.lstsq(A[:, :2], b, rcond=None); resid0 = A[:, :2] @ sol0 - b
    res[i] = dict(n_lines=len(lines), C=[round(float(Cx), 2), round(float(Cy), 2)], h_common_px=round(float(h), 2),
                  rms_px=round(float(np.sqrt(np.mean(resid**2))), 2), C_minus_rivet=[round(float(Cx-cx), 2), round(float(Cy-cy), 2)],
                  C_h0=[round(float(sol0[0]), 2), round(float(sol0[1]), 2)], rms_h0=round(float(np.sqrt(np.mean(resid0**2))), 2),
                  line_rms_px=[l['rms_px'] for l in lines])
json.dump(res, open(os.path.join(OUT, "fm_s18_convergence.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
