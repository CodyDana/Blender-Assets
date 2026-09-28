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

Surface pass (2026-09-26, library 1.2.0): the blind judge's tells were surface and finish, so -
WEAR   pale grey rubbed-through strand tops in ragged patches where REFERENCE_SPEC 9 puts the worn
       zones (and a light 5 % elsewhere), a greyer scuffed film in the heavily worn left zone, fine
       scratches mostly along the strands; the dark smudge only ~22 % darker and still worn through
WEAVE  irregular courses (6 - 12.6 mm) of 4 - 6 unequal strands that wander round the cone, plank
       runs 16 - 52 mm between radial seams, a tone and a gloss PER PLANK TILE (the tile grid); the
       strand gaps no longer touch the gloss (at grazing views a per-strand gloss line was the
       record-groove look) and the course line breaks tile by tile
RODS   ribs a twisted cord with a pale worn core in ALBEDO (rough, low specular: no crawling
       glints); the rim tube's fibres frayed, its rolled crest rubbed pale; the binding cord light;
       the lashings three-ply twisted cord, crests worn pale, deep dark valleys
CAP    a flat lid with pale rib lines and a pale rubbed lip crest
CLOTH  fabric grain (uneven warp streaks, crushed crease lines, fuzzy dust), pale fold ridges on
       the knot and the fanned band, frayed ends
MICRO  fibre-scale albedo, specular and roughness variation (linear channels: mip-safe)
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np

from .blackhat_atlas import Atlas
from .blackhat_geom import COS_A, D2R, MeshBuilder, Member, band_section, knot_fold_field, wrap_profile

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
STRAW_BASE = 0.056
#: surface pass: the worn, rubbed-through strand tops are pale grey (observed sRGB 0.37, albedo
#: 0.08 - 0.20, p90 0.20); a streak covers under half a screen pixel across (0.6 mm of a 1.8 mm
#: strand), so its albedo sits at the bright end for the pixel to read as REFERENCE_SPEC's grey
FLECK_ALB = (0.14, 0.36)
COURSE_MM = 0.031 * 300.0          # REFERENCE_SPEC 5 (0.031 R): the MEAN course
#: surface pass: courses, strands and plank runs are IRREGULAR (round 1's even 9.3 mm courses of five
#: even strands read as record grooves).  Course widths 6.0 - 12.6 mm (mean 9.3), 4 - 6 strands of
#: unequal width per course (mean 1.8 mm = 0.006 R), plank runs 16 - 52 mm between radial seams, a
#: fresh set per course (the brick-like tile grid)
COURSE_W = (6.0, 12.6)
STRANDS_N = (4, 7)
SEAM_MM = (16.0, 52.0)
SEAM_DEG = (3.0, 8.0)              # kept for the report (REFERENCE_SPEC 4: seams 3 - 8 deg apart)
_WEAVE = {}


def weave_table(seed):
    """Course edges along the slant (mm) and each course's strand boundaries (fractions, padded)."""
    if seed in _WEAVE:
        return _WEAVE[seed]
    rng = np.random.default_rng(seed * 1009 + 17)
    w = rng.uniform(*COURSE_W, size=90)
    edges = np.concatenate([[-rng.uniform(0.0, COURSE_W[0])], np.cumsum(w)])
    edges[1:] += edges[0]
    nmax = STRANDS_N[1]
    bounds = np.full((len(w), nmax + 1), 2.0)
    for i in range(len(w)):
        n = int(rng.integers(*STRANDS_N))
        sw = rng.uniform(0.55, 1.45, size=n)
        bounds[i, :n + 1] = np.concatenate([[0.0], np.cumsum(sw) / sw.sum()])
        bounds[i, n] = 1.0
    _WEAVE[seed] = (edges, bounds)
    return edges, bounds


def wear_cover(theta, rho, outer=True):
    """Fraction of straw showing pale worn strand tops, by zone (REFERENCE_SPEC 9, MEASURED): left
    theta -62..-25 rho .45-.97 20 %; streaks theta -18..-5 rho .70-.82 12 %; front -5..16 7 %;
    right 72..95 18 % (partly grazing sheen, so 13 % painted).  Elsewhere (the far side, DESIGNED) only a light 3 %: the pale wear goes
    where the reference shows it and nowhere else."""
    th = (np.asarray(theta) + 180.0) % 360.0 - 180.0
    rho = np.asarray(rho)
    c = np.full(np.shape(th), 0.03)
    c = np.where((th > -95) & (th < 95), 0.06, c)
    c = c + (0.13 - c) * smooth(66, 72, th) * (1 - smooth(95, 101, th))
    c = c + (0.07 - c) * smooth(-7, -3, th) * (1 - smooth(14, 18, th))
    streak = smooth(-20, -16, th) * (1 - smooth(-7, -3, th))
    c = c + (0.08 + 0.10 * smooth(0.66, 0.71, rho) * (1 - smooth(0.81, 0.86, rho)) - c) * streak
    c = c + (0.14 - c) * smooth(-32, -28, th) * (1 - smooth(-20, -16, th))
    left = smooth(-72, -61, th) * (1 - smooth(-27, -22, th)) * smooth(0.40, 0.47, rho)   # edge within the zones' +-5
    c = c + (0.26 - c) * left
    c = np.where(rho < 0.40, c * 0.6, c)
    return c if outer else np.zeros_like(c)


