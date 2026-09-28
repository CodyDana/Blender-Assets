"""Stage 1: segment Roppo.JPG from its background.

blender -b --factory-startup --python s1_segment.py -- <photo> <outdir>
Writes: dist.png (colour distance map), mask.png (piece incl. holes filled = silhouette
minus holes), mask_filled.png, holes.png, seg.npz (arrays for later stages).
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
photo, outdir = argv[0], argv[1]
os.makedirs(outdir, exist_ok=True)

rgb = imgio.load_rgb(photo)
H, W, _ = rgb.shape
print("size", W, H)

# ---- background model from the border band -------------------------------
B = 10
yy, xx = np.mgrid[0:H, 0:W]
band = np.zeros((H, W), bool)
band[:B, :] = band[-B:, :] = True
band[:, :B] = band[:, -B:] = True
lum = rgb.mean(axis=2)
# drop border pixels that are clearly not background (tips touching the frame)
med = np.median(lum[band])
keep = band & (lum > med - 0.15)
print("border px", band.sum(), "kept", keep.sum(), "median lum", med)

# robust quadratic surface fit per channel over kept border pixels
xs = xx[keep].astype(np.float64) / W
ys = yy[keep].astype(np.float64) / H
A = np.stack([np.ones_like(xs), xs, ys, xs * xs, ys * ys, xs * ys], 1)
Xf = xx.astype(np.float64) / W
Yf = yy.astype(np.float64) / H
Afull = np.stack([np.ones_like(Xf), Xf, Yf, Xf * Xf, Yf * Yf, Xf * Yf], -1)
bg = np.zeros_like(rgb, dtype=np.float64)
coefs = []
for c in range(3):
    v = rgb[:, :, c][keep].astype(np.float64)
    wmask = np.ones_like(v, bool)
    for it in range(4):
        co, *_ = np.linalg.lstsq(A[wmask], v[wmask], rcond=None)
        res = v - A @ co
        s = 1.4826 * np.median(np.abs(res[wmask]))
        wmask = np.abs(res) < 3 * max(s, 1e-3)
    coefs.append(co.tolist())
    bg[:, :, c] = Afull @ co
    print("chan", c, "coef", np.round(co, 4), "resid sigma", round(float(s), 4))

d = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
bd = d[keep]
print("border dist pct 50/95/99/99.9:", np.percentile(bd, [50, 95, 99, 99.9]))

# histogram of distance, to choose threshold (Otsu)
hist, edges = np.histogram(d, bins=256, range=(0, 1))
p = hist / hist.sum()
omega = np.cumsum(p)
mu = np.cumsum(p * (edges[:-1] + edges[1:]) / 2)
mut = mu[-1]
sb = (mut * omega - mu) ** 2 / (omega * (1 - omega) + 1e-12)
t_otsu = float(edges[np.nanargmax(sb) + 1])
print("otsu threshold", t_otsu)
for t in [0.08, 0.10, 0.12, 0.15, 0.2, 0.25, 0.3, t_otsu]:
    print("thr", round(t, 3), "fg frac", round(float((d > t).mean()), 4))

np.save(os.path.join(outdir, "dist.npy"), d.astype(np.float32))
imgio.save_rgb(os.path.join(outdir, "dist.png"), np.clip(d / 0.6, 0, 1))
json.dump({"W": W, "H": H, "bg_coefs": coefs, "t_otsu": t_otsu,
           "border_dist_pct": np.percentile(bd, [50, 95, 99, 99.9]).tolist()},
          open(os.path.join(outdir, "s1_stats.json"), "w"), indent=1)

# chroma/lum diagnostics along a few rows
for y in [100, 523, 900]:
    row = rgb[y]
    print("row", y, "x=5", np.round(row[5], 3), "x=W/2", np.round(row[W // 2], 3), "x=W-5", np.round(row[W - 5], 3))
