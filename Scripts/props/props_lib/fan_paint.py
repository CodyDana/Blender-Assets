#!/usr/bin/env python
"""props_lib.fan_paint - SK_Fan's and SK_Fan_Tassel's maps, painted from each part's own coordinates.

numpy only.  Every texel is rasterised from the mesh's UV0 and painted from the LOCAL coordinates the
geometry stored per corner (the flat leaf in mm, a stick's own frame, the eyelet's lathe, the tassel's
strands), never from any image.  NO SURFACE DESIGN: plain black silk, plain black lacquered bamboo, a
plain black silk tassel, a polished eyelet - the fan2 painting (willow, swirls, seal) and the rib
openwork are left for the design stage.

    leaf     habotai silk: warp and weft slubs (0.3 - 3 mm streaks) along the leaf's grain (the flat
             leaf's centre line), a soft mottle; roughness 0.55 - 0.65 (satin sheen).  Round 2: the silk's
             relief in the normal map - the weave's fine ripple and the soft cockling a glued silk leaf
             takes (a few mm across, a few hundredths of a mm high), so a pleat face is not one flat value
    sticks   black lacquered bamboo: fibre streaks along each stick, lacquer roughness 0.25 - 0.36 (round 2: glossier).  Round 2:
             each rib its own slightly different tone and set (a hand-shaved rib is never perfectly flat),
             and rounded long edges, so neighbouring ribs read apart as on fan2
    rivet    polished nickel-silver: F0 (RS 6 bright-pixel hue), roughness 0.18 - 0.26, metallic 1
    tassel   black silk threads: strands along the skirt and cord, the knot's cord turns

``finish`` (copied from props_lib.blackhat_paint, which is frozen) turns the float channels into the
pack's tint-ready maps: BC, ORM (A = specular mask), N (DirectX), and the FULL-RANGE Detail with
Tint = the part's mean colour, Detail Bias/Scale so mean(Bias + Scale x Detail) = 1.  ``detail16``
writes the lossless 16-bit linear copy the materials build imports (G16).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722])


# =========================================================================== noise
def _mix(h):
    h = (h ^ (h >> np.uint64(33))) * np.uint64(0xff51afd7ed558ccd)
    h = (h ^ (h >> np.uint64(33))) * np.uint64(0xc4ceb9fe1a85ec53)
    return h ^ (h >> np.uint64(33))


def hash01(*keys, seed=0):
    with np.errstate(over="ignore"):
        h = np.uint64(seed * 0x9E3779B97F4A7C15 & 0xFFFFFFFFFFFFFFFF)
        for k in keys:
            k = np.asarray(k).astype(np.int64).astype(np.uint64)
            h = _mix(h ^ (k + np.uint64(0x9E3779B97F4A7C15)))
        return (np.asarray(h) >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def vnoise1(x, seed=0):
    i = np.floor(x)
    f = x - i
    a, b = hash01(i, seed=seed), hash01(i + 1, seed=seed)
    u = f * f * (3 - 2 * f)
    return a + (b - a) * u - 0.5


def vnoise2(x, y, seed=0):
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    u, v = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = hash01(ix, iy, seed=seed)
    b = hash01(ix + 1, iy, seed=seed)
    c = hash01(ix, iy + 1, seed=seed)
    d = hash01(ix + 1, iy + 1, seed=seed)
    return (a + (b - a) * u) + ((c + (d - c) * u) - (a + (b - a) * u)) * v - 0.5


def fbm1(x, seed=0, octaves=3):
    out, amp, f, tot = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        out = out + amp * vnoise1(x * f, seed + 17 * o)
        tot += amp
        amp *= 0.5
        f *= 2.03
    return out / tot


def fbm2(x, y, seed=0, octaves=3):
    out, amp, f, tot = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        out = out + amp * vnoise2(x * f, y * f, seed + 31 * o)
        tot += amp
        amp *= 0.5
        f *= 2.07
    return out / tot


# =========================================================================== rasteriser
def rasterise(uv_tris: np.ndarray, attrs: Dict[str, np.ndarray], size: int, ids: np.ndarray):
    """Rasterise triangles (N, 3, 2) in UV (v up) into a size x size grid (rows top-down).  ``attrs``
    are (N, 3, k) per-corner values, interpolated.  Returns (owner (-1 = empty), dict of (H, W, k))."""
    H = W = size
    owner = np.full((H, W), -1, np.int64)
    out = {k: np.zeros((H, W, v.shape[2])) for k, v in attrs.items()}
    px = np.empty_like(uv_tris)
    px[..., 0] = uv_tris[..., 0] * W
    px[..., 1] = (1.0 - uv_tris[..., 1]) * H
    for t in range(len(px)):
        a, b, c = px[t]
        x0 = max(int(math.floor(min(a[0], b[0], c[0]) - 0.5)), 0)
        x1 = min(int(math.ceil(max(a[0], b[0], c[0]) + 0.5)), W - 1)
        y0 = max(int(math.floor(min(a[1], b[1], c[1]) - 0.5)), 0)
        y1 = min(int(math.ceil(max(a[1], b[1], c[1]) + 0.5)), H - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-14:
            continue
        l0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        l1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        l2 = 1.0 - l0 - l1
        m = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not m.any():
            continue
        yy, xx = np.nonzero(m)
        yy, xx = yy + y0, xx + x0
        owner[yy, xx] = ids[t]
        L = np.stack([l0[m], l1[m], l2[m]], 1)
        for k, v in attrs.items():
            out[k][yy, xx] = L @ v[t]
    return owner, out


def dilate(owner: np.ndarray, chans: Dict[str, np.ndarray], iters: int = 24):
    """Fill empty texels from written neighbours (padding for mips and bilinear taps)."""
    own = owner.copy()
    for _ in range(iters):
        empty = own < 0
        if not empty.any():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(np.roll(own, dy, 0), dx, 1)
            take = empty & (src >= 0)
            if not take.any():
                continue
            own[take] = src[take]
            for k, v in chans.items():
                sv = np.roll(np.roll(v, dy, 0), dx, 1)
                v[take] = sv[take]
            empty = own < 0
    return own


# =========================================================================== maps (finish)
def srgb_encode(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def srgb_decode(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def normal_dx(hgt: np.ndarray, own: np.ndarray, px_per_mm: float, written: np.ndarray) -> np.ndarray:
    h = hgt.astype(np.float64)
    hu = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    hv_down = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    same_u = (np.roll(own, -1, 1) == own) & (np.roll(own, 1, 1) == own)
    same_v = (np.roll(own, -1, 0) == own) & (np.roll(own, 1, 0) == own)
    du = np.where(same_u, hu, 0.0) * px_per_mm
    dv = -np.where(same_v, hv_down, 0.0) * px_per_mm
    n = np.stack([-du, -dv, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[..., 1] *= -1.0                                           # DirectX: green = -Y
    n[~written] = (0.0, 0.0, 1.0)
    return n


def finish(ch, chroma, lo_percentile=0.05, hi_percentile=99.95, rough_range=(0.0, 1.0), metal: bool = False):
    """Float channels -> 8-bit maps + the recolour defaults (props_lib.blackhat_paint.finish, copied).

    ch: written (H, W) bool, alb (H, W) luminance albedo, ao, rough, spec (H, W), hgt (H, W) mm, own, px_per_mm.
    For a metal part (the rivet) BC is the plain F0 colour (not recolourable) and ORM.B = 1."""
    wr = ch["written"]
    alb = ch["alb"].astype(np.float64).copy()
    med = float(np.median(alb[wr]))
    alb[~wr] = med
    chroma = np.asarray(chroma, np.float64)
    ao = np.where(wr, ch["ao"], 1.0)
    rough = np.clip(np.where(wr, ch["rough"], float(np.median(ch["rough"][wr]))), *rough_range)
    spec = np.where(wr, ch["spec"], float(np.median(ch["spec"][wr])))
    orm = np.stack([ao, rough, np.full_like(ao, 1.0 if metal else 0.0), spec], -1)
    ORM8 = np.rint(np.clip(orm, 0, 1) * 255.0).astype(np.uint8)
    n = normal_dx(ch["hgt"], ch["own"], ch["px_per_mm"], wr)
    N8 = np.rint((n * 0.5 + 0.5) * 255.0).astype(np.uint8)
    r8 = ORM8[..., 1][wr] / 255.0
    base = {"ORM": ORM8, "N": N8,
            "roughness_stats": {"min": round(float(r8.min()), 4), "p1": round(float(np.percentile(r8, 1)), 4),
                                "p50": round(float(np.percentile(r8, 50)), 4), "max": round(float(r8.max()), 4)},
            "spec_mask_mean": float(spec[wr].mean()),
            "spec_mask_min_max": [round(float(spec[wr].min()), 4), round(float(spec[wr].max()), 4)],
            "albedo_stats": {"mean": float(ch["alb"][wr].mean()), "p10": float(np.percentile(ch["alb"][wr], 10)),
                             "p50": float(np.percentile(ch["alb"][wr], 50)),
                             "p90": float(np.percentile(ch["alb"][wr], 90)), "max": float(ch["alb"][wr].max())}}
    if metal:
        col = alb[..., None] * (chroma / float(chroma @ LUMA))[None, None, :]
        BC8 = np.rint(srgb_encode(col) * 255.0).astype(np.uint8)
        base.update({"BC": BC8, "tint_linear": (float(alb[wr].mean()) * chroma / float(chroma @ LUMA)).tolist()})
        return base
    a_lo = float(np.percentile(alb[wr], lo_percentile))
    a_hi = float(np.percentile(alb[wr], hi_percentile))
    d = np.clip((alb - a_lo) / (a_hi - a_lo), 0.0, 1.0)
    D8 = np.rint(srgb_encode(d) * 255.0).astype(np.uint8)
    dq = srgb_decode(D8.astype(np.float64) / 255.0)
    mean_d = float(dq[wr].mean())
    mean_alb = a_lo + (a_hi - a_lo) * mean_d
    tint = np.round(mean_alb * chroma / float(chroma @ LUMA), 6)
    t_l = float(tint @ LUMA)
    bias = round(a_lo / t_l, 6)
    scale = round((a_hi - a_lo) / t_l, 6)
    bc_lin = (bias + scale * dq)[..., None] * tint[None, None, :]
    BC8 = np.rint(srgb_encode(bc_lin) * 255.0).astype(np.uint8)
    err = np.abs(srgb_decode(BC8.astype(np.float64) / 255.0) - np.clip(bc_lin, 0, 1))[wr]
    dw = D8[wr]
    base.update({
        "BC": BC8, "Detail": D8, "detail_linear_float": d, "tint_linear": tint.tolist(),
        "tint_srgb": srgb_encode(tint).tolist(), "L_ref": a_hi, "detail_bias": bias, "detail_scale": scale,
        "recolour": {"bc_is_recolour_graph": "BC8 = sRGB8(Tint x (DetailBias + DetailScale x sRGBdecode(Detail8/255))) "
                                             "from the quantised Detail and the rounded sidecar numbers",
                     "tint_is": "the part's MEAN linear colour over the written texels",
                     "detail_bias": bias, "detail_scale": scale,
                     "albedo_lo_hi": [round(a_lo, 6), round(a_hi, 6)],
                     "mean_of_bias_plus_scale_x_detail": round(float((bias + scale * dq[wr]).mean()), 6),
                     "max_abs_err_linear": float(err.max()), "detail_levels_used": int(len(np.unique(dw))),
                     "detail_clipped_share_low_high": [float(np.mean(alb[wr] < a_lo)), float(np.mean(alb[wr] > a_hi))],
                     "detail_min_max_code": [int(dw.min()), int(dw.max())]}})
    return base


def detail16(D8: np.ndarray) -> np.ndarray:
    """The lossless 16-bit LINEAR copy of the 8-bit sRGB-encoded Detail (Recolour/..._Detail16.png)."""
    return np.rint(65535.0 * srgb_decode(D8.astype(np.float64) / 255.0)).astype(np.uint16)


def mip_parity(m) -> dict:
    """The recolour graph against BC through Unreal-style mips (box filter in LINEAR light, 8-bit per
    level): mean over the map at mips 0-8, as the black hat's gate."""
    d = srgb_decode(m["Detail"].astype(np.float64) / 255.0)
    bc = srgb_decode(m["BC"].astype(np.float64) / 255.0) @ LUMA
    tl = float(np.asarray(m["tint_linear"]) @ LUMA)
    b, sc = m["detail_bias"], m["detail_scale"]
    out, lev = [], []
    for lvl in range(9):
        a8 = np.rint(srgb_encode(d) * 255) / 255.0
        b8 = np.rint(srgb_encode(bc) * 255) / 255.0
        a_lin = np.clip(tl * (b + sc * srgb_decode(a8)), 0, 1)
        b_lin = srgb_decode(b8)
        out.append(round(float(a_lin.mean() / max(b_lin.mean(), 1e-12) - 1.0) * 100.0, 3))
        lev.append(round(float(abs(srgb_encode(a_lin.mean()) - srgb_encode(b_lin.mean())) * 255.0), 4))
        if d.shape[0] < 2:
            break
        d = 0.25 * (d[0::2, 0::2] + d[1::2, 0::2] + d[0::2, 1::2] + d[1::2, 1::2])
        bc = 0.25 * (bc[0::2, 0::2] + bc[1::2, 0::2] + bc[0::2, 1::2] + bc[1::2, 1::2])
    return {"graph_vs_bc_mean_pct_mip0_8": out, "max_abs_pct": round(max(abs(x) for x in out), 3),
            "mean_level_diff_mip0_8": lev, "max_level_diff": max(lev),
            "note": "a near-black part's BC is a few 8-bit levels: 1 % there is a fraction of one level"}


