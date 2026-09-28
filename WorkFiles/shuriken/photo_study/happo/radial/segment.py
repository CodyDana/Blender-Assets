"""Stage 1: segment Happo.JPG from its background.

Background colour is modelled from the image border (robust per-channel plane fit),
pixels are classified by Euclidean distance in (sRGB-encoded) colour space,
threshold by Otsu on the distance histogram, cleaned with morphology, largest
component kept, interior holes = background components not touching the border.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

SRC = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Happo.JPG"
OUT = os.path.dirname(os.path.abspath(__file__))

rgb, W, H = L.load_rgb(SRC)
print("size", W, H, rgb.dtype, rgb.min(), rgb.max())

# ---- background model from a border strip ----
B = 5
yy, xx = np.mgrid[0:H, 0:W]
border = np.zeros((H, W), bool)
border[:B, :] = border[-B:, :] = True
border[:, :B] = border[:, -B:] = True
bx = xx[border].astype(np.float64) / W
by = yy[border].astype(np.float64) / H
bc = rgb[border].astype(np.float64)
keep = np.ones(len(bx), bool)
A = np.stack([np.ones_like(bx), bx, by], 1)
for it in range(5):
    coef, *_ = np.linalg.lstsq(A[keep], bc[keep], rcond=None)
    res = bc - A @ coef
    rn = np.linalg.norm(res, axis=1)
    med = np.median(rn[keep])
    mad = np.median(np.abs(rn[keep] - med)) + 1e-6
    keep = rn < med + 6 * 1.4826 * mad
print("bg plane coef (rows: 1,x,y; cols RGB)\n", coef)
print("border inliers", keep.mean(), "resid median", med)
bg = (np.stack([np.ones((H, W)), xx / W, yy / H], -1) @ coef).astype(np.float32)
dist = np.linalg.norm(rgb - bg, axis=2)
bd = dist[border][keep]
print("border dist: median %.4f p99 %.4f max %.4f" % (np.median(bd), np.percentile(bd, 99), bd.max()))

# ---- Otsu threshold on distance ----
hist, edges = np.histogram(dist, bins=512, range=(0, float(dist.max())))
centers = 0.5 * (edges[1:] + edges[:-1])
p = hist / hist.sum()
w0 = np.cumsum(p)
m0 = np.cumsum(p * centers)
mt = m0[-1]
between = (mt * w0 - m0) ** 2 / (w0 * (1 - w0) + 1e-12)
t_otsu = centers[np.argmax(between)]
# modes
bgmode = np.median(dist[border][keep])
fgmode = np.median(dist[dist > t_otsu])
print("otsu %.4f  bg mode %.4f  fg median %.4f" % (t_otsu, bgmode, fgmode))
# print a coarse histogram
hc, ec = np.histogram(dist, bins=40, range=(0, float(dist.max())))
for c, e in zip(hc, ec):
    print("  %.3f %8d" % (e, c))

mask0 = dist > t_otsu
mask = L.opening(mask0, 2)
mask = L.closing(mask, 2)
lab, sizes = L.label(mask)
big = max(sizes, key=sizes.get)
print("fg components", len(sizes), "largest", sizes[big], "others (top5)",
      sorted([v for k, v in sizes.items() if k != big], reverse=True)[:5])
piece = lab == big

# holes = background comps not touching border
blab, bsizes = L.label(~piece)
edge_labels = set(np.unique(np.concatenate([blab[0], blab[-1], blab[:, 0], blab[:, -1]]))) - {0}
holes = {k: v for k, v in bsizes.items() if k not in edge_labels}
print("background comps", len(bsizes), "touching border", len(edge_labels), "enclosed holes", holes)
filled = piece.copy()
for k in holes:
    filled |= blab == k

# raw (pre-morphology) enclosed-background check too, to catch small holes lost to closing
rlab, rsizes = L.label(~mask0)
redge = set(np.unique(np.concatenate([rlab[0], rlab[-1], rlab[:, 0], rlab[:, -1]]))) - {0}
rholes = sorted([v for k, v in rsizes.items() if k not in redge], reverse=True)
print("raw enclosed bg specks (px), top 10:", rholes[:10])

# soft alpha: 0 at bg level, 1 at typical fg level, for sub-pixel boundary
alpha = np.clip((dist - bgmode) / (fgmode - bgmode), 0, 1).astype(np.float32)

np.save(os.path.join(OUT, "dist.npy"), dist.astype(np.float32))
np.save(os.path.join(OUT, "mask_filled.npy"), filled)
np.save(os.path.join(OUT, "rgb.npy"), rgb.astype(np.float32))
L.save_png(os.path.join(OUT, "happo_mask.png"), filled.astype(np.float32))

# overlay: mask edge in red on image, removed/added pixels
ov = rgb.copy()
edge = filled & ~L.erode(filled, 1)
ov[edge] = [1, 0, 0]
added = filled & ~mask0
removed = mask0 & ~filled
ov[added] = ov[added] * 0.5 + np.array([0, 0.5, 1]) * 0.5
ov[removed] = ov[removed] * 0.5 + np.array([1, 0.5, 0]) * 0.5
L.save_png(os.path.join(OUT, "seg_check.png"), ov)

ys, xs = np.nonzero(filled)
stats = dict(W=W, H=H, t_otsu=float(t_otsu), bg_dist_mode=float(bgmode), fg_dist_median=float(fgmode),
             bg_coef=coef.tolist(), area_px=int(filled.sum()), n_fg_components=len(sizes),
             enclosed_holes_px=list(holes.values()), raw_enclosed_specks_top=rholes[:10],
             centroid_xy=[float(xs.mean()), float(ys.mean())],
             bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
             added_by_morph=int(added.sum()), removed_by_morph=int(removed.sum()))
json.dump(stats, open(os.path.join(OUT, "seg_stats.json"), "w"), indent=1)
print(json.dumps(stats, indent=1))
