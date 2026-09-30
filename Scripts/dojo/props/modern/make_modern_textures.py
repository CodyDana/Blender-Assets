"""Seamless procedural textures for the dojo MODERN PROPS kit (kit 10): vending machine, AC units, lamps, utility pole,
street lamps, junction box.

Every map is generated here from periodic FFT noise and periodic cell patterns, so every tiling set repeats with no
seam. Nothing comes from a photo, scan or third-party source; the reference sheets are look reference only.
Writes Exports/DojoKit/Props/modern/Textures/T_DKP_Modern_<Set>_{BC,N,ORM}.png
  BC  sRGB base colour
  N   DirectX tangent normal (green down, the Unreal convention; the Blender review material flips it back)
  ORM linear: R ambient occlusion, G roughness, B metallic
and WorkFiles/dojo/build/props/modern/textures_report.json (size, tile, px/cm, mean colour, seam scores).

Helpers (write_png, pnoise, blur, normal_dx, seam_score) are copied from Scripts/dojo/ground/make_ground_textures.py
(read-only reuse, not imported, so this script never runs another kit's code).

Run with Blender's bundled Python (numpy is included):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/props/modern/make_modern_textures.py
"""
import json
import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "Exports" / "DojoKit" / "Props" / "modern" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "modern"
N = 1024          # tiling sets: 1024 px over 2.0 m = 5.12 px/cm (STYLE_GUIDE 6, near pieces)
TILE_M = 2.0


# --------------------------------------------------------------------------- helpers (copied, see the docstring)

