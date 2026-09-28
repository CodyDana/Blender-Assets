#!/usr/bin/env python
"""props_lib.smokebomb_cloth - the woven tape, drawn straight into the atlas (round 3).

numpy only.  Every texel of every island is a point of one strip's chart (s along the tape,
w across it, mm), so the cloth is evaluated where it lives: no projection, no reference
pixel.  What a texel needs to know about its neighbours (how far to its own edge, how far to
the edge of a strip lying over it) comes from the same strip functions the mesh is built
from, so the rolled rim sits exactly on the modelled step and the crevice at its foot.

ROUND 3: WHAT THE REFERENCE SHOWS AT 5x, AND HOW IT IS DRAWN
------------------------------------------------------------
The round-2 adversary read round 2's cloth as "a regular field of short bright dashes (brick
or tweed stipple)".  At 5x the reference is a NET of thin light threads over dark cells:

    warp        thin light crowns along the tape, 0.30 mm apart (4.1 px), continuous, each
                its own brightness (the persistent streaks), over a dark body
    weft        short light cross segments at an irregular pitch (~0.65 mm), each spanning
                one to a few warp gaps, wavering - together with the warp crowns they
                outline small dark cells: the "window screen" grid
    crossings   where a weft segment meets a warp crown: a raised knot, the brightest point
                of the weave (the reference's point glints, ~4 % of pixels)
    fibres      thin light curly fibres, sparse
    padded tape the tape rolls down toward both edges over the last ~1.5 mm (normal map):
                every band shades like a flat tube, not a sheet
    rolled rim  every exposed edge is a round cord ~0.5 mm thick, segmented by thread wraps
                every ~0.7 mm (light crowns, dark joints); its line wanders (the fray,
                1.5 px rms at an 11.5 px wavelength)
    shadow      beyond an upper strip's edge, on the strip beneath: a dark crevice and a
                soft occlusion band (REFERENCE_SPEC 5: 30 - 47 % darker)
    tape side   the geometric wall under a rim is the cord seen from the side: dark cloth,
                never black
    threads     T1 / T2 hang from W's cord over A: light grey curly yarn, forked, with a
                soft shadow; T3 a curl on A; T5 a stub (T4 is geometry: smokebomb_threads)
    colour      one dye for every strip, with a faint fibre-scale hue mottle
    NOT HERE    no dirt, grime, fading, burnish, stains, scorch, slubs
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import smokebomb_strips as SS


@dataclass
class Cloth:
    dye: Tuple[float, float, float] = (0.0504, 0.0415, 0.0374)   # chroma of the dye (luma rescaled)
    fibre: Tuple[float, float, float] = (0.62, 0.575, 0.53)     # light threads / glints (linear)
    # ------------------------------------------------------------- the net
    cell_lum: float = 0.0035          # the dark gaps between threads (linear luma)
    body_lum: float = 0.012           # a warp thread's body
    crown_lum: float = 0.19          # a float's lit crown
    warp_pitch_mm: float = 0.30
    crown_half_mm: float = 0.035
    body_half_mm: float = 0.08
    rib_sigma: float = 0.25           # per-thread brightness (persistent streaks)
    float_sigma: float = 0.35 
    float_end: float = 0.2            # a float's brightness at its ends (it dives under)
    break_half_mm: float = 0.075      # the dark break where the warp dives under the weft        # per-float brightness
    weft_pitch_mm: float = 0.62
    weft_jitter: float = 0.28
    weft_half_mm: float = 0.028
    weft_lum: float = 0.18
    weft_prob: float = 0.8           # share of weft bars that show
    weft_run: float = 3.0             # mean run of consecutive visible bars (warps)
    knot_lum: float = 0.25            # a raised crossing
    knot_prob: float = 0.8
    knot_r_mm: float = 0.045
    glint_lum: float = 1.3           # the rare bright glint on a crossing
    glint_prob: float = 0.35
    mottle: float = 0.08              # slow tone variation of the net
    streak_pitch_mm: float = 0.75     # the persistent streaks along the tape ...
    streak_log: float = 0.16          # ... and their strength (log)
    chroma_mottle: float = 0.12       # fibre-scale hue variation (REFERENCE block chroma std)
    fibre_cell_mm: float = 0.7
    fibre_per_cell: float = 0.22
    fibre_len_mm: Tuple[float, float] = (0.2, 0.7)
    fibre_width_mm: float = 0.065
    fibre_gain: Tuple[float, float] = (0.5, 1.0)
    fibre_curl: float = 7.0
    fibre_tone: float = 0.7
    # ------------------------------------------------------------- relief (normal map), mm
    rib_h_mm: float = 0.04
    weft_h_mm: float = 0.02
    knot_h_mm: float = 0.02
    pad_mm: float = 0.2               # the tape rolls over this much at its own edge ...
    pad_reach_mm: float = 2.5         # ... over this distance (a quarter-round shoulder)
    pad_shape: float = 1.0
    dip_mm: float = 0.35              # a strip dips this much toward a covering edge ...
    dip_w_mm: float = 1.6             # ... over this distance
    cord_relief: float = 1.0
    groove_dark: float = 0.0         # the groove between the rim and the tape body
    # ------------------------------------------------------------- the rolled rim
    cord_mm: float = 0.55             # the cord's width at the edge
    cord_h_mm: float = 0.12
    cord_lum: float = 0.07           # the rim's tone floor (linear luma) ...
    cord_gain: float = 0.8            # ... plus the weave, brightened this much
    cord_body: float = 0.65           # share of the crown tone on the cord's flanks
    cord_lit_at: float = 0.62         # where across the cord (0 edge .. 1 inner) the crown is
    cord_wander: float = 0.7         # share of the fray the cord line follows
    wrap_pitch_mm: float = 0.80       # thread wraps round the cord
    wrap_lean: float = 0.12
    wrap_lum: float = 0.09
    joint_dark: float = 0.3
    joint_half_mm: float = 0.05
    fray_rms_mm: float = 0.2         # the cord's gentle wander (the fine jitter is the bulging segments)
    fray_wavelength_mm: float = 1.0
    cord_bulge_mm: float = 0.12
    fringe_lum: float = 0.035
    fringe_prob: float = 0.25
    # ------------------------------------------------------------- the strip beneath
    core_w_mm: float = 0.12           # the crevice's solid dark core ...
    core_lum: float = 0.001          # ... and its tone
    crevice_mm: float = 0.35
    crevice_dark: float = 0.6
    occl_w_mm: float = 2.2
    occl_pow: float = 1.5
    rim_boost: float = 0.35           # a strip brightens toward its own exposed edge ...
    boost_w_mm: float = 1.5           # ... over this distance
    occl_dark: float = 0.5
    groove_mm: float = 0.07
    # ------------------------------------------------------------- the tape's side (walls)
    wall_lum: float = 0.02
    wall_top_lum: float = 0.06        # the rolled cord seen from the side, at the wall's top
    wall_round_mm: float = 0.25       # the wall's normal-map roll ...
    wall_round_w_mm: float = 0.35     # ... over this depth
    # ------------------------------------------------------------- material
    roughness: float = 0.88
    rough_var: float = 0.05
    fibre_roughness: float = 0.74
    strip_variation: float = 0.02
    # ------------------------------------------------------------- loose threads
    thread_lum: float = 0.30


# =========================================================================== noise
def _hash(*ints, seed: int = 0) -> np.ndarray:
    """Deterministic uniform [0, 1) per integer tuple (vectorised, 64-bit mix)."""
    h = np.uint64(seed * 0x9E3779B97F4A7C15 % (1 << 64))
    with np.errstate(over="ignore"):
        for v in ints:
            x = np.asarray(v).astype(np.int64).astype(np.uint64)
            h = h ^ (x + np.uint64(0x9E3779B97F4A7C15) + (h << np.uint64(6)) + (h >> np.uint64(2)))
            h = h * np.uint64(0xBF58476D1CE4E5B9)
            h = h ^ (h >> np.uint64(31))
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def noise1(x: np.ndarray, seed: int) -> np.ndarray:
    i = np.floor(x)
    f = x - i
    a = _hash(i, seed=seed) * 2 - 1
    b = _hash(i + 1, seed=seed) * 2 - 1
    t = f * f * (3 - 2 * f)
    return a + (b - a) * t


def noise2(x: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    tx, ty = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed=seed)
    b = _hash(ix + 1, iy, seed=seed)
    c = _hash(ix, iy + 1, seed=seed)
    d = _hash(ix + 1, iy + 1, seed=seed)
    return ((a + (b - a) * tx) + ((c + (d - c) * tx) - (a + (b - a) * tx)) * ty) * 2 - 1


def noise3(p: np.ndarray, seed: int) -> np.ndarray:
    """Smooth value noise in [-1, 1] on a unit 3-D lattice (``p`` is (N, 3))."""
    i = np.floor(p)
    f = p - i
    t = f * f * (3 - 2 * f)
    out = np.zeros(len(p))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed=seed) * 2 - 1
                wx = t[:, 0] if dx else 1 - t[:, 0]
                wy = t[:, 1] if dy else 1 - t[:, 1]
                wz = t[:, 2] if dz else 1 - t[:, 2]
                out += h * wx * wy * wz
    return out


def fray_field(P_cam: np.ndarray, cloth, seed: int) -> np.ndarray:
    """The frayed edge's wander (mm), a function of the POINT ON THE BALL, so the upper
    strip's rim and the crevice on the strip beneath wander together."""
    q = P_cam * (35.0 / cloth.fray_wavelength_mm)
    # 1.2 n + 0.5 n' of unit value noise has an rms of 0.473 (measured): normalised
    return cloth.fray_rms_mm / 0.473 * (1.2 * noise3(q, seed) + 0.25 * noise3(q * 2.7, seed + 1))


