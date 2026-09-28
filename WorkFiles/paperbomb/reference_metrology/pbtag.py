# -*- coding: utf-8 -*-
"""Tag detection + rectification + ink segmentation, shared by every stage.

The tag frame: origin at the TAG's top-left corner (the paper, not the canvas),
x right, y down, fractions of tag width W and height H, and mm on the shipped
card (70.0 x 156.0 mm).
"""
import math, os
import numpy as np
import pbmetro as P

CARD_W_MM = 70.0
CARD_H_MM = 156.0


# --------------------------------------------------------------------------
def box_blur(a, r):
    """Separable box mean with edge-truncated windows."""
    a = np.asarray(a, dtype=np.float64)
    h, w = a.shape
    c = np.vstack([np.zeros((1, w)), np.cumsum(a, axis=0)])
    y0 = np.clip(np.arange(h) - r, 0, h)
    y1 = np.clip(np.arange(h) + r + 1, 0, h)
    a2 = (c[y1] - c[y0]) / (y1 - y0)[:, None]
    c = np.hstack([np.zeros((h, 1)), np.cumsum(a2, axis=1)])
    x0 = np.clip(np.arange(w) - r, 0, w)
    x1 = np.clip(np.arange(w) + r + 1, 0, w)
    return (c[:, x1] - c[:, x0]) / (x1 - x0)[None, :]


def paper_mask_white_bg(rgb):
    """Reference guides: white canvas, warm paper tag."""
    L = P.luma_stored(rgb)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    m = (L < 0.955) | (sat > 0.05)
    m = P.close(m, 3)
    lab, n = P.label_cc(m)
    st = P.cc_stats(lab, n)
    st = [s for s in st if s]
    st.sort(key=lambda s: -s['area'])
    big = st[0]
    m = (lab == big['label'])
    # fill holes: flood the outside of the complement
    inv = ~m
    lab2, n2 = P.label_cc(inv)
    edge = set(np.unique(np.concatenate([lab2[0, :], lab2[-1, :], lab2[:, 0], lab2[:, -1]])))
    edge.discard(0)
    outside = np.isin(lab2, list(edge))
    return ~outside


