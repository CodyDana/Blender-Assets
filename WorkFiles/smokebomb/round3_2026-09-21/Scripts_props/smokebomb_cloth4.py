#!/usr/bin/env python
"""props_lib.smokebomb_cloth4 - the woven tape, drawn straight into the atlas (round 4).

numpy only.  Same contract as round 3's props_lib.smokebomb_cloth (which stays in the
package, unchanged, and whose noise helpers this module imports): every texel of every
island is a point of one strip's chart (s along the tape, w across it, mm), the cloth is
evaluated where it lives, and no reference pixel is ever read.

WHY ROUND 4 REWROTE THE WEAVE
-----------------------------
The round-3 blind judge picked our render out of 19 of 19 pairs, first on the weave: a
regular net of thin bright warp and weft lines with evenly spaced round dot glints ("graph
paper", "window screen", "hessian").  The cause was structural: the weft picks were one
coordinate for every warp thread, so every dark break and every light weft bar lined up
across the tape and drew a lattice, and every glint sat on a lattice crossing.  At 5x the
reference shows no lattice at all:

    ribs        warp-faced: rounded warp cords along the tape, 0.30 mm apart (4 px), each
                its own width (spacing jitter ~ +-25 %) and wandering gently; thin dark gaps
                between them.  The rib's rounded relief is most of the texture's contrast.
    floats      along each rib the brightness breaks into floats of random length
                (0.15 - 0.5 mm), each its own tone, with a short dark dip where the warp
                dives under a weft pick.  Every thread has its OWN float positions, so no
                two neighbouring dips line up: nothing forms a grid.
    weft peeks  in some dips a short light cross dash shows (one thread wide), scattered.
    fibres      short bright warm fibres, mostly lying along the warp, some curled into
                hooks and C shapes - the reference's "sparkle" is these, not dots on a grid.
    specks      a sparse scatter of tiny bright points at random positions.
    padded tape the tape's cross-section is a flat tube: the normal map rolls it down over
                the outer third of each half-width, so a band shades across its width.

THE ROLLED EDGE (the second give-away)
--------------------------------------
Round 3's rim was a soft 0.55 mm grey lip.  The reference's exposed edge is a crisp CORD,
~0.35 mm across, bright on its crown, pinched every ~0.65 mm by thread-wrap knuckles
(dark joints, bulging segments), with a thin dark groove just inside it and a very dark
crevice just beyond it on the strip beneath (REFERENCE_SPEC 5; adversary r3: rim +0.65 -
0.85 log over the band median, crevice to -1.9 log at R_in).  The tape's side (the
geometric wall, unfolded onto its island) is the cord's underside: bright for its top
0.14 mm, then near-black.

THREADS
-------
T1 / T2 (REFERENCE_SPEC 6) are two or three thin curly warm-tan fibres each, splitting
toward the tip, hung from W's cord with a soft shadow - not one round grey tube.

NOT HERE: no slubs (REFERENCE_SPEC 7: "none resolvable; do not add"), no dirt, grime,
fading, burnish, stains or scorch.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import smokebomb_strips as SS
from .smokebomb_cloth import (_hash, noise1, noise2, noise3, fbm2, _erfinv, _line, _smooth,
                              _dist_to_polyline, near_strips, normals_from_height)


@dataclass
class Cloth4:
    #: the dye's chroma (luma is set by the tones below): REFERENCE_SPEC 8
    dye: Tuple[float, float, float] = (0.0504, 0.0415, 0.0374)
    #: fibres, specks, threads: warm tan (adversary r3: the reference's bright-pixel chroma
    #: 0.389 / 0.332 / 0.279)
    fibre_rgb: Tuple[float, float, float] = (0.389, 0.332, 0.279)
    gain: float = 0.9                  # one calibration factor on every tone below
    # ------------------------------------------------------------- warp ribs
    warp_pitch_mm: float = 0.30
    pitch_jitter: float = 0.40         # thread-unit amplitude of the spacing warp (< 0.6: monotone)
    wander: float = 0.45               # thread-unit lateral wander ...
    wander_len_mm: float = 2.6         # ... over this length
    rib_lum: float = 0.050
    gap_lum: float = 0.002
    rib_shape: float = 1.6
    thread_sigma: float = 0.22
    float_len_mm: float = 0.34
    float_len_var: float = 0.35
    float_sigma: float = 0.30
    float_hump: float = 0.45
    dive_prob: float = 0.8
    dive_half_mm: float = 0.05
    dive_dark: float = 0.85
    peek_prob: float = 0.25
    peek_lum: float = 0.12
    peek_half_mm: float = 0.04
    streak_pitch_mm: float = 0.75
    streak_log: float = 0.14
    mottle: float = 0.07
    chroma_mottle: float = 0.10
    # ------------------------------------------------------------- fibres and specks
    fibre_cell_mm: float = 0.55
    fibre_per_cell: float = 0.12
    fibre_len_mm: Tuple[float, float] = (0.12, 0.60)
    fibre_half_mm: float = 0.026
    fibre_along_share: float = 0.80
    fibre_along_sigma: float = 0.30
    fibre_curl: float = 6.0
    fibre_lum: Tuple[float, float] = (0.30, 0.80)
    tick_cell_mm: float = 0.60
    tick_prob: float = 0.10
    tick_len_mm: Tuple[float, float] = (0.15, 0.45)
    tick_half_mm: float = 0.028
    tick_sigma: float = 0.22
    tick_curl: float = 1.5
    tick_lum: Tuple[float, float] = (0.22, 0.50)
    speck_cell_mm: float = 0.30
    speck_prob: float = 0.14
    speck_r_mm: float = 0.035
    speck_lum: float = 1.0
    # ------------------------------------------------------------- relief (normal map), mm
    rib_h_mm: float = 0.08
    fibre_h_mm: float = 0.02
    peek_h_mm: float = 0.02
    pad_mm: float = 0.90               # the padded cross-section: drop at the tape's edge ...
    pad_power: float = 2.0             # ... flat in the middle, rolling over the outer part
    edge_roll_mm: float = 0.12         # a little more roll within this of an exposed edge ...
    edge_roll_w_mm: float = 0.9
    dip_mm: float = 0.25               # the tape beneath dips toward a covering edge ...
    dip_w_mm: float = 1.3
    # ------------------------------------------------------------- the rolled cord
    cord_mm: float = 0.40
    cord_h_mm: float = 0.15
    cord_lum: float = 0.24            # crown albedo
    cord_flank: float = 0.40           # tone of the cord's flanks relative to the crown
    cord_lit_at: float = 0.58          # 0 at the edge .. 1 inner side
    knuckle_pitch_mm: float = 0.66
    knuckle_jitter: float = 0.14
    knuckle_half_mm: float = 0.05
    knuckle_dark: float = 0.85
    wrap_lum: float = 0.30
    wrap_prob: float = 0.6
    cord_weave: float = 0.35           # the cord keeps this share of the weave's own texture
    groove_w_mm: float = 0.07
    groove_mul: float = 0.40
    fray_rms_mm: float = 0.07
    fray_wavelength_mm: float = 0.65
    cord_bulge_mm: float = 0.05
    # ------------------------------------------------------------- the strip beneath a cover
    core_w_mm: float = 0.18
    core_lum: float = 0.0006
    crevice_mm: float = 0.60
    crevice_dark: float = 0.80
    occl_w_mm: float = 1.8
    occl_dark: float = 0.55
    occl_pow: float = 1.6
    edge_fibre_cell_mm: float = 0.22
    edge_fibre_prob: float = 0.30
    edge_fibre_len_mm: Tuple[float, float] = (0.08, 0.30)
    edge_fibre_lum: float = 0.08
    # ------------------------------------------------------------- the tape's side (walls)
    wall_top_mm: float = 0.14
    wall_lum: float = 0.002
    wall_round_mm: float = 0.25
    wall_round_w_mm: float = 0.35
    # ------------------------------------------------------------- material
    roughness: float = 0.88
    rough_var: float = 0.05
    fibre_roughness: float = 0.74
    strip_variation: float = 0.02
    # ------------------------------------------------------------- loose threads
    thread_lum: float = 0.40


# =========================================================================== noise helpers
def fray_field(P_cam: np.ndarray, c: Cloth4, seed: int) -> np.ndarray:
    """The frayed edge's wander (mm), a function of the POINT ON THE BALL, so an upper
    strip's cord and the crevice on the strip beneath wander together."""
    q = P_cam * (35.0 / c.fray_wavelength_mm)
    return c.fray_rms_mm / 0.473 * (1.2 * noise3(q, seed) + 0.25 * noise3(q * 2.7, seed + 1))