def fbm2(x, y, seed, octaves=3):
    out, amp, norm = 0.0, 0.5, 0.0
    for o in range(octaves):
        out = out + amp * noise2(x, y, seed + 17 * o)
        norm += amp
        x = x * 2.03
        y = y * 2.03
        amp *= 0.5
    return out / norm


def _erfinv(y):
    a = 0.147
    y = np.clip(y, -0.999999, 0.999999)
    ln = np.log(1 - y * y)
    t = 2 / (np.pi * a) + ln / 2
    return np.sign(y) * np.sqrt(np.sqrt(t * t - ln / a) - t)


def _line(dist, half, aa):
    """Anti-aliased coverage of a line of half-width ``half`` at distance ``dist``."""
    return np.clip((half + aa - dist) / (2 * aa), 0.0, 1.0)


def _smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


# =========================================================================== the net
def weave(s, w, cloth: Cloth, ss: int, aa: float):
    """The warp-faced plain weave: (luma, height mm, knot coverage, glint coverage).

    Warp threads run along s at ``warp_pitch_mm``: a rounded body with dark gaps between.
    Weft picks cross at an irregular, wavering pitch.  At each crossing the weft is either
    OVER the warp (plain weave: every other crossing, with some irregularity) - the warp dives
    (a dark break) and a light weft bar shows across it - or UNDER, where the warp stays up.
    So each warp shows as FLOATS (lit dashes ~2 picks long, each its own brightness, a raised
    crown in the middle) broken by light cross bars: together, the net of the reference."""
    # ---------------------------------------------------------------- warp
    pitch = cloth.warp_pitch_mm * (1.0 + 0.035 * noise1(s / 6.0, ss + 1))
    wob = 0.022 * noise1(s / 1.3 + 0.41 * np.floor(w / 2.5), ss + 2) + 0.02 * fbm2(s / 2.7, w / 1.9, ss + 3, 2)
    u = (w + wob) / pitch
    iw = np.floor(u)
    x = u - iw
    dx = np.abs(x - 0.5) * pitch                 # distance to this thread's centre line
    streak = np.exp(cloth.rib_sigma * math.sqrt(2.0) * _erfinv(2 * _hash(iw, seed=ss + 5) - 1)
                    + 0.18 * noise1(s / 3.3 + 13.1 * iw, ss + 6))
    body = _line(dx, cloth.body_half_mm, aa)
    crown = _line(dx, cloth.crown_half_mm, aa)
    # ---------------------------------------------------------------- weft picks
    wp = cloth.weft_pitch_mm
    v = s / wp + cloth.weft_jitter * noise1(w / 0.9 + 3.7, ss + 13) + 0.12 * noise1(w / 0.33, ss + 14)
    jt = np.floor(v)
    y = v - jt
    dy = np.abs(y - 0.5) * wp                    # distance to the pick's centre line
    # plain weave: the weft is over this warp at this pick on alternate crossings (irregular)
    over = ((iw + jt) % 2 == 0) ^ (_hash(iw, jt, seed=ss + 15) < 0.18)
    shown = _hash(jt, np.floor((iw + 31 * _hash(jt, seed=ss + 20)) / cloth.weft_run), seed=ss + 16) < cloth.weft_prob
    wlum = 0.5 + 1.0 * _hash(jt, iw, seed=ss + 17)
    bar = _line(dy, cloth.weft_half_mm, aa)
    brk = _line(dy, cloth.break_half_mm, aa) * over
    # floats: the warp's lit stretch between two over-crossings, each its own brightness
    fid = np.floor((jt + (iw % 2)) / 2.0)
    fb = np.exp(cloth.float_sigma * math.sqrt(2.0) * _erfinv(2 * _hash(iw, fid, seed=ss + 7) - 1))
    fpos = ((v - 2 * fid - (iw % 2)) / 2.0)                 # 0..1 along the float
    fhi = cloth.float_end + (1 - cloth.float_end) * np.sin(np.pi * np.clip(fpos, 0, 1))
    # ---------------------------------------------------------------- crossings
    kd = np.sqrt(dx * dx + dy * dy)
    knot_here = (~over) & (_hash(jt, iw, seed=ss + 18) < cloth.knot_prob)
    knot = _line(kd, cloth.knot_r_mm, aa) * knot_here
    glint = _line(kd, cloth.knot_r_mm * 0.8, aa) * knot_here * (_hash(jt, iw, seed=ss + 19) < cloth.glint_prob)
    # ---------------------------------------------------------------- tone
    # the reference's persistent streaks (REFERENCE_SPEC 7: ~7 per 100 px across a strip,
    # i.e. every ~0.75 mm, 0.07 log): groups of warp threads a little lighter or darker,
    # running the whole length of the tape; plus a faint slow mottle
    sw = w / cloth.streak_pitch_mm
    streaks = np.exp(cloth.streak_log * (1.3 * noise1(sw + 0.02 * s, ss + 41) + 0.6 * noise1(2.3 * sw + 5.0, ss + 42)))
    mott = streaks * (1.0 + cloth.mottle * fbm2(s / 4.0, w / 3.0, ss + 4, 2))
    warp_lum = (cloth.body_lum * body + (cloth.crown_lum - cloth.body_lum) * crown * fhi) * streak * fb
    warp_lum = warp_lum * (1.0 - brk)
    lum = np.maximum(cloth.cell_lum, warp_lum)
    lum = np.maximum(lum, cloth.weft_lum * bar * wlum * np.where(over, 1.0, 0.45 * (1 - body)) * shown)
    lum = lum * mott
    lum = np.maximum(lum, cloth.knot_lum * knot * streak)
    lum = np.maximum(lum, cloth.glint_lum * glint)
    h = (cloth.rib_h_mm * (np.cos(np.pi * np.clip(dx / (0.5 * pitch), 0, 1)) * 0.5 + 0.5) * (1 - 0.7 * brk) * fhi
         + cloth.weft_h_mm * bar * over + cloth.knot_h_mm * knot)
    return lum, h, knot, glint