def write_png(path, rgb):
    a = np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
    h, w, ch = a.shape
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if ch == 4 else 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def pnoise(h, w, beta, seed, stretch_u=1.0, stretch_v=1.0, fmin=0.0, fmax=None):
    """Periodic 1/f^beta noise, zero mean, unit std (rows = v, columns = u). stretch_u > 1 elongates features along u,
    stretch_v > 1 along v (rows direction, i.e. vertical in the image)."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fv = np.fft.fftfreq(h)[:, None] * h / 256.0 * stretch_v
    fu = np.fft.fftfreq(w)[None, :] * w / 256.0 * stretch_u
    f = np.sqrt(fu * fu + fv * fv)
    f[0, 0] = 1.0
    F = F / np.power(f, beta)
    if fmin > 0:
        F[f < fmin] = 0
    if fmax is not None:
        F[f > fmax] = 0
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n - n.mean()) / (n.std() + 1e-9)


def blur(a, radius):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * radius) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def srgb(hexstr):
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def normal_dx(height_m, px_m):
    du = (np.roll(height_m, -1, 1) - np.roll(height_m, 1, 1)) / (2 * px_m)
    dv = -(np.roll(height_m, -1, 0) - np.roll(height_m, 1, 0)) / (2 * px_m)
    nx, ny, nz = -du, -dv, np.ones_like(height_m)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / ln * 0.5 + 0.5, -ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5])


def seam_score(a):
    a = a.mean(2) if a.ndim == 3 else a
    rows = np.abs(a[0] - a[-1]).mean() / (np.abs(np.diff(a, axis=0)).mean() + 1e-12)
    cols = np.abs(a[:, 0] - a[:, -1]).mean() / (np.abs(np.diff(a, axis=1)).mean() + 1e-12)
    return round(float(rows), 3), round(float(cols), 3)


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def cells(n, grid, seed):
    """Periodic Worley cells on a jittered grid (one seed per grid cell, 3 x 3 neighbourhood search):
    (distance to nearest seed, distance to second nearest, nearest id) in pixels. `grid` must divide n."""
    rng = np.random.default_rng(seed)
    s = n // grid
    jit = rng.uniform(0.05, 0.95, (grid, grid, 2))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cy, cx = (yy // s).astype(int), (xx // s).astype(int)
    d1 = np.full((n, n), 1e9, np.float32)
    d2 = np.full((n, n), 1e9, np.float32)
    idx = np.zeros((n, n), np.int32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            ny_, nx_ = (cy + oy) % grid, (cx + ox) % grid
            py = (cy + oy + jit[ny_, nx_, 0]) * s
            px = (cx + ox + jit[ny_, nx_, 1]) * s
            d = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
            closer = d < d1
            d2 = np.where(closer, d1, np.minimum(d2, d))
            idx = np.where(closer, ny_ * grid + nx_, idx)
            d1 = np.where(closer, d, d1)
    return d1, d2, idx


REPORT = {}


def save_set(name, bc, height_m, rough, ao=None, metal=0.0, px_m=TILE_M / N, extra=None, normal=None, alpha=None):
    OUT.mkdir(parents=True, exist_ok=True)
    bc = np.clip(bc, 0, 1)
    nrm = normal if normal is not None else normal_dx(height_m, px_m)
    ao = np.ones_like(rough) if ao is None else ao
    metal_map = metal if isinstance(metal, np.ndarray) else np.full_like(rough, metal)
    orm = np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1), np.clip(metal_map, 0, 1)])
    write_png(OUT / f"T_DKP_Modern_{name}_BC.png", bc if alpha is None else np.dstack([bc, np.clip(alpha, 0, 1)]))
    write_png(OUT / f"T_DKP_Modern_{name}_N.png", nrm)
    write_png(OUT / f"T_DKP_Modern_{name}_ORM.png", orm)
    ang = np.degrees(np.arccos(np.clip(nrm[..., 2] * 2 - 1, -1, 1)))
    rep = {"size_px": [int(bc.shape[1]), int(bc.shape[0])],
           "tile_m": [round(bc.shape[1] * px_m, 4), round(bc.shape[0] * px_m, 4)],
           "px_per_cm": round(0.01 / px_m, 3), "source": "own procedural (numpy, this script)",
           "mean_srgb": [round(float(x), 3) for x in bc.reshape(-1, 3).mean(0)],
           "mean_srgb_8bit_hex": "#" + "".join(f"{int(round(float(x) * 255)):02X}" for x in bc.reshape(-1, 3).mean(0)),
           "albedo_max_srgb": round(float(bc.max()), 3), "albedo_min_srgb": round(float(bc.min()), 3),
           "rough_mean": round(float(np.clip(rough, 0.02, 1).mean()), 3),
           "metal_mean": round(float(np.clip(metal_map, 0, 1).mean()), 3), "ao_mean": round(float(ao.mean()), 3),
           "normal_tilt_deg_mean_p95": [round(float(ang.mean()), 2), round(float(np.percentile(ang, 95)), 2)],
           "seam_score_bc_rows_cols": seam_score(bc), "seam_score_n_rows_cols": seam_score(nrm)}
    if extra:
        rep.update(extra)
    REPORT[name] = rep
    print(name, rep["mean_srgb_8bit_hex"], rep["size_px"], rep["seam_score_bc_rows_cols"])


def lerp(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2:
        t = t[..., None]
    return a * (1 - t) + b * t


# --------------------------------------------------------------------------- painted sheet steel

def rust_runs(n, seed, count, h_of_row, px_m, h_lo=0.12, h_hi=1.9):
    """Rust bleeding from fasteners and seams: `count` sources (a small rust spot) at random u and height, each with a
    run that tapers and wiggles DOWN the panel (toward lower v). Periodic in u. Returns (run mask, source mask)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    runs = np.zeros((n, n), np.float32)
    src = np.zeros((n, n), np.float32)
    for _ in range(count):
        u0 = rng.uniform(0, n)
        h0 = rng.uniform(h_lo, h_hi)
        r0 = int(np.clip(round((1 - h0 / (n * px_m)) * n), 0, n - 1))       # image row of the source
        length = rng.uniform(0.08, 0.55) / px_m                              # px
        width = rng.uniform(1.2, 3.2)
        amp = rng.uniform(0.45, 1.0)
        dy = yy - r0                                                         # >0 below the source (image down)
        wig = 2.0 * np.sin(dy / rng.uniform(9, 23) + rng.uniform(0, 6.3))
        dx = np.abs(((xx - u0 - wig) + n / 2) % n - n / 2)
        t = np.clip(dy / length, 0, 1)
        w = width * (1 - 0.6 * t)
        m = np.clip(1 - dx / np.maximum(w, 0.4), 0, 1) * (dy >= 0) * (1 - t) ** 1.3 * amp
        runs = np.maximum(runs, m)
        ds = np.sqrt((((xx - u0) + n / 2) % n - n / 2) ** 2 + (yy - r0) ** 2)
        src = np.maximum(src, np.clip(1 - ds / rng.uniform(2.5, 6.0), 0, 1) * amp)
    return runs, src


