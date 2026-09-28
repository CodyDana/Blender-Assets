# -*- coding: utf-8 -*-
"""Like-for-like paper-grain calibration: V1 guide vs our shipped BC map.

METROLOGY ONLY.  This script MEASURES the guide; it never copies a pixel of it into
anything that ships.  It exists because REFERENCE_SPEC row 26's absolute figures
(17.0 % amplitude on a 0.50 mm cell) are not reproducible by an independent
instrument - a fourth measuring pass read V1 at 2.69 % - so the build needs a target
taken with the SAME instrument on both sheets.

Run:
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" grain_calibration.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "reference_metrology"))
import pngread  # noqa: E402

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
V1 = os.path.join(ROOT, "References", "PaperBomb", "paperbomb_guide.png")
BC = os.path.join(ROOT, "Exports", "PaperBomb", "Textures", "T_PaperBomb_BC.png")
OUT = os.path.join(HERE, "grain_calibration.json")

CARD_W_MM, CARD_H_MM = 70.0, 156.0


def _load(path):
    a, _info = pngread.read_png(path)
    a = a.astype(np.float64) / (65535.0 if a.dtype == np.uint16 else 255.0)
    if a.ndim == 2:
        a = a[..., None]
    if a.shape[2] == 1:
        a = np.repeat(a, 3, axis=2)
    return a[..., :3]


def _luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def v1_tag_rect(a):
    """The tag rectangle, by the half-maximum of the paper-to-background warmth."""
    warm = a[..., 0] - a[..., 2]
    hi = float(np.percentile(warm, 99.0))
    lo = float(np.percentile(warm, 1.0))
    m = warm > (lo + 0.5 * (hi - lo))
    ys = np.flatnonzero(m.any(axis=1))
    xs = np.flatnonzero(m.any(axis=0))
    # trim to the largest contiguous run so a stray mark cannot set the rect
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1


def box(a, r):
    p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    s = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
    return s / (n * n)


def first_zero(sig, ppmm, max_mm=8.0):
    s = sig - sig.mean()
    n = min(len(s), int(round(max_mm * ppmm)))
    if n < 4:
        return 0.0
    ac = np.array([float(np.mean(s[:len(s) - k] * s[k:])) for k in range(n)])
    if ac[0] <= 0:
        return 0.0
    ac = ac / ac[0]
    z = np.flatnonzero(ac <= 0.0)
    return (float(z[0]) / ppmm) if z.size else n / ppmm


def measure(luma, paper, ppmm, label):
    """Amplitude (p95-p05 of the <1.2 mm detail over the local mean) and ACF length.

    ``paper`` is True where the sheet is bare.  Ink is excluded from the STATISTICS
    but left in the field, so the box filters see the same signal on both sheets.
    """
    hi = box(luma, max(2, int(round(1.2 * ppmm))))
    detail = luma - hi
    sel = paper
    if sel.sum() < 5000:
        return {}
    mean = float(np.mean(luma[sel]))
    amp = float(np.percentile(detail[sel], 95) - np.percentile(detail[sel], 5)) / max(mean, 1e-9)
    lo = box(luma, max(1, int(round(0.10 * ppmm))))
    bandpass = lo - box(luma, max(2, int(round(1.0 * ppmm))))
    # MASKED autocorrelation: only lags where BOTH samples are bare paper count, so
    # the strokes never enter the correlation and no whole row has to be clear of ink.
    def acf_len(field, mask, axis):
        f = np.where(mask, field - field[mask].mean(), 0.0)
        w = mask.astype(np.float64)
        n = int(round(8.0 * ppmm))
        n = min(n, field.shape[axis] - 2)
        ac = np.empty(n)
        for k in range(n):
            if axis == 1:
                num = float((f[:, :field.shape[1] - k] * f[:, k:]).sum())
                den = float((w[:, :field.shape[1] - k] * w[:, k:]).sum())
            else:
                num = float((f[:field.shape[0] - k] * f[k:]).sum())
                den = float((w[:field.shape[0] - k] * w[k:]).sum())
            ac[k] = num / max(den, 1.0)
        if ac[0] <= 0:
            return 0.0
        ac = ac / ac[0]
        z = np.flatnonzero(ac <= 0.0)
        return (float(z[0]) / ppmm) if z.size else n / ppmm

    cx = acf_len(bandpass, paper, 1)
    cy = acf_len(bandpass, paper, 0)
    m = min(cx, cy)
    energy = float(np.sqrt(np.mean(detail[sel] ** 2)) / max(mean, 1e-9))
    return {
        "label": label,
        "ppmm": round(ppmm, 4),
        "amplitude": round(amp, 5),
        "acf_first_zero_x_mm": round(cx, 4),
        "acf_first_zero_y_mm": round(cy, 4),
        "cell_mm": round(2.0 * m, 4) if m > 0 else 0.0,
        "anisotropy": round(max(cx, cy) / max(m, 1e-6), 3) if m > 0 else 99.0,
        "texture_energy": round(energy, 5),
        "paper_pixels": int(sel.sum()),
    }


def main():
    out = {}

    # --- V1 ------------------------------------------------------------------
    a = _load(V1)
    x0, y0, x1, y1 = v1_tag_rect(a)
    tag = a[y0:y1, x0:x1]
    ppx = (x1 - x0) / CARD_W_MM
    ppy = (y1 - y0) / CARD_H_MM
    ppmm = 0.5 * (ppx + ppy)
    lum = _luma(tag)
    mx = tag.max(axis=2)
    mn = tag.min(axis=2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    ink = (lum < 0.72) | (sat > 0.34)
    paper = ~(box(ink.astype(np.float64), max(2, int(round(1.5 * ppmm)))) > 0.001)
    # interior only: clear of the aged rim, same window the build's own grain() uses
    sy = slice(int(26 * ppy), int((CARD_H_MM - 26) * ppy))
    sx = slice(int(16 * ppx), int((CARD_W_MM - 16) * ppx))
    out["V1"] = measure(lum[sy, sx], paper[sy, sx], ppmm, "V1 guide")
    out["V1"]["tag_px"] = [x1 - x0, y1 - y0]

    # --- ours ---------------------------------------------------------------
    b = _load(BC)
    PPMM = 12.923
    OX = OY = 16
    card = b[OY:OY + int(round(CARD_H_MM * PPMM)), OX:OX + int(round(CARD_W_MM * PPMM))]
    lum2 = _luma(card)
    mx = card.max(axis=2)
    mn = card.min(axis=2)
    sat2 = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    ink2 = (lum2 < 0.72) | (sat2 > 0.34)
    paper2 = ~(box(ink2.astype(np.float64), max(2, int(round(1.5 * PPMM)))) > 0.001)
    sy2 = slice(int(26 * PPMM), int((CARD_H_MM - 26) * PPMM))
    sx2 = slice(int(16 * PPMM), int((CARD_W_MM - 16) * PPMM))
    out["OURS"] = measure(lum2[sy2, sx2], paper2[sy2, sx2], PPMM, "shipped BC front island")

    if out["V1"] and out["OURS"]:
        out["ratio"] = {
            "amplitude_ours_over_v1": round(out["OURS"]["amplitude"] / max(out["V1"]["amplitude"], 1e-9), 3),
            "acf_ours_over_v1": round(out["OURS"]["cell_mm"] / max(out["V1"]["cell_mm"], 1e-9), 3),
            "energy_ours_over_v1": round(out["OURS"]["texture_energy"] / max(out["V1"]["texture_energy"], 1e-9), 3),
        }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
