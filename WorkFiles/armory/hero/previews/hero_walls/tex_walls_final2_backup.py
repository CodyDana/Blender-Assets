"""The lit washi back panel of the hero wall niche (hero_walls: SM_AK_WallPanel_Lit / _190): T_AK_HNicheWashi_BC / _ORM / _N.

wall_alcove.png's back panel is pale cream washi with visible kozo fibres and a soft warm glow falling off from hidden
LEDs: a hot line down both back corners and under the head, the paper brightest next to them and falling off toward
the middle (a few cm), a gentle lift toward the ledge, faint cloudy mottling. The panel carries a unique 0-1 UV over
PANEL_W x PANEL_H metres (hero_walls.wall_panel: the paper face behind the reveal), so everything here is laid out in
metres and the fibres are not stretched.

M_AK_HNicheWashi uses the BC as an unlit emissive picture (emit_image + unlit, like M_AK_LanternPaper): the light is painted
in, the room light does not wash it. ORM: occlusion 1, roughness 0.9, metal 0; N: the fibres as a faint relief.

Writes only NEW files (never overwrites another set's textures).
Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/armory/hero/tex_walls.py
"""
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TEX = ROOT / "Exports" / "ArmoryKit" / "Textures"
OUT = {k: TEX / f"T_AK_HNicheWashi_{k}.png" for k in ("BC", "ORM", "N")}
W_PX, H_PX = 512, 2048
PANEL_W, PANEL_H = 0.426, 1.46     # hero_walls: the paper face (x 0.212-0.638, ledge top - 1 cm to the head underside)
REVEAL = 0.004                     # paper hidden under the reveal each side (x 0.212 -> 0.216)
V_TOP = 0.951                      # the visible top of the opening (the head fascia's underside) in V
# sRGB looks, measured on wall_alcove.png's front elevation (x 300-490, y 45-335)
# (the render's AgX view desaturates and darkens a little: these are set so the preview measures like the sheet:
# upper middle ~(204,140,70), middle ~(212,168,121), over the ledge ~(238,189,132), next to the LEDs ~(252,234,172))
C_TOP = np.array([0.88, 0.54, 0.15])     # the upper middle, furthest from the lift at the ledge
C_MID = np.array([0.91, 0.67, 0.33])     # the paper in the middle of the bay
C_BOT = np.array([1.00, 0.71, 0.30])     # over the ledge (the lift)
C_EDGE = np.array([1.00, 0.90, 0.56])    # next to the hidden LED lines
# the LED glow is brighter than the paper can store at the paper's own level: the picture is stored at 1 / K of the
# radiance (hero_walls: M_AK_HNicheWashi emit = EMIT_AT_K), so the lines next to the LEDs can run GAIN x the paper
K, GAIN_EDGE, GAIN_BOT = 1.7, 1.9, 1.15
SEED = 20260928


