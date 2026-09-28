"""Dev tool (look-match): draw the designed plate outlines / blossom circles over a reference crop.

    blender -b --factory-startup --python shv4_design_overlay.py -- --part throat --out <png> [--scale 5]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "shv4_lib"))
import sfv4_png as PNG  # noqa: E402
import shv4_spec as S  # noqa: E402
import shv4_plates as PL  # noqa: E402

REF = S.ROOT / "References" / "SnowFlower" / "SnowFlower_sheath_reference.png"
CROPS = {"throat": (25, 178, 425, 590), "chape": (1240, 1500, 440, 570), "band": (262, 345, 430, 580)}
COLS = [(1, 0.1, 0.1), (0.1, 0.9, 0.2), (0.2, 0.5, 1.0), (1, 0.8, 0.1), (1, 0.2, 1), (0.1, 1, 1)]


def load(path):
    im = bpy.data.images.load(str(path))
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1][..., :3].copy()
    return a


def draw_poly(img, P, col, sc, r0, x0, closed=True):
    H, W = img.shape[:2]
    P = np.asarray(P, float)
    if closed:
        P = np.vstack([P, P[:1]])
    for (xa, ra), (xb, rb) in zip(P[:-1], P[1:]):
        n = int(max(abs(xb - xa), abs(rb - ra)) * sc * 2) + 2
        for t in np.linspace(0, 1, n):
            x = int(((xa + (xb - xa) * t) - x0) * sc)
            y = int(((ra + (rb - ra) * t) - r0) * sc)
            if 0 <= x < W and 0 <= y < H:
                img[max(y - 1, 0):y + 1, max(x - 1, 0):x + 1] = col


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="throat")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=5)
    a = ap.parse_args(argv)
    ref = load(REF)
    r0, r1, x0, x1 = CROPS[a.part]
    sc = a.scale
    crop = PNG.upscale(ref[r0:r1, x0:x1], sc).copy()
    table = {"throat": S.THROAT_LEAVES, "chape": getattr(S, "CHAPE_LEAVES", []),
             "band": getattr(S, "BAND_LEAVES", [])}[a.part]
    env = {"throat": "crown", "chape": "chape", "band": "core"}[a.part]
    leaves = PL.expand(PL.leaves_from(table, env))
    for k, (tag, lf) in enumerate(leaves):
        draw_poly(crop, PL.leaf_outline_px(lf), COLS[k % len(COLS)], sc, r0, x0)
        sp = [(S.X_AXIS_PX + dx, r) for dx, r in lf.spine]
        draw_poly(crop, sp, COLS[k % len(COLS)], sc, r0, x0, closed=False)
    blos = {"throat": [S.THROAT_BLOSSOM], "chape": [S.CHAPE_BLOSSOM], "band": [S.BAND_BLOSSOM]}[a.part]
    for (xpx, row), d in blos:
        th = np.linspace(0, 2 * np.pi, 80)
        draw_poly(crop, np.c_[xpx + d / 2 * np.cos(th), row + d / 2 * np.sin(th)], (1, 1, 1), sc, r0, x0)
    PNG.write_png(a.out, crop)
    print("OVERLAY_OK", a.out)


if __name__ == "__main__":
    main()
