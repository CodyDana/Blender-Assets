#!/usr/bin/env python
"""props_lib.blackhat_paint - SM_BlackHat's surfaces, painted texel by texel in strand / tape space.

numpy only.  For every texel the atlas's inverse map gives the owning member's LOCAL
coordinates (mm), and from them the part's own parameters: a skin texel knows its slant s and
azimuth theta (so a circumferential strand is a row of constant s that runs on under the ribs
into the next bay); a rib texel its position along the rod and round it (the rope twist); a
lashing texel its place on the loop and across the three cords; a cloth texel its place along
the band / tail and across it.  Nothing is projected and nothing reads the reference: the
numbers are REFERENCE_SPEC's (weave pitch, strand width, seam spacing, wear zones and cover,
fleck albedo, the dark smudge, the rim scuffs, cloth albedo).

Channels (float, linear): alb (albedo luminance; the hue is the slot's Tint), rough, spec (the
specular mask: Specular = SPEC_SCALE[part] x spec, blackhat_look), ao (analytic cavities; the
Cycles bake multiplies in later), hgt (mm, for the normal map).

Final pass (engineering, 2026-09-26): roughness floors so no straw texel is near-mirror (round 1
reached 0.05: the cap and ribs read metallic and the ribs' highlights crawled), matte cloth
(roughness 0.85 - 0.95, Specular 0.25 - 0.35), the inner skin's weave faded into a plain seat disc
at the apex (the strands converged to sub-texel size and swirled), and the recolour convention
changed so the Tint IS the part's mean colour (finish()).
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np

from .blackhat_atlas import Atlas
from .blackhat_geom import COS_A, D2R, MeshBuilder, Member, band_section, wrap_profile

LUMA = np.array([0.2126, 0.7152, 0.0722])


# =========================================================================== noise
def _mix(h):
    h = (h ^ (h >> np.uint64(33))) * np.uint64(0xff51afd7ed558ccd)
    h = (h ^ (h >> np.uint64(33))) * np.uint64(0xc4ceb9fe1a85ec53)
    return h ^ (h >> np.uint64(33))


def hash01(*keys, seed=0):
    h = np.uint64(0x9E3779B97F4A7C15) * np.uint64((int(seed) + 1) % (1 << 63))
    out = None
    for k in keys:
        k = np.asarray(k).astype(np.int64).astype(np.uint64)
        out = _mix((h if out is None else out) ^ (k * np.uint64(0x9E3779B97F4A7C15) + np.uint64(0x632BE59BD9B4E019)))
    return (out >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def vnoise1(x, seed=0):
    i = np.floor(x)
    f = x - i
    f = f * f * (3 - 2 * f)
    return (1 - f) * hash01(i, seed=seed) + f * hash01(i + 1, seed=seed)


def vnoise2(x, y, seed=0):
    i, j = np.floor(x), np.floor(y)
    fx, fy = x - i, y - j
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    a = hash01(i, j, seed=seed)
    b = hash01(i + 1, j, seed=seed)
    c = hash01(i, j + 1, seed=seed)
    d = hash01(i + 1, j + 1, seed=seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm2(x, y, seed=0, octaves=3):
    s, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + amp * vnoise2(x * 2 ** o, y * 2 ** o, seed=seed + 17 * o)
        tot += amp
        amp *= 0.5
    return s / tot


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def line(d, half, aa):
    """1 on a line of half-width ``half`` (mm), anti-aliased over ``aa`` mm."""
    return 1.0 - smooth(half, half + aa, np.abs(d))


# =========================================================================== owners
def domain_distance(m: Member, x, y):
    """Signed distance (mm, <= 0 inside) of local points to the member's domain."""
    if m.kind == "wedge":
        yt = y * m.flip
        s = np.hypot(x, yt)
        th = m.info["theta_mid"] + np.arctan2(yt, x) / (D2R * COS_A)
        k = D2R * COS_A * np.maximum(s, 1.0)
        return np.maximum.reduce([m.info["s0"] - s, s - m.info["s1"], (m.info["theta_a"] - th) * k,
                                  (th - m.info["theta_b"]) * k])
    if m.kind == "disc":
        return np.hypot(x, y) - float(max(np.abs(m.lo).max(), np.abs(m.hi).max()))
    return np.maximum.reduce([m.lo[0] - x, x - m.hi[0], m.lo[1] - y, y - m.hi[1]])


