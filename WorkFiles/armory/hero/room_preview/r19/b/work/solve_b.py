"""r19 b: fit the side cases' plan positions on the C1 projection (1448 x 1086, visible x 40-1408) to reference 2's
boxes, now with the rear PAIR of tall cases per side (reference 2: an outer-near tall behind the scroll / hat case,
its foot hidden, and an inner-far tall whose plinth foot shows) and a smaller case 8 footprint (the tray unchanged).
Usage: py -3 solve_b.py"""
import itertools, json, sys
import numpy as np

CASES = {"S": (1.0, 0.8, 0.55, 0.60), "SF": (1.0, 0.8, 0.40, 0.45), "Tall": (0.9, 0.75, 0.50, 1.70),
         "MT": (0.8, 0.75, 0.60, 0.95)}


def corners(dims, x, y, rot):
    W, D, H, G = dims
    ex, ey = (D, W) if rot in (90, -90) else (W, D)
    pts = []
    for (a, b, z0, z1) in ((ex / 2, ey / 2, 0.0, H), (ex / 2 - 0.022, ey / 2 - 0.022, H, H + G)):
        for sx, sy, z in itertools.product((-1, 1), (-1, 1), (z0, z1)):
            pts.append((x + sx * a, y + sy * b, z))
    return np.array(pts)


def box(dims, x, y, rot, clamp=True):
    p = corners(dims, x, y, rot)
    d = p[:, 1] + 4.18
    px = 724 + 1609 * (p[:, 0] - 6) / d
    py = 87 + 1609 * (3.39 - p[:, 2]) / d
    b = [px.min(), px.max(), py.min(), py.max()]
    if clamp:
        b[0], b[1] = max(40, b[0]), min(1408, b[1])
    return b


def err(b, r, use=(0, 1, 2, 3)):
    r = (max(40, r[0]), min(1408, r[1]), r[2], r[3])
    return float(np.sqrt(np.mean([(b[i] - r[i]) ** 2 for i in use])))


def fit(dims, r, xs, ys, rot=0, use=(0, 1, 2, 3), extra=None):
    best = []
    for x in xs:
        for y in ys:
            b = box(dims, x, y, rot)
            e = err(b, r, use)
            if extra:
                e += extra(x, y, b)
            best.append((e, round(float(x), 3), round(float(y), 3), [round(v) for v in b]))
    best.sort(key=lambda a: a[0])
    return best[:3]


if __name__ == "__main__":
    # reference 2 boxes (x0, x1, y0, y1), re-measured on 2-3x crops (+-5 px)
    REF = {"G4_W_inner_far": (357, 450, 257, 470), "G3_W_outer_near": (287, 400, 272, None),
           "G2_E_inner_far": (1000, 1087, 257, 472), "G5_E_outer_near": (1048, 1130, 272, None),
           "8_shuriken": (1260, 1407, 627, 855), "4_cloak": (130, 312, 307, 700)}
    T = CASES["Tall"]
    print("inner-far W", fit(T, REF["G4_W_inner_far"], np.arange(2.2, 4.0, 0.01), np.arange(8.5, 12.5, 0.02)))
    print("inner-far E", fit(T, REF["G2_E_inner_far"], np.arange(8.0, 9.8, 0.01), np.arange(8.5, 12.5, 0.02)))
    # outer-near: fit x0, x1, y0; foot hidden: y1 between the front case's top and foot (scroll 394-594, hat 337-578)
    hid = lambda lo, hi: (lambda x, y, b: 0.0 if lo + 15 <= b[3] <= hi else 50.0)
    print("outer-near W", fit(T, (287, 400, 272, 0), np.arange(1.6, 3.6, 0.01), np.arange(7.6, 11.5, 0.02),
                              use=(0, 1, 2), extra=hid(394, 594)))
    print("outer-near E", fit(T, (1048, 1130, 272, 0), np.arange(8.3, 10.5, 0.01), np.arange(7.6, 11.5, 0.02),
                              use=(0, 1, 2), extra=hid(337, 578)))
    print("cloak", fit(T, REF["4_cloak"], np.arange(2.6, 3.8, 0.01), np.arange(4.4, 6.0, 0.01)))
    # case 8: rot -90 kept (the tray's orientation); smaller footprints; heights kept (the tray's deck)
    for W in (1.0, 0.9, 0.8, 0.75, 0.70):
        for D in (0.8, 0.7, 0.66, 0.62):
            dims = (W, D, 0.40, 0.45)
            f = fit(dims, (1260, 1407, 627, 855), np.arange(8.4, 9.8, 0.01), np.arange(2.6, 4.0, 0.01), rot=-90)
            raw = box(dims, f[0][1], f[0][2], -90, clamp=False)
            print("SF", W, D, "%.1f" % f[0][0], f[0][1:], "raw x1 %.0f" % raw[1])