def _gauss(u):
    return math.sqrt(2.0) * _erfinv(2.0 * u - 1.0)


# =========================================================================== the weave
def weave(s, w, c: Cloth4, ss: int, aa: float):
    """Warp-faced ribs with per-thread floats: (albedo luma, height mm, fibre-ish light
    coverage for roughness, cavity)."""
    p = c.warp_pitch_mm
    # thread coordinate: a monotone warp of w (spacing jitter) plus a smooth wander along s
    g = w / p
    g = g + c.pitch_jitter * noise1(g * 0.5 + 3.1, ss + 1)
    g = g + c.wander * noise2(s / c.wander_len_mm, g / 9.0, ss + 2)
    iw = np.floor(g)
    x = g - iw                                            # 0..1 across the thread
    prof = np.sin(np.pi * x) ** c.rib_shape               # rounded cord, dark gap at 0 / 1
    # per-thread tone (the reference's persistent streaks) and the grouped streaks
    th_tone = np.exp(c.thread_sigma * _gauss(_hash(iw, seed=ss + 5)))
    sw = w / c.streak_pitch_mm
    streaks = np.exp(c.streak_log * (1.3 * noise1(sw + 0.02 * s, ss + 41) + 0.6 * noise1(2.3 * sw + 5.0, ss + 42)))
    # floats: plain weave - the warp dives under a weft pick every ``float_len_mm``, the
    # neighbouring thread half a pick out of step (the brick of short floats the reference
    # shows), each thread drifting on its own (so the bricks never line up into a lattice)
    # and some dives missing (longer floats)
    fl = c.float_len_mm
    v = (s / fl + 0.5 * (iw % 2) + 0.3 * (_hash(iw, seed=ss + 6) - 0.5)
         + c.float_len_var * noise1(s / 1.3 + 7.3 * iw, ss + 7))
    fid = np.floor(v)
    fpos = v - fid
    bnd = np.round(v)                                     # the nearest pick boundary
    fb = np.exp(c.float_sigma * _gauss(_hash(iw, fid, seed=ss + 8)))
    hump = np.sin(np.pi * fpos) ** 0.8
    dives = _hash(iw, bnd, seed=ss + 9) < c.dive_prob
    dd = np.abs(v - bnd) * fl
    dive = _line(dd, c.dive_half_mm, aa) * dives
    # in some dips a light weft dash shows across this one thread
    peek = dive * (_hash(iw, bnd, seed=ss + 10) < c.peek_prob) * _line(np.abs(x - 0.5) * p, 0.5 * p * 0.9, aa)
    peek = peek * _line(dd, c.peek_half_mm, aa)
    tone = c.gap_lum + (c.rib_lum - c.gap_lum) * prof * ((1.0 - c.float_hump) + c.float_hump * hump)
    tone = tone * fb * th_tone * streaks
    tone = tone * (1.0 - c.dive_dark * dive * (1.0 - peek))
    tone = np.maximum(tone, c.peek_lum * peek * (0.7 + 0.6 * _hash(iw, fid, seed=ss + 11)))
    tone = tone * (1.0 + c.mottle * fbm2(s / 4.0, w / 3.0, ss + 4, 2))
    h = (c.rib_h_mm * prof * (0.6 + 0.4 * hump) * (1.0 - 0.85 * dive)
         + c.peek_h_mm * peek)
    cav = 0.55 + 0.45 * prof
    return tone, h, cav