def owners(mb: MeshBuilder, at: Atlas):
    """-> owner index map (-1 none), local x / y maps, the member list, texel mm per member."""
    n = at.size
    own = np.full((n, n), -1, np.int32)
    best = np.full((n, n), np.inf, np.float32)
    lx = np.zeros((n, n), np.float32)
    ly = np.zeros((n, n), np.float32)
    keys = [k for k, m in mb.members.items() if m.atlas == at.name]
    for idx, key in enumerate(keys):
        m = mb.members[key]
        pl = at.place[key]
        if m.kind in ("wedge", "disc"):
            from .blackhat_atlas import _wedge_outline
            c = _wedge_outline(m)
            if m.kind == "wedge":
                c = c * np.array([1.0, m.flip])
        else:
            c = np.array([[m.lo[0], m.lo[1]], [m.hi[0], m.lo[1]], [m.hi[0], m.hi[1]], [m.lo[0], m.hi[1]]])
        uv = pl.uv_px(c)
        u0 = int(max(0, math.floor(uv[:, 0].min()) - at.pad - 1))
        u1 = int(min(n, math.ceil(uv[:, 0].max()) + at.pad + 1))
        v0 = int(max(0, math.floor(uv[:, 1].min()) - at.pad - 1))
        v1 = int(min(n, math.ceil(uv[:, 1].max()) + at.pad + 1))
        if u1 <= u0 or v1 <= v0:
            continue
        U, V = np.meshgrid(np.arange(u0, u1) + 0.5, np.arange(v0, v1) + 0.5)
        L = pl.local(np.stack([U, V], -1))
        d = domain_distance(m, L[..., 0], L[..., 1])
        scale = abs(np.linalg.det(pl.A)) ** 0.5            # px per mm for this member
        dpx = (d * scale).astype(np.float32)
        rows = n - 1 - np.arange(v0, v1)                    # image rows (top-down)
        sl = (slice(rows[-1], rows[0] + 1), slice(u0, u1))
        dpx, Lx, Ly = dpx[::-1], L[::-1, :, 0], L[::-1, :, 1]
        cur = best[sl]
        upd = (dpx < cur) & (dpx <= at.pad)
        cur[upd] = dpx[upd]
        own[sl][upd] = idx
        lx[sl][upd] = Lx[upd]
        ly[sl][upd] = Ly[upd]
    return own, lx, ly, keys, best


# =========================================================================== the straw
#: REFERENCE_SPEC 9: straw albedo lum 0.042 (the field); flecks 0.10 (0.08 - 0.20); wear cover 15 %
STRAW_BASE = 0.054
FLECK_ALB = (0.09, 0.22)
COURSE_MM = 0.031 * 300.0          # REFERENCE_SPEC 5 (0.031 R)
STRAND_MM = 0.006 * 300.0          # 0.006 R
STRANDS_PER_COURSE = 5
SEAM_DEG = (3.0, 8.0)              # fine radial seams, irregular 3 - 8 deg (texture only)


def wear_cover(theta, rho, outer=True):
    """Fraction of straw showing light worn strand tops, by zone (REFERENCE_SPEC 9)."""
    th = (np.asarray(theta) + 180.0) % 360.0 - 180.0
    c = np.full(np.shape(th), 0.10)                        # far side / elsewhere (DESIGNED 10 %)
    c = np.where((th > -95) & (th < 95), 0.11, c)
    c = np.where((th > 72) & (th < 95), 0.18, c)
    c = np.where((th > -5) & (th < 16), 0.07, c)
    streak = (th > -18) & (th < -5)
    c = np.where(streak, np.where((rho > 0.70) & (rho < 0.82), 0.16, 0.12), c)
    c = np.where((th > -30) & (th < -18), 0.20, c)
    left = (th > -62) & (th < -25) & (rho > 0.45)
    c = np.where(left, 0.30, c)
    # soft edges between zones
    c = np.where(rho < 0.40, c * 0.6, c)
    return c if outer else np.zeros_like(c)


