"""Per-texel painter helpers for gun texture sets (numpy + PIL; runs in plain Python).

Generalised from the katana painter (Scripts/Katana/katana_tex.py): value noise / fBm in 3D (world mm), wood rings in
a virtual blank, directional scratches, normal maps from painted height (tangent frame = the texel's UV directions,
measured from the baked position map, so island rotations and stretch are handled), whiteout blending with a baked
normal, sRGB conversion and the PNG writers. Arrays are the bake's (rows bottom-up); writers flip to PNG order.
"""
from __future__ import annotations

import math

import numpy as np


# ---------------------------------------------------------------- colour
def srgb_to_lin(c):
    c = np.asarray(c, float)
    c = c / 255.0 if c.max() > 1.0 else c
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- noise
def _hash(ix, iy, iz, seed=0):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) \
        ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return ((h & 0xFFFFFF).astype(np.float32)) / float(0xFFFFFF)


def vnoise3(p, seed=0):
    """Value noise in [0, 1] at points p (N, 3), unit lattice."""
    p = np.asarray(p, np.float32)
    i = np.floor(p).astype(np.int64)
    f = p - i
    u = f * f * (3 - 2 * f)
    out = np.zeros(len(p), np.float32)
    for dx in (0, 1):
        wx = u[:, 0] if dx else 1 - u[:, 0]
        for dy in (0, 1):
            wy = u[:, 1] if dy else 1 - u[:, 1]
            for dz in (0, 1):
                wz = u[:, 2] if dz else 1 - u[:, 2]
                out += wx * wy * wz * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm3(p, scale_mm, octaves=4, seed=0, gain=0.5):
    """fBm in [0, 1] of world points p (mm) with the first octave at `scale_mm`."""
    q = np.asarray(p, np.float32) / scale_mm
    out = np.zeros(len(q), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * vnoise3(q, seed + 7 * o)
        tot += amp
        amp *= gain
        q = q * 2.03 + 17.1
    return out / tot


def chunked(fn, P, *a, chunk=1 << 20, **k):
    out = np.empty(len(P), np.float32)
    for s in range(0, len(P), chunk):
        out[s:s + chunk] = fn(P[s:s + chunk], *a, **k)
    return out


def aniso(p, axis, along_mm, across_mm, octaves=3, seed=0):
    """Streaky noise stretched along `axis` (grain pores, sliding scratches)."""
    a = np.asarray(axis, np.float32)
    a = a / np.linalg.norm(a)
    t = np.array([0, 0, 1], np.float32) if abs(a[2]) < 0.9 else np.array([1, 0, 0], np.float32)
    b = np.cross(a, t)
    b /= np.linalg.norm(b)
    c = np.cross(a, b)
    q = np.c_[p @ a / along_mm, p @ b / across_mm, p @ c / across_mm]
    return fbm3(q, 1.0, octaves, seed)


def wood_rings(p, axis, pith, spacing_mm=1.6, warp_mm=2.5, seed=3):
    """Growth rings of a virtual blank: distance to a pith line (parallel to `axis` through `pith`), warped by
    low-frequency noise; returns (ring phase 0..1, radius mm)."""
    a = np.asarray(axis, np.float32)
    a = a / np.linalg.norm(a)
    d = np.asarray(p, np.float32) - np.asarray(pith, np.float32)
    rad = d - np.outer(d @ a, a)
    r = np.linalg.norm(rad, axis=1)
    w = (chunked(fbm3, p, 22.0, 3, seed) - 0.5) * 2 * warp_mm + (chunked(fbm3, p, 6.0, 2, seed + 11) - 0.5) * 0.6
    ph = ((r + w) / spacing_mm) % 1.0
    return ph, r


def scratch_patches(p, cell_mm, along_mm, across_mm, seed=0, ndir=5, octaves=2):
    """Short directional scratches whose direction changes from patch to patch (real handling scratches run in mixed
    directions, clustered where something rubs; one global direction reads as brushed metal): each texel takes one of
    `ndir` hashed 3D directions from the coarse cell (cell_mm) it lies in, and the streaky noise along it."""
    p = np.asarray(p, np.float32)
    rng = np.random.default_rng(seed)
    dirs = rng.normal(size=(ndir, 3)).astype(np.float32)
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    c = np.floor(p / cell_mm).astype(np.int64)
    k = np.minimum((_hash(c[:, 0], c[:, 1], c[:, 2], seed + 3) * ndir).astype(int), ndir - 1)
    out = np.zeros(len(p), np.float32)
    for i in range(ndir):
        sel = k == i
        if sel.any():
            out[sel] = chunked(aniso, p[sel], dirs[i], along_mm, across_mm, octaves, seed + 11 * i)
    return out


def flow_coords(P, ax, up, bin_mm=6.0, q=(2.0, 98.0), smooth=3, min_count=40, rigid=False):
    """Form-following wood coordinates of a furniture part (texel points P, mm): u along `ax`; s = the normalised height
    between the part's lower and upper outline along `up` AT THAT u (0 = lower outline, 1 = upper); w across (ax x up).
    The outlines are robust per-bin percentiles of the part's own texel positions, smoothed, so a grain line s = const
    runs with the part's form (a stock's drop through the wrist, a grip's lean) the way a blank's grain is laid out
    along the piece. Returns u, s, w, the outline span H(u) (mm), the median span, and the local grain tangent T (unit,
    the direction of the line s = const at the point)."""
    from scipy.ndimage import uniform_filter1d
    ax = np.asarray(ax, np.float32) / np.linalg.norm(ax)
    up = np.asarray(up, np.float32)
    up = up - ax * float(up @ ax)
    up /= np.linalg.norm(up)
    cr = np.cross(ax, up)
    u, h, w = P @ ax, P @ up, P @ cr
    u0, u1 = np.percentile(u, 0.5), np.percentile(u, 99.5)
    nb = max(4, int(math.ceil((u1 - u0) / bin_mm)) + 1)
    c = np.linspace(u0, u1, nb)
    lo = np.full(nb, np.nan)
    hi = np.full(nb, np.nan)
    k = np.clip(np.round((u - u0) / max(c[1] - c[0], 1e-6)).astype(int), 0, nb - 1)
    order = np.argsort(k)
    ks, hs = k[order], h[order]
    cuts = np.searchsorted(ks, np.arange(nb + 1))
    for i in range(nb):
        hh = hs[cuts[i]:cuts[i + 1]]
        if len(hh) >= min_count:
            lo[i], hi[i] = np.percentile(hh, q[0]), np.percentile(hh, q[1])
    ok = np.isfinite(lo)
    lo = np.interp(c, c[ok], lo[ok])
    hi = np.interp(c, c[ok], hi[ok])
    if rigid:
        # straight pieces (the handguards): one lower / upper line for the whole piece. Per-u outlines followed the
        # vent slots and the liner channel inside (all of a part's texels count), so the rings stepped into a
        # trapezoid there (realism-fix round 2026-10-07, 'trapezoid bleeding through the upper handguard')
        lo[:] = np.percentile(h, q[0])
        hi[:] = np.percentile(h, q[1])
    lo = uniform_filter1d(lo, 2 * smooth + 1, mode="nearest")
    hi = uniform_filter1d(hi, 2 * smooth + 1, mode="nearest")
    hi = np.maximum(hi, lo + 5.0)
    dlo, dhi = np.gradient(lo, c), np.gradient(hi, c)
    L, Hh = np.interp(u, c, lo), np.interp(u, c, hi)
    span = Hh - L
    s = (h - L) / span
    slope = np.interp(u, c, dlo) + np.clip(s, 0, 1) * (np.interp(u, c, dhi) - np.interp(u, c, dlo))
    T = ax[None, :] + slope[:, None] * up[None, :]
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    return (u.astype(np.float32), s.astype(np.float32), w.astype(np.float32), span.astype(np.float32),
            float(np.median(hi - lo)), T.astype(np.float32))


def ring_phase(v, w, u, pith_vw, spacing_mm, seed, warp_mm=(4.0, 0.7), warp_len=(140.0, 30.0)):
    """Growth-ring phase (0..1) of a virtual blank in straightened wood coordinates (u along the grain, v / w across,
    mm): distance to a pith line at pith_vw, warped smoothly along the grain (long, gentle undulation -> elongated
    cathedral arches where the surface cuts the rings; a weak shorter wave), and IRREGULAR ring widths (a 1D noise of
    the radius stretches and squeezes the spacing, 0.6-1.6x, as real seasons do). Returns (phase, ring index)."""
    r = np.hypot(v - pith_vw[0], w - pith_vw[1])
    Q1 = np.stack([u / warp_len[0], v / (warp_len[0] * 0.3), w / (warp_len[0] * 0.3)], 1)
    Q2 = np.stack([u / warp_len[1], v / (warp_len[1] * 0.4), w / (warp_len[1] * 0.4)], 1)
    rw = r + (chunked(fbm3, Q1, 1.0, 3, seed) - 0.5) * 2 * warp_mm[0] \
        + (chunked(fbm3, Q2, 1.0, 2, seed + 5) - 0.5) * 2 * warp_mm[1]
    # irregular widths: phase = (r + A(r)) / spacing with A a smooth noise of r (cumulative widths)
    R1 = np.stack([rw / (spacing_mm * 2.7), np.full_like(rw, 3.1), np.full_like(rw, 7.7)], 1)
    rr = rw + (chunked(vnoise3, R1, seed + 9) - 0.5) * 1.2 * spacing_mm      # d/dr <= ~0.65: no ring reversal
    x = rr / spacing_mm
    return (x % 1.0).astype(np.float32), np.floor(x).astype(np.int64)


# ---------------------------------------------------------------- normals
def mm_per_px(pos_mm, valid):
    """Texel size (mm per px) along U (columns) and V (rows) from the baked position map (central differences inside
    one island; edges one-sided)."""
    du = np.zeros(pos_mm.shape[:2], np.float32)
    dv = np.zeros(pos_mm.shape[:2], np.float32)
    du[:, 1:-1] = np.linalg.norm(pos_mm[:, 2:] - pos_mm[:, :-2], axis=2) * 0.5
    dv[1:-1, :] = np.linalg.norm(pos_mm[2:] - pos_mm[:-2], axis=2) * 0.5
    return du, dv


def height_to_normal(h, isl, du_mm, dv_mm, max_slope=3.0):
    """Tangent-space normal (OpenGL: +X = +U, +Y = +V) from a height map h (mm) on the atlas; differences only between
    texels of the same island (one-sided at island borders, 0 across gutters)."""
    H, W = h.shape
    gx = np.zeros_like(h)
    gy = np.zeros_like(h)
    same_r = np.zeros((H, W), bool)
    same_l = np.zeros((H, W), bool)
    same_r[:, :-1] = isl[:, :-1] == isl[:, 1:]
    same_l[:, 1:] = isl[:, 1:] == isl[:, :-1]
    hr = np.zeros_like(h)
    hl = np.zeros_like(h)
    hr[:, :-1] = h[:, 1:]
    hl[:, 1:] = h[:, :-1]
    both = same_r & same_l
    gx = np.where(both, (hr - hl) * 0.5, np.where(same_r, hr - h, np.where(same_l, h - hl, 0.0)))
    same_u = np.zeros((H, W), bool)
    same_d = np.zeros((H, W), bool)
    same_u[:-1, :] = isl[:-1, :] == isl[1:, :]
    same_d[1:, :] = isl[1:, :] == isl[:-1, :]
    hu = np.zeros_like(h)
    hd = np.zeros_like(h)
    hu[:-1, :] = h[1:, :]
    hd[1:, :] = h[:-1, :]
    both = same_u & same_d
    gy = np.where(both, (hu - hd) * 0.5, np.where(same_u, hu - h, np.where(same_d, h - hd, 0.0)))
    sx = np.clip(gx / np.maximum(du_mm, 1e-4), -max_slope, max_slope)
    sy = np.clip(gy / np.maximum(dv_mm, 1e-4), -max_slope, max_slope)
    n = np.stack([-sx, -sy, np.ones_like(sx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def whiteout(n1, n2):
    """Blend two tangent-space normals (detail n2 over base n1)."""
    n = np.stack([n1[..., 0] + n2[..., 0], n1[..., 1] + n2[..., 1], n1[..., 2] * n2[..., 2]], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


# ---------------------------------------------------------------- writers (bake rows are bottom-up -> PNG top-down)
def to_u8(x):
    return (np.clip(x, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def write_png(path, arr01, mode="RGB"):
    from PIL import Image
    a = to_u8(np.asarray(arr01))[::-1]
    if a.ndim == 2:
        Image.fromarray(a, "L").save(path, optimize=False, compress_level=6)
    else:
        Image.fromarray(a, mode).save(path, optimize=False, compress_level=6)


def normal_to_dx(n):
    """Tangent-space normal (OpenGL) -> DirectX-encoded RGB 0..1 (green flipped)."""
    return np.stack([n[..., 0] * 0.5 + 0.5, -n[..., 1] * 0.5 + 0.5, n[..., 2] * 0.5 + 0.5], -1)


def dilate_fill(arr, valid, iters=24):
    """Fill invalid texels from valid neighbours (gutter bleed for mips), iteratively."""
    a = arr.copy()
    v = valid.copy()
    for _ in range(iters):
        if v.all():
            break
        acc = np.zeros_like(a, dtype=np.float32)
        cnt = np.zeros(v.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sv = np.roll(v, (dy, dx), (0, 1))
            sa = np.roll(a, (dy, dx), (0, 1))
            m = sv & ~v
            if a.ndim == 3:
                acc[m] += sa[m]
            else:
                acc[m] += sa[m]
            cnt[m] += 1
        new = cnt > 0
        if a.ndim == 3:
            a[new] = acc[new] / cnt[new][:, None]
        else:
            a[new] = acc[new] / cnt[new]
        v = v | new
    return a


def write_png16(path, arr01):
    """16-bit RGB PNG (own writer: PIL saves no 16-bit RGB). For normal maps: 8 bits cannot hold 0.5, and the
    constant 0.0055 tilt of an 8-bit flat (128, 128) turns with each island's tangent frame, which draws seams along
    island borders under a glossy highlight; at 16 bits the flat is 0.5 to 1.5e-5 (Unreal's BC5 keeps it within
    ~5e-4)."""
    import struct
    import zlib
    a = np.asarray(arr01, np.float64)[::-1]
    h, w, c = a.shape
    q = (np.clip(a, 0.0, 1.0) * 65535.0 + 0.5).astype(">u2")
    raw = b"".join(b"\x00" + q[r].tobytes() for r in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
