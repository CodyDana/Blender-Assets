"""Kit 9 (dojo training props) tiling textures: weathered timber (side grain), timber end grain, forged iron and
twisted straw rope. All original and procedural (periodic FFT noise and periodic line functions), so every tile
repeats with no seam; the seam test at the end measures it. No photo, scan or third-party source.

Sets (T_DKP_Train_<Set>_{BC,N,ORM}.png; BC sRGB, N DirectX green (UE), ORM = AO, roughness, metal, linear):
  Timber     1024 px over 2.0 m (5.12 px/cm, STYLE_GUIDE 6), grain along U. GENERIC (look pass: M_Env_Wood).
  TimberEnd  512 px over 1.0 m (5.12 px/cm), growth-ring arcs + checks, for end-grain faces. GENERIC.
  Iron       512 px over 1.0 m (5.12 px/cm), dark forged iron, pitting, light rust. GENERIC (M_Steel_Master tint later).
  Rope       512 x 512: U = one lay length (0.105 m) along the rope, V = once round the rope. UNIQUE to this kit.
(f1: the per-prop weathering masks T_DKP_Train_<Prop>_Mask are baked by build_training_props.py on UV1.)

Run with Blender's bundled Python (numpy included):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/props/training/make_training_textures.py
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "Exports" / "DojoKit" / "Props" / "training" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "training"
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None

# Base colours (sRGB). Style guide 3: weathered dark timber #3A2E26. The training-props sheet reads warmer and a little
# lighter under its soft studio light (measured lit wood p50 about #5A4538), so the albedo sits between the two.
TIMBER_BASE = "#52361F"
TIMBER_DARK = "#1A110A"
TIMBER_WORN = "#96683F"
IRON_BASE = "#3B3733"
RUST = "#5C3B26"
ROPE_BASE = "#8A6A48"   # straw rope; sheet lit rope p50 #946D48


# --------------------------------------------------------------------------- helpers (copied from the armory kit)

def write_png(path, rgb):
    """8-bit RGB PNG writer (zlib only)."""
    a = np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
    h, w, ch = a.shape
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if ch == 4 else 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def pnoise(h, w, beta, seed, stretch_u=1.0, stretch_v=1.0):
    """Periodic 1/f^beta noise, zero mean, unit std. stretch_u > 1 suppresses variation along U (columns), so the
    features run long along U (the armory plank note f2)."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fv = np.fft.fftfreq(h)[:, None] * h / 256.0 * stretch_v
    fu = np.fft.fftfreq(w)[None, :] * w / 256.0 * stretch_u
    f = np.sqrt(fu * fu + fv * fv)
    f[0, 0] = 1.0
    F = F / np.power(f, beta)
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n - n.mean()) / (n.std() + 1e-9)


def srgb(hexstr):
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def lerp(a, b, t):
    t = np.asarray(t)[..., None]
    return a * (1 - t) + b * t


def normal_dx(height, strength):
    """Height (rows downward) to a DirectX tangent normal map (UE convention: green flipped from OpenGL)."""
    du = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dv_gl = -(np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    nx, ny, nz = -du * strength, -dv_gl * strength, np.ones_like(height)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    return np.dstack([nx * 0.5 + 0.5, -ny * 0.5 + 0.5, nz * 0.5 + 0.5])


def blur(a, r):
    """Periodic box blur (3 passes ~ gaussian) along both axes."""
    for _ in range(3):
        a = sum(np.roll(a, k, 0) for k in range(-r, r + 1)) / (2 * r + 1)
        a = sum(np.roll(a, k, 1) for k in range(-r, r + 1)) / (2 * r + 1)
    return a


def cavity_ao(height, r, k):
    """AO from the height field: how far a texel sits below its blurred neighbourhood."""
    d = height - blur(height, r)
    return np.clip(1.0 + k * np.minimum(d, 0) / (np.abs(d).max() + 1e-9), 0.0, 1.0)


def save_set(name, bc, height, nstrength, rough, ao, metal):
    OUT.mkdir(parents=True, exist_ok=True)
    bc = np.clip(bc, 0, 1)
    write_png(OUT / f"T_DKP_Train_{name}_BC.png", bc)
    write_png(OUT / f"T_DKP_Train_{name}_N.png", normal_dx(height, nstrength))
    metal = np.broadcast_to(np.asarray(metal, dtype=float), rough.shape)
    write_png(OUT / f"T_DKP_Train_{name}_ORM.png", np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1), metal]))
    # seam test: the step across the wrap (last column -> first, last row -> first) against the mean interior step
    lum = bc.mean(2)
    wrap_u = float(np.abs(lum[:, 0] - lum[:, -1]).mean())
    wrap_v = float(np.abs(lum[0, :] - lum[-1, :]).mean())
    inner = float(np.abs(np.diff(lum, axis=1)).mean() + np.abs(np.diff(lum, axis=0)).mean()) / 2
    return {"set": f"T_DKP_Train_{name}", "size": [bc.shape[1], bc.shape[0]],
            "mean_srgb": [round(float(x), 3) for x in bc.reshape(-1, 3).mean(0)],
            "mean_hex": "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in bc.reshape(-1, 3).mean(0)),
            "rough_mean": round(float(rough.mean()), 3), "metal_mean": round(float(metal.mean()), 3),
            "seam_step_u": round(wrap_u, 4), "seam_step_v": round(wrap_v, 4), "interior_step": round(inner, 4),
            "seamless": bool(max(wrap_u, wrap_v) < 2.5 * inner + 1e-3)}


