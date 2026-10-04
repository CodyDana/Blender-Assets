"""Katana atlas packer (adapted copy of the Snow Flower v4 skyline packer; that file is not imported).

Islands carry local UVs in millimetres. Each island is placed once (skyline packing, optional 90 deg rotation) at ONE
texel density per atlas (times a per-island scale: hidden faces get fewer texels), found by bisection; the same
transform is applied to every LOD. The steel atlas is UV0 tile u 0..1, the grip atlas tile u 1..2 (the two never
overlap in UV0). A separate uniform pack of every island into 0..1 gives UV1 (lightmap).
"""
from __future__ import annotations

import json
import math
from typing import Callable, Dict

import numpy as np


class Atlas:
    def __init__(self, size, pad_px, u_offset=0.0):
        self.size = size
        self.pad = pad_px
        self.u_offset = u_offset
        self.place: Dict[str, dict] = {}
        self.density = None  # px per mm

    def transform(self, island, uv):
        p = self.place[island]
        uv = np.asarray(uv, float)
        loc = uv - np.array([p["umin"], p["vmin"]])
        if p["rot"]:
            loc = np.stack([p["h_mm"] - loc[:, 1], loc[:, 0]], 1)
        px = loc * self.density * p.get("scale", 1.0) + np.array([p["x"], p["y"]])
        out = px / self.size
        out[:, 0] += self.u_offset
        return out

    def px_per_mm(self, island):
        return self.density * self.place[island].get("scale", 1.0)


def _skyline(boxes, size, pad):
    items = sorted(boxes, key=lambda t: -max(t[1], t[2]))
    sky = [(0, size, 0)]
    out = {}
    for bid, w, h in items:
        best = None
        for rot in (False, True):
            W, H = (h, w) if rot else (w, h)
            W += 2 * pad
            H += 2 * pad
            if W > size:
                continue
            for i in range(len(sky)):
                x = sky[i][0]
                if x + W > size:
                    break
                y = 0
                wleft = W
                j = i
                while wleft > 0 and j < len(sky):
                    y = max(y, sky[j][2])
                    wleft -= sky[j][1]
                    j += 1
                if wleft > 0 or y + H > size:
                    continue
                score = (y + H, x)
                if best is None or score < best[0]:
                    best = (score, x, y, W, H, rot)
        if best is None:
            return None
        _, x, y, W, H, rot = best
        out[bid] = (x + pad, y + pad, rot)
        new = []
        for (sx, sw, sy) in sky:
            ex = sx + sw
            if ex <= x or sx >= x + W:
                new.append((sx, sw, sy))
                continue
            if sx < x:
                new.append((sx, x - sx, sy))
            if ex > x + W:
                new.append((x + W, ex - (x + W), sy))
        new.append((x, W, y + H))
        new.sort()
        merged = []
        for seg in new:
            if merged and merged[-1][2] == seg[2] and merged[-1][0] + merged[-1][1] == seg[0]:
                merged[-1] = (merged[-1][0], merged[-1][1] + seg[1], seg[2])
            else:
                merged.append(seg)
        sky = merged
    return out


def pack(islands: Dict[str, np.ndarray], size, pad, u_offset=0.0, scale_fn: Callable[[str], float] = None,
         max_density=40.0):
    bb = {}
    for k, pts in islands.items():
        umin, vmin = pts.min(axis=0)
        umax, vmax = pts.max(axis=0)
        bb[k] = (umin, vmin, max(umax - umin, 0.05), max(vmax - vmin, 0.05))
    sc = {k: (scale_fn(k) if scale_fn else 1.0) for k in bb}
    lo, hi = 0.05, max_density
    best = None
    for _ in range(32):
        d = 0.5 * (lo + hi)
        boxes = [(k, math.ceil(w * d * sc[k]) + 1, math.ceil(h * d * sc[k]) + 1) for k, (_, _, w, h) in bb.items()]
        res = _skyline(boxes, size, pad)
        if res is None:
            hi = d
        else:
            lo = d
            best = (d, res)
    if best is None:
        raise RuntimeError("atlas pack failed")
    d, res = best
    at = Atlas(size, pad, u_offset)
    at.density = d
    for k, (x, y, rot) in res.items():
        umin, vmin, w, h = bb[k]
        at.place[k] = {"x": x, "y": y, "rot": bool(rot), "umin": umin, "vmin": vmin, "w_mm": w, "h_mm": h,
                       "scale": sc[k]}
    return at


def coverage_fraction(at: Atlas):
    tot = sum((p["w_mm"] * at.density * p.get("scale", 1)) * (p["h_mm"] * at.density * p.get("scale", 1))
              for p in at.place.values())
    return tot / (at.size * at.size)


def save(at: Atlas, path):
    json.dump({"size": at.size, "pad": at.pad, "u_offset": at.u_offset, "density_px_per_mm": at.density,
               "place": at.place}, open(path, "w"), indent=1)


def load(path):
    d = json.load(open(path))
    at = Atlas(d["size"], d["pad"], d["u_offset"])
    at.density = d["density_px_per_mm"]
    at.place = d["place"]
    return at