def paint(name, base_hex, faded_hex, seed, chip_amount, grime_hex="#3E3A33", primer_hex="#8C8A84",
          rust_hex="#7A4A2E", rough_paint=0.48, streak_amount=0.35, runs=72):
    """Aged 1970s paint on sheet steel, HEIGHT-ANCHORED: the map tiles seamlessly along U, and V runs 0 -> 2 m ABOVE
    THE PAINTED BASE of each prop (the builder offsets V per asset so the base sits at v = 0; no prop is taller than
    2 m of paint, so V never wraps). That lets the base carry grime and splash, the upper panels a stronger sun fade,
    and rust bleed run DOWN from fastener / seam spots, with chipped and peeling paint (primer + rust cores)."""
    n = N
    px_m = TILE_M / n
    rows = np.arange(n, dtype=np.float32)[:, None]
    h = (1 - (rows + 0.5) / n) * TILE_M * np.ones((1, n), np.float32)        # metres above the painted base
    fade = smooth(pnoise(n, n, 2.2, seed), -0.6, 1.4)                     # large, soft fade patches
    fade = np.clip(fade * (0.55 + 0.45 * smooth(h, 0.3, 1.6)), 0, 1)      # sun fades the upper panels more
    speck = pnoise(n, n, 0.6, seed + 1)                                    # fine speckle
    streak = pnoise(n, n, 1.4, seed + 2, stretch_v=14.0)                   # long vertical grime streaks
    streak = smooth(streak, 0.3, 2.0) * streak_amount
    chipn = pnoise(n, n, 1.7, seed + 3) + 0.35 * pnoise(n, n, 0.9, seed + 4)
    lowboost = 0.35 * (1 - smooth(h, 0.05, 0.5))                           # knocks and chips near the ground
    chip = smooth(chipn + lowboost, 2.3 - chip_amount, 2.45 - chip_amount)  # chip mask 0..1
    rust = smooth(chipn + lowboost, 2.6 - chip_amount, 2.95 - chip_amount)  # rust in the chip cores
    peel = smooth(pnoise(n, n, 2.0, seed + 6) + 0.6 * pnoise(n, n, 1.0, seed + 7), 2.2, 2.35)   # peeled patches
    splash = smooth(pnoise(n, n, 0.9, seed + 8), 0.2, 1.4)
    grime = np.clip((1 - smooth(h, 0.0, 0.22)) * 0.75 + splash * (1 - smooth(h, 0.05, 0.42)) * 0.5, 0, 1)
    rrun, rsrc = rust_runs(n, seed + 9, runs, h, px_m)
    base = lerp(srgb(base_hex)[None, None, :], srgb(faded_hex)[None, None, :], fade * 0.75)
    base = base * (1 + 0.04 * speck[..., None])
    base = lerp(base, srgb(grime_hex)[None, None, :], streak * 0.55)
    bc = lerp(base, srgb(primer_hex)[None, None, :], np.maximum(chip, peel * 0.9))
    bc = lerp(bc, srgb(rust_hex)[None, None, :], np.maximum(rust, peel * 0.35))
    bc = lerp(bc, srgb("#6B3F22")[None, None, :], rrun * 0.78)
    bc = lerp(bc, srgb("#4E2C18")[None, None, :], rsrc * 0.85)
    bc = lerp(bc, srgb("#3C352C")[None, None, :], grime * 0.62)
    orange_peel = pnoise(n, n, 0.2, seed + 5, fmin=0.6) * 0.00012          # orange peel, metres
    height = orange_peel - blur(np.maximum(chip, peel), 1.2) * 0.0005 - rust * 0.0002 + rsrc * 0.0004
    rough = rough_paint + 0.1 * fade + 0.015 * speck + 0.18 * streak + 0.25 * np.maximum(chip, peel)         + 0.2 * rrun + 0.25 * grime
    ao = 1 - 0.18 * chip - 0.1 * streak - 0.25 * grime - 0.15 * rsrc
    return save_set(name, bc, height, rough, ao, 0.0,
                    extra={"base": base_hex, "faded": faded_hex, "rust_runs": runs,
                           "tile_note": "tiles along U (seamless); V is height-anchored: 0 -> 2 m above the painted "
                                        "base (grime at v 0-0.1, sun fade upward, rust runs downward). The builder "
                                        "offsets V per asset; no painted part spans more than 2 m, so V never wraps."})