def scratches(a, s, density, seed, width=0.30, aa=0.2):
    """Fine scratches where the black finish is rubbed through: straight thin pale lines 4 - 22 mm
    long, mostly along the strands (+-12 deg), one in twenty across; ``density`` (0..1) scales how many
    of the candidates per 24 mm cell are present.  (a, s) is the cone development (mm)."""
    cell = 24.0
    ci, cj = np.floor(a / cell), np.floor(s / cell)
    out = np.zeros(np.shape(a))
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            for k in range(3):
                h = hash01(I, J, k, seed=seed)
                on = h < density * 0.6
                if not np.any(on):
                    continue
                cx = (I + hash01(I, J, k, seed=seed + 1)) * cell
                cy = (J + hash01(I, J, k, seed=seed + 2)) * cell
                g = hash01(I, J, k, seed=seed + 3)
                ang = np.where(g < 0.95, (g / 0.95 - 0.5) * 24.0, (g - 0.975) * 1600.0) * D2R
                L = 4.0 + 18.0 * hash01(I, J, k, seed=seed + 4) ** 1.6
                ux, uy = np.cos(ang), np.sin(ang)
                px, py = a - cx, s - cy
                t = np.clip(px * ux + py * uy, -0.5 * L, 0.5 * L)
                d = np.hypot(px - t * ux, py - t * uy)
                taper = 1.0 - smooth(0.25, 0.5, np.abs(t) / L)
                strength = 0.55 + 0.45 * hash01(I, J, k, seed=seed + 5)
                out = np.maximum(out, on * line(d, width, aa) * taper * strength)
    return out


