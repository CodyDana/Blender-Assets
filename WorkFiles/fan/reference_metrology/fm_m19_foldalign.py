"""Stage 19: fan2 fold alignment. Extend the fitted bare-zone rib-boundary lines (stage 18 method) into the leaf and compare
their angles at r = 200 and 260 with the leaf profile extrema (dark creases / light faces) in narrow bands at those radii."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json")))
i = 2
cx, cy = S2["2"]["rivet_bright_centroid"]
P = np.load(os.path.join(OUT, "fm_polar2.npy")); L = P @ LUMW.astype(np.float32)
Ls = L.copy(); Ls[1:-1] = (L[:-2] + L[1:-1] + L[2:])/3
th = -20 + 0.1*np.arange(L.shape[1])
T = json.load(open(os.path.join(OUT, "fm_s17_ribtrack.json")))["2"]
mx = P.max(2); mn = P.min(2); sat = (mx-mn)/(mx+1e-4)
design = (L > 0.30) | ((sat > 0.35) & (mx > 0.15))
out = dict(lines=[], bands={})
for tr in T:
    cur = tr['start']; pts = []
    for r in range(138, 60, -1):
        j = int(round((cur+20)*10)); w = 10
        seg = Ls[r, j-w:j+w+1]; base = np.convolve(seg, np.ones(9)/9, 'same')
        k = int(np.argmin(seg - 0.5*base + 0.002*np.abs(np.arange(-w, w+1))))
        cur = th[j-w+k]; pts.append((cx + r*np.cos(np.radians(cur)), cy - r*np.sin(np.radians(cur))))
    pts = np.array(pts); c0 = pts.mean(0); U, S, Vt = np.linalg.svd(pts - c0); d = Vt[0]
    ang = {}
    for R in (200, 260, 320):
        # intersect line c0 + s d with circle |p - c| = R (take the far solution)
        f = c0 - np.array([cx, cy]); bq = 2*np.dot(f, d); cq = np.dot(f, f) - R*R
        s1 = (-bq + np.sqrt(bq*bq - 4*cq))/2; s2 = (-bq - np.sqrt(bq*bq - 4*cq))/2
        cand = [c0 + s*d for s in (s1, s2)]
        p = max(cand, key=lambda q: -(q[1]))  # the one higher in the image
        ang[R] = round(float(np.degrees(np.arctan2(cy - p[1], p[0] - cx))), 2)
    out['lines'].append(dict(start=tr['start'], at_r=ang))
for R in (200, 260, 320):
    B = np.where(design[R-8:R+8], np.nan, Ls[R-8:R+8]); prof = np.nanmedian(B, 0)
    p = np.where(np.isnan(prof), np.nanmean(prof), prof)
    p = np.convolve(p, np.ones(5)/5, 'same'); d = p - np.convolve(p, np.ones(66)/66, 'same')
    mins = [round(float(th[j]), 1) for j in range(40, len(d)-40) if 8 < th[j] < 176 and d[j] == d[j-25:j+26].min()]
    maxs = [round(float(th[j]), 1) for j in range(40, len(d)-40) if 8 < th[j] < 176 and d[j] == d[j-25:j+26].max()]
    out['bands'][R] = dict(dark=mins, light=maxs)
json.dump(out, open(os.path.join(OUT, "fm_s19_foldalign.json"), "w"), indent=0)
for R in (200, 260, 320):
    print(f"R{R} lines:", [l['at_r'][R] for l in out['lines']])
    print(f"R{R} dark :", out['bands'][R]['dark'])
    print(f"R{R} light:", out['bands'][R]['light'])
