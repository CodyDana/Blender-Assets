from evalcands import *
import itertools
TD, TW, sw, sd = 0.75, 0.9, 1.0, 0.8
best = []
for x4, y4, xg, yg, xs, ys in itertools.product((1.13, 1.18), (7.85, 7.95, 8.05), np.arange(1.13, 2.01, 0.05), np.arange(9.9, 12.51, 0.1),
                                                (1.98, 2.08, 2.13, 2.18), (13.85, 13.95, 14.05)):
    if yg < y4 + TW + 0.72 or ys < yg + TW + 0.72: continue
    o, p, cx = evaluate(((x4, y4), (xg, yg), (xs, ys)), TD, TW, sfw=1.0, sfg=0.45, sw=sw, sd=sd)
    m = min(o["5-4"], o["4-G3"], o["G3-G1"], o["4-G1"])
    k = min(o["G3~kmin"], o["G1~kmin"])
    if m < 28 or k < 18 or min(cx.values()) < 5: continue
    s1 = np.array(p[2]) - np.array(p[1]); s2 = np.array(p[3]) - np.array(p[2])
    if s1[0] <= 0 or s2[0] <= 0 or s1[1] >= 0 or s2[1] >= 0: continue
    ang = abs(np.degrees(np.arctan2(-s1[1], s1[0]) - np.arctan2(-s2[1], s2[0])))
    ev = max(np.hypot(*s1), np.hypot(*s2)) / min(np.hypot(*s1), np.hypot(*s2))
    sc = ang + 30 * (ev - 1) - 0.4 * min(m, 40) - 0.3 * min(k, 30) - 0.2 * min(cx["G1-G3"], 30)
    best.append((round(sc, 1), round(ang, 1), round(ev, 2), m, k, cx["G1-G3"], [round(float(v), 3) for v in (x4, y4, xg, yg, xs, ys)], p))
best.sort(key=lambda r: r[0])
for r in best[:10]: print(r)
b = best[0][6]
print(evaluate(((b[0], b[1]), (b[2], b[3]), (b[4], b[5])), TD, TW, sfw=1.0, sfg=0.45, sw=sw, sd=sd))
