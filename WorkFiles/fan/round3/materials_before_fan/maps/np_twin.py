"""Float64 twin of the pack's recolour graphs, version 2 (final pass, 2026-09-26). Pure numpy.

This is the ONE place the Python side writes down what M_Fabric_Master / M_PaperInk_Master compute, node for node
(np_functions.py + np_masters.py). derive_constants.py, verify/analyse_captures.py and the final stress test all use
it. recolour_common.tint_detail is the version-1 twin the map generators' own gates were written against; it is kept
unchanged so those generators still reproduce their recorded gates.

Fabric (MF_TintDetail v2 + MF_AlbedoRollOff), per texel:
    Colour_f = Colour + max(ColourFloor - max3(Colour), 0)            pure black is lifted to ~#1A1A1A (hue kept)
    Colour_e = Colour_f * min(1, LightestColour / max3(Colour_f))     very light picks are scaled down to the lightest
                                                                      mean that keeps highlight detail (hue kept)
    H        = log(AlbedoCeiling / max3(Colour_e)) / log(HighlightRatio)
    C_hi     = min(Strength, max(H, 0));  C_lo = lerp(Strength, C_hi, DarkFollow)
    n        = max(DetailBias + DetailScale * Detail, 1e-6);  x = n > 1 ? C_hi : C_lo
    E        = cubic(MomentsLow, C_lo) + cubic(MomentsHigh, C_hi)
    K        = exp(-A(lod) * max(1 - C_hi, 0)^P)                      mip compensation: the power law is applied to the
                                                                      MIP-FILTERED detail, which reads lighter than the
                                                                      filtered result (Jensen); K restores the mean.
                                                                      A(lod) piecewise linear, A(0) = 0. K = 1 at C = 1.
    Albedo   = RollOff(Colour_e * n^x * DetailMean / E * K, 0.85, 0.95)
At the shipped colour every guard is inactive (Colour > floor, Colour < Lightest, H >= 1, so C = 1, E = DetailMean,
K = 1) and Albedo = Colour * n exactly: the item's baked colour at every mip.

Paper (M_PaperInk_Master v2):
    Paper_e  = floor + (Paper * min(1, PaperColourLimit / max3(Paper)))
    gain     = lerp(mean(PoolGain), PoolGain, saturate(sat(Red) / RedPoolDefaultSaturation))
    RedPool  = lerp(Y(Red), Red, PoolSaturation) * gain
    total    = Paper_e * PaperDetail.rgb * PaperWeightScale + Black * W.r + BlackDry * W.g + Red * W.b + RedDry * W.a
               + RedPool * PaperDetail.a;   BaseColor = min(total, AlbedoCeiling) * lerp(1, AO, BakedAOInColour)
"""
from __future__ import annotations

import numpy as np

LUM = np.array([0.2126, 0.7152, 0.0722])
KNEE, LIMIT = 0.85, 0.95
COLOUR_FLOOR = 0.01


