"""The ceiling lattice hero's own glow pictures (hero_ceiling_lattice, reference sheet ceiling_lattice.png):

  T_AK_HLatticeGlow_BC / _ORM / _N   the backlit panel behind the asanoha kumiko, ONE picture over the glow quad
                                     (unique 0-1 UV, d GLOW_E .. 2 - GLOW_E of the 2 x 2 m cell, 2048 px, 0.76 mm/px),
                                     painted cell by cell in register with the bars from hero_ceiling_lattice.cells():
                                     final 4, lit paper: a golden body (tone BASE) rising to a pale cream middle
                                     (PEAK), an amber rim along every bar (RIM), the bars' soft shadow band on the
                                     SHADOW side (SH_W); final 3's whole-cell lit-to-shadow falloff read pillowed.
  T_AK_HLatticeSlot_BC / _ORM / _N   a 1-D glow ramp (256 x 8 px): U = how strongly the hidden LED lights a surface,
                                     0 dark timber .. 1 the pale-gold emitter core. The LED channel and the inner reveal
                                     faces carry U per profile point (hero_ceiling_lattice.PROFILE), so the light falls
                                     off smoothly over the recessed rail faces.
  T_AK_HLatticeTimber_BC / _ORM / _N the lattice's own timber (final 4): the shared T_AK_HTimber (tex_shared.py, read
                                     back, not changed) with its grain contrast cut to ~40 %, its orange pulled toward
                                     the espresso body, half the normal relief, a more even roughness: the sheet's fine,
                                     subtle grain (the shared set's streaks read noisy orange scratches on this piece).
                                     Run after tex_shared.py.
  T_AK_HLatticeBoss_BC / _ORM / _N   the rosette on the star bosses (final 4, 256 px, planar over the boss disc): a
                                     raised bronze ring, a dark groove, an eight-petal disc and a centre knob.

The glow and the slot sets are emissive pictures (hero_ceiling_lattice: emit_image, unlit): emission = linear(BC) x the material's emit
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

GLOW, SLOT, TIMBER, BOSS = "HLatticeGlow", "HLatticeSlot", "HLatticeTimber", "HLatticeBoss"

# (tone v, linear emission RGB): v 0 the deep soft shadow at a bar .. 1 the pale cream-gold on the lit side of a cell.
# On screen (AgX MHC, emission only): 0 #774217, 0.3 #A96B2E, 0.55 #D0904A, 0.75 #EAB26D, 0.9 #F2CA84, 1 #F9DCA4
# (the studio's specular sheen greys the render a little: the lit side lands ~#F2D49A, the sheet's cream-gold)
GLOW_KEYS = [(0.00, (0.200, 0.080, 0.029)), (0.30, (0.450, 0.170, 0.045)), (0.55, (0.850, 0.320, 0.040)),
             (0.75, (1.820, 0.780, 0.000)), (0.90, (2.650, 1.250, 0.000)), (1.00, (3.450, 1.800, 0.000))]
# final 4: the cell's rim (m) and depth, the bar-shadow band (m) and depth (see glow())
RIM, RIM_D, SH_W, SH_D = 0.014, 0.40, 0.0075, 0.40
CORE, BASE, PEAK = (0.010, 0.026), 0.77, 0.96   # a cell: its golden body (tone BASE) rising to the pale cream middle
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
        # final 4 (blind judge: the cells read orange-tan and softly pillowed; the sheet's are lit paper, a pale cream-
        # yellow middle falling off to amber at the edges): a broad flat pale core, a narrow amber rim along every bar
        # (the corners, where two rims meet, go amber), the soft shadow band of the bars on the cell's SHADOW side and
        # only a faint drift across the cell
        s = px * S[0] + py * S[1]
        smin, smax = s[m].min(), s[m].max()
        g = np.clip((s - smin) / max(smax - smin, 1e-4), 0, 1)   # 0 at the shadow-casting bar .. 1 across the cell
        dm = np.clip(dmin, 0, None)
        e = np.clip(dm / RIM, 0, 1)
        rim = 1.0 - e * e * (3 - 2 * e)                          # smoothstep: 1 at the bar, 0 past RIM
        e = np.clip((dm - CORE[0]) / (CORE[1] - CORE[0]), 0, 1)
        core = e * e * (3 - 2 * e)                               # 0 near the bars, 1 in the cell's deep middle
        sh = np.exp(-np.clip(dsh, 0, None) / SH_W)
        v = BASE + (PEAK - BASE) * core - RIM_D * rim - SH_D * sh * (1 - 0.5 * rim) - 0.06 * g
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


def read_png(path):
    """8-bit RGB / RGBA PNG reader for make_armory_textures.write_png's own files (filter 0 on every row) -> 0..1."""
    import struct
    import zlib
    d = Path(path).read_bytes()
    p, idat, hdr = 8, b"", None
    while p < len(d):
        ln, = struct.unpack(">I", d[p:p + 4])
        tag = d[p + 4:p + 8]
        if tag == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", d[p + 8:p + 21])
        elif tag == b"IDAT":
            idat += d[p + 8:p + 8 + ln]
        p += 12 + ln
    w, h, depth, ctype = hdr[0], hdr[1], hdr[2], hdr[3]
    assert depth == 8 and ctype in (2, 6), hdr
    ch = 3 if ctype == 2 else 4
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, 1 + w * ch)
    assert not raw[:, 0].any(), "only filter-0 rows (write_png's) are supported"
    return raw[:, 1:].reshape(h, w, ch)[..., :3].astype(np.float64) / 255.0


