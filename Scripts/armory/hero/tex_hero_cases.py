"""Textures of the hero display cases (hero_cases.py), all NEW files (never overwrites another set):

  T_AK_HKickGlow_BC / _ORM / _N   the plinths' kick glow (fix 6, blind judge: "the kick band reads as flat, matte peach
                                  paint; the reference band has a hot, near-white core with a falloff into the bronze
                                  shoe"): a 1D vertical falloff used as an unlit emissive picture (emit_image) on the
                                  kick face and the hero plinth's recess: v = 1 (top, right under the lacquer overhang)
                                  a white-hot core, falling off through yellow-amber to a long brown-amber tail at
                                  v = 0 (the shoe). Constant along u (tiles along the perimeter). 32 x 512.
  T_AK_HMedallion_BC / _ORM / _N  the medallion face (fix 6, judge: "the medallion face is mottled and grainy, like gold
                                  leaf; the reference disc is brushed with a concentric grain"): the USER'S OWN emblem
                                  (make_armory_textures.emblem_field, the same design, ring and proportions as
                                  T_AK_Emblem, the same -1.06..1.06 span so the medallion UV is unchanged) in clean
                                  spun brass: no gold-leaf grain; a fine concentric turning grain in the normal and
                                  roughness maps and a soft two-lobe radial sheen baked into the colour (the brushed
                                  disc's light "bow-tie"), on the emblem's own dark ground. 2048 px.

Original and procedural (numpy only). Uses make_armory_textures' writers (same PNG / DirectX-normal conventions).
Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_hero_cases.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_armory_textures as MT  # noqa: E402

# ---- kick glow: (v, linear emission RGB) stops, v = 0 bottom (shoe) .. 1 top (under the overhang). Fitted through the
# preview's AgX (Medium High Contrast) to case_standard's kick, row by row (front view, 15 rows under the body): a 1-2 px
# white-hot line, a quick drop through yellow-amber (~251,198,78) to a long brown-amber tail (~145,80,25) at the shoe.
# The texture stores stop / KICK_MAX; hero_cases.KICK_EMIT must equal KICK_MAX (the emission strength)
KICK_MAX = 7.0
KICK_STOPS = [(0.000, (0.26, 0.090, 0.030)), (0.250, (0.29, 0.104, 0.035)), (0.433, (0.352, 0.117, 0.0375)),
              (0.500, (0.386, 0.137, 0.038)), (0.567, (0.51, 0.159, 0.038)), (0.633, (0.67, 0.195, 0.031)),
              (0.700, (1.07, 0.264, 0.0)), (0.767, (1.18, 0.392, 0.0)), (0.833, (1.29, 0.684, 0.0)),
              (0.900, (1.71, 1.05, 0.0)), (0.950, (6.9, 6.2, 3.1)), (1.000, (6.9, 6.2, 3.1))]
# ---- medallion
GOLD = "#CFA45A"         # spun brass (a touch brighter and cleaner than the kit's #C9A057 gold-leaf)
GROUND = "#15120F"       # the emblem's own dark ground (T_AK_Emblem)
SHEEN = 0.24             # the baked two-lobe radial sheen (+/- of the gold value)
SHEEN_ANGLE = 135.0      # the bright lobes' direction (deg, up-left / down-right as case_detail's disc)


def _to_srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def kick_glow(w=32, h=512):
    v = 1.0 - (np.arange(h) + 0.5) / h                 # row 0 = top = v 1
    vs = np.array([s[0] for s in KICK_STOPS])
    cols = np.array([s[1] for s in KICK_STOPS]) / KICK_MAX   # interpolate in linear light
    lin = np.stack([np.interp(v, vs, cols[:, c]) for c in range(3)], -1)
    bc = np.repeat(_to_srgb(lin)[:, None, :], w, 1)
    MT.OUT.mkdir(parents=True, exist_ok=True)
    return MT.save_set("HKickGlow", bc, np.zeros((h, w)), 1.0, np.full((h, w), 0.8), None, 0.0)


def medallion(n=2048, seed=83):
    E = 1.06
    m = MT.raster(MT.emblem_field, n, n, -E, E, -E, E, ss=2)
    c = (np.arange(n) + 0.5) / n * 2 * E - E
    x, y = np.meshgrid(c, -c)
    r = np.hypot(x, y)
    th = np.arctan2(y, x)
    # concentric turning grain: 1D noise along the radius (fine, a few coarser rings), no grain along the circle
    rng = np.random.default_rng(seed)
    nr = 4096
    g1 = MT.blur(rng.standard_normal((1, nr)), 1, 2)[0]
    g2 = MT.blur(rng.standard_normal((1, nr)), 12, 3)[0]
    g1 /= g1.std() + 1e-9
    g2 /= g2.std() + 1e-9
    ri = np.clip(r / E * (nr - 1), 0, nr - 1).astype(int)
    grain = 0.7 * g1[ri] + 0.3 * g2[ri]
    sheen = np.cos(2 * (th - np.radians(SHEEN_ANGLE))) * np.clip(r / 0.5, 0, 1)   # the brushed disc's bow-tie
    gold, ground = MT.srgb(GOLD), MT.srgb(GROUND)
    k = (1 + SHEEN * sheen + 0.012 * np.tanh(g2[ri]))[..., None]
    bc = ground[None, None, :] * (1 - m[..., None]) + np.clip(gold[None, None, :] * k, 0, 1) * m[..., None]
    height = MT.blur(m, 4) + 0.0015 * grain * m        # the emblem's relief as T_AK_Emblem, plus the fine turning
    rough = 0.20 * (1 - m) + (0.24 + 0.02 * np.tanh(grain)) * m
    rep = MT.save_set("HMedallion", bc, height, 3.0, rough, None, 0.0)
    orm = np.dstack([np.ones_like(m), np.clip(rough, 0.02, 1), m])   # metal = the gold mask (as T_AK_Emblem)
    MT.write_png(MT.OUT / "T_AK_HMedallion_ORM.png", orm)
    rep["gold_fraction"] = round(float(m.mean()), 4)
    return rep


if __name__ == "__main__":
    print(json.dumps({"kick": kick_glow(), "medallion": medallion()}))
