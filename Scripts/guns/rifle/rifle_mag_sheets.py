"""AR-01 stage 6 drawings from the fit's re-imported shipped bytes (plain Python: py -3 -B):

    py -3 -B Scripts/guns/rifle/rifle_mag_sheets.py

- section sheet: 5 transverse sections (X = const, frame M) through the well, rifle (red) and seated magazine (blue);
- rock strip: 8 frames of the reload path (MagInsertStart -> MagRockStart -> Mag) in the Y = 0 plane;
Inputs scratch/mag/fit_geom.npz (rifle_mag_fit.py). Output WorkFiles/guns/rifle/review/mag/.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = np.load(ROOT / "WorkFiles" / "guns" / "rifle" / "scratch" / "mag" / "fit_geom.npz")
OUT = ROOT / "WorkFiles" / "guns" / "rifle" / "review" / "mag"
OUT.mkdir(parents=True, exist_ok=True)
RV, RT, MV, MT = D["RV"], D["RT"], D["MV"], D["MT"]
RM, tM, RR, tR, RI, tI = D["RM"], D["tM"], D["RR"], D["tR"], D["RI"], D["tI"]
theta, d_ins = float(D["theta"]), float(D["d_ins"])


def segs(V, T, axis, c):
    s = V[:, axis] - c
    out = []
    A, B, C = T[:, 0], T[:, 1], T[:, 2]
    P, m_ = [], []
    for e0, e1 in ((A, B), (B, C), (C, A)):
        s0, s1 = s[e0], s[e1]
        m = (s0 * s1) < 0
        t = np.where(m, s0 / np.where(m, s0 - s1, 1.0), 0.0)
        P.append(V[e0] + (V[e1] - V[e0]) * t[:, None])
        m_.append(m)
    cnt = m_[0].astype(int) + m_[1] + m_[2]
    for i in np.nonzero(cnt == 2)[0]:
        q = [P[k][i] for k in range(3) if m_[k][i]]
        out.append((q[0], q[1]))
    return out


def ry(th_deg):
    a = math.radians(th_deg)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])


def panel(rs, ms, ax_u, ax_v, box, sc, title):
    u0, u1, v0, v1 = box
    W, H = int((u1 - u0) * sc), int((v1 - v0) * sc)
    im = Image.new("RGB", (W, H + 22), "white")
    dr = ImageDraw.Draw(im)
    for g in range(int(math.floor(u0)), int(u1) + 1):
        if g % 5 == 0:
            dr.line([((g - u0) * sc, 22), ((g - u0) * sc, H + 22)], fill=(232, 232, 232))
    for g in range(int(math.floor(v0)), int(v1) + 1):
        if g % 5 == 0:
            dr.line([(0, (v1 - g) * sc + 22), (W, (v1 - g) * sc + 22)], fill=(232, 232, 232))
    for col, S in (((200, 0, 0), rs), ((0, 0, 210), ms)):
        for p, q in S:
            dr.line([((p[ax_u] - u0) * sc, (v1 - p[ax_v]) * sc + 22), ((q[ax_u] - u0) * sc, (v1 - q[ax_v]) * sc + 22)],
                    fill=col, width=1)
    dr.text((4, 4), title + "   (grid 5 mm; red rifle, blue magazine)", fill=(0, 0, 0))
    return im


def mag_at(R, t):
    return MV @ R.T + t


def main():
    Ms = mag_at(RM, tM)
    tiles = []
    for x in (372.0, 385.0, 400.0, 415.0, 428.0):
        tiles.append(panel(segs(RV, RT, 0, x), segs(Ms, MT, 0, x), 1, 2, (-24, 24, -45, 15), 9, f"X = {x:.0f} (M)"))
    w, h = tiles[0].size
    sheet = Image.new("RGB", (w * 5, h), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * w, 0))
    sheet.save(OUT / "well_sections.png")
    # rock strip: insert start, 2 lerp frames, rock start, 3 slerp frames, seated
    frames = []
    for u in (0.0, 0.5, 1.0):
        frames.append((f"insert {d_ins * (1 - u):.1f} mm", RR, tR + RR @ np.array([0.0, 0.0, -d_ins * (1 - u)])))
    a0 = math.degrees(math.atan2(RR[0, 2], RR[0, 0]))
    a1 = math.degrees(math.atan2(RM[0, 2], RM[0, 0]))
    for u in (0.25, 0.5, 0.75, 0.9, 1.0):
        a = a0 + (a1 - a0) * u
        frames.append((f"rock {a:.1f} deg", ry(a), tM))
    tiles = []
    for name, R, t in frames:
        tiles.append(panel(segs(RV, RT, 1, 0.0), segs(mag_at(R, t), MT, 1, 0.0), 0, 2, (350, 450, -60, 10), 5,
                           "Y = 0: " + name))
    w, h = tiles[0].size
    strip = Image.new("RGB", (w * 4, h * 2), "white")
    for i, t in enumerate(tiles):
        strip.paste(t, ((i % 4) * w, (i // 4) * h))
    strip.save(OUT / "rock_strip.png")
    print("[AR01-sheets] done", OUT)


main()