# --------------------------------------------------------------------------- galvanised steel

def galvanised(seed=31):
    n = N
    d1, d2, idx = cells(n, 32, seed)                                       # spangle crystals (32 x 32 per 2 m, about 6 cm)
    rng = np.random.default_rng(seed)
    tone = rng.normal(0, 1, 32 * 32)[idx]
    edge = smooth(d2 - d1, 0, 2.5)
    dull = smooth(pnoise(n, n, 2.0, seed + 1), -0.2, 1.6)                  # dull grey weathering patches
    whiterust = smooth(pnoise(n, n, 1.2, seed + 2), 1.5, 2.6)
    streak = smooth(pnoise(n, n, 1.4, seed + 3, stretch_v=12.0), 0.8, 2.4)
    base = srgb("#A7AAAD")[None, None, :] * (1 + 0.045 * tone[..., None]) * (0.96 + 0.04 * edge[..., None])
    bc = lerp(base, srgb("#8E918F")[None, None, :], dull * 0.7)
    bc = lerp(bc, srgb("#C9C9C2")[None, None, :], whiterust * 0.8)
    bc = lerp(bc, srgb("#5F5A50")[None, None, :], streak * 0.35)
    rough = 0.36 + 0.06 * tone * 0.5 + 0.22 * dull + 0.35 * whiterust + 0.1 * streak
    metal = np.clip(1.0 - 0.35 * dull - 0.9 * whiterust - 0.4 * streak, 0, 1)
    height = (1 - edge) * -0.00012 + whiterust * 0.0002 + tone * 0.00003
    ao = 1 - 0.08 * streak
    return save_set("Galvanised", bc, height, rough, ao, metal, extra={"base": "#A7AAAD"})


# --------------------------------------------------------------------------- dark painted cast iron

def iron_dark(seed=41):
    n = N
    blot = smooth(pnoise(n, n, 2.0, seed), -0.8, 1.6)
    rustn = pnoise(n, n, 1.5, seed + 1) + 0.4 * pnoise(n, n, 0.8, seed + 2)
    rust = smooth(rustn, 1.6, 2.4)
    bleed = smooth(pnoise(n, n, 1.3, seed + 3, stretch_v=10.0), 1.0, 2.4) * 0.6
    cast = pnoise(n, n, 0.4, seed + 4, fmin=0.3)                           # cast / hammered surface
    bc = lerp(srgb("#2B2724")[None, None, :], srgb("#3A332D")[None, None, :], blot)
    bc = lerp(bc, srgb("#6E4128")[None, None, :], rust)
    bc = lerp(bc, srgb("#5A3A26")[None, None, :], bleed * (1 - rust))
    bc = bc * (1 + 0.04 * cast[..., None])
    rough = 0.52 + 0.1 * blot + 0.3 * rust + 0.1 * bleed
    height = cast * 0.00025 + blur(rust, 1.5) * 0.0006
    ao = 1 - 0.12 * rust
    return save_set("IronDark", bc, height, rough, ao, 0.0, extra={"base": "#2B2724", "rust": "#6E4128"})


