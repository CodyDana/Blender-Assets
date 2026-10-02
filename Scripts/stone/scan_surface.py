"""Rock surface layers from scanned CC0 maps (Poly Haven, downloaded with the owner's approval; provenance in each
folder's SOURCE.md under Assets/Dojo/SourceTextures/PolyHaven/). Pilot 2 of the dojo rocks (STONE_BUILDING_STUDY.md
3.11 grain, 4.11 micro set). numpy + PIL only (system Python):

    py -3 -B Scripts/stone/scan_surface.py --ship Exports/DojoKit/Rocks/Textures --work <dir> --prefix T_DKR

Layers
- GRAIN (shipped tiling detail, T_<P>_GraniteGrain_BC / _N): true speckled crystal grain from granite_tile_03. The
  scan is a 3 x 2 grid of polished tiles with dark grout joints (columns ~684 / ~1365 px, row ~1023 px); only tile
  interiors are sampled (12 px clear of every joint) and quilted into a periodic 1024 tile along warped Voronoi
  boundaries (no straight seams, never a joint). Each patch is flattened to the global mean at low frequency so no
  patch reads as a lighter or darker square. The colour is regraded to the owner's sheet grain close-up by its own
  numbers: luma by quantile mapping onto the sheet panel's luma distribution, the two opponent chroma channels by
  mean/std transfer (the brown polished granite becomes the sheet's white / grey / black crystals with tan grains).
  Scale: the 2x-upsampled 2048 tile = 0.75 m (crystals 3-5 mm; the scan's 50 % autocorrelation is 2 px against the sheet panel's 3 px, so the
  sheet panel spans about 14 cm).
- MACRO (bake inputs, not shipped; baked into each rock's unique maps): tiger_rock (weathered granite relief) for the
  cliff, rock_surface (coarse boulder surface) for the river rocks. Regraded to grey granite: the scan's luma with its
  contrast set by quantile targets, a near-neutral warm-grey tint (the landscape reference's family, hue ~25-30 deg)
  and only 25 % of the scan's own chroma deviation kept; the tan of the sheet is added later as staining. Height and
  normal maps pass through unchanged (DirectX normals kept as DirectX).
- MOSS (shipped tiling detail, T_<P>_MossDetail_BC; also a bake input): mossy_rock's albedo, regraded toward the
  sheet's moss (yellow-green to olive).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PH = ROOT / "Assets" / "Dojo" / "SourceTextures" / "PolyHaven"
SHEET = ROOT / "References" / "Dojo" / "dojo_rocks_ref.png"
SHEET_GRAIN_BOX = (12, 850, 174, 1075)          # inside the sheet's grain close-up panel (8, 845, 178, 1080)

# granite_tile_03 tile interiors (x0, y0, x1, y1), 12 px clear of the grout joints measured on the diff map
GRAIN_TILE_M = 0.45      # pilot 2 fix 1: 0.75 m read 2-3x too coarse in the grain close-up (judge, checked)
GT_TILES = [(12, 12, 672, 1011), (697, 12, 1353, 1011), (1379, 12, 2036, 1011),
            (12, 1036, 672, 2035), (697, 1036, 1353, 2035), (1379, 1036, 2036, 2035)]


# ----------------------------------------------------------------------------------------------- helpers
def load(path, mode="RGB"):
    return np.asarray(Image.open(path).convert(mode), np.float64) / 255.0


def save(a, path, mode="RGB"):
    a = np.clip(np.asarray(a) * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a, mode).save(path)
    return str(path)


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def fft_blur(a, sigma):
    """Periodic gaussian blur (per channel) by FFT."""
    a = np.asarray(a, float)
    H, W = a.shape[:2]
    fy = np.fft.fftfreq(H)[:, None]
    fx = np.fft.fftfreq(W)[None, :]
    g = np.exp(-2 * (math.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    if a.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(a) * g))
    return np.stack([np.real(np.fft.ifft2(np.fft.fft2(a[..., c]) * g)) for c in range(a.shape[2])], -1)


def periodic_noise(n, f_lo, f_hi, rng):
    fx = np.fft.fftfreq(n) * n
    FX, FY = np.meshgrid(fx, fx)
    f = np.hypot(FX, FY)
    amp = ((f >= f_lo) & (f <= f_hi)).astype(float)
    out = np.real(np.fft.ifft2(amp * np.exp(1j * rng.uniform(0, 2 * np.pi, (n, n)))))
    return (out - out.mean()) / max(out.std(), 1e-9)


def to_opp(rgb):
    """Opponent space used for the colour transfer: L = Rec.709 luma, a = R - G, b = (R + G) / 2 - B."""
    L = luma(rgb)
    a = rgb[..., 0] - rgb[..., 1]
    b = 0.5 * (rgb[..., 0] + rgb[..., 1]) - rgb[..., 2]
    return L, a, b


def from_opp(L, a, b):
    G = L - 0.2487 * a + 0.0722 * b
    R = G + a
    B = G + 0.5 * a - b
    return np.stack([R, G, B], -1)


def quantile_map(x, ref, n=256):
    """Map the distribution of ``x`` onto the distribution of ``ref`` (monotone, by quantiles)."""
    qs = np.linspace(0, 100, n)
    xs = np.percentile(x, qs)
    rs = np.percentile(ref, qs)
    xs = np.maximum.accumulate(xs + np.arange(n) * 1e-9)
    return np.interp(x, xs, rs)


def stats(rgb):
    L = luma(rgb)
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = lin.reshape(-1, 3).mean(0)
    return {"luma_p5_p25_p50_p75_p95": [round(float(v), 4) for v in np.percentile(L, (5, 25, 50, 75, 95))],
            "dark_lt_0.25": round(float((L < 0.25).mean()), 4), "bright_gt_0.75": round(float((L > 0.75).mean()), 4),
            "R_over_B": round(float(rgb[..., 0].mean() / max(rgb[..., 2].mean(), 1e-6)), 3),
            "mean_linear_rgb": [round(float(v), 4) for v in m]}


def autocorr_len(L, lv=0.5):
    l = L - L.mean()
    F = np.fft.fft2(l)
    ac = np.real(np.fft.ifft2(F * np.conj(F)))
    ac /= ac[0, 0]
    m = 0.5 * (ac[0, :40] + ac[:40, 0])
    return int(next(k for k in range(40) if m[k] < lv))


def _upsample_sharp(a, k, amount=0.9, sigma=1.6):
    """Periodic k x upsample (Lanczos on a 3 x 3 wrap so the tile edges stay seamless) + unsharp mask."""
    H, W = a.shape[:2]
    C = a.shape[2]
    big = np.tile(a, (3, 3, 1))
    chans = []
    for c in range(C):
        im = Image.fromarray(big[..., c].astype(np.float32), "F").resize((3 * W * k, 3 * H * k), Image.LANCZOS)
        chans.append(np.asarray(im, np.float64)[H * k:2 * H * k, W * k:2 * W * k])
    out = np.stack(chans, -1)
    if amount > 0:
        out = out + amount * (out - fft_blur(out, sigma * k))
    return np.clip(out, 0, 1)


# ----------------------------------------------------------------------------------------------- quilting
def quilt_labels(n, seeds, rng, warp=36.0):
    """Warped periodic Voronoi labels on an n x n tile and each pixel's periodic offset from its seed."""
    ys, xs = np.mgrid[0:n, 0:n].astype(float)
    wx = periodic_noise(n, 2, 7, rng) * warp
    wy = periodic_noise(n, 2, 7, rng) * warp
    X, Y = xs + wx, ys + wy
    best = np.full((n, n), np.inf)
    lab = np.zeros((n, n), np.int64)
    off = np.zeros((n, n, 2))
    for k, (sx, sy) in enumerate(seeds):
        dx = (xs - sx + n / 2) % n - n / 2
        dy = (ys - sy + n / 2) % n - n / 2
        dwx = (X - sx + n / 2) % n - n / 2
        dwy = (Y - sy + n / 2) % n - n / 2
        d = dwx ** 2 + dwy ** 2
        upd = d < best
        best = np.where(upd, d, best)
        lab = np.where(upd, k, lab)
        off[..., 0] = np.where(upd, dx, off[..., 0])
        off[..., 1] = np.where(upd, dy, off[..., 1])
    return lab, off