def paint_skin(m: Member, x, y, ts, seed):
    yt = y * m.flip
    s = np.hypot(x, yt)
    th = m.info["theta_mid"] + np.arctan2(yt, x) / (D2R * COS_A)
    outer = m.info["surface"] == "outer"
    r = s * COS_A
    rho = r / 300.0
    a = th * D2R * r                                     # arc length along the strands (mm)
    aa = max(ts, 0.08)
    # courses, strands
    c = np.floor(s / COURSE_MM)
    fs = s / COURSE_MM - c
    ks = np.floor(fs * STRANDS_PER_COURSE)
    fk = fs * STRANDS_PER_COURSE - ks
    w = COURSE_MM / STRANDS_PER_COURSE
    d_edge = np.minimum(fk, 1 - fk) * w
    gap = line(d_edge, 0.20, aa)
    d_course = np.minimum(fs, 1 - fs) * COURSE_MM
    cline = line(d_course, 0.22, aa) * (0.55 + 0.45 * vnoise1(th * 1.3 + c * 7.1, seed=seed + 13))
    # radial seams: irregular 3-8 deg, a fresh set per course (brick-like runs)
    seam_d = np.full(np.shape(s), 99.0)
    cell = np.zeros(np.shape(s))
    for ci in np.unique(c):
        sel = c == ci
        rng = np.random.default_rng(int(ci) * 7919 + seed * 31 + 5)
        widths = rng.uniform(*SEAM_DEG, size=160)
        edges = rng.uniform(0, SEAM_DEG[0]) - 190.0 + np.concatenate([[0.0], np.cumsum(widths)])
        t = (th[sel] + 180.0) % 360.0 - 180.0
        # about half the seams are faint: the runs read long, as in the reference
        faint = rng.uniform(size=len(edges)) < 0.5
        k = np.clip(np.searchsorted(edges, t), 1, len(edges) - 1)
        dl, dr = t - edges[k - 1], edges[k] - t
        near = np.where(dl < dr, k - 1, k)
        seam_d[sel] = np.minimum(dl, dr) * D2R * r[sel] + faint[near] * 0.25
        cell[sel] = k
    seam = line(seam_d, 0.11, aa)
    # tone: per strand run, streaky along the strand, broad mottling
    run = hash01(c, ks, cell, seed=seed)
    tone = 0.45 + 1.10 * run ** 1.5
    tone *= 0.75 + 0.50 * vnoise1(a / 9.0 + 37.0 * hash01(c, ks, seed=seed + 1), seed=seed + 2)
    tone *= 0.86 + 0.28 * fbm2(a / 70.0, s / 55.0, seed=seed + 3)
    # strand relief (flat strands, slightly domed)
    dome = np.sqrt(np.clip(np.sin(math.pi * fk), 0, 1))
    alb = STRAW_BASE * tone * (0.78 + 0.22 * dome)
    alb *= (1 - 0.60 * gap) * (1 - 0.32 * cline) * (1 - 0.30 * seam)
    # each course is a slightly domed woven band: at grazing views the courses read as bands (the
    # reference's right side), the single strands only head-on
    cdome = np.clip(np.sin(math.pi * fs), 0, 1) ** 0.7
    alb *= 0.86 + 0.28 * hash01(c, np.floor(th / 40.0), seed=seed + 15)
    hgt = 0.06 * dome - 0.08 * gap + 0.30 * cdome - 0.16 * cline - 0.12 * seam
    spec = (0.55 + 0.45 * dome) * (1 - 0.7 * gap) * (1 - 0.5 * cline) * (1 - 0.5 * seam)
    rough = 0.24 + 0.13 * hash01(c, ks, cell, seed=seed + 4) + 0.30 * (gap + cline + seam) + 0.10 * (1 - dome)
    ao = 1.0 - 0.25 * gap - 0.35 * cline - 0.35 * seam
    # the worn zones read as broadly lighter strand tops as well as streaks (REFERENCE_SPEC 9: the
    # left zone's mean is ~2x the front's at similar light)
    if outer:
        tn = (th + 180.0) % 360.0 - 180.0
        zone = (smooth(-66, -58, tn) * (1 - smooth(-27, -21, tn)) * smooth(0.40, 0.50, rho)
                + 0.5 * smooth(-32, -26, tn) * (1 - smooth(-8, -3, tn)) * smooth(0.55, 0.68, rho)
                + 0.45 * smooth(68, 74, tn) * (1 - smooth(93, 98, tn)))
        zone = np.clip(zone, 0, 1) * (0.6 + 0.8 * fbm2(a / 60.0, s / 45.0, seed=seed + 14))
        alb *= 1.0 + 0.45 * zone * dome
        # the handled, worn zone is also polished: glossier strand tops (the reference's sheen)
        spec = spec * (1.0 + 0.5 * zone * dome)
        rough = rough - 0.05 * zone
    # the one darker smudge (theta -45..-35, rho 0.55 - 0.90): the reference's darkest worn-zone band
    if outer:
        tn = (th + 180.0) % 360.0 - 180.0
        # irregular edges: the window's azimuths wander with the slant, and the patch is mottled
        jit = 3.0 * (fbm2(s / 30.0, 3.7, seed=seed + 16) - 0.5)
        sm = (smooth(-42.5, -37.0, tn + jit) * (1 - smooth(-33.5, -29.0, tn - jit))
              * smooth(0.48, 0.60, rho) * (1 - smooth(0.86, 0.96, rho)))
        sm = np.clip(sm * (0.55 + 0.9 * fbm2(a / 18.0, s / 14.0, seed=seed + 12, octaves=4)), 0, 1)
    else:
        sm = np.zeros_like(s)
    # wear: light strand tops in short streaks ALONG the strands (not holes)
    cov = wear_cover(th, rho, outer) * (1 - 0.85 * sm)
    patch = fbm2(a / 45.0, s / 40.0, seed=seed + 9, octaves=3)
    # a streak fills ~1/3 of its cell (tapered ends, the strand's top only): x 3 so the visible cover
    # is the zone's
    cov_l = np.clip(3.0 * cov * (2.2 * patch ** 2), 0.0, 0.95)
    Ls = 4.0 + 14.0 * hash01(c, ks, seed=seed + 5)            # streak cells 4 - 18 mm along the strand
    q = np.floor(a / Ls + hash01(c, ks, seed=seed + 6) * 7.0)
    fq = a / Ls + hash01(c, ks, seed=seed + 6) * 7.0 - q
    on = hash01(c, ks, q, seed=seed + 7) < cov_l
    along = smooth(0.0, 0.25, fq) * (1 - smooth(0.6, 1.0, fq))
    across = smooth(0.12, 0.35, fk) * (1 - smooth(0.65, 0.88, fk))
    fl = on * along * across * (1 - seam)
    fa = FLECK_ALB[0] + (FLECK_ALB[1] - FLECK_ALB[0]) * hash01(c, ks, q, seed=seed + 8) ** 2
    alb = alb * (1 - fl) + fa * fl
    spec = spec * (1 - 0.2 * fl)
    rough = rough + 0.10 * fl
    # the one darker smudge (theta -45..-35, rho 0.55 - 0.90, ~15 % darker)
    if outer:
        # a dull, dirty patch: darker AND less glossy (the reference's smudge is dark under the sheen)
        alb *= 1 - 0.50 * sm
        spec = spec * (1 - 0.75 * sm)
        rough = rough + 0.35 * sm
    else:
        alb *= 0.95
        # the inner skin fades into a plain seat disc at the apex (rho < ~0.1): toward the apex the
        # strands converge below a texel and swirled in round 1's underside view
        f = smooth(0.05, 0.13, rho)
        alb = STRAW_BASE * 0.70 + (alb - STRAW_BASE * 0.70) * f
        hgt = hgt * f
        spec = 0.55 + (spec - 0.55) * f
        rough = 0.55 + (rough - 0.55) * f
        ao = 1.0 + (ao - 1.0) * f
    return {"alb": alb, "rough": rough, "spec": spec, "ao": ao, "hgt": hgt}


