"""Seamless tiling textures for the armory gallery kit (lean path: tiling sets, no trim bake).

Every map is generated from periodic FFT noise, so every tile repeats with no seam. Writes PNGs to
Exports/ArmoryKit/Textures/: T_AK_<Set>_BC (sRGB), T_AK_<Set>_N (DirectX green, linear),
T_AK_<Set>_ORM (AO, roughness, metal; linear). All original and procedural: no photo, scan or third-party source.

Run with Blender's bundled Python (numpy is included):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/make_armory_textures.py
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Exports" / "ArmoryKit" / "Textures"


def write_png(path, rgb):
    """8-bit RGB PNG writer (zlib only), so no imaging library is needed."""
    a = np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
    h, w, ch = a.shape
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    # building stage: RGBA (colour type 6) for the alpha-masked plum-branch cards, RGB (2) otherwise
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if ch == 4 else 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def pnoise(h, w, beta, seed, stretch_u=1.0, stretch_v=1.0, fmin=0.0):
    """Periodic 1/f^beta noise, zero mean, unit std. stretch_u < 1 elongates features along U (columns)."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fv = np.fft.fftfreq(h)[:, None] * h / 256.0 * stretch_v
    fu = np.fft.fftfreq(w)[None, :] * w / 256.0 * stretch_u
    f = np.sqrt(fu * fu + fv * fv)
    f[0, 0] = 1.0
    F = F / np.power(f, beta)
    if fmin > 0:
        F[f < fmin] = 0
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n - n.mean()) / (n.std() + 1e-9)