def paint_skin(m: Member, x, y, ts, seed):
    yt = y * m.flip
    s = np.hypot(x, yt)
    th = m.info["theta_mid"] + np.arctan2(yt, x) / (D2R * COS_A)
    outer = m.info["surface"] == "outer"
    r = s * COS_A
    rho = r / 300.0
    a = th * D2R * r                                     # arc length along the strands (mm)
    aa = max(ts, 0.10)
    edges, bounds = weave_table(seed)
    # hand-woven courses wander a little round the cone (no perfect rings)
    s_w = s + 0.55 * (2.0 * vnoise1(a / 55.0 + 3.1, seed=seed + 21) - 1.0) \
            + 0.25 * (2.0 * vnoise1(a / 13.0 + 7.7, seed=seed + 22) - 1.0)
    c = np.clip(np.searchsorted(edges, s_w, side="right") - 1, 0, len(edges) - 2)
    cw = edges[c + 1] - edges[c]
    fs = np.clip((s_w - edges[c]) / cw, 0.0, 1.0)
    bc = bounds[c]
    ks = np.clip((fs[:, None] >= bc).sum(1) - 1, 0, bounds.shape[1] - 2)
    f0 = np.take_along_axis(bc, ks[:, None], 1)[:, 0]
    f1 = np.minimum(np.take_along_axis(bc, ks[:, None] + 1, 1)[:, 0], 1.0)
    wk = np.maximum((f1 - f0) * cw, 0.3)
    fk = np.clip((fs - f0) / np.maximum(f1 - f0, 1e-6), 0.0, 1.0)
    d_edge = np.minimum(fk, 1 - fk) * wk
    gap = line(d_edge, 0.11, aa)
    d_course = np.minimum(fs, 1 - fs) * cw
    cline = line(d_course, 0.22, aa) * (0.55 + 0.45 * vnoise1(a / 30.0 + c * 7.1, seed=seed + 13))
    # radial seams: plank runs 8 - 30 mm, a fresh set per course (the tile grid)
    seam_d = np.full(np.shape(s), 99.0)
    cell = np.zeros(np.shape(s))
    faintv = np.zeros(np.shape(s))
    for ci in np.unique(c):
        sel = c == ci
        rng = np.random.default_rng(int(ci) * 7919 + seed * 31 + 5)
        r_mid = max(0.5 * (edges[ci] + edges[ci + 1]) * COS_A, 5.0)
        widths = rng.uniform(*SEAM_MM, size=420) / (r_mid * D2R)
        e = -190.0 - rng.uniform(0.0, 5.0) + np.concatenate([[0.0], np.cumsum(widths)])
        faint = rng.uniform(size=len(e))
        t = (th[sel] + 180.0) % 360.0 - 180.0
        k = np.clip(np.searchsorted(e, t), 1, len(e) - 1)
        dl, dr = t - e[k - 1], e[k] - t
        near = np.where(dl < dr, k - 1, k)
        seam_d[sel] = np.minimum(dl, dr) * D2R * r[sel]
        faintv[sel] = faint[near]
        cell[sel] = k
    seam = line(seam_d, 0.14, aa) * np.where(faintv < 0.35, 0.35, 0.8)
    # the course line is broken tile by tile (some plank edges sharp, some worn flush): no continuous rings
    cline = cline * (0.1 + 0.9 * hash01(c, cell, seed=seed + 32) ** 0.8)
    # tone: each plank tile its own tone (the tile grid), each strand a little, fine fibre streaks
    tile = hash01(c, cell, seed=seed)
    tone = 0.80 + 0.38 * tile ** 1.25
    tone *= 0.85 + 0.30 * hash01(c, ks, cell, seed=seed + 1)
    tone *= 0.84 + 0.32 * vnoise1(a / 4.5 + 37.0 * hash01(c, ks, seed=seed + 2), seed=seed + 3)
    tone *= 0.82 + 0.36 * vnoise2(a / 1.1, s_w / 0.7, seed=seed + 23)          # micro grain (texel scale)
    tone *= 0.86 + 0.28 * hash01(np.floor(a / 0.9), np.floor(s_w / 0.45), seed=seed + 35)   # fibre speckle
    dome = np.sqrt(np.clip(np.sin(math.pi * fk), 0, 1))
    alb = STRAW_BASE * tone * (0.94 + 0.06 * dome)
    alb *= (1 - 0.40 * gap) * (1 - 0.38 * cline) * (1 - 0.60 * seam)
    # relief: flat strands, each plank tile a slightly different camber (no two courses alike, so
    # no record grooves at grazing views); fibre ridges along the strands
    camber = (0.02 + 0.05 * hash01(c, cell, seed=seed + 15)) * np.clip(np.sin(math.pi * fs), 0, 1) ** 0.6
    fib = vnoise1(a / 2.2 + 53.0 * hash01(c, ks, seed=seed + 24), seed=seed + 25)
    hgt = 0.01 * dome - 0.012 * gap + camber - 0.03 * cline - 0.10 * seam + 0.012 * fib
    # the strand gaps barely touch the gloss: at grazing views a per-strand gloss line reads as the
    # record grooves round 1 was judged on (the gaps are hidden by the strands there)
    spec = (0.80 + 0.20 * dome) * (0.88 + 0.12 * hash01(c, cell, seed=seed + 33)) * (1 - 0.15 * gap) * (1 - 0.3 * cline) * (1 - 0.6 * seam)
    rough = 0.40 + 0.10 * hash01(c, cell, seed=seed + 4) + 0.04 * gap + 0.12 * cline + 0.20 * seam
    # micro-detail in the GLOSS (the lacquer's sheen dominates the black straw, so albedo speckle alone
    # is invisible): fibre-scale specular and roughness variation.  Linear quantities, so every mip is
    # their average (no crawl); the normal map carries none of it
    fs1 = hash01(np.floor(a / 1.3), np.floor(s_w / 0.45), seed=seed + 36)
    fs2 = vnoise1(a / 2.0 + 53.0 * hash01(c, ks, seed=seed + 37), seed=seed + 38)
    spec = spec * (0.55 + 0.45 * fs1) * (0.8 + 0.4 * fs2)
    rough = rough + 0.10 * (fs2 - 0.5) + 0.06 * (fs1 - 0.5)
    ao = 1.0 - 0.25 * gap - 0.35 * cline - 0.35 * seam
    tn = (th + 180.0) % 360.0 - 180.0
    # the one darker smudge (theta -45..-35, rho 0.55 - 0.90, ~15 % darker than its surround,
    # REFERENCE_SPEC 9): a dull, dirty patch with ragged edges
    if outer:
        # close-out: round 2's smudge was bounded by straight theta / rho edges and read as a
        # rectangular block.  Now a soft irregular blotch: a domain-warped ellipse in mm round the
        # zone's centre (theta -38.5, rho 0.72), a wide soft falloff, patchy inside
        rs = 0.72 * 300.0
        du = (tn + 38.5) * D2R * r                               # mm across the generators
        dv = (rho - 0.72) * 300.0 / COS_A                         # mm along the slant
        wu = du + 9.0 * (fbm2(a / 40.0, s / 40.0, seed=seed + 16, octaves=3) - 0.5)
        wv = dv + 22.0 * (fbm2(a / 45.0 + 5.1, s / 35.0, seed=seed + 17, octaves=3) - 0.5)
        e = np.hypot(wu / (5.2 * D2R * rs), wv / (0.17 * 300.0 / COS_A))
        sm = (1 - smooth(0.45, 1.25, e)) * (0.55 + 0.9 * fbm2(a / 16.0, s / 13.0, seed=seed + 12, octaves=4))
        sm = np.clip(sm, 0, 1)
    else:
        sm = np.zeros_like(s)
    # WEAR: the black finish rubbed through to pale grey on the strand tops, in ragged patches where
    # the zone is worn (REFERENCE_SPEC 9's zones and cover), plus fine scratches.  Close-out: the
    # zone borders are warped (round 2's radial, tile-aligned zone edges read as blocks)
    th_w = th + 7.0 * (fbm2(a / 70.0 + 2.3, s / 50.0, seed=seed + 18, octaves=3) - 0.5) * 2.0
    rho_w = rho + 0.05 * (fbm2(a / 60.0 + 7.9, s / 40.0, seed=seed + 19, octaves=3) - 0.5) * 2.0
    cov = wear_cover(th_w, rho_w, outer) * (1 - 0.25 * sm)
    if outer:
        P = fbm2(a / 34.0, s / 20.0, seed=seed + 9, octaves=4)
        thr = 0.70 - 1.05 * cov
        patch = smooth(thr - 0.04, thr + 0.12, P)            # soft-edged (close-out)
        # inside a patch most strand tops are rubbed; outside, the odd short streak
        p_on = patch * (0.22 + 1.1 * cov) + (1 - patch) * 0.30 * cov
        Ls = 4.0 + 20.0 * hash01(c, ks, seed=seed + 5) ** 1.3          # 0.5 - 3 deg along the strand
        off = hash01(c, ks, seed=seed + 6) * 7.0
        q = np.floor(a / Ls + off)
        fq = a / Ls + off - q
        # a rub crosses two or three neighbouring strands at once (a pale patch, not single hairs)
        grp = np.floor((ks + hash01(c, np.floor(a / 9.0), seed=seed + 30) * 3.0) / 2.5)
        on = (hash01(c, ks, q, seed=seed + 7) < p_on) | (hash01(c, grp, np.floor(a / 7.0), seed=seed + 31) < 0.0 * p_on * patch)
        along = smooth(0.0, 0.05, fq) * (1 - smooth(0.55 + 0.3 * hash01(c, ks, q, seed=seed + 34), 0.62 + 0.3 * hash01(c, ks, q, seed=seed + 34), fq))
        wide = smooth(0.15, 0.24, cov)                 # the heavily worn zone: whole strand tops rubbed
        across = smooth(0.26 - 0.16 * wide, 0.34 - 0.18 * wide, fk) * (1 - smooth(0.66 + 0.18 * wide, 0.74 + 0.16 * wide, fk))
        fl = on * along * across * (1 - 0.7 * seam) * (0.8 + 0.2 * vnoise1(a / 1.3, seed=seed + 26))
        # scuffed lacquer between the streaks in a patch: a greyer film
        film = (patch * (0.45 + 0.55 * fbm2(a / 6.0, s / 4.0, seed=seed + 27)) * smooth(0.10, 0.22, cov)
                * (1 - 0.7 * gap) * (0.6 + 0.4 * dome))
        sc = scratches(a, s_w, np.clip(2.2 * cov - 0.08 + 0.25 * patch * smooth(0.1, 0.2, cov), 0.0, 0.85), seed + 28, 0.26, aa) * (1 - 0.5 * seam)
        fa = FLECK_ALB[0] + (FLECK_ALB[1] - FLECK_ALB[0]) * hash01(c, ks, q, seed=seed + 8) ** 1.8
        alb = alb * (1 + 1.6 * film)
        alb = alb * (1 - fl) + fa * fl
        sa = FLECK_ALB[0] + 0.9 * (FLECK_ALB[1] - FLECK_ALB[0]) * hash01(np.floor(a / 24.0), np.floor(s_w / 24.0), seed=seed + 29)
        alb = alb * (1 - sc) + np.maximum(alb, sa) * sc
        wear = np.maximum(fl, sc)
        # rubbed-through straw is matte; the lacquer around it keeps its sheen
        spec = spec * (1 - 0.35 * wear)
        rough = rough + 0.20 * wear + 0.05 * film
        hgt = hgt - 0.03 * sc
        # the smudge: darker and duller, the wear still showing through it
        alb *= 1 - 0.16 * sm
        spec = spec * (1 - 0.2 * sm)
        rough = rough + 0.08 * sm
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
    spec = np.clip(spec, 0.0, 1.0)
    return {"alb": alb, "rough": rough, "spec": spec, "ao": ao, "hgt": hgt}