def timber():
    """Final 4 (blind judge: the shared timber's orange scratch streaks read noisy and high-contrast on this piece; the
    sheet's is a dark espresso with a fine, subtle grain): T_AK_HLatticeTimber is T_AK_HTimber (same espresso body,
    same grain layout and 2 m tile, so it sits with the room's beams) with the grain's contrast cut to ~40 % and its
    orange pulled toward the body's brown, the normal relief halved; roughness a touch more even."""
    src = MT.OUT
    bc = read_png(src / "T_AK_HTimber_BC.png")
    orm = read_png(src / "T_AK_HTimber_ORM.png")
    nrm = read_png(src / "T_AK_HTimber_N.png")
    lin = np.where(bc <= 0.04045, bc / 12.92, np.power((bc + 0.055) / 1.055, 2.4))
    body = np.median(lin.reshape(-1, 3), axis=0)
    dev = lin - body
    lum = dev @ np.array([0.2126, 0.7152, 0.0722])
    dev = 0.55 * dev + 0.45 * lum[..., None] * (body / max(body.mean(), 1e-6))   # less orange, more body-hued
    lin2 = np.clip(body + 0.40 * dev, 0, 1)
    bc2 = np.where(lin2 <= 0.0031308, lin2 * 12.92, 1.055 * np.power(lin2, 1 / 2.4) - 0.055)
    xy = (nrm[..., :2] - 0.5) * 2 * 0.5
    z = np.sqrt(np.clip(1 - (xy ** 2).sum(-1), 0, 1))
    n2 = np.dstack([xy * 0.5 + 0.5, z * 0.5 + 0.5])
    rough = orm[..., 1]
    rough2 = rough.mean() + 0.6 * (rough - rough.mean())
    info = MT.save_set(TIMBER, bc2, np.zeros(rough.shape), 0.0, rough2, orm[..., 0])
    MT.write_png(MT.OUT / f"T_AK_{TIMBER}_N.png", n2)
    return info


def boss(n=256):
    """Final 4 (blind judge: plain domes; the sheet's bosses are small bronze rosettes with a ring): the boss's underside
    picture, planar-mapped over its disc (UV 0.5 at the centre, the rim at 0.49): a raised bronze outer ring, a dark
    groove, an eight-petal disc and a small bright centre knob; outside the disc the plain dark bronze of the drum."""
    c = (np.arange(n) + 0.5) / n - 0.5
    X, Y = np.meshgrid(c, -c)
    rho = np.hypot(X, Y) / 0.49
    th = np.arctan2(Y, X)

    def band(a, b, soft=0.03):
        return np.clip((rho - a) / soft + 0.5, 0, 1) * np.clip((b - rho) / soft + 0.5, 0, 1)
    ring = band(0.72, 0.97)
    groove = band(0.64, 0.72, 0.02)
    petal = band(0.20, 0.64) * np.clip(0.5 + 0.5 * np.cos(8 * th) * (1 - 0.4 * rho), 0, 1)
    knob = np.clip((0.20 - rho) / 0.05 + 0.5, 0, 1)
    ringr = np.sin(np.clip((rho - 0.72) / 0.25, 0, 1) * np.pi)            # the ring's rounded section
    height = 0.55 * ring * ringr + 0.25 * petal + 0.6 * knob * np.sqrt(np.clip(1 - (rho / 0.2) ** 2, 0, 1))
    height -= 0.15 * groove
    dark, mid, hi = MT.srgb("#241810"), MT.srgb("#4A301C"), MT.srgb("#8A5E36")
    t = np.clip(0.85 * ring * ringr + 0.35 * petal + 0.9 * knob, 0, 1)[..., None]
    bc = dark * (1 - t) + np.where(t > 0.5, hi, mid) * t
    bc *= (1 - 0.5 * groove)[..., None]
    bc = np.where((rho > 1.0)[..., None], dark, bc)
    rough = np.clip(0.52 - 0.14 * ring * ringr - 0.1 * knob + 0.1 * groove, 0.3, 0.8)
    rep = MT.save_set(BOSS, bc, height, 4.0, rough, 1 - 0.35 * groove)
    MT.write_png(MT.OUT / f"T_AK_{BOSS}_ORM.png", np.dstack([1 - 0.35 * groove, rough, np.full_like(rough, 0.75)]))
    return rep


def slot(w=256, h=8):
    u = (np.arange(w) + 0.5) / w
    lin = np.repeat(ramp(SLOT_KEYS, u)[None, :, :], h, axis=0)
    strength = emit_of(L.SL)
    assert lin.max() <= strength * 1.001, (lin.max(), strength)
    return MT.save_set(SLOT, to_bc(lin, strength), np.zeros((h, w)), 0.0, np.full((h, w), 0.9))


if __name__ == "__main__":
    for nm in (GLOW, SLOT, TIMBER, BOSS):
        assert nm.startswith("HLattice")
    print(json.dumps([glow(), slot(), timber(), boss()], indent=2))
