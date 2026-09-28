#!/usr/bin/env python
"""props_lib.smokebomb_cloth - the smoke bomb's cloth, authored in TAPE space (round 2).

numpy only.  This replaces smokebomb_tape's cloth (``cloth_texels``) for the build; the tape
module keeps the section, the sweep, the atlas, the crevice fields and the maps.  Same inputs
and outputs as ``smokebomb_tape.cloth_texels``: tape coordinates (u along the tape, tc across
it from the centre line, mm), the local width, the crevice fields; returns linear albedo
luminance ``alb``, micro height ``hgt`` (mm), ``rough`` and the analytic ``ao``.

WHY IT CHANGED (the round-1 blind judge, 20 of 20 pairs, and the measurer)
    * every band edge read as "uniform light-grey tubes with evenly spaced candy-stripe
      segments" - vinyl piping.  The cord had its OWN albedo, 5x the cloth's mean, and a dark
      joint every 0.9 mm.  A real rolled edge is the same tape rolled over: the warps run on
      round it and the weft turns round it at the selvedge.  So here the cord carries the
      SAME weave as the body (its warps continue along u), darkening as it turns under, with
      the weft's selvedge loops as thin slanted light wraps at an irregular spacing; the
      knuckles are small, irregular and mostly in the normal map.  The rim reads brighter
      only where its round top faces the light (REFERENCE_SPEC 5: 1.5-3x, from geometry).
    * the body read as "a uniform stipple of short parallel dashes, like rain, no crossing
      weft".  Round 1 met the sparkle fraction with a strong elongated glint on every warp
      every 0.6 mm (rows of dots), and its crests were dashes.  Here the warp crests are THIN
      LONG LINES (they dip only briefly at an interlacing) whose brightness drifts slowly
      along each thread and from thread to thread; the weft shows as thin cross lines over
      one to four warps and short ticks in the gaps (an irregular lattice, REFERENCE_SPEC 7:
      "faint, irregular grid", "cross-dots at about twice the warp pitch"); glints are
      sparse, crisp and bright, one texel, on the crests.
    * "the copy's crevices are thin dark lines; the reference has deeper shadowed gaps with
      fibres hanging into them" / crevices near-black (p1 0.0063 vs 0.0165): a wider, softer
      occlusion band (never black) with the covering edge's fibres falling across it.
    * streaks: REFERENCE_SPEC 7's persistent streaks are 0.07 log; round 1's per-thread tone
      was constant along the whole tape, so a long average showed ~0.2 log "barcode"
      banding.  Every thread's tone here decorrelates along u over ~1 mm.

Every tone is a linear albedo; ``gain`` is the one calibration factor.
"""
from __future__ import annotations

import math
import os
import pickle
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from typing import Callable, Dict, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_tape as T

hash01, gauss, vnoise1, vnoise2, fbm2 = T.hash01, T.gauss, T.vnoise1, T.vnoise2, T.fbm2
_line, _smoothstep, VN_RMS = T._line, T._smoothstep, T.VN_RMS
CORD, BODY, SKIRT = T.CORD, T.BODY, T.SKIRT