def srgb(hexstr):
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def normal_dx(height, strength):
    """Height (0-1-ish, rows downward) to a DirectX tangent normal map (UE convention)."""
    du = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dv_gl = -(np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5  # +v is up in GL, rows go down
    nx, ny, nz = -du * strength, -dv_gl * strength, np.ones_like(height)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    return np.dstack([nx * 0.5 + 0.5, -ny * 0.5 + 0.5, nz * 0.5 + 0.5])  # DX: green flipped


def save_set(name, bc, height, nstrength, rough, ao=None, metal=0.0):
    OUT.mkdir(parents=True, exist_ok=True)
    write_png(OUT / f"T_AK_{name}_BC.png", np.clip(bc, 0, 1))
    write_png(OUT / f"T_AK_{name}_N.png", normal_dx(height, nstrength))
    ao = np.ones_like(rough) if ao is None else ao
    write_png(OUT / f"T_AK_{name}_ORM.png", np.dstack([ao, np.clip(rough, 0.02, 1), np.full_like(rough, metal)]))
    return {"set": name, "size": list(bc.shape[:2]), "mean_srgb": [round(float(x), 3) for x in bc.reshape(-1, 3).mean(0)],
            "rough_mean": round(float(rough.mean()), 3)}


def plank(n=2048, boards=20, seed=11):
    """Dark walnut floor planks, boards run along U (the kit maps U to the room axis). Tile = 4 m (5.12 px/cm).
    look pass 2 (2026-09-27): long, narrow boards (28 across = 14.3 cm), 1-2 staggered butt joints per 4 m board run,
    a cooler walnut than fix1 (less orange), satin-gloss. The floor pieces come in four UV-offset variants that tile the
    4 m period across a 2 x 2 checker of 2 m pieces, so the whole 4 m tile shows and no 2 m piece repeats its neighbour."""
    rng = np.random.default_rng(seed)
    # f1 (blind judge delta 9: the floor read as short parquet tiles): the low-frequency blotches that broke each board
    # into short light/dark lengths are much weaker and longer (stretch 0.04 -> 0.012), a fine linear grain carries the
    # wood, the board-to-board tint is gentler, the base darker, and every board has a single long butt joint
    # f2 (blind judge blocker 2 / delta 3: "short, narrow boards in a brick pattern that read as small tiles"): the grain
    # ran ACROSS the boards. pnoise's stretch_u multiplies the U frequency, so a value < 1 keeps the fast U variation
    # (features long along V, i.e. across the boards); > 1 suppresses it (features long along U, the board direction).
    # The grain, fine grain and streaks now run along the boards (stretch_u 80 / 50 / 100, were 0.012 / 0.02 / 0.01);
    # 20 boards across the 4 m tile = 20 cm wide boards (were 28 = 14.3 cm), 4 m long with one staggered butt joint;
    # a stronger board-to-board tint; a redder, slightly lighter walnut; glossier (roughness 0.16, was 0.22)
    grain = pnoise(n, n, 1.6, seed, stretch_u=80.0)
    fine = pnoise(n, n, 0.9, seed + 1, stretch_u=50.0)
    streak = pnoise(n, n, 0.5, seed + 2, stretch_u=100.0)
    rows = np.arange(n)
    edges = np.round(np.arange(boards + 1) * n / boards).astype(int)
    board_id = np.searchsorted(edges, rows, side="right") - 1
    tint = rng.normal(0, 0.08, boards)
    shift = rng.integers(0, n, boards)
    g = np.empty_like(grain)
    for b in range(boards):
        r0, r1 = edges[b], edges[b + 1]
        g[r0:r1] = np.roll(grain[r0:r1], shift[b], axis=1)
    base = srgb("#3B2E24")   # look3: golden walnut. #352A29 had G = B, which read mauve-pink under warm light;
    # reference 2 shaded floor measures sRGB (0.48, 0.36, 0.27): B < G < R   # f2: a dark walnut, a touch redder but less saturated than f1 (reference 2's shaded floor
    # reads mauve-brown, saturation 0.14-0.18) (f1 #322823; was #3F3129; building stage #30231C)
    lum = 1.0 + 0.10 * g + 0.06 * fine + 0.06 * streak + tint[board_id][:, None]
    bc = base[None, None, :] * lum[..., None]
    seam = np.zeros((n, n))
    for e in edges[:-1]:
        for d, k in ((0, 1.0), (1, 0.5)):
            seam[(e + d) % n, :] = np.maximum(seam[(e + d) % n, :], k)
    for b in range(boards):   # staggered butt joints: every board gets 1 or 2 over the 4 m run
        r0, r1 = edges[b], edges[b + 1]
        k = 1
        start = (b * 0.37 + rng.uniform(-0.06, 0.06)) % 1.0
        for j in range(k):
            col = int(((start + j / k) % 1.0) * n)
            for d, w in ((0, 1.0), (1, 0.5)):
                seam[r0:r1, (col + d) % n] = np.maximum(seam[r0:r1, (col + d) % n], w)
    bc *= (1 - 0.6 * seam)[..., None]
    height = 0.35 * g * 0.02 - 0.9 * seam * 0.06
    rough = 0.16 + 0.04 * np.tanh(fine) + 0.3 * seam
    ao = 1 - 0.35 * seam
    return save_set("Plank", bc, height, 6.0, rough, ao)


def backdrop(w=2048, h=1024, seed=71):
    """Sunlit garden seen through the windows: out-of-focus foliage masses under a bright warm sky. Used on an
    emissive backdrop card outside the walls (no shadows). Unique UV over the card."""
    v, u = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    canopy_top = 0.28 + 0.12 * pnoise(1, w, 1.8, seed)[0] * 0.5 + 0.06 * np.sin(u[0] * 9.0)
    foliage = pnoise(h, w, 1.5, seed + 1)
    blobs = pnoise(h, w, 2.4, seed + 2)
    in_trees = (v > canopy_top[None, :] + 0.08 * blobs).astype(float)
    sky = np.dstack([np.full((h, w), 1.0), 0.86 - 0.12 * v, 0.62 - 0.22 * v])
    leaf_lo, leaf_mid, leaf_hi = srgb("#1C2A12"), srgb("#5E7A2C"), srgb("#E8D98A")
    t = np.clip(0.45 + 0.30 * foliage, 0, 1)[..., None]
    leaves = leaf_lo * (1 - t) + leaf_mid * t
    sunlit = np.clip((pnoise(h, w, 1.1, seed + 3) - 0.6) * 1.8, 0, 1)[..., None] * (1 - 0.6 * v[..., None])
    leaves = leaves * (1 - sunlit) + leaf_hi * sunlit            # sun-struck leaf masses
    holes = np.clip((pnoise(h, w, 1.3, seed + 4) - 1.2) * 3, 0, 1)[..., None] * (v[..., None] < 0.7)
    leaves = leaves * (1 - holes) + sky * holes                  # sky showing through the canopy
    trunks = np.zeros((h, w))
    rng = np.random.default_rng(seed)
    for cx in rng.uniform(0, 1, 7):
        wdt = rng.uniform(0.006, 0.014)
        trunks = np.maximum(trunks, np.clip(1 - np.abs(u - cx - 0.03 * (v - 1)) / wdt, 0, 1) * (v > 0.55))
    leaves = leaves * (1 - 0.8 * trunks[..., None]) + srgb("#151009") * 0.8 * trunks[..., None]
    col = sky * (1 - in_trees[..., None]) + leaves * in_trees[..., None]
    # soften (out of focus): box blurs, periodic along U only (no wrap in V)
    for _ in range(4):
        pad = np.concatenate([col[:3], col, col[-3:]], 0)
        col = (col + np.roll(col, 3, 1) + np.roll(col, -3, 1) + pad[:-6] + pad[6:]) / 5.0
    OUT.mkdir(parents=True, exist_ok=True)
    write_png(OUT / "T_AK_Backdrop_BC.png", np.clip(col, 0, 1))
    return {"set": "Backdrop", "size": [h, w], "mean_srgb": [round(float(x), 3) for x in col.reshape(-1, 3).mean(0)]}


def timber(n=2048, seed=21):
    """Near-black timber, grain along U (the kit maps U to each member's long axis). Tile = 2 m (10.24 px/cm)."""
    grain = pnoise(n, n, 1.5, seed, stretch_u=0.04)
    fine = pnoise(n, n, 0.8, seed + 1, stretch_u=0.06)
    mottle = pnoise(n, n, 2.2, seed + 2)
    base = srgb("#221C18")   # building stage: less saturated near-black (was #241B15)
    lum = 1.0 + 0.20 * grain + 0.06 * fine + 0.06 * mottle
    bc = base[None, None, :] * lum[..., None]
    height = 0.5 * grain * 0.02 + 0.2 * fine * 0.01
    rough = 0.52 + 0.05 * np.tanh(fine) - 0.04 * np.tanh(mottle)
    return save_set("Timber", bc, height, 5.0, rough)


def plaster(n=2048, seed=31):
    """Warm cream plaster (albedo under the 0.80 cap). Tile = 2 m."""
    mottle = pnoise(n, n, 2.4, seed)
    trowel = pnoise(n, n, 1.3, seed + 1, stretch_u=0.25, stretch_v=1.0)
    grit = pnoise(n, n, 0.4, seed + 2)
    base = srgb("#DCCDAF")
    lum = 1.0 + 0.035 * mottle + 0.015 * trowel + 0.012 * grit
    bc = np.minimum(base[None, None, :] * lum[..., None], 0.80)
    height = 0.03 * trowel + 0.01 * grit
    rough = 0.86 + 0.03 * np.tanh(trowel)
    return save_set("Plaster", bc, height, 3.0, rough)


def mat(w=2048, h=1024, seed=41):
    """Woven entry mat with a dark cloth border; unique UV over 150 x 90 cm."""
    v, u = np.mgrid[0:h, 0:w]
    weave = 0.5 + 0.5 * np.sin(2 * np.pi * v / 6.0)
    alt = ((u // 24 + v // 6) % 2) * 0.08
    fib = pnoise(h, w, 0.7, seed, stretch_u=0.1)
    base = srgb("#7F7157")
    lum = 0.82 + 0.22 * weave - alt + 0.04 * fib
    bc = base[None, None, :] * lum[..., None]
    border_u, border_v = int(w * 0.055), int(h * 0.09)
    border = (u < border_u) | (u >= w - border_u) | (v < border_v) | (v >= h - border_v)
    bc[border] = srgb("#2A2420") * (1 + 0.05 * fib[border])[:, None]
    height = 0.04 * weave + 0.01 * fib
    rough = np.where(border, 0.8, 0.75)
    return save_set("Mat", bc, height, 4.0, rough)


def ground(n=2048, seed=51):
    """Exterior packed earth and fine gravel outside the door. Tile = 4 m."""
    lo = pnoise(n, n, 2.2, seed)
    mid = pnoise(n, n, 1.2, seed + 1)
    grit = pnoise(n, n, 0.3, seed + 2)
    base = srgb("#6A6154")
    lum = 1.0 + 0.10 * lo + 0.07 * mid + 0.08 * np.tanh(grit * 1.5)
    bc = base[None, None, :] * lum[..., None]
    height = 0.05 * mid + 0.04 * grit
    rough = 0.88 + 0.04 * np.tanh(grit)
    return save_set("Ground", bc, height, 4.0, rough)


def painting(n=2048, seed=61):
    """Original ink-wash mountains in mist on washi, for the 2.4 x 1.8 m panel. No text, no seal, no signature."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:n, 0:n] / n  # v: 0 top .. 1 bottom
    fib = pnoise(n, n, 0.9, seed, stretch_u=0.3)
    paper = srgb("#E3D6BA")
    ink = np.zeros((n, n))

    def fbm1d(x, octaves, s):
        r = np.random.default_rng(s)
        y = np.zeros_like(x)
        amp, freq = 1.0, 2.0
        for _ in range(octaves):
            ph = r.uniform(0, 2 * np.pi, 3)
            y += amp * (np.sin(2 * np.pi * freq * x + ph[0]) * 0.6 + np.sin(2 * np.pi * freq * 1.7 * x + ph[1]) * 0.4)
            amp *= 0.5
            freq *= 2.1
        return y

    x = u[0]

    def peaks(specs, detail_seed, detail_amp):
        """A ridge line from a few broad peaks (centre, height, width) plus fine craggy detail."""
        y = np.zeros_like(x)
        for c, hgt, wid in specs:
            y = np.maximum(y, hgt * np.exp(-((x - c) / wid) ** 2))
        return y + detail_amp * np.abs(fbm1d(x, 7, detail_seed)) * (0.3 + y / max(s[1] for s in specs))

    # far to near: (peak specs, ridge baseline from top, ink darkness, mist fade, detail seed)
    layers = [
        ([(0.62, 0.30, 0.10), (0.78, 0.22, 0.07), (0.40, 0.16, 0.09), (0.95, 0.12, 0.06)], 0.62, 0.20, 0.10, 101),
        ([(0.72, 0.18, 0.06), (0.50, 0.12, 0.08), (0.88, 0.10, 0.05), (0.25, 0.07, 0.08)], 0.72, 0.36, 0.07, 102),
        ([(0.82, 0.10, 0.07), (0.60, 0.06, 0.06), (0.35, 0.05, 0.10)], 0.84, 0.55, 0.05, 103),
    ]
    for specs, base, dark, fade, s in layers:
        ridge = base - peaks(specs, s, 0.012)
        below = v - ridge[None, :]
        body = np.where(below > 0, np.exp(-below / fade), 0.0)          # ink fades down into mist
        edge = np.exp(-np.abs(below) / 0.003) * 0.4 * (below > -0.003)  # a crisper brush line on the ridge
        tex = 0.8 + 0.2 * pnoise(n, n, 1.4, s)
        ink = 1 - (1 - ink) * (1 - np.clip((body + edge) * dark * tex, 0, 1))

    def stroke(points, r0, r1, soft=0.003):
        """A tapering brush stroke along a polyline (u, v points), radius r0 at the start to r1 at the end."""
        pts = np.array(points, dtype=float)
        seg = np.linspace(0, 1, 300)
        cu = np.interp(seg, np.linspace(0, 1, len(pts)), pts[:, 0])
        cv = np.interp(seg, np.linspace(0, 1, len(pts)), pts[:, 1])
        out = np.zeros((n, n))
        for pu, pv, t in zip(cu, cv, seg):
            r = r0 + (r1 - r0) * t
            lo_u, hi_u = int(max(0, (pu - r - 0.01) * n)), int(min(n, (pu + r + 0.01) * n))
            lo_v, hi_v = int(max(0, (pv - r - 0.01) * n)), int(min(n, (pv + r + 0.01) * n))
            d = np.sqrt((u[lo_v:hi_v, lo_u:hi_u] - pu) ** 2 + (v[lo_v:hi_v, lo_u:hi_u] - pv) ** 2)
            out[lo_v:hi_v, lo_u:hi_u] = np.maximum(out[lo_v:hi_v, lo_u:hi_u], np.clip((r - d) / soft, 0, 1))
        return out

    # an old pine rising from the lower left, leaning right; branches reach out and carry flat needle pads
    trunk_pts = [(0.06, 1.02), (0.12, 0.86), (0.15, 0.72), (0.13, 0.60), (0.18, 0.48), (0.24, 0.40), (0.30, 0.36)]
    dry = 0.75 + 0.25 * np.clip(pnoise(n, n, 0.6, 300, stretch_u=0.2), -1, 1)  # dry-brush streaks
    wood = stroke(trunk_pts, 0.030, 0.010) * dry
    branches = [((0.15, 0.70), (0.30, 0.64), (0.40, 0.66)), ((0.14, 0.62), (0.05, 0.56)),
                ((0.18, 0.49), (0.32, 0.46), (0.44, 0.47)), ((0.24, 0.41), (0.36, 0.34)), ((0.30, 0.36), (0.22, 0.30))]
    pad_at = [(0.38, 0.655, 0.10), (0.06, 0.55, 0.07), (0.42, 0.465, 0.09), (0.36, 0.335, 0.08), (0.24, 0.295, 0.07),
              (0.29, 0.36, 0.06)]
    for b in branches:
        wood = np.maximum(wood, stroke(b, 0.009, 0.004) * dry)
    pads = np.zeros((n, n))
    for k, (cx, cy, rx) in enumerate(pad_at):
        ry = rx * 0.28
        e = ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2
        ragged = np.maximum(1 + 0.35 * pnoise(n, n, 0.9, 200 + k), 0.6)  # never <= 0, or specks appear everywhere
        body = np.clip((1.0 - e * ragged) * 5, 0, 1) * (e < 2.5)
        top_dark = np.clip(1.15 - (v - (cy - ry)) / (2 * ry) * 0.4, 0.8, 1.0)  # darker upper edge, as a brush loads
        pads = np.maximum(pads, body * top_dark * rng.uniform(0.88, 0.96))
    ink = 1 - (1 - ink) * (1 - 0.95 * wood) * (1 - pads)
    inkcol = srgb("#1E1B18")
    col = paper[None, None, :] * (1 + 0.03 * fib)[..., None]
    col = col * (1 - ink[..., None]) + inkcol[None, None, :] * ink[..., None]
    height = 0.02 * fib
    rough = 0.9 - 0.1 * ink
    return save_set("Painting", col, height, 2.0, rough)


# --------------------------------------------------------------------------- building stage (2026-09-27)
# The emblem is the USER'S OWN ORIGINAL DESIGN, recreated from their LOOK reference (armory3_reference2.png: the
# plinth-front medallion at about (725, 799) px and the two banner crests). Measured on a 16x upscale of the plinth
# crest (ring fitted by least squares, radius R = 18 px): a gold ring from 0.87 R to 1.0 R; five separate egg petals from
# 0.19 R to 0.74 R, widest (about 0.55 R) just outside 0.47 R, one petal pointing straight up, separated by dark
# gaps (at -90 + 72k deg) that widen toward the middle; a dark band from 0.10 R to 0.18 R; a small heart-shaped centre.

def emblem_field(x, y, ring=True):
    """True where the emblem is gold. x, y in emblem units (ring outer radius 1), y up."""
    r = np.hypot(x, y)
    out = np.zeros(x.shape, dtype=bool)
    if ring:
        out |= (r <= 1.0) & (r >= 0.87)
    for k in range(5):
        # each petal is a separate egg (wider at its outer end), centred at 0.455 R, radial semi-axis 0.285 (so it
        # spans 0.17-0.74 R), tangential semi-axis 0.255 at the centre: neighbours almost touch at the shoulders and the
        # dark gaps widen toward the middle, as on the reference crests
        a = np.radians(90 + 72 * k)
        s = x * np.cos(a) + y * np.sin(a)
        t = -x * np.sin(a) + y * np.cos(a)
        q = (s - 0.455) / 0.285
        half_w = 0.255 * (1.0 + 0.16 * q)   # min gap between neighbours 0.04 R (measured)
        out |= q * q + (t / half_w) ** 2 <= 1.0
    # the small heart-shaped centre, pointing down (about 0.18 R across)
    heart = ((x - 0.040) ** 2 + (y - 0.014) ** 2 <= 0.050 ** 2) | ((x + 0.040) ** 2 + (y - 0.014) ** 2 <= 0.050 ** 2)
    heart |= (y <= 0.014) & (y >= -0.098) & (np.abs(x) <= 0.087 * (y + 0.098) / 0.112)
    return out | heart


def raster(fn, w, h, x0, x1, y0, y1, ss=2):
    """Anti-aliased coverage of a boolean field over a w x h image spanning x0..x1 (columns) and y1..y0 (rows, top
    row = y1), by ss x ss supersampling."""
    xs = x0 + (np.arange(w * ss) + 0.5) / (w * ss) * (x1 - x0)
    ys = y1 - (np.arange(h * ss) + 0.5) / (h * ss) * (y1 - y0)
    cov = np.zeros((h, w))
    for r0 in range(0, h * ss, 512):   # row chunks keep the memory small
        yy, xx = np.meshgrid(ys[r0:r0 + 512], xs, indexing="ij")
        m = fn(xx, yy).astype(float)
        cov[r0 // ss:(r0 + m.shape[0]) // ss] = m.reshape(m.shape[0] // ss, ss, w, ss).mean((1, 3))
    return cov


def blur(a, radius, passes=3):
    for _ in range(passes):
        acc = np.zeros_like(a)
        for d in range(-radius, radius + 1):
            acc += np.roll(a, d, 0)
        a = acc / (2 * radius + 1)
        acc = np.zeros_like(a)
        for d in range(-radius, radius + 1):
            acc += np.roll(a, d, 1)
        a = acc / (2 * radius + 1)
    return a


GOLD = "#C9A057"


def emblem(n=2048, seed=81):
    """T_AK_Emblem (mask, 1 = gold), T_AK_Emblem_N (slight relief) and a ready gold-on-lacquer set T_AK_Emblem_BC /
    _ORM for the medallion discs. The texture spans -1.06..1.06 emblem units (a dark margin outside the ring), which
    is the full disc: UV = 0.5 + p / (2 * disc radius)."""
    E = 1.06
    m = raster(emblem_field, n, n, -E, E, -E, E, ss=2)
    OUT.mkdir(parents=True, exist_ok=True)
    write_png(OUT / "T_AK_Emblem.png", np.dstack([m] * 3))
    grain = pnoise(n, n, 1.0, seed)
    height = blur(m, 4) + 0.02 * grain * m
    gold, ground = srgb(GOLD), srgb("#15120F")
    bc = ground[None, None, :] * (1 - m[..., None]) + gold[None, None, :] * (1 + 0.05 * grain)[..., None] * m[..., None]
    rough = 0.20 * (1 - m) + (0.30 + 0.04 * np.tanh(grain)) * m
    rep = save_set("Emblem", bc, height, 3.0, rough, None, 0.0)
    orm = np.dstack([np.ones_like(m), np.clip(rough, 0.02, 1), m])   # metal = mask
    write_png(OUT / "T_AK_Emblem_ORM.png", orm)
    rep["gold_fraction"] = round(float(m.mean()), 4)
    return rep


def banner(w=512, h=2048, seed=91):
    """Tall black cloth banner (0.55 x 2.2 m, 931 px/m, square texels): the user's emblem in gold near the top and a
    pair of small gold blossom motifs near the hem (the reference's small lower marks; no lettering)."""
    W, H = 0.55, 2.2
    ex, ey, er = W / 2, H - 0.62, 0.20                 # crest centre 0.62 m below the top, 0.40 m across
    crest = raster(lambda x, y: emblem_field((x - ex) / er, (y - ey) / er), w, h, 0, W, 0, H)
    motif = np.zeros((h, w))
    for mx in (0.19, 0.36):   # two small blossoms (petals and centre, no ring) 0.30 m above the hem
        motif = np.maximum(motif, raster(lambda x, y: emblem_field((x - mx) / 0.045, (y - 0.30) / 0.045, ring=False),
                                         w, h, 0, W, 0, H))
    m = np.maximum(crest, motif)
    # f1: a thin gold edge line 2.5 cm in from the sides and the hem, so the black cloth reads as a banner against the
    # dark wall (the crest alone read as a wall medallion); no lettering
    xx = (np.arange(w)[None, :] + 0.5) / w * W
    yy = (h - np.arange(h)[:, None] - 0.5) / h * H
    inset, lw = 0.025, 0.008
    side = (np.abs(xx - inset) < lw / 2) | (np.abs(xx - (W - inset)) < lw / 2)
    hem = np.abs(yy - inset) < lw / 2
    border = ((side & (yy > inset - lw / 2) & (yy < H - 0.05)) | (hem & (xx > inset - lw / 2) & (xx < W - inset + lw / 2)))
    m = np.maximum(m, border.astype(float))
    weave = 0.5 + 0.5 * np.sin(np.arange(h)[:, None] * 2 * np.pi / 3.0) * np.sin(np.arange(w)[None, :] * 2 * np.pi / 3.0)
    fib = pnoise(h, w, 0.8, seed, stretch_u=0.3)
    cloth = srgb("#141312")[None, None, :] * (1 + 0.10 * weave + 0.06 * fib)[..., None]
    gold = srgb("#B8904A")[None, None, :] * (1 + 0.06 * fib)[..., None]
    bc = cloth * (1 - m[..., None]) + gold * m[..., None]
    height = 0.02 * weave + 0.5 * blur(m, 2)
    rough = 0.85 * (1 - m) + 0.45 * m
    rep = save_set("Banner", bc, height, 2.0, rough)
    write_png(OUT / "T_AK_Banner_ORM.png", np.dstack([np.ones_like(m), rough, 0.85 * m]))   # embroidered gold: metallic
    return rep


def plum(w=2048, h=2048, seed=101):
    """Red plum-blossom spray on an alpha-masked card (0.5 x 1.0 card units, 2048 px per unit): building r3, re-drawn
    from a zoom of reference 2's vases (about x 560-690, y 150-280): an ikebana bundle of nearly straight dark stems
    fanning up out of the vase mouth in a narrow V, small round red blossoms and buds strung along the upper two thirds
    of each stem, a few short side twigs, and one or two white-blossom stems leaning out to one side. RGBA.
    f2 (blind judge delta 7: "each window bay has a full, bushy red plum branch spray about 1.5x the vase height"; zoom of
    reference 2's near-left sill vase: the spray is about 1.7x the vase height tall and 2.5x as wide): a SQUARE card
    (1.0 x 1.0 units) and a wide round bush: 22 stems fanning +/-40 deg from the mouth, the outer ones shorter, 2-4
    blossoming twigs per stem, denser and larger blossoms, three white stems leaning out to the right."""
    rng = np.random.default_rng(seed)
    PX = 2048.0   # px per card unit
    col = np.zeros((h, w, 3))
    alpha = np.zeros((h, w))

    def splat(cx, cy, rad, colour, soft=1.2):
        x0, x1 = int(max(0, cx * PX - rad * PX - 3)), int(min(w, cx * PX + rad * PX + 3))
        y0, y1 = int(max(0, (1 - cy) * PX - rad * PX - 3)), int(min(h, (1 - cy) * PX + rad * PX + 3))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.hypot(xx + 0.5 - cx * PX, yy + 0.5 - (1 - cy) * PX)
        a = np.clip((rad * PX - d) / soft + 0.5, 0, 1)
        c = col[y0:y1, x0:x1]
        c[:] = c * (1 - a[..., None]) + np.asarray(colour) * a[..., None]
        alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], a)

    wood = srgb("#2A1D16")
    red, deep, white, eye = srgb("#C8161E"), srgb("#86101A"), srgb("#F2ECE2"), srgb("#E3B85A")

    def stem(x, y, ang, length, width):
        """A nearly straight stem with slight kinks; returns its sample points."""
        pts = [(x, y)]
        n = int(length / 0.03) + 1
        for i in range(n):
            ang += rng.normal(0, 0.035)
            x, y = x + 0.03 * np.cos(ang), y + 0.03 * np.sin(ang)
            pts.append((x, y))
        for i, ((ax, ay), (bx, by)) in enumerate(zip(pts, pts[1:])):
            wd = width * (1 - 0.6 * i / n)
            for t in np.linspace(0, 1, int(0.03 * PX / 1.5) + 1):
                splat(ax + (bx - ax) * t, ay + (by - ay) * t, max(wd, 0.0011), wood, 0.8)
        return pts

    def blossoms(pts, colour, start=0.30, step=0.022, big=(0.0080, 0.0120)):   # f1 / f2: bigger blossoms
        n = len(pts)
        for i in range(int(start * n), n):
            if rng.random() > 0.55:   # f2: airy clusters along many more stems (f1 0.92, was 0.75)
                continue
            x, y = pts[i]
            for _ in range(rng.integers(1, 3)):
                bx, by = x + rng.normal(0, 0.010), y + rng.normal(0, 0.008)
                if not (0.02 < bx < 0.98 and 0.02 < by < 0.98):
                    continue
                rad = rng.uniform(*big) * (0.75 if i > n - 3 else 1.0)
                if colour is white:
                    for k in range(5):
                        a = rng.uniform(0, 1) + k * 2 * np.pi / 5
                        splat(bx + 0.5 * rad * np.cos(a), by + 0.5 * rad * np.sin(a), rad * 0.5, white)
                    splat(bx, by, rad * 0.22, eye)
                elif rng.random() < 0.3:
                    splat(bx, by, rad * 0.6, deep)                            # a bud
                else:
                    splat(bx, by, rad, colour * rng.uniform(0.85, 1.08))   # a round red blossom
                    splat(bx + 0.2 * rad, by + 0.25 * rad, rad * 0.35, colour * 1.25)

    stems = []
    for k in range(22):   # f2: a wide round bush (was 13 stems in a narrow V)
        dev = rng.uniform(-40, 40)
        ang = np.radians(90 + dev)
        length = rng.uniform(0.55, 0.86) * (1 - 0.35 * abs(dev) / 40)
        pts = stem(0.5 + rng.uniform(-0.008, 0.008), 0.0, ang, length, 0.0050)
        stems.append(pts)
        for _ in range(rng.integers(2, 5)):   # blossoming side twigs off the upper two thirds
            j = rng.integers(len(pts) // 3, len(pts) - 1)
            tw = stem(pts[j][0], pts[j][1], ang + rng.choice([-1, 1]) * rng.uniform(0.35, 0.8),
                      rng.uniform(0.06, 0.16), 0.0024)
            stems.append(tw)
    for pts in stems:
        blossoms(pts, red)
    for k in range(3):   # white-blossom stems leaning to the right
        pts = stem(0.5, 0.0, np.radians(rng.uniform(40, 58)), rng.uniform(0.45, 0.62), 0.0038)
        blossoms(pts, white, start=0.40, big=(0.007, 0.010))
    OUT.mkdir(parents=True, exist_ok=True)
    write_png(OUT / "T_AK_Plum_BC.png", np.dstack([np.clip(col, 0, 1), alpha]))
    write_png(OUT / "T_AK_Plum_N.png", normal_dx(np.zeros((h, w)), 1.0))
    write_png(OUT / "T_AK_Plum_ORM.png", np.dstack([np.ones((h, w)), np.full((h, w), 0.65), np.zeros((h, w))]))
    return {"set": "Plum", "size": [h, w], "alpha_coverage": round(float(alpha.mean()), 4)}


def lantern_paper(n=512, seed=121):
    """f2 (reference 2's floor lanterns, zoomed: the paper burns near white in the middle and falls off to deep amber at the
    frame): one lantern paper panel, UV 0-1 over the pane (U across, V up). An emissive picture (the kit material is
    unlit emit_image: the colour IS the glow): a hot cream core just above the middle (the lamp sits at +0.36 of the
    0.70 m lantern, 0.56 up the pane), falling off to amber and a dark amber rim; faint paper fibres. BC + flat N / ORM."""
    v, u = (np.mgrid[0:n, 0:n] + 0.5) / n
    v = 1 - v                                               # rows run down; V up
    fib = pnoise(n, n, 0.8, seed, stretch_u=0.25)
    d = np.sqrt(((u - 0.5) / 0.55) ** 2 + ((v - 0.56) / 0.70) ** 2)
    glow = np.exp(-2.4 * d * d)
    hot, mid, rim = srgb("#FFF1D6"), srgb("#F2A548"), srgb("#8A4A12")
    t = np.clip(glow, 0, 1)[..., None]
    col = np.where(t > 0.5, mid + (hot - mid) * np.clip((t - 0.5) / 0.5, 0, 1) ** 1.2,
                   rim + (mid - rim) * np.clip(t / 0.5, 0, 1) ** 0.9)
    col = col * (1 + 0.04 * fib)[..., None]
    OUT.mkdir(parents=True, exist_ok=True)
    write_png(OUT / "T_AK_LanternPaper_BC.png", np.clip(col, 0, 1))
    write_png(OUT / "T_AK_LanternPaper_N.png", normal_dx(0.004 * fib, 1.0))
    write_png(OUT / "T_AK_LanternPaper_ORM.png", np.dstack([np.ones((n, n)), np.full((n, n), 0.9), np.zeros((n, n))]))
    return {"set": "LanternPaper", "size": [n, n], "mean_srgb": [round(float(x), 3) for x in col.reshape(-1, 3).mean(0)]}


def runner(w=1024, h=2048, seed=43):
    """Building stage: the woven rush runner on the entry axis (reference 2): a fine basket weave with a dark cloth
    border, 1.6 x 3.4 m, unique UV (U across, V along the axis)."""
    v, u = np.mgrid[0:h, 0:w]
    cell = 12   # ~2 cm weave cells
    horiz = ((u // cell + v // cell) % 2) == 0
    phase = np.where(horiz, v % cell, u % cell) / cell
    strand = 0.55 + 0.45 * np.sin(np.pi * phase) ** 0.6
    fib = pnoise(h, w, 0.7, seed, stretch_u=0.1)
    base = srgb("#54483A")   # building r4: darker rush (reference 2's runner reads mid grey-brown); f1: #6F5F45 -> #54483A
    lum = 0.70 + 0.34 * strand + 0.05 * fib - 0.10 * (~horiz)
    bc = base[None, None, :] * lum[..., None]
    bu, bv = int(w * 0.035), int(h * 0.017)
    border = (u < bu) | (u >= w - bu) | (v < bv) | (v >= h - bv)
    inner = ((u >= bu) & (u < bu + 4)) | ((u < w - bu) & (u >= w - bu - 4))
    bc[border] = srgb("#1C1916") * (1 + 0.05 * fib[border])[:, None]
    bc[inner] = srgb("#5A4A36")
    height = 0.05 * strand + 0.01 * fib
    rough = np.where(border, 0.8, 0.72)
    return save_set("Mat", bc, height, 4.0, rough)


def painting_pine(n=2048, seed=61):
    """Building stage: the painted panel as reference 2 shows it: one large ink pine centred on warm cream paper,
    its flat needle pads spreading wide across the upper two thirds, faint hills behind. Original; no text or seal."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:n, 0:n] / n
    fib = pnoise(n, n, 0.9, seed, stretch_u=0.3)
    stain = pnoise(n, n, 2.2, seed + 7)
    # f2 (blind judge delta 5: "the paper is stark white and the pine a grey silhouette"; reference 2's panel is warm
    # beige parchment with dense dark-ink foliage): a warmer, darker beige paper (was #CCBE9F), near-black ink, fuller
    # and darker needle clouds (opacity 0.85-1.0, was 0.62-0.90; 15 % larger), a darker trunk
    paper = srgb("#C2B397")   # look3: paler neutral parchment (reference 2 panel reads pale grey-beige, not ochre)   # house rule: paper albedo <= 0.80 (clamped below as well)
    ink = np.zeros((n, n))
    x = u[0]
    for base, amp, dark, s in ((0.80, 0.10, 0.07, 5), (0.86, 0.07, 0.11, 6)):   # faint far hills
        ridge = base - amp * np.abs(np.sin(x * np.pi * 1.3 + s)) - 0.02 * np.abs(pnoise(1, n, 1.6, s)[0])
        below = v - ridge[None, :]
        ink = np.maximum(ink, np.where(below > 0, np.exp(-below / 0.05), 0) * dark)

    def stroke(points, r0, r1, soft=0.0025):
        pts = np.array(points, dtype=float)
        seg = np.linspace(0, 1, 400)
        cu = np.interp(seg, np.linspace(0, 1, len(pts)), pts[:, 0])
        cv = np.interp(seg, np.linspace(0, 1, len(pts)), pts[:, 1])
        out = np.zeros((n, n))
        for pu, pv, t in zip(cu, cv, seg):
            r = r0 + (r1 - r0) * t
            lo_u, hi_u = int(max(0, (pu - r - 0.01) * n)), int(min(n, (pu + r + 0.01) * n))
            lo_v, hi_v = int(max(0, (pv - r - 0.01) * n)), int(min(n, (pv + r + 0.01) * n))
            d = np.sqrt((u[lo_v:hi_v, lo_u:hi_u] - pu) ** 2 + (v[lo_v:hi_v, lo_u:hi_u] - pv) ** 2)
            out[lo_v:hi_v, lo_u:hi_u] = np.maximum(out[lo_v:hi_v, lo_u:hi_u], np.clip((r - d) / soft, 0, 1))
        return out

    dry = 0.72 + 0.28 * np.clip(pnoise(n, n, 0.6, 300, stretch_u=0.2), -1, 1)
    # f1 (blind judge delta 13: reference 2's pine is fuller, with more branch mass spreading wider): a heavier leaning
    # trunk, seven long branches reaching almost to the panel edges, and 3-4 overlapping ragged needle clouds per branch
    trunk = [(0.46, 1.02), (0.49, 0.90), (0.43, 0.77), (0.47, 0.65), (0.55, 0.55), (0.52, 0.44), (0.48, 0.33),
             (0.52, 0.23), (0.50, 0.15)]
    wood = stroke(trunk, 0.046, 0.012) * dry
    branches = [((0.44, 0.75), (0.31, 0.70), (0.18, 0.73), (0.06, 0.69)),
                ((0.54, 0.57), (0.68, 0.54), (0.82, 0.59), (0.95, 0.55)),
                ((0.51, 0.46), (0.37, 0.41), (0.23, 0.40), (0.09, 0.44)),
                ((0.52, 0.40), (0.66, 0.34), (0.80, 0.31), (0.92, 0.35)),
                ((0.49, 0.31), (0.39, 0.24), (0.27, 0.21), (0.17, 0.24)),
                ((0.51, 0.27), (0.62, 0.19), (0.74, 0.15), (0.83, 0.18)),
                ((0.50, 0.16), (0.47, 0.09), (0.42, 0.07))]
    for b in branches:
        wood = np.maximum(wood, stroke(b, 0.017, 0.006) * dry)
    pad_at = []
    for b in branches:
        pts = np.array(b)
        for t in (0.4, 0.58, 0.74, 0.88, 1.0):   # overlapping clouds along the outer part of every branch
            k = min(len(pts) - 2, int(t * (len(pts) - 1)))
            f_ = t * (len(pts) - 1) - k
            p = pts[k] + min(f_, 1.0) * (pts[k + 1] - pts[k])
            rx = 1.15 * (rng.uniform(0.07, 0.09) if t == 1.0 else rng.uniform(0.05, 0.07))
            pad_at.append((p[0], p[1] - 0.012, rx))
            for _ in range(2):
                pad_at.append((p[0] + rng.uniform(-0.05, 0.05), p[1] - rng.uniform(0.02, 0.05), rx * rng.uniform(0.55, 0.8)))
    pad_at += [(0.50, 0.12, 0.08), (0.44, 0.08, 0.06), (0.56, 0.20, 0.06)]
    pads = np.zeros((n, n))
    for k, (cx, cy, rx) in enumerate(pad_at):
        ry = rx * 0.42
        e = ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2
        ragged = np.maximum(1 + 0.45 * pnoise(n, n, 0.9, 200 + k), 0.5)
        body = np.clip((1.0 - e * ragged) * 5, 0, 1) * (e < 2.5)
        top_dark = np.clip(1.15 - (v - (cy - ry)) / (2 * ry) * 0.45, 0.72, 1.0)
        pads = np.maximum(pads, body * top_dark * rng.uniform(0.85, 1.0))
    needles = np.clip(0.90 + 0.25 * pnoise(n, n, 0.3, 411), 0.6, 1.0)   # f1: a needle texture inside the clouds
    pads = pads * needles
    wood = wood * (1 - 0.75 * np.clip(pads * 1.5, 0, 1))   # f1: the needle clouds cover the branch ends
    ink = 1 - (1 - ink) * (1 - 0.97 * wood) * (1 - 0.97 * pads)
    ground = np.clip((v - 0.93) / 0.05, 0, 1) * np.exp(-((u - 0.5) / 0.25) ** 2) * 0.25   # a faint bank at the foot
    ink = 1 - (1 - ink) * (1 - ground)
    inkcol = srgb("#221E1A")   # look3: a softer ink black
    col = paper[None, None, :] * (1 + 0.03 * fib + 0.03 * stain)[..., None]
    col = col * (1 - ink[..., None]) + inkcol[None, None, :] * ink[..., None]
    col = np.minimum(col, 0.80)
    return save_set("Painting", col, 0.02 * fib, 2.0, 0.9 - 0.1 * ink)


def slate(n=1024, seed=91):
    """Item 1 revision (user: "a flat black slate-looking tray"): honed charcoal slate for the shuriken board, as reference
    2's display boards. Tile = 0.5 m. Fine cleavage streaks along U, soft mottle, a honed (not polished) finish."""
    mottle = pnoise(n, n, 2.2, seed)
    streak = pnoise(n, n, 1.2, seed + 1, stretch_u=0.08)
    grain = pnoise(n, n, 0.5, seed + 2)
    base = srgb("#1D1D1F")   # r2: darker (reference 2's board reads near-black; #2A2A2C read grey)
    lum = 1.0 + 0.07 * mottle + 0.05 * streak + 0.035 * grain
    bc = base[None, None, :] * lum[..., None]
    height = 0.02 * streak + 0.01 * grain
    rough = 0.88 + 0.04 * np.tanh(streak) + 0.02 * grain   # matte honed slate (0.62 read as brushed metal under the case light)
    return save_set("Slate", bc, height, 2.0, rough)


if __name__ == "__main__":
    only = set(sys.argv[1:])
    report = []
    # building stage: runner replaces mat, painting_pine replaces painting (the old functions stay for reference)
    for fn in (plank, timber, plaster, runner, ground, painting_pine, backdrop, emblem, banner, plum, lantern_paper,
               slate):
        if not only or fn.__name__ in only:
            report.append(fn())
            print("done", fn.__name__, flush=True)
    (OUT / "textures_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