def _rope(x, y, r, pitch, plies, aa):
    """Twisted cord: ply parameter f in [0, 1) across each ply, and the groove line."""
    ang = y / max(r, 1e-6)
    ph = (ang / (2 * math.pi) - x / pitch) * plies
    f = ph - np.floor(ph)
    groove = line(np.minimum(f, 1 - f) * (2 * math.pi * r / plies), 0.10, aa)
    return f, groove


def paint_rib(m: Member, x, y, ts, seed):
    r = m.info["r"]
    aa = max(ts, 0.08)
    f, groove = _rope(x, y, r, 1.6 * 2 * r, 2, aa)
    dome = np.sqrt(np.clip(np.sin(math.pi * f), 0, 1))
    k = int(round(m.info["theta"] * 10))
    tone = 0.85 + 0.3 * vnoise1(x / 6.0, seed=seed + k)
    alb = STRAW_BASE * 1.45 * tone * (0.75 + 0.25 * dome) * (1 - 0.6 * groove)
    top = np.cos(y / r - math.pi) * -1.0                    # +1 on the top of the rod
    cov = 0.18 * np.clip(top, 0, 1) * (0.5 + fbm2(x / 30.0, k, seed=seed + 1))
    fl = (hash01(np.floor(x / 4.0), np.floor(f * 2 + y / r), k, seed=seed + 2) < cov) * (1 - groove)
    alb = alb * (1 - fl) + 0.11 * fl
    # rougher than round 1 (0.30): a highlight spreads along the rod instead of breaking into
    # bright dashes that crawl as the view turns
    return {"alb": alb, "rough": 0.58 + 0.15 * groove + 0.1 * fl, "spec": (0.6 + 0.4 * dome) * (1 - 0.7 * groove),
            "ao": 1 - 0.35 * groove, "hgt": 0.18 * dome - 0.15 * groove}


def rim_scuff_thetas():
    """The front rim's light scuffs (REFERENCE_SPEC 9: image x 280 - 330 and 360 - 380 on the
    front face), as azimuths (from the reference camera model, rounded)."""
    return ((-9.5, -2.5), (1.5, 4.5))