def quilt(maps, n, rng, per_side=3):
    """Quilt aligned source maps (dict name -> (H, W, C) arrays of the same scan) into periodic n x n tiles.
    Patches come from the joint-free tile interiors (GT_TILES), one window per seed, each centred so the seed's whole
    warped cell lies inside the window. Returns dict name -> tile, plus the patch list."""
    g = per_side
    cell = n / g
    seeds = [((i + 0.5 + rng.uniform(-0.12, 0.12)) * cell, (j + 0.5 + rng.uniform(-0.12, 0.12)) * cell)
             for j in range(g) for i in range(g)]
    lab, off = quilt_labels(n, seeds, rng)
    reach = int(np.ceil(np.abs(off).max())) + 2
    win = 2 * reach + 1
    patches = []
    order = rng.permutation(len(GT_TILES) * 4)
    used = 0
    for k in range(len(seeds)):
        while True:
            t = order[used % len(order)] % len(GT_TILES)
            used += 1
            x0, y0, x1, y1 = GT_TILES[t]
            if x1 - x0 > win and y1 - y0 > win:
                break
        cx = int(rng.integers(x0 + reach, x1 - reach))
        cy = int(rng.integers(y0 + reach, y1 - reach))
        patches.append((t, cx, cy))
    out = {}
    for name, src in maps.items():
        tile = np.zeros((n, n, src.shape[2]))
        for k, (t, cx, cy) in enumerate(patches):
            m = lab == k
            sx = (cx + off[..., 0][m]).astype(np.int64)
            sy = (cy + off[..., 1][m]).astype(np.int64)
            tile[m] = src[sy, sx]
        out[name] = tile
    return out, {"seeds": len(seeds), "window_px": win, "patches": [list(map(int, p)) for p in patches]}