def _rope(x, y, r, pitch, plies, aa):
    """Twisted cord: ply parameter f in [0, 1) across each ply, and the groove line."""
    ang = y / max(r, 1e-6)
    ph = (ang / (2 * math.pi) - x / pitch) * plies
    f = ph - np.floor(ph)
    groove = line(np.minimum(f, 1 - f) * (2 * math.pi * r / plies), 0.10, aa)
    return f, groove


def _fibres(x, y, pitch, seed, aa):
    """Fine fibres along x inside a ply / strip: (fibre index, fibre groove line, fibre tone)."""
    fi = np.floor(y / pitch)
    ff = y / pitch - fi
    fline = line(np.minimum(ff, 1 - ff) * pitch, 0.05, aa)
    tone = 0.80 + 0.40 * hash01(fi, np.floor(x / (6.0 + 20.0 * hash01(fi, seed=seed))), seed=seed + 1)
    return fi, fline, tone


def paint_rib(m: Member, x, y, ts, seed):
    """A twisted split-cane cord (REFERENCE_SPEC 4: rope twist pitch 1.6 d, a light worn core
    between dark flanks).  Surface pass: the worn core is ALBEDO (pale ply crests on the rod's top),
    not gloss, and the rod stays rough, so a turn never breaks its highlight into crawling dashes."""
    r = m.info["r"]
    aa = max(ts, 0.10)
    f, groove = _rope(x, y, r, 1.6 * 2 * r, 2, aa)
    dome = np.sqrt(np.clip(np.sin(math.pi * f), 0, 1))
    k = int(round(m.info["theta"] * 10))
    top = -np.cos(y / r)                                     # +1 on the top of the rod (away from the skin)
    _fi, fline, ftone = _fibres(x, f * 2 * math.pi * r / 2.0, 0.35, seed + k, aa)
    tone = (0.80 + 0.40 * vnoise1(x / 5.0, seed=seed + k)) * ftone
    alb = STRAW_BASE * 1.05 * tone * (0.70 + 0.30 * dome) * (1 - 0.65 * groove) * (1 - 0.25 * fline)
    # the pale worn core: the crest of each ply on the rod's top rubbed to grey, broken along the rod
    core = smooth(0.15, 0.65, top) * smooth(0.35, 0.85, dome)
    brk = smooth(0.30, 0.55, fbm2(x / 9.0, k * 0.37, seed=seed + 1, octaves=3))
    pale = core * (0.35 + 0.65 * brk) * (1 - groove)
    pa = 0.10 + 0.08 * vnoise1(x / 3.0 + k, seed=seed + 3)
    alb = alb * (1 - pale) + pa * pale
    return {"alb": alb, "rough": 0.66 + 0.12 * groove + 0.08 * pale,
            "spec": (0.35 + 0.25 * dome) * (1 - 0.7 * groove) * (1 - 0.3 * pale),
            "ao": 1 - 0.35 * groove, "hgt": 0.16 * dome - 0.14 * groove - 0.02 * fline}