def paper_mask_atlas(rgb, island='left'):
    """Our shipped atlas: two card UV islands on smeared padding.

    The card carries paper grain and a hard deckle edge; the padding outside the
    island is a smooth dilation with almost no local gradient energy.  A 0.5x
    median-energy cut separates them; the two islands are split at the dead
    vertical strip between them.
    """
    L = P.luma_stored(rgb).astype(np.float64)
    g = (np.abs(np.diff(L, axis=1, prepend=L[:, :1])) +
         np.abs(np.diff(L, axis=0, prepend=L[:1, :])))
    e = box_blur(g, 2)
    thr = 0.5 * float(np.percentile(e, 50))
    m = e > thr
    # split the two islands at the widest dead strip near the middle
    colE = e.mean(axis=0)
    W = len(colE)
    lo, hi = int(0.30 * W), int(0.70 * W)
    dead = colE[lo:hi] < 0.35 * float(np.median(colE))
    best = (0, None)
    i = 0
    while i < len(dead):
        if dead[i]:
            j = i
            while j + 1 < len(dead) and dead[j + 1]:
                j += 1
            if j - i + 1 > best[0]:
                best = (j - i + 1, (i + j) // 2 + lo)
            i = j + 1
        else:
            i += 1
    cut = best[1] if best[1] is not None else W // 2
    if island == 'left':
        m[:, cut:] = False
    else:
        m[:, :cut] = False
    m = P.close(m, 4)
    m = P.open_(m, 2)
    lab, n = P.label_cc(m)
    st = [s for s in P.cc_stats(lab, n) if s]
    st.sort(key=lambda s: -s['area'])
    m = (lab == st[0]['label'])
    inv = ~m
    lab2, n2 = P.label_cc(inv)
    edge = set(np.unique(np.concatenate([lab2[0, :], lab2[-1, :], lab2[:, 0], lab2[:, -1]])))
    edge.discard(0)
    outside = np.isin(lab2, list(edge))
    return ~outside


# --------------------------------------------------------------------------
def edge_traces(mask):
    """Left/right x per row, top/bottom y per column, for rows/cols that have ink."""
    h, w = mask.shape
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    idx = np.arange(w)
    left = np.full(h, np.nan)
    right = np.full(h, np.nan)
    for y in rows:
        r = mask[y]
        left[y] = idx[r][0]
        right[y] = idx[r][-1]
    idy = np.arange(h)
    top = np.full(w, np.nan)
    bot = np.full(w, np.nan)
    for x in cols:
        c = mask[:, x]
        top[x] = idy[c][0]
        bot[x] = idy[c][-1]
    return left, right, top, bot, rows, cols


def fit_tag_quad(mask):
    """Fit the four straight sides of the (chamfered) tag and return the quad,
    the rotation, and the keystone diagnostics."""
    h, w = mask.shape
    left, right, top, bot, rows, cols = edge_traces(mask)
    y0, y1 = rows[0], rows[-1]
    x0, x1 = cols[0], cols[-1]
    hh = y1 - y0
    ww = x1 - x0

    def robust_fit(idx, val, lo, hi, horizontal):
        sel = np.arange(int(lo), int(hi))
        sel = sel[np.isfinite(val[sel])]
        a, b, rms = P.fit_line_x_of_y(sel.astype(np.float64), val[sel])
        for _ in range(3):                   # trim outliers (chamfers, deckle)
            pred = a * sel + b
            res = np.abs(val[sel] - pred)
            keep = res < max(2.0, 2.5 * res.std())
            sel = sel[keep]
            a, b, rms = P.fit_line_x_of_y(sel.astype(np.float64), val[sel])
        return a, b, rms, len(sel)

    # vertical sides: x = aL*y + bL  (use the middle 60% of the height)
    aL, bL, rL, nL = robust_fit(None, left, y0 + 0.20 * hh, y0 + 0.80 * hh, False)
    aR, bR, rR, nR = robust_fit(None, right, y0 + 0.20 * hh, y0 + 0.80 * hh, False)
    # horizontal sides: y = aT*x + bT
    aT, bT, rT, nT = robust_fit(None, top, x0 + 0.20 * ww, x0 + 0.80 * ww, True)
    aB, bB, rB, nB = robust_fit(None, bot, x0 + 0.20 * ww, x0 + 0.80 * ww, True)

    def inter(av, bv, ah, bh):
        # x = av*y + bv ; y = ah*x + bh
        y = (ah * bv + bh) / (1.0 - ah * av)
        x = av * y + bv
        return (float(x), float(y))

    tl = inter(aL, bL, aT, bT)
    tr = inter(aR, bR, aT, bT)
    br = inter(aR, bR, aB, bB)
    bl = inter(aL, bL, aB, bB)

    rot_left = math.degrees(math.atan2(aL, 1.0))     # +ve = leaning right going down
    rot_right = math.degrees(math.atan2(aR, 1.0))
    rot_top = math.degrees(math.atan2(aT, 1.0))
    rot_bot = math.degrees(math.atan2(aB, 1.0))
    # image rotation: average of (vertical sides' lean) and (horizontal sides' lean)
    rot_v = -(rot_left + rot_right) / 2.0
    rot_h = (rot_top + rot_bot) / 2.0
    w_top = math.hypot(tr[0] - tl[0], tr[1] - tl[1])
    w_bot = math.hypot(br[0] - bl[0], br[1] - bl[1])
    h_left = math.hypot(bl[0] - tl[0], bl[1] - tl[1])
    h_right = math.hypot(br[0] - tr[0], br[1] - tr[1])

    diag = dict(
        quad=dict(tl=tl, tr=tr, br=br, bl=bl),
        side_fit_rms_px=dict(left=rL, right=rR, top=rT, bottom=rB),
        side_fit_samples=dict(left=nL, right=nR, top=nT, bottom=nB),
        lean_deg=dict(left_edge=rot_left, right_edge=rot_right,
                      top_edge=rot_top, bottom_edge=rot_bot),
        rotation_deg_from_vertical_sides=rot_v,
        rotation_deg_from_horizontal_sides=rot_h,
        rotation_deg_applied=(rot_v + rot_h) / 2.0,
        keystone_vertical_convergence_deg=rot_right - rot_left,
        keystone_horizontal_convergence_deg=rot_bot - rot_top,
        width_top_px=w_top, width_bottom_px=w_bot,
        height_left_px=h_left, height_right_px=h_right,
        width_taper_pct=100.0 * (w_bot - w_top) / (0.5 * (w_bot + w_top)),
        height_taper_pct=100.0 * (h_right - h_left) / (0.5 * (h_right + h_left)),
    )
    return diag


def rectify(rgb, mask, diag, out_w=None, out_h=None):
    q = diag['quad']
    src = [q['tl'], q['tr'], q['br'], q['bl']]
    W = out_w or int(round(0.5 * (diag['width_top_px'] + diag['width_bottom_px'])))
    H = out_h or int(round(0.5 * (diag['height_left_px'] + diag['height_right_px'])))
    dst = [(0, 0), (W, 0), (W, H), (0, H)]
    Hm = P.homography(src, dst)
    warped = P.warp_bilinear(rgb, Hm, W, H)
    wmask = P.warp_bilinear(mask.astype(np.float32)[..., None], Hm, W, H)[..., 0] > 0.5
    return warped, wmask, W, H, Hm


# --------------------------------------------------------------------------
def segment(rgb_rect, mask_rect):
    """Split the rectified tag into black ink / red ink / paper at the 50%
    contrast crossing, so that images of different ink density compare fairly."""
    L = P.luma_stored(rgb_rect).astype(np.float64)
    red = (rgb_rect[..., 0].astype(np.float64)
           - np.maximum(rgb_rect[..., 1], rgb_rect[..., 2]).astype(np.float64))
    inside = mask_rect
    Lp = float(np.percentile(L[inside], 75))          # paper level
    Li = float(np.percentile(L[inside], 0.5))         # ink floor
    t50 = 0.5 * (Lp + Li)
    rp = float(np.percentile(red[inside], 99.5))
    rt50 = 0.5 * rp
    # red wins over black: a deep seal red can be darker than the black cut-off,
    # and must not be lost between the two masks
    redm = inside & (red > rt50)
    black = inside & (L < t50) & ~redm
    info = dict(paper_luma_p75_stored=Lp, ink_floor_luma_p005_stored=Li,
                black_threshold_stored=t50,
                redness_p995_stored=rp, red_threshold_stored=rt50,
                paper_luma_linear=float(P.srgb_to_linear(Lp)),
                ink_floor_luma_linear=float(P.srgb_to_linear(Li)),
                black_coverage=float(black.sum()) / float(inside.sum()),
                red_coverage=float(redm.sum()) / float(inside.sum()))
    return black, redm, info


# --------------------------------------------------------------------------
class Tag:
    def __init__(self, path, kind='guide', island='left', name=''):
        self.path = path
        self.name = name or os.path.basename(path)
        self.mtime = os.stat(path).st_mtime
        a = P.load_stored(path)
        self.rgb_raw = a[..., :3]
        if kind == 'guide':
            m = paper_mask_white_bg(self.rgb_raw)
        else:
            m = paper_mask_atlas(self.rgb_raw, island)
        self.mask_raw = m
        self.diag = fit_tag_quad(m)
        self.rgb, self.mask, self.W, self.H, self.Hm = rectify(self.rgb_raw, m, self.diag)
        self.black, self.red, self.seg = segment(self.rgb, self.mask)
        self.px_per_mm_x = self.W / CARD_W_MM
        self.px_per_mm_y = self.H / CARD_H_MM
        self.px_per_mm = 0.5 * (self.px_per_mm_x + self.px_per_mm_y)

    def fx(self, x):
        return x / self.W

    def fy(self, y):
        return y / self.H

    def mmx(self, x):
        return x / self.W * CARD_W_MM

    def mmy(self, y):
        return y / self.H * CARD_H_MM

    def box(self, x0, y0, x1, y1):
        return dict(
            x0_frac=round(self.fx(x0), 5), y0_frac=round(self.fy(y0), 5),
            x1_frac=round(self.fx(x1), 5), y1_frac=round(self.fy(y1), 5),
            w_frac=round(self.fx(x1 - x0), 5), h_frac=round(self.fy(y1 - y0), 5),
            x0_mm=round(self.mmx(x0), 3), y0_mm=round(self.mmy(y0), 3),
            x1_mm=round(self.mmx(x1), 3), y1_mm=round(self.mmy(y1), 3),
            w_mm=round(self.mmx(x1 - x0), 3), h_mm=round(self.mmy(y1 - y0), 3),
            cx_frac=round(self.fx(0.5 * (x0 + x1)), 5),
            cy_frac=round(self.fy(0.5 * (y0 + y1)), 5),
            cx_mm=round(self.mmx(0.5 * (x0 + x1)), 3),
            cy_mm=round(self.mmy(0.5 * (y0 + y1)), 3),
            w_over_h=round((self.mmx(x1 - x0) / self.mmy(y1 - y0)) if y1 > y0 else float('nan'), 4),
            w_over_h_px=round(((x1 - x0) / (y1 - y0)) if y1 > y0 else float('nan'), 4),
        )

    def pt(self, x, y):
        return dict(x_frac=round(self.fx(x), 5), y_frac=round(self.fy(y), 5),
                    x_mm=round(self.mmx(x), 3), y_mm=round(self.mmy(y), 3))