def flatten_low(src, sigma=48.0):
    """Remove low-frequency tone drift (polish sheen, lighting) so patches do not read as squares."""
    lo = fft_blur(src, sigma)
    return src / np.maximum(lo, 1e-3) * src.reshape(-1, src.shape[-1]).mean(0)


# ----------------------------------------------------------------------------------------------- layers
def grain_layer(n=1024, seed=8301, ref_box=SHEET_GRAIN_BOX, nrm_gain=2.2, up=2, crisp_keep=0.35):
    rng = np.random.default_rng(seed)
    d = PH / "granite_tile_03"
    diff = load(d / "granite_tile_03_diff_2k.jpg")
    nor = load(d / "granite_tile_03_nor_dx_2k.jpg")
    disp = load(d / "granite_tile_03_disp_2k.jpg", "L")[..., None]
    diff_f = flatten_low(diff)
    tiles, qinfo = quilt({"bc": diff_f, "n": nor, "h": disp}, n, rng)
    bc = tiles["bc"]
    sheet = load(SHEET)
    x0, y0, x1, y1 = ref_box
    ref = sheet[y0:y1, x0:x1]
    L, a, b = to_opp(bc)
    Lr, ar, br = to_opp(ref)
    L2 = quantile_map(L, Lr)
    a2 = (a - a.mean()) / max(a.std(), 1e-6) * ar.std() + ar.mean()
    b2 = (b - b.mean()) / max(b.std(), 1e-6) * br.std() + br.mean()
    out = np.clip(from_opp(L2, a2, b2), 0, 1)
    if up > 1:
        # the sheet's close-up shows ~11 crisp crystals across; our 2K scan gives ~93 px there, so the tile is
        # upsampled (Lanczos) and unsharp-masked to keep crystal edges crisp when magnified (no new detail is
        # invented: the same crystals, sharper edges); the luma quantiles are re-matched afterwards
        out = _upsample_sharp(out, up)
        L, a, b = to_opp(out)
        L = quantile_map(L, Lr)
        # crisp crystal boundaries: each mineral class (by luma: biotite black, smoky quartz grey, feldspar white)
        # pulled toward its class mean with a narrow transition, so the scan's own crystal layout keeps sharp
        # edges after magnification (35 % of the in-class variation kept)
        qs = np.percentile(L, (12, 40))
        cls = [L < qs[0], (L >= qs[0]) & (L < qs[1]), L >= qs[1]]
        means = [float(L[c].mean()) for c in cls]
        w1 = 1.0 / (1.0 + np.exp(-(L - qs[0]) / 0.012))
        w2 = 1.0 / (1.0 + np.exp(-(L - qs[1]) / 0.012))
        target = means[0] * (1 - w1) + means[1] * (w1 - w1 * w2) + means[2] * (w1 * w2)
        L = target + crisp_keep * (L - target)
        L = quantile_map(L, Lr)
        out = np.clip(from_opp(L, a, b), 0, 1)
        tiles = {k: _upsample_sharp(v, up, amount=0.0) for k, v in tiles.items()}
    # normal: the polished scan's relief is very faint (std 9/255): the sheet's crystals stand in relief, so the
    # tangent xy is scaled by ``nrm_gain`` and renormalised (DirectX kept)
    nv = tiles["n"] * 2.0 - 1.0
    nv[..., :2] *= nrm_gain
    nv /= np.maximum(np.linalg.norm(nv, axis=-1, keepdims=True), 1e-6)
    nmap = nv * 0.5 + 0.5
    info = {"source": "granite_tile_03 (Poly Haven CC0)", "tile_px": n * up, "tile_m": GRAIN_TILE_M, "upsample": up, "quilt": qinfo,
            "sheet_panel": stats(ref), "tile": stats(out), "scan_before": stats(diff[GT_TILES[0][1]:GT_TILES[0][3],
                                                                                      GT_TILES[0][0]:GT_TILES[0][2]]),
            "autocorr50_px": {"sheet_panel": autocorr_len(luma(ref)), "tile": autocorr_len(luma(out))},
            "normal_xy_gain": nrm_gain}
    return out, nmap, tiles["h"][..., 0], info