@dataclass
class ClothSpec3:
    """The cloth, round 3.  mm; tones are LINEAR albedo luminance before ``gain``.

    REFERENCE_SPEC 7 (px at 13.26 px/mm): warp pitch 4.1 px -> 0.31 mm; weft irregular at ~2x
    the warp pitch; correlation along 5-10 px, across 3.5-4.5 px; streaks 0.07 log at ~0.72
    mm; high-pass log std 0.13, linear p90/p10 ~8; sparkle 4.2 % of pixels > 3x the local
    median, warm light grey.  REFERENCE_SPEC 5/6: rim 4-8 px, crevice 30-47 % darker 2.5-3.5
    px beyond it; fray rms 1.5 px at 11.5 px.

    Round 3 (the round-2 blind judge, 20 of 20: "evenly spaced parallel lines with crisp short
    perpendicular dashes, like graph paper or a barcode", "straight random scratch-like hair
    lines", "no pinpoint glints", "flat painted bands", "smooth pale piping" edges): the warps
    are broken into FLOATS of irregular length whose tone varies strongly float to float, with
    DARK breaks where they dive under the weft (the weft itself shows only now and then, dim);
    the lines wander; a PUCKER relief (cross-ridges and lumps, 0.8-2 mm) shades the cloth in
    the normal map and a little in the albedo; glints are crisp bright points on the floats;
    the surface fibres are few, short and CURLY (no straight hairs); the band ROLLS OFF toward
    its edges in the normal map (padded); the rolled edge is a smoother, darker-flanked TUBE
    (the albedo no longer paints it pale) segmented by slanted joints with curved weft loops."""
    chroma: Tuple[float, float, float] = (0.3835, 0.324, 0.2925)
    gain: float = 0.52
    # ---- warps
    warp_pitch_mm: float = 0.31
    pitch_jitter: float = 0.22          # slow, thread units
    pitch_fast: float = 0.10            # thread to thread
    wander: float = 0.20                # thread units ...
    wander_len_mm: float = 1.3          # ... over this length: the lines wander, never ruled
    gap_lum: float = 0.012              # the shadowed valley between two warps
    body_lum: float = 0.030             # the yarn's rounded body
    crest_lum: float = 0.13             # the lit crest
    crest_half_mm: float = 0.042
    crest_offset: float = 0.12          # thread units, per thread
    crest_kink: float = 0.08            # per float
    crest_sigma: float = 0.25           # slow log drift of the crests along the thread ...
    crest_len_mm: float = 1.0           # ... over this length
    # the picks: plain weave (warp i over pick k when k + i is even), floats of IRREGULAR length
    pick_mm: float = 0.31
    pick_wave_mm: float = 0.06
    pick_drift: float = 0.25            # pick units, per thread, slow
    float_warp: float = 0.28            # float units: the float boundaries wander along the thread
    float_warp_mm: float = 0.55
    float_exp: float = 0.8
    float_sigma: float = 0.55           # per-float tone (lognormal)
    dip_len_mm: float = 0.05
    dip_depth: float = 0.85             # the break where a warp dives under the weft is DARK
    # ---- the pucker: cross-ridges (short along the tape, long across) and lumps
    pucker_u_mm: float = 0.8
    pucker_a_mm: float = 2.2
    pucker_h_mm: float = 0.045
    pucker_tone: float = 0.20           # log tone per unit of the pucker (cavities darker)
    lump_mm: float = 1.6
    lump_h_mm: float = 0.035
    lump_tone: float = 0.12
    # streaks (REFERENCE_SPEC 7: 0.07 log, ~0.72 mm across)
    streak_mm: float = 0.72
    streak_log: float = 0.07
    mottle: float = 0.05
    # ---- weft: seen only now and then in a break, dim
    weft_prob: float = 0.22
    weft_w_mm: float = 0.07
    weft_lum: Tuple[float, float] = (0.03, 0.16)
    # ---- glints: crisp bright points on the floats' crests
    glint_prob: float = 0.30
    glint_len_mm: Tuple[float, float] = (0.025, 0.05)
    glint_lum: Tuple[float, float] = (0.55, 1.0)
    glint_half_mm: float = 0.032
    # free specks anywhere (a lit fibre end)
    speck_cell_mm: float = 0.30
    speck_prob: float = 0.12
    speck_lum: Tuple[float, float] = (0.45, 0.95)
    speck_r_mm: float = 0.04
    # ---- surface fibres: few, short, CURLY (no straight hairs)
    fibre_cell_mm: float = 0.4
    fibre_prob: float = 0.045
    fibre_len_mm: Tuple[float, float] = (0.08, 0.30)
    fibre_half_mm: float = 0.024
    fibre_along_sigma_deg: float = 25.0
    fibre_cross_share: float = 0.5
    fibre_curl: float = 16.0
    fibre_lum: Tuple[float, float] = (0.05, 0.24)
    alb_max: float = 1.0
    # ---- micro relief (mm) for the normal map
    rib_h_mm: float = 0.045
    crest_h_mm: float = 0.008
    fibre_h_mm: float = 0.012
    weft_h_mm: float = 0.008
    #: the band rolls off toward its edges (padded): height rises this much over ``pad_mm``
    #: in from the groove (normal map only; the crown is geometry)
    pad_h_mm: float = 0.22
    pad_mm: float = 1.4
    # ---- the rolled edge: a tight roll - smoother, the weave only faint on it
    cord_lum: float = 0.034             # the roll's own tone (about the cloth's mean)
    cord_smooth: float = 0.6            # share of the smooth roll over the weave on the cord
    cord_striae: float = 0.30           # the roll's fine lengthwise striations (log)
    under_dark: float = 0.70            # the cord darkens this much as it turns under
    rim_gain: float = 1.7               # the roll's top shows a little more lit fibre
    rope_gain: float = 1.8              # a gathered tape (a rope of its two rims)
    wrap_pitch_mm: float = 0.42         # knuckles: the weft's selvedge wraps ...
    wrap_jitter: float = 0.60           # ... irregular
    wrap_prob: float = 0.55
    wrap_half_mm: float = 0.026
    wrap_lum: Tuple[float, float] = (0.10, 0.40)
    wrap_slant: float = 0.55            # the wrap leans along the cord ...
    wrap_bow: float = 0.30              # ... and bows (a curved loop, not a straight stripe)
    knuckle_h_mm: float = 0.13          # the knuckles' irregular bulge (normal map)
    knuckle_tone: float = 0.40          # log tone spread from knuckle to knuckle
    joint_prob: float = 0.75
    joint_dark: float = 0.75
    groove_half_mm: float = 0.05
    groove_dark: float = 0.45
    groove_warp_dim: float = 0.30
    groove_warp_mm: float = 0.30
    under_lum: float = 0.006            # the skirt's floor ...
    skirt_share: float = 0.5            # ... it keeps this share of the weave
    # ---- the fray and the crevice under a covering edge
    fray_rms_mm: float = 0.11
    fray_len_mm: float = 0.87
    core_mm: float = 0.16
    core_dark: float = 0.72
    crevice_mm: float = 1.3
    crevice_dark: float = 0.62
    occl_mm: float = 1.2
    occl_dark: float = 0.55
    under_edge: float = 0.45           # texels the edge covers (never seen) keep this share
    # the covering edge's fibres falling across the crevice (curly)
    xfibre_cell_mm: float = 0.22
    xfibre_prob: float = 0.30
    xfibre_len_mm: Tuple[float, float] = (0.12, 0.45)
    xfibre_half_mm: float = 0.022
    xfibre_lum: Tuple[float, float] = (0.05, 0.22)
    xfibre_curl: float = 7.0
    # ---- roughness
    roughness: float = 0.90
    rough_var: float = 0.03
    fibre_roughness: float = 0.84
    crevice_roughness: float = 0.95
    # ---- loose threads (their own block): warm tan, lighter than the tape
    thread_lum: float = 0.50
    thread_dark_lum: float = 0.05       # a thread seen against the backdrop keeps some of the tape's tone


