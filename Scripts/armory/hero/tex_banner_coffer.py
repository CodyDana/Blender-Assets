"""hero_banner_coffer's own texture sets (2026-09-28, round 3; references WorkFiles/armory/reference/banner.png and
armory3_reference2.png):

  T_AK_HBannerSatin_BC / _ORM / _N  the banner cloth (M_AK_HBannerSatin): EXACTLY the UV layout of T_AK_HBanner /
                                    make_armory_textures.banner (0.55 x 2.2 m cloth, 1024 x 4096, the crest centre 0.62 m
                                    below the top, 0.40 m across, the same emblem_field, so the user's ring thickness
                                    0.87-1.0 R is unchanged; the 8 mm border lines 2.5 cm in; the two small hem blossoms).
                                    Judge (round 2): the cloth read matte charcoal with a streaky wood-like noise and the
                                    gold flat ochre. Both were pixel-scale patterns beating against the texel grid (a 2.6 px
                                    warp and an 11 px satin float in the field, 3 px satin stitches in the gold = moire
                                    'grain'). Here: a CLEAN deep black satin field (no sub-texel weave, no noise; roughness
                                    0.30 so the belly and the folds carry a soft satin sheen), and the gold as bright
                                    metallic embroidery with every period >= 6 px (no moire): the lines and the ring a
                                    twisted gold cord (diagonal ridges, 3.3 mm pitch), the petals and the heart satin
                                    stitches (3.3 mm), a padded relief, metal 0.55 (foil-wrapped silk thread), roughness ~0.3.
  T_AK_HTassel_BC / _ORM / _N       the tassels (M_AK_HTassel), 1024 x 1024, periodic in U: rows v 0.00-0.50 the skirt (a
                                    fringe of fine gold threads along V, strands 0.7-1.4 mm grouped in soft bundles, light
                                    and dark gold), rows v 0.50-1.00 the head (a knotted 'pineapple' ball: two families of
                                    helical cords crossing over / under in a diamond weave, dark in the crossings).

All original and procedural (no photo, scan or third-party source). Uses make_armory_textures' writers (same PNG /
DirectX-normal conventions) and its emblem_field / raster. Writes ONLY T_AK_HBannerSatin_* and T_AK_HTassel_*.

Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_banner_coffer.py
      [banner] [tassel]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_armory_textures as MT  # noqa: E402

OWN = ("HBannerSatin", "HTassel")


def _save(name, bc, height, nstrength, rough, metal, ao=None):
    assert name in OWN, name
    MT.OUT.mkdir(parents=True, exist_ok=True)
    ao = np.ones_like(rough) if ao is None else ao
    MT.write_png(MT.OUT / f"T_AK_{name}_BC.png", np.clip(bc, 0, 1))
    MT.write_png(MT.OUT / f"T_AK_{name}_N.png", MT.normal_dx(height, nstrength))
    MT.write_png(MT.OUT / f"T_AK_{name}_ORM.png", np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1),
                                                           np.clip(metal, 0, 1)]))
    return {"set": name, "size": list(bc.shape[:2]), "mean_srgb": [round(float(x), 3) for x in bc.reshape(-1, 3).mean(0)],
            "rough_mean": round(float(rough.mean()), 3)}


def _mix(a, b, t):
    return a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]


# --------------------------------------------------------------------------- banner cloth

def banner(w=1024, h=4096, seed=517):
    W, H = 0.55, 2.2
    ex, ey, er = W / 2, H - 0.62, 0.20
    xx = (np.arange(w)[None, :] + 0.5) / w * W + np.zeros((h, 1))
    yy = (h - np.arange(h)[:, None] - 0.5) / h * H + np.zeros((1, w))

    def cov(fn):
        return MT.raster(fn, w, h, 0, W, 0, H, ss=2)

    ring = cov(lambda x, y: MT.emblem_field((x - ex) / er, (y - ey) / er) &
               (np.hypot((x - ex) / er, (y - ey) / er) >= 0.80))
    mon = cov(lambda x, y: MT.emblem_field((x - ex) / er, (y - ey) / er, ring=False))
    motif = np.zeros((h, w))
    for mx in (0.19, 0.36):
        motif = np.maximum(motif, cov(lambda x, y, mx=mx: MT.emblem_field((x - mx) / 0.045, (y - 0.30) / 0.045,
                                                                          ring=False)))
    inset, lw = 0.025, 0.008
    side = cov(lambda x, y: ((np.abs(x - inset) < lw / 2) | (np.abs(x - (W - inset)) < lw / 2)) &
               (y > inset - lw / 2) & (y < H - 0.05))
    hem = cov(lambda x, y: (np.abs(y - inset) < lw / 2) & (x > inset - lw / 2) & (x < W - inset + lw / 2))
    side = np.clip(side, 0, 1)
    hem = np.clip(hem * (1 - side), 0, 1)

    pitch = 0.0033                                   # >= 6 px at 1862 px / m: no beat against the texel grid
    ang = np.arctan2(yy - ey, xx - ex)
    r = np.hypot(xx - ex, yy - ey)
    # twisted cord: ridges running diagonally across the cord (the twist), a whole number round the ring
    n_ring = round(2 * np.pi * er * 0.935 / pitch)
    ph_ring = ang / (2 * np.pi) * n_ring + (r - er * 0.935) / pitch
    xl = np.where(xx < W / 2, xx - inset, xx - (W - inset))
    ph_side = (yy + xl) / pitch
    ph_hem = (xx + (yy - inset)) / pitch
    # petals: satin stitches laid across each petal (split / fishbone toward the tip); the heart: horizontal stitches
    rr = r / er
    k = np.round(((np.degrees(ang) - 90) % 360) / 72) % 5
    a = np.radians(90 + 72 * k)
    s_ax = (xx - ex) * np.cos(a) + (yy - ey) * np.sin(a)
    t_ax = -(xx - ex) * np.sin(a) + (yy - ey) * np.cos(a)
    ph_pet = np.where(rr < 0.16, (yy - ey) / pitch, (s_ax + 0.45 * np.abs(t_ax)) / pitch)
    ph_mot = yy / pitch
    phase = ph_ring * ring + ph_pet * mon + ph_side * side + ph_hem * hem + ph_mot * motif
    gold_m = np.clip(ring + mon + side + hem + motif, 0, 1)
    ridge = 0.5 - 0.5 * np.cos(2 * np.pi * phase)          # smooth rounded threads (no sharp sub-texel features)
    soft = MT.blur(gold_m, 2)
    edge = np.clip(1 - np.abs(soft - 0.5) / 0.35, 0, 1) * (gold_m > 0.05)   # the couched outline cord
    pad = MT.blur(gold_m, 4)                                                # padded (raised) embroidery

    # the clean deep black satin field: a very faint, very broad tonal drift only (no weave, no streaks)
    drift = MT.pnoise(h // 8, w // 8, 2.2, seed)
    drift = np.kron(drift, np.ones((8, 8)))
    cloth = MT.srgb("#0B0A0A")[None, None, :] * (1 + 0.035 * drift)[..., None]
    gold = _mix(MT.srgb("#A46F1A"), MT.srgb("#EDBF4C"), np.clip(0.40 + 0.60 * ridge, 0, 1))
    gold *= (1 - 0.28 * edge)[..., None]
    bc = cloth * (1 - gold_m[..., None]) + gold * gold_m[..., None]
    height = gold_m * (0.45 * pad + 0.14 * ridge + 0.04 * edge)
    # the gold half metallic: metallic thread is fine metal foil wrapped round a silk core, so it keeps a bright
    # diffuse gold under studio light as well as the specular glints (a pure metal reads dark ochre off-highlight)
    rough = 0.30 * (1 - gold_m) + (0.34 - 0.10 * ridge + 0.08 * edge) * gold_m
    metal = 0.55 * gold_m
    ao = 1 - 0.30 * gold_m * (1 - ridge) - 0.15 * edge
    rep = _save("HBannerSatin", bc, height * 0.6, 2.5, rough, metal, ao)
    rep["gold_fraction"] = round(float(gold_m.mean()), 4)
    return rep


# --------------------------------------------------------------------------- tassels

def tassel(n=1024, seed=523):
    u = (np.arange(n)[None, :] + 0.5) / n + np.zeros((n, 1))
    v = 1 - (np.arange(n)[:, None] + 0.5) / n + np.zeros((1, n))
    rng = np.random.default_rng(seed)
    hi, lo, dk = MT.srgb("#EDC04E"), MT.srgb("#B07E24"), MT.srgb("#5E3F14")

    # --- skirt (v < 0.5): fine threads along V. ~150 threads round the tassel (1 per ~6.8 px), grouped into soft
    # bundles by a slow random tone; each thread's own tone; a few darker gaps between bundles
    nth = 150
    tid = np.floor(u * nth).astype(int) % nth
    fu = (u * nth) % 1.0
    tone_t = rng.uniform(0, 1, nth)
    bundle = MT.pnoise(1, 4 * nth, 1.6, seed)[0]
    bundle = np.interp(np.arange(nth) + 0.5, np.arange(4 * nth) / 4, bundle)
    thr = 0.5 - 0.5 * np.cos(2 * np.pi * fu)               # each thread a rounded strand
    wav = 0.08 * np.sin(2 * np.pi * (v * 3 + tone_t[tid]))  # slight waviness of the strand brightness along it
    t_sk = np.clip(0.30 + 0.45 * thr + 0.25 * tone_t[tid] + 0.10 * bundle[tid] + wav, 0, 1)
    sk = _mix(lo, hi, t_sk)
    gap = np.clip(-bundle[tid] - 1.1, 0, 1) * 0.6            # a few deeper partings between bundles
    sk *= (1 - gap - 0.25 * (1 - thr))[..., None]
    h_sk = 0.5 * thr + 0.15 * bundle[tid]

    # --- head (v >= 0.5): the knotted ball. Two families of helical cords (8 each round the ball, 6 turns of the
    # pattern up the head) crossing in a diamond weave, over / under alternating, dark hollows between
    vh = (v - 0.5) * 2
    nc, nr = 8, 6
    p1 = u * nc + vh * nr * 0.5
    p2 = u * nc - vh * nr * 0.5
    c1 = 0.5 + 0.5 * np.cos(2 * np.pi * p1)
    c2 = 0.5 + 0.5 * np.cos(2 * np.pi * p2)
    over = (np.floor(p1) + np.floor(p2)) % 2                 # which cord is on top in this cell
    # each diamond cell is a raised loop of cord (a knob), worked alternately along one family and the other (the
    # basket-like pineapple weave): a pillow per cell, three cord strands across it, dark grooves between the knobs
    f1, f2 = p1 % 1.0, p2 % 1.0
    knob = (np.sin(np.pi * f1) * np.sin(np.pi * f2)) ** 0.5
    strand = 0.5 - 0.5 * np.cos(2 * np.pi * 3 * np.where(over > 0, f1, f2))
    cord = np.clip(knob * (0.72 + 0.28 * strand), 0, 1)
    del c1, c2
    tw = strand
    t_hd = np.clip(0.10 + 0.85 * cord ** 1.3 + 0.08 * tw * cord, 0, 1)
    hd = _mix(dk, hi, t_hd)
    h_hd = cord ** 1.2 + 0.08 * tw * cord

    kh = (v >= 0.5)[..., None]
    bc = np.where(kh, hd, sk)
    height = np.where(v >= 0.5, h_hd, h_sk)
    rough = np.where(v >= 0.5, 0.40 - 0.12 * cord, 0.36 - 0.08 * thr)
    metal = np.where(v >= 0.5, 0.30 + 0.25 * cord, 0.30 + 0.15 * thr)
    ao = np.where(v >= 0.5, 0.55 + 0.45 * cord, 0.85 + 0.15 * thr)
    return _save("HTassel", bc, height, 3.0, rough, metal, ao)


if __name__ == "__main__":
    which = sys.argv[1:] or ["banner", "tassel"]
    rep = []
    if "banner" in which:
        rep.append(banner())
    if "tassel" in which:
        rep.append(tassel())
    print(json.dumps(rep, indent=2))
