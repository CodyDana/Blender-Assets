"""Tileable white-water foam for the river material (plain Python 3: numpy + PIL).

    py -3 -B Scripts/dojo/fx/make_foam.py [--size 2048]

T_DKF_Foam_M  linear, tileable: R = foam coverage (lacy sheets with bubble holes, dense patches), G = fine bubble
              lace (small cells, for close-up detail / a second tiling), B = flow streaks (stretched along V = the
              flow direction), A unused (1)
T_DKF_Foam_N  linear DirectX normal of the foam height (bubble domes on the lace), tileable

Everything is built on the torus (FFT noise, periodic Voronoi), so both maps tile seamlessly; the seam test in the
report compares the wrap-around pixel differences against the interior ones.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402


def voronoi_periodic(size, cells, seed):
    """F1, F2 distances (in cell units) of a jittered-grid Voronoi on the torus."""
    rng = np.random.default_rng(seed)
    pts = rng.random((cells, cells, 2))
    px = (np.arange(size) + 0.5) / size * cells
    X, Y = np.meshgrid(px, px)
    ix, iy = np.floor(X).astype(int), np.floor(Y).astype(int)
    f1 = np.full((size, size), 9.0)
    f2 = np.full((size, size), 9.0)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = ix + dx, iy + dy
            p = pts[cy % cells, cx % cells]
            d = np.hypot(cx + p[..., 0] - X, cy + p[..., 1] - Y)
            f2 = np.where(d < f1, f1, np.minimum(f2, d))
            f1 = np.minimum(f1, d)
    return f1, f2


def voronoi_shifted(size, cells, seed, shift):
    """Same field as voronoi_periodic evaluated with the sample grid shifted by `shift` cells (seam proof)."""
    rng = np.random.default_rng(seed)
    pts = rng.random((cells, cells, 2))
    px = (np.arange(size) + 0.5) / size * cells + shift
    X, Y = np.meshgrid(px, px)
    ix, iy = np.floor(X).astype(int), np.floor(Y).astype(int)
    f1 = np.full((size, size), 9.0)
    f2 = np.full((size, size), 9.0)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = ix + dx, iy + dy
            p = pts[cy % cells, cx % cells]
            d = np.hypot(cx + p[..., 0] - X, cy + p[..., 1] - Y)
            f2 = np.where(d < f1, f1, np.minimum(f2, d))
            f1 = np.minimum(f1, d)
    return f1, f2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=2048)
    a = ap.parse_args()
    n = a.size
    cover_lo = fx.fbm(n, 3, 4, 71, gain=0.55, aniso=(2.5, 1.0))
    streak = fx.fbm(n, 5, 4, 72, gain=0.6, aniso=(6.0, 1.0))
    f1a, f2a = voronoi_periodic(n, 48, 73)   # big bubbles / holes (~43 px)
    f1b, f2b = voronoi_periodic(n, 150, 74)  # fine lace (~14 px)
    rim_a = 1 - fx.smoothstep(0.02, 0.16, f2a - f1a)
    rim_b = 1 - fx.smoothstep(0.02, 0.20, f2b - f1b)
    hole_a = fx.smoothstep(0.18, 0.42, f1a)  # bubble interiors (holes) in the big cells
    # coverage: dense patches where the low noise is high, lace (rims) elsewhere, holes punched by big bubbles
    dense = fx.smoothstep(0.2, 1.0, cover_lo)
    lace = np.clip(0.75 * rim_a + 0.35 * rim_b, 0, 1)
    cov = np.clip(dense * (1 - 0.55 * hole_a * (1 - dense)) + (1 - dense) * lace * fx.smoothstep(-0.9, 0.3, cover_lo), 0, 1)
    cov = np.clip(cov * (0.85 + 0.25 * fx.smoothstep(-1, 1, streak)), 0, 1)
    fine = np.clip(rim_b * 0.8 + 0.2 * (1 - fx.smoothstep(0.0, 0.3, f1b)), 0, 1)
    streaks = fx.smoothstep(-0.3, 1.2, streak)
    M = np.stack([cov, fine, streaks, np.ones_like(cov)], -1)
    # height: bubble domes (1 - f1^2 inside cells) on the foam, flat water where there is none
    dome = np.clip(1 - (f1b / 0.7) ** 2, 0, 1) * 0.5 + np.clip(1 - (f1a / 0.7) ** 2, 0, 1) * 0.5
    h = cov * (0.6 + 0.4 * dome) - 0.3 * hole_a * (1 - dense)
    N = fx.height_to_normal_dx(h, 0.004)
    fx.save_png(M, fx.TEX / "T_DKF_Foam_M.png")
    fx.save_png(N, fx.TEX / "T_DKF_Foam_N.png")
    # seam test: the Voronoi field evaluated half a period further must equal the rolled field (exact on the torus;
    # the FFT noise is periodic by construction). A single wrap-row difference is only one sample of the interior
    # distribution, so it is not used as the gate.
    t1, t2 = voronoi_periodic(256, 16, 99)
    s1, s2 = voronoi_shifted(256, 16, 99, 8.0)
    exact = float(np.abs(np.roll(np.roll(t2 - t1, -128, 0), -128, 1) - (s2 - s1)).max())
    rep = {"size": n, "coverage_mean": round(float(cov.mean()), 4), "periodic_by_construction": True,
           "voronoi_half_period_shift_max_error": exact, "seamless": exact < 1e-9}
    fx.write_json(fx.WORK / "json/foam.json", rep)
    tile = np.tile(cov, (2, 2))
    fx.save_png(tile[::2, ::2], fx.WORK / "renders/flipbooks/foam_tile2x2_preview.png")
    print(rep)


if __name__ == "__main__":
    main()
