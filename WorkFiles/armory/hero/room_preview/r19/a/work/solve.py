"""r19 a (USER DECISION 2026-09-30 "copy the reference order"): fit each side case's plan position (and rotation) so
its C1 box (plinth + glass, every corner, 1448 x 1086, visible x 40-1408) matches the box measured on
armory3_reference2.png. Grid search per case; prints the best fits. Usage: py -3 solve.py"""
import itertools, json, sys
import numpy as np

CASES = {"S": (1.0, 0.8, 0.55, 0.60), "SF": (1.0, 0.8, 0.40, 0.45), "Tall": (0.9, 0.75, 0.50, 1.70),
         "MT": (0.8, 0.75, 0.60, 0.95)}
if __name__ == "__main__" and len(sys.argv) > 1:
    CASES.update(json.loads(sys.argv[1]))
REF = {  # re-measured by eye on 2x crops with a 50 px grid (+-5 px)
    "5_kunai": ((28, 195, 545, 855), "W"), "4_cloak": ((130, 313, 310, 700), "W"),
    "G1_scrolls": ((255, 407, 400, 590), "W"), "G3_reartall": ((287, 450, 255, 470), "W"),
    "8_shuriken": ((1260, 1408, 625, 855), "E"), "7_boots": ((1180, 1410, 472, 715), "E"),
    "6_hat": ((1078, 1210, 344, 575), "E"), "G2_reartall": ((1000, 1130, 255, 472), "E")}


def corners(t, x, y, rot):
    W, D, H, G = CASES[t]
    ex, ey = (D, W) if rot in (90, -90) else (W, D)
    pts = []
    for (a, b, z0, z1) in ((ex / 2, ey / 2, 0.0, H), (ex / 2 - 0.022, ey / 2 - 0.022, H, H + G)):
        for sx, sy, z in itertools.product((-1, 1), (-1, 1), (z0, z1)):
            pts.append((x + sx * a, y + sy * b, z))
    return np.array(pts)


def box(t, x, y, rot, clamp=True):
    p = corners(t, x, y, rot)
    d = p[:, 1] + 4.18
    px = 724 + 1609 * (p[:, 0] - 6) / d
    py = 87 + 1609 * (3.39 - p[:, 2]) / d
    b = [px.min(), px.max(), py.min(), py.max()]
    if clamp:
        b[0], b[1] = max(40, b[0]), min(1408, b[1])
    return b


def clampref(r):
    return (max(40, r[0]), min(1408, r[1]), r[2], r[3])


def err(b, r):
    r = clampref(r)
    return float(np.sqrt(np.mean([(b[i] - r[i]) ** 2 for i in range(4)])))


if __name__ == "__main__":
    types = {"5_kunai": ["S", "SF"], "4_cloak": ["Tall"], "G1_scrolls": ["S"], "G3_reartall": ["Tall"],
             "8_shuriken": ["SF"], "7_boots": ["S"], "6_hat": ["MT", "Tall", "S"], "G2_reartall": ["Tall"]}
    for k, (r, side) in REF.items():
        res = []
        for t in types[k]:
            for rot in (0, 90, -90):
                for x in np.arange(1.2, 10.81, 0.01):
                    if (side == "W") != (x < 6):
                        continue
                    for y in np.arange(2.8, 15.0, 0.02):
                        b = box(t, x, y, rot)
                        res.append((err(b, r), t, rot, round(x, 3), round(y, 3), [round(v) for v in b]))
        res.sort(key=lambda a: a[0])
        seen = set()
        print(k, "ref", clampref(r))
        for e in res:
            key = (e[1], e[2])
            if key in seen:
                continue
            seen.add(key)
            print("   rms %.1f %s rot %d X %.2f Y %.2f box %s" % e)
