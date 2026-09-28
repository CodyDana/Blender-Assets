# Bevel-band width along each point edge (station groups root->tip) and junction notch analysis (shadow-corrected model).
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seg = np.load(os.path.join(OUT, "seg.npz")); Lm, Sm = seg["L"], seg["S"]
Hh, Ww = Lm.shape
FN = pickle.load(open(os.path.join(OUT, "final.pkl"), "rb"))
SH = pickle.load(open(os.path.join(OUT, "shadow.pkl"), "rb"))
RAW, COR = FN["RAW"], FN["COR"]
sdir = FN["sdir"]
cz = np.load(os.path.join(OUT, "contours.npz")); outer_raw = cz["outer"]


def bil(img, x, y):
    x = np.clip(x, 0, Ww - 1.001); y = np.clip(y, 0, Hh - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


offs = np.arange(-30, 15.01, 0.25)
res = {"edges": [], "junctions": []}
CH = COR["CH"]; RH = COR["hub"]["r"]
print("bevel band per edge (RAW line frame; offsets relative to the raw Otsu line; lit = n.s<=0.05)")
for i, p in enumerate(RAW["pts"]):
    pc = COR["pts"][i]
    for s in ("A", "B"):
        e = p[s]; cen, d, nv = e["cen"], e["dir"], e["nrm"]
        ns = float(np.dot(nv, sdir)); lit = ns <= 0.05
        t_root = np.dot(e["root"] - cen, d); t_apex = np.dot(p["apex"] - cen, d)
        t_obs = np.dot(p["obs_tip"] - cen, d)
        rows = []
        for f0, f1 in ((0.0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0)):
            # stations measured along root -> observed tip
            ts = np.linspace(t_root + f0 * (t_obs - t_root), t_root + f1 * (t_obs - t_root), 12)
            P = cen[None] + ts[:, None] * d[None]
            X = P[:, None, 0] + offs[None, :] * nv[0]; Y = P[:, None, 1] + offs[None, :] * nv[1]
            ok = Y.max(1) < Hh - 2
            if ok.sum() < 3:
                rows.append(None); continue
            Lp = np.median(bil(Lm, X, Y)[ok], 0); Sp = np.median(bil(Sm, X, Y)[ok], 0)
            # half-level crossings on S around its peak within [-25, +2]
            win = (offs >= -25) & (offs <= 2)
            Sbg = np.median(Sp[offs >= 8]); Sface = np.median(Sp[(offs >= -30) & (offs <= -24)])
            ip = np.flatnonzero(win)[np.argmax(Sp[win])]; pk = Sp[ip]
            ho = Sbg + 0.5 * (pk - Sbg); hi_ = Sface + 0.5 * (pk - Sface)
            j = ip
            while j < len(offs) - 1 and Sp[j + 1] >= ho: j += 1
            k = ip
            while k > 0 and Sp[k - 1] >= hi_: k -= 1
            s_out, s_in = offs[j], offs[k]
            # L-based band for lit edges: band pixels brighter than face by >35% of (bg-face) but below bg-level transition
            Lbg = np.median(Lp[offs >= 8]); Lface = np.median(Lp[(offs >= -30) & (offs <= -24)])
            thr_in = Lface + 0.35 * (Lbg - Lface)
            jj = np.flatnonzero((offs <= 0.5) & (Lp < thr_in))
            l_in = offs[jj.max()] if len(jj) else np.nan
            rows.append(dict(f=(f0, f1), s_in=float(s_in), s_out=float(s_out), s_width=float(s_out - s_in), s_peak=float(pk), s_face=float(Sface),
                             L_in=float(l_in), L_face=float(Lface), L_bg=float(Lbg)))
        res["edges"].append(dict(point=i, side=s, n_dot_s=ns, lit=lit, rows=rows))
        print(f" pt{i}{s} n.s {ns:+.2f} {'LIT   ' if lit else 'SHADOW'} " + " | ".join(
            (f"{r['f'][0]:.1f}-{r['f'][1]:.1f}: S[{r['s_in']:+.1f},{r['s_out']:+.1f}] w{r['s_width']:.1f} pk{r['s_peak']:.2f}/face{r['s_face']:.2f} Lin{r['L_in']:+.1f}" if r else "--") for r in rows))

# ---- junction notch analysis on the shadow-corrected contour
outer = FN["outer_cor"]
n = len(outer)
r_c = np.hypot(*(outer - CH).T)
print("\njunction deviations from model (hub circle U straight edge), shadow-corrected contour; negative = material missing")
for i, p in enumerate(COR["pts"]):
    for s in ("A", "B"):
        e = p[s]; cen, d, nv, root = e["cen"], e["dir"], e["nrm"], e["root"]
        # contour points within 30 px of the root point
        dist = np.linalg.norm(outer - root, axis=1)
        idx = np.flatnonzero(dist < 30)
        P = outer[idx]
        d_line = (P - cen) @ nv            # + outside the point edge
        d_circ = np.hypot(*(P - CH).T) - RH  # + outside hub
        # inside the model iff inside hub OR inside the point wedge (d_line<0 and beyond root along d)
        along = (P - root) @ d               # + toward tip
        # signed distance approx: if along>0 (edge side) use min(d_line, d_circ) ; else use d_circ bounded by line
        sd = np.where(along > 0, np.minimum(d_line, np.maximum(d_circ, d_line)), np.minimum(d_circ, np.maximum(d_line, d_circ)))
        sd = np.minimum(d_line, d_circ) if True else sd
        # the union's boundary: signed distance of union = min(d_wedge, d_disc); d_wedge ~ d_line near the root on the edge side
        jmin = int(np.argmin(sd)); jmax = int(np.argmax(sd))
        deep = idx[sd < -1.5]
        res["junctions"].append(dict(point=i, side=s, root=root.tolist(), min_dev=float(sd[jmin]), min_at=P[jmin].tolist(),
                                     min_along=float(along[jmin]), max_dev=float(sd[jmax]), n_below_1p5=int(len(deep))))
        print(f" pt{i}{s} root({root[0]:.0f},{root[1]:.0f}) min dev {sd[jmin]:+.2f} px at ({P[jmin][0]:.0f},{P[jmin][1]:.0f}) along {along[jmin]:+.1f} | max {sd[jmax]:+.2f} | n<-1.5px {len(deep)}")
pickle.dump(res, open(os.path.join(OUT, "bevel_notch.pkl"), "wb"))