# --------------------------------------------------------------------------- timber (side grain)

def scratches(n, rng, count, len_rng, ang_sd, w_px):
    """Periodic thin scratch lines, mostly along U (the grain) with a small angular spread: a 0..1 mask."""
    m = np.zeros((n, n), np.float32)
    for _ in range(count):
        r0, c0 = rng.integers(0, n, 2)
        L = int(rng.uniform(*len_rng) * n)
        ang = rng.normal(0, ang_sd)
        t = np.arange(L)
        rr = (r0 + np.round(np.tan(ang) * t + np.cumsum(rng.normal(0, 0.08, L)))).astype(int) % n
        cc = (c0 + t) % n
        a = rng.uniform(0.5, 1.0) * np.clip(np.sin(np.pi * t / max(L - 1, 1)), 0, 1) ** 0.5
        m[rr, cc] = np.maximum(m[rr, cc], a)
        if w_px > 1:
            m[(rr + 1) % n, cc] = np.maximum(m[(rr + 1) % n, cc], a * 0.5)
    return m


def timber(n=1024, seed=901):
    """Weathered dark timber, grain along U, tile 2.0 m at 1024 px = 5.12 px/cm (STYLE_GUIDE 6). f1 weathering pass:
    darker, less orange, denser flat-sawn grain (70 lines per tile), raised grain (latewood proud), many fine
    scratches along the grain and a few across, grime packed into the grooves and checks, and much weaker large-scale
    blotching so every member reads the same tone (the f1 judge saw per-member tone jumps)."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:n, 0:n].astype(np.float32) / n
    warp = 0.022 * pnoise(n, n, 2.6, seed + 1, stretch_u=6.0) + 0.006 * pnoise(n, n, 1.8, seed + 2, stretch_u=14.0)
    lines = 70   # grain lines per 2 m tile across the grain (2.9 cm average spacing)
    drift = 1.8 * pnoise(n, n, 2.2, seed + 6, stretch_u=30.0)
    ph = (v + warp) * lines + drift
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    late = np.power(ring, 3.0) * np.clip(0.55 + 0.45 * pnoise(n, n, 1.8, seed + 8, stretch_u=20.0), 0.1, 1.0)
    fibre = pnoise(n, n, 0.6, seed + 3, stretch_u=60.0)
    fibre2 = pnoise(n, n, 1.0, seed + 7, stretch_u=35.0)
    streak = pnoise(n, n, 1.4, seed + 4, stretch_u=25.0)
    blotch = pnoise(n, n, 2.4, seed + 5, stretch_u=3.0)
    crack = np.zeros((n, n), np.float32)
    for _ in range(260):
        r0, c0 = rng.integers(0, n, 2)
        L = int(rng.uniform(0.02, 0.20) * n)
        wmax = rng.uniform(0.6, 1.8)
        t = np.linspace(0, 1, L)
        width = wmax * np.sin(np.pi * t) ** 0.7
        wander = np.cumsum(rng.normal(0, 0.18, L))
        cc = (c0 + np.arange(L)) % n
        for k in range(-2, 3):
            rr = (r0 + np.round(wander).astype(int) + k) % n
            crack[rr, cc] = np.maximum(crack[rr, cc], np.clip(width - abs(k), 0, 1))
    crack = np.clip(blur(crack, 1) * 1.8, 0, 1)
    scr_along = scratches(n, rng, 900, (0.01, 0.06), 0.04, 1)          # raised-grain scratches along the grain
    scr_across = scratches(n, rng, 160, (0.004, 0.02), 0.9, 1)          # knocks and scuffs at random angles
    knot = np.zeros((n, n), np.float32)
    for _ in range(6):
        kv, ku = rng.uniform(0, 1, 2)
        ru, rv = rng.uniform(0.008, 0.014), rng.uniform(0.004, 0.007)
        dv = (v - kv + 0.5) % 1.0 - 0.5
        du = (u - ku + 0.5) % 1.0 - 0.5
        d = np.sqrt((du / ru) ** 2 + (dv / rv) ** 2)
        knot = np.maximum(knot, np.clip(1.3 - d, 0, 1) * (0.7 + 0.3 * np.cos(d * 9.0)))
    # high-frequency wear only (the low-frequency blotch is kept small so members match)
    wear = np.clip(0.5 + 0.5 * np.tanh(1.5 * streak + 0.8 * fibre2 + 0.2 * blotch), 0, 1)
    col = lerp(srgb(TIMBER_BASE)[None, None, :] * np.ones((n, n, 1)), srgb(TIMBER_WORN), 0.62 * wear ** 1.8)
    col = col * (1.0 + 0.08 * fibre + 0.10 * fibre2 + 0.06 * streak + 0.03 * blotch)[..., None]
    dark_streak = np.clip(-(streak + 0.5 * fibre2) - 0.5, 0, 1)
    col = lerp(col, srgb(TIMBER_DARK), np.clip(0.42 * late + 0.22 * dark_streak, 0, 1))
    col = lerp(col, srgb(TIMBER_WORN) * 1.15, np.clip(0.55 * scr_along * (1 - late), 0, 1))   # light raised fibres
    col = lerp(col, srgb("#6E6358"), np.clip(0.45 * scr_across, 0, 1))                      # grey scuffs
    # pits and flecks: short dark dashes along the grain (the sheet's wood is peppered with them)
    fleck = scratches(n, rng, 1400, (0.002, 0.008), 0.05, 2)
    col = lerp(col, srgb("#120E0B"), np.clip(crack * 0.95 + knot * 0.6 + 0.25 * scr_along * late + 0.7 * fleck, 0, 1))
    grey = col.mean(2, keepdims=True) * np.array([1.02, 1.0, 0.97])
    col = lerp(col, grey, 0.02)                                                             # weathered: less orange
    height = (0.012 * late + 0.004 * fibre + 0.003 * fibre2 + 0.002 * streak - 0.030 * crack - 0.004 * knot
              + 0.004 * scr_along - 0.004 * scr_across - 0.010 * fleck)
    rough = 0.74 + 0.05 * np.tanh(fibre) + 0.06 * (1 - late) + 0.12 * crack + 0.04 * wear
    ao = cavity_ao(height, 3, 0.9) * (1 - 0.35 * crack)
    return save_set("Timber", col, height, 20.0, rough, ao, 0.0)


# --------------------------------------------------------------------------- timber end grain

def timber_end(n=512, seed=911):
    """End grain, tile 0.5 m: growth rings as arcs of a far-off pith (periodic warped stripes), radial checks, darker
    and rougher than side grain (end grain soaks up grime)."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:n, 0:n].astype(np.float32) / n
    bend = 0.10 * np.sin(2 * np.pi * u) + 0.03 * np.sin(4 * np.pi * u + 1.3)
    wob = 0.012 * pnoise(n, n, 2.2, seed + 1)
    rings = 44   # 2.3 cm per ring over the 1.0 m tile (512 px = 5.12 px/cm)
    ph = (v + bend + wob) * rings
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    late = np.power(ring, 5.0)
    pores = pnoise(n, n, 0.6, seed + 2)
    mott = pnoise(n, n, 2.0, seed + 3)
    crack = np.zeros((n, n), np.float32)
    for _ in range(18):   # radial checks: short lines roughly perpendicular to the rings
        c0, r0 = rng.integers(0, n, 2)
        L = int(rng.uniform(0.06, 0.18) * n)
        ang = rng.uniform(-0.35, 0.35)
        t = np.arange(L)
        rr = (r0 + t).astype(int) % n
        cc = (c0 + np.round(np.tan(ang) * t)).astype(int) % n
        w = 1.8 * np.sin(np.pi * t / L) ** 0.6
        for k in range(-2, 3):
            crack[rr, (cc + k) % n] = np.maximum(crack[rr, (cc + k) % n], np.clip(w - abs(k), 0, 1))
    crack = np.clip(blur(crack, 1) * 1.7, 0, 1)
    base = srgb("#4E3624")
    col = base[None, None, :] * (1.0 + 0.10 * pores + 0.10 * mott)[..., None]
    col = lerp(col, srgb("#2B2019"), np.clip(0.6 * late, 0, 1))
    col = lerp(col, srgb("#16110D"), crack)
    height = (0.3 * (1 - late) + 0.1 * pores) * 0.02 - 0.08 * crack
    rough = 0.84 + 0.05 * np.tanh(pores) + 0.08 * crack
    ao = cavity_ao(height, 3, 0.8) * (1 - 0.4 * crack)
    return save_set("TimberEnd", col, height, 4.0, rough, ao, 0.0)


