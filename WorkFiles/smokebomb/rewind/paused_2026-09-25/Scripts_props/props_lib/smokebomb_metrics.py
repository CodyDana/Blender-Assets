#!/usr/bin/env python
"""props_lib.smokebomb_metrics - REFERENCE_SPEC's instruments, run on a RENDER.

numpy only.  Every function takes a stored-sRGB image (rows top-down, 0..1) of the
reference view and measures what a viewer sees; the same functions run on the reference
itself give the instrument's own reading of it, so a comparison never mixes two methods.
Nothing here writes a map or feeds the asset: it measures.

    silhouette   half-maximum outline (backdrop 0.996 vs rim cloth 0.162, as the spec),
                 3600 radial samples, circle fit, rms deviation, 30 deg sectors, ellipse,
                 steps (radius jumps >= 4 px within 0.5 deg), fuzz past the outline
    tones        stored-luma percentiles over the disc r < 0.9 R
    lighting     16 px blocks, 75th percentile linear luma, per quadrant (spec 3)
    colour       chromaticity and HSV hue / saturation of the disc
    sparkle      fraction of disc pixels brighter than 3x their 7 px local median
    weave        dominant spectral period of 64 px patches (px)
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np

EDGE_LEVEL = 0.5 * (0.996 + 0.162)
REF_CENTRE = (627.38, 628.92)
REF_R = 464.11


def luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def to_linear(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _bilinear(img, x, y):
    h, w = img.shape
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    tx, ty = x - x0, y - y0
    return ((1 - tx) * (1 - ty) * img[y0, x0] + tx * (1 - ty) * img[y0, x0 + 1]
            + (1 - tx) * ty * img[y0 + 1, x0] + tx * ty * img[y0 + 1, x0 + 1])


def fit_circle(x, y):
    A = np.stack([x, y, np.ones_like(x)], axis=1)
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0] / 2, c[1] / 2
    r = math.sqrt(c[2] + cx * cx + cy * cy)
    return cx, cy, r


def silhouette(stored_rgb: np.ndarray, n: int = 3600, guess=REF_CENTRE, guess_r=REF_R) -> Dict:
    L = luma(stored_rgb)
    th = np.radians(np.arange(n) * 360.0 / n)
    rr = np.arange(guess_r * 1.25, guess_r * 0.75, -0.25)
    cx, cy = guess
    radii = np.full(n, np.nan)
    for it in range(2):
        X = cx + np.cos(th)[:, None] * rr[None, :]
        Y = cy - np.sin(th)[:, None] * rr[None, :]
        V = _bilinear(L, X, Y)
        below = V < EDGE_LEVEL
        first = np.argmax(below, axis=1)
        ok = below.any(axis=1) & (first > 0)
        i = np.clip(first, 1, len(rr) - 1)
        v0 = V[np.arange(n), i - 1]
        v1 = V[np.arange(n), i]
        t = np.clip((v0 - EDGE_LEVEL) / np.maximum(v0 - v1, 1e-9), 0, 1)
        radii = np.where(ok, rr[i - 1] - t * 0.25, np.nan)
        px = cx + np.cos(th) * radii
        py = cy - np.sin(th) * radii
        good = np.isfinite(radii)
        cx, cy, R = fit_circle(px[good], py[good])
    dev = np.sqrt((px - cx) ** 2 + (py - cy) ** 2) - R
    ang = np.degrees(np.arctan2(-(py - cy), px - cx)) % 360.0
    order = np.argsort(ang)
    ang, dev = ang[order], dev[order]
    sectors = []
    for a in range(0, 360, 30):
        m = (ang >= a) & (ang < a + 30)
        sectors.append(round(float(np.nanmean(dev[m]) / R * 100), 2))
    # low-order reconstruction (n <= 6) for bumpiness
    F = np.fft.rfft(np.nan_to_num(dev))
    F6 = F.copy()
    F6[7:] = 0
    smooth = np.fft.irfft(F6, n=len(dev))
    bump = dev - smooth
    # steps: radius jumps >= 4 px within 0.5 deg (5 samples)
    k = max(1, int(round(0.5 / (360.0 / n))))
    jump = np.abs(np.roll(dev, -k) - dev)
    peaks = []
    i = 0
    while i < n:
        if jump[i] >= 4.0:
            j = i
            while j < n and jump[j] >= 4.0:
                j += 1
            seg = jump[i:j]
            peaks.append((float(ang[i + int(np.argmax(seg))]), float(seg.max())))
            i = j + k
        else:
            i += 1
    harm = np.abs(F[:9]) * 2 / len(dev)
    # ellipse (algebraic, direct least squares on the edge points)
    ell = _ellipse(px[good] - cx, py[good] - cy)
    return {"centre_px": [round(cx, 2), round(cy, 2)], "diameter_px": round(2 * R, 2),
            "rms_dev_pctR": round(float(np.sqrt(np.nanmean(dev ** 2)) / R * 100), 3),
            "max_out_in_px": [round(float(np.nanmax(dev)), 1), round(float(np.nanmin(dev)), 1)],
            "sectors_30deg_pctR": sectors,
            "bumpiness_rms_pctR": round(float(np.sqrt(np.nanmean(bump ** 2)) / R * 100), 3),
            "steps": {"count_ge_4px": len(peaks),
                      "median_px": round(float(np.median([p[1] for p in peaks])), 2) if peaks else 0.0,
                      "max_px": round(float(max([p[1] for p in peaks])), 2) if peaks else 0.0,
                      "where_deg": [round(p[0], 1) for p in peaks]},
            "harmonics_px": [round(float(h), 2) for h in harm[1:9]],
            "ellipse": ell}


def _ellipse(x, y):
    D = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], axis=1)
    _, _, Vt = np.linalg.svd(D, full_matrices=False)
    a, b, c, d, e, f = Vt[-1]
    M = np.array([[a, b / 2], [b / 2, c]])
    w, v = np.linalg.eigh(M)
    x0 = np.linalg.solve(2 * M, [-d, -e])
    F0 = f + 0.5 * (d * x0[0] + e * x0[1])
    axes = np.sqrt(np.abs(-F0 / w))
    long_i = int(np.argmax(axes))
    vec = v[:, long_i]
    angle = math.degrees(math.atan2(-vec[1], vec[0])) % 180.0      # image y is down
    return {"axes_px": [round(float(axes.max()), 2), round(float(axes.min()), 2)],
            "ratio": round(float(axes.max() / axes.min()), 4),
            "long_axis_image_angle_deg": round(angle, 1)}


def disc_mask(shape, centre, R, frac=0.9):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return (xx + 0.5 - centre[0]) ** 2 + (yy + 0.5 - centre[1]) ** 2 < (frac * R) ** 2


def tones(stored_rgb, centre=REF_CENTRE, R=REF_R) -> Dict:
    m = disc_mask(stored_rgb.shape[:2], centre, R)
    L = luma(stored_rgb)[m]
    q = [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]
    return {f"p{p}": round(float(np.percentile(L, p)), 4) for p in q}


def lighting(stored_rgb, centre=REF_CENTRE, R=REF_R) -> Dict:
    lin = luma(to_linear(stored_rgb))
    h, w = lin.shape
    B = 16
    out = {"upper_left": [], "upper_right": [], "lower_left": [], "lower_right": [], "centre": []}
    for by in range(0, h - B, B):
        for bx in range(0, w - B, B):
            cx_, cy_ = bx + B / 2, by + B / 2
            r = math.hypot(cx_ - centre[0], cy_ - centre[1]) / R
            if r > 0.9:
                continue
            v = float(np.percentile(lin[by:by + B, bx:bx + B], 75))
            if r < 0.35:
                out["centre"].append(v)
            else:
                key = ("upper_" if cy_ < centre[1] else "lower_") + ("left" if cx_ < centre[0] else "right")
                out[key].append(v)
    return {k: round(float(np.mean(v)), 5) for k, v in out.items()}


def colour(stored_rgb, centre=REF_CENTRE, R=REF_R) -> Dict:
    m = disc_mask(stored_rgb.shape[:2], centre, R)
    lin = to_linear(stored_rgb)[m]
    mean = lin.mean(axis=0)
    chrom = mean / mean.sum()
    st = stored_rgb[m].mean(axis=0)
    mx, mn = st.max(), st.min()
    hue = 0.0
    if mx > mn:
        r, g, b = st
        if mx == r:
            hue = (60 * ((g - b) / (mx - mn)) + 360) % 360
        elif mx == g:
            hue = 60 * ((b - r) / (mx - mn)) + 120
        else:
            hue = 60 * ((r - g) / (mx - mn)) + 240
    return {"chromaticity_lin": [round(float(c), 4) for c in chrom],
            "mean_stored": [round(float(c), 4) for c in st],
            "hue_deg": round(float(hue), 1), "saturation": round(float((mx - mn) / mx), 3) if mx > 0 else 0.0}


def _gblur(a, sigma):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (math.pi ** 2) * (sigma ** 2) * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def sparkle(stored_rgb, centre=REF_CENTRE, R=REF_R, sigma: float = 6.0) -> Dict:
    """REFERENCE_SPEC 7's definition (round 2): the share of disc pixels whose LINEAR luma
    is more than 3x its Gaussian (sigma 6 px) local mean.  It reads the reference at 4.23 %
    (the spec's 4.2 %); round 1's 7 px median version read it at 1.42 % and was dropped."""
    L = luma(to_linear(stored_rgb))
    h, w = L.shape
    med = _gblur(L, sigma)
    m = disc_mask(L.shape, centre, R)
    bright = (L > 3.0 * med) & m
    rings = []
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.hypot(xx + 0.5 - centre[0], yy + 0.5 - centre[1]) / R
    for a, b in ((0, 0.3), (0.3, 0.6), (0.6, 0.8), (0.8, 0.9)):
        mm = (rr >= a) & (rr < b)
        rings.append(round(float(bright[mm].mean()), 4))
    return {"fraction": round(float(bright[m].mean()), 4), "by_ring": rings}


def weave_period(stored_rgb, centre=REF_CENTRE, R=REF_R, patch: int = 64, n: int = 40, seed: int = 3) -> Dict:
    L = np.log(np.maximum(luma(to_linear(stored_rgb)), 1e-4))
    rng = np.random.default_rng(seed)
    periods = []
    for _ in range(n * 4):
        if len(periods) >= n:
            break
        ang = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(0, 0.6) * R
        x = int(centre[0] + r * np.cos(ang)) - patch // 2
        y = int(centre[1] + r * np.sin(ang)) - patch // 2
        p = L[y:y + patch, x:x + patch]
        if p.shape != (patch, patch):
            continue
        p = p - p.mean()
        win = np.hanning(patch)[:, None] * np.hanning(patch)[None, :]
        Fp = np.abs(np.fft.fftshift(np.fft.fft2(p * win))) ** 2
        c = patch // 2
        yy, xx = np.mgrid[-c:c, -c:c]
        rad = np.hypot(xx, yy)
        band = (rad >= patch / 8.0) & (rad <= patch / 2.8)    # periods 2.8 .. 8 px
        if not band.any():
            continue
        i = np.argmax(np.where(band, Fp, 0))
        periods.append(patch / rad.ravel()[i])
    return {"dominant_period_px_median": round(float(np.median(periods)), 2) if periods else None,
            "patches": len(periods)}


def measure_all(stored_rgb) -> Dict:
    sil = silhouette(stored_rgb)
    c = tuple(sil["centre_px"])
    R = sil["diameter_px"] / 2
    return {"silhouette": sil, "tones": tones(stored_rgb, c, R), "lighting": lighting(stored_rgb, c, R),
            "colour": colour(stored_rgb, c, R), "sparkle": sparkle(stored_rgb, c, R),
            "weave": weave_period(stored_rgb, c, R)}


__all__ = ["silhouette", "tones", "lighting", "colour", "sparkle", "weave_period", "measure_all",
           "luma", "to_linear"]