def macro_layer(name, targets=(0.30, 0.47, 0.56, 0.64, 0.78), tint=(1.01, 1.0, 0.97), keep_chroma=0.10,
                blur_px=3.0, band_keep=0.35, band_sigma_px=20.0, pre_blur_px=0.0):
    """A scanned rock albedo regraded to grey granite: luma by quantile targets (p5, p25, p50, p75, p95 in sRGB),
    a warm-grey tint (hue ~27 deg, sat ~0.11 at the median), ``keep_chroma`` of the scan's own chroma deviation."""
    d = PH / name
    diff = load(d / f"{name}_diff_2k.jpg")
    if pre_blur_px:
        # pilot 2 fix 1: grade at the bake's own resolution (the unique maps hold ~2 mm / px = 2.5 scan px), so
        # the target contrast survives the bake instead of living in sub-texel speckle
        diff = fft_blur(diff, pre_blur_px)
    L, a, b = to_opp(diff)
    qs = np.array([5, 25, 50, 75, 95])
    xs = np.percentile(L, qs)
    xs_full = np.concatenate([[L.min()], xs, [L.max()]])
    t = np.asarray(targets, float)
    ts_full = np.concatenate([[max(0.0, t[0] - (xs[0] - L.min()) * (t[1] - t[0]) / max(xs[1] - xs[0], 1e-6))], t,
                              [min(1.0, t[-1] + (L.max() - xs[-1]) * (t[-1] - t[-2]) / max(xs[-1] - xs[-2], 1e-6))]])
    L2 = np.interp(L, xs_full, ts_full)
    tint = np.asarray(tint) / luma(np.asarray(tint)[None, :])[0]
    grey = L2[..., None] * tint
    Lg, ag, bg = to_opp(grey)
    out = from_opp(Lg, ag + keep_chroma * (a - a.mean()), bg + keep_chroma * (b - b.mean()))
    out = np.clip(out, 0, 1)
    if blur_px:
        out = fft_blur(out, blur_px)
    if band_keep < 1.0:
        # soften the 2 mm - 2 cm scan mottling (it read as blotches over the crystal grain in the close-up); the
        # >= 2 cm weathering mottles that carry the rock-scale contrast stay
        lo = fft_blur(out, band_sigma_px)
        out = lo + band_keep * (out - lo)
    h = load(d / f"{name}_disp_2k.jpg", "L")
    nor = load(d / f"{name}_nor_dx_2k.jpg")
    return out, h, nor, {"source": f"{name} (Poly Haven CC0)", "before": stats(diff), "after": stats(out),
                         "disp_p5_p50_p95": [round(float(v), 4) for v in np.percentile(h, (5, 50, 95))]}


