"""The entrance hero's own tiling texture sets (hero_entrance, reference sheet WorkFiles/armory/reference/entrance.png):

  T_AK_HEntTimber_BC / _ORM / _N   the sheet's charred / weathered near-black timber: a near-black body with strong
                                   lighter grey-brown grain streaks and flecks, a few fine checks (dark cracks) along
                                   the grain, rougher light streaks; the grain runs along V (hero_entrance maps V to
                                   each member's long axis). 2048 px, tiled every 1.0 m (hero_entrance.TIMBER_TILE)
  T_AK_HEntMat_BC / _ORM / _N      the sheet's golden woven rush mat (tatami-like): fine parallel rush strands along U
                                   bound by darker weft threads every ~2.5 cm, strand-to-strand golden / straw / pale
                                   olive variation. 1024 px, tiled every 0.5 m on the mat field
  final fix r5 (new sets, the older ones are kept): T_AK_HEntTimberW (warmer, heavier grain, knots), T_AK_HEntCoir
  (a nubby coir basket weave, no linear ribs), T_AK_HEntBronze (aged bronze with patina; metallic varies in ORM.B)
  genkan r4 (2026-09-28, new sets): T_AK_HEntSisal (the genkan mat's chunky grey-brown knotted sisal rows) and
  T_AK_HEntTimberG (the step beam's lighter weathered top face: the ebony grain in a greyed brown)

Blind judge (layout 2 r3, deltas 4 and 6): the kit's M_AK_Timber read as a flat low-contrast grey-brown on the entrance
and M_AK_Mat as a flat grey-beige; the sheet has near-black grain with lighter worn streaks and a golden straw mat.
Seamless (periodic FFT noise and whole-period sines), original and procedural (no photo, scan or third-party source).
Uses make_armory_textures' writers (same PNG / DirectX-normal conventions). Never overwrites another set.

Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_entrance.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_armory_textures as MT  # noqa: E402


def _check(name):
    for suf in ("BC", "ORM", "N"):
        p = MT.OUT / f"T_AK_{name}_{suf}.png"
        assert p.name.startswith("T_AK_HEnt"), p


def timber(n=2048, seed=301):
    u = np.arange(n)[None, :] / n
    v = np.arange(n)[:, None] / n
    warp = MT.pnoise(n, n, 3.6, seed)                             # uneven ring spacing (smooth, isotropic)
    sway = MT.pnoise(n, n, 4.0, seed + 5, stretch_u=30.0)         # the grain's gentle sideways sway along the member
    fine = MT.pnoise(n, n, 0.9, seed + 1, stretch_u=0.015)        # fine grain lines (long along V)
    band = MT.pnoise(n, n, 1.6, seed + 2, stretch_u=0.03)         # broad light / dark streaks along the grain
    fleck = MT.pnoise(n, n, 0.6, seed + 3, stretch_u=0.25)        # short worn flecks
    mott = MT.pnoise(n, n, 2.4, seed + 4)
    # growth-ring lines: 34 per metre across the grain, bent by the warp, sharpened into thin bright lines
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * (26 * u + 0.6 * sway + 0.4 * warp))
    lines = ring ** 12 * np.clip(0.55 + 0.45 * band, 0.1, 1.4)     # uneven line strength
    light = np.clip(0.20 * lines + 0.18 * np.clip(band - 0.3, 0, None) + 0.12 * np.clip(fine - 0.5, 0, None)
                    + 0.08 * np.clip(fleck - 1.3, 0, None), 0, 1)
    # a few checks (fine dark cracks) along the grain
    rng = np.random.default_rng(seed)
    crack = np.zeros((n, n))
    for _ in range(9):
        c = rng.uniform(0, 1)
        v0, ln = rng.uniform(0, 1), rng.uniform(0.15, 0.45)
        wob = c + 0.004 * np.sin(2 * np.pi * (v * rng.integers(1, 4) + rng.uniform(0, 1)))
        d = np.abs(((u - wob + 0.5) % 1.0) - 0.5) * n
        along = ((v - v0) % 1.0) / ln
        fade = np.clip(np.sin(np.pi * np.clip(along, 0, 1)), 0, 1) * (along <= 1)
        crack = np.maximum(crack, np.clip(1.2 - d / 1.4, 0, 1) * fade)
    dark = MT.srgb("#150F0B")
    lite = MT.srgb("#654A34")
    t = np.clip(light * (1 + 0.15 * mott), 0, 1)[..., None]
    bc = dark[None, None, :] * (1 + 0.10 * mott[..., None]) * (1 - t) + lite[None, None, :] * t
    bc *= (1 - 0.75 * crack)[..., None]
    height = 0.02 * lines + 0.012 * band + 0.006 * fine - 0.05 * crack
    rough = np.clip(0.50 + 0.22 * light[...] - 0.04 * np.tanh(mott) + 0.2 * crack, 0.3, 0.95)
    ao = 1 - 0.4 * crack
    return MT.save_set("HEntTimber", bc, height, 6.0, rough, ao)


def mat(n=1024, seed=311):
    """0.5 m tile, 2048 px/m: strands along U 4.9 mm (10 px) apart, a weft thread every 2.5 cm (51.2 -> 20 per tile)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    strands = n // 10 * 1.0                                        # 102 strands across the tile
    s = (vv * strands / n) % 1.0
    strand = np.sin(np.pi * s) ** 0.6                              # rounded rush strands, dark between
    sid = np.floor(vv * strands / n).astype(int) % int(strands)
    rng = np.random.default_rng(seed)
    tone = rng.normal(0, 0.07, int(strands))[sid]                  # strand-to-strand variation
    hue = np.clip(rng.normal(0, 0.28, int(strands)), -0.6, 0.6)[sid]
    nweft = 20
    w = (uu * nweft / n) % 1.0
    weft = np.clip(1 - np.abs(w - 0.5) / 0.02, 0, 1) * 0.5             # the binding threads across the strands
    fib = MT.pnoise(n, n, 0.8, seed + 1, stretch_u=4.0)
    mott = MT.pnoise(n, n, 2.2, seed + 2)
    gold, straw, olive = MT.srgb("#94702F"), MT.srgb("#A7853F"), MT.srgb("#7E6E38")
    k = np.clip(0.5 + 0.35 * hue, 0, 1)[..., None]
    base = gold[None, None, :] * (1 - k) + straw[None, None, :] * k
    base = base * (1 - 0.18 * np.clip(-hue, 0, 1)[..., None]) + olive[None, None, :] * 0.18 * np.clip(-hue, 0, 1)[..., None]
    lum = (0.62 + 0.38 * strand + tone + 0.04 * fib + 0.05 * mott) * (1 - 0.45 * weft)
    bc = np.clip(base * lum[..., None], 0, 0.8)
    height = 0.6 * strand - 0.5 * weft + 0.05 * fib
    rough = 0.72 + 0.1 * (1 - strand) + 0.05 * weft
    ao = 1 - 0.25 * (1 - strand) - 0.2 * weft
    return MT.save_set("HEntMat", bc, height * 0.05, 4.0, rough, ao)