def fibres(s, w, c: Cloth4, ss: int, aa: float):
    """Short bright fibres: coverage and brightness.  Mostly along the warp, some curled."""
    cell = c.fibre_cell_mm
    ci = np.floor(s / cell)
    cj = np.floor(w / cell)
    cov = np.zeros_like(s)
    lum = np.zeros_like(s)
    half = c.fibre_half_mm
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            present = _hash(I, J, seed=ss) < c.fibre_per_cell
            cx = (I + _hash(I, J, seed=ss + 1)) * cell
            cy = (J + _hash(I, J, seed=ss + 2)) * cell
            L = c.fibre_len_mm[0] + (c.fibre_len_mm[1] - c.fibre_len_mm[0]) * _hash(I, J, seed=ss + 3) ** 1.6
            along = _hash(I, J, seed=ss + 12) < c.fibre_along_share
            ang = np.where(along, c.fibre_along_sigma * _gauss(_hash(I, J, seed=ss + 4)),
                           _hash(I, J, seed=ss + 13) * np.pi)
            kap = (_hash(I, J, seed=ss + 6) - 0.5) * 2.0 * c.fibre_curl * np.where(along, 0.35, 1.0)
            ca, sa = np.cos(ang), np.sin(ang)
            px, py = s - cx, w - cy
            t = px * ca + py * sa
            n = -px * sa + py * ca
            tc = np.clip(t, -0.5 * L, 0.5 * L)
            nd = n - 0.5 * kap * tc * tc
            dist = np.sqrt(nd * nd + (t - tc) ** 2)
            g = c.fibre_lum[0] + (c.fibre_lum[1] - c.fibre_lum[0]) * _hash(I, J, seed=ss + 7)
            # a fibre is brightest in its middle, fading at the ends where it tucks in
            fade = 0.55 + 0.45 * np.cos(np.pi * np.clip(t / np.maximum(0.5 * L, 1e-6), -1, 1)) ** 2
            cv = _line(dist, half, aa) * present
            better = cv * g * fade > cov * np.maximum(lum, 1e-9)
            lum = np.where(better, g * fade, lum)
            cov = np.maximum(cov, cv)
    return cov, lum


