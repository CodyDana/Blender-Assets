from solve import *
import sys
G3 = (float(sys.argv[1]), float(sys.argv[2])); T4 = (float(sys.argv[3]), float(sys.argv[4]))
Bg = box(G3[0], G3[0] + 0.85, G3[1], G3[1] + 1.0, 2.2); B4 = box(T4[0], T4[0] + 0.85, T4[1], T4[1] + 1.0, 2.2)
Bsf = box(2.30, 3.10, 3.15, 4.35, 0.90)
for W in (1.0, 1.1, 1.2, 1.3, 1.4):
    for D in (0.7, 0.8, 0.9, 1.0, 1.1):
        best = None
        for H, Gl in ((0.55, 0.70),):
            for xo in frange(1.6, 3.6, 0.05):
                for yf in frange(12.0, 14.90 - W, 0.05):
                    b = box(xo, xo + D, yf, yf + W, H + Gl)
                    gs = [gap(b, Bg), gap(b, B4), gap(b, Bsf)] + [gap(b, KEEP[k]) for k in KEEP] + [gap(b, CENTRE[k]) for k in CENTRE]
                    pg = plan_gap((xo, xo + D, yf, yf + W), (G3[0], G3[0] + 0.85, G3[1], G3[1] + 1.0))
                    r = (round(min(gs)), round(pg, 2), xo, yf, [round(v) for v in b])
                    if pg >= 0.7 and (best is None or r[0] > best[0]): best = r
        print(W, D, best)