# --------------------------------------------------------------------------- iron

def iron(n=512, seed=921):
    """Dark forged iron, tile 0.5 m: hammer dimples, fine pitting, a little brown rust in patches and a dull mill
    scale. Metallic 0.9 on clean iron, 0.2 on rust."""
    v, u = np.mgrid[0:n, 0:n].astype(np.float32) / n
    ham = pnoise(n, n, 2.8, seed)
    pit = pnoise(n, n, 0.4, seed + 1)
    rustn = pnoise(n, n, 2.0, seed + 2) + 0.35 * pnoise(n, n, 1.0, seed + 3)
    rust = np.clip((rustn - 1.5) * 1.2, 0, 1) * np.clip(0.5 + 0.5 * pnoise(n, n, 0.9, seed + 6), 0, 1)
    scale = pnoise(n, n, 1.6, seed + 4)
    col = srgb(IRON_BASE)[None, None, :] * (1.0 + 0.10 * scale + 0.05 * pit)[..., None]
    col = lerp(col, srgb(RUST), 0.85 * rust)
    pits = np.clip(-(pit - 1.8), 0, 1)
    pits = (pit < -1.9).astype(np.float32)
    col = lerp(col, srgb("#161514"), 0.6 * pits)
    height = 0.012 * ham - 0.004 * pits + 0.004 * rust * pnoise(n, n, 0.8, seed + 5)
    rough = 0.62 + 0.08 * np.tanh(scale) + 0.30 * rust + 0.1 * pits
    metal = 0.9 * (1 - rust) + 0.2 * rust
    ao = cavity_ao(height, 3, 0.5)
    return save_set("Iron", col, height, 3.0, rough, ao, metal)


