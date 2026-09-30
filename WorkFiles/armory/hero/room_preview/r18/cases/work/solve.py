"""r18 cases: search the west side row on the C1 projection (east mirrors it: x' = 1448 - x).
Row order SF(5) -> Tall(4) -> Tall(G3) -> S(G1). Boxes = the whole case (footprint x 0..H+G)."""
import itertools, json, math
F, CX, CY, CAMY, CAMZ = 1609.0, 724.0, 87.0, -4.18, 3.39
VIS = (40, 1408)

def px(X, Y, Z):
    d = Y - CAMY
    return CX + F * (X - 6.0) / d, CY + F * (CAMZ - Z) / d

def box(x0, x1, y0, y1, z1):
    pts = [px(X, Y, Z) for X in (x0, x1) for Y in (y0, y1) for Z in (0.0, z1)]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return [max(VIS[0], min(xs)), min(VIS[1], max(xs)), min(ys), max(ys)]

def gap(a, b):
    return max(a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3])

# keep-clear (measured on night_r17 ref_aspect C1, west side)
KEEP = {"niche": [365, 413, 165, 232], "alcove": [436, 506, 70, 232], "foot_lantern": [489, 521, 280, 359],
        "deck_lantern": [534, 566, 238, 282]}
CENTRE = {"1": box(5.1, 6.9, 3.35, 4.65, 1.2), "2": box(5.1, 6.9, 8.1, 9.3, 1.25), "3": box(5.2, 6.8, 12.9, 13.9, 1.2)}
REF_W = {"SF": [28, 195, 545, 855], "Tall4": [130, 312, 325, 700], "S": [258, 407, 400, 590], "G3": [287, 450, 255, 470]}
REF_E = {"SF": [1260, 1408, 625, 855], "S": [1180, 1410, 470, 715], "Tall4": [1078, 1210, 345, 575], "G3": [1000, 1130, 255, 470]}
REF_Em = {k: [1448 - v[1], 1448 - v[0], v[2], v[3]] for k, v in REF_E.items()}

def frange(a, b, s):
    n = int(round((b - a) / s)); return [round(a + i * s, 3) for i in range(n + 1)]

def evaluate(sfH, sfG, t4, g3, s):
    # sf fixed at (2.70, 3.75) rot 90: X 2.30-3.10, Y 3.15-4.35
    cases = {"SF": (2.30, 3.10, 3.15, 4.35, sfH + sfG)}
    cases["Tall4"] = (t4[0], t4[0] + 0.85, t4[1], t4[1] + 1.0, 2.20)
    cases["G3"] = (g3[0], g3[0] + 0.85, g3[1], g3[1] + 1.0, 2.20)
    W, D, H, G, xo, yf = s
    cases["S"] = (xo, xo + D, yf, yf + W, H + G)
    B = {k: box(*v) for k, v in cases.items()}
    gaps = {}
    for a, b in itertools.combinations(B, 2):
        gaps[f"{a}-{b}"] = gap(B[a], B[b])
    for k, kb in KEEP.items():
        for c in ("G3", "S", "Tall4"):
            gaps[f"{c}~{k}"] = gap(B[c], kb)
    for k, kb in CENTRE.items():
        for c in B:
            gaps[f"{c}~c{k}"] = gap(B[c], kb)
    return cases, B, gaps

def plan_gap(a, b):
    return max(a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3])

if __name__ == "__main__":
    best = []
    for sfH in (0.45, 0.50, 0.55, 0.60):
        for sfG in (0.45, 0.50, 0.55, 0.60, 0.65):
            top = sfH + sfG
            for t4x in frange(1.10, 1.60, 0.05):
                for t4y in frange(6.5, 10.0, 0.05):
                    c4 = (t4x, t4y)
                    B4 = box(t4x, t4x + 0.85, t4y, t4y + 1.0, 2.2)
                    Bsf = box(2.30, 3.10, 3.15, 4.35, top)
                    if gap(B4, Bsf) < 12: continue
                    for g3x in frange(1.10, 1.60, 0.05):
                        for g3y in frange(max(10.0, t4y + 1.8), 14.2, 0.05):
                            Bg = box(g3x, g3x + 0.85, g3y, g3y + 1.0, 2.2)
                            if gap(Bg, B4) < 12 or any(gap(Bg, KEEP[k]) < 12 for k in KEEP): continue
                            best.append((sfH, sfG, c4, (g3x, g3y), B4, Bg, Bsf))
    print(len(best))
    # score: min gap margin, then closeness to the reference boxes
    def sc(r):
        sfH, sfG, c4, cg, B4, Bg, Bsf = r
        m = min(gap(B4, Bsf), gap(Bg, B4), min(gap(Bg, KEEP[k]) for k in KEEP))
        ref = REF_W
        d = sum(abs(a - b) for a, b in zip(Bsf, ref["SF"])) + sum(abs(a - b) for a, b in zip(B4, ref["Tall4"])) + \
            sum(abs(a - b) for a, b in zip(Bg, ref["G3"]))
        return (min(m, 25), -d)
    best.sort(key=sc, reverse=True)
    for r in best[:15]:
        print(r[0], r[1], r[2], r[3], [round(v) for v in r[4]], [round(v) for v in r[5]], [round(v) for v in r[6]], sc(r))
