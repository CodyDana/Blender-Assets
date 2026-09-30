"""Pine texture sets (our own procedural work, numpy + PIL; no pixel from the AI sheet, which was only measured).

Writes Exports/DojoKit/Pines/Textures/:
  T_DKN_Bark_BC / _N / _ORM   1024 x 1024, one tile = 1 m x 1 m (10.24 px/cm: the sheet's bark close-up frames a
                              trunk, study 4.6), tiling in U and V. BC sRGB, N DirectX (green = -Y), ORM linear.
  T_DKN_Needle_BC / _N / _ORM / _SSS  1024 x 1024 = 64 x 8 identical needle cells (16 x 128 px each; see
                              vegetation/foliage.py). SSS is a LINEAR single-channel thickness/transmission mask.
  T_DKN_Moss_BC / _N / _ORM   1024 x 1024, one tile = 2 m (the rock's moss; the material scales UV0 by 2 because
                              the rock's box UVs are in the granite set's 4 m tiles).
and WorkFiles/dojo/build/pines/tex/bark_height.npy: the bark height map the trunk builder displaces the plate
geometry with (so geometric fissures and texture fissures line up).

Colour targets (render look, measured on the sheet's close-ups, study 8.1 / 3.9): needles median sRGB (82, 88, 50),
hue ~70 deg, sat ~0.42; bark median (84, 71, 63), P10 (30, 23, 18), P90 (160, 141, 130), luma P90/P10 ~6.0.
Run: py -3 -B Scripts/dojo/pines/make_pine_textures.py [--bark-scale 1.0] [--needle-value 1.0]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TEX = ROOT / "Exports" / "DojoKit" / "Pines" / "Textures"
BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "pines"


# ----------------------------------------------------------------------------- periodic noise

def pnoise(h, w, gy, gx, seed):
    """Periodic smooth value noise (bicubic-ish) on a (gy, gx) lattice over an (h, w) tile, 0-1."""
    rng = np.random.default_rng(seed)
    G = rng.random((gy, gx))
    y = (np.arange(h) + 0.5) / h * gy
    x = (np.arange(w) + 0.5) / w * gx
    y0 = np.floor(y).astype(int)
    x0 = np.floor(x).astype(int)
    fy = y - y0
    fx = x - x0
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = G[np.ix_(y0 % gy, x0 % gx)]
    b = G[np.ix_(y0 % gy, (x0 + 1) % gx)]
    c = G[np.ix_((y0 + 1) % gy, x0 % gx)]
    d = G[np.ix_((y0 + 1) % gy, (x0 + 1) % gx)]
    return (a * (1 - fx)[None, :] + b * fx[None, :]) * (1 - fy)[:, None] + (c * (1 - fx)[None, :] + d * fx[None, :]) * fy[:, None]


def fbm(h, w, gy, gx, seed, octaves=4, gain=0.5):
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * pnoise(h, w, gy * 2 ** o, gx * 2 ** o, seed + o * 17)
        tot += amp
        amp *= gain
    return out / tot


def voronoi_periodic(h, w, nx, ny, seed, aniso=1.0, warp=None):
    """Jittered-grid Voronoi on a torus. Returns F1, F2 (in tile units of U) and the cell id. ``aniso`` > 1
    stretches cells along V (rows)."""
    rng = np.random.default_rng(seed)
    jit = rng.random((ny, nx, 2)) * 0.8 + 0.1
    ys = (np.arange(h) + 0.5) / h
    xs = (np.arange(w) + 0.5) / w
    X, Y = np.meshgrid(xs, ys)
    if warp is not None:
        X = X + warp[0]
        Y = Y + warp[1]
    gx = X * nx
    gy = Y * ny
    cx = np.floor(gx).astype(int)
    cy = np.floor(gy).astype(int)
    F1 = np.full((h, w), 9.0)
    F2 = np.full((h, w), 9.0)
    ID = np.zeros((h, w), dtype=np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ix = cx + dx
            iy = cy + dy
            j = jit[iy % ny, ix % nx]
            px = (ix + j[..., 0]) / nx
            py = (iy + j[..., 1]) / ny
            d = np.sqrt((X - px) ** 2 + ((Y - py) / aniso) ** 2)
            cid = (iy % ny) * nx + (ix % nx)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            ID = np.where(closer, cid, ID)
            F1 = np.where(closer, d, F1)
    return F1, F2, ID


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def to_srgb8(lin):
    lin = np.clip(lin, 0, 1)
    s = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    return (np.clip(s, 0, 1) * 255 + 0.5).astype(np.uint8)


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def normal_from_height(H, strength, px_size_m, tile=True):
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) / (2 * px_size_m)
    gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) / (2 * px_size_m)
    # image rows run top-down; V (and +Y tangent) runs up, so dH/dv = -gy
    nx = -gx * strength
    ny_gl = gy * strength          # = -dH/dv
    nz = np.ones_like(H)
    n = np.stack([nx, ny_gl, nz], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[..., 1] *= -1.0              # DirectX: green = -Y
    return ((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)


def blur_wrap(A, r):
    out = A.copy()
    for _ in range(2):
        acc = np.zeros_like(out)
        for d in range(-r, r + 1):
            acc += np.roll(out, d, 1)
        out = acc / (2 * r + 1)
        acc = np.zeros_like(out)
        for d in range(-r, r + 1):
            acc += np.roll(out, d, 0)
        out = acc / (2 * r + 1)
    return out


# ----------------------------------------------------------------------------- bark

def edge_distance(e, px_m):
    """Real-space distance (m) to a cell boundary from an edge measure e = F2 - F1 computed in a stretched domain:
    first-order e / |grad e|, so horizontal cracks are not widened by the stretch (f1 fix: the r0 map drew every
    boundary as a thin line of one width, which read as a cellular net)."""
    gx = (np.roll(e, -1, 1) - np.roll(e, 1, 1)) / (2 * px_m)
    gy = (np.roll(e, -1, 0) - np.roll(e, 1, 0)) / (2 * px_m)
    g = np.sqrt(gx * gx + gy * gy)
    return e / np.maximum(g, 1e-6), gx / np.maximum(g, 1e-6), gy / np.maximum(g, 1e-6)


def noise_at(X, Y, gy, gx, seed):
    """Periodic value noise sampled at arbitrary tile coordinates X, Y (0-1 wraps), smoothstep interpolation."""
    rng = np.random.default_rng(seed)
    G = rng.random((gy, gx))
    fx, fy = X * gx, Y * gy
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = G[y0 % gy, x0 % gx]
    b = G[y0 % gy, (x0 + 1) % gx]
    c = G[(y0 + 1) % gy, x0 % gx]
    d = G[(y0 + 1) % gy, (x0 + 1) % gx]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def fbm_at(X, Y, gy, gx, seed, octaves=3, gain=0.5):
    out = np.zeros_like(X)
    amp = tot = 0.0
    amp = 1.0
    for o in range(octaves):
        out += amp * noise_at(X, Y, gy * 2 ** o, gx * 2 ** o, seed + 31 * o)
        tot += amp
        amp *= gain
    return out / tot


def level_distance(N, px_m, level=0.5):
    """Distance (m) to the level set N = level, first order: |N - level| / |grad N| (wraps)."""
    gx = (np.roll(N, -1, 1) - np.roll(N, 1, 1)) / (2 * px_m)
    gy = (np.roll(N, -1, 0) - np.roll(N, 1, 0)) / (2 * px_m)
    g = np.sqrt(gx * gx + gy * gy)
    return np.abs(N - level) / np.maximum(g, 1e-6), np.abs(gx) / np.maximum(g, 1e-6)


def bark(size=1024, seed=31, value_scale=1.0, n_cols=18):
    """f1 plated black-pine bark, column method (third construction; the Voronoi cells read as a net and the
    level-set furrows came out sparse and jagged, so the method changed twice, per CLAUDE.md).

    * Furrows: ``n_cols`` meandering vertical boundaries per metre (periodic), spacing varied 0.5-1.6x, so the
      plate columns are 4-12 cm wide; neighbours pinch together in places.
    * Cross cracks: each column is cut every 12-30 cm by a slanted, shallower crack; the cracks are staggered
      column to column, so the plates are 1:2-1:3 and never line up into a grid.
    * Each plate is domed across its column and layered: an fbm quantised to three soft terraces gives irregular
      flakes; where the outer (grey) layer is gone the rust-orange inner bark shows (the sheet's close-up).
    * Near-black furrow floors, dark grey-brown plates, pale grey weathered flakes on the highest layer.
    Returns (H, col_linear, ao, rough); H drives the trunk plate geometry (tubes.py) and the normal map."""
    h = w = size
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    X = (xx + 0.5) / w
    Y = 1.0 - (yy + 0.5) / h
    # --- column boundaries x_k(Y), periodic in Y: meander + jagged, broken edges
    gaps = rng.uniform(0.45, 1.7, n_cols)
    base_x = np.concatenate([[0.0], np.cumsum(gaps)[:-1]]) / gaps.sum() + rng.uniform(0, 1)
    bx = np.zeros((n_cols, h), np.float32)
    for k in range(n_cols):
        m1 = fbm(h, 1, 3, 1, seed + 100 + k, 3)[:, 0] - 0.5
        m2 = fbm(h, 1, 11, 1, seed + 200 + k, 2)[:, 0] - 0.5
        m3 = fbm(h, 1, 60, 1, seed + 300 + k, 2)[:, 0] - 0.5
        m4 = fbm(h, 1, 24, 1, seed + 400 + k, 2)[:, 0] - 0.5
        bx[k] = base_x[k] + 1.0 / n_cols * m1 + 0.45 / n_cols * m2 + 0.35 / n_cols * m4 + 0.010 * m3
    bx = bx[:, ::-1]                                  # image rows run top-down, Y up
    dl = np.full((h, w), 9.0, np.float32)
    dr = np.full((h, w), 9.0, np.float32)
    col_id = np.zeros((h, w), np.int32)
    for k in range(n_cols):
        off = (X - bx[k][:, None]) % 1.0              # distance from boundary k to the right
        closer = off < dl
        col_id = np.where(closer, k, col_id)
        dl = np.minimum(dl, off)
        dr = np.minimum(dr, (bx[k][:, None] - X) % 1.0)
    cw = dl + dr
    d_f = np.minimum(dl, dr)                          # metres to the nearest furrow (1 m tile)
    # --- cross cracks per column: staggered, slanted, ragged, some stop short
    Mmax = 10
    cr = np.full((n_cols, Mmax), 9.0, np.float32)
    slope = rng.uniform(-0.45, 0.45, n_cols).astype(np.float32)
    for k in range(n_cols):
        y, lst = rng.uniform(0, 1), []
        while len(lst) < Mmax:
            lst.append(y % 1.0)
            y += rng.uniform(0.10, 0.26)
            if y - lst[0] > 0.93:
                break
        cr[k, :len(lst)] = lst
    rag = 0.004 * (fbm(h, w, 40, 40, seed + 21, 2) - 0.5)
    Yc = Y - slope[col_id] * (dl - 0.5 * cw) + rag
    cpos = cr[col_id]                                 # (h, w, Mmax)
    valid = cpos < 5
    dy = np.where(valid, (Yc[..., None] - cpos) % 1.0, 9.0)
    plate_m = dy.argmin(-1)
    d_c = np.minimum(dy.min(-1), np.where(valid, (cpos - Yc[..., None]) % 1.0, 9.0).min(-1))
    plate_id = col_id * Mmax + plate_m
    npl = n_cols * Mmax
    # --- relief
    edge_rag = 0.0035 * (fbm(h, w, 30, 30, seed + 22, 3) - 0.5)          # ragged plate outlines
    hw = 0.0030 + 0.0080 * fbm(h, w, 5, 8, seed + 5, 2) ** 1.5 + edge_rag   # furrow half width ~3-11 mm
    sh = 0.005 + 0.004 * fbm(h, w, 5, 7, seed + 6, 2)                   # rounded shoulder
    plate = smoothstep(hw, hw + sh, d_f)
    part = smoothstep(0.35, 0.55, fbm(h, w, 5, 9, seed + 23, 2))        # some cracks stop short
    crack = (1.0 - smoothstep(0.0020 + 0.8 * np.abs(edge_rag), 0.008, d_c)) * (0.35 + 0.65 * part)
    plate_c = plate * (1.0 - 0.75 * crack)
    across = np.clip(4.0 * dl * dr / np.maximum(cw * cw, 1e-6), 0, 1) ** 0.35      # dome across the column
    p_h = rng.uniform(0.72, 1.0, npl)[plate_id]
    p_tone = rng.uniform(0.0, 1.0, npl)[plate_id]
    p_off = rng.uniform(-0.2, 0.2, npl)[plate_id]
    # flaky terraces: three soft levels of an fbm; high-frequency noise makes the risers ragged (flake outlines)
    fl = np.clip(0.42 * fbm(h, w, 12, 24, seed + 7, 3, gain=0.55) + 0.30 * fbm(h, w, 30, 50, seed + 8, 2)
                 + 0.16 * fbm(h, w, 120, 140, seed + 27, 2) + 0.08 + p_off, 0, 1)
    q = fl * 2.999
    fq = np.floor(q)
    level = fq + smoothstep(0.84, 0.95, q - fq)                   # 0, 1, 2 with steep risers
    riser = np.clip(1.0 - np.abs((q - fq) - 0.895) / 0.07, 0, 1)
    # crumble: ridged noise at 0.5-3 cm (the scaly, broken plate surface), no cells. It carries most of the look:
    # lit ridges, shadowed pits, rust in the pits.
    warpc = 0.004 * (fbm(h, w, 25, 25, seed + 29, 2) - 0.5)
    rn1 = fbm(h, w, 18, 24, seed + 25, 3, gain=0.6)
    rn2 = fbm(h, w, 44, 56, seed + 26, 2, gain=0.6)
    rn3 = fbm(h, w, 100, 120, seed + 30, 2)
    cr1 = 1.0 - np.abs(2.0 * rn1 - 1.0)
    cr2 = 1.0 - np.abs(2.0 * rn2 - 1.0)
    cr3 = 1.0 - np.abs(2.0 * rn3 - 1.0)
    crum = 0.5 * cr1 ** 1.5 + 0.32 * cr2 ** 1.5 + 0.18 * cr3
    crum = (crum - crum.min()) / (crum.max() - crum.min())
    crumb = fbm(h, w, 90, 90, seed + 9, 2)
    H = plate_c * p_h * (0.40 + 0.10 * across + 0.17 * level + 0.24 * crum)
    H = (H - H.min()) / (H.max() - H.min())
    # --- colour (linear). Sheet close-up sRGB: furrow floor ~(20,14,10), median ~(83,70,63), P75 ~(121,105,96),
    # P95 ~(177,160,149); rust ~(150,100,70) on ~8 %.
    c_fis = srgb_to_lin((14, 10, 8))
    c_dark = srgb_to_lin((40, 32, 27))
    c_mid = srgb_to_lin((114, 102, 92))
    c_pale = srgb_to_lin((168, 158, 148))
    c_rust = srgb_to_lin((162, 100, 60))
    top = smoothstep(1.4, 1.9, level)
    low = 1.0 - smoothstep(0.4, 0.9, level)
    tone = fbm(h, w, 6, 6, seed + 13, 3)
    var = (0.80 + 0.30 * tone + 0.25 * (p_tone - 0.5))[..., None]
    t = smoothstep(0.30, 0.80, crum)[..., None]                  # pits -> ridges
    col = (c_dark[None, None, :] * (1 - t) + c_mid[None, None, :] * t) * var
    pale = (smoothstep(0.55, 0.85, crum) * smoothstep(0.40, 0.70, fbm(h, w, 20, 26, seed + 31, 2))
            * (0.5 + 0.5 * top))[..., None]
    col = col * (1 - pale) + c_pale[None, None, :] * pale
    rust_n = smoothstep(0.42, 0.62, fbm(h, w, 28, 40, seed + 15, 2))
    pit = smoothstep(0.45, 0.15, crum)
    rust = np.clip(0.8 * pit * rust_n * (0.3 + 0.7 * low) + 0.9 * riser * rust_n + 0.55 * low * rust_n * (1 - pit), 0, 1)
    wall = np.clip(1.0 - np.abs(plate - 0.35) / 0.3, 0, 1) * rust_n * 0.7
    rust = np.clip(rust + wall, 0, 1)[..., None]
    col = col * (1 - rust) + c_rust[None, None, :] * rust
    col = col * (1.0 - 0.5 * riser * (1 - low))[..., None]          # shadow line under each flake edge
    pf = (np.clip(plate_c, 0, 1) ** 1.3)[..., None]
    col = col * pf + c_fis[None, None, :] * (1 - pf)
    col *= value_scale
    cav = np.clip(blur_wrap(H, 6) - H, 0, 1)
    ao = np.clip(1.0 - 3.5 * cav - 0.6 * (1 - plate_c), 0.06, 1.0)
    rough = np.clip(0.88 - 0.08 * pale[..., 0] + 0.06 * (1 - plate_c), 0, 1)
    return H, col, ao, rough


def bark_v2(size=1024, seed=57, value_scale=1.0, n_cols=16):
    """v2 black-pine bark from explicit PLATE GEOMETRY (height field of raised, layered plates; the normal map and
    the trunk displacement are both derived from it: 'bake from plate geometry: normal + height').

    f1 read as a regular tile of smooth clay columns with blobby crumble. v2, per the sheet's bark close-up:
      * plates: meandering vertical columns (4-13 cm wide, strongly varied), cut by staggered, slanted, ragged
        cross cracks every 1.6-3.2 column widths (aspect 1:2-1:3); some plates split again by a thin secondary
        crack, some cross cracks stop short, so no grid reads;
      * relief per plate follows its OUTLINE: 3 flaky layers stacked inward from the plate edge (terraces 3-6 mm
        high, ragged risers), a gentle dome and a scaly surface on top; wide deep near-black fissures between;
      * colour: dark grey-brown plate tops (~sRGB 70,58,48) with sparse pale grey weathered flakes, orange-rust
        exposed layers at the plate edges and on the risers (~150,90,50), near-black fissures (~14,10,8).
    Returns (H, col_linear, ao, rough)."""
    h = w = size
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    X = (xx + 0.5) / w
    Y = 1.0 - (yy + 0.5) / h
    # --- column boundaries x_k(Y), periodic in Y, strongly varied widths
    gaps = rng.uniform(0.35, 1.9, n_cols)
    base_x = np.concatenate([[0.0], np.cumsum(gaps)[:-1]]) / gaps.sum() + rng.uniform(0, 1)
    bx = np.zeros((n_cols, h), np.float32)
    for k in range(n_cols):
        m1 = fbm(h, 1, 2, 1, seed + 100 + k, 3)[:, 0] - 0.5
        m2 = fbm(h, 1, 9, 1, seed + 200 + k, 2)[:, 0] - 0.5
        m3 = fbm(h, 1, 70, 1, seed + 300 + k, 2)[:, 0] - 0.5
        bx[k] = base_x[k] + 1.1 / n_cols * m1 + 0.55 / n_cols * m2 + 0.012 * m3
    bx = bx[:, ::-1]
    dl = np.full((h, w), 9.0, np.float32)
    dr = np.full((h, w), 9.0, np.float32)
    col_id = np.zeros((h, w), np.int32)
    for k in range(n_cols):
        off = (X - bx[k][:, None]) % 1.0
        closer = off < dl
        col_id = np.where(closer, k, col_id)
        dl = np.minimum(dl, off)
        dr = np.minimum(dr, (bx[k][:, None] - X) % 1.0)
    cw = dl + dr
    d_f = np.minimum(dl, dr)
    # --- cross cracks per column: spacing 1.6-3.2 column widths (plates 1:2-1:3), staggered, slanted, ragged
    Mmax = 12
    colw = np.array([np.median(cw[col_id == k]) if (col_id == k).any() else 0.06 for k in range(n_cols)])
    cr = np.full((n_cols, Mmax), 9.0, np.float32)
    part_len = np.ones((n_cols, Mmax), np.float32)
    slope = rng.uniform(-0.55, 0.55, n_cols).astype(np.float32)
    for k in range(n_cols):
        y, lst = rng.uniform(0, 1), []
        while len(lst) < Mmax:
            lst.append(y % 1.0)
            y += colw[k] * rng.uniform(1.6, 3.2)
            if y - lst[0] > 1.0 - colw[k] * 1.2:
                break
        cr[k, :len(lst)] = lst
        part_len[k, :len(lst)] = rng.choice([1.0, 1.0, 1.0, 0.55, 0.7], len(lst))
    rag = 0.005 * (fbm(h, w, 40, 40, seed + 21, 2) - 0.5) + 0.003 * (fbm(h, w, 120, 120, seed + 24, 2) - 0.5)
    across_pos = dl / np.maximum(cw, 1e-6)                       # 0 at the left boundary .. 1 at the right
    Yc = Y - slope[col_id] * (dl - 0.5 * cw) + rag
    cpos = cr[col_id]
    valid = cpos < 5
    dy_up = np.where(valid, (Yc[..., None] - cpos) % 1.0, 9.0)
    dy_dn = np.where(valid, (cpos - Yc[..., None]) % 1.0, 9.0)
    plate_m = dy_up.argmin(-1)
    near_up = dy_up.min(-1)
    near_dn = dy_dn.min(-1)
    # partial cracks: a crack whose part_len < 1 only spans that share of the column (from a random side)
    k_dn = dy_dn.argmin(-1)
    pl_up = np.take_along_axis(part_len[col_id], plate_m[..., None], -1)[..., 0]
    pl_dn = np.take_along_axis(part_len[col_id], k_dn[..., None], -1)[..., 0]
    side_ok_up = np.where(pl_up < 1.0, across_pos < pl_up, True)
    side_ok_dn = np.where(pl_dn < 1.0, across_pos > 1.0 - pl_dn, True)
    d_c = np.minimum(np.where(side_ok_up, near_up, 9.0), np.where(side_ok_dn, near_dn, 9.0))
    plate_id = col_id * Mmax + plate_m
    npl = n_cols * Mmax
    # secondary thin splits (a vertical hairline crack through some plates)
    split_on = rng.random(npl) < 0.35
    split_at = rng.uniform(0.3, 0.7, npl)
    d_s = np.where(split_on[plate_id], np.abs(across_pos - split_at[plate_id]) * cw, 9.0)
    d_s = d_s + 0.002 * (fbm(h, w, 60, 20, seed + 25, 2) - 0.5)
    # --- distance to the plate outline (m) with ragged edges
    edge_rag = 0.004 * (fbm(h, w, 34, 34, seed + 22, 3) - 0.5) + 0.002 * (fbm(h, w, 140, 140, seed + 26, 2) - 0.5)
    fis_hw = 0.0045 + 0.0060 * fbm(h, w, 4, 7, seed + 5, 2) ** 1.3          # vertical fissure half width 4.5-10.5 mm
    d_edge = np.minimum(d_f - fis_hw, 0.85 * d_c - 0.0030) + edge_rag
    d_edge = np.minimum(d_edge, d_s * 1.6 - 0.0005)
    furrow = smoothstep(-0.005, 0.002, d_edge)                   # 0 at the fissure floor .. 1 on the plate
    p_h = rng.uniform(0.78, 1.0, npl)[plate_id]
    p_tone = rng.uniform(0.0, 1.0, npl)[plate_id]
    # crumbly plate surface: ridged multi-scale noise (1-4 cm crumbs with dark crevices between; the sheet's plates
    # are rough blocks, not smooth cells), domain-warped and stretched a little along the grain
    WX = X + 0.012 * (fbm_at(X, Y, 4, 4, seed + 43) - 0.5)
    WY = Y + 0.012 * (fbm_at(X, Y, 4, 4, seed + 45) - 0.5)
    r1 = 1.0 - np.abs(2.0 * fbm_at(WX, WY, 26, 40, seed + 50, octaves=2, gain=0.5) - 1.0)
    r2 = 1.0 - np.abs(2.0 * fbm_at(WX, WY, 55, 80, seed + 51, octaves=2, gain=0.5) - 1.0)
    r3 = 1.0 - np.abs(2.0 * fbm_at(WX, WY, 120, 150, seed + 52, octaves=2, gain=0.5) - 1.0)
    crumb = np.clip(0.50 * r1 ** 2.2 + 0.32 * r2 ** 2.0 + 0.18 * r3 ** 1.5, 0, 1)
    crumb = (crumb - crumb.min()) / (crumb.max() - crumb.min())
    # v2 r7: inverted, the ridge lines become thin dark cracks between bright flakes (the veiny bright net of the
    # un-inverted noise read as marble); a gamma keeps most of each flake light
    crumb = np.clip(1.0 - crumb, 0, 1) ** 0.7
    # broken secondary cracks inside plates (level lines, masked so they end: no closed cells, P50)
    hl = fbm_at(WX, WY, 7, 14, seed + 33, octaves=2)
    hdist, _ = level_distance(hl, 1.0 / size)
    hair = (1.0 - smoothstep(0.0006, 0.0022, hdist)) * smoothstep(0.45, 0.62, fbm_at(X, Y, 7, 7, seed + 34))
    # flakes lost: small (1-3 cm) patches, most of them near the plate edges, show the rust layer one step down
    fl = fbm_at(WX, WY, 30, 44, seed + 7, octaves=2)
    near_edge = 1.0 - smoothstep(0.004, 0.022, d_edge)
    lost = smoothstep(0.76, 0.79, fl + 0.14 * near_edge)
    dome = np.clip(4.0 * dl * dr / np.maximum(cw * cw, 1e-6), 0, 1) ** 0.5
    Hm = furrow * p_h * (0.45 + 0.10 * dome + 0.30 * crumb - 0.08 * lost - 0.10 * hair)
    H = (Hm - Hm.min()) / (Hm.max() - Hm.min())
    # --- colour (linear): crumb crevices dark, crumb tops grey-brown to pale grey, rust in the lost patches and on
    # the upper plate sides, near-black fissure floors
    c_fis = srgb_to_lin((12, 9, 7))
    c_wall = srgb_to_lin((38, 28, 21))
    c_lo = srgb_to_lin((22, 17, 14))
    c_top = srgb_to_lin((84, 70, 58))
    c_hi = srgb_to_lin((152, 140, 126))
    c_pale = srgb_to_lin((168, 160, 150))
    c_rust = srgb_to_lin((132, 84, 54))
    c_rust2 = srgb_to_lin((104, 58, 32))
    tone = fbm(h, w, 5, 6, seed + 13, 3)
    t1 = smoothstep(0.10, 0.55, crumb)[..., None]
    t2 = smoothstep(0.55, 0.90, crumb)[..., None]
    col = c_lo[None, None] * (1 - t1) + c_top[None, None] * t1
    col = col * (1 - t2) + c_hi[None, None] * t2
    col = col * (0.84 + 0.28 * tone + 0.20 * (p_tone - 0.5))[..., None]
    pale = (smoothstep(0.72, 0.95, crumb) * smoothstep(0.40, 0.70, fbm(h, w, 18, 24, seed + 31, 2)))[..., None]
    col = col * (1 - 0.8 * pale) + c_pale[None, None] * 0.8 * pale
    rn = smoothstep(0.3, 0.8, crumb)[..., None]
    rust_col = c_rust2[None, None] * (1 - rn) + c_rust[None, None] * rn
    col = col * (1 - lost[..., None]) + rust_col * lost[..., None]
    col = col * (1.0 - 0.65 * hair)[..., None]
    upper_wall = (smoothstep(0.30, 0.65, furrow) * (1.0 - smoothstep(0.75, 1.0, furrow))
                  * smoothstep(0.35, 0.6, fbm(h, w, 20, 30, seed + 35, 2)))[..., None]
    col = col * (1 - 0.25 * upper_wall) + c_rust[None, None] * 0.25 * upper_wall
    wall = (1.0 - smoothstep(0.25, 0.7, furrow))[..., None]
    col = col * (1 - wall) + (c_wall[None, None] * (1 - wall) + c_fis[None, None] * wall) * wall
    col *= value_scale
    cav = np.clip(blur_wrap(H, 3) - H, 0, 1)
    ao = np.clip(1.0 - 4.0 * cav - 0.7 * (1 - furrow), 0.05, 1.0)
    rough = np.clip(0.86 - 0.10 * pale[..., 0] + 0.06 * (1 - furrow), 0, 1)
    return H, col, ao, rough


def lit_preview(H, col, ao, px_m=1.0 / 1024, strength=1.0, light=(-0.55, 0.45, 0.70)):
    """Numpy preview (sRGB uint8): albedo x (0.25 + 0.75 Lambert from the height normal) x AO, a raking key from
    the upper left (the sheet's close-up light)."""
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) / (2 * px_m)
    gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) / (2 * px_m)
    k = 0.020 * strength
    n = np.stack([-gx * k, gy * k, np.ones_like(H)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array(light, float)
    L /= np.linalg.norm(L)
    lam = np.clip((n * L).sum(-1), 0, 1)
    img = col * (0.22 + 1.05 * lam)[..., None] * ao[..., None] ** 0.8
    return to_srgb8(img)


def bark_levelset(size=1024, seed=31, value_scale=1.0):
    """f1 second attempt (level-set furrows; rejected: sparse, jagged). Kept for the record.
    Level-set method (the Voronoi version still read as a cellular net: changed method).

    Furrows are the 0.5 level set of a periodic noise stretched about 1:6 along V and domain-warped: its contour
    lines run mostly vertically, meander, and join and split, so the plates between them are long lenticular
    ridges (the anastomosing pattern of old pine bark) instead of polygon cells. A second noise stretched the other
    way gives short, shallow cross cracks (masked, so they break only some plates: plates 1:2-1:3). The plate
    surface is shingled flakes (small Voronoi scales, each tilted so its lower edge lifts), with rust-orange under
    the lifted edges and on the furrow walls, pale grey weathered flakes, and near-black furrow floors."""
    h = w = size
    px_m = 1.0 / size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    X = (xx + 0.5) / w
    Y = 1.0 - (yy + 0.5) / h                        # V up
    WX = X + 0.030 * (fbm_at(X, Y, 2, 3, seed + 1) - 0.5) + 0.010 * (fbm_at(X, Y, 6, 10, seed + 2) - 0.5)
    WY = Y + 0.020 * (fbm_at(X, Y, 3, 3, seed + 3) - 0.5)
    # furrows: level set of a vertically stretched noise (features ~ 6 cm across, ~35 cm along)
    N = fbm_at(WX, WY, 3, 16, seed + 4, octaves=3, gain=0.45)
    dF, vert = level_distance(N, px_m)
    halfw = 0.0035 + 0.0045 * fbm_at(X, Y, 4, 6, seed + 5)           # 3.5-8 mm half width (7-16 mm furrows)
    shoulder = 0.008 + 0.006 * fbm_at(X, Y, 5, 7, seed + 6)
    plate = smoothstep(halfw, halfw + shoulder, dF)
    # cross cracks: level set of a horizontally stretched noise, only where a mask allows (breaks some plates)
    M = fbm_at(WX, WY, 9, 3, seed + 7, octaves=2)
    dC, _ = level_distance(M, px_m)
    cmask = smoothstep(0.45, 0.62, fbm_at(X, Y, 6, 9, seed + 8))
    crack = (1.0 - smoothstep(0.0015, 0.005, dC)) * cmask
    plate = plate * (1.0 - 0.75 * crack)
    # plate relief: low-frequency lobes along each ridge
    lobe = fbm_at(WX, WY, 5, 12, seed + 9, octaves=2)
    # shingled flakes on the plates
    F1, F2, FID = voronoi_periodic(h, w, 34, 16, seed + 10, aniso=1.0, warp=(WX - X, WY - Y))
    rng = np.random.default_rng(seed + 11)
    nf = 34 * 16
    f_h = rng.uniform(0.0, 1.0, nf)[FID]
    f_tone = rng.uniform(0.0, 1.0, nf)[FID]
    # tilt: each flake rises toward its top edge (its lower edge lifts off the one below): F1 grows away from the
    # cell centre; use the vertical offset from the centre via a second noise (cheap: F1 * sign by flake)
    f_tilt = rng.uniform(0.4, 1.0, nf)[FID]
    f_edge = 1.0 - smoothstep(0.0006, 0.0035, F2 - F1)
    flake = 0.55 * f_h + 0.45 * (1.0 - np.clip(F1 / 0.03, 0, 1)) * f_tilt
    crumb = fbm_at(X, Y, 60, 60, seed + 12, octaves=2)
    H = plate * (0.62 + 0.18 * lobe + 0.16 * flake - 0.06 * f_edge + 0.04 * (crumb - 0.5))
    H = (H - H.min()) / (H.max() - H.min())
    # --- colour (albedo, linear). Sheet close-up (sRGB): furrow floors ~(20,14,10), median ~(83,70,63),
    # upper quartile ~(121,105,96), pale flakes to ~(170,155,145), rust ~(150,100,70) on about 8 % of the area.
    c_fis = srgb_to_lin((16, 11, 8))
    c_plate = srgb_to_lin((78, 66, 56))
    c_dark = srgb_to_lin((48, 40, 34))
    c_light = srgb_to_lin((158, 148, 138))
    c_rust = srgb_to_lin((156, 96, 58))
    tone = fbm_at(X, Y, 6, 6, seed + 13)
    col = c_plate[None, None, :] * (0.78 + 0.35 * tone + 0.18 * (f_tone - 0.5))[..., None]
    dk = (smoothstep(0.35, 0.05, f_tone) * 0.6 + 0.4 * f_edge)[..., None]
    col = col * (1 - dk) + c_dark[None, None, :] * dk
    pale = np.clip(smoothstep(0.72, 0.95, f_tone) * smoothstep(0.45, 0.8, H) * 0.85, 0, 1)
    col = col * (1 - pale[..., None]) + c_light[None, None, :] * pale[..., None]
    wall = np.clip(1.0 - np.abs(plate - 0.45) / 0.4, 0.0, 1.0)
    rn = fbm_at(X, Y, 10, 14, seed + 15)
    lifted = f_edge * smoothstep(0.55, 0.8, f_h) * smoothstep(0.3, 0.6, f_tilt)
    rust = np.clip(0.9 * wall * smoothstep(0.35, 0.65, rn) + 0.8 * lifted * smoothstep(0.4, 0.7, rn)
                   + 0.5 * crack * plate, 0.0, 1.0)
    col = col * (1 - rust[..., None]) + c_rust[None, None, :] * rust[..., None]
    pf = (np.clip(plate, 0, 1) ** 1.4)[..., None]
    col = col * pf + c_fis[None, None, :] * (1 - pf)
    col *= value_scale
    cav = np.clip(blur_wrap(H, 10) - H, 0, 1)
    ao = np.clip(1.0 - 3.0 * cav - 0.6 * (1 - plate), 0.06, 1.0)
    rough = np.clip(0.86 - 0.10 * pale + 0.08 * (1 - plate), 0, 1)
    return H, col, ao, rough


def bark_voronoi(size=1024, seed=31, value_scale=1.0):
    """f1 first attempt (Voronoi plates; rejected: still a cellular net). Kept for the record.
    (judge r0: 'uniform cellular network of dark grooves over flat pinkish cells').

    Tall irregular plates about 6-9 cm wide and 15-25 cm tall (aspect 1:2-1:3), separated by WIDE, deep, near-black
    vertical furrows and narrower, shallower cross cracks. Each plate is raised with a rounded shoulder and broken
    into 2-3 flaky layers (terraces); the terrace steps and the furrow walls show the orange-rust inner bark. Plate
    tops are dark grey-brown with sparse pale grey weathered highlights. Fine crackle is kept weak.
    Height is the displacement source for the trunk plate geometry (tubes.py) and the normal map."""
    h = w = size
    px_m = 1.0 / size
    rng = np.random.default_rng(seed + 9)
    # meandering vertical flow (plates follow the grain) + small wobble
    wx = 0.045 * (fbm(h, w, 2, 4, seed + 1, 3) - 0.5) + 0.012 * (fbm(h, w, 12, 12, seed + 21, 3) - 0.5)
    wy = 0.020 * (fbm(h, w, 4, 2, seed + 2, 3) - 0.5) + 0.010 * (fbm(h, w, 12, 12, seed + 22, 3) - 0.5)
    NX, NY = 13, 5                                  # 7.7 cm x 20 cm cells: plates 1:2.6
    F1, F2, ID = voronoi_periodic(h, w, NX, NY, seed, aniso=1.0, warp=(wx, wy))
    d, nx, ny = edge_distance(F2 - F1, px_m)        # metres to the nearest plate boundary, boundary normal
    vertical = np.abs(nx)                           # 1 on a vertical furrow (normal points sideways), 0 on a cross crack
    # furrow half-width: wide on the vertical furrows (6-11 mm), narrow on cross cracks (2-4 mm), varied
    wv = 0.006 + 0.005 * fbm(h, w, 3, 8, seed + 3, 3)
    wh = 0.002 + 0.002 * fbm(h, w, 8, 8, seed + 4, 2)
    half = wh + (wv - wh) * smoothstep(0.35, 0.85, vertical)
    shoulder = 0.010 + 0.006 * fbm(h, w, 6, 6, seed + 5, 2)   # the rounded plate edge above the furrow
    plate = smoothstep(half, half + shoulder, d)               # 0 in the furrow .. 1 on the plate top
    depth_cross = 0.45 + 0.55 * smoothstep(0.3, 0.9, vertical)  # cross cracks are shallower
    ncell = NX * NY
    cell_h = rng.uniform(0.72, 1.0, ncell)[ID]
    cell_tone = rng.uniform(0.82, 1.12, ncell)[ID]
    # flaky layers: 2-3 terraces per plate from a stretched noise, quantised with soft steps
    fl = fbm(h, w, 10, 4, seed + 6, 3, gain=0.55) + 0.35 * rng.uniform(-0.5, 0.5, ncell)[ID]
    q = fl * 3.0
    step_soft = np.floor(q) + smoothstep(0.82, 1.0, q - np.floor(q))
    terr = step_soft / 3.0
    step_edge = np.clip(1.0 - np.abs((q - np.floor(q)) - 0.9) / 0.10, 0.0, 1.0)   # 1 on the terrace risers
    crumb = fbm(h, w, 40, 24, seed + 7, 3, gain=0.5)
    H = plate * (cell_h * (0.70 + 0.22 * terr) + 0.05 * (crumb - 0.5))
    H = H * (1.0 - (1.0 - depth_cross) * (1.0 - plate))
    H = (H - H.min()) / (H.max() - H.min())
    # --- colour (albedo, linear). Targets (sheet close-up, sRGB): furrow ~(20,14,10), plate median ~(72,60,50)
    # (judge: less pink), highlights to ~(150,138,125), rust ~(150,90,50) on about 8 % of the area.
    c_fis = srgb_to_lin((17, 12, 9))
    c_plate = srgb_to_lin((74, 62, 50))
    c_dark = srgb_to_lin((52, 43, 36))
    c_light = srgb_to_lin((150, 139, 126))
    c_rust = srgb_to_lin((152, 90, 50))
    tone = fbm(h, w, 6, 6, seed + 13, 3)
    col = c_plate[None, None, :] * (cell_tone * (0.85 + 0.3 * tone))[..., None]
    dk = smoothstep(0.55, 0.2, crumb)[..., None] * 0.5
    col = col * (1 - dk) + c_dark[None, None, :] * dk
    # pale weathered highlights on the highest, outer parts of plates (sparse)
    hi = np.clip(smoothstep(0.62, 0.85, H) * smoothstep(0.5, 0.8, fbm(h, w, 24, 16, seed + 14, 3)) * 0.8, 0, 1)
    col = col * (1 - hi[..., None]) + c_light[None, None, :] * hi[..., None]
    # rust: the furrow walls (between the furrow floor and the plate top) and the terrace risers, noise-broken
    wall = np.clip(1.0 - np.abs(plate - 0.45) / 0.35, 0.0, 1.0) * smoothstep(0.3, 0.8, vertical)
    rn = fbm(h, w, 14, 8, seed + 15, 3)
    rust = np.clip(0.85 * wall * smoothstep(0.40, 0.70, rn) + 0.75 * step_edge * plate * smoothstep(0.45, 0.75, rn),
                   0.0, 1.0)
    col = col * (1 - rust[..., None]) + c_rust[None, None, :] * rust[..., None]
    pf = (np.clip(plate, 0, 1) ** 1.6)[..., None]
    col = col * pf + c_fis[None, None, :] * (1 - pf)
    col *= value_scale
    cav = np.clip(blur_wrap(H, 10) - H, 0, 1)
    ao = np.clip(1.0 - 3.0 * cav - 0.55 * (1 - plate), 0.08, 1.0)
    rough = np.clip(0.86 - 0.10 * hi + 0.08 * (1 - plate), 0, 1)
    return H, col, ao, rough


def bark_r0(size=1024, seed=31, value_scale=1.0):
    """r0 bark (kept for reference; replaced by ``bark`` in f1).
    Plated black-pine bark: tall irregular plates (about 7 x 18 cm) split by deep, wide, mostly vertical furrows,
    crumbly scaly plate tops, warm orange-brown exposed inner bark on the furrow walls and under lifted scales."""
    h = w = size
    wx = (0.030 * (fbm(h, w, 3, 3, seed + 1, 3) - 0.5) + 0.016 * (fbm(h, w, 16, 16, seed + 21, 3) - 0.5)
          + 0.006 * (fbm(h, w, 64, 64, seed + 23, 2) - 0.5)) * 2
    wy = (0.060 * (fbm(h, w, 3, 3, seed + 2, 3) - 0.5) + 0.020 * (fbm(h, w, 16, 16, seed + 22, 3) - 0.5)
          + 0.006 * (fbm(h, w, 64, 64, seed + 24, 2) - 0.5)) * 2
    F1, F2, ID = voronoi_periodic(h, w, 20, 5, seed, aniso=2.4, warp=(wx, wy))
    edge = F2 - F1
    fw = 0.004 + 0.007 * fbm(h, w, 6, 6, seed + 3, 3) + 0.006 * fbm(h, w, 40, 40, seed + 4, 2)
    plate = smoothstep(0.35 * fw, 1.5 * fw, edge)          # 0 deep in the furrow, 1 on the plate
    # major vertical furrows every ~14 cm: a coarse Voronoi stretched along V
    G1, G2, _ = voronoi_periodic(h, w, 7, 2, seed + 40, warp=(wx * 1.5, wy))
    major = smoothstep(0.004, 0.028, G2 - G1)
    plate = plate * (0.35 + 0.65 * major)
    rng = np.random.default_rng(seed + 9)
    cell_h = rng.uniform(0.70, 1.0, 20 * 5)[ID]
    cell_tone = rng.uniform(0.75, 1.15, 20 * 5)[ID]
    # scales on the plates: small cells with a step at their edges
    f1, f2, fid = voronoi_periodic(h, w, 44, 16, seed + 5, aniso=1.8, warp=(wx * 0.7, wy * 0.7))
    flake_step = 1.0 - smoothstep(0.0, 0.0045, f2 - f1)
    flake_h = np.random.default_rng(seed + 11).uniform(0.0, 1.0, 44 * 16)[fid]
    crumb = fbm(h, w, 48, 48, seed + 7, 4, gain=0.6)
    crumb2 = fbm(h, w, 160, 160, seed + 8, 2)
    dome = np.clip(1.0 - F1 / 0.03, 0.0, 1.0) ** 0.6
    rough_hi = fbm(h, w, 96, 96, seed + 30, 4, gain=0.65)
    g1, g2, gid = voronoi_periodic(h, w, 70, 36, seed + 31, warp=(wx * 0.5, wy * 0.5))
    micro_step = 1.0 - smoothstep(0.0, 0.0025, g2 - g1)
    micro_h = np.random.default_rng(seed + 32).uniform(0.0, 1.0, 70 * 36)[gid]
    top = (cell_h * (0.70 + 0.08 * dome + 0.12 * flake_h + 0.08 * crumb + 0.06 * micro_h)
           - 0.07 * flake_step - 0.04 * micro_step + 0.10 * (rough_hi - 0.5))
    H = np.clip(plate, 0, 1) ** 0.7 * top
    H = (H - H.min()) / (H.max() - H.min())
    # colour (albedo, linear)
    c_fis = srgb_to_lin((20, 14, 11))
    c_warm = srgb_to_lin((150, 96, 62))
    c_plate = srgb_to_lin((92, 80, 71))
    c_light = srgb_to_lin((168, 152, 138))
    wall = np.clip(1.0 - np.abs(plate - 0.5) / 0.5, 0, 1)
    warm_n = fbm(h, w, 10, 10, seed + 13, 3)
    lifted = (flake_h > 0.82) * plate * (1 - flake_step)
    warm = np.clip(0.7 * wall * smoothstep(0.45, 0.75, warm_n) + 0.55 * lifted * smoothstep(0.5, 0.8, warm_n)
                   + 0.35 * smoothstep(0.78, 0.92, fbm(h, w, 20, 20, seed + 19, 3)) * plate, 0, 1)
    speck = np.clip((crumb2 - 0.35) * 1.6, 0, 1)
    light = np.clip(smoothstep(0.55, 0.9, rough_hi) * 0.55 + 0.35 * speck * smoothstep(0.6, 1.0, top)
                    + 0.25 * micro_h * (1 - micro_step), 0, 1)
    shade = 0.45 + 0.9 * crumb * (0.7 + 0.3 * crumb2)
    col = c_plate[None, None, :] * (cell_tone * shade)[..., None]
    col = col * (1 - light[..., None]) + c_light[None, None, :] * light[..., None]
    col = col * (1 - 0.05 * flake_step[..., None])
    col = col * (1 - warm[..., None]) + c_warm[None, None, :] * warm[..., None]
    pf = (np.clip(plate, 0, 1) ** 1.3)[..., None]
    col = col * pf + c_fis[None, None, :] * (1 - pf)
    col *= value_scale
    ao = np.clip(1.0 - 2.0 * np.clip(blur_wrap(H, 8) - H, 0, 1) - 0.4 * (1 - plate), 0.15, 1.0)
    rough = np.clip(0.9 - 0.08 * light + 0.05 * (1 - plate), 0, 1)
    return H, col, ao, rough


# ----------------------------------------------------------------------------- needles

NEEDLE_VARIANTS = {
    # v2: the f1 render measured median (58-64, 64-70, 34-41), hue 71-72 against the sheet's (83, 88, 49), hue
    # 66-68, P90 (131, 134, 94). Brighter, a touch warmer bodies and paler grey-green highlights; pale yellow
    # new-growth tips on one variant (the sheet's yellow specks); the render exposure is not changed to fake it.
    # v2 r6: the render measured hue 61-62 (too yellow: the warm key and translucency push it) against 66.6, and
    # P90 blue 74 against 94: greener bodies, bluer grey-green highlights; the yellow stays in the sheaths and tips
    0: dict(body=(124, 140, 78), tip=(146, 156, 98)),      # standard
    1: dict(body=(98, 116, 70), tip=(118, 132, 84)),       # darker older needles, a little bluer
    2: dict(body=(126, 140, 76), tip=(204, 190, 96)),      # new growth: pale yellow tips
    3: dict(body=(136, 156, 118), tip=(158, 170, 132)),    # glaucous grey-green highlight needles
}


def needle_cell(cw=16, ch=128, value_scale=1.0, variant=0):
    v = (np.arange(ch)[::-1] + 0.5) / ch          # image row 0 = top = v 1 (tip)
    u = (np.arange(cw) + 0.5) / cw
    U, Vv = np.meshgrid(u, v)
    base = srgb_to_lin((196, 184, 106))            # pale yellow-green sheath / fascicle base (v2: yellower)
    nv = NEEDLE_VARIANTS[variant]
    body = srgb_to_lin(nv["body"])
    tip = srgb_to_lin(nv["tip"])
    t = smoothstep(0.55, 1.0, Vv)[..., None]
    col = body * (1 - t) + tip * t
    across = 1.0 - 0.22 * (np.abs(U - 0.5) * 2) ** 2      # edges darker, midrib lighter
    col = col * across[..., None]
    sheath = smoothstep(0.10, 0.05, Vv)[..., None]
    col = col * (1 - sheath) + base * sheath
    col *= value_scale
    sss = np.clip(0.55 + 0.4 * Vv, 0, 1) * (0.85 + 0.15 * (1 - np.abs(U - 0.5) * 2))
    sss = np.where(Vv < 0.075, 0.25, sss)
    nx = (U - 0.5) * 2 * 0.65
    n = np.stack([nx, np.zeros_like(nx), np.sqrt(np.clip(1 - nx ** 2, 0, 1))], -1)
    n[..., 1] *= -1.0
    ao = np.clip(0.75 + 0.25 * smoothstep(0.0, 0.3, Vv), 0, 1)
    rough = np.full_like(Vv, 0.55)
    return col, sss, n, ao, rough


def tile_cells(a, nu=64, nv=8):
    return np.tile(a, (nv, nu) + (1,) * (a.ndim - 2))


def tile_variant_cells(cells, nu=64, nv=8):
    """cells: list of 4 cell images; column c uses variant pattern [0,1,0,2,0,3,1,0] (half standard needles)."""
    pattern = [0, 1, 0, 2, 0, 3, 1, 0]
    row = np.concatenate([cells[pattern[c % len(pattern)]] for c in range(nu)], axis=1)
    return np.concatenate([row] * nv, axis=0)


def rock_overlay(size=1024, seed=91):
    """T_DKN_RockOverlay_M (linear, 1 m tile): R = lichen speckle (crustose rosettes 0.5-4 cm, clustered),
    G = warm stain streaks running down the rock (vertical), B = fine grit. Our own procedural mask, applied over the
    shared granite (MI_DKN_PineRock) so the boulder reads darker, lichened and stained like the sheet's rock."""
    h = w = size
    rng = np.random.default_rng(seed)
    dens = smoothstep(0.45, 0.75, fbm(h, w, 5, 5, seed + 1, 3))
    lich = np.zeros((h, w))
    for (n, rmin, rmax) in ((1600, 0.003, 0.008), (400, 0.006, 0.014), (100, 0.012, 0.022)):
        F1, F2, _ = voronoi_periodic(h, w, int(np.sqrt(n)), int(np.sqrt(n)), seed + n, aniso=1.0)
        r = rng.uniform(rmin, rmax)
        lich = np.maximum(lich, smoothstep(r, 0.6 * r, F1))
    edge_noise = fbm(h, w, 64, 64, seed + 3, 2)
    lich = np.clip(lich * dens * (0.6 + 0.8 * edge_noise), 0, 1)
    streak = fbm(h, w, 1, 18, seed + 4, 3)                     # stretched down V
    stain = smoothstep(0.55, 0.8, streak) * smoothstep(0.3, 0.7, fbm(h, w, 3, 3, seed + 5, 2))
    grit = fbm(h, w, 200, 200, seed + 6, 2)
    return np.stack([lich, stain, grit], -1)


# ----------------------------------------------------------------------------- moss

def moss(size=1024, seed=71):
    h = w = size
    lump = fbm(h, w, 16, 16, seed, 4)
    fine = fbm(h, w, 128, 128, seed + 3, 2)
    H = 0.7 * lump + 0.3 * fine
    # v2: the sheet's mound moss is a light yellow-green (about sRGB 120-150, 125-150, 50-60 lit)
    c1 = srgb_to_lin((104, 112, 42))
    c2 = srgb_to_lin((150, 148, 62))
    c3 = srgb_to_lin((60, 68, 26))
    t = np.clip((H - 0.35) / 0.4, 0, 1)[..., None]
    col = c3 * (1 - t) + c2 * t
    col = col * 0.6 + c1 * 0.4 * (0.6 + 0.8 * fine[..., None])
    ao = np.clip(0.55 + 0.6 * H, 0, 1)
    rough = np.full_like(H, 0.92)
    return H, col, ao, rough


def soil(size=1024, seed=83):
    """v2 mound soil (2 m tile, like the moss): dark humus brown with needle litter streaks and small grit / pebbles."""
    h = w = size
    lump = fbm(h, w, 12, 12, seed, 4)
    fine = fbm(h, w, 160, 160, seed + 3, 2)
    F1, F2, _ = voronoi_periodic(h, w, 60, 60, seed + 5)
    peb = smoothstep(0.004, 0.0015, F1) * smoothstep(0.55, 0.75, fbm(h, w, 20, 20, seed + 6, 2))
    litter = smoothstep(0.62, 0.8, fbm(h, w, 90, 12, seed + 7, 2))
    c1 = srgb_to_lin((58, 44, 32))
    c2 = srgb_to_lin((92, 72, 52))
    c_peb = srgb_to_lin((140, 132, 120))
    c_lit = srgb_to_lin((118, 88, 56))
    t = np.clip((lump - 0.3) / 0.45, 0, 1)[..., None]
    col = c1 * (1 - t) + c2 * t
    col = col * (0.8 + 0.4 * fine[..., None])
    col = col * (1 - litter[..., None] * 0.6) + c_lit * litter[..., None] * 0.6
    col = col * (1 - peb[..., None]) + c_peb * peb[..., None]
    H = 0.6 * lump + 0.25 * fine + 0.35 * peb
    ao = np.clip(0.6 + 0.5 * H, 0, 1)
    rough = np.full_like(H, 0.95)
    return H, col, ao, rough


def save_rgb(path, arr8):
    Image.fromarray(arr8).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bark-scale", type=float, default=1.0)
    ap.add_argument("--needle-value", type=float, default=1.0)
    a = ap.parse_args()
    TEX.mkdir(parents=True, exist_ok=True)
    (BUILD / "tex").mkdir(parents=True, exist_ok=True)
    rep = {}
    H, col, ao, rough = bark_v2(value_scale=a.bark_scale)
    np.save(BUILD / "tex" / "bark_height.npy", np.flipud(H).astype(np.float32))   # rows = V from the bottom
    save_rgb(TEX / "T_DKN_Bark_BC.png", to_srgb8(col))
    save_rgb(TEX / "T_DKN_Bark_N.png", normal_from_height(H, 0.110, 1.0 / 1024))
    orm = np.stack([ao, rough, np.zeros_like(ao)], -1)
    save_rgb(TEX / "T_DKN_Bark_ORM.png", (np.clip(orm, 0, 1) * 255 + 0.5).astype(np.uint8))
    bc8 = to_srgb8(col).reshape(-1, 3).astype(float)
    L = bc8 @ np.array([0.2126, 0.7152, 0.0722])
    rep["bark"] = {"median": np.median(bc8, 0).round().tolist(), "p10": np.percentile(bc8, 10, 0).round().tolist(),
                   "p90": np.percentile(bc8, 90, 0).round().tolist(),
                   "luma_p90_p10": round(float(np.percentile(L, 90) / max(np.percentile(L, 10), 1)), 2),
                   "tile_m": 1.0, "px": 1024, "px_per_cm": 10.24}
    cells = [needle_cell(value_scale=a.needle_value, variant=k) for k in range(4)]
    col, sss, n, ao_n, rough_n = cells[0]
    save_rgb(TEX / "T_DKN_Needle_BC.png", tile_variant_cells([to_srgb8(c[0]) for c in cells]))
    save_rgb(TEX / "T_DKN_Needle_N.png", tile_cells(((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)))
    orm = np.stack([ao_n, rough_n, np.zeros_like(ao_n)], -1)
    save_rgb(TEX / "T_DKN_Needle_ORM.png", tile_cells((np.clip(orm, 0, 1) * 255 + 0.5).astype(np.uint8)))
    Image.fromarray(tile_cells((np.clip(sss, 0, 1) * 255 + 0.5).astype(np.uint8))).save(TEX / "T_DKN_Needle_SSS.png")
    body = np.concatenate([to_srgb8(c[0])[10:110].reshape(-1, 3) for c in cells]).astype(float)
    rep["needle"] = {"body_median_srgb": np.median(body, 0).round().tolist(), "cells": [64, 8], "cell_px": [16, 128],
                     "variants": {k: v for k, v in NEEDLE_VARIANTS.items()}, "column_pattern": [0, 1, 0, 2, 0, 3, 1, 0]}
    ov = rock_overlay()
    save_rgb(TEX / "T_DKN_RockOverlay_M.png", (np.clip(ov, 0, 1) * 255 + 0.5).astype(np.uint8))
    rep["rock_overlay"] = {"R": "lichen speckle", "G": "warm stain streaks", "B": "grit", "tile_m": 1.0,
                           "lichen_share": round(float((ov[..., 0] > 0.5).mean()), 3),
                           "stain_share": round(float((ov[..., 1] > 0.5).mean()), 3)}
    Hm, colm, aom, roughm = moss()
    save_rgb(TEX / "T_DKN_Moss_BC.png", to_srgb8(colm))
    save_rgb(TEX / "T_DKN_Moss_N.png", normal_from_height(Hm, 0.006, 2.0 / 1024))
    orm = np.stack([aom, roughm, np.zeros_like(aom)], -1)
    save_rgb(TEX / "T_DKN_Moss_ORM.png", (np.clip(orm, 0, 1) * 255 + 0.5).astype(np.uint8))
    rep["moss"] = {"median": np.median(to_srgb8(colm).reshape(-1, 3), 0).round().tolist(), "tile_m": 2.0}
    Hs, cols, aos, roughs = soil()
    save_rgb(TEX / "T_DKN_Soil_BC.png", to_srgb8(cols))
    save_rgb(TEX / "T_DKN_Soil_N.png", normal_from_height(Hs, 0.006, 2.0 / 1024))
    save_rgb(TEX / "T_DKN_Soil_ORM.png", (np.clip(np.stack([aos, roughs, np.zeros_like(aos)], -1), 0, 1) * 255 + 0.5
                                          ).astype(np.uint8))
    rep["soil"] = {"median": np.median(to_srgb8(cols).reshape(-1, 3), 0).round().tolist(), "tile_m": 2.0}
    rep["args"] = vars(a)
    (BUILD / "textures_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
