# sm_m10: marble lacquer (tone range, vein orientation, correlation lengths) and metal (value, sheen) statistics
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); L = lum(a); rgb = a[..., :3]
fg = np.load(os.path.join(HERE, "sm_sheath_fg.npy"))
prof = np.array(json.load(open(os.path.join(HERE, "sm_s01.json")))["profile"])
edge = {int(r[0]): (int(r[1]), int(r[2])) for r in prof}
out = {}
# metal mask (dilated) to exclude from lacquer
metal = L > 0.42
m = metal.copy()
for _ in range(4):
    g = m.copy(); g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]; m = g
lac = np.zeros_like(fg)
for y in range(340, 1250):
    l, r = edge[y]; c = (l + r) / 2; hw = (r - l) / 2
    lac[y, int(np.ceil(c - 0.82 * hw)):int(np.floor(c + 0.82 * hw)) + 1] = True
lac &= ~m
v = L[lac]
out["lacquer_lum_percentiles"] = {str(q): float(np.percentile(v, q)) for q in (1, 5, 25, 50, 75, 95, 99)}
out["lacquer_rgb_mean"] = rgb[lac].mean(0).tolist()
out["lacquer_rgb_p50_dark_quartile"] = rgb[lac & (L < np.percentile(v, 25))].mean(0).tolist()
out["lacquer_rgb_bright_decile"] = rgb[lac & (L > np.percentile(v, 90))].mean(0).tolist()
out["lacquer_sat_mean"] = float(sat(rgb[lac]).mean())
print("lacquer", json.dumps(out, indent=0))
# structure tensor orientation of veins (gradient smoothed); veins run perpendicular to dominant gradient
Ls = L.copy()
k = np.array([1, 4, 6, 4, 1], float); k /= k.sum()
for ax in (0, 1):
    Ls = np.apply_along_axis(lambda s: np.convolve(s, k, mode="same"), ax, Ls)
gy, gx = np.gradient(Ls)
sel = lac.copy(); sel[:, :2] = False
gxx = (gx * gx)[sel].sum(); gyy = (gy * gy)[sel].sum(); gxy = (gx * gy)[sel].sum()
theta_grad = 0.5 * np.degrees(np.arctan2(2 * gxy, gxx - gyy))
coh = np.sqrt((gxx - gyy) ** 2 + 4 * gxy ** 2) / (gxx + gyy)
# orientation histogram of strong gradients (vein direction = grad + 90)
ang = (np.degrees(np.arctan2(gy[sel], gx[sel])) + 90) % 180  # vein direction, 0 = image horizontal, 90 = vertical (along sheath)
mag = np.hypot(gx[sel], gy[sel])
strong = mag > np.percentile(mag, 80)
h, e = np.histogram(ang[strong], bins=12, range=(0, 180), weights=mag[strong])
out["vein_dir_hist_deg_0horiz_90along"] = {f"{int(e[i])}-{int(e[i+1])}": float(h[i] / h.sum()) for i in range(12)}
out["structure_tensor_grad_angle_deg"] = float(theta_grad); out["coherence"] = float(coh)
print("vein direction histogram (0=across sheath, 90=along sheath):")
for kk, vv in out["vein_dir_hist_deg_0horiz_90along"].items():
    print("  %8s %.3f %s" % (kk, vv, "#" * int(vv * 200)))
print("coherence", coh, "grad angle", theta_grad)
# correlation lengths on the lacquer (centre-face patch), after removing the smooth column trend
def corr_len(axis):
    res = []
    for y0 in range(360, 1200, 60):
        l, r = edge[y0 + 30]; c = int((l + r) / 2)
        patch = L[y0:y0 + 60, c - 18:c + 19].astype(float)
        mk = m[y0:y0 + 60, c - 18:c + 19]
        if mk.mean() > 0.15:
            continue
        p = np.where(mk, np.nan, patch)
        p = p - np.nanmean(p)
        p = np.nan_to_num(p)
        n = p.shape[axis]
        ac = []
        for lag in range(0, min(30, n - 5)):
            if axis == 0:
                a1, a2 = p[:n - lag], p[lag:]
            else:
                a1, a2 = p[:, :n - lag], p[:, lag:]
            ac.append((a1 * a2).mean())
        ac = np.array(ac) / ac[0]
        below = np.where(ac < 1 / np.e)[0]
        res.append(int(below[0]) if len(below) else 30)
    return res
cy = corr_len(0); cx = corr_len(1)
out["lacquer_corr_len_px_along"] = cy; out["lacquer_corr_len_px_across"] = cx
print("corr length (1/e) along sheath px", cy, "median", np.median(cy))
print("corr length across sheath px", cx, "median", np.median(cx))
# vein fraction: pixels brighter than local median + 0.08
vein = lac & (L > np.median(v) + 0.10)
out["vein_pixel_fraction"] = float(vein.sum() / lac.sum())
print("vein fraction", out["vein_pixel_fraction"])
# ---- metal (fittings and vine) -----
def stats(mask, name):
    vv = L[mask]
    d = {str(q): float(np.percentile(vv, q)) for q in (5, 25, 50, 75, 95, 99)}
    d["rgb_mean"] = rgb[mask].mean(0).tolist(); d["sat"] = float(sat(rgb[mask]).mean()); d["n"] = int(mask.sum())
    out[name] = d
    print(name, json.dumps(d))
rows = np.zeros_like(fg); rows[41:142] = True
stats(fg & rows & (L > 0.30), "throat_metal_L>0.30")
stats(fg & rows, "throat_all")
rows = np.zeros_like(fg); rows[1293:1497] = True
stats(fg & rows & (L > 0.30), "chape_metal_L>0.30")
stats(fg & rows, "chape_all")
rows = np.zeros_like(fg); rows[288:321] = True
stats(fg & rows, "midband_all")
# specular-ness: fraction of near-white (L>0.9) pixels in fittings
for nm, (ya, yb) in {"throat": (41, 142), "midband": (288, 321), "chape": (1293, 1497)}.items():
    mk = fg.copy(); mk[:ya] = False; mk[yb:] = False
    out[f"{nm}_frac_L>0.9"] = float((L[mk] > 0.9).mean()); out[f"{nm}_frac_L<0.15"] = float((L[mk] < 0.15).mean())
    print(nm, "frac >0.9 %.3f  frac <0.15 %.3f" % (out[f"{nm}_frac_L>0.9"], out[f"{nm}_frac_L<0.15"]))
# silhouette rim brightness (outer 3px of body both sides) -> edge highlights
rim = []
for y in range(340, 1250):
    l, r = edge[y]
    rim += list(L[y, l:l + 3]) + list(L[y, r - 2:r + 1])
out["body_silhouette_rim_lum_median"] = float(np.median(rim))
print("rim median", np.median(rim))
json.dump(out, open(os.path.join(HERE, "sm_s10.json"), "w"), indent=1)