def rush(n=1024, seed=331):
    """Layout 2 r4 (entrance.png, the top view): the sheet's mat is a coir-like golden rush weave, warm orange-gold with
    strong texture contrast - raised ribs running front to back (along V) about 4 cm apart with dark grooves between
    them (the parallel lines of the sheet), each rib a column of rounded weft nubs ~1.25 cm apart, offset half a nub on
    alternate ribs (a basket weave). 0.5 m tile, 2048 px/m: 12 ribs (85.3 px) across, 40 nubs (25.6 px) along each rib.
    Measured on the sheet's top view: field ~ sRGB (176, 127, 79), pixel std ~25 (the first r4 pass rendered a pale,
    flat (185, 145, 97), std 5)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    nr, nn = 12, 40
    ru = uu * nr / n
    ri = np.floor(ru).astype(int) % nr
    pu = ru % 1.0
    rib = np.sin(np.pi * pu) ** 0.45                               # a rounded rib, a dark groove at its edges
    pv = (vv * nn / n + 0.5 * (ri % 2)) % 1.0
    nub = np.sin(np.pi * pv) ** 0.7                                # rounded weft nubs along the rib
    rng = np.random.default_rng(seed)
    tone = rng.normal(0, 0.04, nr)[ri]                             # rib-to-rib variation
    hue = np.clip(rng.normal(0, 0.30, nr), -0.6, 0.6)[ri]
    fib = MT.pnoise(n, n, 0.8, seed + 1, stretch_u=4.0)           # fibres across each nub (along U)
    mott = MT.pnoise(n, n, 2.2, seed + 2)
    gold, straw = MT.srgb("#8A5820"), MT.srgb("#A87436")          # warm orange-gold rush (the sheet's)
    k = np.clip(0.5 + 0.4 * hue + 0.05 * mott, 0, 1)[..., None]
    base = gold[None, None, :] * (1 - k) + straw[None, None, :] * k
    lum = (0.25 + 0.80 * rib) * (0.62 + 0.38 * nub) + tone + 0.07 * fib + 0.012 * mott
    bc = np.clip(base * lum[..., None], 0, 0.85)
    height = 0.55 * rib + 0.35 * nub * rib + 0.05 * fib
    rough = np.clip(0.70 + 0.12 * (1 - rib) - 0.04 * nub, 0.4, 0.95)
    ao = 1 - 0.40 * (1 - rib) - 0.18 * (1 - nub)
    return MT.save_set("HEntRush", bc, height * 0.05, 5.0, rough, ao)


def timber_warm(n=2048, seed=341):
    """Final fix r5 (blind judge: the hero timber read flatter and cooler than the sheet's warm, weathered, heavily
    grained timber): the same grain build as timber() with a warmer dark-brown body, bolder lighter-brown grain lines and
    streaks, broader weathered bands and a few darker knots. Grain along V, 1.0 m tile."""
    u = np.arange(n)[None, :] / n
    v = np.arange(n)[:, None] / n
    warp = MT.pnoise(n, n, 3.6, seed)
    sway = MT.pnoise(n, n, 4.0, seed + 5, stretch_u=30.0)
    fine = MT.pnoise(n, n, 0.9, seed + 1, stretch_u=0.015)
    band = MT.pnoise(n, n, 1.6, seed + 2, stretch_u=0.03)
    fleck = MT.pnoise(n, n, 0.6, seed + 3, stretch_u=0.25)
    mott = MT.pnoise(n, n, 2.4, seed + 4)
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * (30 * u + 0.22 * sway + 0.30 * warp))
    lines = ring ** 10 * np.clip(0.6 + 0.5 * band, 0.15, 1.6)
    light = np.clip(0.30 * lines + 0.07 * np.clip(band - 0.6, 0, None) + 0.20 * np.clip(fine - 0.4, 0, None)
                    + 0.10 * np.clip(fleck - 1.2, 0, None), 0, 1)
    rng = np.random.default_rng(seed)
    crack = np.zeros((n, n))
    for _ in range(12):
        c = rng.uniform(0, 1)
        v0, ln = rng.uniform(0, 1), rng.uniform(0.15, 0.5)
        wob = c + 0.004 * np.sin(2 * np.pi * (v * rng.integers(1, 4) + rng.uniform(0, 1)))
        d = np.abs(((u - wob + 0.5) % 1.0) - 0.5) * n
        along = ((v - v0) % 1.0) / ln
        fade = np.clip(np.sin(np.pi * np.clip(along, 0, 1)), 0, 1) * (along <= 1)
        crack = np.maximum(crack, np.clip(1.2 - d / 1.5, 0, 1) * fade)
    knot = np.zeros((n, n))
    for _ in range(3):   # a few darker knots, stretched along the grain (seamless: wrapped distances)
        cu, cv = rng.uniform(0, 1, 2)
        du = np.abs(((u - cu + 0.5) % 1.0) - 0.5) / 0.012
        dv = np.abs(((v - cv + 0.5) % 1.0) - 0.5) / 0.035
        knot = np.maximum(knot, np.clip(1 - np.sqrt(du ** 2 + dv ** 2), 0, 1))
    dark = MT.srgb("#1A110B")
    lite = MT.srgb("#74523A")
    t = np.clip(light * (1 + 0.18 * mott), 0, 1)[..., None]
    bc = dark[None, None, :] * (1 + 0.12 * mott[..., None]) * (1 - t) + lite[None, None, :] * t
    bc *= (1 - 0.75 * crack)[..., None] * (1 - 0.55 * knot)[..., None]
    height = 0.025 * lines + 0.015 * band + 0.008 * fine - 0.05 * crack - 0.02 * knot
    rough = np.clip(0.55 + 0.20 * light - 0.04 * np.tanh(mott) + 0.2 * crack, 0.3, 0.95)
    ao = 1 - 0.4 * crack
    return MT.save_set("HEntTimberW", bc, height, 7.0, rough, ao)


def coir(n=1024, seed=351):
    """Final fix r5 (blind judge: the r4 rush read as straight front-to-back ribs, corduroy lines; the sheet's mat is a
    coarse nubby coir / basket texture with no strong linear ribs): a basket weave of small rounded nubs - 2 x 2 blocks
    of short strands alternating across / along, ~1.6 cm cells (32 per 0.5 m tile), jittered in tone and height, with
    loose fibre speckle and a soft mottle. Warm orange-gold, mean near the sheet's (176, 127, 79)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    nc = 40
    cu, cv = uu * nc / n, vv * nc / n
    iu, iv = np.floor(cu).astype(int), np.floor(cv).astype(int)
    fu, fv = cu % 1.0, cv % 1.0
    across = ((iu // 1 + iv // 1) % 2) == 0                        # alternate strand direction per cell
    sub = 3                                                        # three strands in each cell
    su = np.where(across, (fv * sub) % 1.0, (fu * sub) % 1.0)      # position across a strand
    sl = np.where(across, fu, fv)                                  # position along it
    rng = np.random.default_rng(seed)
    jit = MT.pnoise(n, n, 0.3, seed + 7)                            # per-nub irregularity (a coarse, uneven weave)
    strand = np.sin(np.pi * su) ** 0.6 * (0.45 + 0.55 * np.sin(np.pi * sl) ** 0.5) * (1 + 0.12 * jit)
    cell = rng.normal(0, 1, (nc, nc))
    ctone = cell[iv % nc, iu % nc]
    fib = MT.pnoise(n, n, 0.5, seed + 1)
    mott = MT.pnoise(n, n, 2.2, seed + 2)
    gold, straw = MT.srgb("#8C5A24"), MT.srgb("#B07A3C")
    k = np.clip(0.5 + 0.18 * ctone + 0.12 * mott, 0, 1)[..., None]
    base = gold[None, None, :] * (1 - k) + straw[None, None, :] * k
    lum = (0.42 + 0.66 * strand) * (1 + 0.05 * ctone) + 0.06 * np.clip(fib - 1.0, 0, None) + 0.015 * mott
    bc = np.clip(base * lum[..., None], 0, 0.85)
    height = 0.8 * strand + 0.12 * ctone * 0.2 + 0.06 * fib
    rough = np.clip(0.74 + 0.12 * (1 - strand), 0.4, 0.95)
    ao = 1 - 0.35 * (1 - strand)
    return MT.save_set("HEntCoir", bc, height * 0.05, 5.0, rough, ao)


def bronze(n=1024, seed=361):
    """Final fix r5 (blind judge: the hero's brass was a saturated clean yellow; the sheet's is a darker aged bronze
    with patina): a satin aged bronze with dark brown patina blotches, faint rubbed lighter zones and fine scratches.
    Metallic in the ORM blue channel varies (bronze 0.9, patina 0.55). 0.5 m tile."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    blot = MT.pnoise(n, n, 1.6, seed)
    fine = MT.pnoise(n, n, 1.0, seed + 1)
    scr = MT.pnoise(n, n, 0.7, seed + 2, stretch_u=0.02)
    pat = np.clip((blot + 0.45 * fine - 0.3) * 0.75, 0, 0.85)            # patina amount
    rub = np.clip((-blot - 0.9) * 0.8, 0, 1)                          # rubbed lighter zones
    bronze_c, patina_c, rub_c = MT.srgb("#9C784A"), MT.srgb("#4A3A26"), MT.srgb("#A8895A")
    p3, r3 = pat[..., None], rub[..., None]
    bc = bronze_c * (1 - p3) + patina_c * p3
    bc = bc * (1 - r3) + rub_c * r3
    bc *= (1 + 0.04 * fine[..., None] + 0.05 * np.clip(scr - 1.5, 0, None)[..., None])
    height = 0.02 * fine - 0.03 * pat + 0.01 * np.clip(scr - 1.5, 0, None)
    rough = np.clip(0.42 + 0.25 * pat - 0.08 * rub + 0.03 * fine, 0.25, 0.9)
    metal = np.clip(0.92 - 0.37 * pat, 0, 1)
    OUTP = MT.OUT
    MT.write_png(OUTP / "T_AK_HEntBronze_BC.png", np.clip(bc, 0, 1))
    MT.write_png(OUTP / "T_AK_HEntBronze_N.png", MT.normal_dx(height, 3.0))
    MT.write_png(OUTP / "T_AK_HEntBronze_ORM.png", np.dstack([1 - 0.2 * pat, rough, metal]))
    return {"set": "HEntBronze", "size": [n, n], "mean_srgb": [round(float(x), 3) for x in bc.reshape(-1, 3).mean(0)],
            "rough_mean": round(float(rough.mean()), 3)}


def timber_ebony(n=2048, seed=371, name="HEntTimberE", dark="#1E120A", mid="#2F1E12", lite="#553A26", rough0=0.80,
                 nknots=3):
    """Final fix r6 (blind judge: the r5 timber showed strong regular orange / rust streak bands on every board - it
    read procedural; the sheet's timber is a darker charcoal-ebony with real plank grain, knots, long dark checks and
    only thin warm edge highlights): a charcoal-brown body, low-contrast irregular grain (line spacing varies, lines
    converge and drift, line strength varies), long broken dark checks, a few knots with a pale ring and a darker
    heart, faint greyed weathering. No broad bright bands. Grain along V, 1.0 m tile (sheet measured: (51, 40, 33) on
    the side wall, (59, 46, 39) on the lintel front)."""
    u = np.arange(n)[None, :] / n
    v = np.arange(n)[:, None] / n
    rng = np.random.default_rng(seed)
    drift = MT.pnoise(n, n, 3.4, seed, stretch_u=3.0)            # slow sideways drift of the grain along the member
    spac = MT.pnoise(n, n, 2.4, seed + 1, stretch_u=0.3)         # uneven line spacing across the board
    fine = MT.pnoise(n, n, 0.9, seed + 2, stretch_u=0.012)       # fibre lines along V
    fib2 = MT.pnoise(n, n, 0.5, seed + 3, stretch_u=0.03)        # finer fibre sheen
    mott = MT.pnoise(n, n, 2.2, seed + 4)                         # soft weathering
    lstr = MT.pnoise(n, n, 1.8, seed + 5, stretch_u=0.2)         # line strength: some lines faint, some bold
    # growth lines: ~24 per metre on average, their spacing uneven, gently drifting, thin and low contrast
    phase = 24 * u + 0.45 * drift + 0.9 * spac
    ring = (0.5 + 0.5 * np.cos(2 * np.pi * phase)) ** 18
    lines = np.clip(ring * np.clip(0.45 + 0.45 * lstr, 0.0, 1.3), 0, 1.2)
    # long broken checks (dark, some dashed like the sheet's)
    crack = np.zeros((n, n))
    for _ in range(16):
        c = rng.uniform(0, 1)
        v0, ln = rng.uniform(0, 1), rng.uniform(0.12, 0.55)
        wob = c + 0.003 * np.sin(2 * np.pi * (v * rng.integers(1, 4) + rng.uniform(0, 1)))
        d = np.abs(((u - wob + 0.5) % 1.0) - 0.5) * n
        along = ((v - v0) % 1.0) / ln
        dash = (0.5 + 0.5 * np.sin(2 * np.pi * (along * rng.uniform(3, 9) + rng.uniform(0, 1)))) > 0.25
        fade = np.clip(np.sin(np.pi * np.clip(along, 0, 1)), 0, 1) * (along <= 1) * dash
        crack = np.maximum(crack, np.clip(1.3 - d / 1.6, 0, 1) * fade)
    knot = np.zeros((n, n))
    kring = np.zeros((n, n))
    for _ in range(nknots):   # matfix b3: 0 for the step bar / mat boards (a knot repeated every metre read as holes)
        cu, cv = rng.uniform(0, 1, 2)
        du = np.abs(((u - cu + 0.5) % 1.0) - 0.5) / rng.uniform(0.010, 0.016)
        dv = np.abs(((v - cv + 0.5) % 1.0) - 0.5) / rng.uniform(0.022, 0.034)
        r = np.sqrt(du ** 2 + dv ** 2)
        knot = np.maximum(knot, np.clip(1.2 - r, 0, 1))
        kring = np.maximum(kring, np.clip(1 - np.abs(r - 1.35) / 0.25, 0, 1))
    # the studio's grey sheen desaturates it (a first pass at #1E1712 / #4F4034 rendered a grey (55, 49, 46)): a
    # warmer, more saturated dark brown, rougher, so it renders near the sheet's warm charcoal
    dark = MT.srgb(dark)               # charcoal-brown body (HEntTimberE: #1E120A)
    mid = MT.srgb(mid)                 # (#2F1E12)
    lite = MT.srgb(lite)               # the lighter grain / worn fibres (a brown, not orange; #553A26)
    body = np.clip(0.5 + 0.18 * mott + 0.20 * np.clip(fine, -2, 2), 0, 1)[..., None]
    bc = dark * (1 - body) + mid * body
    t = np.clip(0.50 * lines + 0.22 * np.clip(fine - 0.6, 0, None) + 0.10 * np.clip(fib2 - 1.0, 0, None)
                + 0.25 * kring, 0, 1)[..., None]
    bc = bc * (1 - t) + lite * t
    bc *= (1 - 0.70 * crack)[..., None] * (1 - 0.60 * knot)[..., None]
    height = 0.012 * lines + 0.006 * fine - 0.06 * crack - 0.02 * knot + 0.004 * mott
    rough = np.clip(rough0 + 0.06 * np.tanh(mott) - 0.06 * lines + 0.15 * crack, min(0.5, rough0 - 0.1), 0.97)
    ao = 1 - 0.45 * crack - 0.2 * knot
    return MT.save_set(name, bc, height, 7.0, rough, ao)


def coir_ribbed(n=1024, seed=381):
    """Final fix r6 (blind judge: the r5 coir read as a flat speckle at the sheet's distances; the sheet shows a clear
    woven row / tuft texture with directional ribs front to back): 12 ribs per 0.5 m tile (4.2 cm) running along V,
    each a column of rounded tufts (22 per tile, 2.3 cm) staggered half a tuft on alternate ribs, deep dark grooves
    between the ribs and a shallow pinch between tufts, a lighter golden tuft crown, per-tuft tone jitter and loose
    fibre speckle - the contrast the sheet's top view shows (field ~ (178, 126, 75), pixel std ~ 36)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    nr, nt = 12, 22
    ru = uu * nr / n
    ri = np.floor(ru).astype(int) % nr
    pu = ru % 1.0
    tv = vv * nt / n + 0.5 * (ri % 2)
    ti = np.floor(tv).astype(int) % nt
    pv = tv % 1.0
    rng = np.random.default_rng(seed)
    jw = rng.uniform(0.85, 1.0, (nr, nt))[ri, ti]                      # tuft width jitter
    x = (pu - 0.5) / (0.5 * jw)
    y = (pv - 0.5) / 0.5
    tuft = np.clip(1 - x ** 2, 0, 1) ** 0.6 * (0.40 + 0.60 * np.cos(0.5 * np.pi * np.clip(y, -1, 1)) ** 0.8)
    fib = MT.pnoise(n, n, 0.4, seed + 1, stretch_u=3.0)                # fibres across the tuft
    spk = MT.pnoise(n, n, 0.2, seed + 2)
    mott = MT.pnoise(n, n, 2.0, seed + 3)
    ttone = rng.normal(0, 1, (nr, nt))[ri, ti]
    groove, crown = MT.srgb("#5A3A1C"), MT.srgb("#C8964F")
    k = np.clip(tuft * (0.82 + 0.06 * ttone) + 0.05 * np.clip(fib, -2, 2) + 0.03 * mott, 0, 1)[..., None]
    bc = groove * (1 - k) + crown * k
    bc *= (1 + 0.10 * np.clip(spk - 1.3, 0, None))[..., None]
    height = 0.9 * tuft + 0.05 * fib
    rough = np.clip(0.80 - 0.08 * tuft, 0.5, 0.95)
    ao = 1 - 0.45 * (1 - tuft)
    return MT.save_set("HEntCoirR", np.clip(bc, 0, 0.9), height * 0.05, 5.0, rough, ao)


def sisal(n=1024, seed=401):
    """Genkan r4 (blind judge 6.5, delta 1: "the reference mat is a coarse, chunky basket / sisal weave in mid
    grey-brown ... r3 reads as a fine horizontal-ribbed tatami in bright straw"): reference 2's foreground mat, zoomed,
    shows rows of chunky rounded knots running ACROSS the mat (build 3: each row drifted a little, no hex stagger), dark
    gaps between them and a faint row-to-row tone banding; measured field sRGB ~(111, 82, 67) in the golden light (a
    greyer, cooler tan than the hall planks). 14 rows per 0.5 m tile (3.6 cm) of 18 knots (2.8 cm); the rows run along
    V (hero_entrance maps U to world Y, V to world X, so the rows lie across the mat); a knot is a rounded dome with a
    twisted-fibre sheen across it, per-knot tone jitter, loose fibre speckle. Mid grey-brown, not straw."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    nr, nk = 14, 18                   # build 2: 22 x 20 read a fine dot grid; build 3: 16 rows, staggered, a hex dot grid
    ru = uu * nr / n
    ri = np.floor(ru).astype(int) % nr
    pu = ru % 1.0
    kv = vv * nk / n + 0.23 * (ri % 3)                                # a slight drift row to row (no hex grid)
    ki = np.floor(kv).astype(int) % nk
    pv = kv % 1.0
    rng = np.random.default_rng(seed)
    jw = rng.uniform(0.95, 1.12, (nr, nk))[ri, ki]
    x = (pu - 0.5) / (0.56 * jw)
    y = np.clip((pv - 0.5) / 0.5, -1, 1)
    # a chunky knot: deep seams between the rows, a clear pinch between the knots along a row (build 2's plain dome
    # merged into flat blocks)
    knot = np.clip(1 - x ** 2, 0, 1) ** 0.45 * (0.62 + 0.38 * np.cos(0.5 * np.pi * y) ** 1.2)   # rows read first
    twist = 0.5 + 0.5 * np.sin(2 * np.pi * (3.0 * pu + 1.4 * pv))      # the twisted fibres across each knot
    fib = MT.pnoise(n, n, 0.4, seed + 1)
    spk = MT.pnoise(n, n, 0.2, seed + 2)
    mott = MT.pnoise(n, n, 2.2, seed + 3)
    ktone = rng.normal(0, 1, (nr, nk))[ri, ki]
    rtone = rng.normal(0, 1, nr)[ri]                                   # faint row-to-row banding
    gap, crown = MT.srgb("#241910"), MT.srgb("#8E6E56")   # build 2: #3E3027 / #98806C read pale; build 3 warmer
    k = np.clip(knot * (0.80 + 0.07 * ktone + 0.05 * rtone) + 0.08 * (twist - 0.5) * knot + 0.04 * np.clip(fib, -2, 2)
                + 0.03 * mott, 0, 1)[..., None]
    bc = gap * (1 - k) + crown * k
    bc *= (1 + 0.08 * np.clip(spk - 1.3, 0, None))[..., None]
    height = knot + 0.08 * twist * knot + 0.04 * fib
    rough = np.clip(0.86 - 0.06 * knot, 0.5, 0.95)
    ao = 1 - 0.55 * (1 - knot)
    return MT.save_set("HEntSisal", np.clip(bc, 0, 0.9), height * 0.06, 6.0, rough, ao)


def timber_weathered(n=2048, seed=411):
    """Genkan r4 (blind judge delta 2: "the reference beam is dark, satin, weathered wood with a visible lighter-brown
    top face and a darker front face"): the step beam's worn TOP face, reference 2 measured ~(64, 61, 65) there in the
    golden light against the planks' (105, 71, 48): the ebony set's grain, checks and knots (timber_ebony, seed 371)
    in a lighter, greyed weathered brown. Grain along V, 1.0 m tile."""
    return timber_ebony(n, seed, name="HEntTimberG", dark="#2C2622", mid="#3E3630", lite="#6E6258")


def timber_lacquer(n=2048, seed=431):
    """Entryfix r2 (blind judge 6/10: "the reference beam has a slightly lit top face and edge that read as a timber";
    the user: "a black bar"): the step bar's near-black LACQUERED timber: the ebony set's grain, checks and knots
    (timber_ebony, its own seed) in #0D0A08 / #15100C / #2B211A under a satin lacquer (roughness ~0.30, a little
    rougher in the checks), so the top face picks up the lit hall as a soft sheen over faint grain. Grain along V, 1.0 m
    tile."""
    # b4: b3's #0D0A08-#2B211A top read L 3-6 at night against the hall floor's ~60 (a void): a touch lighter, still
    # near-black (mean sRGB ~0.10), satin 0.28; b5: b4's top read L ~12 against the floor's ~60 (reference 2: about
    # the floor's tone): #1C1612-#46372A (mean sRGB ~0.12)
    return timber_ebony(n, seed, name="HEntTimberL", dark="#1C1612", mid="#2A2019", lite="#46372A", rough0=0.28)


def rush_knit(n=1024, seed=421):
    """Entryfix r2 (blind judge 6/10, blocker 1: "the weave reads as a regular grid of round dots, like cobbles or polka
    dots. The reference shows fine woven rush in straw tan, with a woven texture you can make out"): reference 2's mat,
    zoomed through the refit C1 (4.2 px cords, 5.5 px stitches at ~6.5 m), is COLUMNS of small interlocked V stitches
    running front to back: cords ~1.8 cm apart (deep dark seams between them), each cord a chain of slanted paired lobes
    ~4.2 cm long, twisted fibre sheen along each lobe, a slight random phase per cord (no dot rows), cord-to-cord straw
    tone variation. Straw tan (the knot crowns ~#A88A66, the seams #2A1D12). Tile 0.5 m: 28 cords along V (hero_entrance
    maps V to world X, across the mat), 12 stitches along U (world Y, toward the bar)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    nc, nk = 28, 12
    rng = np.random.default_rng(seed)
    cv = vv * nc / n
    ci = np.floor(cv).astype(int) % nc
    pc = cv % 1.0                                                  # across the cord, 0..1
    ph = rng.uniform(-0.18, 0.18, nc)[ci]                          # each cord's own stitch phase
    # b4: b3's sharp paired V lobes read as machine knitting (graphic chevrons) with broad light / dark cord bands:
    # rounder beads (the lobes merge, a soft central crease), a gentler V, much weaker cord-to-cord and mottle tones
    wob = 0.05 * np.sin(2 * np.pi * (2 * uu / n + 0.37 * ci))     # the stitch rows wander a little
    ku = uu * nk / n + ph + wob
    ki = np.floor(ku).astype(int) % nk
    pk = ku % 1.0                                                  # along the stitch, 0..1
    x = (pc - 0.5) * 2.0                                           # -1..1 across the cord
    ax = np.abs(x)
    xl = ax - 0.5                                                  # each lobe centred at |x| = 0.5
    yk = ((pk - 0.16 * xl) % 1.0) - 0.5                            # the V: the lobes rise toward the cord's edges
    bead = np.clip(1 - (x / 1.05) ** 2 - (yk / 0.56) ** 2, 0, 1) ** 0.5
    pair = np.clip(1 - (xl / 0.62) ** 2 - (yk / 0.56) ** 2, 0, 1) ** 0.6
    lobe = 0.65 * bead + 0.35 * pair
    cord = np.clip(1 - x ** 2, 0, 1) ** 0.30                       # the cord's round section, dark seams between
    h = cord * (0.45 + 0.55 * lobe)
    twist = 0.5 + 0.5 * np.sin(2 * np.pi * (5.0 * yk + 2.2 * xl * np.sign(x)))   # fibres along each lobe
    fib = MT.pnoise(n, n, 0.4, seed + 1)
    mott = MT.pnoise(n, n, 2.4, seed + 2)
    ctone = rng.normal(0, 1, nc)[ci]                               # cord-to-cord straw variation
    stone = rng.normal(0, 1, (nc, nk))[ci, ki]
    gap, crown = MT.srgb("#2E2115"), MT.srgb("#AE9068")
    k = np.clip(h * (0.86 + 0.02 * ctone + 0.04 * stone) + 0.07 * (twist - 0.5) * lobe + 0.035 * np.clip(fib, -2, 2)
                + 0.012 * mott, 0, 1)[..., None]
    bc = gap * (1 - k) + crown * k
    bc = bc * (1 + np.array([0.0, 0.008, -0.01]) * ctone[..., None])   # a few greener / warmer cords
    height = h + 0.06 * twist * lobe + 0.03 * fib
    rough = np.clip(0.84 - 0.08 * lobe, 0.5, 0.95)
    ao = 1 - 0.5 * (1 - h)
    return MT.save_set("HEntRushK", np.clip(bc, 0, 0.9), height * 0.05, 6.0, rough, ao)


def weave(n=1024, seed=441, nc=17, nk=15, ns=3):
    """Matfix (2026-09-28, the user: "fix the mat"; entry_foreground_crop.png): ONE coarse, nubbly woven sisal rug in a
    warm grey-tan. Reference 2's field through C1 (row / column spectra of the mat, matfix/texstats.py): strongly
    periodic columns ~7.6 px apart at ~265 px/m = cords ~2.9 cm apart running front to back (toward the bar), only a
    weak period along them (nubs ~5-8 cm), rounded nubs lit on one side, relief contrast ~0.15 of the mean, field
    ~(109, 81, 67) sRGB in the golden light. The r2 T_AK_HEntRushK (1.8 cm cords, 4.2 cm stitches) was 1.6x too fine
    and read as a tatami grid. Here: nc cords per 0.5 m tile along U (hero_entrance maps U to world Y, toward the bar;
    2.94 cm apart), each a chain of nk rounded nubs (3.3 cm) that bulge and pinch like a basket weave, alternate cords
    offset half a nub (a staggered interlock, no rows of dots), each nub slanted as a twisted cord, inside each nub ns sisal strands whose direction
    alternates nub to nub (across / along: the basket checker at close range), the lattice domain-warped by smooth
    periodic noise (wavy cords), per-nub and per-strand height / tone jitter, twisted-fibre striations and loose-fibre
    fuzz. Thin deep seams between the cords, the nubs touching along them. Warm grey-tan."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    wv = MT.pnoise(n, n, 2.6, seed + 1) * 0.06                    # cords wander (in cord widths)
    wu = MT.pnoise(n, n, 2.6, seed + 2) * 0.12                    # nubs wander along the cord (in nub lengths)
    cv = vv * nc / n + wv
    ci = np.floor(cv).astype(int) % nc
    pc = cv % 1.0                                                 # across the cord, 0..1
    ku = uu * nk / n + 0.5 * (ci % 2) + rng.uniform(-0.08, 0.08, nc)[ci] + wu
    ki = np.floor(ku).astype(int) % nk
    pk = ku % 1.0                                                 # along the nub, 0..1
    x = 2 * pc - 1                                                # -1..1 across the cord
    # b2: b1's straight nubs with dark seams all round read from above as a dot / cobble grid: each nub a SLANTED bead
    # (a twisted cord, one slant throughout; alternating read as knit), the nubs along a cord merging (a soft pinch, light seams)
    x0 = 2 * pc - 1
    y = ((pk + 0.12 * x0 + 0.5) % 1.0) * 2 - 1                    # -1..1 along the nub (0.22 alternating read as knit)
    njit = rng.uniform(0.85, 1.10, (nc, nk))[ci, ki]
    wid = rng.uniform(0.90, 1.0, (nc, nk))[ci, ki]
    # t2: t1's flat-topped pillows with dark seams all round read as bricks / cobbles: a rounded dome across the cord
    # (deep seams between cords), a soft pinch between the nubs along it (they touch)
    pill = np.clip(1 - (np.abs(x) / wid) ** 2, 0, 1) ** 0.45 * (0.45 + 0.55 * np.clip(1 - np.abs(y) ** 2, 0, 1) ** 0.6)
    o = (ci + ki) % 2                                             # strand direction per nub: across / along
    sb = np.where(o == 0, (y + 1) / 2, (x + 1) / 2) * ns
    si = np.clip(np.floor(sb).astype(int), 0, ns - 1)
    ps = sb % 1.0
    strand = np.clip(1 - (2 * ps - 1) ** 2, 0, 1) ** 0.5
    sjit = rng.uniform(0.9, 1.06, (nc, nk, ns))[ci, ki, si]
    nub = pill * njit * (0.78 + 0.22 * strand * sjit)
    along = np.where(o == 0, x, y)
    twist = 0.5 + 0.5 * np.sin(2 * np.pi * (3.5 * along + 1.2 * ps))   # twisted fibres along each strand
    fuzz = MT.pnoise(n, n, 0.35, seed + 3)
    mott = MT.pnoise(n, n, 2.2, seed + 4)
    ntone = rng.normal(0, 1, (nc, nk))[ci, ki]
    ctone = rng.normal(0, 1, nc)[ci]
    stone = rng.normal(0, 1, (nc, nk, ns))[ci, ki, si]
    h = nub + 0.06 * twist * nub + 0.03 * fuzz
    gap, crown = MT.srgb("#2A1E16"), MT.srgb("#A4866C")                  # b2: warmer tan (b1 read grey in golden)
    k = np.clip(0.22 + 0.74 * nub + 0.045 * ntone + 0.02 * ctone + 0.03 * stone + 0.06 * (twist - 0.5) * nub
                + 0.03 * np.clip(fuzz, -2, 2) + 0.03 * mott, 0, 1)[..., None]
    bc = gap * (1 - k) + crown * k
    bc = bc * (1 + np.array([0.012, 0.0, -0.02]) * stone[..., None])   # a few warmer / greyer strands
    rough = np.clip(0.88 - 0.06 * nub, 0.5, 0.95)
    ao = np.clip(1 - 0.6 * (1 - np.clip(nub, 0, 1)) ** 1.5, 0, 1)
    return MT.save_set("HEntWeave", np.clip(bc, 0, 0.9), h * 0.12, 7.0, rough, ao)   # b2: stronger relief (0.08)


def timber_bar(n=2048, seed=431):
    """Matfix b3 (blind judge 6/10: "three small dark round dots or holes on the riser face directly above the mat"):
    T_AK_HEntTimberL's lacquered near-black bar timber with no knots (one knot per 1 m tile repeated along the 12 cm
    face as a row of holes). Same seed, colours and satin as timber_lacquer; only the knots are gone."""
    return timber_ebony(n, seed, name="HEntTimberN", dark="#1C1612", mid="#2A2019", lite="#46372A", rough0=0.28, nknots=0)


def timber_board(n=2048, seed=451):
    """Matfix b3 (blind judge: "the frame boards are lighter, redder wood with prominent grain ... the reference frame is
    uniformly dark, near-black, low-sheen board on all sides, matching the dark step bar"): the bar's near-black timber
    (#1C1612-#46372A, no knots) at a low sheen (roughness ~0.62) for the mat's surround boards and the pit's side
    returns (M_AK_HMatBoard; was the ebony at tint 2.4 with warm worn arrises)."""
    return timber_ebony(n, seed, name="HEntTimberM", dark="#1A1411", mid="#261D17", lite="#3C3026", rough0=0.62, nknots=0)


def knot_weave(n=2048, seed=461, name="HEntKnot", gap="#2A221C", crown="#8E7865", rough0=0.86, nc=34, nk=20):
    """Matfix b3 (blind judge 6/10 on T_AK_HEntWeave: "vertical corduroy ropes separated by continuous dark grooves ...
    the reference is round, nubbly, roughly isotropic knots in both row and column directions with strong 3D relief";
    staircase blocks inside each rope; too fine; too flat): a chunky knotted (Berber-loop) sisal. Reference 2's field
    through C1 (matfix/texstats.py): period 7.6 px across (columns ~3 cm apart) and ~11.9 px along (knots ~7 cm long in
    the world, which the view foreshortens to a round knot on screen); b2 had 5 px along (3.3 cm nubs), far too fine.
    Here (b4): a 1 m tile at 2048 px (b3's 0.5 m tile repeated as visible bands across the mat), nc columns along V
    (world X across the mat: 2.94 cm, reference 2's 7.6 px) of nk knots along U (world Y: 5 cm, a round knot on
    screen at C1; the reference's along-spectrum is weak, peaks 7.9-11.9 px).
    Every knot is its own smooth dome (height = the max of the neighbouring domes, so there are no cell steps): a
    slightly slanted squarish ellipse, touching its neighbours, a clear pinch between the knots along a column, a shallower
    crease between the columns, dark pockets only where four knots meet. Each column has its own phase (the rows wander,
    no dot grid); per-knot size / height / tone jitter blended smoothly across the creases; four twisted plies slant
    across every knot; fine fuzz. The height carries a strong normal (knot flanks tilt ~35-50 deg) for real relief."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    cv = vv * nc / n + MT.pnoise(n, n, 2.8, seed + 1) * 0.05           # columns wander a little (column units)
    ku = uu * nk / n + MT.pnoise(n, n, 2.8, seed + 2) * 0.06           # knots wander along (knot units)
    cph = rng.uniform(-0.22, 0.22, nc)                                 # each column's own knot phase
    cjit = rng.uniform(-0.05, 0.05, nc)
    kjit = rng.uniform(-0.07, 0.07, (nc, nk))
    rxs = rng.uniform(0.50, 0.57, (nc, nk))                            # half width, column units
    rys = rng.uniform(0.56, 0.66, (nc, nk))                            # half length, knot units
    amp = rng.uniform(0.90, 1.0, (nc, nk))
    tone = rng.normal(0, 1, (nc, nk))
    slant = rng.uniform(0.14, 0.24, (nc, nk)) * np.where(rng.random(nc) < 0.85, 1, -1)[:, None]
    ply_ph = rng.uniform(0, 1, (nc, nk))
    c0 = np.floor(cv).astype(int)
    H = np.zeros((n, n)); W = np.zeros((n, n)); T = np.zeros((n, n)); P = np.zeros((n, n)); D = np.zeros((n, n))
    for dc in (-1, 0, 1):
        c = c0 + dc
        cm = c % nc
        cx = c + 0.5 + cjit[cm]
        dx = cv - cx
        kk0 = np.floor(ku - cph[cm]).astype(int)
        for dk in (-1, 0, 1):
            k = kk0 + dk
            km = k % nk
            cy = k + 0.5 + cph[cm] + kjit[cm, km]
            dy = ku - cy
            a = dx / rxs[cm, km]
            b = (dy + slant[cm, km] * dx) / rys[cm, km]
            r2 = (np.abs(a) ** 2.4 + np.abs(b) ** 2.4) ** (2 / 2.4)      # a squarer end: chunky knots, not rice grains
            dome = np.clip(1 - r2, 0, 1) ** 0.85 * amp[cm, km]   # b4: 0.55 read flat-topped cobbles
            # four plies slanting across the knot (a twisted loop), strongest on the crown
            ply = 0.5 + 0.5 * np.cos(2 * np.pi * (1.9 * (0.55 * a + 0.83 * b) + ply_ph[cm, km]))
            w = np.exp(24 * dome) * (dome > 0)
            upd = dome > H
            H = np.where(upd, dome, H)
            D = np.where(upd, ply, D)
            W += w; T += w * tone[cm, km]; P += w * ply
    T = T / np.maximum(W, 1e-9)
    P = P / np.maximum(W, 1e-9)
    fuzz = MT.pnoise(n, n, 0.3, seed + 3)
    mott = MT.pnoise(n, n, 2.4, seed + 4)
    h = H * (0.93 + 0.07 * P) + 0.012 * fuzz
    # value: mostly the knot's own tone (the relief is left to the normal), dark only low in the creases / pockets
    occ = np.clip(H / 0.45, 0, 1) ** 0.7
    # b4: b3's dark crease network and per-knot tone read as a cobble mosaic: lighter creases, gentler tone, more ply
    k = np.clip(0.48 + 0.44 * occ + 0.12 * (P - 0.5) * occ + 0.025 * T + 0.025 * np.clip(fuzz, -2, 2)
                + 0.03 * mott, 0, 1)[..., None]
    g, cr = MT.srgb(gap), MT.srgb(crown)
    bc = g * (1 - k) + cr * k
    bc = bc * (1 + np.array([0.010, 0.0, -0.012]) * T[..., None])       # a few warmer / greyer knots
    rough = np.clip(rough0 - 0.05 * occ + 0.03 * fuzz, 0.4, 0.97)
    ao = np.clip(0.35 + 0.65 * occ, 0, 1)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, 30.0, rough, ao)   # b4: 2048 px / 1 m (b3 1024 / 0.5 m, 22)


def knot_weave_black(n=2048, seed=461):
    """Matfix b3 (blind judge: "the border is too thin and too flat and reads as dark grey, not black. The reference
    has a wide, jet-black woven or knotted border ... with its own rope texture"): the field's knots (same lattice, so
    the weave runs on into the border) in a jet black, a little satin on the knot crowns so the rope relief reads."""
    return knot_weave(n, seed, name="HEntKnotB", gap="#040303", crown="#181513", rough0=0.78)   # b4: b3 #1F1B18 / 0.74 read grey lit


def nub_weave(n=2048, seed=471, name="HEntNub", gap="#2A1E17", crown="#907260", nr=30, nc=36, offset=0.5, sx=1.0, tone_k=1.0):
    """r20 mat (2026-09-28, judge 7/10 on T_AK_HEntKnot: "the knots are ~1.5x too coarse (about 17 visible rows vs ~25 in
    the reference) ... tall vertical ovals stacked in columns (reads like cable-knit) ... vertical seams mid-mat at night";
    "the golden field is washed out"): small, ROUND, even nubs in a staggered lattice. A 1 m tile at 2048 px: nr rows
    along U (hero_entrance maps U to world Y, toward the bar; 2.78 cm apart: ~25 rows over the 0.76 m field, as reference
    2's C1 field) of nc nubs along V (world X; 2.78 cm, reference 2's column period 7.4 px through C1), alternate rows
    offset half a nub (nr even, so the offset tiles), so the rows read as strongly as the columns. Every nub is one smooth
    round dome (height = the max of the neighbouring domes: no cell steps), touching its row neighbours at a soft pinch,
    a darker pocket where three nubs meet; the size / position / tone jitter is small and per nub only (b7's per-column
    knot phases and reversed-slant columns read as vertical seams at night: gone), one twist direction for the plies on
    every nub (alternating reads as knit). Everything is periodic on the tile (checked: edge differences equal the
    interior's). A darker, warmer grey-tan than HEntKnot (golden field read washed out)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    rf = uu * nr / n + MT.pnoise(n, n, 3.0, seed + 1) * 0.025          # row coordinate (row units), a whisper of wander
    cfb = vv * nc / n + MT.pnoise(n, n, 3.0, seed + 2) * 0.025         # column coordinate (nub units)
    rj = rng.uniform(-0.03, 0.03, nr)
    cj = rng.uniform(-0.04, 0.04, (nr, nc))
    # b2: the lattice in pitch units (rows 3.33 cm, nubs 2.78 cm along a row: ~5 px x 7.5 px through C1, reference 2's);
    # b1 (hard max of steep domes, rows 2.78 cm) read as fish scales / a honeycomb: softer domes merged by a smooth max
    rad = rng.uniform(0.56, 0.60, (nr, nc))                          # dome radius (pitch units): neighbours touch
    amp = rng.uniform(0.92, 1.0, (nr, nc))
    tone = rng.normal(0, 1, (nr, nc)) * tone_k                     # rib: calmer per-nub tone (no checker)
    ply_ph = rng.uniform(0, 1, (nr, nc))
    r0 = np.floor(rf).astype(int)
    E = np.zeros((n, n)); W = np.zeros((n, n)); T = np.zeros((n, n)); P = np.zeros((n, n))
    for dr in (-1, 0, 1):
        r = r0 + dr
        rm = r % nr
        dy = rf - (r + 0.5 + rj[rm])
        cf = cfb - offset * (r % 2)                                   # alternate rows offset half a nub (rib: none)
        c0 = np.floor(cf).astype(int)
        for dc in (-1, 0, 1):
            c = c0 + dc
            cm = c % nc
            dx = cf - (c + 0.5 + cj[rm, cm])
            rr = rad[rm, cm]
            r2 = ((dx / sx) ** 2 + dy * dy) / (rr * rr)                 # sx > 1: nubs merge along the row (a rib)
            dome = np.clip(1 - r2, 0, 1) ** 0.9 * amp[rm, cm]
            # three plies twisting across the nub (a looped cord), one slant everywhere
            ply = 0.5 + 0.5 * np.cos(2 * np.pi * (1.6 * (0.62 * dx - 0.78 * dy) / rr + ply_ph[rm, cm]))
            w = np.exp(24 * dome) * (dome > 0)
            E += np.exp(10 * dome) - 1                                  # b2: smooth max (soft creases, no hex outlines)
            W += w; T += w * tone[rm, cm]; P += w * ply
    H = np.log1p(E) / 10
    T = T / np.maximum(W, 1e-9)
    P = P / np.maximum(W, 1e-9)
    fuzz = MT.pnoise(n, n, 0.3, seed + 3)
    mott = MT.pnoise(n, n, 2.4, seed + 4)
    h = H * (0.92 + 0.08 * P) + 0.010 * fuzz
    occ = np.clip(H / 0.5, 0, 1) ** 0.7
    k = np.clip(0.54 + 0.40 * occ + 0.10 * (P - 0.5) * occ + 0.03 * T + 0.02 * np.clip(fuzz, -2, 2)
                + 0.025 * mott, 0, 1)[..., None]
    g, cr = MT.srgb(gap), MT.srgb(crown)
    bc = g * (1 - k) + cr * k
    bc = bc * (1 + np.array([0.010, 0.0, -0.012]) * T[..., None])
    # b4 tried matte crowns (0.96) and a warmer #947056: golden R/G matched reference 2 (1.34) but the night field went
    # orange (G/B 2.2 against b7's 1.5; the user's default is night): kept b3's
    rough = np.clip(0.86 - 0.05 * occ + 0.03 * fuzz, 0.4, 0.97)
    ao = np.clip(0.30 + 0.70 * occ, 0, 1)
    # b3: normal 22 -> 18 (b2's night field read 27% darker than b7's, the moon grazing deep nub shading)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, 18.0, rough, ao)


def rib_weave(n=2048, seed=491):
    """r20 fix round (blind judge 7/10, delta 4: the HEntNub field read as a pebbled, fish-scale bump texture; reference
    2's is a fine, even, ribbed coir / tatami weave): the nub lattice with its rows ALIGNED (no half-nub offset: the
    staggered rows made the scales) and each nub stretched 1.6x along its row, so the nubs of a row merge into one
    continuous rib running across the mat (V = world X) with a soft stitch pinch every 2.78 cm; the rows 3.33 cm apart
    (~23 over the field), the same tone, roughness and relief as HEntNub. Periodic on the 1 m tile."""
    return nub_weave(n, seed, name="HEntRib", offset=0.0, sx=1.6, tone_k=0.35)


def rope_black(n=2048, seed=481, name="HEntRopeB", ncord=64, twist=120, gap="#050404", crown="#110F0E", nstrength=3.0):
    """r20 mat (judge 7/10: "the border must be solid near-BLACK with a fine rope texture, an even width, crisp edges (it
    reads speckled grey in golden light)"): the binding as fine twisted black cords laid ALONG the border (hero_entrance
    maps U along each border strip, V across it). A 1 m tile at 2048 px: ncord cords across V (1.56 cm, ~4 across the
    binding), each with plies slanting across it every 1/twist m (8.3 mm); near-black (#070606 in the creases to #171412
    on the crowns), matte (roughness ~0.84) and a gentle normal, so the sun finds no bright glints (HEntKnotB's satin
    knot crowns read as grey speckle)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    cv = vv * ncord / n
    ci = np.floor(cv).astype(int) % ncord
    pc = cv % 1.0
    cord = np.clip(1 - (2 * pc - 1) ** 2, 0, 1) ** 0.5                 # a round cord across
    ph = rng.uniform(0, 1, ncord)[ci]
    ply = 0.5 + 0.5 * np.cos(2 * np.pi * (uu * twist / n + 1.1 * pc + ph))   # plies slanting across the cord
    fuzz = MT.pnoise(n, n, 0.4, seed + 1)
    mott = MT.pnoise(n, n, 2.2, seed + 2)
    h = cord * (0.75 + 0.25 * ply) + 0.02 * fuzz
    k = np.clip(0.25 + 0.55 * cord * (0.7 + 0.3 * ply) + 0.04 * mott + 0.03 * np.clip(fuzz, -2, 2), 0, 1)[..., None]
    # b2: b1 (#171412 crowns, roughness 0.86, normal 8) lit up as grey-white cord lines in the golden sun: darker, matte,
    # a gentle normal (the rope reads up close, not as glints)
    g, cr = MT.srgb(gap), MT.srgb(crown)
    bc = g * (1 - k) + cr * k
    rough = np.clip(0.95 - 0.02 * cord + 0.02 * fuzz, 0.85, 1.0)
    ao = np.clip(0.55 + 0.45 * cord, 0, 1)
    return MT.save_set(name, bc, h, nstrength, rough, ao)


def rope_navy(n=2048, seed=487):
    """r17 mat (blind judge delta 6: "the binding is flat, pure black; the reference binding is a very dark navy-black
    with a subtle woven or stitched texture along its length"): HEntRopeB's twisted cords laid along the binding, a touch
    lifted and cooler (#060709 creases to #14151B crowns, was #050404 / #110F0E; b1 #1A1C25 read lavender-grey in the
    golden sun) and a firmer cord normal (5, was 3) so
    the weave shows along the strip; still matte (roughness ~0.95)."""
    return rope_black(n, seed, name="HEntRopeN", ncord=64, twist=120, gap="#060709", crown="#14151B", nstrength=5.0)


def timber_board_matte(n=2048, seed=451):
    """r20 mat b2: T_AK_HEntTimberM (the mat surround boards and the pit's side returns) at roughness ~0.84 (was ~0.62):
    in the golden preset the low sun's sheen turned the near-black boards pale cream in C1 and the top-down views."""
    return timber_ebony(n, seed, name="HEntTimberMR", dark="#1A1411", mid="#261D17", lite="#3C3026", rough0=0.84, nknots=0)


def coir_bump(n=2048, seed=501, name="HEntCoirB", gap="#150F0B", crown="#8A7564", nr=33, nc=36, across=0.94, jit=0.04,
              rad_r=(0.55, 0.59), amp_r=(0.85, 1.0), row_shift=0.0, wander=0.03):
    """r16 entry (2026-09-29, the user's crop entry_foreground_crop.png / reference 2 zoomed: "a darker, coarse, bumpy
    coir mat; ours is fine, light and tatami-like"): a coarse loop-pile coir. Reference 2's field through C1 is a GRID
    of round bumps - columns 7.5 px apart at the far end (2.7-2.8 cm, measured by FFT), rows ~3 cm, the columns the
    stronger - each bump lit on one side and dark on the other, deep dark pockets between them, warm grey-brown
    ((106-131, 79-97, 63-79) in the golden light, R/G 1.35, G/B 1.22). HEntRib merged the bumps into ribs across the
    mat (the "tatami" read); HEntNub staggered them (the "fish-scale" read). Here: rows ALIGNED (no offset) and each
    bump its own round dome, packed so neighbours meet in dark creases (radius 0.57 pitch, a little narrower across, so
    the creases between the columns run deeper), bristly coir fibres slanting across each loop, strong relief (normal
    30), dark pockets where four bumps meet. b1 (radius 0.47, hard max) read as separate discs on a dark ground.
    A 1 m tile at 2048 px: nr rows along U (hero_entrance maps U to world Y), nc bumps along V (world X). Periodic."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    rf = uu * nr / n + MT.pnoise(n, n, 3.0, seed + 1) * wander         # row coordinate (row units), a little wander
    # coir_loop: each row slides along itself by its own amount (no column grid survives from row to row)
    rsh = rng.uniform(-row_shift, row_shift, nr) if row_shift else np.zeros(nr)
    cf = vv * nc / n + MT.pnoise(n, n, 3.0, seed + 2) * wander
    rj = rng.uniform(-jit, jit, (nr, nc))
    cj = rng.uniform(-jit, jit, (nr, nc))
    rad = rng.uniform(*rad_r, (nr, nc))
    amp = rng.uniform(*amp_r, (nr, nc))
    tone = rng.normal(0, 1, (nr, nc))
    slant = rng.uniform(-0.25, 0.25, (nr, nc))
    ph = rng.uniform(0, 1, (nr, nc))
    r0 = np.floor(rf).astype(int)
    E = np.zeros((n, n)); W = np.zeros((n, n)); T = np.zeros((n, n)); F = np.zeros((n, n))
    for dr in (-1, 0, 1):
        r = r0 + dr
        rm = r % nr
        cfs = cf - rsh[rm]                                               # this row's own slide (no seams: per row)
        c0 = np.floor(cfs).astype(int)
        for dc in (-1, 0, 1):
            c = c0 + dc
            cm = c % nc
            dy = rf - (r + 0.5 + rj[rm, cm])
            dx = cfs - (c + 0.5 + cj[rm, cm])
            rr = rad[rm, cm]
            q = ((dx / across) ** 2 + dy * dy) / (rr * rr)               # 0.94: a touch narrower across (columns separate)
            dome = np.clip(1 - q, 0, 1) ** 0.75 * amp[rm, cm]           # a full round crown
            # coir fibres: fine twisted strands slanting across the loop (one slant per bump, jittered)
            fib = 0.5 + 0.5 * np.cos(2 * np.pi * (5.0 * (dx * (0.8 + slant[rm, cm]) - 0.6 * dy) / rr + ph[rm, cm]))
            w = np.exp(24 * dome) * (dome > 0)
            E += np.exp(12 * dome) - 1                                   # smooth max: soft creases, no outlines
            W += w; T += w * tone[rm, cm]; F += w * fib
    H = np.log1p(E) / 12
    T = T / np.maximum(W, 1e-9)
    F = F / np.maximum(W, 1e-9)
    fuzz = MT.pnoise(n, n, 0.2, seed + 3)                                # bristle speckle
    mott = MT.pnoise(n, n, 2.4, seed + 4)
    h = H * (0.90 + 0.10 * F) + 0.012 * fuzz
    occ = np.clip(H / 0.55, 0, 1) ** 1.4                                  # 0 in the pockets, 1 on the crowns
    # b2 (b1 C1: golden pockets read pure black under white crowns, a polka-dot grid; reference 2's pockets are a dark
    # brown, not black): the pockets lifted (k 0.14 -> 0.26)
    k = np.clip(0.26 + 0.64 * occ + 0.09 * (F - 0.5) * occ + 0.035 * T + 0.03 * np.clip(fuzz, -2, 2)
                + 0.03 * mott, 0, 1)[..., None]
    g, cr = MT.srgb(gap), MT.srgb(crown)
    bc = g * (1 - k) + cr * k
    bc = bc * (1 + np.array([0.012, 0.0, -0.010]) * T[..., None])
    rough = np.clip(0.90 - 0.04 * occ + 0.03 * fuzz, 0.6, 0.98)
    ao = np.clip(0.20 + 0.80 * occ, 0, 1)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, 30.0, rough, ao)


def coir_loop(n=2048):
    """r16 fix round (blind judge 7/10, point 5: HEntCoirB's field read as a very regular dot grid, like pegboard, and
    light in the golden sun; reference 2 / entry_foreground_crop.png show LOOPED ROWS of coarse coir, darker): the same
    loop pile, but each loop is elongated along its row (1.18x) so neighbours in a row merge into a knotted looped row
    with pinches between the loops, the rows parted by deeper creases; every row slides along itself by a random amount
    (+-0.5 loop) and the loops jitter (+-0.12), vary in size (0.50-0.62) and height (0.70-1.0), so no column grid or
    polka-dot lattice survives; darker, warmer crowns (#7A5C42, was #8A7564; b1's #6C5A4B read grey in the sun). Rows ~3.0 cm (33 per metre) as before."""
    return coir_bump(n, seed=517, name="HEntCoirL", gap="#140C07", crown="#7A5C42", nr=33, nc=30, across=1.18,
                     jit=0.12, rad_r=(0.50, 0.62), amp_r=(0.70, 1.0), row_shift=0.5, wander=0.06)


def sisal_rib(n=2048, seed=521, name="HEntSisalV", nc=36, nr=34, groove="#564636", crown="#8C7864", pinch=0.35,
              rib_pow=1.0, slant=0.08, nstrength=12.0, bead_pow=1.0, k0=0.20, mott_k=0.06):
    """r17 mat (blind judge 3/10 on HEntCoirL: "the weave reads as cobbles, pebbles or brick ... staggered horizontal rows
    of fat rounded lozenges with deep near-black gaps"; reference 2 / entry_foreground_crop.png: "a fine, even, low-relief
    ribbed weave: tight nubbly columns that run front-to-back, with only faint cross-banding", a warm grey-tan): a flat
    woven sisal of RIBS running along U (hero_entrance maps U to world Y, toward the hall), nc per metre across V (world
    X). Reference 2's C1 column period measured by FFT on 480-980 px: 7.1 px at y 960 to 8.3 px at y 1060, i.e. 2.8 cm
    at the mat's C1 scale (HEntCoirL's 3.33 cm rendered 8.5-9.4 px), so nc = 36. Each rib is a chain of low nubs
    (nr per metre, 2.9 cm: reference 2's faint cross-banding at ~4.5 px vertical), every rib at its own phase so no row
    grid lines up, the nub crests slanting a little (alternately left / right: a plied cord) and only a shallow pinch
    (0.35) between nubs, so the column grooves dominate (b1's pinch 0.60 / flat-topped ribs read as a grid of small
    rectangles, and at night as a herringbone). Soft rounded ribs (rib_pow 1.0), the relief low (normal 12: mean
    tilt ~1/3 of HEntCoirL's 38 deg), the albedo from groove #564636 to crown #8C7864 (a desaturated warm grey-tan;
    HEntCoirL's #7A5C42 over #140C07 pockets read rust and near-black at night), a soft large-scale mottle, fine fibre
    strands along each rib, a faint stray-fibre fuzz, matte fibre roughness ~0.79. C1 test copy (r17/mat): night
    nub:gap p90/p10 ~1.7 (HEntCoirL 7.1), golden ~1.3 (reference 2 1.5). 1 m tile at 2048 px, periodic."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    cf = vv * nc / n + MT.pnoise(n, n, 3.2, seed + 1) * 0.035           # across (rib units), a faint wander
    ci = np.floor(cf).astype(int) % nc
    pc = cf % 1.0
    across = np.clip(1 - (2 * pc - 1) ** 2, 0, 1) ** rib_pow            # a flat-topped rib, a narrow soft groove
    ph = rng.uniform(0, 1, nc)[ci]
    sl = (slant * np.where(np.arange(nc) % 2 == 0, 1.0, -1.0) * rng.uniform(0.7, 1.3, nc))[ci]
    a = uu * nr / n + ph + sl * (pc - 0.5) + MT.pnoise(n, n, 3.0, seed + 2) * 0.05
    na = np.floor(a).astype(int) % nr
    pa = a % 1.0
    bead = np.clip(1 - (2 * pa - 1) ** 2, 0, 1) ** bead_pow             # a rounded nub along the rib
    nub_amp = rng.uniform(0.85, 1.0, (nc, nr))[ci, na]
    nub_tone = rng.normal(0, 1, (nc, nr))[ci, na]
    rib_tone = rng.normal(0, 1, nc)[ci]
    strand = 0.5 + 0.5 * np.cos(2 * np.pi * (pc * 5 + 0.35 * pa))       # 5 fibre strands along each rib
    fuzz = MT.pnoise(n, n, 0.25, seed + 3)
    mott = MT.pnoise(n, n, 2.2, seed + 4)
    h = across * (1 - pinch + pinch * bead * nub_amp) * (0.94 + 0.06 * strand) + 0.015 * fuzz
    # albedo: groove -> crown by the relief, soft (the groove only ~0.75x the crown's value)
    k = np.clip(k0 + (1 - k0) * np.clip(h, 0, 1) ** 0.8 + 0.05 * (strand - 0.5) + 0.03 * np.clip(fuzz, -2, 2)
                + 0.03 * nub_tone + 0.04 * rib_tone + mott_k * mott, 0, 1.1)[..., None]
    g, cr = MT.srgb(groove), MT.srgb(crown)
    bc = g * (1 - k) + cr * k
    bc = bc * (1 + np.array([0.008, 0.0, -0.008]) * rib_tone[..., None])  # a faint warmer / cooler rib to rib
    rough = np.clip(0.82 - 0.05 * np.clip(h, 0, 1) + 0.03 * fuzz, 0.65, 0.95)
    ao = np.clip(0.55 + 0.45 * np.clip(h, 0, 1), 0, 1)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, nstrength, rough, ao)


def timber_polished(n=2048, seed=433):
    """r16 entry (the crop: "a thick polished near-black beam with a visible front face"): the step beam's TOP and its
    rounded nosing: the knot-free near-black bar timber (T_AK_HEntTimberN's colours, a little lighter grain so the
    polish shows the figure) under a polished finish (roughness ~0.16), so the top picks up the lit hall as a sheen and
    the rounded nosing a crisp highlight line (reference 2's top reads (59-87, 56-71, 60-79): a cool sheen over dark
    wood). Grain along V, 1.0 m tile."""
    return timber_ebony(n, seed, name="HEntTimberP", dark="#1A1411", mid="#271E18", lite="#4C3B2E", rough0=0.16,
                        nknots=0)


def timber_face(n=2048, seed=437):
    """r16 entry: the step beam's FRONT FACE (reference 2: a dark brown face (16-29, 8-18, 2-11) below the nosing,
    clearly darker than the top but not a void; ours at night rendered 0): the bar timber a step lighter
    (#2A1F17-#5A4533) at a satin finish (~0.34), so the lanterns' and the mat's light shows the face as timber."""
    return timber_ebony(n, seed, name="HEntTimberF", dark="#2A1F17", mid="#3A2C21", lite="#5A4533", rough0=0.34,
                        nknots=0)


def knit_bead(n=2048, seed=531, name="HEntSisalK", nc=36, nr=32, groove="#4A3C30", crown="#8E7C6A", rx=0.50,
              ry=0.66, sq=2.0, dome_pow=0.70, occ_s=0.70, nstrength=38.0, jit=0.05, size_j=0.07, amp_j=0.08,
              tone_j=0.10, drift=0.22, band_k=0.10, fuzz_k=0.05, k0=0.06, mott_k=0.09, col_shift=0.0):
    """r17 mat b2 (blind judge 6/10 on HEntSisalV: "continuous smooth ribs with dark grooves ... corduroy or tatami rush";
    reference 2 / entry_foreground_crop.png: "columns of separate, near-round nubs, each with its own bright dome
    highlight ... the nubs also line up side to side ... a nubbly loop or knit weave"): a knit-bead sisal. Columns along
    U (hero_entrance maps U to world Y, toward the hall), nc per metre across V (2.78 cm: reference 2's C1 column period
    7.1-8.4 px, kept from HEntSisalV), each column a chain of rounded beads, nr per metre along it (3.1 cm, 1.13:1 long
    to wide; reference 2's C1 cross period 4.6 px at y 960-1000 against HEntSisalV's 34 per metre at 4.3 px). Every bead
    is its own elliptical dome (radii rx across, ry along, in cell units; superellipse power sq) joined to its neighbours
    by a soft max, so the grooves between columns are narrow V creases and a PINCHED neck, a little shallower, parts
    the beads along the column (reference 2's column / cross gradient ratio 0.65; C1 golden b2 0.76, HEntSisalV 0.65
    with no beads); the beads line up side to side, the rows drifting a little (a
    large-scale wander of +-drift bead) so faint irregular cross bands show, as in the reference. Per bead: position
    (+-jit), size (+-size_j), height (+-amp_j) and albedo (+-tone_j) jitter; a faint low-frequency banding of the rows
    (band_k) and a soft blotchy mottle (mott_k); per-bead cavity AO in the albedo (Blender's review material does not wire ORM.R) and in ORM.R; fine fibre
    strands slanting across each bead and a stray-fibre fuzz on the rims (normal, roughness and a lighter fuzz tone on
    the rims: the soft sisal sheen); crowns a touch smoother (0.70) than the creases (0.92) so each nub catches its own
    highlight. Albedo from a warm grey-brown crease (#4A3C30) to a warm grey-tan crown (#8E7C6A, a touch greyer and
    cooler than HEntSisalV's #8C7864). Trials in r17/mat/work2 (C1 1448 x 1086): b1 (rx 0.50 / ry 0.53, sq 2) read as
    separate discs on a dark ground in the texture; sq 2.6 as square cobbles; K2-K7 as below, the chosen one the
    highest-relief K6 (golden local contrast / mean 0.23 on the field against reference 2's 0.175 and HEntSisalV's
    0.10) with stronger banding and mottle. 1 m tile at 2048 px, periodic (whole cells, periodic noise)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    # across: column coordinate from V; along: bead coordinate from U with a large-scale drift (rows wander)
    cf = vv * nc / n + MT.pnoise(n, n, 3.2, seed + 1) * 0.03
    af = uu * nr / n + MT.pnoise(n, n, 3.0, seed + 2, stretch_u=0.6) * drift
    cj = rng.uniform(-jit, jit, (nc, nr))
    aj = rng.uniform(-jit, jit, (nc, nr))
    sz = 1 + rng.uniform(-size_j, size_j, (nc, nr))
    amp = 1 + rng.uniform(-amp_j, amp_j, (nc, nr))
    tone = rng.uniform(-1, 1, (nc, nr))
    slant = np.where(rng.random((nc, nr)) < 0.5, -1.0, 1.0) * rng.uniform(0.25, 0.55, (nc, nr))
    fph = rng.uniform(0, 1, (nc, nr))
    # r17 fix round (knit_loop): each column slides along itself by its own amount, so the beads no longer line up
    # side to side in a regular grid (0 for HEntSisalK: its random stream is unchanged, drawn after the others)
    csh = rng.uniform(-col_shift, col_shift, nc) if col_shift else np.zeros(nc)
    c0 = np.floor(cf).astype(int)
    E = np.zeros((n, n)); W = np.zeros((n, n)); T = np.zeros((n, n)); F = np.zeros((n, n)); R = np.zeros((n, n))
    for dc in (-1, 0, 1):
        c = c0 + dc
        cm = c % nc
        afs = af - csh[cm]                                                  # this column's own slide
        a0 = np.floor(afs).astype(int)
        for da in (-1, 0, 1):
            a = a0 + da
            am = a % nr
            dx = cf - (c + 0.5 + cj[cm, am])
            dy = afs - (a + 0.5 + aj[cm, am])
            s = sz[cm, am]
            q = np.abs(dx / (rx * s)) ** sq + np.abs(dy / (ry * s)) ** sq      # a cushion (superellipse sq)
            dome = np.clip(1 - q, 0, 1) ** dome_pow * amp[cm, am]            # a round dome per bead
            fib = 0.5 + 0.5 * np.cos(2 * np.pi * (4.0 * (dx * slant[cm, am] * 2.2 - dy) + fph[cm, am]))
            w = np.exp(30 * dome) * (dome > 0)
            E += np.exp(14 * dome) - 1                                      # soft max: creases and necks, no outlines
            W += w; T += w * tone[cm, am]; F += w * fib; R += w * np.sqrt(np.clip(q, 0, 1))
    H = np.log1p(E) / 14
    W = np.maximum(W, 1e-9)
    T, F, R = T / W, F / W, R / W                                           # R: 0 at a bead's centre, 1 at its rim
    Hn = np.clip(H / max(float(np.percentile(H, 99.5)), 1e-6), 0, 1)
    rim = np.clip(R, 0, 1) ** 2 * (Hn > 0.02)
    fuzz = MT.pnoise(n, n, 0.15, seed + 3)                                  # stray fibres (high frequency)
    band = MT.pnoise(n, n, 2.6, seed + 4, stretch_v=0.15)                   # faint bands across the mat (rows)
    mott = MT.pnoise(n, n, 2.2, seed + 5)
    h = Hn * (0.92 + 0.08 * F) + 0.018 * fuzz * (0.4 + rim)
    occ = np.clip(Hn / occ_s, 0, 1) ** 1.2                                   # cavity: 0 in the creases, 1 on the crowns
    k = np.clip(k0 + (1 - k0) * occ ** 0.85 + 0.05 * (F - 0.5) * occ + tone_j * T + band_k * band
                + mott_k * mott + fuzz_k * np.clip(fuzz, -2, 2) * rim + 0.05 * rim * occ, 0, 1.15)[..., None]
    g, cr = MT.srgb(groove), MT.srgb(crown)
    bc = g * (1 - k) + cr * k
    bc = bc * (1 + np.array([0.010, 0.0, -0.010]) * T[..., None])           # a faint warmer / cooler bead to bead
    rough = np.clip(0.92 - 0.22 * occ * (1 - rim) + 0.03 * fuzz + 0.04 * rim, 0.62, 0.97)
    ao = np.clip(0.35 + 0.65 * occ, 0, 1)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, nstrength, rough, ao)


def knit_loop(n=2048):
    """r17 fix round (blind judge 7/10 on r17/final, delta c: HEntSisalK "is a regular, even grid that reads as tatami
    or basketweave; the reference is coarser and irregular with rounded loops", and "grey-beige against the reference's
    warm tan ... in golden the mat reads nearly white"): the knit-bead sisal made coarser (30 columns x 27 loops per
    metre: 3.3 x 3.7 cm, was 2.78 x 3.1), each loop rounder (rx 0.52 / ry 0.58, was 0.50 / 0.66) and irregular: every
    column slides along itself by up to +-0.28 loop (the side-to-side rows break up), more position / size / height /
    tone jitter (0.08 / 0.10 / 0.16 / 0.14), stronger row drift (0.40) and mottle; loops that meet along and across the
    columns (rx 0.56 / ry 0.64, shallower creases k0 0.16: a trial with 0.45 slides and wide dark creases read as
    pebbles); warm tan albedo (crease #4A301E, crown #9C7450: R/G 1.35 like reference 2's field, was the grey #4A3C30 /
    #8E7C6A)."""
    return knit_bead(n, seed=551, name="HEntSisalW", nc=30, nr=27, groove="#4A301E", crown="#9C7450", rx=0.56, ry=0.64,
                     sq=2.0, dome_pow=0.62, occ_s=0.66, nstrength=40.0, jit=0.08, size_j=0.10, amp_j=0.16,
                     tone_j=0.14, drift=0.40, band_k=0.08, fuzz_k=0.06, k0=0.16, mott_k=0.12, col_shift=0.28)


def braid_dark(w=2048, hgt=256):
    """r17 fix round (delta c3: "the black border is a wide solid band; the reference border is a thinner braided dark
    edge"): the binding braid for the narrower 5 cm binding (hero_entrance BIND_W): two slanted lanes of beads (was
    three), the bead crowns a lifted charcoal (#2A2521, was the near-black #0F0E0E) over black creases, so the braid
    reads as a textured dark edge rather than a solid black band; the stitch dots a warm grey (#3C3530)."""
    return braid_black(w, hgt, seed=543, name="HEntBraidL", lanes=2, pitch=0.011, crease="#040303", crown="#2A2521",
                       stitch="#3C3530", nstrength=8.0)


def braid_black(w=2048, hgt=256, seed=541, name="HEntBraidK", lanes=3, pitch=0.0125, crease="#030303",
                crown="#0F0E0E", stitch="#1E1C1A", nstrength=6.0, bind_w=0.08):
    """r17 mat b2 (blind judge 6/10, delta 3: "the reference border is a textured binding: a braided, nubbly black edge
    with a faint row of stitch dots along its inner edge and a slightly raised, rounded profile. Ours is a flat, smooth
    black strip ... fine nubbly or stitch normal in near-black (not pure 0) so it catches a faint sheen"): the binding
    as a flat braid. NOT a square tile: U (2048 px) runs 1 m along the strip, V (256 px) spans the binding's whole
    width (hero_entrance maps V 0 at the outer edge to 1 at the field, BIND_W across). Across V 0.06-0.84 `lanes` lanes
    of slanted beads (a herringbone: the lanes slant alternately), beads `pitch` apart along the strip (1.25 cm, the
    reference's border dots ~3-4 px at C1); at V 0.90 a row of small round stitch dots (8 mm apart) a touch lighter
    (#1E1C1A, faint); the creases #030303, the bead crowns #0F0E0E (near-black, neutral: b1's #1B1A1F crowns read
    purple-brown in the golden sun), crowns a little smoother (0.72) than the creases (0.95). Periodic along U."""
    uu, vv = np.meshgrid(np.arange(w), np.arange(hgt))
    rng = np.random.default_rng(seed)
    x = uu / w                                   # metres along the strip (1 m tile)
    v = 1.0 - (vv + 0.5) / hgt                   # 0 at the outer edge .. 1 at the field (image rows run down = V up)
    npitch = round(1.0 / pitch)
    b0, b1 = 0.06, 0.84
    lv = (v - b0) / (b1 - b0) * lanes
    li = np.clip(np.floor(lv), 0, lanes - 1).astype(int)
    pl = lv - li                                 # 0..1 across a lane
    inband = (v > b0) & (v < b1)
    sgn = np.where(li % 2 == 0, 1.0, -1.0)
    lane_w = (b1 - b0) / lanes * bind_w          # a lane's width in metres (BIND_W 8 cm; HEntBraidL's 5 cm reads close)
    t = x * npitch + sgn * (pl - 0.5) * (lane_w / pitch) * 0.9 + li * 0.5
    ti = np.floor(t).astype(int) % npitch
    pt = t % 1.0
    bead = np.clip(1 - (2 * pt - 1) ** 2, 0, 1) ** 0.6 * np.clip(1 - (2 * pl - 1) ** 2, 0, 1) ** 0.45
    bj = rng.uniform(0.85, 1.0, (lanes, npitch))[li, ti]
    bead = bead * bj * inband
    # the stitch dots along the inner edge
    sp = 0.008
    sx = (x / sp) % 1.0 - 0.5
    sv = (v - 0.905) / 0.035
    dot = np.clip(1 - ((sx * sp / 0.0028) ** 2 + sv ** 2), 0, 1) ** 0.5
    fuzz = MT.pnoise(hgt, w, 0.3, seed + 1)
    h = 0.85 * bead + 0.45 * dot + 0.03 * fuzz
    k = np.clip(0.10 + 0.80 * bead + 0.04 * np.clip(fuzz, -2, 2), 0, 1)[..., None]
    bc = MT.srgb(crease) * (1 - k) + MT.srgb(crown) * k
    dk = np.clip(dot * 1.3, 0, 1)[..., None]
    bc = bc * (1 - dk) + MT.srgb(stitch) * dk
    rough = np.clip(0.95 - 0.23 * bead - 0.15 * dot + 0.02 * fuzz, 0.68, 0.98)
    ao = np.clip(0.45 + 0.55 * np.maximum(bead, dot), 0, 1)
    return MT.save_set(name, bc, h, nstrength, rough, ao)


def sisal_twist(n=2048, seed=561, name="HEntSisalT", nc=36, nr=30, groove="#4E382C", crown="#98796A", gw=0.14,
                pinch=0.45, slant=0.06, stag=0.0, stag_j=0.22, wob=0.10, wj=0.04, aj=0.18, tone_j=0.14, col_tone=0.07,
                fib_k=0.10, fib_f=3.0, fuzz_k=0.05, band_k=0.08, mott_k=0.08, nstrength=45.0, k0=0.22, prof_p=1.7,
                bead=1.0, bead_p=4.0, seg_p=0.7, rough0=0.95, rough_k=0.10):
    """r18 mat (r17 judge: HEntSisalW's nubs ~25-30 % coarser than reference 2's, "felt balls or pebbles rather than a
    fine weave" at golden; "the reference weave has continuous ribs running toward the hall with slight fibre
    irregularity"): continuous sisal ribs carrying round nubs. Reference 2 at C1 (1448 x 1086) measured by 2D FFT on
    the field (WorkFiles/armory/hero/room_preview/r18/mat/work/mstats.py): rib period 7.31 / 7.76 / 7.21 px in three
    patches (HEntSisalW 8.98 / 8.98 / 8.53 at 30 per metre), so nc = 36 per metre (2.78 cm; renders 7.53 / 7.64 / 7.01);
    the along-rib period ~5.5-6 px on screen (nr = 30 per metre, 3.3 cm); the rib band holds 0.22 of the spectral
    energy and the rows 0.14 (HEntSisalW the reverse, 0.13 / 0.21: pebbles in a grid). Ribs along U (hero_entrance maps
    U to world Y, toward the hall), nc across V. Per rib: a rounded cord (cross-section power prof_p, a narrow soft
    groove gw of the pitch) pinched to (1 - pinch) between segments, and on each segment a round dome (bead, soft max
    power bead_p) so every nub carries its own highlight while the rib stays continuous; the segment creases nearly
    square across (slant), each rib's phase random (+-stag_j of a segment, stag = 0: the nubs half line up side to
    side, as the reference's faint rows); per nub height and tone jitter (aj, tone_j), fine fibre strands across each
    nub (fib_k, fib_f), stray-fibre fuzz, the ribs wandering sideways (wob of a pitch, +-wj width), per-rib tone
    (col_tone), faint cross bands (band_k), soft mottle. A warm tan-brown, less saturated than HEntSisalW (crown
    #98796A, groove #4E382C, shallow cavity k0) so the warm golden and lantern light render it tan rather than orange;
    matte (rough ~0.9; hero_entrance sets the specular level low). Trials in r18/mat/work (T2-T9). 1 m tile at 2048 px,
    periodic (whole ribs and nubs, periodic noise)."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    cf = vv * nc / n + wob * MT.pnoise(n, n, 3.4, seed + 1)             # the ribs wander a little sideways
    c = np.floor(cf).astype(int)
    cm = c % nc
    x = cf - c - 0.5                                                     # -0.5 .. 0.5 across a rib
    wc = 1 + rng.uniform(-wj, wj, nc)
    ph = np.where(np.arange(nc) % 2 == 1, stag, 0.0) + rng.uniform(-stag_j, stag_j, nc)
    r = np.abs(x) / (0.5 * (1 - 0.5 * gw) * wc[cm])                      # 0 at the rib's crown, 1 at the groove
    prof = np.sqrt(np.clip(1 - np.clip(r, 0, 1) ** prof_p, 0, 1))
    a = uu * nr / n + ph[cm] + slant * 2 * x + 0.06 * MT.pnoise(n, n, 3.0, seed + 2)
    j = np.floor(a).astype(int)
    jm = j % nr
    t = a - j - 0.5                                                      # -0.5 .. 0.5 along a segment
    amp = (1 + rng.uniform(-aj, aj, (nc, nr)))[cm, jm]
    tone = rng.uniform(-1, 1, (nc, nr))[cm, jm]
    ctone = rng.uniform(-1, 1, nc)[cm]
    fph = rng.uniform(0, 1, (nc, nr))[cm, jm]
    fib = 0.5 + 0.5 * np.cos(2 * np.pi * (fib_f * (t + 0.9 * 2 * x) + fph))   # fibre strands across each nub
    fuzz = MT.pnoise(n, n, 0.2, seed + 3)
    band = MT.pnoise(n, n, 2.6, seed + 4, stretch_v=0.15)                   # faint bands across the mat
    mott = MT.pnoise(n, n, 2.2, seed + 5)
    if bead > 0:   # a round dome per segment on the pinched rib (soft max): each nub its own round highlight
        dome = np.sqrt(np.clip(1 - (np.clip(r, 0, 1.5) ** 2 + (2 * t) ** 2), 0, 1)) * bead * amp
        body = (np.maximum(prof * (1 - pinch), 0) ** bead_p + dome ** bead_p) ** (1 / bead_p)
    else:          # plain twisted segments (the T2-T6 trials)
        seg = np.clip(1 - (2 * t) ** 2, 0, 1) ** seg_p
        body = prof * (1 - pinch + pinch * seg) * amp
    h = body + 0.035 * fib * prof + 0.012 * fuzz
    Hn = np.clip(body / max(float(np.percentile(body, 99.5)), 1e-6), 0, 1)
    occ = np.clip(Hn / 0.75, 0, 1) ** 1.1                                   # cavity: 0 in the grooves, 1 on the crowns
    k = np.clip(k0 + (1 - k0) * occ ** 0.8 + tone_j * tone * occ + col_tone * ctone + band_k * band + mott_k * mott
                + fib_k * (fib - 0.5) * occ + fuzz_k * np.clip(fuzz, -2, 2) * (1 - occ), 0, 1.1)[..., None]
    g, cr = MT.srgb(groove), MT.srgb(crown)
    bc = g * (1 - k) + cr * k
    rough = np.clip(rough0 - rough_k * occ + 0.03 * fuzz, 0.70, 0.99)
    ao = np.clip(0.35 + 0.65 * occ, 0, 1)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, nstrength, rough, ao)


def braid_charcoal(w=2048, hgt=256):
    """r18 mat (r17 judge: the black border about half reference 2's width and not one even band): the binding braid
    for the 6 cm binding on all four sides (hero_entrance BIND_W = BIND_NEAR): three slanted lanes of small beads
    9 mm apart (the reference's fine braided texture at ~16 px), charcoal-black crowns (#302C29) over black creases
    (#070606), faint stitch dots (#3A3531) along the inner edge; hero_entrance darkens it further with a tint so the
    band stays charcoal-black in the golden sun."""
    return braid_black(w, hgt, seed=547, name="HEntBraidC", lanes=3, pitch=0.009, crease="#070606", crown="#302C29",
                       stitch="#3A3531", nstrength=7.0, bind_w=0.060)


def MT_blur(img, sigma):
    """Periodic gaussian blur (FFT) of a 2D map, sigma in pixels (r18 mat second pass: soft sisal loops)."""
    if sigma <= 0:
        return img
    fy = np.fft.fftfreq(img.shape[0])[:, None]
    fx = np.fft.fftfreq(img.shape[1])[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


def sisal_cord(n=2048, seed=571, name="HEntSisalR", nc=36, seg=0.026, seg_j=0.45, groove="#635449", crown="#978679",
               k0=0.42, gw=0.30, pinch=0.60, slant=0.08, wob=0.08, wj=0.06, aj=0.20, tone_j=0.18, col_tone=0.06,
               fib_k=0.08, fib_f=2.5, band_k=0.05, mott_k=0.14, nstrength=24.0, rough0=0.93, rough_k=0.06, blur=2.0,
               dye_u=0.5, dye_w=0.040, dye_col="#2E2825", dye_k=0.90):
    """r18 mat, second pass (the r18 judge 5.5/10 on HEntSisalT: "the field weave reads as a rigid ribbed grid, not the
    soft sisal / coir loops in the reference": a strong regular row period of 5.0-5.7 px at C1 that reference 2 lacks,
    continuous dark grooves between the columns, relative contrast 0.21-0.25 against the reference's 0.13, an even grid
    of dots at night, too orange). Soft twisted sisal cords running along U (hero_entrance maps U to world Y, toward the
    hall), nc per metre across V (2.78 cm: reference 2's C1 column period 7.1-8.0 px measured by FFT in 12 patches is
    2.65-2.85 cm on the mat plane, mean 2.74). Along each cord a chain of soft, nearly square-on loops of RANDOM
    length (seg +-seg_j: 1.4-3.8 cm, each cord's chain made periodic on its own), so no along-cord period survives the
    averaging over cords (reference 2's along spectrum is weak and irregular); smooth cosine sections across the cord
    and along each loop, the height map blurred (blur px) so there are no creases; the grooves between cords soft and
    only moderately dark (k0), the cords wander and vary in width (wob, wj) so the grooves are not ruled lines; per
    loop tone jitter and a large soft mottle (mott_k) for reference 2's darker patches. A greyer warm tan (crown
    #978679, groove #635449; R/B ~1.25 at the texture: the golden and lantern light add ~1.35x, so the render lands
    near reference 2's R/B 1.65), a low normal strength (the r18 HEntSisalT ran 45) so the lanterns' grazing night
    light shows soft cords, not a dot grid. Matte (rough ~0.9). One dyed band per tile: dye_w wide cords centred on
    U dye_u blended dye_k toward dye_col (reference 2's dark woven cross band near the mat's near end, ~0.36x the
    field's brightness; hero_entrance offsets the field's U so the band lands on STRIPE_Y). Trials in
    WorkFiles/armory/hero/room_preview/r18/mat/work2 (SisR2, SisR3). 1 m tile at 2048 px, periodic."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    cf = vv * nc / n + wob * MT.pnoise(n, n, 3.4, seed + 1)             # the cords wander a little sideways
    c = np.floor(cf).astype(int)
    cm = c % nc
    x = cf - c - 0.5                                                     # -0.5 .. 0.5 across a cord
    wc = (1 + rng.uniform(-wj, wj, nc))[cm]
    prof = (0.5 + 0.5 * np.cos(2 * np.pi * np.clip(x / wc, -0.5, 0.5))) ** 0.55   # a smooth round cord section
    upos = uu / n + slant * seg * np.sign(np.arange(nc) % 2 - 0.5)[cm] * 2 * x \
        + 0.004 * MT.pnoise(n, n, 3.0, seed + 2)                          # the loops slant (alternately per cord)
    t = np.zeros((n, n))
    j = np.zeros((n, n), dtype=int)
    for ci in range(nc):                                                 # each cord: its own random-length loop chain
        L = []
        while sum(L) < 1.0:
            L.append(seg * (1 + rng.uniform(-seg_j, seg_j)))
        L = np.array(L) / sum(L)                                         # exactly 1 m: periodic along U
        edges = np.concatenate([[0.0], np.cumsum(L)])
        ph = rng.uniform(0, 1)
        m = cm == ci
        up = (upos[m] + ph) % 1.0
        k = np.clip(np.searchsorted(edges, up, side="right") - 1, 0, len(L) - 1)
        t[m] = (up - edges[k]) / L[k] - 0.5
        j[m] = k + 97 * ci
    rj = np.random.default_rng(seed + 9).uniform(-1, 1, (4096 * 2,))
    rj2 = np.random.default_rng(seed + 10).uniform(-1, 1, (4096 * 2,))
    rj3 = np.random.default_rng(seed + 11).uniform(0, 1, (4096 * 2,))
    jj = j % 8192
    amp = 1 + aj * rj[jj]
    tone = rj2[jj]
    ctone = rng.uniform(-1, 1, nc)[cm]
    loop = (0.5 + 0.5 * np.cos(2 * np.pi * t)) ** 0.7                  # a soft loop along the cord (0 at its ends)
    body = prof * (1 - pinch + pinch * loop * amp)
    fib = 0.5 + 0.5 * np.cos(2 * np.pi * (fib_f * (t + 1.2 * x) + rj3[jj]))   # fibre strands along each loop's twist
    fuzz = MT.pnoise(n, n, 0.2, seed + 3)
    band = MT.pnoise(n, n, 2.6, seed + 4, stretch_v=0.15)
    mott = MT.pnoise(n, n, 2.2, seed + 5)
    h = MT_blur(0.45 + 0.55 * body + 0.015 * fib * prof * loop + 0.012 * fuzz, blur)
    occ = np.clip(body / max(float(np.percentile(body, 99.0)), 1e-6), 0, 1)
    kk = np.clip(k0 + (1 - k0) * occ + tone_j * tone * occ * loop + col_tone * ctone + band_k * band + mott_k * mott
                 + fib_k * (fib - 0.5) * occ * loop + 0.04 * np.clip(fuzz, -2, 2), 0, 1.1)[..., None]
    g, cr = MT.srgb(groove), MT.srgb(crown)
    bc = g * (1 - kk) + cr * kk
    if dye_k > 0:   # the dyed cross band: its edges wander ~2 mm and soften over ~3 mm
        du = np.abs(((uu / n + 0.002 * MT.pnoise(n, n, 2.0, seed + 6) - dye_u + 0.5) % 1.0) - 0.5)
        dye = np.clip((0.5 * dye_w - du) / 0.003 + 0.5, 0, 1)[..., None] * dye_k
        bc = bc * (1 - dye) + MT.srgb(dye_col) * (0.75 + 0.5 * kk) * dye
    rough = np.clip(rough0 - rough_k * occ + 0.03 * fuzz, 0.70, 0.99)
    ao = np.clip(0.70 + 0.30 * occ, 0, 1)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, nstrength, rough, ao)


def braid_soft(w=2048, hgt=256):
    """r18 mat, second pass (the r18 judge: "in shade the top and bottom read as flat black bands ... at night the whole
    border renders as pure black (0), so no braid is readable"; reference 2's binding reads L ~36-64 on its sunlit west
    side, ~26-43 on the shaded east side and ~15-22 under the beam, against a field of ~90): the binding braid for the
    5.5 cm binding (hero_entrance BIND_W): three slanted lanes of 9 mm beads, a lifted charcoal crown (#4A4541) over
    near-black creases (#0A0908) so the braid reads as a dark TEXTURED band, lighter than the black slot outside it."""
    return braid_black(w, hgt, seed=549, name="HEntBraidD", lanes=3, pitch=0.009, crease="#0A0908", crown="#4A4541",
                       stitch="#524C47", nstrength=6.0, bind_w=0.055)


def sisal_nub(n=2048, seed=581, name="HEntSisalN", nc=36, seg=0.026, seg_j=0.22, groove="#5E4F44", crown="#9A897C",
              k0=0.42, rx=0.48, ry=0.50, base=0.42, gw=0.35, wob=0.07, wj=0.05, aj=0.18, sj=0.10, tone_j=0.16,
              col_tone=0.05, fib_k=0.07, fib_f=2.0, band_k=0.05, mott_k=0.14, nstrength=26.0, rough0=0.93,
              rough_k=0.06, blur=2.2, dye_u=0.5, dye_w=0.040, dye_col="#2E2825", dye_k=0.90):
    """r18 final fix (the r18 combined judge 8/10, delta 4: "the r18 weave reads as long chain-stitch columns, where the
    reference shows round nubby bumps"; the weave pitch (column period 7.38 vs 7.26 px at C1), the row spectrum and the
    shaded mean colour already matched): the same cords (nc per metre across V, 2.78 cm; the loops seg +-seg_j along
    U, each cord's chain periodic on its own and its phase random, so the rows only half line up as reference 2's), but
    each loop is now a ROUND dome (an ellipse rx x ry of the pitch / loop, soft-max'ed over a low cord base) instead of
    the separable cord-times-loop cushion whose continuous crowns read as chain columns: a deep pinch between loops
    (base 0.30 of the dome) and a soft groove between cords, so every nub carries its own round highlight. Per nub
    size / height / tone jitter (sj, aj, tone_j), a faint fibre twist across each nub, large soft mottle; the colours
    and the dyed cross band as HEntSisalR (the shaded C1 mean then stays near reference 2's). 1 m tile, periodic."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    rng = np.random.default_rng(seed)
    cf = vv * nc / n + wob * MT.pnoise(n, n, 3.4, seed + 1)
    c = np.floor(cf).astype(int)
    cm = c % nc
    x = cf - c - 0.5                                                     # -0.5 .. 0.5 across a cord
    wc = (1 + rng.uniform(-wj, wj, nc))[cm]
    prof = (0.5 + 0.5 * np.cos(2 * np.pi * np.clip(x / (wc * (1 - 0.5 * gw) * 2 * 0.5), -0.5, 0.5))) ** 0.6
    upos = uu / n + 0.003 * MT.pnoise(n, n, 3.0, seed + 2)
    t = np.zeros((n, n))
    j = np.zeros((n, n), dtype=int)
    for ci in range(nc):
        L = []
        while sum(L) < 1.0:
            L.append(seg * (1 + rng.uniform(-seg_j, seg_j)))
        L = np.array(L) / sum(L)
        edges = np.concatenate([[0.0], np.cumsum(L)])
        ph = rng.uniform(0, 1)
        m = cm == ci
        up = (upos[m] + ph) % 1.0
        k = np.clip(np.searchsorted(edges, up, side="right") - 1, 0, len(L) - 1)
        t[m] = (up - edges[k]) / L[k] - 0.5
        j[m] = k + 97 * ci
    jj = j % 8192
    rj = np.random.default_rng(seed + 9).uniform(-1, 1, (8192, 5))
    amp = 1 + aj * rj[jj, 0]
    size = 1 + sj * rj[jj, 1]
    tone = rj[jj, 2]
    ox, oy = 0.05 * rj[jj, 3], 0.05 * rj[jj, 4]                          # each nub a little off its cell centre
    ctone = rng.uniform(-1, 1, nc)[cm]
    rr = np.sqrt(((x - ox) / (rx * wc * size)) ** 2 + ((t - oy) / (ry * size)) ** 2)
    dome = np.sqrt(np.clip(1 - rr ** 2, 0, 1)) * amp                    # a round nub per loop
    body = (dome ** 4 + (base * prof) ** 4) ** 0.25                      # soft max over the low cord base
    fib = 0.5 + 0.5 * np.cos(2 * np.pi * (fib_f * (t + 1.0 * x) + 0.37 * (jj % 7)))
    fuzz = MT.pnoise(n, n, 0.2, seed + 3)
    band = MT.pnoise(n, n, 2.6, seed + 4, stretch_v=0.15)
    mott = MT.pnoise(n, n, 2.2, seed + 5)
    h = MT_blur(0.40 + 0.60 * body + 0.012 * fib * dome + 0.010 * fuzz, blur)
    occ = np.clip(body / max(float(np.percentile(body, 99.0)), 1e-6), 0, 1)
    kk = np.clip(k0 + (1 - k0) * occ ** 1.4 + tone_j * tone * occ + col_tone * ctone + band_k * band + mott_k * mott
                 + fib_k * (fib - 0.5) * occ + 0.04 * np.clip(fuzz, -2, 2), 0, 1.1)[..., None]
    g, cr = MT.srgb(groove), MT.srgb(crown)
    bc = g * (1 - kk) + cr * kk
    if dye_k > 0:
        du = np.abs(((uu / n + 0.002 * MT.pnoise(n, n, 2.0, seed + 6) - dye_u + 0.5) % 1.0) - 0.5)
        dye = np.clip((0.5 * dye_w - du) / 0.003 + 0.5, 0, 1)[..., None] * dye_k
        bc = bc * (1 - dye) + MT.srgb(dye_col) * (0.75 + 0.5 * kk) * dye
    rough = np.clip(rough0 - rough_k * occ + 0.03 * fuzz, 0.70, 0.99)
    ao = np.clip(0.62 + 0.38 * occ, 0, 1)
    return MT.save_set(name, np.clip(bc, 0, 0.9), h, nstrength, rough, ao)


def braid_plain(w=2048, hgt=256):
    """r18 final fix (the r18 combined judge, delta 4: "the border is a herringbone braid plus a black band rather than
    a plain solid black band"): the binding as ONE plain near-black band: the same three lanes of 9 mm beads, but
    crowns barely above the creases (#1C1A18 over #0C0B0A) and a soft normal, so it reads as a solid black cloth edge
    with only a fine nubbly sheen, merging with the black slot outside it instead of showing a lighter braid."""
    return braid_black(w, hgt, seed=553, name="HEntBraidP", lanes=3, pitch=0.009, crease="#0C0B0A", crown="#1C1A18",
                       stitch="#1E1C1A", nstrength=3.0, bind_w=0.055)


def brushed(n=1024, seed=391):
    """Final fix r6 (blind judge: the post shoe read heavy blotchy dark patina, its rivets lost; the sheet's shoe is a
    clean brushed brass with four prominent corner rivets - measured (155, 104, 56) on the sheet, the r5 bronze rendered
    (119, 84, 41)): a satin brushed brass, fine horizontal brush lines, faint soft tarnish only (no blotches), slightly
    darker grime in a thin band toward the tile edges is left to the geometry. Metallic 0.95; 0.5 m tile."""
    uu, vv = np.meshgrid(np.arange(n), np.arange(n))
    brush = MT.pnoise(n, n, 0.6, seed, stretch_v=0.01)                # fine brush lines along U
    brush2 = MT.pnoise(n, n, 1.0, seed + 1, stretch_v=0.04)
    soft = MT.pnoise(n, n, 2.4, seed + 2)
    tarn = np.clip((soft - 0.8) * 0.25, 0, 0.35)                      # faint soft tarnish
    # a first pass at #B8904F rendered a saturated yellow (142, 102, 35) against the sheet's paler (155, 104, 56)
    base, tar = MT.srgb("#C29A6E"), MT.srgb("#7E6A50")
    t3 = tarn[..., None]
    bc = base * (1 - t3) + tar * t3
    bc *= (1 + 0.012 * brush[..., None] + 0.012 * brush2[..., None])   # faint: strong lines read as wood grain
    height = 0.01 * brush + 0.006 * brush2
    rough = np.clip(0.34 + 0.05 * brush2 + 0.2 * tarn, 0.2, 0.7)
    metal = np.clip(0.96 - 0.3 * tarn, 0, 1)
    OUTP = MT.OUT
    MT.write_png(OUTP / "T_AK_HEntBrushed_BC.png", np.clip(bc, 0, 1))
    MT.write_png(OUTP / "T_AK_HEntBrushed_N.png", MT.normal_dx(height, 2.0))
    MT.write_png(OUTP / "T_AK_HEntBrushed_ORM.png", np.dstack([np.ones_like(rough), rough, metal]))
    return {"set": "HEntBrushed", "size": [n, n], "mean_srgb": [round(float(x), 3) for x in bc.reshape(-1, 3).mean(0)],
            "rough_mean": round(float(rough.mean()), 3)}


SETS = {"HEntTimber": timber, "HEntMat": mat, "HEntRush": rush, "HEntTimberW": timber_warm, "HEntCoir": coir,
        "HEntBronze": bronze, "HEntTimberE": timber_ebony, "HEntCoirR": coir_ribbed, "HEntBrushed": brushed,
        "HEntSisal": sisal, "HEntTimberG": timber_weathered, "HEntRushK": rush_knit, "HEntTimberL": timber_lacquer, "HEntWeave": weave,
        "HEntKnot": knot_weave, "HEntKnotB": knot_weave_black, "HEntTimberN": timber_bar, "HEntTimberM": timber_board,
        "HEntNub": nub_weave, "HEntRib": rib_weave, "HEntRopeB": rope_black, "HEntTimberMR": timber_board_matte,
        "HEntCoirB": coir_bump, "HEntCoirL": coir_loop, "HEntTimberP": timber_polished, "HEntTimberF": timber_face,
        "HEntSisalV": sisal_rib, "HEntRopeN": rope_navy, "HEntSisalK": knit_bead, "HEntBraidK": braid_black,
        "HEntSisalW": knit_loop, "HEntBraidL": braid_dark, "HEntSisalT": sisal_twist, "HEntBraidC": braid_charcoal,
        "HEntSisalR": sisal_cord, "HEntBraidD": braid_soft, "HEntSisalN": sisal_nub, "HEntBraidP": braid_plain}

if __name__ == "__main__":
    # r4: name the sets to write (e.g. `tex_entrance.py HEntRush`); an existing set is never rewritten by accident
    # entryfix r2: --out DIR writes the sets into DIR (a test copy's Textures folder) instead of Exports/ArmoryKit
    argv = sys.argv[1:]
    if "--out" in argv:
        MT.OUT = Path(argv[argv.index("--out") + 1])
        del argv[argv.index("--out"):argv.index("--out") + 2]
    want = argv or list(SETS)
    rep = []
    for name in want:
        _check(name)
        rep.append(SETS[name]())
    print(json.dumps(rep, indent=2))