def fibres(s, w, cloth: Cloth, ss: int, aa: float):
    """Coverage (0..1) and gain of thin light curly fibres."""
    cell = cloth.fibre_cell_mm
    ci = np.floor(s / cell)
    cj = np.floor(w / cell)
    out = np.zeros_like(s)
    gain = np.zeros_like(s)
    half = 0.5 * cloth.fibre_width_mm
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            present = _hash(I, J, seed=ss) < cloth.fibre_per_cell
            cx = (I + _hash(I, J, seed=ss + 1)) * cell
            cy = (J + _hash(I, J, seed=ss + 2)) * cell
            L = cloth.fibre_len_mm[0] + (cloth.fibre_len_mm[1] - cloth.fibre_len_mm[0]) * _hash(I, J, seed=ss + 3) ** 1.5
            ang = _hash(I, J, seed=ss + 4) * np.pi
            kap = (_hash(I, J, seed=ss + 6) - 0.5) * cloth.fibre_curl  # curvature 1/mm
            ca, sa = np.cos(ang), np.sin(ang)
            px, py = s - cx, w - cy
            t = px * ca + py * sa
            n = -px * sa + py * ca
            tc = np.clip(t, -0.5 * L, 0.5 * L)
            nd = n - 0.5 * kap * tc * tc
            dist = np.sqrt(nd * nd + (t - tc) ** 2)
            g = cloth.fibre_gain[0] + (cloth.fibre_gain[1] - cloth.fibre_gain[0]) * _hash(I, J, seed=ss + 7)
            c = _line(dist, half, aa) * present
            better = c * g > out * np.maximum(gain, 1e-6)
            gain = np.where(better, g, gain)
            out = np.maximum(out, c)
    return out, gain


