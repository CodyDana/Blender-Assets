"""Stage 1c: shadow-aware segmentation of Happo.JPG by directional smooth flood.

Lighting (established by probing, see notes in the final report): the scan lamp sits
on the image-down/left side, so the piece throws a SOFT lid shadow toward -y (up) and
+x (right); shaded bevel facets on up-facing edges are dark, lit bevels on down-facing
edges are light grey-tan and close to the lid colour.

Method:
  bg_lum : robust degree-4 polynomial of the lid luminance (from segment2 logic).
  perm   : lum < bg_lum - DELTA   (anything clearly darker than the local lid)
  shadow : flood from the lid (non-perm pixels) into perm pixels, moving only in the
           shadow directions (down, left, down-left, down-right in image coords, i.e.
           from the lid toward the metal for up/right-facing edges), and only across
           SMOOTH steps (|dlum| < TAU per pixel). A real metal outline is an in-focus
           step and stops the flood; a lid shadow is a smooth gradient and is eaten.
  variant OUTER: the flood may not enter lum < 0.30 (keeps every dark band: shaded
           facets AND black umbra).  variant INNER: no such limit (dark bands whose
           outer side is a smooth gradient are eaten; stops at the next sharp step).
  metal = perm minus shadow, opened r1, closed r2, largest component, hole check.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
H, W = rgb.shape[:2]
lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)

yy, xx = np.mgrid[0:H, 0:W]
core0 = L.closing(lum < 0.30, 2)
sm = core0[::4, ::4]
far = ~L.dilate(sm, 12)
far = np.repeat(np.repeat(far, 4, 0), 4, 1)[:H, :W]
sel = far & (lum > 0.45)


def design(X, Y, deg=4):
    return np.stack([X ** i * Y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], 1)


X = (xx[sel] / W - 0.5).astype(np.float64); Y = (yy[sel] / H - 0.5).astype(np.float64)
A = design(X, Y)
v = lum[sel].astype(np.float64)
keep = np.ones(len(v), bool)
for _ in range(6):
    c, *_ = np.linalg.lstsq(A[keep], v[keep], rcond=None)
    res = v - A @ c
    s = 1.4826 * np.median(np.abs(res[keep])) + 1e-4
    keep = np.abs(res) < 3 * s
bg_lum = (design((xx / W - 0.5).ravel(), (yy / H - 0.5).ravel()) @ c).reshape(H, W).astype(np.float32)
print("bg poly sigma %.4f range %.3f..%.3f" % (s, bg_lum.min(), bg_lum.max()))

DELTA = float(os.environ.get("DELTA", 0.08))
TAU = float(os.environ.get("TAU", 0.06))
T_STRICT = 0.30
MOVES = [(1, 0), (0, -1), (1, -1), (1, 1)]  # (dy, dx): down, left, down-left, down-right

perm = lum < (bg_lum - DELTA)


def flood(limit_dark):
    shadow = ~perm
    allowed = perm.copy()
    if limit_dark:
        allowed &= lum >= T_STRICT
    sh_l = [(dy, dx, L.shift(lum, dy, dx, 0.0)) for dy, dx in MOVES]
    smooth = [(dy, dx, np.abs(lum - sl) < TAU) for dy, dx, sl in sh_l]
    it = 0
    while True:
        it += 1
        grow = np.zeros_like(shadow)
        for dy, dx, sm_ in smooth:
            grow |= L.shift(shadow, dy, dx, False) & sm_
        grow &= allowed & ~shadow
        n = int(grow.sum())
        if n == 0 or it > 2000:
            break
        shadow |= grow
    return shadow & perm, it


def finish(shadow, tag):
    metal = perm & ~shadow
    metal = L.opening(metal, 1)
    metal = L.closing(metal, 2)
    lab, sizes = L.label(metal)
    big = max(sizes, key=sizes.get)
    piece = lab == big
    blab, bsizes = L.label(~piece)
    edge_labels = set(np.unique(np.concatenate([blab[0], blab[-1], blab[:, 0], blab[:, -1]]))) - {0}
    holes = {int(k): int(v) for k, v in bsizes.items() if k not in edge_labels}
    info = []
    for k, v in sorted(holes.items(), key=lambda t: -t[1])[:8]:
        ys, xs = np.nonzero(blab == k)
        info.append(dict(px=v, cx=float(xs.mean()), cy=float(ys.mean()), mean_lum=float(lum[ys, xs].mean()),
                         bg_lum=float(bg_lum[ys, xs].mean())))
    filled = piece.copy()
    for k in holes:
        filled |= blab == k
    others = sorted([v for k, v in sizes.items() if k != big], reverse=True)[:6]
    ys, xs = np.nonzero(filled)
    st = dict(variant=tag, area_px=int(filled.sum()), centroid_xy=[float(xs.mean()), float(ys.mean())],
              bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
              other_components_px=others, enclosed_nonmetal_regions=info,
              shadow_px=int(shadow.sum()),
              bottom_row_run=[int(v) for v in np.flatnonzero(filled[-1])[[0, -1]]] if filled[-1].any() else None)
    return filled, st


stats = dict(DELTA=DELTA, TAU=TAU, T_STRICT=T_STRICT, bg_sigma=float(s))
for tag, lim in (("outer", True), ("inner", False)):
    sh, it = flood(lim)
    m, st = finish(sh, tag)
    st["flood_iterations"] = it
    stats[tag] = st
    np.save(os.path.join(OUT, "mask_%s.npy" % tag), m)
    ov = rgb.copy()
    ov[sh] = ov[sh] * 0.4 + np.array([0.2, 0.4, 1.0]) * 0.6
    e = m & ~L.erode(m, 1)
    ov[e] = [1, 0, 0]
    L.save_png(os.path.join(OUT, "seg3_%s_check.png" % tag), ov)
    print(json.dumps(st))

np.save(os.path.join(OUT, "lum.npy"), lum)
np.save(os.path.join(OUT, "bg_lum.npy"), bg_lum)
mo = np.load(os.path.join(OUT, "mask_outer.npy")); mi = np.load(os.path.join(OUT, "mask_inner.npy"))
diff = mo ^ mi
print("outer vs inner differ on %d px" % diff.sum())
L.save_png(os.path.join(OUT, "happo_mask.png"), mo.astype(np.float32))
d = np.zeros((H, W, 3), np.float32)
d[mo & mi] = [1, 1, 1]
d[mo & ~mi] = [1, 0.3, 0]
d[mi & ~mo] = [0, 0.6, 1]
L.save_png(os.path.join(OUT, "seg3_outer_vs_inner.png"), d)
json.dump(stats, open(os.path.join(OUT, "seg3_stats.json"), "w"), indent=1)