def ticks(s, w, c: Cloth4, ss: int, aa: float):
    """Short light weft dashes ACROSS the ribs (one to three threads long), scattered with
    no period: where the weft floats over the warp.  Coverage and brightness."""
    cell = c.tick_cell_mm
    ci = np.floor(s / cell)
    cj = np.floor(w / cell)
    cov = np.zeros_like(s)
    lum = np.zeros_like(s)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            present = _hash(I, J, seed=ss) < c.tick_prob
            cx = (I + _hash(I, J, seed=ss + 1)) * cell
            cy = (J + _hash(I, J, seed=ss + 2)) * cell
            L = c.tick_len_mm[0] + (c.tick_len_mm[1] - c.tick_len_mm[0]) * _hash(I, J, seed=ss + 3)
            ang = 0.5 * np.pi + c.tick_sigma * _gauss(_hash(I, J, seed=ss + 4))
            kap = (_hash(I, J, seed=ss + 6) - 0.5) * 2.0 * c.tick_curl
            ca, sa = np.cos(ang), np.sin(ang)
            px, py = s - cx, w - cy
            t = px * ca + py * sa
            n = -px * sa + py * ca
            tc = np.clip(t, -0.5 * L, 0.5 * L)
            nd = n - 0.5 * kap * tc * tc
            dist = np.sqrt(nd * nd + (t - tc) ** 2)
            g = c.tick_lum[0] + (c.tick_lum[1] - c.tick_lum[0]) * _hash(I, J, seed=ss + 7)
            cv = _line(dist, c.tick_half_mm, aa) * present
            better = cv * g > cov * np.maximum(lum, 1e-9)
            lum = np.where(better, g, lum)
            cov = np.maximum(cov, cv)
    return cov, lum


def specks(s, w, c: Cloth4, ss: int, aa: float):
    cell = c.speck_cell_mm
    I = np.floor(s / cell)
    J = np.floor(w / cell)
    r = c.speck_r_mm
    present = _hash(I, J, seed=ss) < c.speck_prob
    cx = (I + r / cell + (1 - 2 * r / cell) * _hash(I, J, seed=ss + 1)) * cell
    cy = (J + r / cell + (1 - 2 * r / cell) * _hash(I, J, seed=ss + 2)) * cell
    d = np.hypot(s - cx, w - cy)
    g = 0.6 + 0.8 * _hash(I, J, seed=ss + 3)
    return _line(d, r, aa) * present, g


# =========================================================================== threads
#: REFERENCE_SPEC 6's loose threads, reference-view image px (DESIGNED strands through the
#: spec's end points).  T1 / T2 hang from W's cord (their first point is ON the edge) and
#: drape over A as two or three curly strands that split toward the tip.  T3 is a curl on A,
#: T5 a stub; T4 (the hook past the outline) is geometry (smokebomb_threads), its root here.
THREADS_PX = {
    "T1": [[(801, 697), (803, 704), (800, 711), (802, 719), (799, 727), (798, 734), (797, 741)],
           [(803, 704), (806, 711), (808, 719), (806, 727), (809, 734)],
           [(800, 715), (796, 721), (797, 728), (794, 733)]],
    "T2": [[(936, 778), (935, 786), (936, 794), (934, 803), (932, 812)],
           [(935, 788), (939, 794), (942, 800), (940, 806)]],
    "T3": [[(368, 611), (371, 604), (377, 602), (382, 606), (380, 612)],
           [(376, 603), (379, 598)]],
    "T4": [[(197, 433), (193, 431)]],
    "T5": [[(989, 817), (990, 825)]],
}
THREAD_HALF_PX = {"T1": 1.0, "T2": 0.95, "T3": 0.8, "T4": 0.9, "T5": 0.9}
THREAD_TONE = {"T1": 1.0, "T2": 0.95, "T3": 0.75, "T4": 0.8, "T5": 0.85}


