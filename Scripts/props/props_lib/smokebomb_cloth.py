#!/usr/bin/env python
"""props_lib.smokebomb_cloth - the smoke bomb's cloth, authored in TAPE space (rounds 2-3).

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

ROUND 3 (rewind builder 3; the round-1 and round-2 blind judges both picked the copy 20 of 20)
    * tones are DETAIL units (0..1) and ``gain`` is the default Tint's luminance; the shipped
      Detail stores sqrt(detail) (gamma 2, smokebomb_tape.Shading.detail_power), so the dark weave
      with its bright tail fills the whole 0..1 (median ~56/255; round 2's linear Detail sat at
      5/255) and BaseColor = Detail^2 x Tint reproduces BC exactly;
    * the warps are floats of irregular length with persistent streaks along the tape (the
      reference's band-aligned striations at half size), weft ticks plus weft RUNS over 2-6
      warps (the lit strips' lattice), round crisp glints and specks (roughness 0.55), thin
      fibres that are true ARCS - curls and hooks, never straight hairs;
    * the rolled rim is lit across ``rim_ext_mm`` into the body with bright slanted cross-wraps;
      the covering edge sheds a fringe of fibre ends and hanging LOOPS (true circular arcs) into
      a narrower, darker crevice; a gathered tape (W's twisted section) is a raised double rim.

Every tone is a Detail value; ``gain`` is the one calibration factor.
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
class ClothSpec4:
    """The cloth, round 3 (rewind builder 3).  mm; tones are DETAIL units: 0..1, the value the
    shipped T_SmokeBomb_Detail stores.  ``gain`` (linear albedo luminance of Detail = 1) is the
    default Tint's luminance, so linear albedo = Detail x gain.

    FULL RANGE by design (round 3's promise to the user): the weave's own values span the whole
    0..1 - the valleys between the warps ~0.06-0.12, the float bodies ~0.25-0.45, the lit crests
    ~0.5-0.8, weft ticks, fibres and glints up to 1 - and the default Tint absorbs the darkness.
    Round 2's Detail held the cloth body in 3-12 of 255 levels (median 5/255: recolouring to a
    light dye would posterise); here the median sits near 70/255.  The glints no longer need an
    albedo 50x the body: they are Detail ~1 with a LOWER roughness, and M_SmokeBomb's Specular
    0.5 x Detail^2 (smokebomb_tape.Shading) makes them catch the key light where it is lit.

    REFERENCE_SPEC 7 (px at 13.26 px/mm): warp pitch 4.1 px -> 0.31 mm; weft irregular at ~2x
    the warp pitch; sparkle 4.2 % of pixels > 3x the local mean, warm light grey.
    REFERENCE_SPEC 5/6: rim 4-8 px, crevice 30-47 % darker 2.5-3.5 px beyond it; fray rms 1.5 px
    at 11.5 px.  Looked at 5-6x against the reference crops (never read by the build): warp floats
    of irregular length with a lit crest and dark breaks, bright weft ticks now and then (in the
    lit strips a clear brick lattice), crisp 1-px glints, thin 1-px fibres that are CURLED or
    HOOKED (never straight), a lumpy relief with dark pockets, rolled rims that carry the weave
    with cross-wraps and loose fibre loops falling into a dark crevice."""
    chroma: Tuple[float, float, float] = (0.3835, 0.324, 0.2925)
    #: linear albedo luminance at Detail = 1 (the default Tint's luminance)
    gain: float = 0.4
    # ---- warps
    warp_pitch_mm: float = 0.31
    pitch_jitter: float = 0.22
    pitch_fast: float = 0.10
    wander: float = 0.14
    wander_len_mm: float = 1.3
    gap_d: float = 0.016                 # the shadowed valley between two warps
    body_d: float = 0.03                # the yarn's rounded body
    crest_d: float = 0.12               # the lit crest line, on top of the body
    crest_half_mm: float = 0.06
    crest_offset: float = 0.12
    crest_kink: float = 0.08
    crest_sigma: float = 0.3
    crest_len_mm: float = 4.0
    # the picks: plain weave, floats of IRREGULAR length
    pick_mm: float = 0.31
    pick_wave_mm: float = 0.06
    pick_drift: float = 0.25
    float_warp: float = 0.28
    float_warp_mm: float = 0.55
    float_exp: float = 0.8
    float_sigma: float = 0.35           # per-float tone (lognormal)
    dip_len_mm: float = 0.05
    dip_depth: float = 0.85
    # ---- the pucker / lumps (relief; darker pockets)
    pucker_u_mm: float = 0.8
    pucker_a_mm: float = 2.2
    pucker_h_mm: float = 0.045
    pucker_tone: float = 0.12
    lump_mm: float = 1.4
    lump_h_mm: float = 0.04
    lump_tone: float = 0.15
    streak_mm: float = 0.72
    streak_log: float = 0.25
    mottle: float = 0.03
    # ---- weft: short ticks in the breaks; now and then a bright run across 2-3 warps
    weft_prob: float = 0.6
    weft_w_mm: float = 0.09
    weft_d: Tuple[float, float] = (0.06, 0.4)
    weft_run_prob: float = 0.3
    weft_run_d: Tuple[float, float] = (0.06, 0.35)
    weft_run_min: float = 2.0           # warps a weft run spans
    weft_run_max: float = 6.0
    # ---- glints: crisp bright points on the floats' crests (Detail ~1, lower roughness)
    glint_prob: float = 0.2
    glint_len_mm: Tuple[float, float] = (0.035, 0.055)
    glint_d: Tuple[float, float] = (0.9, 1.0)
    glint_half_mm: float = 0.055
    # free specks anywhere (a lit fibre end)
    speck_cell_mm: float = 0.30
    speck_prob: float = 0.22
    speck_d: Tuple[float, float] = (0.7, 1.0)
    speck_r_mm: float = 0.05
    # ---- surface fibres: thin, CURLED or HOOKED (two arcs meeting at a kink)
    fibre_cell_mm: float = 0.42
    fibre_prob: float = 0.1
    fibre_len_mm: Tuple[float, float] = (0.15, 0.55)
    fibre_half_mm: float = 0.03
    fibre_curl: float = 7.0             # 1/mm, either sense
    fibre_kink_deg: Tuple[float, float] = (50.0, 130.0)
    fibre_kink_share: float = 0.55      # the share that are hooks (a kink), the rest arcs
    fibre_d: Tuple[float, float] = (0.3, 0.8)
    alb_max: float = 1.0
    #: the painter's tones are Detail units: finish_maps stores Detail = alb / gain exactly
    detail_units: bool = True
    # ---- micro relief (mm) for the normal map
    rib_h_mm: float = 0.045
    crest_h_mm: float = 0.008
    fibre_h_mm: float = 0.014
    weft_h_mm: float = 0.010
    pad_h_mm: float = 0.22
    pad_mm: float = 1.4
    # ---- the rolled edge: the same weave rolled over, knuckled by the weft's wraps
    cord_smooth: float = 0.1           # share of a smoother roll tone over the weave on the cord
    cord_d: float = 0.03                # that smoother roll's own tone
    cord_striae: float = 0.30
    under_dark: float = 0.6
    rim_gain: float = 3.5              # the roll's top shows a little more lit fibre
    rim_ext_mm: float = 0.25            # the roll's top runs on this far into the body
    rope_gain: float = 2.2
    rope_twist_mm: float = 0.55          # the twisted section's slanted wraps (period along u)
    rope_ridge_h_mm: float = 0.10        # the two rims' height in the normal map
    wrap_pitch_mm: float = 0.4
    wrap_jitter: float = 0.70
    wrap_prob: float = 0.85
    wrap_half_mm: float = 0.045
    wrap_d: Tuple[float, float] = (0.3, 0.9)
    wrap_slant: float = 0.55
    wrap_bow: float = 0.30
    knuckle_h_mm: float = 0.14
    knuckle_tone: float = 0.3
    joint_prob: float = 0.65
    joint_dark: float = 0.35
    groove_half_mm: float = 0.05
    groove_dark: float = 0.30
    groove_warp_dim: float = 0.20
    groove_warp_mm: float = 0.30
    under_d: float = 0.006               # the skirt's floor ...
    skirt_share: float = 0.5            # ... it keeps this share of the weave
    # ---- the fray and the crevice under a covering edge
    fray_rms_mm: float = 0.11
    fray_len_mm: float = 0.87
    core_mm: float = 0.16
    core_dark: float = 0.85
    crevice_mm: float = 0.6
    crevice_dark: float = 0.85
    occl_mm: float = 1.2
    occl_dark: float = 0.55
    under_edge: float = 0.45
    xfibre_cell_mm: float = 0.22
    xfibre_prob: float = 0.6
    xfibre_len_mm: Tuple[float, float] = (0.2, 0.55)
    xfibre_half_mm: float = 0.036
    xfibre_d: Tuple[float, float] = (0.3, 0.8)
    xfibre_curl: float = 12.0
    # the rim's fringe of short fibre ends
    fringe_cell_mm: float = 0.12
    fringe_prob: float = 0.5
    fringe_len_mm: Tuple[float, float] = (0.08, 0.22)
    fringe_half_mm: float = 0.026
    fringe_d: Tuple[float, float] = (0.12, 0.4)
    # ---- roughness (ORM.G)
    roughness: float = 0.90
    rough_var: float = 0.03
    fibre_roughness: float = 0.70
    glint_roughness: float = 0.55
    crevice_roughness: float = 0.95
    # ---- loose threads (their own block): warm tan, lighter than the tape
    thread_d: float = 0.7
    thread_dark_d: float = 0.05


@dataclass
class ClothSpec5(ClothSpec4):
    """The cloth, round 4 (rewind builder, round 3 of the workflow).  ClothSpec4's fields with
    new defaults plus the round-4 features, each off at ClothSpec4's values.

    What the round-3 blind judge (20 of 20) and the measurer read, and the change:
      * "pale grey piping-like outline strips along every band edge": the rim was painted 3.5x
        and SPILLED 0.25 mm into the body (``rim_ext_mm``) as a pale band.  Now the rolled cord
        keeps the cloth's own tone (a smoother, striated roll), no spill, a crisp dark GROOVE
        line where it meets the body, knuckled by thin bright wrap arcs; its roundness is in
        the NORMAL map (``relief_gain``: the true section minus LOD0's chords, so the cheap
        rounded-shoulder geometry shades as a cord with a groove);
      * "straight grey scratch lines / a lattice": the weft RUNS were straight lines over 2-6
        warps.  Now they are short (1-3 warps), WAVY and slanted (``weft_wave_mm``), fainter;
      * "uniform parallel straight dashes, barcode": shorter, more broken floats with deeper
        breaks and a stronger per-float tone;
      * "short curly bright fibre glints / point highlights": more, smaller specks and more,
        curlier fibres."""
    # ---- weft: short wavy runs, not straight lattice lines
    weft_run_prob: float = 0.3
    weft_run_min: float = 2.0
    weft_run_max: float = 5.0
    weft_run_d: Tuple[float, float] = (0.15, 0.4)
    weft_wave_mm: float = 0.05
    weft_wave_len_mm: float = 0.55
    weft_slant: float = 0.35
    # ---- floats: shorter, more broken
    dip_depth: float = 0.8
    dip_len_mm: float = 0.07
    float_sigma: float = 0.35
    # ---- specks / fibres
    speck_cell_mm: float = 0.26
    speck_prob: float = 0.06
    speck_r_mm: float = 0.05
    fibre_prob: float = 0.1
    fibre_len_mm: Tuple[float, float] = (0.2, 0.6)
    fibre_curl: float = 8.0
    # ---- the rolled edge: the cloth's own tone, a groove, wraps, relief in the normal map
    rim_gain: float = 1.55
    rim_ext_mm: float = 0.0
    cord_smooth: float = 0.85
    cord_d: float = 0.14
    cord_striae: float = 0.35
    groove_half_mm: float = 0.035
    groove_dark: float = 0.4
    wrap_pitch_mm: float = 0.6
    wrap_jitter: float = 0.6
    wrap_prob: float = 0.8
    wrap_half_mm: float = 0.045
    wrap_d: Tuple[float, float] = (0.6, 1.0)
    wrap_bow: float = 0.3
    # ---- the crevice under a covering edge: dark, never black (the measurer: 3x the reference's
    #      near-black area)
    core_dark: float = 0.8
    crevice_dark: float = 0.75
    #: > 0: the normal map carries (true section - LOD0's piecewise-linear section) x this, so
    #: the rolled cord and its groove shade as geometry on LOD0's rounded shoulder
    relief_gain: float = 1.5
    #: the weft's cross-dots (``_weave``): per warp at a pick, this probability x the pick's own
    #: visibility (hash ^ vis_exp); a dot is ``weft_dot_len_mm`` across the warp, ``weft_dot_w_mm``
    #: along the tape
    weft_dot_prob: float = 0.25
    weft_dot_vis_exp: float = 1.5
    weft_dot_d: Tuple[float, float] = (0.35, 1.0)
    weft_dot_len_mm: float = 0.14
    weft_dot_w_mm: float = 0.07
    #: the knuckles' tone swing inside a segment (ClothSpec4: 0.2, a +-20 % ripple; round 4: the
    #: reference's cords are strings of rounded segments, lit in the middle, dark at the joints)
    knuckle_mod: float = 0.75
    pad_h_mm: float = 0.35
    relief_cord_deg: Tuple[float, ...] = (-40.0, 45.0)
    relief_groove: bool = True
    relief_body_chord_mm: float = 3.0
    relief_body_fracs: Tuple[float, ...] = (0.45, 0.0)
    # ---- round 4: ClothSpec4 fields re-set by the whole-ball calibration (build5 c-iterations)
    crevice_mm: float = 1.1
    wrap_slant: float = 0.08
    knuckle_tone: float = 0.4
    joint_dark: float = 0.7
    joint_prob: float = 0.8
    knuckle_h_mm: float = 0.18
    weft_prob: float = 0.1
    weft_d: Tuple[float, float] = (0.1, 0.5)
    weft_w_mm: float = 0.07
    fibre_half_mm: float = 0.022
    fibre_d: Tuple[float, float] = (0.5, 1.0)
    speck_d: Tuple[float, float] = (0.8, 1.0)
    glint_prob: float = 0.2
    fringe_prob: float = 0.7
    fringe_len_mm: Tuple[float, float] = (0.12, 0.4)
    fringe_d: Tuple[float, float] = (0.3, 0.75)
    fringe_half_mm: float = 0.03
    pad_mm: float = 2.2
    crest_half_mm: float = 0.035
    body_d: float = 0.022
    crest_d: float = 0.13
    gap_d: float = 0.018
    gain: float = 0.52
    xfibre_half_mm: float = 0.045
    xfibre_d: Tuple[float, float] = (0.5, 1.0)
    thread_d: float = 0.95
    # ---- round 4: ClothSpec4 fields re-set by the whole-ball calibration (build5 c-iterations)
    float_warp: float = 0.12
    pick_drift: float = 0.12
    pick_wave_mm: float = 0.08
    # ---- round 4: ClothSpec4 fields re-set by the whole-ball calibration (build5 c-iterations)
    streak_log: float = 0.35
    streak_mm: float = 0.55


@dataclass
class ClothSpec6(ClothSpec5):
    """The cloth, final pass (maintainer, 2026-09-25).  ClothSpec5 with the round-3 judge's and
    the craft reviewer's tells taken out:

      * "every edge carries a uniform tubular cord with regular barber-pole ring knuckles - sewn
        piping": the knuckles no longer swing 75 % in tone segment by segment (knuckle_mod 0.35) and at irregular spacing, few joints and few, dim wraps, a 1.3x rim (was 1.55x; the measurer's WLO read +0.66 log against +0.25), a
        low knuckle relief, and the roll carries the WEAVE (cord_smooth 0.45) instead of a smooth
        tube; and over long stretches (``cord_vis_*``) the edge shows no cord at all, only the
        weave turning under into shadow;
      * "grey-flecked tweed / heathered denim: salt-and-pepper specks and curly white squiggles":
        specks cut to a fifth, fibres to 40 % and dimmer, the wavy weft runs mostly gone and
        straight, the low-frequency heather (streaks, pucker / lump tone, mottle, per-float tone)
        cut down - so the weave reads as warp ribs crossed by thin weft ladders (weft ticks in
        most breaks) with scattered broken fibre highlights;
      * "a frosted, sugary sparkle under the gallery rig": glints are fewer, ELONGATED along the
        warp crest (0.07-0.12 mm dashes, the reference's broken fibre highlights, not round
        dots) and rougher (0.68);
      * loose threads: Detail 0.60 (were 0.95, the brightest things on the ball)."""
    speck_prob: float = 0.012
    fibre_prob: float = 0.04
    fibre_d: Tuple[float, float] = (0.35, 0.75)
    weft_run_prob: float = 0.10
    weft_wave_mm: float = 0.015
    weft_slant: float = 0.10
    weft_run_d: Tuple[float, float] = (0.12, 0.30)
    weft_prob: float = 0.6
    weft_d: Tuple[float, float] = (0.20, 0.50)
    weft_dot_d: Tuple[float, float] = (0.3, 0.8)
    glint_prob: float = 0.16
    glint_len_mm: Tuple[float, float] = (0.07, 0.12)
    glint_half_mm: float = 0.03
    glint_roughness: float = 0.68
    streak_log: float = 0.22
    pucker_tone: float = 0.05
    lump_tone: float = 0.05
    mottle: float = 0.0
    float_sigma: float = 0.28
    # ---- the rolled edge: the weave rolled over, not piping
    rim_gain: float = 1.3
    knuckle_mod: float = 0.35
    knuckle_tone: float = 0.15
    joint_prob: float = 0.5
    joint_dark: float = 0.45
    wrap_prob: float = 0.45
    wrap_d: Tuple[float, float] = (0.45, 0.85)
    wrap_jitter: float = 0.9
    knuckle_h_mm: float = 0.10
    cord_smooth: float = 0.55
    groove_dark: float = 0.3
    relief_gain: float = 1.1
    #: > 0: along each edge a low-frequency visibility (wavelength ~ this, mm): where it is low
    #: the cord's own tone, wraps and knuckles fade out and the edge is just the weave turning
    #: under into shadow; ``cord_vis_share`` of the edge length is faded
    cord_vis_len_mm: float = 3.0
    cord_vis_share: float = 0.2
    thread_d: float = 0.60
    # ---- tones: the whole-ball calibration at the reference view (final pass c6 iterations,
    #      WorkFiles/smokebomb/final_pass/c6a..c6e; tones p10/p50/p90 within +-12 %, sparkle 3-5.5 %)
    gain: float = 0.55
    crest_d: float = 0.15
    weft_dot_prob: float = 0.35
    # ---- the crevice under a covering edge: a soft dark line, not a serrated row of black teeth
    core_dark: float = 0.6
    crevice_dark: float = 0.6
    fringe_prob: float = 0.15
    xfibre_prob: float = 0.35
    under_d: float = 0.05
    skirt_share: float = 0.75
    under_dark: float = 0.4


#: the build's name for the current calibration
ClothSpec = ClothSpec6


def _weave(u, a, c: ClothSpec4, seed: int, aa: float):
    """Plain weave, warp-faced, in tape space (u along, a across, mm); Detail units.

    Warp i passes OVER pick k when k + i is even, so each warp shows as FLOATS about two picks
    long, staggered from its neighbours; the float boundaries wander along each thread, so the
    lattice is never regular.  A float is brightest along its lit crest and dips into a dark
    break where it dives under the weft; each float has its own tone.  The weft shows as a short
    tick in a break now and then, and every so often floats over two or three warps as a bright
    cross line (the reference's lit strips read as a brick lattice).  Glints are crisp points ON
    a crest.  A pucker / lump relief shades the cloth and darkens its pockets.
    Returns (D, height, crest coverage, thread index, glint coverage)."""
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
    w = 0.5 * (v - np.mod(i, 2.0))
    w = w + c.float_warp * VN_RMS * 0.6 * vnoise1(u / c.float_warp_mm + 17.3 * i, seed + 12)
    fid = np.floor(w)
    fp = w - fid
    endd = np.minimum(fp, 1.0 - fp) * 2.0 * qp
    dip = _smoothstep(0.0, c.dip_len_mm, endd - 0.5 * c.weft_w_mm)
    dipf = 1.0 - c.dip_depth * (1.0 - dip)
    shape = np.sin(np.pi * fp) ** c.float_exp
    ft = np.exp(c.float_sigma * np.clip(gauss(i, fid, seed=seed + 9), -2.2, 2.2))
    ft = ft * np.exp(c.crest_sigma * VN_RMS * 0.6 * vnoise1(u / c.crest_len_mm + 37.1 * i, seed + 8))
    dx = (x - 0.5 - c.crest_offset * (2 * hash01(i, seed=seed + 11) - 1)
          - c.crest_kink * (2 * hash01(i, fid, seed=seed + 10) - 1)) * p
    cline = _line(dx, c.crest_half_mm, aa)
    crest = cline * dipf * (0.3 + 0.7 * shape)
    D = c.gap_d + c.body_d * body * dipf * (0.45 + 0.55 * shape) * np.sqrt(ft) + c.crest_d * crest * ft
    h = c.rib_h_mm * body * (0.45 + 0.55 * dip * shape) + c.crest_h_mm * crest
    # the weft at a break: a short cross-tick one warp wide
    du_x = (np.where(fp < 0.5, fp, fp - 1.0)) * 2.0 * qp
    wshow = hash01(i, fid, seed=seed + 62) < c.weft_prob
    wl = _line(du_x, 0.5 * c.weft_w_mm, aa) * _smoothstep(0.05, 0.30, x) * _smoothstep(0.95, 0.70, x) * wshow
    wd = c.weft_d[0] + (c.weft_d[1] - c.weft_d[0]) * hash01(i, fid, seed=seed + 64) ** 1.3
    D = np.maximum(D, wd * wl)
    h = h + c.weft_h_mm * wl
    # now and then the weft floats over several warps: a cross line (the reference's lit strips
    # read as a lattice); each pick is cut into runs of 2..weft_run_max warps
    kpk = np.floor(v + 0.5)
    rl_len = c.weft_run_min + (c.weft_run_max - c.weft_run_min) * hash01(kpk, seed=seed + 68)
    j0 = np.floor((i + rl_len * hash01(kpk, seed=seed + 65)) / rl_len)
    runon = hash01(j0, kpk, seed=seed + 66) < c.weft_run_prob
    duk = (v - kpk) * qp
    wav = getattr(c, "weft_wave_mm", 0.0)
    if wav > 0.0:
        # round 4: a weft run is a WAVY, slanted thread over 1-3 warps (never a straight lattice
        # line): displaced along u by a sine across a and a per-run slant about the run's centre
        h65 = hash01(kpk, seed=seed + 65)
        ic = (j0 + 0.5) * rl_len - rl_len * h65
        ph = 2.0 * np.pi * hash01(j0, kpk, seed=seed + 69)
        sl = (2.0 * hash01(j0, kpk, seed=seed + 70) - 1.0) * c.weft_slant
        duk = duk - wav * np.sin(2.0 * np.pi * a / c.weft_wave_len_mm + ph) - sl * (g - ic) * p
        # the run dives under at its ends
        endf = np.minimum(g - (ic - 0.5 * rl_len), (ic + 0.5 * rl_len) - g)
        runon = runon * _smoothstep(0.0, 0.35, endf)
    rl = _line(duk, 0.5 * c.weft_w_mm, aa) * runon
    rd = c.weft_run_d[0] + (c.weft_run_d[1] - c.weft_run_d[0]) * hash01(j0, kpk, seed=seed + 67)
    D = np.maximum(D, rd * rl)
    h = h + c.weft_h_mm * rl
    # glints: crisp bright points ON a float's crest
    gon = hash01(i, fid, seed=seed + 81) < c.glint_prob
    gpos = 0.2 + 0.6 * hash01(i, fid, seed=seed + 82)
    sg = c.glint_len_mm[0] + (c.glint_len_mm[1] - c.glint_len_mm[0]) * hash01(i, fid, seed=seed + 83)
    G = c.glint_d[0] + (c.glint_d[1] - c.glint_d[0]) * hash01(i, fid, seed=seed + 84)
    gcov = gon * np.exp(-0.5 * (((fp - gpos) * 2.0 * qp) / sg) ** 2) * _line(dx, c.glint_half_mm, aa)
    D = np.maximum(D, G * gcov)
    wdp = getattr(c, "weft_dot_prob", 0.0)
    if wdp > 0.0:
        # round 4: the weft's CROSS-DOTS - where a pick floats over a warp it catches the light as a
        # short bright tick across that warp's crest.  Each pick has its own visibility (some
        # picks show at most warps, most at few), so the dots line up ACROSS the tape into the
        # reference's irregular crosshatch instead of a random static of specks
        vis = hash01(kpk, seed=seed + 91) ** c.weft_dot_vis_exp
        don = hash01(i, kpk, seed=seed + 92) < wdp * vis
        dd = c.weft_dot_d[0] + (c.weft_dot_d[1] - c.weft_dot_d[0]) * hash01(i, kpk, seed=seed + 93)
        dxc = (x - 0.5 - 0.25 * (2 * hash01(i, kpk, seed=seed + 94) - 1)) * p
        dcov = don * _line(duk, 0.5 * c.weft_dot_w_mm, aa) * _line(dxc, 0.5 * c.weft_dot_len_mm, aa)
        D = np.maximum(D, dd * dcov)
        h = h + c.weft_h_mm * dcov
        gcov = np.maximum(gcov, dcov * (dd > 0.6))
    # the pucker: cross-ridges (short along u, long across) + lumps; relief with dim pockets
    pk = VN_RMS * 0.75 * fbm2(u / c.pucker_u_mm + 0.25 * a / c.pucker_a_mm, a / c.pucker_a_mm, seed + 44, 2)
    lm = VN_RMS * 0.75 * fbm2(u / c.lump_mm, a / c.lump_mm, seed + 45, 2)
    h = h + c.pucker_h_mm * pk + c.lump_h_mm * lm
    relief = np.exp(np.clip(c.pucker_tone * pk + c.lump_tone * lm, -0.9, 0.9))
    st = np.exp(c.streak_log * VN_RMS * 0.7 * (vnoise1(a / c.streak_mm + 0.012 * u, seed + 41)
                                               + 0.45 * vnoise1(a / (0.47 * c.streak_mm) + 5.0, seed + 42)) / 1.1)
    D = D * st * relief * (1.0 + c.mottle * fbm2(u / 3.0, a / 2.4, seed + 4, 2))
    return D, h, cline, i, np.clip(gcov, 0.0, 1.0)


def _seg_dist(px, py, ox, oy, ca, sa, L, kap):
    """Distance from (px, py) to a true circular ARC starting at (ox, oy) heading (ca, sa),
    length L, signed curvature kap (1/mm; + turns left); also the arc parameter t in [0, L].
    A tight curvature gives a real loop ("c" / "?" shapes), never a parabola."""
    kap = np.asarray(kap, np.float64)
    dx, dy = px - ox, py - oy
    # straight fallback where the arc is nearly flat
    tt = dx * ca + dy * sa
    nn = -dx * sa + dy * ca
    flat = np.abs(kap) < 1e-3
    tcf = np.clip(tt, 0.0, L)
    d_flat = np.sqrt((nn) ** 2 + (tt - tcf) ** 2)
    ks = np.where(flat, 1.0, kap)
    r = 1.0 / np.abs(ks)
    sg = np.sign(ks)
    # centre: r along the left normal (-sa, ca) for a left turn
    cx = ox - sa * r * sg
    cy = oy + ca * r * sg
    th0 = np.arctan2(oy - cy, ox - cx)
    thp = np.arctan2(py - cy, px - cx)
    dth = np.mod((thp - th0) * sg, 2.0 * np.pi)        # swept angle from the start, in the turn's sense
    sweep = np.minimum(L * np.abs(ks), 2.0 * np.pi - 1e-6)
    inside = dth <= sweep
    rp = np.hypot(px - cx, py - cy)
    d_arc = np.abs(rp - r)
    # outside the swept range: nearest end point
    ex = cx + r * np.cos(th0 + sg * sweep)
    ey = cy + r * np.sin(th0 + sg * sweep)
    d_end = np.minimum(np.hypot(px - ox, py - oy), np.hypot(px - ex, py - ey))
    t_arc = np.where(inside, dth * r, np.where(np.hypot(px - ox, py - oy) < np.hypot(px - ex, py - ey), 0.0, L))
    d = np.where(inside, d_arc, d_end)
    return np.where(flat, d_flat, d), np.where(flat, tcf, t_arc)


def _fibres(u, a, c: ClothSpec4, seed, aa, cell=None, prob=None, lens=None, half=None, dvals=None):
    """Thin surface fibres in a jittered grid: each is two ARCS meeting at a point - a HOOK (a
    kink of 50-130 deg) or a smooth CURL (no kink, the second arc curling on) - tapering at the
    free ends; never a straight hair.  Returns (coverage, Detail value)."""
    cell = c.fibre_cell_mm if cell is None else cell
    prob = c.fibre_prob if prob is None else prob
    lens = c.fibre_len_mm if lens is None else lens
    half = c.fibre_half_mm if half is None else half
    dvals = c.fibre_d if dvals is None else dvals
    ci, cj = np.floor(u / cell), np.floor(a / cell)
    cov = np.zeros_like(u)
    val = np.zeros_like(u)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            present = hash01(I, J, seed=seed) < prob
            if not np.any(present):
                continue
            cx = (I + hash01(I, J, seed=seed + 1)) * cell
            cy = (J + hash01(I, J, seed=seed + 2)) * cell
            L = lens[0] + (lens[1] - lens[0]) * hash01(I, J, seed=seed + 3) ** 1.3
            k = 0.3 + 0.4 * hash01(I, J, seed=seed + 4)
            ang = 2.0 * np.pi * hash01(I, J, seed=seed + 5)
            sgn = np.where(hash01(I, J, seed=seed + 6) < 0.5, -1.0, 1.0)
            kap1 = sgn * c.fibre_curl * (0.4 + 1.2 * hash01(I, J, seed=seed + 7))
            hook = hash01(I, J, seed=seed + 8) < c.fibre_kink_share
            kd = np.radians(c.fibre_kink_deg[0] + (c.fibre_kink_deg[1] - c.fibre_kink_deg[0]) * hash01(I, J, seed=seed + 9))
            kink = np.where(hook, kd * np.where(hash01(I, J, seed=seed + 10) < 0.5, -1.0, 1.0), 0.0)
            kap2 = np.where(hook, -kap1 * 0.5, kap1 * 1.6)
            # arc 1 runs BACK from the kink point (cx, cy) along -ang; arc 2 runs on from it,
            # turned by the kink (a curl keeps curling: its second arc tighter)
            d1, t1 = _seg_dist(u, a, cx, cy, np.cos(ang + np.pi), np.sin(ang + np.pi), k * L, -kap1)
            a2 = ang + kink
            d2, t2 = _seg_dist(u, a, cx, cy, np.cos(a2), np.sin(a2), (1.0 - k) * L, kap2)
            d = np.minimum(d1, d2)
            # taper toward both free ends
            s_end = np.where(d1 < d2, t1 / np.maximum(k * L, 1e-6), t2 / np.maximum((1.0 - k) * L, 1e-6))
            taper = 0.35 + 0.65 * np.cos(0.5 * np.pi * np.clip(s_end, 0, 1))
            hw = half * (0.7 + 0.6 * hash01(I, J, seed=seed + 11))
            cv = _line(d, hw, aa) * present
            vv = (dvals[0] + (dvals[1] - dvals[0]) * hash01(I, J, seed=seed + 12) ** 1.2) * taper
            better = cv * vv > cov * val
            val = np.where(better, vv, val)
            cov = np.maximum(cov, cv)
    return cov, val


def _specks(u, a, c: ClothSpec4, seed: int, aa: float):
    """Free fibre-end specks: tiny, crisp, bright points.  Returns (coverage, Detail value)."""
    cell = c.speck_cell_mm
    ci, cj = np.floor(u / cell), np.floor(a / cell)
    cov = np.zeros_like(u)
    val = np.zeros_like(u)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            I, J = ci + di, cj + dj
            on = hash01(I, J, seed=seed) < c.speck_prob
            cx = (I + hash01(I, J, seed=seed + 1)) * cell
            cy = (J + hash01(I, J, seed=seed + 2)) * cell
            d = np.hypot(u - cx, a - cy)
            G = c.speck_d[0] + (c.speck_d[1] - c.speck_d[0]) * hash01(I, J, seed=seed + 3)
            cv = on * _line(d, c.speck_r_mm, aa)
            better = cv * G > cov * val
            val = np.where(better, G, val)
            cov = np.maximum(cov, cv)
    return cov, val


def _wraps(u, e, c: ClothSpec4, aa: float, seed: int, e_mid: float = 0.0, e_half: float = 0.4):
    """The rolled edge's knuckles: the roll is SEGMENTED at an irregular spacing by slanted
    joints (the weft's selvedge wraps).  Some joints show a curved light loop (the wrap), most a
    dark groove; each knuckle bulges with its own height and tone.  Returns the loop coverage
    and Detail value, the knuckle height (normal map) and the knuckle's tone factor."""
    kp = c.wrap_pitch_mm
    en = (e - e_mid) / max(e_half, 1e-6)
    lv = (u / kp + c.wrap_jitter * VN_RMS * 0.5 * vnoise1(u / 1.1, seed + 21) + c.wrap_slant * e / kp
          + c.wrap_bow * en * en)
    kj = np.floor(lv + 0.5)
    fr = lv - kj
    on = hash01(kj, seed=seed + 23) < c.wrap_prob
    cov = _line(np.abs(fr) * kp, c.wrap_half_mm, aa) * on
    val = c.wrap_d[0] + (c.wrap_d[1] - c.wrap_d[0]) * hash01(kj, seed=seed + 24) ** 1.2
    gdist = np.abs(fr - 0.12 * np.where(hash01(kj, seed=seed + 26) < 0.5, 1.0, -1.0)) * kp
    groove = _line(gdist, 0.04, aa) * (hash01(kj, seed=seed + 27) < c.joint_prob)
    kk = np.floor(lv)
    fk = lv - kk
    hk = 0.35 + 0.65 * hash01(kk, seed=seed + 25)
    bulge = np.sin(np.pi * fk) ** 1.5 * hk - 0.7 * groove
    km = getattr(c, "knuckle_mod", 0.2)
    if km == 0.2:
        ktone = np.exp(c.knuckle_tone * (2.0 * hash01(kk, seed=seed + 28) - 1.0)) * (0.8 + 0.4 * np.sin(np.pi * fk))
    else:
        # round 4: each knuckle is a rounded segment - lit in its middle, dark at its joints
        ktone = np.exp(c.knuckle_tone * (2.0 * hash01(kk, seed=seed + 28) - 1.0))             * ((1.0 - km) + km * np.sin(np.pi * fk) ** 0.8 / 0.69)
    ktone = ktone * (1.0 - c.joint_dark * groove)
    return cov, val, bulge, ktone


def section_relief(tc, width, prof: T.Profile, cord_deg=(-60.0, 30.0), body_chord_mm: float = 3.0,
                   body_fracs=(0.45, 0.0), skirt: bool = True, groove: bool = False) -> np.ndarray:
    """(true section - LOD0's piecewise-linear section) along the chord's normal, mm, at centred
    ``tc`` for a tape ``width`` wide: what LOD0's rounded-shoulder geometry leaves out (the
    cord's round, the groove, the crown between body points).  LOD0's section points are
    smokebomb_ball.section_points (the cord at ``cord_deg``, body points no more than
    ``body_chord_mm`` apart at this width, the skirt foot), so the normal map made from this
    height shades LOD0 as the true section.  numpy only."""
    tc = np.asarray(tc, np.float64)
    w = np.broadcast_to(np.asarray(width, np.float64), tc.shape)
    x = np.abs(tc)
    m = (prof.region == T.CORD) & (prof.side == -1)
    ph, tt = prof.phi[m], prof.tc[m]
    o = np.argsort(ph)
    cords = sorted(abs(float(np.interp(math.radians(d), ph[o], tt[o]))) for d in cord_deg
                   if math.radians(d) < prof.phi_j - 1e-6)
    if groove:                                       # the cord / body junction is a section point
        cords = sorted(cords + [abs(float(np.interp(prof.phi_j, ph[o], tt[o])))])
    dW = prof.dW(w)
    tbw = np.maximum(prof.tb0 + dW, 0.2)
    mb = prof.region == T.BODY
    ab, tb = prof.a[mb], prof.tc[mb]
    amax = ab.max()
    Aw = amax + dW
    n = np.maximum(np.ceil(np.maximum(Aw, 1e-6) / body_chord_mm - 1e-9), 1.0)
    order_b = np.argsort(ab)
    ab_s, tb_s = ab[order_b], tb[order_b]
    pos = ab_s >= 0

    def tc_body(fr):
        return np.interp(fr * amax, ab_s, tb_s) * tbw / prof.tb0

    # x's own body fraction (only meaningful on the body)
    f_of_x = np.interp(x * prof.tb0 / tbw, tb_s[pos], ab_s[pos]) / amax
    use_n = n >= 2
    fl_n = np.floor(f_of_x * n) / n
    fr_n = np.minimum(fl_n + 1.0 / n, 1.0)
    fr_fixed = np.sort(np.asarray(body_fracs, np.float64))
    k = np.clip(np.searchsorted(fr_fixed, f_of_x, side="right") - 1, 0, len(fr_fixed) - 1)
    fl_f = fr_fixed[k]
    fr_f = np.where(k + 1 < len(fr_fixed), fr_fixed[np.minimum(k + 1, len(fr_fixed) - 1)], 1.0)
    f_lo = np.where(use_n, fl_n, fl_f)
    f_hi = np.where(use_n, fr_n, fr_f)
    last_body = np.where(use_n, (n - 1.0) / n, fr_fixed[-1])
    x_last = tc_body(last_body)
    pts = [cc + dW for cc in cords]                  # actual |tc| of the cord points, inner .. outer
    pts = pts[::-1] if len(pts) > 1 and np.all(pts[0] > pts[-1]) else pts
    x_sk = prof.thalf0 + dW
    seq = [x_last] + sorted(pts, key=lambda z: float(np.mean(z))) + ([x_sk] if skirt else [])
    body_side = x <= x_last
    x0 = np.where(body_side, tc_body(f_lo), np.nan)
    x1 = np.where(body_side, np.minimum(tc_body(f_hi), x_last), np.nan)
    for lo_, hi_ in zip(seq[:-1], seq[1:]):
        inside = (~body_side) & (x >= lo_) & (x <= hi_)
        x0 = np.where(inside, lo_, x0)
        x1 = np.where(inside, hi_, x1)
    beyond = ~(np.isfinite(x0) & np.isfinite(x1)) | (x1 - x0 < 1e-6)
    x0 = np.where(beyond, x, x0)
    x1 = np.where(beyond, x + 1e-3, x1)
    sgn = np.where(tc < 0, -1.0, 1.0)
    q = prof.section(tc, w)
    q0 = prof.section(sgn * x0, w)
    q1 = prof.section(sgn * x1, w)
    f = np.clip((x - x0) / np.maximum(x1 - x0, 1e-9), 0.0, 1.0)
    la = q0["a"] + f * (q1["a"] - q0["a"])
    lh = q0["h"] + f * (q1["h"] - q0["h"])
    da, dh = q1["a"] - q0["a"], q1["h"] - q0["h"]
    L = np.maximum(np.hypot(da, dh), 1e-9)
    na, nh = -dh / L, da / L
    # the normal pointing away from the tape's inside: up on the body, outward on the cord
    out_a = np.where(np.abs(la) > 1e-9, np.sign(la), 0.0)
    flip = (nh * 1.0 + na * out_a * 0.5) < 0
    na, nh = np.where(flip, -na, na), np.where(flip, -nh, nh)
    d = (q["a"] - la) * na + (q["h"] - lh) * nh
    return np.where(beyond, 0.0, d)


def cloth_texels(u, tc, prof: T.Profile, c: ClothSpec4, ppmm: float, width, seed: int = 1, tape_id: int = 0,
                 crev: Optional[Dict[str, np.ndarray]] = None, gather=None) -> Dict[str, np.ndarray]:
    """The cloth at tape coordinates (u, tc), flat arrays (smokebomb_tape.cloth_texels'
    contract): ``alb`` = Detail x gain (linear albedo luminance), ``hgt`` (mm), ``rough``, ``ao``.
    ``gather`` (0 flat .. 1 a rope): a gathered tape is its two rolled edges side by side."""
    u = np.asarray(u, np.float64)
    tc = np.asarray(tc, np.float64)
    aa = 0.5 / ppmm
    q = prof.section(tc, width)
    e, region = q["e"], q["region"]
    a = tc
    ss = seed * 1009 + tape_id * 7919
    D, h, crest, ti, gcov = _weave(u, a, c, ss, aa)
    on_cord = region == CORD
    ej = prof.spec.cord_r_mm * prof.phi_j
    fray = c.fray_rms_mm * VN_RMS * 0.8 * (vnoise1(u / c.fray_len_mm, ss + 80)
                                          + 0.35 * vnoise1(u / (0.37 * c.fray_len_mm), ss + 81))
    under = _smoothstep(0.10, -0.30, e - 0.6 * fray)
    e_lo = -0.5 * math.pi * prof.spec.cord_r_mm
    wc, wd, bulge, ktone = _wraps(u + 997.0 * (q["side"] > 0), e, c, aa, seed * 131 + tape_id * 17,
                                  e_mid=0.5 * (ej + e_lo), e_half=0.5 * (ej - e_lo))
    top = _smoothstep(-0.20, 0.10, e - 0.5 * fray) * (1.0 - _smoothstep(ej + c.rim_ext_mm - 0.10, ej + c.rim_ext_mm + 0.02, e))
    striae = np.exp(c.cord_striae * VN_RMS * 0.6 * vnoise2(u / 0.35, e / 0.05, ss + 85))
    roll = c.cord_d * striae
    ctone = (1.0 - c.cord_smooth) * D + c.cord_smooth * roll
    cord_D = np.maximum(ctone * (1.0 + (c.rim_gain - 1.0) * top) * ktone, wd * wc) * (1.0 - c.under_dark * under)
    # round 3: the roll's lit top runs on ``rim_ext_mm`` into the body (the reference's rims are
    # 4-8 px = 0.3-0.6 mm wide; LOD0's rounded shoulder carries the cord in fewer pixels)
    rim_w = np.where(on_cord, 1.0, (region == BODY) * (1.0 - _smoothstep(ej, ej + c.rim_ext_mm, e)))
    cvl = getattr(c, "cord_vis_len_mm", 0.0)
    if cvl > 0.0:
        # final pass: over long stretches of edge the cord fades out - only the weave turning
        # under into shadow shows (the reference's edges are intermittent rolled lips)
        nv = VN_RMS * 0.7 * vnoise1(u / cvl + 53.0 * (q["side"] > 0) + 0.37 * tape_id, ss + 97)
        thr = (c.cord_vis_share - 0.5) * 1.2
        vis = _smoothstep(thr - 0.25, thr + 0.25, nv)
        plain = D * (1.0 - c.under_dark * under)
        cord_D = plain + (cord_D - plain) * vis
        bulge = bulge * vis
        wc = wc * vis
    D = D * (1.0 - rim_w) + cord_D * rim_w
    h = h + rim_w * (c.knuckle_h_mm * bulge + 0.01 * wc)
    if gather is not None:
        # round 3: a gathered tape (W's twisted section) is the tape seen EDGE-ON: its two rolled
        # rims side by side, a groove between them (REFERENCE_SPEC 4.2 "a raised double rolled
        # rim"); round 2 painted the whole rope one tone and it read as a thin dark rod.  Across
        # the (compressed) width: two bright ridges at |x| ~ 0.5, dark at the centre and the
        # sides; along it the twist's slanted wraps.
        rope = _smoothstep(0.55, 0.95, np.asarray(gather, np.float64)) * (region == BODY)
        xw = np.clip(tc / np.maximum(0.5 * np.asarray(width, np.float64), 1e-6), -1.0, 1.0)
        ridge = np.exp(-(((np.abs(xw) - 0.5) / 0.24) ** 2))
        twist = 0.75 + 0.25 * np.sin(2.0 * np.pi * (u / c.rope_twist_mm + 1.3 * xw))
        base = (1.0 - c.cord_smooth) * D + c.cord_smooth * roll
        rope_D = np.maximum(base * c.rope_gain * ktone * (0.65 + 0.75 * ridge) * twist, wd * wc * (0.5 + 0.5 * ridge))
        D = D * (1.0 - rope) + rope_D * rope
        h = h + rope * (c.knuckle_h_mm * bulge + c.rope_ridge_h_mm * ridge)
    D = D * (1.0 - c.groove_warp_dim * (1.0 - _smoothstep(ej, ej + c.groove_warp_mm, e)))
    groove = np.exp(-0.5 * ((e - ej) / c.groove_half_mm) ** 2) * (region != SKIRT)
    D = D * (1.0 - c.groove_dark * groove)
    h = h + c.pad_h_mm * _smoothstep(ej, ej + c.pad_mm, e) * (region == BODY)
    rg = getattr(c, "relief_gain", 0.0)
    if rg > 0.0:
        h = h + rg * section_relief(tc, width, prof, c.relief_cord_deg, c.relief_body_chord_mm,
                                    c.relief_body_fracs, groove=getattr(c, "relief_groove", False))
    # fibres and specks lie on everything visible
    f_cov, f_val = _fibres(u, a, c, ss + 50, aa)
    face = ((region == BODY) | on_cord) * np.where(on_cord, 1.0 - 0.7 * under, 1.0)
    fib = f_cov * face
    D = D * (1 - fib) + f_val * fib
    s_cov, s_val = _specks(u, a, c, ss + 70, aa)
    s_cov = s_cov * face
    D = np.maximum(D, s_val * s_cov)
    hgt = h + c.fibre_h_mm * fib
    D = np.where(region == SKIRT, np.maximum(c.under_d, c.skirt_share * D), D)
    ao = np.ones_like(u)
    rough = c.roughness + c.rough_var * fbm2(u / 1.7, a / 1.7, ss + 90, 2)
    rough = rough * (1 - fib) + c.fibre_roughness * fib
    shine = np.clip(np.maximum(gcov * (region == BODY), s_cov), 0.0, 1.0)
    rough = rough * (1 - shine) + c.glint_roughness * shine
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
        D = np.where(near | fuzz, D * shade, D)
        D = np.where(covered, D * c.under_edge, D)
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
            # a fibre leaves the covering edge (edge_u = s0, beyond = -0.04) heading into the
            # crevice and CURLS (a true arc: tight ones close into the reference's hanging loops)
            kap = np.where(hash01(I, esd, etp, seed=es + 9) < 0.5, -1.0, 1.0) * c.xfibre_curl                 * (0.5 + hash01(I, esd, etp, seed=es + 7))
            dist, tcl = _seg_dist(eu, bcl, s0, -0.04, np.sin(ang), np.cos(ang), L, kap)
            cv = _line(dist, c.xfibre_half_mm, aa) * on
            g = c.xfibre_d[0] + (c.xfibre_d[1] - c.xfibre_d[0]) * hash01(I, esd, etp, seed=es + 8)
            g = g * (1.0 - 0.4 * np.clip(tcl / np.maximum(L, 1e-6), 0, 1))
            better = cv * g > xc * xl
            xl = np.where(better, g, xl)
            xc = np.maximum(xc, cv)
        # the rim's fringe: short fibre ends standing off the covering edge ("eyelashes")
        if c.fringe_prob > 0:
            cell = c.fringe_cell_mm
            ci = np.floor(eu / cell)
            for dci in (-1, 0, 1):
                I = ci + dci
                on = (hash01(I, esd, etp, seed=es + 23) < c.fringe_prob) & (near | fuzz)
                s0 = (I + hash01(I, esd, etp, seed=es + 24)) * cell
                L = c.fringe_len_mm[0] + (c.fringe_len_mm[1] - c.fringe_len_mm[0]) * hash01(I, esd, etp, seed=es + 25)
                ang = (2 * hash01(I, esd, etp, seed=es + 26) - 1) * 0.7
                kap = (2 * hash01(I, esd, etp, seed=es + 27) - 1) * 4.0
                dist, tcl = _seg_dist(eu, bcl, s0, -0.05, np.sin(ang), np.cos(ang), L, kap)
                cv = _line(dist, c.fringe_half_mm, aa) * on
                g = (c.fringe_d[0] + (c.fringe_d[1] - c.fringe_d[0]) * hash01(I, esd, etp, seed=es + 28))                     * (1.0 - 0.6 * np.clip(tcl / np.maximum(L, 1e-6), 0, 1))
                better = cv * g > xc * xl
                xl = np.where(better, g, xl)
                xc = np.maximum(xc, cv)
        D = D * (1 - xc) + xl * xc
        hgt = hgt + 0.012 * xc
        rough = rough * (1 - xc) + c.fibre_roughness * xc
        occ = np.where(near | fuzz, np.exp(-np.clip(bb, 0, None) / (0.45 * c.occl_mm)), 0.0)
        ao = np.where(near | fuzz, 1.0 - c.occl_dark * occ, ao)
        ao = np.where(covered, 0.3, ao)
        rough = np.where(near, rough * (1 - crv) + c.crevice_roughness * crv, rough)
    ao = ao * (1.0 - 0.30 * groove)
    ao = np.where(region == SKIRT, 0.35, ao)
    alb = np.clip(D, 0.0, c.alb_max) * c.gain
    return {"alb": alb, "hgt": hgt, "rough": np.clip(rough, 0.0, 1.0), "ao": np.clip(ao, 0.0, 1.0)}


def thread_texels(u, t, ppmm: float, c: ClothSpec4, seed: int = 3,
                  ranges: Optional[Sequence[Tuple[float, float, str]]] = None) -> Dict[str, np.ndarray]:
    """The loose threads' own block: warm tan multi-fibre yarn (the dye at a lighter tone, so a
    recolour tints it too) - fibres along it, the twist as a faint slant, lit fibre tips.
    ``ranges`` [(u0, u1, tone)]: parts whose tone is 'cloth' take the tape's own tone instead."""
    u = np.asarray(u, np.float64)
    t = np.asarray(t, np.float64)
    aa = 0.5 / ppmm
    tw = 0.75 + 0.25 * np.sin(2 * np.pi * (u / 0.31 + t / 0.17))
    fib = 1.0 + 0.30 * vnoise2(u / 0.08, t / 0.03, seed) + 0.15 * vnoise2(u / 0.3, t / 0.1, seed + 1)
    lum = np.full_like(u, c.thread_d)
    if ranges:
        for u0, u1, tone in ranges:
            if tone == "cloth":
                lum = np.where((u >= u0 - 0.25) & (u <= u1 + 0.25), c.thread_dark_d, lum)
    D = lum * tw * fib
    D = np.maximum(D, np.minimum(1.0, 1.3 * lum) * _line(np.abs(np.mod(t + 0.3 * u, 0.09) - 0.045), 0.008, aa))
    return {"alb": np.clip(D, 0.0, c.alb_max) * c.gain,
            "hgt": 0.004 * np.sin(2 * np.pi * (u / 0.31 + t / 0.17)),
            "rough": np.full_like(u, 0.75), "ao": np.ones_like(u)}


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


def paint_blocks(atlas, widths: Dict[str, WidthTable], cloth: ClothSpec4, seed: int, crev: Optional[Dict[str, np.ndarray]],
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


def spec_dict(c: ClothSpec4) -> Dict[str, object]:
    return asdict(c)


__all__ = ["ClothSpec4", "ClothSpec5", "ClothSpec6", "ClothSpec", "section_relief", "cloth_texels", "thread_texels", "WidthTable", "paint_blocks", "merge_painted", "spec_dict"]