#: the build's name for the current calibration
ClothSpec = ClothSpec3


def _weave(u, a, c: ClothSpec3, seed: int, aa: float):
    """Plain weave, warp-faced, in tape space (u along, a across, mm).

    The weft picks cross the tape every ``pick_mm`` (wavy); warp i passes OVER pick k when
    k + i is even and UNDER it otherwise, so each warp shows as FLOATS about two picks long,
    staggered from its neighbours - but the float boundaries wander along each thread
    (``float_warp``), so the lattice is never regular.  At each under-crossing the warp dives
    into a DARK break; the weft shows on top of it only now and then, dim.  Every float has its
    own tone (lognormal, wide), so a thread is a run of dashes of very different brightness.
    A pucker relief (cross-ridges, lumps) shades the cloth; it darkens its cavities a little."""
    p = c.warp_pitch_mm
    g = a / p
    g = g + c.pitch_jitter * vnoise1(g * 0.35 + 3.1, seed + 1) * VN_RMS * 0.6
    g = g + c.pitch_fast * vnoise1(a / p + 7.7, seed + 3) * VN_RMS * 0.6
    g = g + c.wander * vnoise2(u / c.wander_len_mm, a / 1.2, seed + 2) * VN_RMS * 0.6
    i = np.floor(g)
    x = g - i
    body = np.sin(np.pi * x) ** 2
    qp = c.pick_mm
    wave = c.pick_wave_mm * VN_RMS * 0.6 * vnoise1(a / 1.3 + 0.07 * u, seed + 5)
    drift = c.pick_drift * qp * VN_RMS * 0.5 * vnoise1(u / 1.7 + 7.3 * i, seed + 7)
    v = (u + wave + drift) / qp
    w = 0.5 * (v - np.mod(i, 2.0))                          # one float per unit
    w = w + c.float_warp * VN_RMS * 0.6 * vnoise1(u / c.float_warp_mm + 17.3 * i, seed + 12)
    fid = np.floor(w)
    fp = w - fid                                            # 0 / 1 = the under-crossings
    endd = np.minimum(fp, 1.0 - fp) * 2.0 * qp              # mm to the nearest under-crossing
    dip = _smoothstep(0.0, c.dip_len_mm, endd - 0.5 * c.weft_w_mm)
    dipf = 1.0 - c.dip_depth * (1.0 - dip)
    shape = np.sin(np.pi * fp) ** c.float_exp               # the float's own rounding along
    ft = np.exp(c.float_sigma * np.clip(gauss(i, fid, seed=seed + 9), -2.2, 2.2))
    ft = ft * np.exp(c.crest_sigma * VN_RMS * 0.6 * vnoise1(u / c.crest_len_mm + 37.1 * i, seed + 8))
    dx = (x - 0.5 - c.crest_offset * (2 * hash01(i, seed=seed + 11) - 1)
          - c.crest_kink * (2 * hash01(i, fid, seed=seed + 10) - 1)) * p
    cline = _line(dx, c.crest_half_mm, aa)
    crest = cline * dipf * (0.3 + 0.7 * shape)
    tone = c.gap_lum + c.body_lum * body * dipf * (0.4 + 0.6 * shape) * np.sqrt(ft) + c.crest_lum * crest * ft
    h = c.rib_h_mm * body * (0.45 + 0.55 * dip * shape) + c.crest_h_mm * crest
    # the weft on top of this warp at its under-crossing: now and then a short dim cross-tick
    du_x = (np.where(fp < 0.5, fp, fp - 1.0)) * 2.0 * qp
    wshow = hash01(i, fid, seed=seed + 62) < c.weft_prob
    wl = _line(du_x, 0.5 * c.weft_w_mm, aa) * _smoothstep(0.1, 0.35, x) * _smoothstep(0.9, 0.65, x) * wshow
    wlum = c.weft_lum[0] + (c.weft_lum[1] - c.weft_lum[0]) * hash01(i, fid, seed=seed + 64) ** 1.5
    tone = np.maximum(tone, wlum * wl)
    h = h + c.weft_h_mm * wl
    # glints: crisp bright points ON a float's crest
    gon = hash01(i, fid, seed=seed + 81) < c.glint_prob
    gpos = 0.2 + 0.6 * hash01(i, fid, seed=seed + 82)
    sg = c.glint_len_mm[0] + (c.glint_len_mm[1] - c.glint_len_mm[0]) * hash01(i, fid, seed=seed + 83)
    G = c.glint_lum[0] + (c.glint_lum[1] - c.glint_lum[0]) * hash01(i, fid, seed=seed + 84) ** 1.5
    gl = gon * G * np.exp(-0.5 * (((fp - gpos) * 2.0 * qp) / sg) ** 2)
    tone = np.maximum(tone, gl * _line(dx, c.glint_half_mm, aa))
    # the pucker: cross-ridges (short along u, long across) + lumps; relief with dim cavities
    pk = VN_RMS * 0.75 * fbm2(u / c.pucker_u_mm + 0.25 * a / c.pucker_a_mm, a / c.pucker_a_mm, seed + 44, 2)
    lm = VN_RMS * 0.75 * fbm2(u / c.lump_mm, a / c.lump_mm, seed + 45, 2)
    h = h + c.pucker_h_mm * pk + c.lump_h_mm * lm
    relief = np.exp(np.clip(c.pucker_tone * pk + c.lump_tone * lm, -0.9, 0.9))
    # persistent streaks (0.07 log across the tape) and a faint mottle
    st = np.exp(c.streak_log * VN_RMS * 0.7 * (vnoise1(a / c.streak_mm + 0.012 * u, seed + 41)
                                               + 0.45 * vnoise1(a / (0.47 * c.streak_mm) + 5.0, seed + 42)) / 1.1)
    tone = tone * st * relief * (1.0 + c.mottle * fbm2(u / 3.0, a / 2.4, seed + 4, 2))
    return tone, h, cline, i