# --------------------------------------------------------------------------- rope

def rope(n=512, seed=931):
    """Three-strand straw rope. U = one lay length along the rope (0.12 m), V = once round the rope. Each strand
    runs diagonally (it makes one turn round the rope per lay length), so strand boundaries are the periodic lines
    frac(3 (v - u)) = 0. Fibres follow the strand direction; each strand has its own tint."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:n, 0:n].astype(np.float32) / n
    s = 3.0 * (v - u)
    strand = np.floor(s).astype(int) % 3
    f = s - np.floor(s)                     # 0..1 across one strand
    prof = np.sin(np.pi * f) ** 0.5          # rounded strand (the mesh carries the same lobes)
    # fibres: noise sheared along the strand direction (periodic: the shear is a whole number of tiles)
    fib = pnoise(n, n, 0.9, seed + 1, stretch_v=40.0)
    rows = np.arange(n)
    sheared = np.empty_like(fib)
    for r in range(n):
        sheared[r] = np.roll(fib[r], r)       # shift row r by r columns: vertical streaks become the u = v strand lay
    fib = sheared
    coarse = pnoise(n, n, 1.4, seed + 2)
    tint = np.array([0.0, 0.06, -0.05])[strand]
    # f1: loose straw hairs crossing the strands at random angles (the sheet's rope is rough and fibrous)
    hair = scratches(n, rng, 1500, (0.03, 0.14), 0.7, 1)
    hair = np.maximum(hair, np.roll(scratches(n, rng, 1100, (0.03, 0.12), 0.7, 1).T, 0, 0))
    dhair = scratches(n, rng, 900, (0.02, 0.10), 0.8, 1)          # dark weathered fibres
    base = srgb(ROPE_BASE)
    col = base[None, None, :] * (0.84 + 0.18 * prof + 0.26 * fib + 0.12 * coarse + tint)[..., None]
    # straw: lighter golden fibres on the crowns, grey-brown grime in the valleys, weathered grey patches
    col = lerp(col, srgb("#C9A874"), np.clip(0.35 * (fib - 0.6), 0, 0.45) * prof)
    col = lerp(col, srgb("#D2B480"), 0.75 * hair)
    col = lerp(col, srgb("#352819"), np.clip(np.clip(1 - prof, 0, 1) ** 3 * 0.40 + 0.45 * dhair, 0, 1))
    col = lerp(col, col.mean(2, keepdims=True) * np.array([1.05, 1.0, 0.9]), 0.25 * np.clip(coarse, 0, 1))
    height = 1.0 * prof + 0.30 * fib + 0.05 * coarse + 0.25 * hair
    rough = 0.86 + 0.06 * np.tanh(fib)
    ao = np.clip(0.45 + 0.55 * prof ** 0.5, 0, 1)
    return save_set("Rope", col, height, 22.0, rough, ao, 0.0)


def main():
    report = {}
    for name, fn in (("Timber", timber), ("TimberEnd", timber_end), ("Iron", iron), ("Rope", rope)):
        if ONLY and name not in ONLY:
            continue
        report[name] = fn()
        print(name, report[name])
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / "textures_report.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(report)
    path.write_text(json.dumps(old, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()