# =========================================================================== painters
def paint_leaf(loc: np.ndarray, grain_deg: float, seed: int = 11):
    """loc (M, 2): flat-leaf mm.  Returns (alb_factor, rough, spec, hgt_mm) for those texels."""
    g = math.radians(grain_deg)
    ux, uy = math.cos(g), math.sin(g)
    a = loc[:, 0] * ux + loc[:, 1] * uy            # along the warp
    b = -loc[:, 0] * uy + loc[:, 1] * ux           # across it (the weft direction)
    warp = fbm1(b * 2.2, seed, 4) + 0.35 * vnoise1(b * 9.0, seed + 3)            # slubs 0.1 - 1 mm across
    warp *= 0.6 + 0.4 * (0.5 + fbm1(a * 0.05, seed + 5, 2))                        # varying along
    weft = fbm1(a * 1.7, seed + 7, 3)
    mott = fbm2(loc[:, 0] * 0.045, loc[:, 1] * 0.045, seed + 9, 3)
    # cockling: the soft undulation of glued silk (features 3 - 12 mm, elongated along the warp)
    cock = fbm2(a * 0.10, b * 0.22, seed + 13, 3)
    # the weave's fine ripple (0.3 - 0.6 mm), broken so it never reads as a regular pattern
    rip = vnoise2(a * 2.4, b * 3.1, seed + 15) * (0.6 + 0.4 * (0.5 + fbm1(a * 0.2, seed + 17, 2)))
    f = 1.0 + 0.070 * warp + 0.035 * weft + 0.050 * mott
    # round 3: NO cockling relief (the measurer: invented, fan2 resolves none) - the faces are flat silk facets; the
    # weave's own relief is stronger so a fine silk grain survives the mips (0.3 - 1 mm features, 2 - 5 texels)
    rough = 0.60 + 0.06 * warp - 0.04 * mott
    spec = 0.50 + 0.12 * warp
    hgt = 0.014 * (warp + 0.5 * weft) + 0.010 * rip
    del cock
    return f, rough, spec, hgt