def thread_fields(P_cam: np.ndarray):
    """(coverage, crown, shadow, tone) of the loose threads at front-facing points
    (reference-view px; the threads are designed for the reference view)."""
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
            hh = half * (0.85 if pi else 1.0)
            d, _ = _dist_to_polyline(qf, P)
            cov = np.clip(hh + 0.5 - d, 0, 1)
            cr = np.clip(1.0 - d / max(hh, 0.5), 0, 1) * cov
            dsh, _ = _dist_to_polyline(qf - np.array([-1.2, 1.8]), P)
            sh = np.clip(1.0 - dsh / (hh + 1.8), 0, 1) * (1 - cov)
            c_ = np.maximum(c_, cov)
            h_ = np.maximum(h_, cr)
            s_ = np.maximum(s_, sh * THREAD_TONE[name])
            t_ = np.where(cov > 0, np.maximum(t_, THREAD_TONE[name]), t_)
    core[front], hil[front], shd[front], tone[front] = c_, h_, s_, t_
    return core, hil, shd, tone


# =========================================================================== the cord
def _cord(de, s_edge, k_edge, c: Cloth4, seed: int, aa: float):
    """The rolled cord at distance ``de`` inside a frayed edge, along the edge owner's own
    chart coordinate ``s_edge`` (both islands paint the same knuckles).  Returns
    (crown tone, weave share, height mm, effective distance inside the bulging outline)."""
    r = c.cord_mm
    k_edge = np.asarray(k_edge, np.float64)
    ks = seed * 101 + 23
    lp = c.knuckle_pitch_mm * (1.0 + c.knuckle_jitter * noise1(s_edge / 2.3 + 17.0 * k_edge, ks + 21))
    lv = s_edge / lp + 0.2 * noise1(s_edge / 1.9 + 11.0 * k_edge, ks + 22)
    lj = np.floor(lv)
    lf = lv - lj
    seg = np.sin(np.pi * lf)
    de = de + c.cord_bulge_mm * (seg * (0.6 + 0.8 * _hash(k_edge, lj, seed=ks + 25)) - 0.55)
    xr = np.clip(de / r, 0.0, 1.0)
    prof = np.sqrt(np.clip(1.0 - (2.0 * xr - 1.0) ** 2, 0.0, 1.0))
    lit = np.clip(1.0 - np.abs(xr - c.cord_lit_at) / 0.3, 0.0, 1.0) ** 1.3
    knuck = _line(np.minimum(lf, 1.0 - lf) * lp, c.knuckle_half_mm, aa)
    wrap = _line(np.abs(lf - 0.18 - 0.1 * (xr - 0.5)) * lp, 0.025, aa) * (_hash(k_edge, lj, seed=ks + 23) < c.wrap_prob)
    segb = 0.85 + 0.3 * _hash(k_edge, lj, seed=ks + 24)
    crown = c.cord_lum * segb * (c.cord_flank + (1.0 - c.cord_flank) * lit) * (0.7 + 0.3 * seg)
    crown = crown * (1.0 - c.knuckle_dark * knuck)
    crown = np.maximum(crown, c.wrap_lum * wrap * prof)
    h = c.cord_h_mm * prof * (0.85 + 0.15 * seg) - 0.05 * knuck * prof
    return crown, h, knuck, de


# =========================================================================== one block
def island_channels(model, k: int, S: np.ndarray, W: np.ndarray, ppmm: float, c: Cloth4,
                    seed: int, near: Optional[List[int]] = None) -> Dict[str, np.ndarray]:
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
    higher = f.rank > f.rank[kk][None, :]
    higher[kk] = False
    dcm = np.where(higher, f.d, -1e3)
    ic = np.argmax(dcm, axis=0)
    jj = np.arange(len(s))
    dc = dcm[ic, jj]
    kc = np.asarray(idx)[ic].astype(np.float64)
    s_cov = f.s[ic, jj]
    out = texel_channels(s, w, P, d_own, dc, f.half_width[kk], k, ppmm, c, seed, kc=kc, s_cov=s_cov)
    return {key: (v.reshape(shape + (3,)) if key == "base" else v.reshape(shape)) for key, v in out.items()}