# --------------------------------------------------------------------------- creosoted pole timber

def pole_wood(seed=51):
    """Weathered pole timber, warm orange-brown (the sheet's pole), sun-silvered in patches, with many long drying
    checks. Grain and checks run along V (the pole axis; the kit's tube UVs put the length on V). Seamless in both
    directions (V tiles along the 8 m pole)."""
    n = N
    grain = pnoise(n, n, 1.2, seed, stretch_v=60.0)
    fine = pnoise(n, n, 0.8, seed + 1, stretch_v=30.0)
    blot = pnoise(n, n, 2.2, seed + 2)
    silver = smooth(pnoise(n, n, 1.8, seed + 3, stretch_v=4.0), 0.3, 1.8)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    crack = np.zeros((n, n), np.float32)
    edge = np.zeros((n, n), np.float32)
    for k in range(22):
        x0 = rng.uniform(0, n)
        wav = 6.0 * np.sin(2 * np.pi * (yy / n) * rng.integers(1, 3) + rng.uniform(0, 6.3)) \
            + 3.0 * np.sin(2 * np.pi * (yy / n) * rng.integers(3, 6) + rng.uniform(0, 6.3))
        dx = np.abs(((xx - x0 - wav) + n / 2) % n - n / 2)
        big = k < 7
        width = (1.0 if big else 0.55) + (1.1 if big else 0.5) * (0.5 + 0.5 * np.sin(
            2 * np.pi * yy / n * rng.integers(1, 4) + rng.uniform(0, 6.3)))
        # checks open and close along their length (periodic in V)
        open_ = smooth(np.sin(2 * np.pi * yy / n * rng.integers(1, 3) + rng.uniform(0, 6.3)),
                       -0.6 if big else -0.1, 0.3)
        crack = np.maximum(crack, np.clip(1 - dx / width, 0, 1) * open_)
        edge = np.maximum(edge, np.clip(1 - dx / (width + 2.5), 0, 1) * open_)
    base = lerp(srgb("#3F2818")[None, None, :], srgb("#5E3C22")[None, None, :], smooth(blot, -0.5, 1.6) * 0.85)
    bc = base * (1 + 0.11 * grain[..., None] + 0.05 * fine[..., None])
    bc = lerp(bc, srgb("#6E655B")[None, None, :], silver * 0.30)                # sun-silvered weathering
    bc = lerp(bc, srgb("#3A2618")[None, None, :], (edge - crack).clip(0, 1) * 0.35)
    bc = lerp(bc, srgb("#1A120C")[None, None, :], crack * 0.9)
    height = grain * 0.0004 + fine * 0.0002 - crack * 0.004
    rough = 0.82 + 0.05 * fine * 0.3 + 0.06 * silver - 0.05 * crack
    ao = 1 - 0.55 * crack - 0.15 * (edge - crack).clip(0, 1)
    return save_set("PoleWood", bc, height, rough, ao, 0.0,
                    extra={"base": "#4E3220", "grain": "along V", "checks": 22})


# --------------------------------------------------------------------------- concrete

