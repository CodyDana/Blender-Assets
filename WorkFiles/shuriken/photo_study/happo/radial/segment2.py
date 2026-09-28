"""Stage 1b: shadow-aware segmentation of Happo.JPG.

Why: the flatbed scan lights the piece from the +y (image-down) side. Edges whose
outward normal points up (-y) get a soft grey lid shadow outside them (and a black
umbra in upward-opening notches); edges facing down carry bright ground bevels that
are close to the background grey. A single colour-distance threshold (segment.py)
therefore both eats bevels and adds shadow.

Rule used here (per image column, i.e. along the shadow direction):
  strict = lum < 0.30 (dark face, dark shaded facets, black umbra)  [closed r=2]
  perm   = lum < bg_lum(x,y) - 0.08   (anything clearly darker than the local lid)
  For each perm run in a column: pixels above the first strict pixel are kept only
  from the first SHARP entry step (drop >= 0.14 over 2 px) downward; soft shadow
  gradients above it are dropped. Everything from the first strict pixel down to
  the bottom of the run (face + bright bevels on down-facing edges) is kept.
  Runs with no strict pixel: kept only below a sharp entry step.
Result = 'outer' outline: includes the dark band on up-facing edges (facet OR umbra;
see measure.py for the inner alternative on the edges where it is ambiguous).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
H, W = rgb.shape[:2]
lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)

# background luminance: robust degree-4 polynomial surface fitted to pixels that are
# far (> 48 px) from the dark core, so lid vignetting (0.63 .. 0.96) is modelled.
yy, xx = np.mgrid[0:H, 0:W]
core0 = L.closing(lum < 0.30, 2)
sm = core0[::4, ::4]
far = ~L.dilate(sm, 12)
far = np.repeat(np.repeat(far, 4, 0), 4, 1)[:H, :W]
sel = far & (lum > 0.45)
X = (xx[sel] / W - 0.5).astype(np.float64); Y = (yy[sel] / H - 0.5).astype(np.float64)
def design(X, Y, deg=4):
    return np.stack([X ** i * Y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], 1)
A = design(X, Y)
v = lum[sel].astype(np.float64)
keep = np.ones(len(v), bool)
for _ in range(6):
    c, *_ = np.linalg.lstsq(A[keep], v[keep], rcond=None)
    res = v - A @ c
    s = 1.4826 * np.median(np.abs(res[keep])) + 1e-4
    keep = np.abs(res) < 3 * s
bg_lum = (design((xx / W - 0.5).ravel(), (yy / H - 0.5).ravel()) @ c).reshape(H, W).astype(np.float32)
print("bg poly fit on %d px, robust sigma %.4f, bg range %.3f..%.3f" % (sel.sum(), s, bg_lum.min(), bg_lum.max()))
res_img = np.zeros((H, W), np.float32); res_img[sel] = res
print("bg residual percentiles (sel):", np.percentile(res, [1, 5, 50, 95, 99]))

T_STRICT = 0.30
DELTA = 0.08
STEP = 0.14
strict = L.closing(lum < T_STRICT, 2)
perm = lum < (bg_lum - DELTA)
perm |= strict

inc = np.zeros((H, W), bool)
n_shadow_px = 0
for x in range(W):
    col = perm[:, x]
    st = strict[:, x]
    lc = lum[:, x]
    d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    for a, b in zip(starts, ends):
        sidx = np.flatnonzero(st[a:b])
        first_strict = a + sidx[0] if len(sidx) else b
        # search for first sharp entry step in [a, first_strict)
        cut = first_strict
        for y in range(a, first_strict):
            y0 = max(y - 1, 0)
            y1 = min(y + 1, H - 1)
            if lc[y0] - lc[y1] >= STEP:
                cut = y
                break
        if len(sidx) == 0 and cut == b:
            n_shadow_px += b - a
            continue
        n_shadow_px += cut - a
        inc[cut:b, x] = True

inc = L.opening(inc, 1)
inc = L.closing(inc, 2)
lab, sizes = L.label(inc)
big = max(sizes, key=sizes.get)
piece = lab == big
print("components", len(sizes), "largest", sizes[big], "others", sorted([v for k, v in sizes.items() if k != big], reverse=True)[:6])

blab, bsizes = L.label(~piece)
edge_labels = set(np.unique(np.concatenate([blab[0], blab[-1], blab[:, 0], blab[:, -1]]))) - {0}
holes = {int(k): int(v) for k, v in bsizes.items() if k not in edge_labels}
print("enclosed non-metal regions (px):", sorted(holes.values(), reverse=True))
hole_info = []
for k, v in sorted(holes.items(), key=lambda t: -t[1])[:8]:
    ys, xs = np.nonzero(blab == k)
    hole_info.append(dict(px=v, cx=float(xs.mean()), cy=float(ys.mean()), mean_lum=float(lum[ys, xs].mean())))
print(hole_info)
filled = piece.copy()
for k in holes:
    filled |= blab == k

np.save(os.path.join(OUT, "mask2.npy"), filled)
np.save(os.path.join(OUT, "lum.npy"), lum)
np.save(os.path.join(OUT, "bg_lum.npy"), bg_lum)
L.save_png(os.path.join(OUT, "happo_mask.png"), filled.astype(np.float32))

ov = rgb.copy()
edge = filled & ~L.erode(filled, 1)
shadow_dropped = perm & ~filled
ov[shadow_dropped] = ov[shadow_dropped] * 0.4 + np.array([0.2, 0.4, 1.0]) * 0.6
ov[edge] = [1, 0, 0]
L.save_png(os.path.join(OUT, "seg2_check.png"), ov)

ys, xs = np.nonzero(filled)
st = dict(area_px=int(filled.sum()), centroid_xy=[float(xs.mean()), float(ys.mean())],
          bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
          enclosed_regions=hole_info, T_STRICT=T_STRICT, DELTA=DELTA, STEP=STEP,
          touches_border=dict(top=bool(filled[0].any()), bottom=bool(filled[-1].any()),
                              left=bool(filled[:, 0].any()), right=bool(filled[:, -1].any())),
          bottom_row_run=[int(v) for v in np.flatnonzero(filled[-1])[[0, -1]]] if filled[-1].any() else None)
json.dump(st, open(os.path.join(OUT, "seg2_stats.json"), "w"), indent=1)
print(json.dumps(st, indent=1))