def texel_channels(s, w, P, d_own, dc, half_width, k: int, ppmm: float, c: Cloth4, seed: int,
                   threads: bool = True, kc=None, s_cov=None) -> Dict[str, np.ndarray]:
    """The cloth at texels (s, w) of strip k.  ``d_own``: distance inside its own edge (mm,
    + inside); ``dc``: distance inside the nearest covering strip (+ under it, - beyond it)."""
    ss = seed * 101 + k * 7919
    aa = 0.55 / ppmm
    G = c.gain
    tone, h, cav = weave(s, w, c, ss, aa)
    fc, fl = fibres(s, w, c, ss + 50, aa)
    tc_, tl_ = ticks(s, w, c, ss + 60, aa)
    better = tc_ * tl_ > fc * fl
    fl = np.where(better, tl_, fl)
    fc = np.maximum(fc, tc_)
    sc_, sg = specks(s, w, c, ss + 70, aa)
    # ---------------------------------------------------------------- edges, frayed
    fray = fray_field(P, c, seed + 12)
    r = c.cord_mm
    kc_ = np.full_like(s, k) if kc is None else kc
    s_c = s if s_cov is None else s_cov
    de_o0 = d_own + fray
    de_c0 = dc + fray
    cr_o, ch_o, kn_o, de_o = _cord(de_o0, s, np.full_like(s, k), c, seed, aa)
    cr_c, ch_c, kn_c, de_c = _cord(de_c0, s_c, kc_, c, seed, aa)
    in_o = (de_o >= 0.0) & (de_o < r)
    in_c = (dc < 0.0) & (de_c >= 0.0) & (de_c < r)
    wall = (d_own < -0.015) & (de_o < 0.0) & ~in_c
    eaten = (d_own >= 0.0) & (de_o < 0.0) & ~in_c
    # the cord: its crown tone with a share of the weave's own texture showing through
    rel = tone / max(c.rib_lum, 1e-9)
    cord_o = cr_o * ((1.0 - c.cord_weave) + c.cord_weave * np.clip(rel, 0.2, 2.5))
    cord_c = cr_c * ((1.0 - c.cord_weave) + c.cord_weave * np.clip(rel, 0.2, 2.5))
    lum = tone.copy()
    lum = np.where(in_o, cord_o, lum)
    lum = np.where(in_c & ~in_o, cord_c, lum)
    # a thin dark groove just inside the cord (bright on the edge line, dark inside it)
    grv = _line(np.abs(de_o - r - 0.5 * c.groove_w_mm), 0.5 * c.groove_w_mm, aa) * (d_own >= 0.0) * ~in_c
    lum = lum * (1.0 - (1.0 - c.groove_mul) * grv)
    # the tape's side: the cord's underside, bright at the top, then near-black
    wz = np.clip(-d_own, 0.0, 3.0)
    wt = np.clip(wz / c.wall_top_mm, 0.0, 1.0)
    wall_tone = c.cord_lum * 0.55 * (1.0 - wt) ** 1.6 + c.wall_lum * (0.8 + 0.4 * _hash(np.floor(s * 9), seed=ss + 26))
    lum = np.where(wall, wall_tone, lum)
    lum = np.where(eaten, c.wall_lum * (0.8 + 0.4 * _hash(np.floor(s * 12), np.floor(w * 12), seed=ss + 25)), lum)
    # ---------------------------------------------------------------- beneath a cover
    beyond = -de_c
    near_c = (dc < 0.015) & (beyond > 0.0)
    crev = _smooth((c.crevice_mm - beyond) / (0.6 * c.crevice_mm)) * near_c
    occ = np.clip(1.0 - beyond / c.occl_w_mm, 0.0, 1.0) * near_c
    shade = (1.0 - c.crevice_dark * crev) * (1.0 - c.occl_dark * occ ** c.occl_pow)
    lum = lum * np.where(in_o | in_c | wall, 1.0, shade)
    core = np.clip(1.0 - beyond / c.core_w_mm, 0.0, 1.0) * near_c
    core = core * (0.8 + 0.2 * noise1(s_c / 0.7 + 5.3 * kc_, seed + 27))
    lum = lum * (1.0 - core) + c.core_lum * core
    # loose fibres of the cover's frayed edge lying across the crevice, each with a shadow
    ecell = c.edge_fibre_cell_mm
    ei = np.floor(s_c / ecell)
    e_on = (_hash(kc_, ei, seed=seed + 31) < c.edge_fibre_prob) & near_c
    e_s0 = (ei + _hash(kc_, ei, seed=seed + 32)) * ecell
    e_len = c.edge_fibre_len_mm[0] + (c.edge_fibre_len_mm[1] - c.edge_fibre_len_mm[0]) * _hash(kc_, ei, seed=seed + 33)
    e_ang = (_hash(kc_, ei, seed=seed + 34) - 0.5) * 1.2
    e_u = (s_c - e_s0) * np.cos(e_ang) - beyond * np.sin(e_ang)
    e_t = (s_c - e_s0) * np.sin(e_ang) + beyond * np.cos(e_ang)
    e_tc = np.clip(e_t, 0.0, e_len)
    e_d = np.hypot(e_u, e_t - e_tc)
    efc = _line(e_d, 0.022, aa) * e_on
    esh = _line(np.hypot(e_u - 0.04, e_t - np.clip(e_t, 0.0, e_len)), 0.05, aa) * e_on * (1.0 - efc)
    lum = lum * (1.0 - 0.5 * esh)
    lum = lum * (1.0 - efc) + c.edge_fibre_lum * efc
    # ---------------------------------------------------------------- colour
    lum = lum * G
    var = 1.0 + c.strip_variation * (2 * _hash(np.array([k]), seed=seed + 99)[0] - 1)
    tint = np.asarray(c.dye) / (0.2126 * c.dye[0] + 0.7152 * c.dye[1] + 0.0722 * c.dye[2])
    cm_r = c.chroma_mottle * (0.6 * fbm2(s / 1.3 + 7.1, w / 1.1, ss + 31, 2) + 0.6 * fbm2(s / 5.0 + 1.7, w / 4.0, ss + 33, 2))
    cm_b = c.chroma_mottle * (0.6 * fbm2(s / 1.2 + 3.3, w / 1.3, ss + 32, 2) + 0.6 * fbm2(s / 4.6 + 9.1, w / 4.4, ss + 34, 2))
    tintp = np.stack([tint[0] * (1 + cm_r), tint[1] * np.ones_like(cm_r), tint[2] * (1 + cm_b)], axis=1)
    base = tintp * (lum * var)[:, None]
    ftint = np.asarray(c.fibre_rgb) / (0.2126 * c.fibre_rgb[0] + 0.7152 * c.fibre_rgb[1] + 0.0722 * c.fibre_rgb[2])
    # fibres and specks: on the tape's face and the cord, shaded by any crevice they lie in
    fshade = ((1.0 - c.crevice_dark * crev) * (1.0 - core) * (1.0 - c.occl_dark * occ ** c.occl_pow))
    face = ~(wall | eaten)
    fib = np.clip(fc, 0.0, 1.0) * face * np.where(in_o | in_c, 0.6, 1.0)
    spk = np.clip(sc_, 0.0, 1.0) * face
    fl_lum = fl * G * fshade
    base = base * (1.0 - fib[:, None]) + (ftint[None, :] * fl_lum[:, None]) * fib[:, None]
    base = base * (1.0 - spk[:, None]) + (ftint[None, :] * (c.speck_lum * G * sg * fshade)[:, None]) * spk[:, None]
    # ---------------------------------------------------------------- loose threads
    if threads:
        tcv, thl, tsh, ttn = thread_fields(P)
    else:
        tcv = thl = tsh = ttn = np.zeros(len(s))
    tcore = tcv * (~wall)
    base = base * (1.0 - 0.55 * tsh[:, None])
    tcol = ftint[None, :] * (c.thread_lum * G) * (0.45 + 0.55 * thl)[:, None] * ttn[:, None]
    base = base * (1.0 - tcore[:, None]) + tcol * tcore[:, None]
    # ---------------------------------------------------------------- height (normal map), mm
    hw = np.maximum(half_width, 0.5)
    xw = np.clip(np.abs(w) / hw, 0.0, 1.0)
    pad = c.pad_mm * (1.0 - xw ** c.pad_power)
    roll = c.edge_roll_mm * (1.0 - np.clip(np.clip(de_o, 0.0, None) / c.edge_roll_w_mm, 0.0, 1.0)) ** 2
    dipt = np.clip(1.0 - np.clip(beyond, 0.0, None) / c.dip_w_mm, 0.0, 1.0) * (dc < 0.015)
    base_h = pad - roll - c.dip_mm * dipt ** 2
    hh = base_h + h + c.fibre_h_mm * fib + 0.03 * spk
    hh = np.where(in_o, base_h + ch_o, hh)
    hh = np.where(in_c & ~in_o, base_h + ch_c + 0.02, hh)
    hh = hh - 0.05 * crev
    hwall = c.wall_round_mm * (1.0 - (1.0 - np.clip(wz / c.wall_round_w_mm, 0.0, 1.0)) ** 2)
    hh = np.where(wall, hwall, hh)
    hh = np.where(eaten, base_h - 0.04, hh)
    hh = hh + 0.03 * tcore * (0.5 + 0.5 * thl)
    # ---------------------------------------------------------------- roughness, cavity
    light = np.maximum(fib, spk)
    rough = c.roughness + c.rough_var * fbm2(s / 1.7, w / 1.7, ss + 41, 2)
    rough = rough * (1.0 - light) + c.fibre_roughness * light
    rough = np.where(in_o | in_c, rough - 0.04, rough)
    rough = rough * (1.0 - tcore) + 0.78 * tcore
    cavity = np.where(in_o | in_c | wall, 1.0, cav) * (1.0 - 0.35 * crev) * (1.0 - 0.2 * occ)
    return {"base": base, "rough": rough, "height": hh, "cavity": cavity}