def paint_stick(loc: np.ndarray, kind: np.ndarray, stick: np.ndarray, seed: int = 23, half_width=None,
                rounded: Optional[np.ndarray] = None, edge_band_mm: float = 0.9, edge_drop_mm: float = 0.30):
    """loc (M, 2): the stick's own frame (x along it) for faces, (perimeter, z) for walls.

    ``half_width(x)`` (mm) and ``rounded`` (per texel: an inner rib's face) give each rib's rounded long
    edges in the height (so in the normal map): RS 4's 2 - 3 px dark boundary between neighbouring ribs is
    their edges turning away from the light; the plates' own walls are only 0.37 mm tall."""
    x = loc[:, 0]
    y = loc[:, 1]
    s = stick.astype(np.float64)
    along = np.where(kind == 2, loc[:, 0], x)                                     # walls: along the perimeter
    across = np.where(kind == 2, loc[:, 1] * 4.0, y)
    fib = fbm1(across * 3.1 + s * 13.7, seed, 4) * (0.7 + 0.3 * (0.5 + fbm1(along * 0.08 + s, seed + 2, 2)))
    fine = vnoise1(across * 11.0 + s * 3.3, seed + 4)
    lac = fbm2(along * 0.03 + s * 5.1, across * 0.3, seed + 6, 2)
    # each stick its own tone (bamboo from different culms) and its own lacquer sheen
    tone = hash01(stick.astype(np.int64), seed=seed + 8) - 0.5
    # round 3 (craft review: the sticks read as smooth extruded plastic): lacquered BAMBOO long grain - the vascular
    # bundles as fine streaks along the stick (0.1 - 0.4 mm apart) in the albedo, the gloss and the relief, each stick
    # its own tone and sheen.  No nodes: fan2 shows none on the ribs
    bundles = vnoise1(across * 7.3 + s * 5.9, seed + 11) * (0.75 + 0.25 * vnoise1(along * 0.6 + s * 2.1, seed + 12))
    f = 1.0 + 0.10 * fib + 0.05 * fine + 0.08 * bundles + 0.03 * lac + 0.16 * tone
    rough = 0.30 + 0.05 * fib + 0.04 * bundles + 0.02 * lac + 0.06 * (hash01(stick.astype(np.int64), seed=seed + 9) - 0.5)
    spec = 0.50 + 0.06 * fib + 0.04 * bundles
    hgt = 0.010 * (fib + 0.4 * fine) + 0.008 * bundles
    if half_width is not None and rounded is not None:
        d = np.maximum(half_width(x) - np.abs(y), 0.0)
        u = np.clip(d / edge_band_mm, 0.0, 1.0)
        prof = 1.0 - (1.0 - u) ** 2                                                  # a quarter-round
        # each rib's own set: a slight twist across it (+- 4 deg), so neighbouring ribs catch the light apart
        tilt = 0.070 * (2.0 * hash01(stick.astype(np.int64), seed=seed + 10) - 1.0)
        hgt = hgt + np.where(rounded, -edge_drop_mm * (1.0 - prof) + tilt * y, 0.0)
    return f, rough, spec, hgt