def rim_scuff_thetas():
    """The front rim's light scuffs (REFERENCE_SPEC 9: image x 280 - 330 and 360 - 380 on the
    front face), as azimuths (from the reference camera model, rounded)."""
    return ((-9.5, -2.5), (1.5, 4.5))


def paint_tube(m: Member, x, y, ts, seed, cord=False):
    Rc, rt = m.info["Rc"], m.info["rt"]
    th = m.info["theta_a"] + x / (Rc * D2R)
    a = m.info["a0"] + y / rt / D2R                          # section angle (deg), 0 = outward
    an = ((a + 180.0) % 360.0) - 180.0
    aa = max(ts, 0.10)
    if cord:
        # the LIGHT binding cord on the tube's inner top (REFERENCE_SPEC 6): a twisted two-ply cord,
        # its crests worn pale
        f, groove = _rope(x, y, rt, 3.2, 2, aa)
        dome = np.sqrt(np.clip(np.sin(math.pi * f), 0, 1))
        wear = smooth(0.4, 0.75, fbm2(x / 12.0, 1.3, seed=seed + 1)) * dome
        alb = (STRAW_BASE * 1.2 * (0.75 + 0.25 * dome) * (0.8 + 0.4 * vnoise1(x / 6.0, seed=seed))
               * (1 - 0.6 * groove))
        alb = alb * (1 - wear) + 0.11 * wear
        return {"alb": alb, "rough": 0.60 + 0.2 * groove, "spec": 0.35 * (0.6 + 0.4 * dome) * (1 - 0.6 * groove),
                "ao": 0.7 - 0.3 * groove, "hgt": 0.08 * dome - 0.07 * groove}
    # split cane rolled round the rim: long fibre strips along the rim, frayed
    fib_w = 0.75 + 0.3 * hash01(np.floor(y / 1.05), seed=seed + 9)
    fi = np.floor(y / 1.05)
    ff = y / 1.05 - fi
    fline = line(np.minimum(ff, 1 - ff) * fib_w, 0.06, aa)
    tone = (0.72 + 0.56 * hash01(fi, np.floor(x / (8.0 + 30.0 * hash01(fi, seed=seed)) + hash01(fi, seed=seed) * 3),
                                 seed=seed + 1) ** 1.3)
    tone *= 0.82 + 0.36 * vnoise1(x / 5.0 + 11.0 * hash01(fi, seed=seed + 2), seed=seed + 3)
    alb = STRAW_BASE * 0.62 * tone * (1 - 0.55 * fline)
    # frayed fibre ends: short, thin, pale strands lifting off the roll at a slight angle
    fx = x + 0.12 * y * (hash01(np.floor(x / 14.0), seed=seed + 10) - 0.5) * 8.0
    fr_on = hash01(np.floor(fx / 14.0), fi, seed=seed + 11) < 0.10
    fr_f = (fx / 14.0) % 1.0
    fray = fr_on * smooth(0.0, 0.1, fr_f) * (1 - smooth(0.3, 0.7, fr_f)) * (1 - fline)
    # the rolled edge's crest (top, outward-up) is rubbed pale all round: the edge highlight
    crest = smooth(18.0, 45.0, an) * (1 - smooth(78.0, 102.0, an))
    crest = crest * smooth(0.25, 0.60, fbm2(x / 16.0, y / 4.0, seed=seed + 12)) * (1 - fline)
    # wear flecks along the fibres, and the scuffs on the front face (REFERENCE_SPEC 9)
    cov = 0.15 * (0.3 + 1.4 * fbm2(x / 40.0, y / 10.0, seed=seed + 4)) * (0.4 + 0.6 * smooth(-60.0, 10.0, an) * (1 - smooth(60.0, 120.0, an)))
    q = np.floor(x / (2.0 + 8.0 * hash01(fi, seed=seed + 5)))
    fl = (hash01(fi, q, seed=seed + 6) < cov) * (1 - fline)
    thn = (th + 180.0) % 360.0 - 180.0
    face = smooth(-75, -35, an) * (1 - smooth(25, 60, an))
    sc = np.zeros_like(x)
    for lo, hi in rim_scuff_thetas():
        sc = np.maximum(sc, smooth(lo - 1.0, lo + 0.5, thn) * (1 - smooth(hi - 0.5, hi + 1.0, thn)))
    # scuffs are rubbed FIBRES: whole fibre runs 2 - 12 mm long, not blobs
    qs = np.floor(x / (2.0 + 10.0 * hash01(fi, seed=seed + 14)) + hash01(fi, seed=seed + 15) * 5.0)
    scuff = sc * face * (hash01(fi, qs, seed=seed + 7) < 0.28 * (0.5 + fbm2(x / 8.0, y / 3.0, seed=seed + 16)))
    fl = np.clip(np.maximum.reduce([fl, scuff * 0.9, 0.85 * crest, 0.8 * fray]), 0, 1)
    pa = 0.10 + 0.14 * hash01(fi, q, seed=seed + 8) ** 1.5
    alb = alb * (1 - fl) + pa * fl
    return {"alb": alb, "rough": 0.58 + 0.12 * fline + 0.15 * fl, "spec": 0.8 * (1 - 0.5 * fline) * (1 - 0.4 * fl),
            "ao": 1 - 0.25 * fline, "hgt": -0.09 * fline + 0.05 * fray + 0.02 * vnoise1(x / 2.0 + fi * 3.1, seed=seed + 13)}