def paint_tube(m: Member, x, y, ts, seed, cord=False):
    Rc, rt = m.info["Rc"], m.info["rt"]
    th = m.info["theta_a"] + x / (Rc * D2R)
    a = m.info["a0"] + y / rt / D2R                          # section angle (deg), 0 = outward
    aa = max(ts, 0.08)
    if cord:
        f, groove = _rope(x, y, rt, 3.2, 2, aa)
        dome = np.sqrt(np.clip(np.sin(math.pi * f), 0, 1))
        alb = STRAW_BASE * 0.55 * (0.8 + 0.2 * dome) * (1 - 0.5 * groove) * (0.85 + 0.3 * vnoise1(x / 8.0, seed=seed))
        return {"alb": alb, "rough": 0.55 + 0.2 * groove, "spec": 0.35 * (0.6 + 0.4 * dome) * (1 - 0.6 * groove),
                "ao": 0.7 - 0.3 * groove, "hgt": 0.06 * dome - 0.05 * groove}
    # split cane rolled round the rim: long fibres along the rim
    fib_w = 0.9
    fi = np.floor(y / fib_w)
    ff = y / fib_w - fi
    fline = line(np.minimum(ff, 1 - ff) * fib_w, 0.07, aa)
    tone = (0.82 + 0.36 * hash01(fi, np.floor(x / 40.0 + hash01(fi, seed=seed) * 3), seed=seed + 1))
    tone *= 0.85 + 0.3 * vnoise1(x / 14.0 + 11.0 * hash01(fi, seed=seed + 2), seed=seed + 3)
    alb = STRAW_BASE * 0.72 * tone * (1 - 0.45 * fline)
    # wear: flecks along the fibres, and the scuffs on the front face
    cov = 0.06 * (0.3 + 1.4 * fbm2(x / 40.0, y / 10.0, seed=seed + 4))
    q = np.floor(x / (2.0 + 6.0 * hash01(fi, seed=seed + 5)))
    fl = (hash01(fi, q, seed=seed + 6) < cov) * (1 - fline)
    thn = (th + 180.0) % 360.0 - 180.0
    face = smooth(-75, -35, ((a + 180.0) % 360.0) - 180.0) * (1 - smooth(25, 60, ((a + 180.0) % 360.0) - 180.0))
    sc = np.zeros_like(x)
    for lo, hi in rim_scuff_thetas():
        sc = np.maximum(sc, smooth(lo - 1.0, lo + 0.5, thn) * (1 - smooth(hi - 0.5, hi + 1.0, thn)))
    scuff = sc * face * (fbm2(x / 3.0, y / 2.0, seed=seed + 7) > 0.60)
    fl = np.maximum(fl, scuff * 0.9)
    alb = alb * (1 - fl) + (0.09 + 0.07 * hash01(fi, q, seed=seed + 8)) * fl
    return {"alb": alb, "rough": 0.52 + 0.12 * fline + 0.15 * fl, "spec": (1 - 0.4 * fline) * (1 - 0.3 * fl),
            "ao": 1 - 0.2 * fline, "hgt": -0.06 * fline}


def paint_lashing(m: Member, x, y, ts, seed, rw):
    aa = max(ts, 0.08)
    prof, _pn, seg = wrap_profile("wraps", rw)
    # the three cords across y: edges at seg[1], valleys seg[3], seg[5], edge seg[7]
    b = [seg[1], seg[3], seg[5], seg[7]]
    k = np.clip(np.searchsorted(np.array(b), y) - 1, 0, 2)
    y0 = np.array(b)[k]
    y1 = np.array(b)[k + 1]
    fy = np.clip((y - y0) / (y1 - y0), 0, 1)
    # twisted cord: diagonal ply lines
    f, groove = _rope(x, (y - y0) * 1.0, rw, 3.0, 3, aa)
    dome = np.sqrt(np.clip(np.sin(math.pi * fy), 0, 1))
    valley = 1 - smooth(0.0, 0.22, np.minimum(fy, 1 - fy))
    kk = int(round(m.info["theta"] * 10))
    tone = 0.85 + 0.3 * vnoise1(x / 7.0 + k * 13.0, seed=seed + kk)
    alb = STRAW_BASE * 1.55 * tone * (0.7 + 0.3 * dome) * (1 - 0.4 * groove) * (1 - 0.75 * valley)
    fl = (hash01(np.floor(x / 3.0), k, kk, seed=seed + 3) < 0.10) * dome
    alb = alb * (1 - fl) + 0.10 * fl
    return {"alb": alb, "rough": 0.52 + 0.15 * groove, "spec": (0.5 + 0.5 * dome) * (1 - 0.5 * groove) * (1 - 0.6 * valley),
            "ao": 1 - 0.25 * groove - 0.5 * valley, "hgt": 0.12 * dome - 0.08 * groove - 0.15 * valley}


