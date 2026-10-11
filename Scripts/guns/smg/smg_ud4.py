"""SMG01 gate UD4 (plain Python): the authored UV1 (lightmap) at 64 and 128 px with 2 px padding.

    py -3 -B Scripts/guns/smg/smg_ud4.py [--npz scratch/uv/uv1_lod0.npz] [--json scratch/uv/ud4.json]

Input: every LOD0 triangle's UV1 and its lightmap chart id (smg_uv: -1 = a hidden face collapsed to a point). Per
resolution R: each chart rasterised conservatively (a texel is taken when any of the chart's triangles reaches within
half a texel diagonal of its centre: what a lightmap baker can touch), then grown by the padding (2 px, Chebyshev);
UD4 counts texels where a chart's grown footprint meets another chart's own texels (0 = every pair of charts at least
2 empty texels apart), texels outside 0..1, and zero-area (collapsed) triangles, which take no texel and are left out.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SCRATCH  # noqa: E402


def raster(T, R):
    """Conservative raster of triangles T (n, 3, 2) in UV 0..1 at R x R -> bool (R, R)."""
    M = np.zeros((R, R), bool)
    r = 0.7072
    P = T * R
    for tri in P:
        lo = np.floor(tri.min(0) - r).astype(int)
        hi = np.ceil(tri.max(0) + r).astype(int)
        x0, y0, x1, y1 = max(lo[0], 0), max(lo[1], 0), min(hi[0], R), min(hi[1], R)
        if x1 <= x0 or y1 <= y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        a = tri
        ar = (a[1, 0] - a[0, 0]) * (a[2, 1] - a[0, 1]) - (a[2, 0] - a[0, 0]) * (a[1, 1] - a[0, 1])
        sg = 1.0 if ar >= 0 else -1.0
        ok = np.ones(X.shape, bool)
        for k in range(3):
            p, q = a[k], a[(k + 1) % 3]
            e = q - p
            L = math.hypot(e[0], e[1])
            if L < 1e-12:
                continue
            ok &= sg * ((X - p[0]) * e[1] - (Y - p[1]) * e[0]) / L <= r
        M[y0:y1, x0:x1] |= ok
    return M


def grow(M, d):
    out = M.copy()
    for dy in range(-d, d + 1):
        for dx in range(-d, d + 1):
            out |= np.roll(np.roll(M, dy, 0), dx, 1) if (dy or dx) else M
    # (np.roll wraps: clear the wrapped bands)
    return out


def measure(tris, chart, R, pad):
    e1, e2 = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    real = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) > 1e-12
    own = np.zeros((R, R), np.int32)               # texels taken per chart count
    first = np.full((R, R), -1, np.int32)
    grown_hits = 0
    rasters = {}
    for c in np.unique(chart[(chart >= 0) & real]):
        rasters[int(c)] = raster(tris[(chart == c) & real], R)
    taken = np.zeros((R, R), np.int32)
    for c, M in rasters.items():
        taken += M
    for c, M in rasters.items():
        Mp = np.pad(M, pad)
        G = np.zeros_like(Mp)
        for dy in range(-pad, pad + 1):
            for dx in range(-pad, pad + 1):
                G[pad + dy:pad + dy + R, pad + dx:pad + dx + R] |= M
        G = G[pad:pad + R, pad:pad + R]
        others = taken - M.astype(np.int32)
        grown_hits += int((G & (others > 0)).sum())
    out_of_range = int(((tris < -1e-6) | (tris > 1 + 1e-6)).any(axis=(1, 2)).sum())
    return {"resolution": R, "padding_px": pad, "charts": len(rasters),
            "texels_shared_by_two_charts": int((taken > 1).sum()),
            "padding_violations_texels": grown_hits, "triangles_outside_0_1": out_of_range,
            "collapsed_triangles": int((~real).sum()), "texels_used": int((taken > 0).sum()),
            "pass": grown_hits == 0 and out_of_range == 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(SCRATCH / "uv" / "uv1_lod0.npz"))
    ap.add_argument("--json", default=str(SCRATCH / "uv" / "ud4.json"))
    a = ap.parse_args()
    d = np.load(a.npz)
    tris, chart = d["tris"].astype(np.float64), d["chart"]
    res = {"input": Path(a.npz).name, "rows": [measure(tris, chart, R, 2) for R in (64, 128)]}
    res["pass"] = all(r["pass"] for r in res["rows"])
    Path(a.json).write_text(json.dumps(res, indent=1))
    for r in res["rows"]:
        print("[UD4]", json.dumps(r))
    print("[UD4]", "PASS" if res["pass"] else "FAIL")


if __name__ == "__main__":
    main()