def _strokes(u, a, cell, prob, lens, half, along_sig_deg, cross_share, curl, lums, seed, aa):
    """Short curly fibres in a jittered grid: coverage and brightness.  Each is an ARC (the
    curvature ``curl`` 1/mm, either sense), tapering at both ends."""
    ci, cj = np.floor(u / cell), np.floor(a / cell)
    cov = np.zeros_like(u)
    lum = np.zeros_like(u)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            present = hash01(I, J, seed=seed) < prob
            cx = (I + hash01(I, J, seed=seed + 1)) * cell
            cy = (J + hash01(I, J, seed=seed + 2)) * cell
            L = lens[0] + (lens[1] - lens[0]) * hash01(I, J, seed=seed + 3) ** 1.5
            cross = hash01(I, J, seed=seed + 12) < cross_share
            ang = np.where(cross, hash01(I, J, seed=seed + 13) * np.pi,
                           np.radians(along_sig_deg) * gauss(I, J, seed=seed + 4))
            kap = np.where(hash01(I, J, seed=seed + 6) < 0.5, -1.0, 1.0) * curl * (0.6 + 0.8 * hash01(I, J, seed=seed + 14))
            ca, sa = np.cos(ang), np.sin(ang)
            px, py = u - cx, a - cy
            tt = px * ca + py * sa
            nn = -px * sa + py * ca
            tc = np.clip(tt, -0.5 * L, 0.5 * L)
            nd = nn - 0.5 * kap * tc * tc
            dist = np.sqrt(nd * nd + (tt - tc) ** 2)
            g = lums[0] + (lums[1] - lums[0]) * hash01(I, J, seed=seed + 7) ** 1.3
            taper = 0.35 + 0.65 * np.cos(0.5 * np.pi * np.clip(tt / np.maximum(0.5 * L, 1e-6), -1, 1))
            hw = half * (0.75 + 0.5 * hash01(I, J, seed=seed + 8))
            cv = _line(dist, hw, aa) * present
            val = g * taper
            better = cv * val > cov * lum
            lum = np.where(better, val, lum)
            cov = np.maximum(cov, cv)
    return cov, lum


def _specks(u, a, c: ClothSpec3, seed: int, aa: float):
    """Free fibre-end specks: tiny, crisp, bright points."""
    cell = c.speck_cell_mm
    ci, cj = np.floor(u / cell), np.floor(a / cell)
    out = np.zeros_like(u)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            on = hash01(I, J, seed=seed) < c.speck_prob
            cx = (I + hash01(I, J, seed=seed + 1)) * cell
            cy = (J + hash01(I, J, seed=seed + 2)) * cell
            d = np.hypot(u - cx, a - cy)
            G = c.speck_lum[0] + (c.speck_lum[1] - c.speck_lum[0]) * hash01(I, J, seed=seed + 3)
            out = np.maximum(out, on * G * _line(d, c.speck_r_mm, aa))
    return out


