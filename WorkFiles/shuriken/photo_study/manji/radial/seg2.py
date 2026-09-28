"""Stage 1b: shadow-robust segmentation.
The scanner throws soft shadows / blur ramps off the up- and right-facing edges which a colour-distance
threshold swallows (up to ~45 px). The metal face is in focus and textured; shadows are smooth.
  1. texture energy E -> coarse metal mask (slightly dilated by the filter support)
  2. trace its contour, then along each inward normal find the sharp luminance step (in-focus edge)
  3. rasterise the refined sub-pixel polygon -> final mask
Outputs: mask.npy/mask.png (final), contour_refined.npy (Nx2 float x,y top-origin), seg2.json, overlays.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

t0 = time.time()


def box(a, r):
    k = 2 * r + 1
    P = np.pad(a, r, mode='edge').astype(np.float64)
    S = np.zeros((P.shape[0] + 1, P.shape[1] + 1))
    S[1:, 1:] = P.cumsum(0).cumsum(1)
    return ((S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]) / (k * k)).astype(np.float32)


rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
g = box(box(box(lum, 2), 2), 2)
E = box(np.abs(lum - g), 4)

# ---- coarse texture mask ----
tE = C.otsu(np.clip(E, 0, 0.05))
print("otsu tE", tE)
tE = min(tE, 0.0065)
m = E > tE
m = C.open_(m, 2)
m = C.close_(m, 6)
runs, roots, areas, touch = C.label_runs(m, True)
big = int(np.argmax(areas))
m = C.paint((h, w), runs, roots == big)
rb, rtb, ab, tb = C.label_runs(~m, False)
for cid in np.unique(rtb):
    if not tb[cid]:
        m |= C.paint((h, w), rb, rtb == cid)
m = C.open_(m, 3)
print("coarse texture mask area", m.sum(), time.time() - t0)
C.save_png(m.astype(np.float32)[::2, ::2], os.path.join(C.OUT, "mask_texture_coarse_half.png"))

# ---- contour + normals ----
cont = C.trace_contour(m).astype(np.float64)
N = len(cont)
print("contour points", N)


def circ_smooth(a, r):
    k = 2 * r + 1
    ext = np.concatenate([a[-r:], a, a[:r]], 0)
    cs = np.cumsum(np.concatenate([np.zeros((1,) + a.shape[1:]), ext], 0), 0)
    return (cs[k:] - cs[:-k]) / k


cs = circ_smooth(cont, 6)
tang = np.roll(cs, -3, 0) - np.roll(cs, 3, 0)
tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12
# contour is clockwise on screen (y down); inward normal = rotate tangent by +90 deg on screen: (x,y)->(-y,x)
nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
# verify orientation: a step inward should be inside the mask
test = cs + 4 * nrm
inside = m[np.clip(test[:, 1].round().astype(int), 0, h - 1), np.clip(test[:, 0].round().astype(int), 0, w - 1)].mean()
if inside < 0.5:
    nrm = -nrm
    inside = 1 - inside
print("normal orientation check (fraction inside)", inside)

# ---- profile search ----
lum_s = box(lum, 1)  # 3x3 mean
S_OUT, S_IN, ST = -10.0, 28.0, 0.5
s = np.arange(S_OUT, S_IN + 1e-9, ST)
offs = np.array([-2, -1, 0, 1, 2], np.float64)
prof = np.zeros((N, len(s)))
for o in offs:
    px = cs[:, 0:1] + nrm[:, 0:1] * s[None, :] + tang[:, 0:1] * o
    py = cs[:, 1:2] + nrm[:, 1:2] * s[None, :] + tang[:, 1:2] * o
    prof += C.bilinear(lum_s, px, py)
prof /= len(offs)
d = np.gradient(prof, ST, axis=1)
# derivative smoothed a little (1.5 px)
kern = np.ones(3) / 3
d = np.apply_along_axis(lambda v: np.convolve(v, kern, mode='same'), 1, d)
ad = np.abs(d)
ad[:, :2] = 0; ad[:, -2:] = 0
k = np.argmax(ad, 1)
# sub-sample parabola refinement
kk = np.clip(k, 1, len(s) - 2)
y0, y1, y2 = ad[np.arange(N), kk - 1], ad[np.arange(N), kk], ad[np.arange(N), kk + 1]
den = (y0 - 2 * y1 + y2)
frac = np.where(np.abs(den) > 1e-9, 0.5 * (y0 - y2) / den, 0)
sstar = s[kk] + np.clip(frac, -1, 1) * ST
sign = np.sign(d[np.arange(N), kk])  # <0: gets darker going inward (bg->metal); >0: brighter inward (shadow->face)
peak = ad[np.arange(N), kk]
# robustify: median filter of sstar along the contour (window 9)
def circ_median(a, r):
    idx = (np.arange(len(a))[:, None] + np.arange(-r, r + 1)[None, :]) % len(a)
    return np.median(a[idx], 1)
sstar_m = circ_median(sstar, 4)
ref = cs + nrm * sstar_m[:, None]
print("s* stats: median %.2f p5 %.2f p95 %.2f ; frac sign>0 (shadow-side steps) %.3f" % (
    np.median(sstar_m), np.percentile(sstar_m, 5), np.percentile(sstar_m, 95), (sign > 0).mean()))

# ---- rasterise refined polygon (even-odd scanline) ----
def rasterise(poly, h, w):
    x = poly[:, 0]; y = poly[:, 1]
    x2 = np.roll(x, -1); y2 = np.roll(y, -1)
    out = np.zeros((h, w), bool)
    ymin, ymax = int(np.floor(y.min())), int(np.ceil(y.max()))
    for row in range(max(ymin, 0), min(ymax + 1, h)):
        yc = row  # pixel centre row
        cond = ((y <= yc) & (y2 > yc)) | ((y2 <= yc) & (y > yc))
        if not cond.any():
            continue
        xi = x[cond] + (yc - y[cond]) * (x2[cond] - x[cond]) / (y2[cond] - y[cond])
        xi.sort()
        for a, b in zip(xi[0::2], xi[1::2]):
            c0 = int(np.ceil(a)); c1 = int(np.floor(b))
            if c1 >= c0:
                out[row, max(c0, 0):min(c1 + 1, w)] = True
    return out

final = rasterise(ref, h, w)
print("final area", final.sum(), "coarse", m.sum())
# holes in final?  (enclosed background components of the colour threshold inside the final outline)
np.save(os.path.join(C.OUT, "mask.npy"), np.packbits(final, axis=None))
np.save(os.path.join(C.OUT, "contour_refined.npy"), ref)
np.save(os.path.join(C.OUT, "contour_aux.npy"), np.stack([sstar, sstar_m, sign, peak], 1))
C.save_png(final.astype(np.float32), os.path.join(C.OUT, "mask.png"))

# overlays: refined edge red, coarse texture edge blue, old colour-threshold edge yellow
ov = rgb.copy()
e_c = m & ~C.erode(m, 1)
ov[e_c] = [0.2, 0.4, 1.0]
e_f = final & ~C.erode(final, 1)
ov[e_f] = [1, 0, 0]
C.save_png(ov, os.path.join(C.OUT, "seg2_overlay_full.png"))
C.save_png(ov[::2, ::2], os.path.join(C.OUT, "seg2_overlay_half.png"))
json.dump(dict(tE=float(tE), coarse_area=float(m.sum()), final_area=float(final.sum()), contour_points=int(N),
               sstar_median=float(np.median(sstar_m)), shadow_side_fraction=float((sign > 0).mean())),
          open(os.path.join(C.OUT, "seg2.json"), "w"), indent=1)
print("done", time.time() - t0)