def concrete(seed=61):
    n = N
    blot = pnoise(n, n, 2.1, seed)
    fine = pnoise(n, n, 0.5, seed + 1)
    d1, d2, _ = cells(n, 64, seed + 2)
    pores = smooth(3.2 - d1, 0, 1.8) * (pnoise(n, n, 0.3, seed + 3) > 1.1)
    stain = smooth(pnoise(n, n, 1.4, seed + 4, stretch_v=8.0), 0.6, 2.2)
    bc = srgb("#9A9892")[None, None, :] * (1 + 0.06 * blot[..., None] + 0.04 * fine[..., None])
    bc = lerp(bc, srgb("#6B675F")[None, None, :], stain * 0.45)
    bc = lerp(bc, srgb("#4E4B46")[None, None, :], pores * 0.8)
    height = fine * 0.0005 - pores * 0.002
    rough = 0.88 + 0.04 * fine * 0.3 + 0.05 * pores
    ao = 1 - 0.35 * pores
    return save_set("Concrete", bc, height, rough, ao, 0.0, extra={"base": "#9A9892"})


# --------------------------------------------------------------------------- condenser coil fins

def coil_fins(seed=71):
    """Aluminium condenser coil seen through its opening: vertical fins every 2.5 mm (512 px over 0.25 m = 20.48 px/cm,
    5 px a fin), the copper hairpin tubes as faint horizontal bands every 25 mm, dust caught in the fins."""
    n, tile = 512, 0.25
    px_m = tile / n
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    fin = 0.5 + 0.5 * np.cos(2 * np.pi * xx / (n / 102.0))             # 1 on the fin, 0 in the gap (102 fins per tile)
    gap = smooth(0.35 - fin, -0.1, 0.35)
    tube = smooth(np.cos(2 * np.pi * yy / 51.2), 0.86, 0.97)            # hairpin tubes every 25 mm
    dust = smooth(pnoise(n, n, 1.6, seed), 0.0, 2.0)
    bc = lerp(srgb("#B7BBBC")[None, None, :], srgb("#232526")[None, None, :], gap * 0.85)
    bc = lerp(bc, srgb("#8C6A4E")[None, None, :], tube * 0.35)
    bc = lerp(bc, srgb("#7A7468")[None, None, :], dust * 0.55)
    height = fin * 0.0012 + tube * 0.0006
    rough = 0.42 + 0.3 * dust + 0.2 * gap
    metal = np.clip(0.85 - 0.6 * dust - 0.7 * gap, 0, 1)
    ao = 1 - 0.55 * gap
    return save_set("CoilFins", bc, height, rough, ao, metal, px_m=px_m,
                    extra={"fin_pitch_mm": 2.5, "tube_pitch_mm": 25.0, "note": "fins run along V"})


# --------------------------------------------------------------------------- vending display panel (unique, emissive)