def s2l(x):
    x = np.asarray(x, np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def cubic(m, c):
    return m[0] + c * (m[1] + c * (m[2] + c * m[3]))


def mip_A(p: dict, lod: float) -> float:
    inc = list(p["Detail Mip Compensation 1-4"][:4]) + list(p["Detail Mip Compensation 5-8"][:4])
    return float(sum(d * min(max(lod - i, 0.0), 1.0) for i, d in enumerate(inc)))


def fabric_colour(p: dict, colour) -> np.ndarray:
    c = np.asarray(colour, np.float64)[:3]
    c = c + max(COLOUR_FLOOR - float(c.max()), 0.0)
    return c * min(1.0, p["Lightest Colour"] / max(float(c.max()), 1e-4))


def fabric_exponents(p: dict, colour_e, strength=None):
    s = p.get("Detail Strength", 1.0) if strength is None else strength
    h = np.log(p["Albedo Ceiling"] / max(float(np.max(colour_e)), 1e-4)) / np.log(p["Detail Highlight Ratio"])
    c_hi = min(s, max(h, 0.0))
    c_lo = s + (c_hi - s) * p["Dark Detail Follow"]
    return float(h), float(c_hi), float(c_lo)


def fabric_scalar(p: dict, d, colour, lod: float = 0.0, strength=None, mip_comp=True):
    """(g, Colour_e, info): the per-texel factor g with Albedo = Colour_e * g (the roll-off scales all channels by one
    factor, so the whole graph is Colour_e times a scalar). ``d`` = the Detail Map value(s), linear 0..1."""
    ce = fabric_colour(p, colour)
    h, c_hi, c_lo = fabric_exponents(p, ce, strength)
    n = np.maximum(p["Detail Bias"] + p["Detail Scale"] * np.asarray(d, np.float64), 1e-6)
    x = np.where(n > 1.0, c_hi, c_lo)
    e = cubic(p["Detail Moments Low"], c_lo) + cubic(p["Detail Moments High"], c_hi)
    k = np.exp(-mip_A(p, lod) * max(1.0 - c_hi, 0.0) ** p["Detail Mip Compensation Power"]) if mip_comp else 1.0
    s = np.power(n, x) * (p["Detail Mean"] / e) * k
    m = float(ce.max()) * s
    w = LIMIT - KNEE
    mm = KNEE + w * (1.0 - np.exp(-np.maximum(m - KNEE, 0.0) / w))
    g = s * (mm / np.maximum(m, KNEE))
    return g, ce, {"H": h, "C_hi": c_hi, "C_lo": c_lo, "E": float(e), "K": float(k), "colour_e": ce.tolist()}


def fabric_albedo(p: dict, d, colour, lod: float = 0.0, strength=None):
    g, ce, info = fabric_scalar(p, d, colour, lod, strength)
    return ce * np.asarray(g)[..., None], info


def ink_derive(p: dict, paper, black, red):
    paper, black, red = (np.asarray(v, np.float64)[:3] for v in (paper, black, red))
    black_dry = (black + (paper - black) * p["Black Ink Dry Paper Mix"]) * np.asarray(p["Black Ink Dry Gain"][:3])
    red_dry = s2l(np.clip(p["Red Ink Dry Value Scale"] * l2s(np.clip(red, 0.0, 1.0)), 0.0, 1.0))
    y = float(red @ LUM)
    gain = np.asarray(p["Red Ink Pool Gain"][:3], np.float64)
    mx, mn = float(red.max()), float(red.min())
    sat = (mx - mn) / max(mx, 1e-6)
    t = min(max(sat / p["Red Ink Pool Default Saturation"], 0.0), 1.0)
    gain_e = gain.mean() + (gain - gain.mean()) * t
    red_pool = (y + (red - y) * p["Red Ink Pool Saturation"]) * gain_e
    return black_dry, red_dry, red_pool


def paper_colour(p: dict, paper):
    c = np.asarray(paper, np.float64)[:3]
    c = c + max(COLOUR_FLOOR - float(c.max()), 0.0)
    return c * min(1.0, p["Paper Colour Limit"] / max(float(c.max()), 1e-4))


def paper_albedo(p: dict, maps: dict, paper=None, black=None, red=None, ao_in_colour=None, clip=True):
    """maps: pd_rgb (decoded, (...,3)), pd_a (...,1), iw (...,4), ao (...,1). Returns (albedo, unclipped, derived)."""
    paper = p["Paper Colour"] if paper is None else paper
    black = p["Black Ink Colour"] if black is None else black
    red = p["Red Ink Colour"] if red is None else red
    pe = paper_colour(p, paper)
    black = np.asarray(black, np.float64)[:3]
    red = np.asarray(red, np.float64)[:3]
    bd, rd, rp = ink_derive(p, pe, black, red)
    iw = maps["iw"]
    tot = (pe * maps["pd_rgb"] * p["Paper Weight Scale"] + black * iw[..., 0:1] + bd * iw[..., 1:2]
           + red * iw[..., 2:3] + rd * iw[..., 3:4] + rp * maps["pd_a"])
    unclipped = tot
    if clip:
        tot = np.minimum(tot, p["Albedo Ceiling"])
    ao = p.get("Baked AO In Colour", 1.0) if ao_in_colour is None else ao_in_colour
    if ao:
        tot = tot * (1.0 + (maps["ao"] - 1.0) * ao)
    return tot, unclipped, {"PaperColour_e": pe.tolist(), "BlackDry": bd.tolist(), "RedDry": rd.tolist(),
                            "RedPool": rp.tolist()}
