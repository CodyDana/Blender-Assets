"""Texture sets of the hero wall pieces (hero_walls): the lit washi back panels of the niche (T_AK_HNicheWashi for the
2.40 m niche, T_AK_HNicheWashi190 for the 1.90 m one) and the dark oak of the niche, window casing and sill bearer
(T_AK_HWallOak).

T_AK_HNicheWashi_BC / _ORM / _N, T_AK_HNicheWashi190_*  (SM_AK_WallPanel_Lit / _190)
  wall_alcove.png's back panel: warm cream washi with visible kozo fibres (no clouds), a crisp LED line down both
  inner sides and across the top with a GOLDEN glow on the paper next to them (sRGB ~(251,201,112) 1 cm in,
  ~(231,170,101) 3.5 cm in, the centre ~(207,162,115)), a golden band right under the top line, a dimmer zone under the
  head and the paper brightening down to the ledge (~(241,193,137)). The colours are the reference's own, measured and
  inverted through the preview's view transform (AgX Medium High Contrast) into scene-linear emission anchors, so the
  preview measures like the sheet. Each panel carries a unique 0-1 UV over its paper (hero_walls.wall_panel: the paper
  face behind the reveal, OPEN_W x the set's opening height), so everything is laid out in metres.
  M_AK_HNicheWashi(190) use the BC as an unlit emissive picture (emit_image + unlit, emit = E_WASHI): the light is
  painted in, the room light does not wash it. ORM: occlusion 1, roughness 0.9, metal 0; N: the fibres as a faint relief.

T_AK_HWallOak_BC / _ORM / _N  (M_AK_HWallOak, 1 m tile)
  wall_alcove.png / window.png timber: a dark espresso-stained oak with a SUBTLE straight grain (fine low-contrast
  latewood lines, pore streaks along the grain, a slight tone change from board to board), satin oil finish. Grain
  runs along U and tiles in U. V 0.00-0.86 is long grain (hero_walls maps each member's across-grain extent inside it);
  V 0.875-1.00 is an END-GRAIN band (gentle growth-ring arcs and fine checks), where hero_walls maps the end faces of
  posts and beams (window.png's top view shows the posts' end grain).

T_AK_HNicheWashiRoom_* / T_AK_HNicheWashiRoom190_*  (calibration pass 2, 2026-09-28: the sets the niches wear IN THE ROOM)
  the same paper (seed, fibres, relief) as a plain beige albedo (ROOM_PAPER), lit by the niche's downlight, so the back
  reads warm beige, hot under the lens and falling off toward the ledge, as reference 2's niches (washi_room()).

T_AK_HBayBoard_BC / _ORM / _N  (r16 walls round, 2026-09-29: M_AK_HBayBoard, the wall bays' DARK backboard)
  armory3_reference2.png's side-wall displays: a matte dark warm taupe hemp cloth board, 1 m tile (bay_board()).

Writes only its own sets (never overwrites another set's textures). -- --out DIR writes into DIR (a test copy's
<preview dir>/Textures); -- --board writes only T_AK_HBayBoard; -- --winpaper only T_AK_HWinPaper (r21, the backlit
upper-window paper, win_paper()).
Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/armory/hero/tex_walls.py
  (-- --room: only the pass-2 room sets)
"""
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TEX = ROOT / "Exports" / "ArmoryKit" / "Textures"
OWN = ("T_AK_HNicheWashi_", "T_AK_HNicheWashi190_", "T_AK_HWallOak_")

# ------------------------------------------------------------------ washi
W_PX, H_PX = 1024, 2048           # power of two (QA)
OPEN_W = 0.50                     # hero_walls: the lit opening width (x RV..W-RV), both niche heights
WASHI_SETS = {"HNicheWashi": 1.26, "HNicheWashi190": 1.00}   # set -> the lit opening height (hero_walls OPEN_H)
REVEAL = 0.0045                   # paper hidden under the reveal each side
LED_IN = 0.017                    # the gold return strip + LED line inside the reveal edge: the paper shows from here
BELOW, ABOVE = 0.010, 0.030       # paper below the ledge top / above the visible top of the opening (behind the head)
E_WASHI = 5.0                     # = hero_walls MATERIALS emit of the washi: BC (linear) x E = the scene-linear emission
# Anchors in scene-linear emission, inverted from wall_alcove.png's measured sRGB through the preview's view transform
# (AgX, Medium High Contrast; the reference's opening is ~200 px = 46 cm, 2.3 mm / px).
# Across (at 56 % of the height): distance (m) in from the LED line's inner edge -> colour
SIDE_D = (0.000, 0.011, 0.023, 0.035, 0.058, 0.081, 0.115, 0.150, 0.196)
SIDE_C = ((4.22, 1.91, 0.0), (3.07, 1.07, 0.0), (2.09, 0.68, 0.0), (1.385, 0.524, 0.022), (0.95, 0.407, 0.083),
          (0.76, 0.359, 0.110), (0.825, 0.408, 0.127), (0.914, 0.449, 0.131), (1.008, 0.488, 0.136))