def _wraps(u, e, c: ClothSpec3, aa: float, seed: int, e_mid: float = 0.0, e_half: float = 0.4):
    """The rolled edge's knuckles: the roll is SEGMENTED at an irregular spacing by slanted
    joints (the weft's selvedge wraps).  Some joints show a curved light loop (the wrap), most
    a dark groove; each knuckle bulges with its own height and tone.  Returns the loop
    coverage and tone, the knuckle height (normal map) and the knuckle's tone factor."""
    kp = c.wrap_pitch_mm
    en = (e - e_mid) / max(e_half, 1e-6)
    lv = (u / kp + c.wrap_jitter * VN_RMS * 0.5 * vnoise1(u / 1.1, seed + 21) + c.wrap_slant * e / kp
          + c.wrap_bow * en * en)
    kj = np.floor(lv + 0.5)
    fr = lv - kj                                           # 0 at a joint, +-0.5 mid-knuckle
    on = hash01(kj, seed=seed + 23) < c.wrap_prob
    cov = _line(np.abs(fr) * kp, c.wrap_half_mm, aa) * on
    lum = c.wrap_lum[0] + (c.wrap_lum[1] - c.wrap_lum[0]) * hash01(kj, seed=seed + 24) ** 1.4
    gdist = np.abs(fr - 0.12 * np.where(hash01(kj, seed=seed + 26) < 0.5, 1.0, -1.0)) * kp
    groove = _line(gdist, 0.04, aa) * (hash01(kj, seed=seed + 27) < c.joint_prob)
    kk = np.floor(lv)
    fk = lv - kk
    hk = 0.35 + 0.65 * hash01(kk, seed=seed + 25)
    bulge = np.sin(np.pi * fk) ** 1.5 * hk - 0.7 * groove
    ktone = np.exp(c.knuckle_tone * (2.0 * hash01(kk, seed=seed + 28) - 1.0)) * (0.8 + 0.4 * np.sin(np.pi * fk))
    ktone = ktone * (1.0 - c.joint_dark * groove)
    return cov, lum, bulge, ktone


