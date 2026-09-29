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


def timber_ebony(n=2048, seed=371, name="HEntTimberE", dark="#1E120A", mid="#2F1E12", lite="#553A26"):
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
    for _ in range(3):
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
    rough = np.clip(0.80 + 0.06 * np.tanh(mott) - 0.06 * lines + 0.15 * crack, 0.5, 0.97)
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
        "HEntSisal": sisal, "HEntTimberG": timber_weathered}

if __name__ == "__main__":
    # r4: name the sets to write (e.g. `tex_entrance.py HEntRush`); an existing set is never rewritten by accident
    want = sys.argv[1:] or list(SETS)
    rep = []
    for name in want:
        _check(name)
        rep.append(SETS[name]())
    print(json.dumps(rep, indent=2))
