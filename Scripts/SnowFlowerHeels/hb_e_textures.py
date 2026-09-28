"""Stage E: authored texture sources (numpy only; Blender's bundled python, run inside Blender for the insole mapping).

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_e_textures.py

Writes r1/tex/:
  floral_emboss.png  - tileable 1024 height map: tone-on-tone blossoms and branches for the vamp leather (the reference
                       shows dark blossoms/branches embossed on black; drawn plainly, no invented motif)
  grain.png          - tileable 1024 fine leather grain (height)
  insole_print.png   - 2048 insole base colour in the insole's planar UV: charcoal ground, lighter centre band, the
                       kite emblem at the heel seat and the printed blossom branch, placed where view A shows them
  insole_uv.json     - the planar mapping (local u, v mm -> uv)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hb_common as C  # noqa: E402
import metro_png as png  # noqa: E402

OUT = C.R1 / "tex"
RNG = np.random.default_rng(7)


def disk_stamp(img, cx, cy, r, val, soft=1.0, mode="max"):
    H, W = img.shape
    x0, x1 = int(max(cx - r - 2, 0)), int(min(cx + r + 3, W))
    y0, y1 = int(max(cy - r - 2, 0)), int(min(cy + r + 3, H))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.hypot(xx - cx, yy - cy)
    a = np.clip((r - d) / soft + 0.5, 0, 1) * val
    if mode == "max":
        img[y0:y1, x0:x1] = np.maximum(img[y0:y1, x0:x1], a)
    else:
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - np.clip((r - d) / soft + 0.5, 0, 1)) + a


def petal_mask(H, W, cx, cy, R, rot, petals=5, notch=True):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    dx, dy = xx - cx, yy - cy
    r = np.hypot(dx, dy) / R
    th = np.arctan2(dy, dx) - rot
    k = petals
    ph = (th * k / (2 * np.pi)) % 1.0 - 0.5          # -0.5..0.5 within a petal
    shape = 0.95 * np.cos(np.pi * ph) ** 0.55          # petal radius profile
    if notch:
        shape -= 0.18 * np.exp(-(ph / 0.07) ** 2)
    m = np.clip((shape - r) * R / 1.2 + 0.5, 0, 1)
    # vein/edge relief: brighter toward the rim
    rel = np.clip(r / np.maximum(shape, 1e-3), 0, 1)
    return m, rel


def stroke(img, pts, width, val):
    pts = np.asarray(pts, float)
    for a, b in zip(pts[:-1], pts[1:]):
        L = max(np.linalg.norm(b - a), 1e-6)
        n = int(L / 0.7) + 1
        for t in np.linspace(0, 1, n):
            p = a + (b - a) * t
            disk_stamp(img, p[0], p[1], width / 2, val, 0.8)


def wrap_draw(size, draw):
    """Draw on a 3x3 canvas and fold back to make a tileable image."""
    big = np.zeros((size * 3, size * 3))
    draw(big, size)
    out = np.zeros((size, size))
    for i in range(3):
        for j in range(3):
            out = np.maximum(out, big[i * size:(i + 1) * size, j * size:(j + 1) * size])
    return out


def floral(size=1024):
    def draw(big, s):
        # branches: wandering curves, blossoms along them, buds
        for _ in range(24):
            p = np.array([RNG.uniform(s, 2 * s), RNG.uniform(s, 2 * s)])
            ang = RNG.uniform(0, 2 * np.pi)
            pts = [p.copy()]
            for _k in range(26):
                ang += RNG.normal(0, 0.28)
                p = p + 14 * np.array([math.cos(ang), math.sin(ang)])
                pts.append(p.copy())
                if RNG.random() < 0.18:        # twig
                    a2 = ang + RNG.choice([-1, 1]) * RNG.uniform(0.6, 1.1)
                    q = p.copy()
                    tw = [q.copy()]
                    for _j in range(4):
                        q = q + 10 * np.array([math.cos(a2), math.sin(a2)])
                        tw.append(q.copy())
                    stroke(big, tw, 2.2, 0.55)
                    disk_stamp(big, q[0], q[1], 4.5, 0.75, 1.2)
            stroke(big, pts, 3.4, 0.6)
            for idx in RNG.choice(len(pts), 4, replace=False):
                cx, cy = pts[idx]
                R = RNG.uniform(12, 24)
                x0, y0 = int(cx - R - 3), int(cy - R - 3)
                m, rel = petal_mask(int(2 * R + 6), int(2 * R + 6), R + 3, R + 3, R, RNG.uniform(0, 2 * np.pi))
                h = m * (0.55 + 0.45 * rel)
                sl = big[y0:y0 + h.shape[0], x0:x0 + h.shape[1]]
                sl[:] = np.maximum(sl, h[:sl.shape[0], :sl.shape[1]])
                disk_stamp(big, cx, cy, R * 0.18, 0.35, 1.0, mode="set")
    return wrap_draw(size, draw)


def grain(size=1024):
    """Fine pebble grain: sum of jittered cell bumps (tileable by construction)."""
    img = np.zeros((size, size))
    n = 9000
    xs = RNG.uniform(0, size, n)
    ys = RNG.uniform(0, size, n)
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    # accumulate small bumps via splatting on a coarse grid: use FFT convolution of a point map with a bump kernel
    pts = np.zeros((size, size))
    np.add.at(pts, (ys.astype(int) % size, xs.astype(int) % size), RNG.uniform(0.6, 1.0, n))
    r = 4.0
    k = np.exp(-((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (2 * r * r))
    k = np.fft.ifftshift(k)
    img = np.real(np.fft.ifft2(np.fft.fft2(pts) * np.fft.fft2(k)))
    img -= img.min()
    img /= img.max()
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fl = floral()
    png.write(str(OUT / "floral_emboss.png"), (np.clip(fl, 0, 1) * 255).astype(np.uint8))
    gr = grain()
    png.write(str(OUT / "grain.png"), (gr * 255).astype(np.uint8))
    print("TEX floral/grain ok")


if __name__ == "__main__":
    main()