# Down the middle: fraction of the paper height from under the top LED line (0) to the ledge (1) -> colour
# (sRGB (178,134,90) dim under the head, (214,172,126) mid, (241,193,137) bright over the ledge)
VERT_F = (0.0, 0.186, 0.356, 0.525, 0.695, 0.864, 0.932, 0.983, 1.0)
VERT_C = ((0.459, 0.2465, 0.106), (0.459, 0.2465, 0.106), (0.70, 0.367, 0.136), (0.992, 0.497, 0.140),
          (1.315, 0.588, 0.092), (1.933, 0.815, 0.016), (2.10, 0.878, 0.018), (0.953, 0.462, 0.123), (0.80, 0.40, 0.12))
# Under the top LED line: distance (m) down -> added golden glow (sRGB (239,168,79) right under it, (191,130,67) 3 cm down)
TOP_D = (0.0, 0.0115, 0.0345, 0.069, 0.10)
TOP_ADD = ((1.20, 0.26, -0.10), (0.55, 0.11, -0.085), (0.10, -0.008, -0.042), (0.0, -0.02, -0.02), (0.0, 0.0, 0.0))
SEED = 20260928


def interp3(x, xs, cs):
    cs = np.array(cs)
    return np.stack([np.interp(x, xs, cs[:, k]) for k in range(3)], -1)