def paint_rivet(loc: np.ndarray, kind: Optional[np.ndarray] = None, seed: int = 31):
    """kind 4 = the heads' blind recess (fan2's dark eyelet centre): dull and dark"""
    f = 1.0 + 0.02 * fbm2(loc[:, 0] * 2.0, loc[:, 1] * 2.0, seed, 3)
    rough = 0.07 + 0.02 * fbm2(loc[:, 0] * 3.0, loc[:, 1] * 3.0, seed + 1, 2)   # round 3: mirror-polished (fan2's glint)
    if kind is not None:
        rec = kind == 4
        f = np.where(rec, 0.05, f)
        rough = np.where(rec, 0.30, rough)
    return f, rough, np.full(len(loc), 0.5), np.zeros(len(loc))


def paint_tassel(loc: np.ndarray, kind: np.ndarray, seed: int = 41):
    """loc (M, 2): (around-the-strand mm, along-the-strand mm).  kind: 0 cord, 1 knot, 2 neck, 3 skirt."""
    u, v = loc[:, 0], loc[:, 1]
    strands = fbm1(u * 3.3, seed, 4) + 0.6 * vnoise1(u * 12.0, seed + 1) + 0.4 * vnoise1(u * 24.0, seed + 5)
    strands = strands * (0.8 + 0.2 * (0.5 + fbm1(v * 0.2, seed + 2, 2)))
    twist = vnoise1((u + v * 1.4) * 2.6, seed + 3)                   # a twisted cord's plies
    knot = vnoise2(u * 1.2, v * 1.2, seed + 4)
    f = np.where(kind == 3, 1.0 + 0.26 * strands,
                 np.where(kind == 0, 1.0 + 0.10 * twist, np.where(kind == 1, 1.0 + 0.12 * knot + 0.06 * strands,
                                                                   1.0 + 0.08 * twist)))
    rough = np.where(kind == 3, 0.55 + 0.06 * strands, 0.6)
    spec = np.where(kind == 3, 0.5 + 0.12 * strands, 0.45)
    hgt = np.where(kind == 3, 0.06 * strands, np.where(kind == 0, 0.05 * twist, 0.05 * knot))
    return f, rough, spec, hgt


__all__ = ["rasterise", "dilate", "finish", "detail16", "mip_parity", "paint_leaf", "paint_stick", "paint_rivet",
           "paint_tassel", "srgb_encode", "srgb_decode", "LUMA", "fbm1", "fbm2"]
