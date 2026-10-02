"""Tiling granite grain and moss detail textures (STONE_BUILDING_STUDY.md 3.11 granite grain, 4.11 micro set):
seamless numpy textures, our own (no scans), for the unique-UV rock master's detail layer.

Granite: angular crystals from a periodic power diagram (jittered seeds, additive weights so crystal sizes vary,
2-7 mm), four minerals by share: plagioclase white, K-feldspar cream, smoky quartz grey, biotite black (~6-8 %
area: the sheet's grain close-up reads 11 % below luma 0.25 including shadow; the study's S10 cap is ~5 % of black
speckle, so 7 % is the compromise and is measured). A neutral tile: the rock's tone comes from the material tint and
the unique stain mask, so one tile serves every rock.

    py -3 -B Scripts/stone/granite_tile.py --out <dir> --prefix T_DKR [--size 2048] [--tile_m 1.0]

Writes <prefix>_GraniteDetail_BC.png (sRGB), <prefix>_GraniteDetail_N.png (DirectX, Non-Color),
<prefix>_GraniteDetail_H.png (height, Non-Color), <prefix>_MossDetail_BC.png (sRGB) and a JSON of the shares.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


def periodic_noise(n, f_lo, f_hi, rng, slope=0.0):
    """Band-limited periodic gaussian noise (n x n), frequencies in cycles per tile, normalised to std 1."""
    fx = np.fft.fftfreq(n) * n
    FX, FY = np.meshgrid(fx, fx)
    f = np.hypot(FX, FY)
    amp = ((f >= f_lo) & (f <= f_hi)).astype(float) * np.where(f > 0, f, 1.0) ** (-slope)
    ph = rng.uniform(0, 2 * np.pi, (n, n))
    spec = amp * np.exp(1j * ph)
    out = np.real(np.fft.ifft2(spec))
    return (out - out.mean()) / max(out.std(), 1e-9)


def power_cells(n, cell_px, rng, wspread=0.6):
    """Periodic power diagram on an n x n tile: seeds on a jittered grid of ``cell_px``, additive weights.
    Returns (label (n, n), dist-to-border proxy (n, n), seed count)."""
    g = int(round(n / cell_px))
    cp = n / g
    jx = rng.uniform(0.05, 0.95, (g, g))
    jy = rng.uniform(0.05, 0.95, (g, g))
    w = rng.uniform(-wspread, wspread, (g, g)) * cp * cp * 0.5
    best = np.full((n, n), np.inf)
    second = np.full((n, n), np.inf)
    lab = np.zeros((n, n), np.int64)
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    ci = (xs // cp).astype(np.int64)
    cj = (ys // cp).astype(np.int64)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ii = (ci + di) % g
            jj = (cj + dj) % g
            sx = (ci + di + jx[jj, ii]) * cp
            sy = (cj + dj + jy[jj, ii]) * cp
            d = (xs - sx) ** 2 + (ys - sy) ** 2 - w[jj, ii]
            idv = jj * g + ii
            upd = d < best
            second = np.where(upd, best, np.minimum(second, d))
            best = np.where(upd, d, best)
            lab = np.where(upd, idv, lab)
    border = np.sqrt(np.maximum(second - best, 0))       # small near cell borders
    return lab, border, g * g


def granite(n=2048, tile_m=1.0, seed=5151):
    rng = np.random.default_rng(seed)
    px_mm = tile_m * 1000 / n
    # two crystal scales: coarse feldspar/quartz crystals (~5 mm) and fine biotite flakes (~2.5 mm)
    lab, border, ns = power_cells(n, 4.6 / px_mm, rng, 0.8)
    labf, borderf, nsf = power_cells(n, 2.4 / px_mm, rng, 0.5)
    u = rng.uniform(size=ns)
    uf = rng.uniform(size=nsf)
    # minerals on the coarse cells: plagioclase 48 %, K-feldspar 16 %, quartz 30 % (+ biotite on the fine cells)
    mineral = np.where(u < 0.48, 0, np.where(u < 0.64, 1, 2))[lab]
    bio_cell = uf < 0.20
    clump = periodic_noise(n, 6, 40, rng)                # biotite clusters in clumps, not an even dusting
    bio = bio_cell[labf] & (clump > 0.35)
    tone = rng.uniform(-1, 1, ns)[lab]
    fine = periodic_noise(n, 120, 600, rng)
    # sRGB colours per mineral
    col = np.zeros((n, n, 3))
    plag = np.array([0.86, 0.85, 0.83])
    kfel = np.array([0.84, 0.79, 0.73])
    qtz = np.array([0.50, 0.50, 0.50])
    biot = np.array([0.10, 0.10, 0.10])
    for k, c, var in ((0, plag, 0.05), (1, kfel, 0.05), (2, qtz, 0.10)):
        m = mineral == k
        col[m] = c * (1.0 + var * tone[m, None] + 0.03 * fine[m, None])
    col[bio] = biot * (1.0 + 0.25 * fine[bio, None])
    # grain boundaries a touch darker
    edge = np.exp(-(border / (0.8 / px_mm)) ** 2)
    col *= (1.0 - 0.10 * edge)[..., None]
    col = np.clip(col, 0, 1)
    # height: feldspar proud, quartz mid, biotite pitted, crystal-internal roughness
    h = np.where(mineral == 2, 0.45, 0.62) + 0.04 * tone + 0.03 * fine - 0.08 * edge
    h = np.where(bio, 0.22, h)
    lum = 0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2]
    shares = {"plagioclase": float((mineral == 0).mean()), "k_feldspar": float((mineral == 1).mean()),
              "quartz": float((mineral == 2).mean()), "biotite_area": float(bio.mean()),
              "dark_lt_0.25": float((lum < 0.25).mean()), "mean_srgb": [float(x) for x in col.mean((0, 1))],
              "crystal_mm": [2.4, 4.6], "tile_m": tile_m, "px": n}
    return col, h, shares


def normal_dx(h, px_m, strength_m=0.0015):
    """Tangent-space normal (DirectX: green = -dH/dv) from a periodic height field of ``strength_m`` relief."""
    hz = h * strength_m
    dx = (np.roll(hz, -1, 1) - np.roll(hz, 1, 1)) / (2 * px_m)
    dy = (np.roll(hz, -1, 0) - np.roll(hz, 1, 0)) / (2 * px_m)    # image rows go down = -v
    nx, ny, nz = -dx, dy, np.ones_like(hz)                         # OpenGL (+v up): ny = -dH/dv = +dH/drow
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / L, ny / L, nz / L], -1)
    n[..., 1] *= -1.0                                              # DirectX: flip green
    return n * 0.5 + 0.5


def moss(n=1024, seed=6161):
    rng = np.random.default_rng(seed)
    a = periodic_noise(n, 40, 200, rng)
    b = periodic_noise(n, 150, 500, rng)
    c = periodic_noise(n, 4, 20, rng)
    t = np.clip(0.5 + 0.25 * a + 0.2 * b + 0.15 * c, 0, 1)
    dark = np.array([0.20, 0.25, 0.07])
    light = np.array([0.55, 0.58, 0.18])
    dry = np.array([0.52, 0.45, 0.22])
    col = dark + (light - dark) * t[..., None]
    col = col + (dry - col) * np.clip(0.5 * c - 0.2, 0, 1)[..., None] * 0.6
    return np.clip(col, 0, 1)


def save(arr, path, mode="RGB"):
    a = np.clip(np.round(arr * 255), 0, 255).astype(np.uint8)
    Image.fromarray(a, mode if a.ndim == 3 else "L").save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="T_DKR")
    ap.add_argument("--size", type=int, default=2048)
    ap.add_argument("--tile_m", type=float, default=1.0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    col, h, shares = granite(a.size, a.tile_m)
    save(col, out / f"{a.prefix}_GraniteDetail_BC.png")
    save(normal_dx(h, a.tile_m / a.size), out / f"{a.prefix}_GraniteDetail_N.png")
    save(np.clip(h, 0, 1), out / f"{a.prefix}_GraniteDetail_H.png", "L")
    save(moss(1024), out / f"{a.prefix}_MossDetail_BC.png")
    (out / f"{a.prefix}_GraniteDetail.json").write_text(json.dumps(shares, indent=1), encoding="utf-8")
    print(json.dumps(shares))


if __name__ == "__main__":
    main()