def cloth_texels(u, tc, prof: T.Profile, c: ClothSpec3, ppmm: float, width, seed: int = 1, tape_id: int = 0,
                 crev: Optional[Dict[str, np.ndarray]] = None, gather=None) -> Dict[str, np.ndarray]:
    """The cloth at tape coordinates (u, tc), flat arrays (smokebomb_tape.cloth_texels'
    contract).  ``gather`` (0 flat .. 1 a rope, the winder's roll): a gathered tape is its two
    rolled edges side by side (REFERENCE_SPEC 4.2 "W twisted: a raised double rim"), so it
    reads like a rim - knuckled - across its whole footprint."""
    u = np.asarray(u, np.float64)
    tc = np.asarray(tc, np.float64)
    aa = 0.5 / ppmm
    q = prof.section(tc, width)
    e, region = q["e"], q["region"]
    a = tc
    ss = seed * 1009 + tape_id * 7919
    tone, h, crest, ti = _weave(u, a, c, ss, aa)
    on_cord = region == CORD
    ej = prof.spec.cord_r_mm * prof.phi_j               # the groove, from the outer-most point
    fray = c.fray_rms_mm * VN_RMS * 0.8 * (vnoise1(u / c.fray_len_mm, ss + 80)
                                          + 0.35 * vnoise1(u / (0.37 * c.fray_len_mm), ss + 81))
    under = _smoothstep(0.10, -0.30, e - 0.6 * fray)        # 1 round the underside
    e_lo = -0.5 * math.pi * prof.spec.cord_r_mm
    wc, wlum, bulge, ktone = _wraps(u + 997.0 * (q["side"] > 0), e, c, aa, seed * 131 + tape_id * 17,
                                    e_mid=0.5 * (ej + e_lo), e_half=0.5 * (ej - e_lo))
    top = _smoothstep(-0.20, 0.10, e - 0.5 * fray) * (1.0 - _smoothstep(ej - 0.08, ej + 0.04, e))
    # the tight roll: its own smooth tone with fine lengthwise striations, the weave faint on it
    striae = np.exp(c.cord_striae * VN_RMS * 0.6 * vnoise2(u / 0.35, e / 0.05, ss + 85))
    roll = c.cord_lum * striae
    ctone = (1.0 - c.cord_smooth) * tone + c.cord_smooth * roll
    cord_tone = np.maximum(ctone * (1.0 + (c.rim_gain - 1.0) * top) * ktone, wlum * wc) * (1.0 - c.under_dark * under)
    tone = np.where(on_cord, cord_tone, tone)
    h = np.where(on_cord, h + c.knuckle_h_mm * bulge + 0.01 * wc, h)
    if gather is not None:
        rope = _smoothstep(0.55, 0.95, np.asarray(gather, np.float64)) * (region == BODY)
        rope_tone = np.maximum(((1.0 - c.cord_smooth) * tone + c.cord_smooth * roll) * c.rope_gain * ktone, wlum * wc)
        tone = tone * (1.0 - rope) + rope_tone * rope
        h = h + rope * c.knuckle_h_mm * bulge
    # the warps next to the roll are pulled down into its groove
    tone = tone * (1.0 - c.groove_warp_dim * (1.0 - _smoothstep(ej, ej + c.groove_warp_mm, e)))
    groove = np.exp(-0.5 * ((e - ej) / c.groove_half_mm) ** 2) * (region != SKIRT)
    tone = tone * (1.0 - c.groove_dark * groove)
    # the band rolls off toward its edges (padded) - normal map only
    h = h + c.pad_h_mm * _smoothstep(ej, ej + c.pad_mm, e) * (region == BODY)
    # fibres and specks lie on everything visible
    f_cov, f_lum = _strokes(u, a, c.fibre_cell_mm, c.fibre_prob, c.fibre_len_mm, c.fibre_half_mm,
                            c.fibre_along_sigma_deg, c.fibre_cross_share, c.fibre_curl, c.fibre_lum, ss + 50, aa)
    face = ((region == BODY) | on_cord) * np.where(on_cord, 1.0 - 0.7 * under, 1.0)
    fib = f_cov * face
    alb = tone * (1 - fib) + f_lum * fib
    alb = np.maximum(alb, _specks(u, a, c, ss + 70, aa) * face)
    hgt = h + c.fibre_h_mm * fib
    alb = np.where(region == SKIRT, np.maximum(c.under_lum, c.skirt_share * tone), alb)
    ao = np.ones_like(u)
    rough = c.roughness + c.rough_var * fbm2(u / 1.7, a / 1.7, ss + 90, 2)
    rough = rough * (1 - fib) + c.fibre_roughness * fib
    # ---------------------------------------------------------------- beneath a covering edge
    if crev is not None:
        b = np.asarray(crev["beyond"], np.float64)
        has = np.isfinite(b)
        eu = np.asarray(crev["edge_u"], np.float64)
        esd = np.asarray(crev["side"], np.float64)
        etp = np.asarray(crev["tape"], np.float64)
        es = seed * 577 + 13
        fr2 = c.fray_rms_mm * VN_RMS * 0.8 * (vnoise1(eu / c.fray_len_mm + 3.7 * esd + 11.0 * etp, es)
                                              + 0.35 * vnoise1(eu / (0.37 * c.fray_len_mm) + 1.3 * esd, es + 1))
        bb = np.where(has, b - np.abs(fr2) * 0.8, np.inf)
        covered = has & (b < 0.0)
        near = has & (bb > -0.05) & (bb < 2.5)
        core = np.where(near, np.exp(-np.clip(bb, 0, None) / c.core_mm), 0.0)
        crv = np.where(near, _smoothstep(c.crevice_mm, 0.0, bb) ** 1.5, 0.0)
        shade = (1.0 - c.core_dark * core) * (1.0 - c.crevice_dark * crv)
        fuzz = has & (b >= 0.0) & (bb < 0.0)
        alb = np.where(near | fuzz, alb * shade, alb)
        alb = np.where(covered, alb * c.under_edge, alb)
        # the covering edge's fibres falling across the crevice (rooted at the edge, curly)
        cell = c.xfibre_cell_mm
        ci = np.floor(eu / cell)
        xc = np.zeros_like(u)
        xl = np.zeros_like(u)
        bcl = np.clip(np.where(has, b, 3.0), -1, 3)
        for dci in (-1, 0, 1):
            I = ci + dci
            on = (hash01(I, esd, etp, seed=es + 3) < c.xfibre_prob) & (near | fuzz)
            s0 = (I + hash01(I, esd, etp, seed=es + 4)) * cell
            L = c.xfibre_len_mm[0] + (c.xfibre_len_mm[1] - c.xfibre_len_mm[0]) * hash01(I, esd, etp, seed=es + 5) ** 1.3
            ang = (2 * hash01(I, esd, etp, seed=es + 6) - 1) * 0.9
            du_ = eu - s0
            tt = du_ * np.sin(ang) + bcl * np.cos(ang)
            nn = du_ * np.cos(ang) - bcl * np.sin(ang)
            kap = (2 * hash01(I, esd, etp, seed=es + 7) - 1) * c.xfibre_curl
            tcl = np.clip(tt, -0.05, L)
            nd = nn - 0.5 * kap * tcl * tcl
            dist = np.hypot(nd, tt - tcl)
            cv = _line(dist, c.xfibre_half_mm, aa) * on
            g = c.xfibre_lum[0] + (c.xfibre_lum[1] - c.xfibre_lum[0]) * hash01(I, esd, etp, seed=es + 8)
            g = g * (1.0 - 0.55 * np.clip(tcl / np.maximum(L, 1e-6), 0, 1))       # dimmer as they fall
            better = cv * g > xc * xl
            xl = np.where(better, g, xl)
            xc = np.maximum(xc, cv)
        alb = alb * (1 - xc) + xl * xc
        hgt = hgt + 0.012 * xc
        occ = np.where(near | fuzz, np.exp(-np.clip(bb, 0, None) / (0.45 * c.occl_mm)), 0.0)
        ao = np.where(near | fuzz, 1.0 - c.occl_dark * occ, ao)
        ao = np.where(covered, 0.3, ao)
        rough = np.where(near, rough * (1 - crv) + c.crevice_roughness * crv, rough)
    ao = ao * (1.0 - 0.30 * groove)
    ao = np.where(region == SKIRT, 0.35, ao)
    alb = np.clip(alb * c.gain, 0.0, c.alb_max * c.gain)
    return {"alb": alb, "hgt": hgt, "rough": np.clip(rough, 0.0, 1.0), "ao": np.clip(ao, 0.0, 1.0)}