# =========================================================================== threads
#: REFERENCE_SPEC 6: the loose threads, image px of the reference view.  T1 / T2 hang from
#: W's rolled lower edge (their first point is ON the edge) and drape down over A.  T4 (the
#: hook past the outline at 155 deg) is modelled in props_lib.smokebomb_threads; its root on
#: the ball is drawn here.
THREADS_PX = {
    "T1": [[(801, 695), (804, 707), (799, 718), (802, 727), (799, 734), (797, 741)],
           [(801, 728), (806, 734), (808, 740)]],
    "T2": [[(936, 776), (934, 788), (935, 800), (932, 812)],
           [(935, 787), (940, 793), (942, 799)]],
    "T3": [[(368, 611), (371, 604), (377, 602), (382, 606), (380, 612)],
           [(376, 603), (379, 598)]],
    "T4": [[(197, 433), (193, 431)]],
    "T5": [[(989, 816), (990, 825)]],
}
THREAD_HALF_PX = {"T1": 2.0, "T2": 1.9, "T3": 1.1, "T4": 1.2, "T5": 1.3}
THREAD_TONE = {"T1": 1.0, "T2": 1.0, "T3": 0.75, "T4": 0.8, "T5": 0.85}


def _dist_to_polyline(q: np.ndarray, poly: np.ndarray):
    """Distance and the signed side (+ = left of travel in image px, i.e. the lit side)."""
    d = np.full(len(q), 1e9)
    side = np.zeros(len(q))
    for a, b in zip(poly[:-1], poly[1:]):
        ab = b - a
        t = np.clip(((q - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        c = a + t[:, None] * ab
        dd = np.linalg.norm(q - c, axis=1)
        cr = np.sign((q - a)[:, 0] * ab[1] - (q - a)[:, 1] * ab[0])
        better = dd < d
        side = np.where(better, cr, side)
        d = np.minimum(d, dd)
    return d, side


def thread_fields(P_cam: np.ndarray):
    """(core coverage, crown, shadow, tone) of the loose threads at front-facing points;
    distances in reference-image px (the threads are designed for the reference view)."""
    q = SS.cam_to_img(P_cam)
    front = P_cam[:, 2] > 0.05
    core = np.zeros(len(P_cam))
    hil = np.zeros(len(P_cam))
    shd = np.zeros(len(P_cam))
    tone = np.zeros(len(P_cam))
    if not front.any():
        return core, hil, shd, tone
    qf = q[front]
    c_ = np.zeros(len(qf)); h_ = np.zeros(len(qf)); s_ = np.zeros(len(qf)); t_ = np.zeros(len(qf))
    for name, polys in THREADS_PX.items():
        half = THREAD_HALF_PX[name]
        for pi, poly in enumerate(polys):
            P = np.asarray(poly, np.float64)
            hh = half * (0.8 if pi else 1.0)
            d, side = _dist_to_polyline(qf, P)
            cov = np.clip(hh + 0.5 - d, 0, 1)
            # the yarn is round: brightest along its middle
            cr = np.clip(1.0 - d / max(hh, 0.5), 0, 1) * cov
            # its shadow on the tape: down-left of it, soft
            dsh, _ = _dist_to_polyline(qf - np.array([-1.6, 2.2]), P)
            sh = np.clip(1.0 - dsh / (hh + 3.0), 0, 1) * (1 - cov)
            c_ = np.maximum(c_, cov)
            h_ = np.maximum(h_, cr)
            s_ = np.maximum(s_, sh * THREAD_TONE[name])
            t_ = np.where(cov > 0, np.maximum(t_, THREAD_TONE[name]), t_)
    core[front], hil[front], shd[front], tone[front] = c_, h_, s_, t_
    return core, hil, shd, tone


# =========================================================================== one island
def island_channels(model, k: int, S: np.ndarray, W: np.ndarray, ppmm: float, cloth: Cloth,
                    seed: int, near: Optional[List[int]] = None) -> Dict[str, np.ndarray]:
    """Base colour (linear RGB), roughness, height (mm) and cavity for a block of texels on
    strip k's chart (rows x cols, mm)."""
    st = model.strips[k]
    shape = S.shape
    s = S.ravel()
    w = W.ravel()
    P = st.chart_to_cam(s, w, 35.0)
    idx = list(range(len(model.strips))) if near is None else sorted(set(near) | {k})
    sub = [model.strips[i] for i in idx]
    f = SS.evaluate_field(sub, P, 35.0)
    kk = idx.index(k)
    d_own = f.d[kk]
    my_rank = f.rank[kk]
    higher = f.rank > my_rank[None, :]
    higher[kk] = False
    dcm = np.where(higher, f.d, -1e3)
    ic = np.argmax(dcm, axis=0)
    jj = np.arange(len(s))
    dc = dcm[ic, jj]                                      # >0 under a cover; <0 its distance away
    kc = np.asarray(idx)[ic].astype(np.float64)
    s_cov = f.s[ic, jj]
    out = texel_channels(s, w, P, d_own, dc, f.half_width[kk], k, ppmm, cloth, seed,
                         family=getattr(st, "family", ""), kc=kc, s_cov=s_cov)
    return {key: (v.reshape(shape + (3,)) if key == "base" else v.reshape(shape)) for key, v in out.items()}


def _cord(de, s_edge, k_edge, cloth: Cloth, seed: int, aa: float):
    """The rolled rim at signed distance ``de`` inside a (gently wandering) edge, along the
    edge owner's own chart coordinate ``s_edge`` (so both islands paint the same segments).
    The thread wraps pinch the cord into segments that bulge between them: the cord's outer
    line bulges with each segment (the reference's edge jitter at ~1 mm).  Returns luma,
    height (mm), the joint coverage and the effective distance inside the bulging outline."""
    r = cloth.cord_mm
    k_edge = np.asarray(k_edge, np.float64)
    ks = seed * 101 + 23
    lp = cloth.wrap_pitch_mm * (1 + 0.15 * noise1(s_edge / 2.9 + 17.0 * k_edge, ks + 21))
    lv0 = s_edge / lp + 0.25 * noise1(s_edge / 2.1 + 11.0 * k_edge, ks + 22)
    lj0 = np.floor(lv0)
    segb = 0.9 + 0.2 * _hash(k_edge, lj0, seed=ks + 24)
    seg0 = np.sin(np.pi * np.clip(lv0 - lj0, 0.0, 1.0))
    de = de + cloth.cord_bulge_mm * (seg0 * (0.6 + 0.8 * _hash(k_edge, lj0, seed=ks + 25)) - 0.55)
    xr = np.clip(de / r, 0.0, 1.0)
    prof = np.sqrt(np.clip(1.0 - (2 * xr - 1) ** 2, 0, 1))      # round cord
    lv = lv0 + cloth.wrap_lean * (xr - 0.5)
    lj = np.floor(lv)
    lf = lv - lj
    seg = np.sin(np.pi * np.clip(lf, 0.0, 1.0))
    joint = _line(np.minimum(lf, 1 - lf) * lp, cloth.joint_half_mm, aa)
    wrap = _line(np.abs(lf - 0.16) * lp, 0.03, aa) * (_hash(k_edge, lj, seed=ks + 23) < 0.55)
    lit = np.clip(1.0 - np.abs(xr - cloth.cord_lit_at) / 0.2, 0, 1) ** 1.5
    # the rim is the tape's own weave rolled over, brighter (REFERENCE_SPEC 5: 1.5 - 3x),
    # segmented by the wraps: returned as a GAIN on the weave plus a floor and the wraps
    gain = cloth.cord_gain * segb * (cloth.cord_body + (1 - cloth.cord_body) * lit) * (0.75 + 0.25 * seg)
    gain = gain * (1.0 - cloth.joint_dark * joint)
    floor = cloth.cord_lum * (0.5 + 0.5 * lit) * (0.75 + 0.25 * seg) * (1.0 - cloth.joint_dark * joint)
    wr = cloth.wrap_lum * wrap * prof
    h = cloth.cord_h_mm * prof * (0.9 + 0.1 * seg) - 0.04 * joint * prof
    return (gain, floor, wr), h, joint, de


def texel_channels(s, w, P, d_own, dc, half_width, k: int, ppmm: float, cloth: Cloth, seed: int,
                   family: str = "", threads: bool = True, kc=None, s_cov=None) -> Dict[str, np.ndarray]:
    """The cloth at texels (s, w) of strip k, given the distance to its own edge (``d_own``,
    + inside) and to the nearest covering strip's edge (``dc``, + under the cover)."""
    ss = seed * 101 + k * 7919
    aa = 0.55 / ppmm
    # ---------------------------------------------------------------- the net
    lum, h, knot, glint = weave(s, w, cloth, ss, aa)
    fc, fg = fibres(s, w, cloth, ss + 50, aa)
    # ---------------------------------------------------------------- the edges, frayed
    # ONE fray field on the ball: the cord of an upper strip wanders across its geometric
    # step, painted on its own island where it pulls in and on the island beneath where it
    # overhangs, both from the same point function and the upper strip's own chart
    fray = fray_field(P, cloth, seed + 12)
    r = cloth.cord_mm
    de_o = d_own + fray                                    # inside the OWN frayed edge
    de_c = dc + fray if dc is not None else np.full_like(s, -1e3)   # inside a COVER's frayed edge
    kc_ = np.full_like(s, k) if kc is None else kc
    sc_ = s if s_cov is None else s_cov
    cl_o, ch_o, jo_o, de_o = _cord(de_o, s, np.full_like(s, k), cloth, seed, aa)
    cl_c, ch_c, jo_c, de_c = _cord(de_c, sc_, kc_, cloth, seed, aa)
    wall = (d_own < -0.015) & (de_o < 0.0)                 # the tape's side, not overhung by its cord
    in_o = (de_o >= 0.0) & (de_o < r)
    in_c = (dc < 0.0) & (de_c >= 0.0) & (de_c < r)
    eaten = (d_own >= 0.0) & (de_o < 0.0)                 # the frayed edge is inside the step
    lum_o = np.maximum(lum * cl_o[0] + cl_o[1], cl_o[2])
    lum_c = np.maximum(lum * cl_c[0] + cl_c[1], cl_c[2])
    lum = np.where(in_o, lum_o, lum)
    lum = np.where(in_c & ~in_o, lum_c, lum)
    # the groove between a cord and its tape body
    grv = np.clip(1.0 - np.abs(de_o - r) / 0.09, 0, 1) * (d_own >= 0.0)
    lum = lum * (1.0 - cloth.groove_dark * grv)
    lum = np.where(eaten & ~in_c, cloth.wall_lum * (0.7 + 0.6 * _hash(np.floor(s * 12), np.floor(w * 12), seed=ss + 25)), lum)
    # the tape's side: dark dyed cloth seen end-on, lighter just under the cord
    wz = np.clip(-d_own, 0, 3.0)
    # the upper part of the wall is the rolled cord seen from the side (it continues the
    # cord's segments), fading to the dark tape side lower down
    wt = np.clip(wz / cloth.wall_round_w_mm, 0.0, 1.0)
    wall_tone = (cloth.wall_top_lum * (1.0 - wt) ** 1.5
                 + cloth.wall_lum * (0.8 + 0.4 * _hash(np.floor(s * 9), seed=ss + 26)))
    lum = np.where(wall & ~in_c, wall_tone, lum)
    # ---------------------------------------------------------------- the strip beneath a cover
    beyond = -de_c                                         # distance BEYOND a covering frayed edge
    near_c = (dc < 0.015) & (beyond > 0.0)
    crev = _smooth((cloth.crevice_mm - beyond) / (0.6 * cloth.crevice_mm)) * near_c   # a plateau, then a ramp
    occ = np.clip(1.0 - beyond / cloth.occl_w_mm, 0.0, 1.0) * near_c
    shade = (1.0 - cloth.crevice_dark * crev) * (1.0 - cloth.occl_dark * occ ** cloth.occl_pow)
    # the shingle: each strip brightens toward its own exposed, rolled edge (the reference's
    # saw-tooth tone across the fan: dark where a strip runs under its neighbour, light at
    # its own rim)
    tb = np.clip(1.0 - (de_o - r) / cloth.boost_w_mm, 0.0, 1.0) * (de_o >= r) * (1.0 - occ)
    shade = shade * (1.0 + cloth.rim_boost * tb ** 1.5)
    lum = lum * shade
    # the crevice's core: a solid dark slit right under the overhang (the reference's
    # darkest pixels are these continuous lines, not the weave's cells)
    core = np.clip(1.0 - beyond / cloth.core_w_mm, 0.0, 1.0) * near_c
    core = core * (0.75 + 0.25 * noise1(sc_ / 0.9 + 5.3 * kc_, seed + 27))
    lum = lum * (1.0 - core) + cloth.core_lum * core
    # a few loose fibre loops of the upper edge hanging over the shadow
    fzc = _hash(kc_, np.floor(sc_ * 6.0), seed=seed + 18) < cloth.fringe_prob
    fz = _line(np.abs(beyond - 0.12 * (0.5 + _hash(kc_, np.floor(sc_ * 6.0), seed=seed + 19))), 0.03, aa) * fzc * near_c
    lum = lum * (1 - fz) + cloth.fringe_lum * fz
    # ---------------------------------------------------------------- colour
    var = 1.0 + cloth.strip_variation * (2 * _hash(np.array([k]), seed=seed + 99)[0] - 1)
    tint = np.asarray(cloth.dye) / (0.2126 * cloth.dye[0] + 0.7152 * cloth.dye[1] + 0.0722 * cloth.dye[2])
    cm_r = cloth.chroma_mottle * (0.6 * fbm2(s / 1.3 + 7.1, w / 1.1, ss + 31, 2) + 0.6 * fbm2(s / 5.0 + 1.7, w / 4.0, ss + 33, 2))
    cm_b = cloth.chroma_mottle * (0.6 * fbm2(s / 1.2 + 3.3, w / 1.3, ss + 32, 2) + 0.6 * fbm2(s / 4.6 + 9.1, w / 4.4, ss + 34, 2))
    tintp = np.stack([tint[0] * (1 + cm_r), tint[1] * np.ones_like(cm_r), tint[2] * (1 + cm_b)], axis=1)
    base = tintp * (lum * var)[:, None]
    fib = np.clip(fc * fg, 0, 1) * np.where(wall | eaten | in_o | in_c, 0.4, 1.0)
    fcol = np.asarray(cloth.fibre)[None, :] * (0.7 + 0.5 * _hash(np.floor(s * 7), np.floor(w * 7), seed=ss + 17))[:, None]
    glint_mask = np.clip(glint, 0, 1) * ~wall
    light = np.clip(fib, 0.0, 1.0)
    # fibres and glints lying in a crevice or under an overhang are in its shadow too
    fshade = ((1.0 - cloth.crevice_dark * crev) * (1.0 - core) * (1.0 - cloth.occl_dark * occ ** cloth.occl_pow))[:, None]
    base = base * (1 - light[:, None]) + fcol * cloth.fibre_tone * light[:, None] * fshade
    base = base * (1 - glint_mask[:, None]) + (np.asarray(cloth.fibre)[None, :] * cloth.glint_lum / 0.58) * glint_mask[:, None] * fshade
    # ---------------------------------------------------------------- loose threads
    if threads:
        tc, th, tsh, tt = thread_fields(P)
    else:
        tc = th = tsh = tt = np.zeros(len(s))
    tcore = tc * (~wall)
    base = base * (1.0 - 0.6 * tsh[:, None])
    tcol = np.asarray(cloth.fibre)[None, :] * (cloth.thread_lum / 0.58) * (0.45 + 0.55 * th)[:, None] * tt[:, None]
    base = base * (1 - tcore[:, None]) + tcol * tcore[:, None]
    # ---------------------------------------------------------------- height (normal map), mm
    # the padded tape: rolls down toward both edges; pressed flat where an upper strip lies
    hw = np.maximum(half_width, 0.5)
    reach = np.minimum(cloth.pad_reach_mm, hw)
    # the tape rolls over toward its own edge: a parabolic shoulder
    tpad = np.clip(np.clip(de_o, 0, None) / reach, 0, 1)
    pad = cloth.pad_mm * (1.0 - (1.0 - tpad) ** 2) ** cloth.pad_shape
    # ... and dips toward a covering strip's edge, where it runs under it
    dipt = np.clip(1.0 - np.clip(beyond, 0, None) / cloth.dip_w_mm, 0, 1) * (dc < 0.015)
    padh = pad - cloth.dip_mm * dipt ** 2
    h = h + padh
    h = np.where(in_o, padh + ch_o * cloth.cord_relief, h)
    h = np.where(in_c & ~in_o, ch_c * cloth.cord_relief + 0.02, h)
    h = h - cloth.groove_mm * crev
    # the wall rolls: its shading normal turns from the tape's top (at the rim) to the wall's
    # own (lower down), so the tape reads as a padded tube, not a cut sheet
    hw_ = cloth.wall_round_mm * (1.0 - (1.0 - wt) ** 2)
    h = np.where(wall & ~in_c, hw_, h)
    h = np.where(eaten & ~in_c, -0.03, h)
    h = h + 0.05 * tcore * (0.5 + 0.5 * th)
    # ---------------------------------------------------------------- roughness
    rough = cloth.roughness + cloth.rough_var * fbm2(s / 1.7, w / 1.7, ss + 41, 2)
    rough = rough * (1 - np.maximum(light, glint_mask)) + cloth.fibre_roughness * np.maximum(light, glint_mask)
    rough = np.where(in_o | in_c, rough - 0.04, rough)
    rough = rough * (1 - tcore) + 0.78 * tcore
    cav = (1.0 - 0.35 * crev) * (1.0 - 0.2 * occ)
    return {"base": base, "rough": rough, "height": h, "cavity": cav}


# =========================================================================== the atlas
def near_strips(model, k: int, S: np.ndarray, W: np.ndarray, reach_mm: float = 4.0) -> List[int]:
    """Strips that come within ``reach_mm`` of this block (checked on a coarse sample)."""
    st = model.strips[k]
    ys = np.linspace(0, S.shape[0] - 1, min(S.shape[0], 12)).astype(int)
    xs = np.linspace(0, S.shape[1] - 1, min(S.shape[1], 40)).astype(int)
    P = st.chart_to_cam(S[np.ix_(ys, xs)].ravel(), W[np.ix_(ys, xs)].ravel(), 35.0)
    out = [k]
    for i, other in enumerate(model.strips):
        if i == k:
            continue
        if (other.evaluate(P, 35.0)["d"] > -reach_mm - 3.0).any():
            out.append(i)
    return out


def paint_atlas(model, atlas, pieces, cloth: Cloth, seed: int, log=print) -> Dict[str, np.ndarray]:
    size = atlas.size
    base = np.zeros((size, size, 3), np.float32)
    rough = np.full((size, size), cloth.roughness, np.float32)
    height = np.zeros((size, size), np.float32)
    cav = np.ones((size, size), np.float32)
    written = np.zeros((size, size), bool)
    from .smokebomb_atlas import piece_key
    for p in pieces:
        key = piece_key(p)
        x0, y0, bw, bh = atlas.block(key)
        isl = atlas.islands[key]
        if getattr(p, "is_thread", False):
            # a loose thread's own island (props_lib.smokebomb_threads): the tape's yarn, a
            # light twisted fibre - its twist shows as faint stripes along it
            ys = slice(max(y0, 0), min(y0 + bh, size))
            xs = slice(max(x0, 0), min(x0 + bw, size))
            yy, xx = np.mgrid[ys, xs]
            u = (xx - isl.x0) / atlas.ppmm
            v = (isl.y0 - yy) / atlas.ppmm
            twist = 0.8 + 0.2 * np.sin(2 * np.pi * (u / 0.35 + v / 0.25))
            base[ys, xs] = (np.asarray(cloth.fibre) * (cloth.thread_lum / 0.58))[None, None, :] * twist[..., None]
            rough[ys, xs] = 0.78
            height[ys, xs] = 0.0
            cav[ys, xs] = 1.0
            written[ys, xs] = True
            continue
        px = x0 + np.arange(bw) + 0.5
        py = y0 + np.arange(bh) + 0.5
        s = isl.s0 + (px - isl.x0) / atlas.ppmm
        w = isl.w1 - (py - isl.y0) / atlas.ppmm
        S, W = np.meshgrid(s, w)
        near = near_strips(model, p.strip, S, W)
        # rows in chunks: bounded memory on the big islands
        for r0 in range(0, bh, 256):
            r1 = min(bh, r0 + 256)
            ch = island_channels(model, p.strip, S[r0:r1], W[r0:r1], atlas.ppmm, cloth, seed, near)
            yy0 = y0 + r0
            ys = slice(max(yy0, 0), min(y0 + r1, size))
            xs = slice(max(x0, 0), min(x0 + bw, size))
            if ys.stop <= ys.start or xs.stop <= xs.start:
                continue
            oy, ox = ys.start - yy0, xs.start - x0
            hh, ww = ys.stop - ys.start, xs.stop - xs.start
            base[ys, xs] = ch["base"][oy:oy + hh, ox:ox + ww]
            rough[ys, xs] = ch["rough"][oy:oy + hh, ox:ox + ww]
            height[ys, xs] = ch["height"][oy:oy + hh, ox:ox + ww]
            cav[ys, xs] = ch["cavity"][oy:oy + hh, ox:ox + ww]
            written[ys, xs] = True
    if (~written).any():
        base[~written] = base[written].mean(axis=0)
    return {"base": base, "rough": rough, "height": height, "cavity": cav, "written": written}


def normals_from_height(height: np.ndarray, ppmm: float, strength: float = 1.0) -> np.ndarray:
    """Tangent-space normals (OpenGL: +x = +u, +y = +v) from a height map in mm.
    The atlas image is top-down and +v is UP the image, so d/dv = -d/drow."""
    h = height.astype(np.float64)
    dx = np.zeros_like(h)
    dy = np.zeros_like(h)
    dx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * 0.5 * ppmm
    dy[1:-1, :] = -(h[2:, :] - h[:-2, :]) * 0.5 * ppmm
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n


__all__ = ["Cloth", "THREADS_PX", "paint_atlas", "island_channels", "normals_from_height",
           "thread_fields", "noise1", "noise2", "fbm2", "weave", "fibres"]
