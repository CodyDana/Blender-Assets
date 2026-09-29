"""C1 camera fit: level shift-lens (or pitched) camera, landmarks on reference 2 (1448 x 1086)."""
import itertools
import math
import sys

import numpy as np

W, H = 1448, 1086
LX, LY, LH, LZ0 = (3.76, 8.24), 2.323, 0.23, -0.12        # entry lanterns (hero SM_AK_Lantern 0.46 x 0.46 x 0.645)
LT = LZ0 + 0.645
LM = [  # world, ref px, weight
    ((5.1, 3.05, 0.0), (543, 832), 1), ((6.9, 3.05, 0.0), (903, 832), 1), ((5.1, 3.05, 0.5), (543, 762), 1),
    ((5.12, 3.07, 1.45), (555, 608), 1), ((6.88, 3.07, 1.45), (890, 608), 1),
    ((5.12, 4.33, 1.45), (560, 538), 1), ((6.88, 4.33, 1.45), (892, 538), 1),
    ((4.8, 15.9, 3.8), (650, 74), 1), ((7.2, 15.9, 1.5), (800, 221), 1),
    ((LX[0] - LH, LY - LH, LZ0), (60, 1060), 1), ((LX[0] + LH, LY - LH, LT), (165, 897), 1),
    ((LX[1] - LH, LY - LH, LT), (1278, 900), 1), ((LX[1] + LH, LY - LH, LZ0), (1378, 1062), 1),
    ((LX[0] - LH, LY + LH, LT), (67, 843), 1), ((LX[1] + LH, LY + LH, LT), (1385, 843), 1),
]
BAR = [((6.0, 2.56, 0.0), 930), ((6.0, 2.72, 0.0), 900)]


def proj(p, cam, f, shift, pitch=0.0, w=W, h=H):
    x, y, z = (p[i] - cam[i] for i in range(3))
    # pitch (deg, negative = down) about X: camera forward = (0, cos, sin)
    a = math.radians(pitch)
    fy, fz = math.cos(a), math.sin(a)
    depth = y * fy + z * fz
    up = -y * fz + z * fy
    k = f / 36.0 * max(w, h)
    return (w / 2 + k * x / depth, h / 2 - (k * up / depth - shift * max(w, h)))


def lantern_metrics(cam, f, shift, pitch=0.0, w=W, h=H, lx=LX[0]):
    pts = [proj((lx + sx * LH, LY + sy * LH, z), cam, f, shift, pitch, w, h)
           for sx in (-1, 1) for sy in (-1, 1) for z in (LZ0, LT)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    fb = proj((lx - LH, LY - LH, LZ0), cam, f, shift, pitch, w, h)
    ft = proj((lx + LH, LY - LH, LT), cam, f, shift, pitch, w, h)
    front_w, front_h = abs(ft[0] - fb[0]), abs(fb[1] - ft[1])
    return dict(sil_w=max(xs) - min(xs), sil_h=max(ys) - min(ys), sil_ratio=(max(xs) - min(xs)) / (max(ys) - min(ys)),
                front_w=front_w, front_h=front_h, front_ratio=front_w / front_h,
                top_px=front_h and (ft[1] - min(ys)), top_over_front=(ft[1] - min(ys)) / front_h,
                box=(min(xs), min(ys), max(xs), max(ys)))


def resid(cam, f, shift, pitch=0.0):
    r = []
    for p, (u, v), wt in LM:
        a, b = proj(p, cam, f, shift, pitch)
        r += [(a - u) * wt, (b - v) * wt]
    for p, v in BAR:
        r.append(proj(p, cam, f, shift, pitch)[1] - v)
    return np.array(r)


def rms(r):
    return float(np.sqrt(np.mean(r ** 2)))


def fit(f, pitch_free=False, zmax=None, ymax=None, shift_fixed=None):
    best = None
    for yc in np.arange(-8.0, 1.01, 0.05):
        for zc in np.arange(1.8, 4.61, 0.05):
            if zmax and zc > zmax:
                continue
            if ymax is not None and yc > ymax:
                continue
            pitches = np.arange(-30, 0.1, 1.0) if pitch_free else [0.0]
            for pt in pitches:
                cam = (6.0, yc, zc)
                # best shift in closed form (vertical offset is linear in shift)
                if shift_fixed is not None:
                    s = shift_fixed
                else:
                    r0 = resid(cam, f, 0.0, pt)
                    # v residual indices: odd entries of landmarks + bar entries
                    idx = [2 * i + 1 for i in range(len(LM))] + list(range(2 * len(LM), 2 * len(LM) + len(BAR)))
                    s = -float(np.mean(r0[idx])) / max(W, H) * -1
                    s = -s
                    # v = h/2 - (k*up/d - s*W): dv/ds = +W; want mean(v - ref) = 0
                    s = -float(np.mean(r0[idx])) / max(W, H)
                r = resid(cam, f, s, pt)
                e = rms(r)
                if best is None or e < best[0]:
                    best = (e, cam, s, pt)
    return best


if __name__ == "__main__":
    cur = ((6.0, -1.51, 3.42), 24.5, -0.303)
    print("current", rms(resid(*cur)), lantern_metrics(*cur))
    for f in [float(a) for a in sys.argv[1:]] or [24.5, 28, 30, 32, 35, 40, 45]:
        e, cam, s, pt = fit(f)
        m = lantern_metrics(cam, f, s)
        print(f"f {f}: rms {e:.1f} cam ({cam[1]:.2f}, {cam[2]:.2f}) shift {s:.3f} | lantern sil {m['sil_ratio']:.3f} "
              f"front {m['front_ratio']:.3f} top/front {m['top_over_front']:.3f} box {[round(v) for v in m['box']]}")