def paint_lashing(m: Member, x, y, ts, seed, rw):
    """Three wraps of twisted three-ply cord (REFERENCE_SPEC 6): dark cord, the ply crests worn
    pale, each wrap its own tone, deep dark valleys between the wraps."""
    aa = max(ts, 0.10)
    prof, _pn, seg = wrap_profile("wraps", rw)
    # the three cords across y: edges at seg[1], valleys seg[3], seg[5], edge seg[7]
    b = [seg[1], seg[3], seg[5], seg[7]]
    k = np.clip(np.searchsorted(np.array(b), y) - 1, 0, 2)
    y0 = np.array(b)[k]
    y1 = np.array(b)[k + 1]
    fy = np.clip((y - y0) / (y1 - y0), 0, 1)
    kk = int(round(m.info["theta"] * 10))
    # twisted cord: diagonal ply lines, the pitch a little different per wrap
    pitch = 2.6 + 0.8 * hash01(k, kk, seed=seed + 5)
    f, groove = _rope(x + 7.0 * hash01(k, kk, seed=seed + 6), (y - y0) * 1.0, rw, pitch, 3, aa)
    pd = np.sqrt(np.clip(np.sin(math.pi * f), 0, 1))
    dome = np.sqrt(np.clip(np.sin(math.pi * fy), 0, 1))
    valley = 1 - smooth(0.0, 0.25, np.minimum(fy, 1 - fy))
    tone = (0.75 + 0.5 * hash01(k, kk, seed=seed + 7)) * (0.85 + 0.3 * vnoise1(x / 5.0 + k * 13.0, seed=seed + kk))
    alb = STRAW_BASE * 1.0 * tone * (0.65 + 0.35 * pd) * (1 - 0.6 * groove) * (1 - 0.8 * valley)
    wear = (smooth(0.45, 0.85, pd * dome) * smooth(0.35, 0.65, fbm2(x / 5.0, k * 1.7 + kk * 0.13, seed=seed + 3))
            * (1 - groove))
    alb = alb * (1 - wear) + (0.09 + 0.05 * hash01(np.floor(x / 2.0), k, kk, seed=seed + 4)) * wear
    return {"alb": alb, "rough": 0.62 + 0.15 * groove + 0.08 * wear,
            "spec": (0.4 + 0.3 * pd * dome) * (1 - 0.5 * groove) * (1 - 0.6 * valley),
            "ao": 1 - 0.25 * groove - 0.5 * valley, "hgt": 0.10 * dome + 0.10 * pd - 0.12 * groove - 0.15 * valley}


