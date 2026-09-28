"""pd_r2_slices.py -- horizontal cross-sections through the jaw ramus (no Unreal).

Run with Blender's bundled Python (numpy). For each mesh, slices the surface with planes z = const (UE world cm) on
the character's left side (+X) and right side (-X, mirrored), keeps the outline between the cheek and the back of the
neck, and measures the tightest bend of the outline around the posterior border of the jaw ramus (radius of the
circle through outline points 4 mm apart). Writes r2_slices.json and a PNG plot of the outlines (x lateral vs y
forward) for visual comparison. Kelvin (different head size/position) is similarity-aligned onto FaceC first using
the shared MetaHuman topology.

usage: python pd_r2_slices.py <out_stem> name=path.obj [name=path.obj ...]
"""
from __future__ import annotations

import json
import math
import sys
import zlib
import struct
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import load_obj, kabsch, apply  # noqa: E402

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default")
ZS = [161.0, 162.5, 164.0, 165.5, 167.0, 168.5]


def slice_segments(V, F, z):
    d = V[:, 2] - z
    s = np.sign(d)
    fs = s[F]
    cross = ~((fs > 0).all(1) | (fs < 0).all(1))
    segs = []
    for f in F[cross]:
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ia, ib = f[a], f[b]
            da, db = d[ia], d[ib]
            if (da > 0) != (db > 0):
                t = da / (da - db)
                pts.append(V[ia] + t * (V[ib] - V[ia]))
        if len(pts) == 2:
            segs.append((pts[0][:2], pts[1][:2]))
    return segs


def chain(segs, tol=1e-4):
    """Join segments into polylines (by rounding endpoints)."""
    key = lambda p: (round(float(p[0]) / tol), round(float(p[1]) / tol))  # noqa: E731
    adj = {}
    for i, (a, b) in enumerate(segs):
        adj.setdefault(key(a), []).append((i, 0))
        adj.setdefault(key(b), []).append((i, 1))
    used = np.zeros(len(segs), bool)
    lines = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        line = [segs[i][0], segs[i][1]]
        for direction in (1, 0):
            while True:
                end = line[-1] if direction else line[0]
                nxt = None
                for j, e in adj.get(key(end), []):
                    if not used[j]:
                        nxt = (j, e)
                        break
                if nxt is None:
                    break
                j, e = nxt
                used[j] = True
                other = segs[j][1 - e]
                if direction:
                    line.append(other)
                else:
                    line.insert(0, other)
        lines.append(np.array(line))
    return lines


def resample(line, step=0.1):
    seg = np.linalg.norm(np.diff(line, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(s[-1] / step))
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, line[:, 0]), np.interp(t, s, line[:, 1])], 1)


def outline(V, F, z, side):
    P = V.copy()
    if side < 0:
        P[:, 0] *= -1
    lines = chain(slice_segments(P, F, z))
    # keep the part of the outline on the +X side between y=-6 and y=10 (cheek -> back of neck), outermost chain
    best = None
    for ln in lines:
        m = (ln[:, 0] > 2.0) & (ln[:, 1] > -6.0) & (ln[:, 1] < 10.0)
        if m.sum() < 5:
            continue
        pts = ln[m]
        score = pts[:, 0].mean() + 0.001 * len(pts)
        if best is None or score > best[0]:
            best = (score, pts)
    if best is None:
        return None
    pts = best[1]
    pts = pts[np.argsort(pts[:, 1])]            # order back -> front
    return resample(pts, 0.05)


def tightest_bend(pts, span=0.4, y_range=(-4.0, 6.0)):
    """Smallest radius of circles through (p[i-k], p[i], p[i+k]) with k*0.05 cm = span; concave+convex both."""
    k = max(1, int(round(span / 0.05)))
    best = (1e9, None, 0)
    for i in range(k, len(pts) - k):
        a, b, c = pts[i - k], pts[i], pts[i + k]
        if not (y_range[0] <= b[1] <= y_range[1]):
            continue
        ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        if area2 < 1e-9:
            continue
        r = ab * bc * ca / (2 * area2)
        cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if r < best[0]:
            best = (r, b, 1 if cr > 0 else -1)
    return best


def turn_profile(pts, span=0.4):
    k = max(1, int(round(span / 0.05)))
    out = []
    for i in range(k, len(pts) - k):
        v1 = pts[i] - pts[i - k]
        v2 = pts[i + k] - pts[i]
        ang = math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], float(v1 @ v2)))
        out.append((float(pts[i][1]), float(pts[i][0]), ang))
    return out


def write_png(path, arr):
    h, w = arr.shape[:2]
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                          chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def main(stem, pairs):
    meshes = {}
    for p in pairs:
        name, path = p.split("=", 1)
        meshes[name] = load_obj(Path(path))
    names = list(meshes)
    ref = names[0]
    Vr = meshes[ref][0]
    for n in names:
        V, F = meshes[n]
        if n.lower().startswith("kelvin") and V.shape == Vr.shape:
            sel = (Vr[:, 2] > 150)
            R, t, s = kabsch(V[sel], Vr[sel], scale=True)
            meshes[n] = (apply(R, t, s, V), F)
    colors = [(255, 60, 60), (60, 200, 255), (255, 220, 0), (80, 255, 80), (255, 120, 255), (255, 255, 255)]
    res = {"zs": ZS, "meshes": names, "bends": {}}
    W, H = 360, 520                 # one panel per z: x 2..11 cm, y -6..10 cm at 32 px/cm
    img = np.zeros((H, W * len(ZS), 3), np.uint8) + 25
    for zi, z in enumerate(ZS):
        for ci, n in enumerate(names):
            V, F = meshes[n]
            for side in (1, -1):
                pts = outline(V, F, z, side)
                keyname = f"{n}|z{z}|{'L' if side > 0 else 'R'}"
                if pts is None:
                    res["bends"][keyname] = None
                    continue
                r, at, sign = tightest_bend(pts)
                res["bends"][keyname] = {"min_radius_cm": round(float(r), 3),
                                         "at_xy": [round(float(at[0]), 2), round(float(at[1]), 2)] if at is not None else None,
                                         "concave": sign < 0}
                if side > 0:
                    for x, y in pts:
                        px = int(zi * W + (x - 2.0) * 36)
                        py = int(H - (y + 6.0) * 32)
                        if 0 <= py < H and zi * W <= px < (zi + 1) * W:
                            img[max(0, py - 1):py + 1, max(0, px - 1):px + 1] = colors[ci % len(colors)]
        img[:, zi * W] = (90, 90, 90)
    write_png(OUT / f"{stem}.png", img)
    summ = {}
    for n in names:
        rs = [v["min_radius_cm"] for k, v in res["bends"].items() if v and k.startswith(n + "|")]
        summ[n] = {"min_radius_cm_median": round(float(np.median(rs)), 3) if rs else None,
                   "min_radius_cm_min": round(float(min(rs)), 3) if rs else None}
    res["summary"] = summ
    (OUT / f"{stem}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(summ, indent=1))
    for n in names:
        print(n, [(k.split("|")[1] + k.split("|")[2], v["min_radius_cm"]) for k, v in res["bends"].items()
                  if v and k.startswith(n + "|")])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
