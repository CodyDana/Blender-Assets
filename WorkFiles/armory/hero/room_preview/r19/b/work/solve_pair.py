"""r19 b: the rear PAIR of tall cases per side, fitted jointly on C1 (reference 2: an outer-near tall directly behind
the scroll / hat case, its foot hidden by it, top ~272; an inner-far tall further back and inboard, foot ~470, top
~257). Constraints: plan gap >= GAP to the case in front (scroll G1 back Y 7.58 / hat 6 back 7.675), pair members
apart by >= GAP where they overlap in X, inner edge <= 4.20 / >= 7.80 (0.9 m aisle to the centre column), outer-near
foot hidden (its C1 foot y inside the front case's box). Usage: py -3 solve_pair.py <W> <D> [GAP]"""
import sys
import numpy as np
from solve_b import box

W, D = float(sys.argv[1]), float(sys.argv[2])
GAP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.40
dims = (W, D, 0.50, 1.70)
SIDES = {"W": dict(front=((256, 405, 394, 594), 7.58), near=(287, 400, 272), far=(357, 450, 257, 470),
                   xs=np.arange(1.8, 4.2, 0.02)),
         "E": dict(front=((1074, 1214, 337, 578), 7.675), near=(1048, 1130, 272), far=(1000, 1087, 257, 472),
                   xs=np.arange(7.8, 10.2, 0.02))}
for s, c in SIDES.items():
    fb, fback = c["front"]
    ys = np.arange(fback + GAP + D / 2, 12.2, 0.02)
    near = []
    for x in c["xs"]:
        if (s == "W" and x + W / 2 > 4.20) or (s == "E" and x - W / 2 < 7.80):
            continue
        for y in ys:
            b = box(dims, x, y, 0)
            e = np.sqrt(((b[0] - c["near"][0]) ** 2 + (b[1] - c["near"][1]) ** 2 + (b[2] - c["near"][2]) ** 2) / 3)
            hidden = fb[2] + 10 <= b[3] <= fb[3]
            near.append((e + (0 if hidden else 25), x, y, b))
    near.sort(key=lambda a: a[0])
    far = []
    for x in c["xs"]:
        if (s == "W" and x + W / 2 > 4.20) or (s == "E" and x - W / 2 < 7.80):
            continue
        for y in ys:
            b = box(dims, x, y, 0)
            far.append((float(np.sqrt(np.mean([(b[i] - c["far"][i]) ** 2 for i in range(4)]))), x, y, b))
    far.sort(key=lambda a: a[0])
    best = None
    for en, xn, yn, bn in near[:400]:
        for ef, xf, yf, bf in far[:400]:
            xo = min(xn, xf) + W / 2 > max(xn, xf) - W / 2 - GAP   # overlap in X (with the gap)
            if xo and abs(yf - yn) < D + GAP:
                continue
            tot = en + ef
            if best is None or tot < best[0]:
                best = (tot, (round(en, 1), xn, yn, [round(v) for v in bn]), (round(ef, 1), xf, yf, [round(v) for v in bf]))
    print(s, "W x D", W, D, "gap", GAP, "total %.1f" % best[0])
    print("   near", best[1], "(ref", c["near"], ")")
    print("   far ", best[2], "(ref", c["far"], ")")