def paint_cap(m: Member, x, y, ts, seed, rib_thetas, lip=False):
    """The crown cap (surface pass): a flat lid of concentric strands with the 13 ribs carried
    over it as pale worn lines meeting at the top (no finial), and a hard lip whose crest is rubbed
    pale all round (the reference's light cap edge)."""
    aa = max(ts, 0.10)
    if lip:
        # y = arc down the lip profile from the lid's edge: 0 - 1.2 mm the crest (pale, rubbed),
        # then the lip's face, then the dark undercut
        fi = np.floor(y / 0.8)
        tone = 0.75 + 0.5 * hash01(np.floor(x / (3.0 + 6.0 * hash01(fi, seed=seed))), fi, seed=seed + 1)
        crest = (1 - smooth(1.0, 2.2, y)) * smooth(0.2, 0.5, fbm2(x / 7.0, 0.5, seed=seed + 2))
        under = smooth(2.6, 3.6, y)
        alb = STRAW_BASE * 1.3 * tone * (1 - 0.8 * under)
        alb = alb * (1 - crest) + (0.14 + 0.08 * hash01(np.floor(x / 2.0), seed=seed + 3)) * crest
        return {"alb": alb, "rough": 0.62 + 0.1 * crest, "spec": 0.6 * (1 - 0.8 * under), "ao": 1 - 0.7 * under,
                "hgt": -0.04 * line(np.minimum(y / 0.8 - fi, 1 - (y / 0.8 - fi)) * 0.8, 0.06, aa)}
    s = np.hypot(x, y)
    phi = m.info["theta0"] + 180.0 + np.arctan2(y, x) / D2R
    r = s * math.cos(m.info.get("slope_deg", 21.0) * D2R)
    # concentric strands (irregular widths) and the ribs carried over the lid
    sw = 1.3 + 0.8 * hash01(np.floor(s / 1.7), seed=seed + 5)
    ci = np.floor(s / 1.7)
    fs = s / 1.7 - ci
    gap = line(np.minimum(fs, 1 - fs) * sw, 0.1, aa)
    rl = np.zeros_like(s)
    for t in rib_thetas:
        d = ((phi - t + 180.0) % 360.0 - 180.0) * D2R * np.maximum(r, 0.5)
        rl = np.maximum(rl, line(d, 0.9, aa) * smooth(1.5, 4.0, r))
    tone = 0.75 + 0.5 * hash01(ci, np.floor(phi / 9.0), seed=seed)
    alb = STRAW_BASE * 1.25 * tone * (1 - 0.5 * gap)
    # the rib lines: pale, rubbed, broken
    rpale = rl * smooth(0.2, 0.5, fbm2(r / 4.0, phi / 25.0, seed=seed + 6))
    alb = alb * (1 - rpale) + 0.20 * rpale
    fl = (hash01(ci, np.floor(phi * r / 40.0 / (1.0 + 2.0 * hash01(ci, seed=seed + 8))), seed=seed + 1) < 0.22) * (1 - gap)
    alb = alb * (1 - fl) + (0.11 + 0.08 * hash01(ci, np.floor(phi / 3.0), seed=seed + 9)) * fl
    # the lid's outer edge rubbed pale (it joins the lip crest)
    edge = smooth(m.info["rc"] - 2.0, m.info["rc"] - 0.3, r) * smooth(0.3, 0.6, fbm2(phi / 6.0, 2.0, seed=seed + 7))
    alb = alb * (1 - edge) + 0.16 * edge
    return {"alb": alb, "rough": 0.62 + 0.1 * gap + 0.05 * (rpale + fl), "spec": 0.7 - 0.4 * gap, "ao": 1 - 0.3 * gap,
            "hgt": -0.08 * gap + 0.22 * rl}


# =========================================================================== the cloth
#: REFERENCE_SPEC 9: cloth lum 0.030 (band and tails), neutral, matte
CLOTH_BASE = 0.026


def _weave(x, y, ts, seed):
    """A fine plain weave (0.45 mm threads) with slub and mottling."""
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


def _grain(x, y, seed, aa):
    """Surface pass: the fabric grain the reference shows at its own scale - warp streaks along the
    cloth (threads of uneven thickness and tone, 0.4 - 1.6 mm, varying along their length), faint
    crushed crease lines along the length, and a fuzzy, dusty mottle.  Returns (tone, crease
    line, fuzz)."""
    band_w = 0.4 + 1.2 * hash01(np.floor(y / 1.1), seed=seed + 1)
    yi = np.floor(y / 1.1)
    streak = 0.88 + 0.24 * hash01(yi, np.floor(x / (5.0 + 25.0 * hash01(yi, seed=seed + 2))), seed=seed + 3) ** 1.3
    streak *= 0.88 + 0.24 * vnoise1(x / 2.5 + 31.0 * hash01(yi, seed=seed + 4), seed=seed + 5)
    # crushed creases: long thin lines along the cloth at irregular spacing, wandering slowly
    cy = y + 1.2 * (vnoise1(x / 30.0, seed=seed + 6) - 0.5)
    ci = np.floor(cy / 5.5)
    cf = cy / 5.5 - ci
    on = hash01(ci, np.floor(x / 60.0), seed=seed + 7) < 0.45
    crease = on * line((cf - 0.5) * 5.5, 0.22 + 0.2 * hash01(ci, seed=seed + 8), aa)
    ridge = on * line((cf - 0.5) * 5.5 - 0.9, 0.35, aa)
    fuzz = fbm2(x / 7.0, y / 6.0, seed=seed + 9, octaves=5)
    return streak * (1 - 0.45 * crease) * (1 + 0.35 * ridge), crease, fuzz, band_w