def vend_panel(seed=81):
    """The machine's display window (unique, emissive): teal-tinted glazing over a dim, warm backlit display of plain
    dummy cans on three shelves. Blank: no text, no labels, no product art (the cans are plain coloured cylinders).
    Mapped 0-1 over the arch-topped window opening (0.66 x 0.54 m; the arch is the white surround in front of it).
    ORM.R carries a real AO term baked here from the display's own height field (can bodies, shelf lips, the recess
    edge), so it is not a constant. The Unreal emissive material uses BC as the emissive colour (times a scalar)."""
    n, nh = 512, 256
    W_M, H_M = 0.66, 0.33
    v, u = np.mgrid[0:nh, 0:n].astype(np.float32)
    v, u = v / nh, u / n                                                  # v = 0 at the image top
    x, y = u * W_M, (1 - v) * H_M                                       # metres, y up from the window bottom
    rng = np.random.default_rng(seed)
    hgt = np.zeros((nh, n), np.float32)                                 # metres toward the viewer
    glow = np.clip(1 - 1.5 * ((u - 0.5) ** 2 + 0.9 * (v - 0.5) ** 2), 0, 1) ** 1.2
    col = lerp(srgb("#24595F")[None, None, :], srgb("#D9C096")[None, None, :], glow * 0.45)
    tones = ["#B5AC98", "#9E6450", "#6F958F", "#B9A874", "#8C8199", "#B5AC98", "#7F9A70", "#9E6450"]
    for si, s0 in enumerate((0.030, 0.180)):
        lip = (y > s0 - 0.012) & (y < s0 + 0.004)
        hgt = np.where(lip, 0.012, hgt)
        col = np.where(lip[..., None], srgb("#9A9C98")[None, None, :], col)
        for k in range(7):
            cx = 0.06 + k * 0.09 + rng.uniform(-0.004, 0.004)
            r = 0.029
            y0, y1 = s0 + 0.004, s0 + 0.004 + 0.118
            body = (np.abs(x - cx) < r) & (y > y0) & (y < y1 - r * 0.45)
            cap = ((x - cx) / r) ** 2 + ((y - (y1 - r * 0.45)) / (r * 0.45)) ** 2 < 1
            inside = body | cap
            prof = np.sqrt(np.clip(1 - ((x - cx) / r) ** 2, 0, 1))
            hgt = np.where(inside, np.maximum(hgt, 0.02 * prof), hgt)
            tone = srgb(tones[(k + 3 * si) % len(tones)])
            shade = (0.62 + 0.38 * prof)[..., None]
            col = np.where(inside[..., None], tone[None, None, :] * shade, col)
    # real AO from the height field: occlusion where the neighbourhood stands higher (multi-radius blur)
    occ = np.zeros_like(hgt)
    for rad, wgt in ((2, 0.35), (6, 0.4), (14, 0.25)):
        occ += wgt * np.clip((blur(hgt, rad) - hgt) / 0.006, 0, 1)
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    recess = 1 - smooth(edge, 0.0, 0.06)                                 # the recess edge behind the surround
    ao = np.clip(1 - 0.6 * occ - 0.45 * recess, 0.15, 1)
    glass = pnoise(nh, n, 1.2, seed + 2) * 0.02
    lum = (0.5 + 0.5 * np.clip(1 - 1.4 * ((u - 0.5) ** 2 + 0.7 * (v - 0.45) ** 2), 0, 1)) * ao + glass
    tint = srgb("#8FC4C4")[None, None, :]                                # teal-tinted glazing
    bc = np.clip(col * lum[..., None] * (0.55 + 0.45 * tint) * 0.95, 0, 1)
    rough = np.full((nh, n), 0.12)
    return save_set("VendPanel", bc, hgt, rough, ao, 0.0, px_m=W_M / n,
                    extra={"unique": True, "mapped_over_m": [W_M, H_M], "emissive": "BC used as emissive colour",
                           "ao": "baked from the display height field (cans, shelf lips, recess edge)",
                           "ao_mean_min": [round(float(ao.mean()), 3), round(float(ao.min()), 3)]})


def lamp_glass(seed=91):
    """Seeded (bubbly) amber lantern glass, one pane mapped 0-1 (u across, v up). The BC doubles as the emissive
    colour: a warm falloff from a hotspot at the bulb height (v 0.45) toward the soot-darkened top and the bottom
    rim, so an opaque-emissive Unreal material still reads lit with a bulb behind it."""
    w, hpx = 256, 512
    yy, xx = np.mgrid[0:hpx, 0:w].astype(np.float32)
    v = 1 - yy / hpx
    u = xx / w
    hot = np.exp(-(((v - 0.45) / 0.26) ** 2) - ((u - 0.5) / 0.34) ** 2)
    lum = 0.28 + 0.72 * hot
    soot = smooth(v, 0.78, 1.0) * 0.45
    rng = np.random.default_rng(seed)
    bub = np.zeros((hpx, w), np.float32)
    for _ in range(160):
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, hpx), rng.uniform(0.8, 2.6)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        bub = np.maximum(bub, np.clip(1 - d / r, 0, 1))
    wav = pnoise(hpx, w, 1.6, seed + 1) * 0.5
    colr = lerp(srgb("#7A4418")[None, None, :], srgb("#FFC477")[None, None, :], lum)
    bc = colr * (1 - soot[..., None]) * (1 + 0.06 * wav[..., None]) * (1 + 0.12 * bub[..., None])
    height = bub * 0.0004 + wav * 0.0002
    rough = 0.22 + 0.2 * soot + 0.05 * wav
    ao = 1 - 0.3 * soot
    return save_set("LampGlass", bc, height, rough, ao, 0.0, px_m=0.2 / hpx,
                    extra={"unique": True, "mapping": "one pane 0-1 (u across, v up)",
                           "emissive": "BC used as emissive colour", "hotspot_v": 0.45})