def paint_cap(m: Member, x, y, ts, seed, rib_thetas, lip=False):
    aa = max(ts, 0.08)
    if lip:
        return paint_tube(Member("x", "straw", "rect", {"Rc": m.info["rc"], "rt": 2.0, "theta_a": 180.0, "a0": 0.0}),
                          x, y, ts, seed + 50)
    s = np.hypot(x, y)
    Rs = m.info["Rs"]
    phi = m.info["theta0"] + 180.0 + np.arctan2(y, x) / D2R
    r = Rs * np.sin(np.clip(s / Rs, 0, 1.5))
    # concentric strands and the lid's faint radial ribs (the 13 ribs carried over the lid)
    ci = np.floor(s / 1.6)
    fs = s / 1.6 - ci
    gap = line(np.minimum(fs, 1 - fs) * 1.6, 0.1, aa)
    rl = np.zeros_like(s)
    for t in rib_thetas:
        d = ((phi - t + 180.0) % 360.0 - 180.0) * D2R * np.maximum(r, 0.5)
        rl = np.maximum(rl, line(d, 0.55, aa) * smooth(1.5, 4.0, r))
    tone = 0.82 + 0.36 * hash01(ci, np.floor(phi / 9.0), seed=seed)
    alb = STRAW_BASE * 1.5 * tone * (1 - 0.4 * gap) * (1 + 1.6 * rl)
    fl = (hash01(ci, np.floor(phi / 4.0), seed=seed + 1) < 0.18) * (1 - gap)
    alb = alb * (1 - fl) + 0.10 * fl
    return {"alb": alb, "rough": 0.58 + 0.1 * gap - 0.05 * rl, "spec": 0.8 - 0.4 * gap, "ao": 1 - 0.3 * gap,
            "hgt": -0.08 * gap + 0.25 * rl}


# =========================================================================== the cloth
#: REFERENCE_SPEC 9: cloth lum 0.030 (band and tails), neutral, matte
CLOTH_BASE = 0.026


def _weave(x, y, ts, seed):
    """A fine plain weave (0.45 mm threads) with slub and mottling."""
    aa = max(ts, 0.05)
    p = 0.45
    fx, fy = x / p, y / p
    ix, iy = np.floor(fx), np.floor(fy)
    over = ((ix + iy) % 2) == 0
    ux, uy = fx - ix, fy - iy
    warp = np.sqrt(np.clip(np.sin(math.pi * uy), 0, 1))
    weft = np.sqrt(np.clip(np.sin(math.pi * ux), 0, 1))
    h = np.where(over, warp, weft)
    slub = 0.9 + 0.2 * vnoise1(x / 3.0 + 17 * hash01(iy, seed=seed), seed=seed + 1)
    return h, slub


def paint_cloth(m: Member, x, y, ts, seed, hat=None):
    part = m.info["part"]
    h, slub = _weave(x, y, ts, seed)
    mott = 0.62 + 0.76 * fbm2(x / 38.0, y / 22.0, seed=seed + 2, octaves=4)
    alb = CLOTH_BASE * 1.35 * mott * slub * (0.12 + 0.88 * h)
    # matte cloth (final pass): roughness 0.85 - 0.95 and a specular mask of 0.5 - 0.7, which at
    # SPEC_SCALE cloth 0.5 is Unreal Specular 0.25 - 0.35 (F0 0.020 - 0.028); round 1's 0.35 - 0.90 at
    # scale 1.0 gave the tails a satin / patent sheen
    rough = 0.86 + 0.05 * (1 - h)
    spec = 0.50 + 0.20 * h
    ao = 0.9 + 0.1 * h
    hgt = 0.05 * h
    dust = np.zeros_like(x)
    if part == "band":
        # the twisted roll carries diagonal twist lines where it is rolled (REFERENCE_SPEC 7)
        tp = m.info["theta0"] + (m.info["theta1"] - m.info["theta0"]) * np.clip(
            x / max(m.hi[0], 1e-6), 0, 1)
        q = np.clip((0.040 * 300 - band_section(hat, tp)[0]) / ((0.040 - 0.016) * 300), 0, 1)
        tw = (x * 0.7 + y) / 4.0
        twl = line((tw - np.floor(tw) - 0.5) * 4.0, 0.35, 0.3) * q
        alb *= (1 + 0.55 * q) * (1 - 0.45 * twl)
        rough = rough - 0.02 * q
        hgt = hgt - 0.25 * twl
        ao = ao * (1 - 0.3 * twl)
        dust = 0.25 * (fbm2(x / 20.0, y / 6.0, seed=seed + 5) > 0.62)
    elif part in ("tail", "tail_wall"):
        # tails: dusty lighter patches (the reference's greyer tail faces), worn edges
        dust = 0.6 * smooth(0.52, 0.72, fbm2(x / 30.0, y / 12.0, seed=seed + 6, octaves=4))
        if part == "tail":
            L = m.info["length"]
            # fraying toward the tear: lighter fibres near the end
            dust = np.maximum(dust, 0.5 * smooth(L - 90.0, L - 10.0, x) * (fbm2(x / 3.0, y / 1.5, seed=seed + 7) > 0.5))
    elif part == "knot":
        dust = 0.3 * smooth(0.55, 0.75, fbm2(x / 10.0, y / 10.0, seed=seed + 8))
    alb = alb * (1 + 1.6 * dust)
    rough = rough + 0.04 * dust
    return {"alb": alb, "rough": rough, "spec": spec, "ao": ao, "hgt": hgt}


