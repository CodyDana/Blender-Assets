"""The shared-material hero pass's own texture sets (hero_shared, 2026-09-28; references in WorkFiles/armory/reference:
armory3_reference2.png, entrance.png, rear_alcove.png, ceiling_coffer.png, banner.png):

  T_AK_HTimber_BC / _ORM / _N   M_AK_Timber's new look: a near-black espresso stain over wire-brushed timber with warm,
                                clearly visible grain (thin raised latewood lines catching a warm brown, broad soft
                                streaks, short worn flecks) and fine checks (short dark cracks along the grain). The grain
                                runs along U, the way the kit's Piece.box maps every timber face (U along the face's longer
                                extent = along the member), at the kit's 2 m tile (2048 px, ~1 mm / px).
                                T_AK_HEntTimber (tex_entrance.py) was the first candidate: it is tuned for a 1 m tile and its
                                grain runs along V, so on the kit's box UVs it runs ACROSS every scripted post and beam;
                                this set keeps its recipe (periodic noise, sharpened ring lines, checks) but re-scaled for
                                2 m and turned 90 degrees.
  T_AK_HBanner_BC / _ORM / _N   M_AK_Banner's new cloth: EXACTLY the UV layout of make_armory_textures.banner (0.55 x 2.2 m
                                cloth, crest centre 0.62 m below the top, 0.40 m across, the same emblem_field so the
                                user's ring thickness 0.87-1.0 R is unchanged, the two small hem blossoms, the 8 mm border
                                line 2.5 cm in), at twice the resolution (1024 x 4096). A deep black satin field (a fine
                                warp-faced satin weave in the normal map, ORM roughness ~0.35 for the soft sheen) and the
                                gold worked as fine embroidery: satin stitches of metallic gold thread laid ACROSS each
                                element (radial on the ring, across the border lines, across each petal), a couched darker
                                outline round every element, a raised padded relief. No noise streaks in the gold.
  T_AK_HPlank_BC / _ORM / _N    (r20 look: the BC re-coloured to PLANK_TARGET, a dark walnut, desaturation off; calibration
                                pass 2: the BC mixed PLANK_DESAT toward its own luminance, roughness +0.06)
                                calibration pass 1 (2026-09-28, the room judge: the floor read mirror-like with specular
                                streaks; reference 2's floor is matte to satin): the kit's own walnut floor (make_armory_
                                textures.plank, same seed, boards, joints and colour, so BC and N are the kit's pixels) with
                                a satin roughness (ORM G + PLANK_ROUGH_ADD: 0.16 -> ~0.30 on the boards, the joints rougher
                                still). M_AK_Plank uses it through hero_shared (the kit's T_AK_Plank is untouched).

All original and procedural (no photo, scan or third-party source), seamless where tiled (periodic FFT noise, whole-period
sines). Uses make_armory_textures' writers (same PNG / DirectX-normal conventions) and its emblem_field / raster.
Never overwrites another set: it writes only T_AK_HTimber_*, T_AK_HBanner_* and T_AK_HPlank_*.

Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_shared.py [timber] [banner] [plank]
      [--out DIR] [--plank-target #RRGGBB]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_armory_textures as MT  # noqa: E402

OWN = ("HTimber", "HBanner", "HPlank")


def _save(name, bc, height, nstrength, rough, ao=None, metal=None):
    assert name in OWN, name
    rep = MT.save_set(name, bc, height, nstrength, rough, ao)
    if metal is not None:   # a per-pixel metal channel (the gold thread)
        ao = np.ones_like(rough) if ao is None else ao
        MT.write_png(MT.OUT / f"T_AK_{name}_ORM.png", np.dstack([ao, np.clip(rough, 0.02, 1), np.clip(metal, 0, 1)]))
    return rep


# --------------------------------------------------------------------------- timber

def timber(n=2048, seed=401):
    """Built in a grain-along-V frame (rows = along the member) and transposed at the end, so the grain runs along U.
    The look of the reference beams (entrance.png, ceiling_coffer.png, rear_alcove.png): a near-black espresso body,
    straight grain of many thin, broken, unevenly spaced lighter lines and short streaks, a few fine checks."""
    u = np.arange(n)[None, :] / n            # across the grain (before the transpose)
    v = np.arange(n)[:, None] / n            # along the grain
    spacing = MT.pnoise(n, n, 2.6, seed, stretch_u=0.12)           # uneven line spacing (smooth across, long along)
    drift = MT.pnoise(n, n, 3.2, seed + 5)                         # a gentle sideways drift of the grain
    brk = MT.pnoise(n, n, 1.3, seed + 6, stretch_u=0.2)            # breaks each line into 5-40 cm runs
    fine = MT.pnoise(n, n, 0.9, seed + 1, stretch_u=0.012)         # fine grain / pores, long along the member
    fine2 = MT.pnoise(n, n, 0.6, seed + 7, stretch_u=0.05)         # short lighter streaks (brushed fibres)
    band = MT.pnoise(n, n, 1.4, seed + 2, stretch_u=0.03)          # soft light / dark streaks along the grain
    mott = MT.pnoise(n, n, 2.4, seed + 4)                          # a soft stain mottle
    # latewood lines: ~60 per 2 m tile across the grain (3.3 cm mean, uneven), sharpened into thin lines of uneven,
    # broken strength; a fainter set of finer lines between them
    ph = 60 * u + 1.8 * spacing + 0.25 * drift
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    ring2 = 0.5 + 0.5 * np.cos(2 * np.pi * (3 * ph + 0.5 * spacing))
    strength = np.clip(0.45 + 0.55 * brk, 0.0, 1.3)
    lines = ring ** 22 * strength + 0.45 * ring2 ** 24 * np.clip(0.3 + 0.7 * brk + 0.3 * fine, 0, 1.2)
    streak = np.clip(fine2 - 0.8, 0, None) * 0.8 + np.clip(fine - 1.1, 0, None) * 0.6
    light = np.clip(0.72 * lines + 0.42 * streak + 0.12 * np.clip(band, 0, 1.5), 0, 1)
    # fine checks: short dark cracks along the grain, a pixel or so wide, fading in and out
    rng = np.random.default_rng(seed)
    crack = np.zeros((n, n))
    for _ in range(18):
        c = rng.uniform(0, 1)
        v0, ln = rng.uniform(0, 1), rng.uniform(0.03, 0.14)          # 6-28 cm long on the 2 m tile
        wob = c + 0.0010 * np.sin(2 * np.pi * (v * rng.integers(1, 5) + rng.uniform(0, 1)))
        d = np.abs(((u - wob + 0.5) % 1.0) - 0.5) * n
        along = ((v - v0) % 1.0) / ln
        fade = np.clip(np.sin(np.pi * np.clip(along, 0, 1)), 0, 1) ** 0.6 * (along <= 1)
        crack = np.maximum(crack, np.clip(1.1 - d / rng.uniform(0.7, 1.2), 0, 1) * fade)
    dark = MT.srgb("#150E0A")       # espresso stain: near black with a warm red-brown undertone
    lite = MT.srgb("#6C4B35")       # the warm brushed grain
    body = dark[None, None, :] * (1 + 0.07 * mott[..., None] + 0.05 * np.tanh(band)[..., None])
    t = np.clip(light, 0, 1)[..., None]
    bc = body * (1 - t) + lite[None, None, :] * t
    bc *= (1 - 0.8 * crack)[..., None]
    height = 0.030 * lines + 0.012 * streak + 0.006 * np.tanh(band) + 0.004 * fine - 0.06 * crack
    # satin stained finish: the raised brushed lines are a touch rougher (worn), the flats sheen
    rough = np.clip(0.46 + 0.14 * light - 0.04 * np.tanh(mott) + 0.25 * crack, 0.3, 0.95)
    ao = 1 - 0.45 * crack
    # rows = along the member -> transpose so the grain runs along U (image columns)
    tr = (lambda a: np.ascontiguousarray(np.swapaxes(a, 0, 1)))
    return _save("HTimber", tr(bc), tr(height), 6.0, tr(rough), tr(ao))


# --------------------------------------------------------------------------- banner

def banner(w=1024, h=4096, seed=491):
    W, H = 0.55, 2.2                                   # make_armory_textures.banner's cloth (unchanged layout)
    ex, ey, er = W / 2, H - 0.62, 0.20                 # crest centre and radius (unchanged)
    ppm = w / W                                        # 1862 px / m
    xx = (np.arange(w)[None, :] + 0.5) / w * W + np.zeros((h, 1))
    yy = (h - np.arange(h)[:, None] - 0.5) / h * H + np.zeros((1, w))

    def cov(fn):
        return MT.raster(fn, w, h, 0, W, 0, H, ss=2)

    # the gold elements, each with its own stitch phase (the coordinate that runs ALONG the element, so the satin
    # stitches lie across it). Pitch 1.6 mm (3 px): fine thread, reads as a smooth gold sheen from a few metres.
    pitch = 0.0016
    ring = cov(lambda x, y: MT.emblem_field((x - ex) / er, (y - ey) / er) &
               (np.hypot((x - ex) / er, (y - ey) / er) >= 0.80))      # the ring (0.87-1.0 R) alone
    mon = cov(lambda x, y: MT.emblem_field((x - ex) / er, (y - ey) / er, ring=False))   # petals + heart
    motif = np.zeros((h, w))
    for mx in (0.19, 0.36):   # the two small hem blossoms (same place and size as the kit texture)
        motif = np.maximum(motif, cov(lambda x, y, mx=mx: MT.emblem_field((x - mx) / 0.045, (y - 0.30) / 0.045,
                                                                          ring=False)))
    inset, lw = 0.025, 0.008
    side = (np.abs(xx - inset) < lw / 2) | (np.abs(xx - (W - inset)) < lw / 2)
    hem = np.abs(yy - inset) < lw / 2
    side_m = (side & (yy > inset - lw / 2) & (yy < H - 0.05)).astype(float)
    hem_m = (hem & (xx > inset - lw / 2) & (xx < W - inset + lw / 2)).astype(float)
    # anti-alias the line edges a little (the kit set is hard-edged too; this keeps the same widths)
    side_m = np.maximum(side_m, 0)
    border = np.maximum(side_m, hem_m)

    # stitch phases
    ang = np.arctan2(yy - ey, xx - ex)
    n_ring = round(2 * np.pi * er * 0.935 / pitch)                # a whole number of stitches round the ring (no seam)
    ph_ring = (ang / (2 * np.pi)) * n_ring                       # along the ring's circumference -> radial stitches
    # petals: stitches across each petal (the phase runs along the petal's radial axis); the heart: horizontal stitches
    r = np.hypot(xx - ex, yy - ey) / er
    k = np.round(((np.degrees(ang) - 90) % 360) / 72) % 5
    a = np.radians(90 + 72 * k)
    s_ax = ((xx - ex) * np.cos(a) + (yy - ey) * np.sin(a))       # metres along the petal axis
    t_ax = (-(xx - ex) * np.sin(a) + (yy - ey) * np.cos(a))
    # split satin (fishbone): each petal is worked in two halves from its centre line, the stitches angled toward the
    # tip, so the petals read as embroidery; the heart is worked in horizontal stitches
    ph_pet = np.where(r < 0.16, (yy - ey) / pitch, (s_ax + 0.35 * np.abs(t_ax)) / pitch)
    ph_side = yy / pitch                                         # vertical lines: horizontal stitches
    ph_hem = xx / pitch
    ph_mot = yy / (pitch * 0.8)
    m_ring = np.clip(ring, 0, 1)
    m_mon = np.clip(mon, 0, 1)
    m_mot = np.clip(motif, 0, 1)
    phase = ph_ring * m_ring + ph_pet * m_mon + ph_side * side_m + ph_hem * hem_m * (1 - side_m) + ph_mot * m_mot
    # the coordinate ALONG each stitch (for the twist of the metallic thread)
    q = (r * er) * m_ring + np.where(r < 0.16, xx, np.abs(t_ax)) * m_mon + xx * side_m + yy * hem_m * (1 - side_m)         + xx * m_mot
    gold_m = np.clip(m_ring + m_mon + border + m_mot, 0, 1)
    f = (phase % 1.0)
    ridge = np.sin(np.pi * f) ** 0.7                             # each thread a rounded cord, dark between threads
    # a barely-there per-stitch tone, and the twist of the gold thread: small highlights every 2.4 mm along each stitch,
    # offset by half a twist on alternate stitches (the brick-like glint of couched metallic thread, not a streak)
    sid = np.floor(phase).astype(np.int64)
    rng = np.random.default_rng(seed)
    tone_lut = rng.normal(0, 1, 4096)
    tone = tone_lut[sid % 4096]
    twist = 0.5 + 0.5 * np.cos(2 * np.pi * (q / 0.0024 + 0.5 * (sid % 2)))
    # couched outline: a slightly darker, rounder cord along every element's edge (from the blurred mask)
    soft = MT.blur(gold_m, 2)
    edge = np.clip(1 - np.abs(soft - 0.5) / 0.32, 0, 1) * (gold_m > 0.05)
    # --- the black satin field
    # warp-faced satin: long floats along V (the warp), each float ~3 px wide and offset every weft; the texture is
    # far below a pixel at viewing distance, so it lives in the normal map and a tiny roughness variation only
    col = np.arange(w)[None, :]
    row = np.arange(h)[:, None]
    float_ph = ((row + (col % 5) * 7) % 11) / 11.0                # a 5-shaft satin stepping every column
    floats = 0.5 + 0.5 * np.cos(2 * np.pi * float_ph)
    warp = 0.5 + 0.5 * np.cos(2 * np.pi * col / 2.6)
    slub = MT.pnoise(h, w, 1.2, seed + 1)                         # very faint yarn irregularity (isotropic)
    cloth = MT.srgb("#0C0B0B")[None, None, :] * (1 + 0.04 * slub + 0.03 * warp)[..., None]
    # --- the gold thread
    gold_hi, gold_lo = MT.srgb("#D8AE5E"), MT.srgb("#9A7234")
    g = np.clip(0.50 + 0.40 * ridge + 0.12 * ridge * twist + 0.03 * tone, 0, 1)[..., None]
    gold = gold_lo[None, None, :] * (1 - g) + gold_hi[None, None, :] * g
    gold *= (1 - 0.30 * edge)[..., None]
    bc = cloth * (1 - gold_m[..., None]) + gold * gold_m[..., None]
    height = (0.004 * warp + 0.003 * floats) * (1 - gold_m) + gold_m * (0.35 * MT.blur(gold_m, 3) + 0.10 * ridge
                                                                         + 0.02 * ridge * twist + 0.03 * edge)
    rough = (0.35 + 0.02 * slub + 0.03 * (1 - floats)) * (1 - gold_m) + (0.34 - 0.06 * ridge + 0.10 * edge) * gold_m
    metal = 0.9 * gold_m
    ao = 1 - 0.25 * gold_m * (1 - ridge) - 0.15 * edge
    rep = _save("HBanner", bc, height * 0.6, 2.5, rough, ao, metal)
    rep["gold_fraction"] = round(float(gold_m.mean()), 4)
    rep["px_per_m"] = round(ppm, 1)
    return rep


# --------------------------------------------------------------------------- satin floor

# calibration pass 2 (reference 2's floor out of the sun reads a cool dark brown, C1 (0.37, 0.29, 0.28): its sheen
# reflects the bright windows; under the room's warm lights the kit walnut went orange at any brightness)
# r20 look (2026-10-01, the user: "the wood flooring should be like dark brown like the reference.. looks kinda grayish
# right now ... with the light on its gray"): judged by ALBEDO, not by the night renders. Pass 2's floor albedo (this BC
# x M_AK_Plank tint 1.8) was sRGB (77, 65, 56), HSV 25 deg / 0.27 / 0.30: a taupe grey-brown. Reference 2's shaded
# floor samples read mauve (hue ~340, sat 0.10-0.17) only because its satin sheen mirrors the bright sky; its sunlit
# boards (sat 0.35-0.40, hue 28-29 under a warm sun) and the read of the image are a dark walnut. So the desaturation is
# gone (PLANK_DESAT 0.30 -> 0) and the BC is RE-COLOURED to PLANK_TARGET: every pixel keeps its own linear luminance
# ratio to the mean (grain, board-to-board tint, seams and joints unchanged) and takes the target's chroma, so the mean
# linear albedo is exactly PLANK_TARGET. hero_shared FLOOR_TINT 1.8 -> 1.0 (the colour now lives in the map).
PLANK_DESAT = 0.0
PLANK_TARGET = "#3E2D25"   # r20 final2 (judge delta: #42291D overshot to orange-mahogany, golden floor S 0.44-0.79): chroma cut ~30 % at the same value, sRGB (62, 45, 37), HSV 19 deg / 0.40 / 0.24, linear lum 0.030. Was #42291D, r20 look: a rich dark walnut, sRGB (66, 41, 29), HSV 20 deg / 0.56 / 0.26, linear lum 0.029 (tried #4A3022: read chestnut under a white key)
PLANK_ROUGH_ADD = 0.06   # calibration pass 2: 0.14 -> 0.06 (boards ~0.22: reference 2 is a dark walnut with a satin sheen that mirrors the glows; pass 1 went matte). Pass 1: 0.16 -> 0.30


def _lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((np.clip(c, 0, 1) + 0.055) / 1.055) ** 2.4)


def _srgb(lin):
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)


def plank():
    """The kit's walnut floor set (make_armory_textures.plank, byte-identical BC and N) with a satin roughness, written as
    T_AK_HPlank_* (plank() calls save_set("Plank", ...): redirected here so the kit's T_AK_Plank_* are never touched)."""
    orig = MT.save_set

    def redirect(name, bc, height, nstrength, rough, ao=None, metal=0.0):
        assert name == "Plank", name
        lin = _lin(bc)
        W = np.array([0.2126, 0.7152, 0.0722])
        if PLANK_DESAT:   # calibration pass 2: a cooler, less saturated walnut (mixed toward its own luminance, linear)
            lum = (lin * W).sum(-1, keepdims=True)
            lin = lin * (1 - PLANK_DESAT) + lum * PLANK_DESAT
        if PLANK_TARGET:   # r20 look: the target's chroma at each pixel's own luminance ratio (the pattern is untouched)
            lum = (lin * W).sum(-1, keepdims=True)
            tgt = _lin(np.array([int(PLANK_TARGET[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]))
            lin = tgt[None, None, :] * (lum / lum.mean())
        bc = _srgb(lin)
        return orig("HPlank", bc, height, nstrength, np.clip(rough + PLANK_ROUGH_ADD, 0.02, 1.0), ao)   # (not _save: it calls MT.save_set)
    MT.save_set = redirect
    try:
        return MT.plank()
    finally:
        MT.save_set = orig


if __name__ == "__main__":
    args = sys.argv[1:]
    # r20 look: --out DIR writes the sets into a test copy's Textures folder (build_armory_kit --preview-dir prefers
    # <preview dir>/Textures), so a trial never lands in Exports/ArmoryKit/Textures; --plank-target #RRGGBB for a trial
    if "--out" in args:
        i = args.index("--out")
        MT.OUT = Path(args[i + 1])
        del args[i:i + 2]
    if "--plank-target" in args:
        i = args.index("--plank-target")
        PLANK_TARGET = args[i + 1]
        del args[i:i + 2]
    which = args or ["timber", "banner"]
    rep = []
    if "timber" in which:
        rep.append(timber())
    if "banner" in which:
        rep.append(banner())
    if "plank" in which:
        rep.append(plank())
    print(json.dumps(rep, indent=2))