def fan_grille(seed=101):
    """Condenser fan guard (unique, alpha-masked): 11 concentric rings and 14 spokes of wire over the fan disc, a
    plain blank centre plate. RGBA BC (alpha = wire) for a masked material. Replaces the modelled rings, which cost
    about 2,800 triangles on the roof unit."""
    n = 512
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx = cy = (n - 1) / 2
    R = n / 2 - 2
    dx, dy = xx - cx, yy - cy
    r = np.sqrt(dx * dx + dy * dy)
    wire_px = 2.6
    rings = np.zeros((n, n), np.float32)
    for k in range(1, 12):
        rk = R * (0.16 + 0.84 * k / 11)
        rings = np.maximum(rings, np.clip(1 - np.abs(r - rk) / wire_px, 0, 1))
    spokes = np.zeros_like(rings)
    for k in range(14):
        a = 2 * np.pi * k / 14
        d = np.abs(-dx * np.sin(a) + dy * np.cos(a))
        along = dx * np.cos(a) + dy * np.sin(a)
        spokes = np.maximum(spokes, np.clip(1 - d / (wire_px * 0.9), 0, 1) * (along > R * 0.12) * (r < R + 1))
    centre = np.clip((R * 0.17 - r) / 1.5, 0, 1)
    wire = np.maximum(rings, spokes)
    alpha = np.clip(np.maximum(wire, centre), 0, 1) * (r < R + 1.5)
    dust = smooth(pnoise(n, n, 1.4, seed), 0.0, 2.0)
    rustn = smooth(pnoise(n, n, 1.2, seed + 1), 1.4, 2.3)
    bc = lerp(srgb("#5C5F60")[None, None, :], srgb("#3B3A36")[None, None, :], dust * 0.6)
    bc = lerp(bc, srgb("#6B4128")[None, None, :], rustn * 0.75)
    bc = lerp(bc, srgb("#8E918F")[None, None, :], centre * 0.8)
    height = np.sqrt(wire) * 0.0015 + centre * 0.001
    rough = 0.5 + 0.3 * dust + 0.2 * rustn
    metal = np.clip(0.6 - 0.5 * dust - 0.6 * rustn, 0, 1)
    ao = 1 - 0.3 * dust
    return save_set("FanGrille", bc, height, rough, ao, metal, px_m=0.67 / n, alpha=alpha,
                    extra={"unique": True, "alpha": "wire mask (masked material)", "rings": 11, "spokes": 14,
                           "alpha_coverage": round(float(alpha.mean()), 3)})


def main():
    paint("PaintTeal", "#2C6F75", "#5A9392", seed=11, chip_amount=0.45)
    paint("PaintGrey", "#9A9587", "#ABA696", seed=27, chip_amount=0.42, grime_hex="#5E574B", rough_paint=0.5)
    paint("PaintWhite", "#D5D2C6", "#E3DDCB", seed=21, chip_amount=0.38, grime_hex="#6F675A", rough_paint=0.44,
          streak_amount=0.6)
    galvanised()
    iron_dark()
    pole_wood()
    concrete()
    coil_fins()
    vend_panel()
    lamp_glass()
    fan_grille()
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "textures_report.json").write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
    print("wrote", len(REPORT), "sets to", OUT)


if __name__ == "__main__":
    main()