def blur(a, sigma_px_x, sigma_px_y):
    """Separable-free Gaussian blur through the FFT (wraps; the panel's edges are under the reveal anyway)."""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * np.pi ** 2 * ((fx * sigma_px_x) ** 2 + (fy * sigma_px_y) ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def fibres(rng, n, len_m, width_px, amp):
    """Long thin wandering kozo fibres, splatted bilinearly in metre space, then softened."""
    acc = np.zeros((H_PX, W_PX), np.float64)
    sx, sy = W_PX / PANEL_W, H_PX / PANEL_H
    for _ in range(n):
        x, y = rng.uniform(0, PANEL_W), rng.uniform(0, PANEL_H)
        ang = rng.uniform(0, np.pi)
        L = len_m * rng.uniform(0.4, 1.6)
        steps = max(8, int(L / 0.0004))
        turn = rng.normal(0, 0.035, steps).cumsum()
        a = ang + turn
        px = x + np.cumsum(np.cos(a)) * (L / steps)
        py = y + np.cumsum(np.sin(a)) * (L / steps)
        u, v = px * sx, py * sy
        ok = (u >= 0) & (u < W_PX - 1) & (v >= 0) & (v < H_PX - 1)
        u, v = u[ok], v[ok]
        if not len(u):
            continue
        i, j = v.astype(int), u.astype(int)
        fu, fv = u - j, v - i
        s = rng.choice((-1.0, 1.0), p=(0.35, 0.65)) * rng.uniform(0.5, 1.0)
        for di, dj, wgt in ((0, 0, (1 - fu) * (1 - fv)), (0, 1, fu * (1 - fv)), (1, 0, (1 - fu) * fv), (1, 1, fu * fv)):
            np.add.at(acc, (i + di, j + dj), s * wgt)
    acc = blur(acc, width_px, width_px * sy / sx)
    return amp * acc / (np.abs(acc).max() + 1e-9)


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def save(path, arr, noncolor=False):
    assert not path.exists() or path.name.startswith("T_AK_HNicheWashi_"), path   # only this set is ever (re)written
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr, 0, 1)
    im = bpy.data.images.new(path.stem, w, h, alpha=False)
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(rgba[::-1].ravel())
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def main():
    rng = np.random.default_rng(SEED)
    # metre coordinates of every texel (row 0 = the top of the panel, V = 1)
    x = (np.arange(W_PX) + 0.5) / W_PX * PANEL_W
    v = 1.0 - (np.arange(H_PX) + 0.5) / H_PX
    X, V = np.meshgrid(x, v)
    Z = V * PANEL_H
    z_top = V_TOP * PANEL_H
    # distance from the hidden LED lines: the back corners (just inside the reveal) and the head fascia's underside
    d_side = np.minimum(X - REVEAL, PANEL_W - REVEAL - X).clip(0, None)
    d_top = (z_top - Z).clip(0, None)
    edge = 0.55 * np.exp(-d_side / 0.012) + 0.45 * np.exp(-d_side / 0.045)
    top = 0.80 * np.exp(-d_top / 0.015) + 0.20 * np.exp(-d_top / 0.070)
    bot = 0.45 * np.exp(-Z / 0.05)                          # a hidden LED at the back of the ledge washes up
    glow = np.clip(np.maximum(np.maximum(edge, top), bot) + 0.35 * np.minimum(edge, np.maximum(top, bot)), 0, 1)
    lift = np.clip(1.0 - Z / z_top, 0, 1)[..., None]       # 1 at the ledge, 0 under the head
    lo, mi, hi = (srgb_to_lin(c)[None, None, :] for c in (C_TOP, C_MID, C_BOT))
    t1, t2 = np.clip(lift * 2, 0, 1) ** 1.2, np.clip(lift * 2 - 1, 0, 1) ** 1.4
    base = np.where(lift < 0.5, lo * (1 - t1) + mi * t1, mi * (1 - t2) + hi * GAIN_BOT * t2)
    col = base * (1 - glow[..., None]) + srgb_to_lin(C_EDGE)[None, None, :] * GAIN_EDGE * glow[..., None]
    # paper: cloudy mottling (formation), long kozo fibres, a fine grain
    cloud = np.zeros_like(X)
    for sig, amp in ((60, 0.03), (22, 0.04), (7, 0.03)):
        n = blur(rng.normal(0, 1, X.shape), sig, sig * (H_PX / PANEL_H) / (W_PX / PANEL_W))
        cloud += amp * n / (n.std() + 1e-9)
    fib = (fibres(rng, 1400, 0.045, 0.7, 0.14) + fibres(rng, 420, 0.10, 1.6, 0.24)
           + fibres(rng, 110, 0.16, 2.4, 0.20))   # fine net, visible strands, a few long kozo strands
    grain = 0.015 * rng.normal(0, 1, X.shape)
    m = np.exp(cloud + fib + grain)
    fibre_tint = np.where(fib[..., None] > 0, np.array([1.0, 0.99, 0.96]), np.array([0.97, 0.93, 0.86]))
    lin = col * m[..., None] * fibre_tint / K
    bc = lin_to_srgb(lin)
    save(OUT["BC"], bc)
    orm = np.zeros(X.shape + (3,))
    orm[..., 0], orm[..., 1], orm[..., 2] = 1.0, 0.9, 0.0
    save(OUT["ORM"], orm, noncolor=True)
    # normal: the fibre field as a faint height (DirectX green, like the kit's other maps)
    hgt = blur(fib + 0.4 * cloud, 1.0, 1.0)
    gy, gx = np.gradient(hgt)
    k = 1.2
    nx, ny = -gx * k, gy * k            # DirectX: green flipped relative to OpenGL
    nz = np.ones_like(nx)
    ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    nrm = np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5
    save(OUT["N"], nrm, noncolor=True)
    c = bc[H_PX // 2, W_PX // 2]
    print("WASHI written", {k: str(p) for k, p in OUT.items()}, "mid sRGB", [round(float(t) * 255) for t in c],
          "edge sRGB", [round(float(t) * 255) for t in bc[H_PX // 2, 3]])


main()