# =========================================================================== the atlas
def paint_atlas(mb: MeshBuilder, at: Atlas, seed: int = 7, hat=None, log=print) -> Dict[str, np.ndarray]:
    own, lx, ly, keys, dist = owners(mb, at)
    n = at.size
    ch = {k: np.zeros((n, n), np.float32) for k in ("alb", "rough", "spec", "ao", "hgt")}
    written = own >= 0
    flat = own.ravel()
    order = np.argsort(flat, kind="stable")
    counts = np.bincount(flat[flat >= 0], minlength=len(keys))
    start = int(np.sum(flat < 0))
    rib_thetas = sorted({mb.members[k].info["theta"] for k in keys if mb.members[k].info.get("part") == "rib"})
    for idx, key in enumerate(keys):
        cnt = int(counts[idx])
        if cnt == 0:
            continue
        sel = order[start:start + cnt]
        start += cnt
        m = mb.members[key]
        x = lx.ravel()[sel].astype(np.float64)
        y = ly.ravel()[sel].astype(np.float64)
        pl = at.place[key]
        ts = 1.0 / (abs(np.linalg.det(pl.A)) ** 0.5)          # mm per texel
        part = m.info.get("part")
        if m.kind != "wedge":
            y = y * m.flip                                     # the part's own (unflipped) local y
        if m.kind == "wedge":
            out = paint_skin(m, x, y, ts, seed)
        elif m.kind == "disc":
            out = paint_cap(m, x, y, ts, seed + 40, rib_thetas)
        elif part == "rib":
            out = paint_rib(m, x, y, ts, seed + 10)
        elif part == "tube":
            out = paint_tube(m, x, y, ts, seed + 20)
        elif part == "cord":
            out = paint_tube(m, x, y, ts, seed + 25, cord=True)
        elif part == "lashing":
            out = paint_lashing(m, x, y, ts, seed + 30, m.info["rw"])
        elif part == "cap_lip":
            out = paint_cap(m, x, y, ts, seed + 45, rib_thetas, lip=True)
        else:
            out = paint_cloth(m, x, y, ts, seed + 60 + (idx % 7), hat=hat)
        for k in ch:
            ch[k].ravel()[sel] = np.asarray(out[k], np.float64) * np.ones(len(sel))
    ch["written"] = written
    ch["own"] = own
    ch["keys"] = keys
    # per-texel px per mm (for the normal map's slopes)
    scale = np.zeros(len(keys) + 1, np.float32)
    for idx, key in enumerate(keys):
        scale[idx] = abs(np.linalg.det(at.place[key].A)) ** 0.5
    ch["px_per_mm"] = scale[np.where(own >= 0, own, len(keys))]
    log(f"  painted {at.name}: {int(written.sum())} texels ({written.mean():.3f} of the atlas), {len(keys)} members")
    return ch


