from evalcands import *
import itertools
TD, TW = float(sys.argv[1]), float(sys.argv[2]); sw, sd = float(sys.argv[3]), float(sys.argv[4])
best = []
for x4, y4, xg, yg, xs, ys in itertools.product(np.arange(1.13, 1.40, 0.05), np.arange(7.7, 8.4, 0.1), np.arange(1.13, 2.2, 0.05),
                                                np.arange(9.8, 11.6, 0.1), np.arange(1.9, 2.6, 0.05), np.arange(13.6, 15.06 - sw, 0.1)):
    if yg < y4 + TW + 0.72 or ys < yg + TW + 0.72: continue
    o, p, cx = evaluate(((x4, y4), (xg, yg), (xs, ys)), TD, TW, sfw=1.0, sfg=0.45, sw=sw, sd=sd)
    m = min(o["5-4"], o["4-G3"], o["G3-G1"], o["4-G1"])
    k = min(o["G3~kmin"], o["G1~kmin"])
    if m < 30 or k < 18: continue
    s1 = np.array(p[2]) - np.array(p[1]); s2 = np.array(p[3]) - np.array(p[2])
    if s1[0] <= 0 or s2[0] <= 0 or s1[1] >= 0 or s2[1] >= 0: continue
    ang = abs(np.degrees(np.arctan2(-s1[1], s1[0]) - np.arctan2(-s2[1], s2[0])))
    ev = max(np.hypot(*s1), np.hypot(*s2)) / min(np.hypot(*s1), np.hypot(*s2))
    sc = ang + 30 * (ev - 1) - 0.3 * min(m, 45) - 0.2 * min(cx["G1-G3"], 30) - 0.5 * (p[1][0] - p[0][0])
    best.append((round(sc, 1), round(ang, 1), round(ev, 2), m, k, cx["G1-G3"], [round(v, 3) for v in (x4, y4, xg, yg, xs, ys)], p, o, cx))
best.sort(key=lambda r: r[0])
for r in best[:12]: print(r[:8]); 
print(best[0][8], best[0][9])