def thread_texels(u, t, ppmm: float, c: ClothSpec3, seed: int = 3,
                  ranges: Optional[Sequence[Tuple[float, float, str]]] = None) -> Dict[str, np.ndarray]:
    """The loose threads' own block: warm tan multi-fibre yarn (the dye at a lighter tone, so a
    recolour tints it too) - fibres along it, the twist as a faint slant, lit fibre tips.
    ``ranges`` [(u0, u1, tone)]: parts whose tone is 'cloth' (T4, seen against the backdrop)
    take the tape's own dark tone instead."""
    u = np.asarray(u, np.float64)
    t = np.asarray(t, np.float64)
    aa = 0.5 / ppmm
    tw = 0.75 + 0.25 * np.sin(2 * np.pi * (u / 0.31 + t / 0.17))
    fib = 1.0 + 0.35 * vnoise2(u / 0.08, t / 0.03, seed) + 0.2 * vnoise2(u / 0.3, t / 0.1, seed + 1)
    lum = np.full_like(u, c.thread_lum)
    if ranges:
        for u0, u1, tone in ranges:
            if tone == "cloth":
                lum = np.where((u >= u0 - 0.25) & (u <= u1 + 0.25), c.thread_dark_lum, lum)
    alb = lum * tw * fib
    alb = np.maximum(alb, 1.6 * lum * _line(np.abs(np.mod(t + 0.3 * u, 0.09) - 0.045), 0.008, aa))
    return {"alb": np.clip(alb * c.gain, 0.0, c.alb_max * c.gain),
            "hgt": 0.004 * np.sin(2 * np.pi * (u / 0.31 + t / 0.17)),
            "rough": np.full_like(u, 0.82), "ao": np.ones_like(u)}


# =========================================================================== painting
class WidthTable:
    """What painting needs of a sweep: its width (and gather) along u, its profile and tape id."""

    def __init__(self, s, w, tape_id, profile, g=None):
        self.s = np.asarray(s, np.float64)
        self.w = np.asarray(w, np.float64)
        self.g = None if g is None else np.asarray(g, np.float64)
        self.tape_id = int(tape_id)
        self.profile = profile

    def width_at(self, u):
        return np.interp(np.asarray(u, np.float64), self.s, self.w)

    def gather_at(self, u):
        if self.g is None or not np.any(self.g > 1e-3):
            return None
        return np.interp(np.asarray(u, np.float64), self.s, self.g)


def _paint_one(atlas, b, sw, cloth, seed, crev, ss, special_fn, chunk_px=192):
    """One block: returns (ya, yb, xa, xb, {k: array}, own mask)."""
    S = atlas.size
    offs = (np.arange(ss) + 0.5) / ss - 0.5
    xs, ys, uu_all, tt_all = atlas.texel_grid(b)
    x0, y0 = int(xs[0] - 0.5), int(ys[0] - 0.5)
    xa, xb = max(0, x0), min(S, x0 + len(xs))
    ya, yb = max(0, y0), min(S, y0 + len(ys))
    if xb <= xa or yb <= ya:
        return None
    tt = tt_all[ya - y0:yb - y0]
    res = {k: np.zeros((yb - ya, xb - xa), np.float32) for k in ("alb", "hgt", "rough", "ao")}
    for xc0 in range(xa, xb, chunk_px):
        xc1 = min(xb, xc0 + chunk_px)
        uu = uu_all[xc0 - x0:xc1 - x0]
        acc = {k: np.zeros((yb - ya, xc1 - xc0)) for k in res}
        cv0 = None
        if crev is not None and special_fn is None:
            cv0 = {k: np.asarray(v[ya:yb, xc0:xc1], np.float64) for k, v in crev.items()}
        for oy in offs:
            for ox in offs:
                U, Tt = np.meshgrid(uu + ox / atlas.ppmm, tt + oy / atlas.ppmm)
                if special_fn is not None:
                    ch = special_fn(U.ravel(), Tt.ravel(), atlas.ppmm * ss)
                else:
                    cv = None
                    if cv0 is not None:
                        cv = {k: v.ravel() for k, v in cv0.items()}
                        cv["beyond"] = np.broadcast_to(
                            cv0["beyond"] + (ox * cv0["ox"] + oy * cv0["oy"]) / atlas.ppmm, U.shape).ravel()
                        cv["edge_u"] = np.broadcast_to(
                            cv0["edge_u"] + (-ox * cv0["oy"] + oy * cv0["ox"]) / atlas.ppmm, U.shape).ravel()
                    ch = cloth_texels(U.ravel(), Tt.ravel(), sw.profile, cloth, atlas.ppmm * ss,
                                      sw.width_at(U.ravel()), seed, sw.tape_id, cv,
                                      gather=sw.gather_at(U.ravel()) if hasattr(sw, "gather_at") else None)
                for k in acc:
                    acc[k] += ch[k].reshape(acc[k].shape)
        n = float(ss * ss)
        for k in res:
            res[k][:, xc0 - xa:xc1 - xa] = acc[k] / n
    own = np.zeros((yb - ya, xb - xa), bool)
    oy0, oy1 = max(0, b.y - ya), max(0, b.y + b.h - ya)
    ox0, ox1 = max(0, b.x - xa), max(0, min(xb, b.x + b.w) - xa)
    own[oy0:oy1, ox0:ox1] = True
    return ya, yb, xa, xb, res, own


