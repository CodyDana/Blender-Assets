"""Trace pilot: fit the blossom (5 pearl petals, centre pearl) to the reference by model fitting.
Petal model (local axis u from the blossom centre outward at angle phi, v across):
    u in [d0, d1], s = (u - d0)/(d1 - d0),  half-width(s) = w/2 * (2 sqrt(s(1-s)))**q * (1 + e (s - 0.5))
The fit maximises IoU against the pearl mask (smoothed lum > iso) inside the petal's 72-degree sector."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
a = np.load(OUT + "/ref_full.npy")[..., :3]
lum_full = a @ np.array([0.2126, 0.7152, 0.0722])
S = 4
r0, r1, c0, c1 = 48, 126, 468, 544
lum = tp_img.resize(lum_full[r0:r1, c0:c1], S, kind='linear')
X, Y = G.grid(r0, r1, c0, c1, S)

def petal_poly(cx, cy, phi, d0, d1, w, q, e, n=64):
    s = np.linspace(0, 1, n)
    hw = w / 2 * (2 * np.sqrt(np.clip(s * (1 - s), 0, None))) ** q * (1 + e * (s - 0.5))
    u = d0 + s * (d1 - d0)
    up = np.c_[u, hw]; dn = np.c_[u[::-1], -hw[::-1]]
    P = np.vstack([up, dn[1:-1]])
    cu, su = np.cos(phi), np.sin(phi)
    return np.c_[cx + P[:, 0] * cu - P[:, 1] * su, cy + P[:, 0] * su + P[:, 1] * cu]

def iou(poly, M, sect):
    ins = G.pip(X, Y, poly)
    I = (ins & M & sect).sum(); U = ((ins | M) & sect).sum()
    return I / max(U, 1)

cx, cy = 505.6, 88.0
ang = np.arctan2(Y - cy, X - cx); rad = np.hypot(X - cx, Y - cy)
res = {"centre": [cx, cy], "petals": []}
ISO = 0.50
M = G.gauss(lum, 1.0) > ISO
rng = np.random.default_rng(7)
def contrast(poly):
    ins = G.pip(X, Y, poly)
    inner = ins & ~G.erode(ins, 6)          # 1.5 px band inside (S = 4)
    outer = G.dilate(ins, 6) & ~ins
    return Ls[inner].mean() - Ls[outer].mean()
Ls = G.gauss(lum, 1.0)
INIT = {0: (-90.0, 10.2, 34.1, 20.7), 1: (-18.0, 10.5, 33.0, 21.0), 2: (54.0, 10.5, 33.0, 21.0),
        3: (126.0, 10.5, 33.0, 21.0), 4: (198.0, 10.5, 33.0, 21.0)}
for i in range(5):
    ph, d0, d1, w = INIT[i]
    p = np.array([np.radians(ph), d0, d1, w, 0.8, 0.0])
    best = contrast(petal_poly(cx, cy, *p))
    step = np.array([0.05, 0.8, 0.8, 0.8, 0.1, 0.1])
    for it in range(400):
        k = rng.integers(0, 6)
        cand = p.copy(); cand[k] += rng.normal() * step[k]
        cand[1] = np.clip(cand[1], 6, 16); cand[4] = np.clip(cand[4], 0.4, 1.4); cand[5] = np.clip(cand[5], -0.6, 0.8)
        cand[3] = np.clip(cand[3], 15, 25); cand[2] = np.clip(cand[2], 26, 38)
        v = contrast(petal_poly(cx, cy, *cand))
        if v > best: best, p = v, cand
        if it == 200: step *= 0.4
    poly = petal_poly(cx, cy, *p)
    ins = G.pip(X, Y, poly)
    print(f"petal {i}: phi {np.degrees(p[0]):.1f} d0 {p[1]:.2f} d1 {p[2]:.2f} w {p[3]:.2f} q {p[4]:.2f} e {p[5]:.2f} contrast {best:.3f} mean-in {Ls[ins].mean():.3f}")
    res["petals"].append({"phi": float(p[0]), "d0": float(p[1]), "d1": float(p[2]), "w": float(p[3]), "q": float(p[4]),
                          "e": float(p[5]), "edge_contrast": float(best)})
# centre pearl: circle fit on the bright disc inside r < 9 (bezel = the dark ring around it)
best = (0, None)
for rr in np.arange(4.0, 7.6, 0.25):
    for dx in np.arange(-1.0, 1.01, 0.25):
        for dy in np.arange(-1.0, 1.01, 0.25):
            ins = np.hypot(X - cx - dx, Y - cy - dy) < rr
            ring = (np.hypot(X - cx - dx, Y - cy - dy) >= rr) & (np.hypot(X - cx - dx, Y - cy - dy) < rr + 1.5)
            sc = lum[ins].mean() - lum[ring].mean()
            if sc > best[0]: best = (sc, (cx + dx, cy + dy, rr))
print("centre pearl", best)
res["pearl"] = {"cx": best[1][0], "cy": best[1][1], "r": best[1][2], "contrast": best[0]}
# stamens: bright local maxima in the annulus 7..12 px (beads)
Ls = G.gauss(lum, 1.2)
ann = (rad > 7.0) & (rad < 13.0)
pk = (Ls == np.maximum.reduce([np.roll(np.roll(Ls, a_, 0), b_, 1) for a_ in range(-4, 5) for b_ in range(-4, 5)])) & ann & (Ls > 0.45)
ys, xs = np.nonzero(pk)
beads = [(float(X[y, x]), float(Y[y, x]), float(Ls[y, x])) for y, x in zip(ys, xs)]
print("stamen bead candidates", len(beads), [(round(b[0], 1), round(b[1], 1)) for b in beads])
res["stamen_beads"] = beads
json.dump(res, open(OUT + "/blossom_fit.json", "w"), indent=1)
# overlay
big = tp_img.resize(a[r0:r1, c0:c1], 10, kind='linear')
Xb, Yb = G.grid(r0, r1, c0, c1, 10)
for pp in res["petals"]:
    poly = petal_poly(cx, cy, pp["phi"], pp["d0"], pp["d1"], pp["w"], pp["q"], pp["e"], 200)
    for x, y in poly:
        xi, yi = int((x - c0) * 10), int((y - r0) * 10)
        if 0 <= xi < big.shape[1] and 0 <= yi < big.shape[0]: big[yi-1:yi+1, xi-1:xi+1, :3] = [1, 0, 0]
pc = res["pearl"]
for t in np.linspace(0, 2*np.pi, 200):
    xi, yi = int((pc["cx"] + pc["r"]*np.cos(t) - c0) * 10), int((pc["cy"] + pc["r"]*np.sin(t) - r0) * 10)
    big[yi-1:yi+1, xi-1:xi+1, :3] = [0, 1, 0]
for b in beads:
    xi, yi = int((b[0] - c0) * 10), int((b[1] - r0) * 10); big[yi-3:yi+3, xi-3:xi+3, :3] = [0, 0.4, 1]
tp_img.save(OUT + "/blossom_fit_x10.png", big)