def paint_cloth(m: Member, x, y, ts, seed, hat=None):
    part = m.info["part"]
    aa = max(ts, 0.08)
    h, slub = _weave(x, y, ts, seed)
    tone, crease, fuzz, _bw = _grain(x, y, seed, aa)
    mott = (0.70 + 0.60 * fbm2(x / 38.0, y / 22.0, seed=seed + 2, octaves=4)) * (0.80 + 0.40 * vnoise2(x / 0.9, y / 0.9, seed=seed + 13))
    alb = CLOTH_BASE * 1.20 * mott * slub * tone * (0.55 + 0.45 * h)
    # matte cloth (final pass): roughness 0.85 - 0.95 and a specular mask of 0.5 - 0.7, which at
    # SPEC_SCALE cloth 0.5 is Unreal Specular 0.25 - 0.35 (F0 0.020 - 0.028)
    rough = 0.86 + 0.05 * (1 - h)
    spec = 0.50 + 0.20 * h
    ao = (0.9 + 0.1 * h) * (1 - 0.3 * crease)
    hgt = 0.05 * h - 0.12 * crease
    dust = 0.35 * smooth(0.55, 0.80, fuzz)
    if part == "band":
        # the twisted roll carries diagonal twist lines where it is rolled (REFERENCE_SPEC 7), their
        # ridges rubbed paler
        tp = m.info["theta0"] + (m.info["theta1"] - m.info["theta0"]) * np.clip(
            x / max(m.hi[0], 1e-6), 0, 1)
        q = np.clip((0.040 * 300 - band_section(hat, tp)[0]) / ((0.040 - 0.016) * 300), 0, 1)
        tw = (x * 0.7 + y) / 4.0
        fr = tw - np.floor(tw)
        twl = line((fr - 0.5) * 4.0, 0.35, 0.3) * q
        twr = line((fr - 0.15) * 4.0, 0.45, 0.3) * q
        alb *= (1 + 0.45 * q) * (1 - 0.50 * twl) * (1 + 0.8 * twr)
        rough = rough - 0.02 * q
        hgt = hgt - 0.25 * twl + 0.08 * twr
        ao = ao * (1 - 0.3 * twl)
        # the fanned band near the knot (close-out): round 2 painted an even stack of parallel fold
        # lines here (every 6.5 mm across the band), which the reference does not show.  Now only
        # soft uneven shading and, where the band enters the knot, a pale rubbed highlight
        # (REFERENCE: the band is paler where it goes into the knot)
        fan = 1 - q
        shade = fbm2(x / 18.0, y / 9.0, seed=seed + 11, octaves=3)
        alb *= 1 + fan * 0.35 * (shade - 0.5)
        entry = np.maximum(smooth(398.0, 412.0, tp), 1 - smooth(63.0, 68.0, tp))
        rub = entry * smooth(0.42, 0.68, fbm2(x / 9.0, y / 3.5, seed=seed + 14, octaves=3))
        alb *= 1 + 1.4 * rub
        rough = rough + 0.03 * rub
        dust = np.maximum(dust, 0.4 * (fbm2(x / 20.0, y / 6.0, seed=seed + 5) > 0.60))
    elif part in ("tail", "tail_wall"):
        # tails: dusty greyer patches (the reference's greyer tail faces), worn and frayed edges
        dust = np.maximum(dust, 0.75 * smooth(0.50, 0.72, fbm2(x / 26.0, y / 10.0, seed=seed + 6, octaves=4)))
        if part == "tail":
            L = m.info["length"]
            # fraying toward the tear: pale loose fibres along the cloth near the end
            fib = (hash01(np.floor(y / 0.7), np.floor(x / 6.0), seed=seed + 7) < 0.25)
            dust = np.maximum(dust, 0.9 * smooth(L - 110.0, L - 20.0, x) * fib)
        else:
            dust = np.maximum(dust, 0.7 * (hash01(np.floor(x / 0.8), seed=seed + 9) < 0.4))
    elif part == "knot":
        # the knot: gathered folds (the geometry's) with pale rubbed ridges and dark creases between
        rm, rb = m.info.get("rm", 20.0), m.info.get("rb", 15.0)
        # the two lobes' folds twist in opposite senses (geom.knot_fold_field), so they cross
        folds = m.info.get("folds", (0.35, 1.45, 2.6, 3.9, 5.0))
        side = np.sin(np.clip(y / rb, 0, math.pi)) ** 2.5
        amps = [0.55 + 0.45 * ((i * 2) % 3) / 2.0 for i in range(len(folds))]
        ridge = np.clip(knot_fold_field(x / rm, np.clip(y / rb, 0, math.pi), folds, amps, 0.16), 0, 1) * side
        be = y / rb
        crease_k = np.clip(1 - ridge * 2.5, 0, 1) * np.sin(np.clip(be, 0, math.pi)) ** 0.5
        alb *= (1 + 2.2 * ridge * (0.5 + 0.5 * fuzz)) * (1 - 0.35 * crease_k * smooth(0.4, 0.8, fbm2(x / 6.0, y / 6.0, seed=seed + 12)))
        hgt = hgt + 0.15 * ridge
        ao = ao * (1 - 0.3 * crease_k)
        dust = np.maximum(dust, 0.5 * smooth(0.5, 0.75, fbm2(x / 8.0, y / 8.0, seed=seed + 8)))
    alb = alb * (1 + 1.3 * dust)
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