# =========================================================================== the atlas
def paint_atlas(model, atlas, pieces, c: Cloth4, seed: int, log=print) -> Dict[str, np.ndarray]:
    size = atlas.size
    base = np.zeros((size, size, 3), np.float32)
    rough = np.full((size, size), c.roughness, np.float32)
    height = np.zeros((size, size), np.float32)
    cav = np.ones((size, size), np.float32)
    written = np.zeros((size, size), bool)
    from .smokebomb_atlas import piece_key
    ftint = np.asarray(c.fibre_rgb) / (0.2126 * c.fibre_rgb[0] + 0.7152 * c.fibre_rgb[1] + 0.0722 * c.fibre_rgb[2])
    for p in pieces:
        key = piece_key(p)
        x0, y0, bw, bh = atlas.block(key)
        isl = atlas.islands[key]
        if getattr(p, "is_thread", False):
            # the T4 hook's own island (props_lib.smokebomb_threads): warm tan yarn, its
            # twist a faint stripe along it
            ys = slice(max(y0, 0), min(y0 + bh, size))
            xs = slice(max(x0, 0), min(x0 + bw, size))
            yy, xx = np.mgrid[ys, xs]
            u = (xx - isl.x0) / atlas.ppmm
            v = (isl.y0 - yy) / atlas.ppmm
            twist = 0.8 + 0.2 * np.sin(2 * np.pi * (u / 0.35 + v / 0.25))
            base[ys, xs] = (ftint * c.thread_lum * c.gain)[None, None, :] * twist[..., None]
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
        for r0 in range(0, bh, 256):
            r1 = min(bh, r0 + 256)
            ch = island_channels(model, p.strip, S[r0:r1], W[r0:r1], atlas.ppmm, c, seed, near)
            yy0 = y0 + r0
            ys = slice(max(yy0, 0), min(y0 + r1, size))
            xs = slice(max(x0, 0), min(x0 + bw, size))
            if ys.stop <= ys.start or xs.stop <= xs.start:
                continue
            oy, ox = ys.start - yy0, xs.start - x0
            hh_, ww_ = ys.stop - ys.start, xs.stop - xs.start
            base[ys, xs] = ch["base"][oy:oy + hh_, ox:ox + ww_]
            rough[ys, xs] = ch["rough"][oy:oy + hh_, ox:ox + ww_]
            height[ys, xs] = ch["height"][oy:oy + hh_, ox:ox + ww_]
            cav[ys, xs] = ch["cavity"][oy:oy + hh_, ox:ox + ww_]
            written[ys, xs] = True
    if (~written).any():
        base[~written] = base[written].mean(axis=0)
    return {"base": base, "rough": rough, "height": height, "cavity": cav, "written": written}


__all__ = ["Cloth4", "THREADS_PX", "paint_atlas", "island_channels", "texel_channels",
           "normals_from_height", "thread_fields", "weave", "fibres", "specks"]
