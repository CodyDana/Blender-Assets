"""The rear alcove hero's own backlit panel picture (hero_rear_alcove, reference sheets rear_alcove.png / back_wall.png):

  T_AK_HAlcoveReturn_BC / _ORM / _N  final3: the light warm timber of the niche returns (the cheeks' inner faces), grain
                                     along U (hero_rear_alcove maps U along each member), 1 m tile, 1024 px: a honey
                                     tan body with soft darker latewood lines and a faint mottle (rear_alcove.png 3/4).
  T_AK_HAlcovePanel_BC / _ORM / _N   the lit parchment / marble panel behind the empty rack, ONE picture over the whole
                                     panel (unique 0-1 UV on its front face, 1.11 x 1.79 m, 512 x 1024 px): a saturated
                                     amber-gold soft cloudy mottle with only faint veins, a wide soft LED halo that
                                     brightens the last 5-8 cm inside every visible edge, and a warm hot spot at the top
                                     centre under the soffit lens. hero_rear_alcove uses it as an emissive picture
                                     (M_AK_HAlcovePanel: base colour and emission from the BC map). final4: very faint
                                     soft marbling, the bottom halo starts above the foot glow line.
  T_AK_HAlcoveGrille_BC / _ORM / _N  final4: the gold backlight behind the kumiko grille (unique 0-1 UV, 1024 x 512):
                                     saturated gold with a hot spot at the top centre (back_wall.png's grille).

final3 (judge 7: pale cream / peach, a cream-white halo, veins barely visible): a warmer, more saturated golden
amber body, visible faint marbled veins, a hot yellow-gold halo; the panel starts at the 72 cm cabinet.
Blind judge (earlier round, 7.5): the flat cream panel read too pale and uniform; the references show a saturated amber-gold
(~#C79D6B) cloudy parchment glowing hot along every edge. Original and procedural (periodic FFT noise, no photo, scan
or third-party source). Uses make_armory_textures' writers (same PNG / DirectX-normal conventions). Never overwrites
another set.

Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_rear_alcove.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_armory_textures as MT  # noqa: E402

NAME = "HAlcovePanel"
# the panel's front face in the piece frame (hero_rear_alcove: x 0.345..1.455, z 0.55..2.34) and its VISIBLE edges
# (inside the corner LED strips, above the cabinet top slab, under the grille rail's glow line)
PX0, PX1, PZ0, PZ1 = 0.345, 1.455, 0.67, 2.34
VX0, VX1, VZ0, VZ1 = 0.360, 1.440, 0.785, 2.322   # final4: VZ0 above the foot glow line (it hid the bottom halo)
BASE = "#A17A3C"      # mid-panel parchment (final3: at emit 2.2, tuned so the rendered panel reads a warm golden beige)
DEEP = "#8F6830"      # the darker clouds of the mottle
PALE = "#B18A48"      # the lighter clouds
HALO = "#FFA81C"      # the LED halo along every edge
HOT = "#FFC850"       # the hot spot at the top centre


def panel(w=512, h=1024, seed=411):
    u = (np.arange(w)[None, :] + 0.5) / w
    v = 1.0 - (np.arange(h)[:, None] + 0.5) / h            # rows run top-down, v = 1 at the top
    x = PX0 + u * (PX1 - PX0)
    z = PZ0 + v * (PZ1 - PZ0)
    sx = (PZ1 - PZ0) / (PX1 - PX0)                           # pnoise works in cycles per picture: keep clouds round
    # soft cloudy mottle: two octaves of smooth noise (large clouds + finer parchment fibre)
    cloud = MT.pnoise(h, w, 1.8, seed, stretch_u=sx)
    fine = MT.pnoise(h, w, 1.3, seed + 1, stretch_u=sx)
    m = np.clip(0.5 + 0.10 * cloud + 0.045 * fine, 0, 1)   # final4: a slightly more even parchment
    # only faint veins: thin ridges of a smooth noise field, shown only where a mask noise allows (sparse, broken)
    rid = MT.pnoise(h, w, 1.9, seed + 2, stretch_u=sx)
    mask = np.clip(0.55 + 0.6 * MT.pnoise(h, w, 2.4, seed + 3, stretch_u=sx), 0.15, 1)
    rid2 = MT.pnoise(h, w, 1.5, seed + 4, stretch_u=sx)
    rid3 = MT.pnoise(h, w, 1.3, seed + 5, stretch_u=sx)
    # final3: a fine crackle network over the whole panel (three ridge fields, thin), strongest where the mask allows
    rid4 = MT.pnoise(h, w, 1.1, seed + 6, stretch_u=sx)
    # final4 (judge: the veins read as darker brown crack / water-stain branches; rear_alcove.png's marbling is very
    # faint and soft): wider, softer ridges at a third of the darkening
    vein = np.maximum.reduce([np.exp(-(rid / 0.05) ** 2), 0.8 * np.exp(-(rid2 / 0.04) ** 2),
                              0.6 * np.exp(-(rid3 / 0.032) ** 2), 0.45 * np.exp(-(rid4 / 0.028) ** 2)]) * mask
    base, deep, pale = MT.srgb(BASE), MT.srgb(DEEP), MT.srgb(PALE)
    t = (m - 0.5)[..., None]
    col = base + (deep - base) * np.clip(t, 0, None) * 3.0 + (pale - base) * np.clip(-t, 0, None) * 3.0
    col = col * (1.0 - 0.045 * vein[..., None])  # final4: very faint soft marbling
    # the wide soft LED halo: each visible edge brightens its last 5-8 cm (smooth falloff, full on the edge)
    def fall(d):
        return np.exp(-np.power(np.clip(d, 0, None) / 0.050, 1.4))
    e = [fall(x - VX0), fall(VX1 - x), fall(z - VZ0), fall(VZ1 - z)]
    halo = 1.0 - (1 - e[0]) * (1 - e[1]) * (1 - e[2]) * (1 - e[3])
    # the hot spot at the top centre under the soffit lens
    hot = np.exp(-(((x - 0.9) / 0.22) ** 2 + ((z - VZ1) / 0.24) ** 2))
    col = col + (MT.srgb(HALO) - col) * (0.80 * halo)[..., None]
    col = col + (MT.srgb(HOT) - col) * (0.80 * hot)[..., None]
    height = 0.5 + 0.10 * cloud + 0.05 * fine - 0.06 * vein
    rough = np.full_like(m, 0.85) + 0.05 * fine
    return MT.save_set(NAME, np.clip(col, 0, 1), height, 0.6, np.clip(rough, 0.6, 0.95))


def return_timber(n=1024, seed=431):
    """Light warm timber for the niche returns, 1 m tile. Built with rows along the grain and transposed at the end,
    so the grain runs along U (image columns), like T_AK_HTimber."""
    u = np.arange(n)[None, :] / n            # across the grain (before the transpose)
    spacing = MT.pnoise(n, n, 2.6, seed, stretch_u=0.12)
    brk = MT.pnoise(n, n, 1.3, seed + 1, stretch_u=0.2)
    fine = MT.pnoise(n, n, 0.9, seed + 2, stretch_u=0.015)
    band = MT.pnoise(n, n, 1.4, seed + 3, stretch_u=0.03)
    mott = MT.pnoise(n, n, 2.4, seed + 4)
    # final4 (judge: the return read as a smooth tan gradient, grain barely visible; the reference 3/4 left return shows
    # clear vertical grain): denser, wider, darker latewood lines, fine streaks and broad figure bands
    ph = 44 * u + 2.2 * spacing                                   # ~44 latewood lines per metre, uneven
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    lines = ring ** 5 * np.clip(0.6 + 0.5 * brk, 0.15, 1.2)
    dark = np.clip(0.80 * lines + 0.35 * np.clip(fine - 0.3, 0, None) + 0.16 * np.tanh(band), 0, 1)
    body = MT.srgb("#B38655") * (1 + 0.06 * mott[..., None])
    late = MT.srgb("#5A391C")
    t = dark[..., None]
    bc = body * (1 - t) + late * t
    height = 0.02 * (1 - lines) + 0.004 * fine
    rough = np.clip(0.55 + 0.08 * lines + 0.03 * np.tanh(mott), 0.4, 0.8)
    tr = (lambda a: np.ascontiguousarray(np.swapaxes(a, 0, 1)))
    return MT.save_set("HAlcoveReturn", np.clip(tr(bc), 0, 1), tr(height), 3.0, tr(rough))


def grille_glow(w=1024, h=512, seed=451):
    """final4: the gold backlight behind the kumiko grille (x 0.345..1.455, z 2.355..2.96 on a unique 0-1 UV), after
    back_wall.png's grille: bright saturated gold in every opening with a hot spot at the top centre under the soffit
    lens, a little dimmer toward the lower corners."""
    u = (np.arange(w)[None, :] + 0.5) / w
    v = 1.0 - (np.arange(h)[:, None] + 0.5) / h
    x = 0.345 + u * 1.11
    z = 2.355 + v * 0.605
    soft = MT.pnoise(h, w, 2.0, seed, stretch_u=0.55)
    col = MT.srgb("#F0A032") * (1 + 0.05 * soft[..., None]) * (0.86 + 0.14 * v[..., None])
    hot = np.exp(-(((x - 0.9) / 0.26) ** 2 + ((z - 2.96) / 0.30) ** 2))
    col = col + (MT.srgb("#FFF0B8") - col) * (0.95 * hot)[..., None]
    return MT.save_set("HAlcoveGrille", np.clip(col, 0, 1), np.full((h, w), 0.5), 0.0, np.full((h, w), 0.9))


def showcase(w=512, h=512, seed=471):
    """Rear dais (2026-09-28): the corner showcases' backlit panel (hero_rear_alcove SM_AK_H_CornerShowcase: x 0.08..0.62,
    z 0.75..1.75 in the piece, 0.54 x 1.00 m, unique 0-1 UV), after armory3_reference2.png's corner niches: a paler,
    creamier parchment than the rack alcoves' amber panel, the same soft cloudy mottle and faint marbling, a warm LED halo
    inside the side and head edges and a hot spot under the soffit lens at the top centre."""
    # b4: the 0.64 x 0.71 m panel of the shorter, wider unit (x 0.08..0.72, z 0.75..1.46)
    # b8: the 0.54 x 0.99 m panel of the taller unit (x 0.08..0.62, z 0.62..1.61)
    x0, x1, z0, z1 = 0.08, 0.62, 0.62, 1.61
    vx0, vx1, vz0, vz1 = 0.082, 0.618, 0.622, 1.588   # inside the frame, under the head line
    u = (np.arange(w)[None, :] + 0.5) / w
    v = 1.0 - (np.arange(h)[:, None] + 0.5) / h
    x = x0 + u * (x1 - x0)
    z = z0 + v * (z1 - z0)
    sx = (z1 - z0) / (x1 - x0)
    cloud = MT.pnoise(h, w, 1.8, seed, stretch_u=sx)
    fine = MT.pnoise(h, w, 1.3, seed + 1, stretch_u=sx)
    m = np.clip(0.5 + 0.10 * cloud + 0.045 * fine, 0, 1)
    rid = MT.pnoise(h, w, 1.9, seed + 2, stretch_u=sx)
    mask = np.clip(0.55 + 0.6 * MT.pnoise(h, w, 2.4, seed + 3, stretch_u=sx), 0.15, 1)
    vein = np.exp(-(rid / 0.05) ** 2) * mask
    # b2: a little deeper and warmer (b1 read near-white in the golden C1, whiter than the rack alcoves)
    base, deep, pale = MT.srgb("#A98450"), MT.srgb("#9A7746"), MT.srgb("#B8935C")
    t = (m - 0.5)[..., None]
    col = base + (deep - base) * np.clip(t, 0, None) * 3.0 + (pale - base) * np.clip(-t, 0, None) * 3.0
    col = col * (1.0 - 0.04 * vein[..., None])

    def fall(d):
        return np.exp(-np.power(np.clip(d, 0, None) / 0.045, 1.4))
    e = [fall(x - vx0), fall(vx1 - x), fall(vz1 - z), 0.6 * fall(z - vz0)]
    halo = 1.0 - (1 - e[0]) * (1 - e[1]) * (1 - e[2]) * (1 - e[3])
    hot = np.exp(-(((x - 0.35) / 0.16) ** 2 + ((z - vz1) / 0.22) ** 2))
    col = col + (MT.srgb("#FFB84A") - col) * (0.50 * halo)[..., None]   # b4: 0.70 -> 0.50 (no side LED lines)
    col = col + (MT.srgb("#FFD890") - col) * (0.80 * hot)[..., None]
    height = 0.5 + 0.10 * cloud + 0.05 * fine - 0.06 * vein
    rough = np.full_like(m, 0.85) + 0.05 * fine
    return MT.save_set("HShowcasePanel", np.clip(col, 0, 1), height, 0.6, np.clip(rough, 0.6, 0.95))


if __name__ == "__main__":
    # rear dais (2026-09-28): [--out DIR] (a test copy's <preview dir>/Textures) [set names: HAlcovePanel HAlcoveReturn
    # HAlcoveGrille HShowcasePanel; default: all]
    argv = sys.argv[1:]
    if "--out" in argv:
        MT.OUT = Path(argv[argv.index("--out") + 1])
        del argv[argv.index("--out"):argv.index("--out") + 2]
    makers = {NAME: panel, "HAlcoveReturn": return_timber, "HAlcoveGrille": grille_glow, "HShowcasePanel": showcase}
    want = argv or list(makers)
    for nm in want:
        for suf in ("BC", "ORM", "N"):
            assert (MT.OUT / f"T_AK_{nm}_{suf}.png").name.startswith(("T_AK_HAlcove", "T_AK_HShowcase"))
    print(json.dumps([makers[nm]() for nm in want], indent=2))
