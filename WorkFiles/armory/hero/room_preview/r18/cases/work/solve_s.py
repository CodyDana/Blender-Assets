from solve import *
import sys
G3 = (float(sys.argv[1]), float(sys.argv[2]))
T4 = (float(sys.argv[3]), float(sys.argv[4]))
Bg = box(G3[0], G3[0] + 0.85, G3[1], G3[1] + 1.0, 2.2)
B4 = box(T4[0], T4[0] + 0.85, T4[1], T4[1] + 1.0, 2.2)
Bsf = box(2.30, 3.10, 3.15, 4.35, 0.90)
print("G3", [round(v) for v in Bg], "T4", [round(v) for v in B4])
out = []
for W in (1.0, 1.1, 1.2, 1.3, 1.4):
    for D in (0.7, 0.8, 0.9, 1.0, 1.1):
        for H, Gl in ((0.55, 0.70), (0.50, 0.65), (0.45, 0.60), (0.50, 0.70), (0.45, 0.55)):
            for xo in frange(1.6, 3.6, 0.05):
                for yf in frange(12.0, 14.95 - W, 0.05):
                    b = box(xo, xo + D, yf, yf + W, H + Gl)
                    gs = [gap(b, Bg), gap(b, B4), gap(b, Bsf)] + [gap(b, KEEP[k]) for k in KEEP] + [gap(b, CENTRE[k]) for k in CENTRE]
                    pg = plan_gap((xo, xo + D, yf, yf + W), (G3[0], G3[0] + 0.85, G3[1], G3[1] + 1.0))
                    if min(gs) < 12 or pg < 0.3 or xo + D > 4.25: continue
                    ref = REF_W["S"]
                    d = sum(abs(a - c) for a, c in zip(b, ref))
                    out.append((min(min(gs), 25), round(pg, 2), -d, W, D, H, Gl, xo, yf, [round(v) for v in b], [round(v) for v in gs]))
out.sort(key=lambda r: (r[0], min(r[1], 0.8), r[3] * r[4]), reverse=True)
print(len(out))
for r in out[:25]: print(r)