def blur(a, sigma_px_x, sigma_px_y):
    """Gaussian blur through the FFT (wraps: seamless where the field must tile)."""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * np.pi ** 2 * ((fx * sigma_px_x) ** 2 + (fy * sigma_px_y) ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def fibres(rng, n, len_m, width_px, amp, pw, ph, hpx=None, wpx=None):
    """Long thin wandering kozo fibres, splatted bilinearly in metre space (panel pw x ph m), then softened.
    hpx / wpx (r21): another picture size than the niche sets' H_PX x W_PX (the window paper)."""
    hpx, wpx = hpx or H_PX, wpx or W_PX
    acc = np.zeros((hpx, wpx), np.float64)
    sx, sy = wpx / pw, hpx / ph
    for _ in range(n):
        x, y = rng.uniform(0, pw), rng.uniform(0, ph)
        ang = rng.uniform(0, np.pi)
        L = len_m * rng.uniform(0.4, 1.6)
        steps = max(8, int(L / 0.0004))
        turn = rng.normal(0, 0.035, steps).cumsum()
        a = ang + turn
        px = x + np.cumsum(np.cos(a)) * (L / steps)
        py = y + np.cumsum(np.sin(a)) * (L / steps)
        u, v = px * sx, py * sy
        ok = (u >= 0) & (u < wpx - 1) & (v >= 0) & (v < hpx - 1)
        u, v = u[ok], v[ok]
        if not len(u):
            continue
        i, j = v.astype(int), u.astype(int)
        fu, fv = u - j, v - i
        s = rng.choice((-1.0, 1.0), p=(0.55, 0.45)) * rng.uniform(0.5, 1.0)
        for di, dj, wgt in ((0, 0, (1 - fu) * (1 - fv)), (0, 1, fu * (1 - fv)), (1, 0, (1 - fu) * fv), (1, 1, fu * fv)):
            np.add.at(acc, (i + di, j + dj), s * wgt)
    acc = blur(acc, width_px, width_px * sy / sx)
    return amp * acc / (acc.std() + 1e-9)


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


def washi(name, open_h):
    rng = np.random.default_rng(SEED)
    pw, ph = OPEN_W + 2 * REVEAL, open_h + BELOW + ABOVE
    x = (np.arange(W_PX) + 0.5) / W_PX * pw
    v = 1.0 - (np.arange(H_PX) + 0.5) / H_PX          # row 0 = the top of the panel, V = 1
    X, V = np.meshgrid(x, v)
    Z = V * ph
    z_led = BELOW + open_h - LED_IN                   # the top LED line's lower edge
    d_side = np.minimum(X - REVEAL - LED_IN, pw - REVEAL - LED_IN - X).clip(0, None)
    d_top = (z_led - Z).clip(0, None)
    f = ((z_led - Z) / (z_led - BELOW)).clip(0, 1)
    centre = np.array(SIDE_C[-1])
    ratio = interp3(d_side, SIDE_D, SIDE_C) / centre
    col = interp3(f, VERT_F, VERT_C) * ratio + interp3(d_top, TOP_D, TOP_ADD)
    col = np.clip(col, 0, None)
    # paper: even (no clouds), a fine formation, long kozo fibres, a fine grain: wall_alcove.png's fibrous cream
    form = blur(rng.normal(0, 1, X.shape), 4, 4 * (H_PX / ph) / (W_PX / pw))
    form = 0.025 * form / (form.std() + 1e-9)
    fib = (fibres(rng, 2600, 0.045, 0.8, 0.045, pw, ph) + fibres(rng, 800, 0.10, 1.5, 0.060, pw, ph)
           + fibres(rng, 180, 0.16, 2.2, 0.040, pw, ph))   # fine net, visible strands, a few long kozo strands
    grain = 0.015 * rng.normal(0, 1, X.shape)
    m = np.exp(form + fib + grain)
    fibre_tint = np.where(fib[..., None] > 0, np.array([1.0, 1.0, 0.98]), np.array([0.98, 0.96, 0.93]))
    lin = col * m[..., None] * fibre_tint / E_WASHI
    bc = lin_to_srgb(lin)
    sets = {k: TEX / f"T_AK_{name}_{k}.png" for k in ("BC", "ORM", "N")}
    save(sets["BC"], bc)
    orm = np.zeros(X.shape + (3,))
    orm[..., 0], orm[..., 1], orm[..., 2] = 1.0, 0.9, 0.0
    save(sets["ORM"], orm, noncolor=True)
    save(sets["N"], normal_from_height(blur(fib + 0.4 * form, 1.0, 1.0), 4.0), noncolor=True)
    c = bc[H_PX // 2, W_PX // 2]
    print("WASHI written", name, round(pw, 4), round(ph, 4), "mid sRGB", [round(float(t) * 255) for t in c],
          "clipped %", round(float((lin > 1).any(-1).mean() * 100), 2))


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


def washi_room(name, open_h):
    """Calibration pass 2 (2026-09-28, the room judge: the niches read as flat saturated amber panels; reference 2's are
    warm beige backs lit from the top, falling off downward): the SAME paper (same seed, formation, kozo fibres and
    relief as washi()) as a plain beige ALBEDO, lit by the niche's own downlight in the room (PanelLight_* at the lens
    under the head). The studio sets' painted glow (golden bands, bright over the ledge) stays in T_AK_HNicheWashi(190)."""
    rng = np.random.default_rng(SEED)
    pw, ph = OPEN_W + 2 * REVEAL, open_h + BELOW + ABOVE
    x = (np.arange(W_PX) + 0.5) / W_PX * pw
    v = 1.0 - (np.arange(H_PX) + 0.5) / H_PX
    X, V = np.meshgrid(x, v)
    form = blur(rng.normal(0, 1, X.shape), 4, 4 * (H_PX / ph) / (W_PX / pw))
    form = 0.025 * form / (form.std() + 1e-9)
    fib = (fibres(rng, 2600, 0.045, 0.8, 0.045, pw, ph) + fibres(rng, 800, 0.10, 1.5, 0.060, pw, ph)
           + fibres(rng, 180, 0.16, 2.2, 0.040, pw, ph))
    grain = 0.015 * rng.normal(0, 1, X.shape)
    m = np.exp(form + fib + grain)
    fibre_tint = np.where(fib[..., None] > 0, np.array([1.0, 1.0, 0.98]), np.array([0.98, 0.96, 0.93]))
    lin = srgb_to_lin(np.array(ROOM_PAPER)) * m[..., None] * fibre_tint
    bc = lin_to_srgb(lin)
    sets = {k: TEX / f"T_AK_{name}_{k}.png" for k in ("BC", "ORM", "N")}
    save(sets["BC"], bc)
    orm = np.zeros(X.shape + (3,))
    orm[..., 0], orm[..., 1], orm[..., 2] = 1.0, 0.9, 0.0
    save(sets["ORM"], orm, noncolor=True)
    save(sets["N"], normal_from_height(blur(fib + 0.4 * form, 1.0, 1.0), 4.0), noncolor=True)
    print("WASHI ROOM written", name, "mean sRGB", [round(float(t) * 255) for t in bc.reshape(-1, 3).mean(0)])


# calibration pass 2: the room sets (beige paper albedo; sRGB, reference 2's niche backs read ~(160,112,69) lit warm)
ROOM_SETS = {"HNicheWashiRoom": 1.26, "HNicheWashiRoom190": 1.00}
ROOM_PAPER = (0.80, 0.64, 0.44)
OWN = OWN + tuple(f"T_AK_{k}_" for k in ROOM_SETS)

# ------------------------------------------------------------------ dark bay backboard (r16 walls round, 2026-09-29)
# The room judge: the lit wall bays read as big flat beige glowing panels (blank shoji). armory3_reference2.png's side
# wall displays have DARK backboards (measured between the downlight pools ~sRGB (90,60,40) in its golden light, the
# pools ~(250,210,135)), dark frames and a warm gold light only at the edges and grazing down from the top. The board:
# a matte dark warm taupe hemp cloth on a board, 1 m tile (hero_walls maps it in metres, so the 3.85 m bay is not a
# stretched picture): a fine plain weave (warp and weft ~1.6 mm pitch), slubbed threads, a faint mottle; low contrast so
# it reads as a quiet dark board under the downlight graze.
BOARD_SET = "HBayBoard"
N_BOARD = 2048
BOARD_BASE = (0.40, 0.32, 0.25)      # sRGB albedo (~(102,82,64)); calibrated in the room (r16 walls t2: (0.235,0.196,0.168) read black at night)
OWN = OWN + (f"T_AK_{BOARD_SET}_",)


def bay_board():
    rng = np.random.default_rng(SEED + 31)
    n = N_BOARD
    t = (np.arange(n) + 0.5) / n
    U, VV = np.meshgrid(t, t)
    threads = 640                                   # per metre (tiles: an integer count over the tile)
    # slubs: each thread's thickness wanders along its length (long blur along the thread, tiling through the FFT)
    slub_w = blur(rng.normal(0, 1, (n, n)), 40, 0.8)     # weft (horizontal threads): long in x
    slub_w /= slub_w.std() + 1e-9
    slub_p = blur(rng.normal(0, 1, (n, n)), 0.8, 40)     # warp (vertical threads): long in y
    slub_p /= slub_p.std() + 1e-9
    weft = 0.5 + 0.5 * np.cos(2 * np.pi * threads * VV)
    warp = 0.5 + 0.5 * np.cos(2 * np.pi * threads * U)
    over = (np.floor(threads * U) + np.floor(threads * VV)) % 2       # plain weave: which thread lies on top
    hgt = np.where(over > 0, weft * (1 + 0.25 * slub_w), warp * (1 + 0.25 * slub_p))
    tone = 0.035 * (hgt - hgt.mean()) / (hgt.std() + 1e-9)
    tone += 0.030 * np.where(over > 0, slub_w, slub_p)
    mott = blur(rng.normal(0, 1, (n, n)), 90, 90)
    mott = 0.030 * mott / (mott.std() + 1e-9)
    lin = srgb_to_lin(np.array(BOARD_BASE)) * np.exp(tone + mott)[..., None]
    bc = lin_to_srgb(lin)
    sets = {k: TEX / f"T_AK_{BOARD_SET}_{k}.png" for k in ("BC", "ORM", "N")}
    save(sets["BC"], bc)
    orm = np.zeros((n, n, 3))
    orm[..., 0] = 1.0 - 0.10 * (1 - hgt)
    orm[..., 1] = 0.86 + 0.04 * (1 - hgt)
    orm[..., 2] = 0.0
    save(sets["ORM"], orm, noncolor=True)
    save(sets["N"], normal_from_height(blur(hgt, 0.7, 0.7), 0.6), noncolor=True)
    print("BAY BOARD written", sets["BC"], "mean sRGB", [round(float(c) * 255) for c in bc.reshape(-1, 3).mean(0)])


# ------------------------------------------------------------------ backlit window paper (r21, 2026-10-02)
# The user: "re-implement the windows on the top rows where the plants are" (armory3_reference2.png: the upper side bays
# are bright lattice windows with the red plum branches in front of them). build_armory_kit puts a 1 cm paper sheet
# (SM_AK_Window_Paper_35_W / _E) 9 cm behind each upper lattice, its room face mapped 0-1 onto this picture; the
# materials M_AK_HWinPaperW / E read the BC as an unlit emissive picture (emit_image + unlit). The picture is the paper
# as a light source: warm cream kozo paper (the day / golden colour; at night render_armory NIGHT_EMIT multiplies in the
# moon's cool tint (0.30, 0.45, 1.0), so WP_BASE x tint = (0.30, 0.33, 0.37): a cool-neutral glow), even over the field
# with a soft cloudy formation and fine fibres (backlit washi), a little brighter toward the top (the sky side), falling
# off over the last few cm into the dark reveals (the lining's shade). No pattern of its own: the dark lattice bars and
# the plum branches in front of it make the pattern.
WP_SET = "HWinPaper"
WP_W, WP_H = 3.50, 1.45            # the clear opening (build_armory_kit WIN_BAY - 0.5 x WIN_HEAD - WIN_SILL), metres
WP_PX = (2048, 1024)               # (width, height) power of two: 1.7 x 1.4 mm per texel
WP_BASE = (1.00, 0.74, 0.37)       # linear: warm cream (sRGB ~(255, 222, 163))
WP_PEAK = 0.92                     # the brightest texel's level (BC stays under 1: the emission strength scales it)
WP_EDGE = 0.07                     # m: the fall-off into each reveal
OWN = OWN + (f"T_AK_{WP_SET}_",)


def win_paper():
    rng = np.random.default_rng(SEED + 47)
    wpx, hpx = WP_PX
    x = (np.arange(wpx) + 0.5) / wpx * WP_W
    z = (1.0 - (np.arange(hpx) + 0.5) / hpx) * WP_H     # row 0 = the top of the opening
    X, Z = np.meshgrid(x, z)
    # the field: a gentle rise toward the top, the edges falling off into the reveals (smooth, ~35 % at the very edge)
    d = np.minimum(np.minimum(X, WP_W - X), np.minimum(Z, WP_H - Z))
    t = np.clip(d / WP_EDGE, 0, 1)
    edge = 0.35 + 0.65 * t * t * (3 - 2 * t)
    vert = 0.86 + 0.14 * (Z / WP_H) ** 1.5
    # backlit washi: a soft cloudy formation (thicker / thinner paper), fibres and a fine grain, low contrast
    sx, sz = wpx / WP_W, hpx / WP_H
    form = blur(rng.normal(0, 1, X.shape), 0.025 * sx, 0.025 * sz)
    form = 0.035 * form / (form.std() + 1e-9)
    fine = blur(rng.normal(0, 1, X.shape), 0.004 * sx, 0.004 * sz)
    fine = 0.02 * fine / (fine.std() + 1e-9)
    fib = (fibres(rng, 9000, 0.05, 0.8, 0.010, WP_W, WP_H, hpx, wpx)
           + fibres(rng, 1500, 0.12, 1.4, 0.014, WP_W, WP_H, hpx, wpx))
    grain = 0.010 * rng.normal(0, 1, X.shape)
    m = np.exp(form + fine + fib + grain)
    lin = np.array(WP_BASE)[None, None, :] * (edge * vert * m)[..., None]
    lin = lin * (WP_PEAK / np.percentile(lin[..., 0], 99.0))
    bc = lin_to_srgb(lin)
    sets = {k: TEX / f"T_AK_{WP_SET}_{k}.png" for k in ("BC", "ORM", "N")}
    save(sets["BC"], bc)
    orm = np.zeros(X.shape + (3,))
    orm[..., 0], orm[..., 1], orm[..., 2] = 1.0, 0.9, 0.0
    save(sets["ORM"], orm, noncolor=True)
    save(sets["N"], normal_from_height(blur(fib + 0.3 * form, 1.0, 1.0), 2.0), noncolor=True)
    c = bc[hpx // 2, wpx // 2]
    print("WINDOW PAPER written", sets["BC"], "mid sRGB", [round(float(v) * 255) for v in c],
          "mean sRGB", [round(float(v) * 255) for v in bc.reshape(-1, 3).mean(0)],
          "edge sRGB", [round(float(v) * 255) for v in bc[hpx // 2, 2]])


if __name__ == "__main__":
    import sys
    _a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--out" in _a:   # a test copy: write into <preview dir>/Textures (build_armory_kit.tex_file prefers it)
        TEX = Path(_a[_a.index("--out") + 1])
        TEX.mkdir(parents=True, exist_ok=True)
        OAK = {k: TEX / f"T_AK_HWallOak_{k}.png" for k in ("BC", "ORM", "N")}
    if "--winpaper" in _a:   # r21: only the backlit window paper (T_AK_HWinPaper)
        win_paper()
        sys.exit(0)
    if "--board" in _a:   # r16 walls round: only the dark bay backboard set
        bay_board()
        sys.exit(0)
    only_room = "--room" in _a
    if not only_room:   # --room: write only the pass-2 room sets (the studio washi and the oak are left as they are)
        for _name, _h in WASHI_SETS.items():
            washi(_name, _h)
        oak()
    for _name, _h in ROOM_SETS.items():
        washi_room(_name, _h)
    bay_board()
