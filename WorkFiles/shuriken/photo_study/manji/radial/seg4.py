"""Stage 1c: shadow-robust segmentation (final).
Colour-distance threshold (seg.py) captures metal PLUS the scanner's soft shadows on up/right-facing edges.
The metal face is the in-focus plane: its outline is always a SHARP luminance step, while shadow ramps are
broad. Along the inward normal of the colour-mask contour we take the OUTERMOST sharp step with a
face-like inner side, then carve away everything outside it.
Outputs: mask.npy / mask.png (final), refined_pts.npy (x, y, s*, ok), seg3.json, overlays.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

t0 = time.time()
rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
lum = (rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)).astype(np.float32)

# ---------- colour-distance mask (same recipe as seg.py) ----------
B = 40
border = np.zeros((h, w), bool); border[:B] = border[-B:] = True; border[:, :B] = border[:, -B:] = True
c0 = np.median(rgb[border], axis=0)
fg0 = np.linalg.norm(rgb - c0, axis=2) > C.otsu(np.linalg.norm(rgb - c0, axis=2))
BS = 64
excl = C.dilate(fg0, 12)
ny, nx = (h + BS - 1) // BS, (w + BS - 1) // BS
grid = np.full((ny, nx, 3), np.nan, np.float32)
for j in range(ny):
    for i in range(nx):
        ok = ~excl[j * BS:(j + 1) * BS, i * BS:(i + 1) * BS]
        if ok.sum() > 0.3 * ok.size:
            grid[j, i] = np.median(rgb[j * BS:(j + 1) * BS, i * BS:(i + 1) * BS][ok], axis=0)
valid = ~np.isnan(grid[..., 0]); g = np.where(valid[..., None], grid, 0)
for it in range(400):
    p = np.pad(g, ((1, 1), (1, 1), (0, 0)), mode='edge')
    g = np.where(valid[..., None], grid, (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4)
yc = (np.arange(ny) + 0.5) * BS - 0.5; xc = (np.arange(nx) + 0.5) * BS - 0.5
FX, FY = np.meshgrid(np.clip(np.interp(np.arange(w), xc, np.arange(nx)), 0, nx - 1),
                     np.clip(np.interp(np.arange(h), yc, np.arange(ny)), 0, ny - 1))
bg = C.bilinear(g, FX, FY).astype(np.float32)
bg_lum = bg @ np.array([0.2126, 0.7152, 0.0722], np.float32)
D = np.linalg.norm(rgb - bg, axis=2)
tcol = C.otsu(D)
cm = C.open_(C.close_(D > tcol, 2), 2)
runs, roots, areas, touch = C.label_runs(cm, True)
cm = C.paint((h, w), runs, roots == int(np.argmax(areas)))
rb, rtb, ab, tb = C.label_runs(~cm, False)
colour_holes = [float(ab[c]) for c in np.unique(rtb) if not tb[c]]
for c in np.unique(rtb):
    if not tb[c]:
        cm |= C.paint((h, w), rb, rtb == c)
print("colour mask area", cm.sum(), "enclosed bg comps", colour_holes, time.time() - t0)

# ---------- contour + normals ----------
cont = C.trace_contour(cm).astype(np.float64)
N = len(cont)


def circ_smooth(a, r):
    k = 2 * r + 1
    ext = np.concatenate([a[-r:], a, a[:r]], 0)
    cs = np.cumsum(np.concatenate([np.zeros((1,) + a.shape[1:]), ext], 0), 0)
    return (cs[k:] - cs[:-k]) / k


cs = circ_smooth(cont, 8)
tang = np.roll(cs, -4, 0) - np.roll(cs, 4, 0)
tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12
nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
test = cs + 5 * nrm
fin = cm[np.clip(test[:, 1].round().astype(int), 0, h - 1), np.clip(test[:, 0].round().astype(int), 0, w - 1)].mean()
if fin < 0.5:
    nrm = -nrm
print("contour pts", N, "inward check", max(fin, 1 - fin))

# ---------- profiles (RGB, 9 tangential lines) ----------
S_OUT, S_IN, ST = -18.0, 70.0, 0.5
s = np.arange(S_OUT, S_IN + 1e-9, ST)
ns = len(s)
prof = np.zeros((N, ns, 3), np.float64)
TOFF = np.arange(-4, 5, 1.0)
for o in TOFF:
    px = cs[:, 0:1] + nrm[:, 0:1] * s[None, :] + tang[:, 0:1] * o
    py = cs[:, 1:2] + nrm[:, 1:2] * s[None, :] + tang[:, 1:2] * o
    prof += C.bilinear(rgb, px, py)
prof /= len(TOFF)
plum = prof @ np.array([0.2126, 0.7152, 0.0722])
d3 = np.zeros_like(prof)
d3[:, 2:-2] = (prof[:, 4:] - prof[:, :-4]) / 2.0
d3 = (np.roll(d3, 1, 1) + d3 + np.roll(d3, -1, 1)) / 3
ad = np.linalg.norm(d3, axis=2)
off = int(round(5 / ST))
sh = np.zeros_like(ad)
sh[:, off:-off] = ad[:, off:-off] - np.maximum(ad[:, :-2 * off], ad[:, 2 * off:])
wi0, wi1 = int(2 / ST), int(8 / ST)
idx = np.arange(ns)
lo_in = np.clip(idx + wi0, 0, ns); hi_in = np.clip(idx + wi1, 0, ns)
lo_out = np.clip(idx - wi1, 0, ns); hi_out = np.clip(idx - wi0, 0, ns)
cum3 = np.concatenate([np.zeros((N, 1, 3)), np.cumsum(prof, 1)], 1)
rgb_in = (cum3[:, hi_in] - cum3[:, lo_in]) / np.maximum(hi_in - lo_in, 1)[None, :, None]
rgb_out = (cum3[:, hi_out] - cum3[:, lo_out]) / np.maximum(hi_out - lo_out, 1)[None, :, None]
m_in = rgb_in @ np.array([0.2126, 0.7152, 0.0722]); m_out = rgb_out @ np.array([0.2126, 0.7152, 0.0722])
contrast = np.linalg.norm(rgb_in - rgb_out, axis=2)
face_like = (m_in > 0.12) & (m_in < 0.56)
S_ABS = 0.02
REL = 0.5
cand = (sh > S_ABS) & face_like & (contrast > 0.07)
cand[:, s < -8] = False; cand[:, -off - 4:] = False
lm = np.zeros_like(cand)
lm[:, 1:-1] = (sh[:, 1:-1] >= sh[:, :-2]) & (sh[:, 1:-1] >= sh[:, 2:])
cand &= lm
smax = np.max(np.where(cand, sh, 0), 1)
cand &= sh >= REL * smax[:, None]
has = cand.any(1)
first = np.argmax(cand, 1)
sstar = np.where(has, s[first], np.nan)
kind = np.where(has, np.sign(m_in[np.arange(N), first] - m_out[np.arange(N), first]), 0)
print("profiles with an edge", has.mean())


def circ_nanmedian(a, r):
    ix = (np.arange(len(a))[:, None] + np.arange(-r, r + 1)[None, :]) % len(a)
    return np.nanmedian(a[ix], 1)


s_med = circ_nanmedian(sstar, 12)
s_fill = np.where(np.isnan(s_med), 0.0, s_med)
s_use = np.where(np.isnan(sstar) | (np.abs(sstar - s_fill) > 3), s_fill, sstar)
s_use = circ_nanmedian(s_use, 2)
ref = cs + nrm * s_use[:, None]
print("s* (px inward from colour edge): median %.2f p5 %.2f p95 %.2f max %.2f" % tuple(
    [np.median(s_use)] + list(np.percentile(s_use, [5, 95])) + [s_use.max()]))
print("fraction shadow-side (inner brighter) edges %.3f, lit-side %.3f, replaced %.3f" % (
    (kind > 0).mean(), (kind < 0).mean(), (np.isnan(sstar) | (np.abs(sstar - s_fill) > 3)).mean()))

# ---------- carve ----------
removed = np.zeros((h, w), bool)
for k0 in range(0, N):
    if s_use[k0] <= 0.5:
        continue
    tt = np.arange(-8.0, s_use[k0], 0.35)
    for o in (-0.7, 0.0, 0.7):
        xx = np.round(cs[k0, 0] + nrm[k0, 0] * tt + tang[k0, 0] * o).astype(int)
        yy = np.round(cs[k0, 1] + nrm[k0, 1] * tt + tang[k0, 1] * o).astype(int)
        okk = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
        removed[yy[okk], xx[okk]] = True
final = cm & ~removed
final = C.open_(C.close_(final, 1), 1)
runs, roots, areas, touch = C.label_runs(final, True)
final = C.paint((h, w), runs, roots == int(np.argmax(areas)))
rb, rtb, ab, tb = C.label_runs(~final, False)
for c in np.unique(rtb):
    if not tb[c]:
        final |= C.paint((h, w), rb, rtb == c)
print("final area", final.sum(), "colour area", cm.sum(), "ratio", final.sum() / cm.sum())

np.save(os.path.join(C.OUT, "mask.npy"), np.packbits(final, axis=None))
np.save(os.path.join(C.OUT, "mask_colour.npy"), np.packbits(cm, axis=None))
np.save(os.path.join(C.OUT, "refined_pts.npy"), np.column_stack([ref, s_use, kind, has]))
C.save_png(final.astype(np.float32), os.path.join(C.OUT, "mask.png"))
ov = rgb.copy()
ov[cm & ~C.erode(cm, 1)] = [1.0, 0.85, 0.0]
ov[final & ~C.erode(final, 1)] = [1, 0, 0]
C.save_png(ov, os.path.join(C.OUT, "seg4_overlay_full.png"))
C.save_png(ov[::2, ::2], os.path.join(C.OUT, "seg4_overlay_half.png"))
json.dump(dict(colour_otsu=float(tcol), colour_area=float(cm.sum()), final_area=float(final.sum()),
               colour_enclosed_bg_components=colour_holes, contour_pts=int(N),
               s_median=float(np.median(s_use)), s_p95=float(np.percentile(s_use, 95)), s_max=float(s_use.max()),
               edge_found_fraction=float(has.mean()), shadow_side_fraction=float((kind > 0).mean())),
          open(os.path.join(C.OUT, "seg4.json"), "w"), indent=1)
print("done", time.time() - t0)