def moss_layer(name="mossy_rock", sat_gain=1.25, hue_shift=0.0):
    d = PH / name
    diff = load(d / f"{name}_diff_2k.jpg")
    L, a, b = to_opp(diff)
    # push toward the sheet's yellow-green moss: more saturation on the green side, a touch darker
    out = from_opp(L * 0.92, a * sat_gain - 0.01, b * sat_gain + 0.03)
    out = np.clip(out, 0, 1)
    return out, {"source": f"{name} (Poly Haven CC0)", "after": stats(out)}


# ----------------------------------------------------------------------------------------------- lichen detail
# Pilot 2 fix 1 (judge: "lichen is uniform pale stamps with soft alpha edges and no internal structure"; the sheet's
# lichen panel, bottom row 5th, looked at: foliose rosettes of 3-7 broad rounded lobes with scalloped margins,
# lighter raised lobe rims, radial texture, a darker centre with a dark spot, lobes overlapping like petals, clusters
# that merge). The baked unique maps hold 5 px/cm, far too coarse for that, so lichen is a TILING DETAIL like the
# grain: this periodic tile (1024 px = 0.5 m, 20 px/cm) carries crisp rosettes; the baked M.G (lichen zone) decides
# where they appear, per rosette (an id channel), so a rosette is shown whole or not at all.
LICHEN_TILE_M = 0.5


def _wrap_window(n, cx, cy, r):
    x0, x1 = int(math.floor(cx - r)) - 1, int(math.ceil(cx + r)) + 2
    y0, y1 = int(math.floor(cy - r)) - 1, int(math.ceil(cy + r)) + 2
    xs = np.arange(x0, x1)
    ys = np.arange(y0, y1)
    X, Y = np.meshgrid(xs, ys)
    return X, Y, X % n, Y % n