# =========================================================================== maps
def srgb_encode(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def srgb_decode(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def normal_dx(ch) -> np.ndarray:
    """Tangent-space normal (DirectX) from the height in mm.  Rows run top-down (V down); every
    member is placed by a rotation + uniform scale, so the texel grid IS the tangent frame; a
    slope across an owner boundary is set to 0."""
    h = ch["hgt"].astype(np.float64)
    own = ch["own"]
    k = ch["px_per_mm"].astype(np.float64)
    hu = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    hv_down = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    same_u = (np.roll(own, -1, 1) == own) & (np.roll(own, 1, 1) == own)
    same_v = (np.roll(own, -1, 0) == own) & (np.roll(own, 1, 0) == own)
    du = np.where(same_u, hu, 0.0) * k                          # dh/du (mm per mm)
    dv = -np.where(same_v, hv_down, 0.0) * k                    # dh/dv, v UP
    n = np.stack([-du, -dv, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[..., 1] *= -1.0                                           # DirectX: green = -Y
    n[~ch["written"]] = (0.0, 0.0, 1.0)
    return n


def finish(ch, chroma, lo_percentile=0.05, hi_percentile=99.95, rough_range=(0.0, 1.0)):
    """Float channels -> the shipped maps (8-bit), the detail and the default recolour parameters.

    Detail  sRGB-ENCODED LINEAR detail d, FULL RANGE at BOTH ends: d = (albedo - a_lo) / (a_hi - a_lo)
            (a_lo / a_hi the albedo at the lo / hi percentile of the written texels), quantised
            ONCE from float data.  Import sRGB ON: Unreal decodes before filtering, so a filtered
            sample is the average LINEAR d, and the affine map below commutes with the filter.
    Tint    the part's MEAN colour (linear): mean albedo x chroma / lum(chroma), the mean taken
            over the written texels of what the quantised Detail reproduces.  A buyer who sets Tint
            to a colour gets that colour as the part's average (and at the far mips).
    DetailBias, DetailScale  a_lo / lum(Tint), (a_hi - a_lo) / lum(Tint): mean(Bias + Scale x d) = 1.
    BC      sRGB8( Tint x (DetailBias + DetailScale x sRGBdecode(Detail8)) ) from the QUANTISED
            Detail and the ROUNDED sidecar numbers, so BC = the recolour graph at the default Tint
            to BC's own 8-bit rounding (source level; Unreal's BC1 compression of BC adds its own
            block error, the uncompressed G8 Detail does not)
    ORM     R AO, G roughness (clipped to ``rough_range``), B metallic 0, A the SPECULAR MASK
            (linear, Specular = SPEC_SCALE x ORM.A): a linear quantity, so mip-safe
    N       DirectX
    Texels outside every island take the median values so no mip ever pulls a foreign value in."""
    wr = ch["written"]
    alb = ch["alb"].astype(np.float64).copy()
    med = float(np.median(alb[wr]))
    alb[~wr] = med
    a_lo = float(np.percentile(alb[wr], lo_percentile))
    a_hi = float(np.percentile(alb[wr], hi_percentile))
    d = np.clip((alb - a_lo) / (a_hi - a_lo), 0.0, 1.0)
    D8 = np.rint(srgb_encode(d) * 255.0).astype(np.uint8)
    dq = srgb_decode(D8.astype(np.float64) / 255.0)
    mean_d = float(dq[wr].mean())
    mean_alb = a_lo + (a_hi - a_lo) * mean_d
    chroma = np.asarray(chroma, np.float64)
    tint = np.round(mean_alb * chroma / float(chroma @ LUMA), 6)
    t_l = float(tint @ LUMA)
    bias = round(a_lo / t_l, 6)
    scale = round((a_hi - a_lo) / t_l, 6)
    bc_lin = (bias + scale * dq)[..., None] * tint[None, None, :]
    BC8 = np.rint(srgb_encode(bc_lin) * 255.0).astype(np.uint8)
    ao = np.where(wr, ch["ao"], 1.0)
    rough = np.clip(np.where(wr, ch["rough"], float(np.median(ch["rough"][wr]))), *rough_range)
    spec = np.where(wr, ch["spec"], float(np.median(ch["spec"][wr])))
    orm = np.stack([ao, rough, np.zeros_like(ao), spec], -1)
    ORM8 = np.rint(np.clip(orm, 0, 1) * 255.0).astype(np.uint8)
    n = normal_dx(ch)
    N8 = np.rint((n * 0.5 + 0.5) * 255.0).astype(np.uint8)
    err = np.abs(srgb_decode(BC8.astype(np.float64) / 255.0) - np.clip(bc_lin, 0, 1))[wr]
    dw = D8[wr]
    r8 = ORM8[..., 1][wr] / 255.0
    return {"BC": BC8, "ORM": ORM8, "N": N8, "Detail": D8, "tint_linear": tint.tolist(),
            "tint_srgb": srgb_encode(tint).tolist(), "L_ref": a_hi, "detail_bias": bias, "detail_scale": scale,
            "recolour": {"bc_is_recolour_graph": "BC8 = sRGB8(Tint x (DetailBias + DetailScale x sRGBdecode(Detail8/255))) "
                                                 "from the quantised Detail and the rounded sidecar numbers",
                         "tint_is": "the part's MEAN linear colour over the written texels",
                         "detail_bias": bias, "detail_scale": scale,
                         "albedo_lo_hi": [round(a_lo, 6), round(a_hi, 6)],
                         "mean_of_bias_plus_scale_x_detail": round(float((bias + scale * dq[wr]).mean()), 6),
                         "max_abs_err_linear": float(err.max()), "detail_levels_used": int(len(np.unique(dw))),
                         "detail_clipped_share_low_high": [float(np.mean(alb[wr] < a_lo)), float(np.mean(alb[wr] > a_hi))],
                         "detail_min_max_code": [int(dw.min()), int(dw.max())],
                         "detail_percentiles_of_255": {str(p): float(np.percentile(dw, p))
                                                       for p in (0.1, 1, 10, 50, 90, 99, 99.9)}},
            "albedo_stats": {"mean": float(ch["alb"][wr].mean()), "p10": float(np.percentile(ch["alb"][wr], 10)),
                             "p50": float(np.percentile(ch["alb"][wr], 50)),
                             "p90": float(np.percentile(ch["alb"][wr], 90)), "max": float(ch["alb"][wr].max())},
            "roughness_stats": {"min": round(float(r8.min()), 4), "p1": round(float(np.percentile(r8, 1)), 4),
                                "p50": round(float(np.percentile(r8, 50)), 4), "max": round(float(r8.max()), 4)},
            "spec_mask_mean": float(spec[wr].mean()),
            "spec_mask_min_max": [round(float(spec[wr].min()), 4), round(float(spec[wr].max()), 4)]}


__all__ = ["paint_atlas", "finish", "owners", "srgb_encode", "srgb_decode", "wear_cover", "hash01", "fbm2"]