def merge_painted(size: int, roughness: float, parts) -> Dict[str, np.ndarray]:
    """Apply painted blocks IN BLOCK ORDER exactly as smokebomb_tape.paint_blocks does (a
    block's own rectangle always wins; its padding only fills what nothing wrote yet)."""
    out = {"alb": np.zeros((size, size)), "hgt": np.zeros((size, size)), "rough": np.full((size, size), roughness),
           "ao": np.ones((size, size)), "written": np.zeros((size, size), bool)}
    for part in parts:
        if part is None:
            continue
        ya, yb, xa, xb, res, own = part
        written = out["written"][ya:yb, xa:xb]
        put = own | ~written
        for k in res:
            reg = out[k][ya:yb, xa:xb]
            reg[put] = res[k][put]
        written[put] = True
    return out


def _special_threads(cloth, ranges=None):
    return lambda u, t, pp: thread_texels(u, t, pp, cloth, ranges=ranges)


def paint_blocks(atlas, widths: Dict[str, WidthTable], cloth: ClothSpec3, seed: int, crev: Optional[Dict[str, np.ndarray]],
                 supersample: int, special_keys: Sequence[str] = ("threads",), workers: int = 0,
                 thread_ranges: Optional[Sequence[Tuple[float, float, str]]] = None,
                 python_exe: Optional[str] = None, work_dir: Optional[str] = None, log: Callable = print):
    """Evaluate the cloth into every block (padding included), ``supersample``^2 samples per
    texel.  ``workers`` > 1 paints the blocks in that many separate numpy-only Python
    processes (``python_exe``: a Python with numpy, e.g. Blender's bundled one) and merges
    them in block order - the result is identical to painting them in one process."""
    nb = len(atlas.blocks)
    if workers and workers > 1:
        wd = work_dir or tempfile.mkdtemp(prefix="sb_paint_")
        os.makedirs(wd, exist_ok=True)
        crev_paths = {}
        if crev is not None:
            for k, v in crev.items():
                pth = os.path.join(wd, f"crev_{k}.npy")
                np.save(pth, np.asarray(v, np.float32))
                crev_paths[k] = pth
        job = os.path.join(wd, "job.pkl")
        with open(job, "wb") as f:
            pickle.dump({"atlas": atlas, "widths": widths, "cloth": cloth, "seed": seed, "crev": crev_paths,
                         "ss": supersample, "special": list(special_keys),
                         "thread_ranges": list(thread_ranges or [])}, f, protocol=pickle.HIGHEST_PROTOCOL)
        # interleave the blocks so each worker gets a similar load
        order = sorted(range(nb), key=lambda k: -(atlas.blocks[k].w * atlas.blocks[k].h))
        groups = [order[w::workers] for w in range(workers)]
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # Scripts/props
        procs = []
        for w, grp in enumerate(groups):
            outp = os.path.join(wd, f"part_{w:02d}.pkl")
            code = ("import sys; sys.path.insert(0, %r); from props_lib import smokebomb_cloth as C; "
                    "C._worker(%r, %r, %r)" % (here, job, outp, grp))
            env = dict(os.environ)
            env["PYTHONUTF8"] = "1"
            env["OMP_NUM_THREADS"] = "1"
            env["OPENBLAS_NUM_THREADS"] = "1"
            env["MKL_NUM_THREADS"] = "1"
            procs.append((subprocess.Popen([python_exe or sys.executable, "-c", code], env=env,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT), outp))
        parts = [None] * nb
        for p, outp in procs:
            so, _ = p.communicate()
            if p.returncode != 0:
                raise RuntimeError("paint worker failed:\n" + so.decode("utf8", "replace")[-4000:])
            with open(outp, "rb") as f:
                for bi, part in pickle.load(f):
                    parts[bi] = part
            os.remove(outp)
        log(f"  painted {nb} blocks in {workers} workers")
        merged = merge_painted(atlas.size, cloth.roughness, parts)
        for pth in list(crev_paths.values()) + [job]:           # the scratch inputs (~400 MB)
            try:
                os.remove(pth)
            except OSError:
                pass
        return merged
    parts = []
    for bi, b in enumerate(atlas.blocks):
        fn = _special_threads(cloth, thread_ranges) if b.key in special_keys else None
        parts.append(_paint_one(atlas, b, widths.get(b.key), cloth, seed, crev, supersample, fn))
    return merge_painted(atlas.size, cloth.roughness, parts)


def _worker(job_path, out_path, blocks):
    with open(job_path, "rb") as f:
        job = pickle.load(f)
    crev = {k: np.load(v, mmap_mode="r") for k, v in job["crev"].items()} if job["crev"] else None
    atlas = job["atlas"]
    out = []
    for bi in blocks:
        b = atlas.blocks[bi]
        fn = _special_threads(job["cloth"], job.get("thread_ranges")) if b.key in job["special"] else None
        out.append((bi, _paint_one(atlas, b, job["widths"].get(b.key), job["cloth"], job["seed"], crev, job["ss"], fn)))
    with open(out_path, "wb") as f:
        pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)


def spec_dict(c: ClothSpec3) -> Dict[str, object]:
    return asdict(c)


__all__ = ["ClothSpec3", "ClothSpec", "cloth_texels", "thread_texels", "WidthTable", "paint_blocks", "merge_painted", "spec_dict"]