def lichen_layer(n=1024, tile_m=LICHEN_TILE_M, seed=9101, clusters=34, r_cm=(0.9, 2.9)):
    rng = np.random.default_rng(seed)
    ppcm = n / (tile_m * 100.0)
    cover = np.zeros((n, n))
    shade = np.zeros((n, n))           # 0 crease .. 1 rim
    height = np.zeros((n, n))
    rid = np.zeros((n, n))
    centre_dark = np.zeros((n, n))
    placed = []
    for ci in range(clusters):
        ccx, ccy = rng.uniform(0, n, 2)
        k = int(rng.integers(1, 6))
        for _ in range(k):
            R = float(np.exp(rng.uniform(math.log(r_cm[0]), math.log(r_cm[1])))) * ppcm
            ang = rng.uniform(0, 2 * math.pi)
            dd = rng.uniform(0.0, 1.6) * R if placed else 0.0
            cx, cy = (ccx + math.cos(ang) * dd) % n, (ccy + math.sin(ang) * dd) % n
            placed.append((cx, cy, R))
            ident = rng.uniform()
            X, Y, Xm, Ym = _wrap_window(n, cx, cy, R * 1.25)
            dx, dy = X - cx, Y - cy
            rr = np.hypot(dx, dy)
            th = np.arctan2(dy, dx)
            nl = int(rng.integers(4, 8))
            ph = rng.uniform(0, 2 * math.pi)
            # lobes: discs around the rosette centre, each with a scalloped (crenate) margin
            lob_cov = np.zeros(X.shape)
            lob_rel = np.full(X.shape, 9.0)
            lob_idx = np.full(X.shape, -1)
            order = rng.permutation(nl)
            for li in order:
                a = ph + 2 * math.pi * li / nl + rng.uniform(-0.25, 0.25)
                lr = R * rng.uniform(0.42, 0.56)
                lc = R * rng.uniform(0.40, 0.55)
                lx, ly = math.cos(a) * lc, math.sin(a) * lc
                ddx, ddy = dx - lx, dy - ly
                d = np.hypot(ddx, ddy)
                phi = np.arctan2(ddy, ddx)
                m = int(rng.integers(5, 10))
                edge = lr * (1.0 + 0.055 * np.abs(np.sin(0.5 * m * phi + rng.uniform(0, 6.28))) +
                             0.02 * np.sin(2.3 * m * phi + rng.uniform(0, 6.28)))
                inside = d < edge
                # later lobes lie over earlier ones (overlapping petals)
                lob_rel = np.where(inside, d / edge, lob_rel)
                lob_idx = np.where(inside, li, lob_idx)
                lob_cov = np.maximum(lob_cov, np.clip((edge - d) / 1.2 + 0.5, 0, 1))
            core = rr < R * 0.34
            lob_cov = np.maximum(lob_cov, np.clip((R * 0.34 - rr) / 1.2 + 0.5, 0, 1))
            rel = np.where(lob_idx >= 0, lob_rel, np.where(core, rr / (R * 0.34) * 0.5, 9.0))
            # shade: lighter raised rim on each lobe (outer 18 %), a darker line just inside where a lobe overlaps
            # another (the edge of the upper lobe), radial striation, darker centre
            rim = np.clip((rel - 0.80) / 0.14, 0, 1)
            stri = 0.5 + 0.5 * np.sin(th * rng.uniform(16, 26) + 2.0 * np.sin(rr / max(R, 1) * 5.0))
            sh = 0.62 + 0.30 * rim + 0.06 * (stri - 0.5)
            sh = np.where(rel > 0.985, 0.25, sh)               # the lobe margin itself is a thin dark crease
            cdark = np.clip(1.0 - rr / (R * 0.30), 0, 1)
            m_new = lob_cov > cover[Ym, Xm]
            cover[Ym, Xm] = np.maximum(cover[Ym, Xm], lob_cov)
            shade[Ym, Xm] = np.where(m_new, sh, shade[Ym, Xm])
            centre_dark[Ym, Xm] = np.where(m_new, cdark, centre_dark[Ym, Xm])
            rid[Ym, Xm] = np.where(m_new & (lob_cov > 0.01), ident, rid[Ym, Xm])
            h = (0.55 + 0.45 * rim) * np.clip(lob_cov, 0, 1) * (1.0 - 0.4 * cdark)
            height[Ym, Xm] = np.maximum(height[Ym, Xm], h)
    noise = periodic_noise(n, 60, 200, rng) * 0.035
    body = np.array([0.79, 0.81, 0.72])
    rimc = np.array([0.88, 0.89, 0.82])
    crease = np.array([0.42, 0.44, 0.36])
    cen = np.array([0.50, 0.50, 0.40])
    dot = np.array([0.22, 0.20, 0.16])
    t = np.clip((shade - 0.25) / 0.65, 0, 1)[..., None]
    col = crease * (1 - t) + (body * (1 - np.clip(t * 1.4 - 0.4, 0, 1)) + rimc * np.clip(t * 1.4 - 0.4, 0, 1)) * t
    cd = centre_dark[..., None]
    col = col * (1 - 0.8 * cd) + cen * 0.8 * cd
    col = np.where((centre_dark > 0.78)[..., None], dot, col)
    col = np.clip(col + noise[..., None], 0, 1)
    rgba = np.concatenate([col, cover[..., None]], -1)
    # normal from height (lobes raised ~1 mm; DirectX: +y down)
    hm = height * 1.0                                   # mm
    gx = (np.roll(hm, -1, 1) - np.roll(hm, 1, 1)) * 0.5 * ppcm / 10.0   # mm per mm
    gy = (np.roll(hm, -1, 0) - np.roll(hm, 1, 0)) * 0.5 * ppcm / 10.0
    nv = np.stack([-gx, gy, np.ones_like(gx)], -1)
    nv /= np.linalg.norm(nv, axis=-1, keepdims=True)
    hid = np.stack([np.clip(height, 0, 1), rid, np.zeros_like(rid)], -1)
    info = {"tile_m": tile_m, "px": n, "rosettes": len(placed), "cover_share": round(float((cover > 0.5).mean()), 3),
            "radius_cm": list(r_cm), "maker": "ours (procedural, numpy); no scan"}
    return rgba, nv * 0.5 + 0.5, hid, info


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ship", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--prefix", default="T_DKR")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    ship, work = Path(a.ship), Path(a.work)
    ship.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    if a.only == "lichen":
        rgba, nm, hid, li = lichen_layer()
        li["files"] = [save(rgba, ship / f"{a.prefix}_LichenDetail_BC.png", "RGBA"),
                       save(nm, ship / f"{a.prefix}_LichenDetail_N.png"),
                       save(hid, ship / f"{a.prefix}_LichenDetail_HID.png")]
        jp = work / "scan_surface.json"
        info = json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else {}
        info["lichen"] = li
        jp.write_text(json.dumps(info, indent=1), encoding="utf-8")
        print(json.dumps(li, indent=1))
        return
    info = {}
    bc, nm, h, gi = grain_layer()
    info["grain"] = gi
    info["grain"]["files"] = [save(bc, ship / f"{a.prefix}_GraniteGrain_BC.png"),
                              save(nm, ship / f"{a.prefix}_GraniteGrain_N.png"),
                              save(h, work / f"{a.prefix}_GraniteGrain_H.png", "L")]
    # pilot 2 fix 1: the macro layers were graded too bright and flat (whole-rock local contrast 0.08-0.10 vs the
    # sheet's 0.13-0.15; its p5 is 0.10): the scan's own 1-10 cm mottling is kept (less blur, full band) and the
    # luma targets widened toward the sheet's rock percentiles (ref_measure.json, RiverRound front: 0.10 / 0.23 /
    # 0.38 / 0.56 / 0.76 under the studio light; the bake is albedo, so the targets sit above those)
    for nm_, key, tg in (("tiger_rock", "cliff", (0.16, 0.34, 0.48, 0.61, 0.80)),
                         ("rock_surface", "river", (0.14, 0.32, 0.47, 0.61, 0.81))):
        m, hh, nor, mi = macro_layer(nm_, tg, band_keep=1.0, blur_px=0.0, pre_blur_px=2.5)
        mi["files"] = [save(m, work / f"Macro_{key}_BC.png"), save(hh, work / f"Macro_{key}_H.png", "L"),
                       save(nor, work / f"Macro_{key}_N_dx.png")]
        info["macro_" + key] = mi
    mo, moi = moss_layer()
    moi["files"] = [save(mo, ship / f"{a.prefix}_MossDetail_BC.png")]
    info["moss"] = moi
    (work / "scan_surface.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("quilt",)} for k, v in info.items()},
                     indent=1))


if __name__ == "__main__":
    main()
