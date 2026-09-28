"""Texture sets of the hero wall pieces (hero_walls): the lit washi back panel of the niche (T_AK_HNicheWashi) and the
dark oak of the niche, window casing and sill bearer (T_AK_HWallOak).

T_AK_HNicheWashi_BC / _ORM / _N  (SM_AK_WallPanel_Lit / _190)
  wall_alcove.png's back panel is pale cream washi with visible kozo fibres, lit evenly, with crisp bright LED lines
  down both inner sides and across the top: the paper is brightest right next to the lines (a few cm), a gentle lift
  toward the ledge, faint mottling (no clouds). The panel carries a unique 0-1 UV over PANEL_W x PANEL_H metres
  (hero_walls.wall_panel: the paper face behind the reveal; both niche heights use the same 55 x 110 cm opening, so one
  picture serves both), so everything here is laid out in metres and the fibres are not stretched.
  M_AK_HNicheWashi uses the BC as an unlit emissive picture (emit_image + unlit, like M_AK_LanternPaper): the light is
  painted in, the room light does not wash it. ORM: occlusion 1, roughness 0.9, metal 0; N: the fibres as a faint relief.

T_AK_HWallOak_BC / _ORM / _N  (M_AK_HWallOak, 1 m tile)
  wall_alcove.png / window.png timber: a dark espresso-stained oak with a SUBTLE straight grain (fine low-contrast
  latewood lines, pore streaks along the grain, a slight tone change from board to board), satin oil finish. Grain
  runs along U and tiles in U. V 0.00-0.86 is long grain (hero_walls maps each member's across-grain extent inside it);
  V 0.875-1.00 is an END-GRAIN band (gentle growth-ring arcs and fine checks), where hero_walls maps the end faces of
  posts and beams (window.png's top view shows the posts' end grain).

Writes only its own sets (never overwrites another set's textures).
Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/armory/hero/tex_walls.py
"""
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TEX = ROOT / "Exports" / "ArmoryKit" / "Textures"
OWN = ("T_AK_HNicheWashi_", "T_AK_HWallOak_")

# ------------------------------------------------------------------ washi
WASHI = {k: TEX / f"T_AK_HNicheWashi_{k}.png" for k in ("BC", "ORM", "N")}
W_PX, H_PX = 1024, 2048      # power of two (QA)
OPEN_W, OPEN_H = 0.55, 1.10       # hero_walls: the lit opening (x RV..W-RV, ledge top .. ledge top + OPEN_H)
REVEAL = 0.0045                   # paper hidden under the reveal each side
BELOW, ABOVE = 0.010, 0.030       # paper below the ledge top / above the visible top of the opening (behind the head)
PANEL_W, PANEL_H = OPEN_W + 2 * REVEAL, OPEN_H + BELOW + ABOVE
V_TOP = (BELOW + OPEN_H) / PANEL_H   # the visible top of the opening in V
# sRGB paper tones (the render's AgX view desaturates a little: set so the preview measures like wall_alcove.png's
# pale cream: middle ~(220,185,140), toward the head ~(212,172,126), over the ledge ~(238,196,146), at the LEDs ~(252,236,185))
C_TOP = np.array([0.93, 0.67, 0.34])
C_MID = np.array([0.96, 0.73, 0.39])
C_BOT = np.array([1.00, 0.77, 0.41])
C_EDGE = np.array([1.00, 0.88, 0.56])
K, GAIN_EDGE, GAIN_BOT = 1.7, 2.1, 1.10
SEED = 20260928


def blur(a, sigma_px_x, sigma_px_y):
    """Gaussian blur through the FFT (wraps: seamless where the field must tile)."""
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
        s = rng.choice((-1.0, 1.0), p=(0.55, 0.45)) * rng.uniform(0.5, 1.0)
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
    assert path.name.startswith(OWN), path   # only this module's own sets are ever (re)written
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


def normal_from_height(hgt, k):
    """DirectX-green normal map (like the kit's other maps) from a height field (texel units)."""
    gy, gx = np.gradient(hgt)
    nx, ny = -gx * k, gy * k            # DirectX: green flipped relative to OpenGL
    nz = np.ones_like(nx)
    ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5


