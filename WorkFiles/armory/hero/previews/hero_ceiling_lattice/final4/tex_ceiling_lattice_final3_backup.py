"""The ceiling lattice hero's own glow pictures (hero_ceiling_lattice, reference sheet ceiling_lattice.png):

  T_AK_HLatticeGlow_BC / _ORM / _N   the backlit panel behind the asanoha kumiko, ONE picture over the glow quad
                                     (unique 0-1 UV, d GLOW_E .. 2 - GLOW_E of the 2 x 2 m cell, 2048 px, 0.76 mm/px),
                                     painted cell by cell in register with the bars from hero_ceiling_lattice.cells():
                                     a smooth falloff inside every cell from a pale buttery cream-gold on its lit side
                                     to amber on its shadow side, a thin soft shadow along the bars on the shadow side
                                     (the sheet's zoom: the bars' soft shadows fall along SHADOW). No steps, no bands.
  T_AK_HLatticeSlot_BC / _ORM / _N   a 1-D glow ramp (256 x 8 px): U = how strongly the hidden LED lights a surface,
                                     0 dark timber .. 1 the pale-gold emitter core. The LED channel and the inner reveal
                                     faces carry U per profile point (hero_ceiling_lattice.PROFILE), so the light falls
                                     off smoothly over the recessed rail faces.

Both are emissive pictures (hero_ceiling_lattice: emit_image, unlit): emission = linear(BC) x the material's emit
strength. The key colours are EMISSION values chosen so the review render (AgX, Medium High Contrast look, as
preview_hero.py / below.py) shows the sheet's tones: they were inverted through a measured AgX table (emission-only
patches rendered and read back), e.g. the cell core (2.51, 1.34, 0) linear -> #F2D199 on screen, the sheet's ~#F2D49A.
AgX keeps blue from saturating at these levels, so the bright keys carry no blue.

Original and procedural (geometry of the module's own lattice, no photo, scan or third-party source). Uses
make_armory_textures' writers (same PNG / DirectX-normal conventions). Never overwrites another set.

Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_ceiling_lattice.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_armory_textures as MT  # noqa: E402
import hero_ceiling_lattice as L  # noqa: E402

GLOW, SLOT = "HLatticeGlow", "HLatticeSlot"

# (tone v, linear emission RGB): v 0 the deep soft shadow at a bar .. 1 the pale cream-gold on the lit side of a cell.
# On screen (AgX MHC, emission only): 0 #774217, 0.3 #A96B2E, 0.55 #D0904A, 0.75 #EAB26D, 0.9 #F2CA84, 1 #F9DCA4
# (the studio's specular sheen greys the render a little: the lit side lands ~#F2D49A, the sheet's cream-gold)
GLOW_KEYS = [(0.00, (0.200, 0.080, 0.029)), (0.30, (0.450, 0.170, 0.040)), (0.55, (0.850, 0.310, 0.030)),
             (0.75, (1.650, 0.700, 0.000)), (0.90, (2.600, 1.250, 0.000)), (1.00, (3.600, 1.900, 0.000))]
# (u, linear emission RGB) for the LED ramp. On screen: 0 #20120C (the dark timber), 0.2 #4B2B14, 0.4 #884E1E,
# 0.6 #C58339, 0.8 #E2AF5D, 1 #FAE3B0 (the sheet's pale-gold core of the strip, ~#FDEAAE)
SLOT_KEYS = [(0.0, (0.030, 0.016, 0.011)), (0.2, (0.094, 0.043, 0.020)), (0.4, (0.250, 0.105, 0.038)),
             (0.6, (0.640, 0.250, 0.035)), (0.8, (1.250, 0.580, 0.000)), (1.0, (4.000, 2.300, 0.000))]


def ramp(keys, t):
    """Piecewise-linear in linear emission (smooth on screen, AgX is monotonic) -> (..., 3)."""
    xs = [k for k, _ in keys]
    return np.stack([np.interp(t, xs, [c[i] for _, c in keys]) for i in range(3)], axis=-1)


def to_bc(lin, strength):
    """Linear emission -> the sRGB BC map for a material of that emit strength."""
    x = np.clip(lin / strength, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def emit_of(mat):
    return L.MATERIALS[mat][2]["emit"]


def glow(n=2048, seed=611):
    e0, e1 = L.GLOW_E, 2.0 - L.GLOW_E
    span = e1 - e0
    u = (np.arange(n) + 0.5) / n
    X = e0 + u[None, :] * span + np.zeros((n, 1))
    Y = e0 + (1.0 - u)[:, None] * span + np.zeros((1, n))      # rows run top-down: v = 1 at the top row
    tone = np.full((n, n), 0.30)                                # under the bars (hidden inside them)
    o0, o1 = L.POCKET, 2.0 - L.POCKET
    hw = L.STRIP_W / 2
    sl = math.hypot(*L.SHADOW)
    S = (L.SHADOW[0] / sl, L.SHADOW[1] / sl)
    count = 0
    for poly in L.cells(o0, o1):
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        i0 = max(int((min(xs) - e0) / span * n) - 1, 0)
        i1 = min(int((max(xs) - e0) / span * n) + 2, n)
        r0 = max(int((1 - (max(ys) - e0) / span) * n) - 1, 0)
        r1 = min(int((1 - (min(ys) - e0) / span) * n) + 2, n)
        if i1 <= i0 or r1 <= r0:
            continue
        px, py = X[r0:r1, i0:i1], Y[r0:r1, i0:i1]
        inside = np.ones(px.shape, bool)
        dmin = np.full(px.shape, 9.0)       # to the nearest bar edge
        dsh = np.full(px.shape, 9.0)        # to the nearest shadow-side bar (its shadow falls into this cell)
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        for q in range(len(poly)):
            a, b = poly[q], poly[(q + 1) % len(poly)]
            nx, ny = -(b[1] - a[1]), b[0] - a[0]
            ln = math.hypot(nx, ny)
            if ln < 1e-9:
                continue
            nx, ny = nx / ln, ny / ln
            if nx * (cx - a[0]) + ny * (cy - a[1]) < 0:
                nx, ny = -nx, -ny
            d = nx * (px - a[0]) + ny * (py - a[1])
            inside &= d >= 0
            on_rect = (abs(a[0] - b[0]) < 1e-6 and min(abs(a[0] - o0), abs(a[0] - o1)) < 1e-6) or \
                      (abs(a[1] - b[1]) < 1e-6 and min(abs(a[1] - o0), abs(a[1] - o1)) < 1e-6)
            d = d - (0.0 if on_rect else hw)                    # from the bar's visible edge (the rail face: 0)
            dmin = np.minimum(dmin, d)
            facing = nx * S[0] + ny * S[1]                      # > 0: this bar's shadow falls into the cell
            if facing > 0.25:
                dsh = np.minimum(dsh, d / min(1.0, facing + 0.25))
        m = inside & (dmin > 0)
        if not m.any():
            continue
        # lit side -> shadow side across the cell: the position against SHADOW, normalised over the visible cell
        s = -(px * S[0] + py * S[1])
        smin, smax = s[m].min(), s[m].max()
        g = np.clip((s - smin) / max(smax - smin, 1e-4), 0, 1)
        v = 0.10 + 0.90 * np.power(g, 0.60)                     # pale on the lit side, amber toward the shadow side
        v *= 1.0 - 0.10 * np.exp(-np.clip(dmin, 0, None) / 0.008)   # a little warmer along every bar
        v *= 1.0 - 0.55 * np.exp(-np.clip(dsh, 0, None) / 0.0055)   # the bar's soft shadow on its shadow side
        tone[r0:r1, i0:i1] = np.where(m, v, tone[r0:r1, i0:i1])
        count += 1
    # a faint, very soft paper cloud (+-2 %), so the panel is not CG-flat
    cloud = MT.pnoise(n, n, 2.2, seed)
    tone = np.clip(tone * (1.0 + 0.02 * cloud), 0, 1)
    lin = ramp(GLOW_KEYS, tone)
    strength = emit_of(L.GLOW)
    assert lin.max() <= strength * 1.001, (lin.max(), strength)
    bc = to_bc(lin, strength)
    info = MT.save_set(GLOW, bc, np.zeros((n, n)), 0.0, np.full((n, n), 0.9))
    info["cells"] = count
    return info


def slot(w=256, h=8):
    u = (np.arange(w) + 0.5) / w
    lin = np.repeat(ramp(SLOT_KEYS, u)[None, :, :], h, axis=0)
    strength = emit_of(L.SL)
    assert lin.max() <= strength * 1.001, (lin.max(), strength)
    return MT.save_set(SLOT, to_bc(lin, strength), np.zeros((h, w)), 0.0, np.full((h, w), 0.9))


if __name__ == "__main__":
    for nm in (GLOW, SLOT):
        assert nm.startswith("HLattice")
    print(json.dumps([glow(), slot()], indent=2))