def washi():
    rng = np.random.default_rng(SEED)
    x = (np.arange(W_PX) + 0.5) / W_PX * PANEL_W
    v = 1.0 - (np.arange(H_PX) + 0.5) / H_PX          # row 0 = the top of the panel, V = 1
    X, V = np.meshgrid(x, v)
    Z = V * PANEL_H
    z_top = V_TOP * PANEL_H
    # distance from the LED lines: the back corners (just inside the reveal) and the head's underside
    d_side = np.minimum(X - REVEAL, PANEL_W - REVEAL - X).clip(0, None)
    d_top = (z_top - Z).clip(0, None)
    edge = 0.50 * np.exp(-d_side / 0.015) + 0.50 * np.exp(-d_side / 0.060)
    top = 0.75 * np.exp(-d_top / 0.012) + 0.25 * np.exp(-d_top / 0.060)
    bot = 0.35 * np.exp(-(Z - BELOW).clip(0, None) / 0.06)      # the ledge's hidden LED washes up a little
    glow = np.clip(np.maximum(np.maximum(edge, top), bot) + 0.30 * np.minimum(edge, np.maximum(top, bot)), 0, 1)
    lift = np.clip(1.0 - Z / z_top, 0, 1)[..., None]            # 1 at the ledge, 0 under the head
    lo, mi, hi = (srgb_to_lin(c)[None, None, :] for c in (C_TOP, C_MID, C_BOT))
    t1, t2 = np.clip(lift * 2, 0, 1) ** 1.2, np.clip(lift * 2 - 1, 0, 1) ** 1.4
    base = np.where(lift < 0.5, lo * (1 - t1) + mi * t1, mi * (1 - t2) + hi * GAIN_BOT * t2)
    col = base * (1 - glow[..., None]) + srgb_to_lin(C_EDGE)[None, None, :] * GAIN_EDGE * glow[..., None]
    # paper: faint formation (no clouds), long kozo fibres, a fine grain
    cloud = np.zeros_like(X)
    for sig, amp in ((40, 0.012), (14, 0.020), (5, 0.022)):
        n = blur(rng.normal(0, 1, X.shape), sig, sig * (H_PX / PANEL_H) / (W_PX / PANEL_W))
        cloud += amp * n / (n.std() + 1e-9)
    fib = (fibres(rng, 2400, 0.045, 0.8, 0.16) + fibres(rng, 700, 0.10, 1.6, 0.26)
           + fibres(rng, 160, 0.16, 2.2, 0.16))   # fine net, visible strands, a few long kozo strands
    grain = 0.012 * rng.normal(0, 1, X.shape)
    m = np.exp(cloud + fib + grain)
    fibre_tint = np.where(fib[..., None] > 0, np.array([1.0, 0.99, 0.97]), np.array([0.97, 0.94, 0.89]))
    lin = col * m[..., None] * fibre_tint / K
    bc = lin_to_srgb(lin)
    save(WASHI["BC"], bc)
    orm = np.zeros(X.shape + (3,))
    orm[..., 0], orm[..., 1], orm[..., 2] = 1.0, 0.9, 0.0
    save(WASHI["ORM"], orm, noncolor=True)
    save(WASHI["N"], normal_from_height(blur(fib + 0.4 * cloud, 1.0, 1.0), 1.2), noncolor=True)
    c = bc[H_PX // 2, W_PX // 2]
    print("WASHI written", PANEL_W, PANEL_H, round(V_TOP, 4), "mid sRGB", [round(float(t) * 255) for t in c])


# ------------------------------------------------------------------ dark oak
OAK = {k: TEX / f"T_AK_HWallOak_{k}.png" for k in ("BC", "ORM", "N")}
N_OAK = 2048                      # 1 m tile: ~0.5 mm per texel
END_V0 = 0.875                    # V 0.875-1.0: the end-grain band
# sRGB (the render darkens a little: set so the preview measures like wall_alcove.png's stiles ~(47,36,29))
O_BASE = np.array([0.118, 0.071, 0.042])
O_LATE = np.array([0.050, 0.031, 0.020])
O_LIGHT = np.array([0.215, 0.135, 0.080])


def oak():
    rng = np.random.default_rng(SEED + 7)
    n = N_OAK
    u = (np.arange(n) + 0.5) / n                     # metres along the grain (1 m tile)
    vv = 1.0 - (np.arange(n) + 0.5) / n              # row 0 = V 1
    U, VV = np.meshgrid(u, vv)
    # ---- long grain: straight latewood lines 2-7 mm apart, a very slight periodic waver (tiles in U)
    wav = np.zeros_like(U)
    for k, a in ((1, 0.0012), (2, 0.0007), (3, 0.0004), (5, 0.00025)):
        wav += a * np.sin(2 * np.pi * (k * U + rng.uniform(0, 1))) * np.cos(2 * np.pi * (VV * rng.uniform(1.0, 3.0)))
    y = VV + wav
    edges = np.cumsum(rng.uniform(0.004, 0.013, 300))
    edges = edges[edges < 1.2]
    idx = np.searchsorted(edges, y.clip(0, 1.19))
    prev = np.where(idx > 0, edges[np.maximum(idx - 1, 0)], 0.0)
    nxt = edges[np.minimum(idx, len(edges) - 1)]
    t = ((y - prev) / np.maximum(nxt - prev, 1e-4)).clip(0, 1)      # 0..1 across one growth ring
    late = np.exp(-((1 - t) / 0.16) ** 2)                            # a soft dark latewood band at the ring's end
    ring_amp = rng.uniform(0.55, 1.0, len(edges) + 1)[idx]
    # the latewood line is broken along its length (pores), so it reads as a fine grain, not stripes
    brk = blur(rng.normal(0, 1, U.shape), 60, 1.2)
    brk = (brk / brk.std()).clip(-2, 2) * 0.25 + 0.75
    late = late * ring_amp * brk
    # pore streaks: fine, long, low contrast
    pores = blur(rng.normal(0, 1, U.shape), 24, 0.6)
    pores /= pores.std()
    # board-to-board tone (~10-16 cm bands across the grain) and a soft figure along the grain
    board = blur(rng.normal(0, 1, (n, 8)), 0.01, 70)[:, :1].repeat(n, 1)
    board /= board.std() + 1e-9
    figure = blur(rng.normal(0, 1, U.shape), 180, 40)
    figure /= figure.std()
    lin = (srgb_to_lin(O_BASE) * np.exp(0.06 * board + 0.05 * figure + 0.05 * pores)[..., None])
    lin = lin * (1 - 0.70 * late[..., None]) + srgb_to_lin(O_LATE) * 0.70 * late[..., None]
    lit = np.clip(0.9 * np.exp(-(t / 0.25) ** 2) * (pores > 0.45), 0, 1) * 0.60     # a few brighter earlywood flecks
    lin = lin * (1 - lit[..., None]) + srgb_to_lin(O_LIGHT) * lit[..., None]
    hgt = -1.2 * late + 0.05 * pores
    # ---- end grain band (V >= END_V0): growth-ring arcs around piths below the band, fine radial checks
    band = VV >= END_V0 - 0.004
    ex, ey = U, VV
    cx = np.floor(ex / 0.25) * 0.25 + 0.125 + 0.03 * np.sin(np.floor(ex / 0.25) * 2.1)
    cy = END_V0 - 0.18
    r = np.hypot(ex - cx, ey - cy)
    ang = np.arctan2(ey - cy, ex - cx)
    rwarp = blur(rng.normal(0, 1, U.shape), 40, 40)
    rwarp /= rwarp.std()
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * (r + 0.004 * rwarp) / 0.0045 + 0.4 * np.sin(ang * 7) + 2.0 * np.sqrt(r / 0.0045) * 0.15)
    ring = ring ** 3
    chk = blur(rng.normal(0, 1, U.shape), 0.6, 0.6)
    chk = (np.abs(np.sin(ang * 40 + 3 * chk)) < 0.02) * (rng.uniform(0, 1, U.shape) < 0.5)
    end_lin = srgb_to_lin(O_BASE * 0.92) * (1 - 0.35 * ring[..., None]) * (1 - 0.4 * chk[..., None])
    end_lin = end_lin * np.exp(0.04 * blur(rng.normal(0, 1, U.shape), 3, 3))[..., None]
    lin = np.where(band[..., None], end_lin, lin)
    hgt = np.where(band, -0.6 * ring - 1.5 * chk, hgt)
    bc = lin_to_srgb(lin)
    save(OAK["BC"], bc)
    orm = np.zeros(U.shape + (3,))
    orm[..., 0] = 1.0 - 0.25 * late.clip(0, 1)
    orm[..., 1] = (0.48 + 0.12 * late + 0.03 * pores).clip(0.35, 0.75)   # satin oil finish, the pores a little rougher
    orm[..., 2] = 0.0
    save(OAK["ORM"], orm, noncolor=True)
    save(OAK["N"], normal_from_height(blur(hgt, 1.2, 1.2), 0.35), noncolor=True)   # a soft relief: no grazing streaks
    print("OAK written mean sRGB", [round(float(t) * 255) for t in bc[: int(n * 0.8)].reshape(-1, 3).mean(0)])


washi()
oak()
