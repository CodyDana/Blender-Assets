"""Trace pilot v2: TRACE the blossom petals from the reference pixels (replaces the parametric petal fit as the outline).

For each of the 5 petals (sector = nearest fitted petal axis): pearl pixels = smoothed luminance above a threshold,
constrained to the fitted petal dilated 2.2 px (so reflections outside cannot leak in) and seeded by the fitted petal
shrunk 2 px (so the shaded lower-right of each pearl stays in); largest component, holes filled, contour smoothed.
The traced contour is the PEARL edge; the silver bezel is built 1.0 px outside it.
    blender -b --factory-startup --python tp_petals.py
Output work/petals_traced.json (ref px) + work/petals_traced_x10.png."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
BF = json.load(open(WORK + "/blossom_fit.json"))
cx, cy = BF["centre"]
ref = np.load(WORK + "/ref_full.npy")[..., :3]
lum1 = ref @ np.array([0.2126, 0.7152, 0.0722])
S = 8
R0, R1, C0, C1 = int(cy - 40), int(cy + 40), int(cx - 40), int(cx + 40)
X, Y = G.grid(R0, R1, C0, C1, S)
import tp_relief_util as U
LUM = G.gauss(U.bilinear(lum1, X, Y), 0.45 * S)
R = np.hypot(X - cx, Y - cy); A = np.arctan2(Y - cy, X - cx)
phis = np.array([p["phi"] for p in BF["petals"]])
dang = np.abs(np.angle(np.exp(1j * (A[..., None] - phis[None, None, :]))))
sector = dang.argmin(-1)
THR = float(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else 0.50
out = []
for i, pp in enumerate(BF["petals"]):
    poly = U.petal_poly(cx, cy, pp["phi"], pp["d0"], pp["d1"], pp["w"], pp["q"], pp["e"])
    dfit = U.sdist_grid(poly, X, Y)
    m = (sector == i) & (dfit > -2.2) & (R > 6.0) & ((LUM > THR) | (dfit > 2.0))
    lab, n = G.label(m)
    if n == 0:
        continue
    sizes = np.bincount(lab.ravel())[1:]
    m = lab == (1 + int(sizes.argmax()))
    # fill holes
    outside = G.flood(np.pad(np.zeros_like(m), 1, constant_values=True), np.pad(~m, 1, constant_values=True))[1:-1, 1:-1]
    m = ~outside
    f = G.gauss(m.astype(float), 1.1 * S)
    loops = G.marching_squares(f, 0.52)
    L = max(loops, key=lambda l: abs(G.signed_area(l)))
    P = np.c_[C0 + (L[:, 0] + 0.5) / S, R0 + (L[:, 1] + 0.5) / S]
    P = G.smooth_closed(G.resample_closed(P, 0.3), 6)
    out.append(P.round(3).tolist())
    print("petal", i, "pts", len(P), "area px2 %.1f fit %.1f" % (abs(G.signed_area(P)), abs(G.signed_area(poly))), flush=True)
json.dump({"threshold": THR, "petals": out}, open(WORK + "/petals_traced.json", "w"))
V = 10
big = tp_img.resize(ref[R0:R1, C0:C1], V, kind='linear')
def draw(P, col):
    for x, y in P:
        xi, yi = int((x - C0) * V), int((y - R0) * V)
        if 1 <= xi < big.shape[1] - 1 and 1 <= yi < big.shape[0] - 1:
            big[yi - 1:yi + 2, xi - 1:xi + 2, :3] = col
for P in out:
    draw(P, [1, 0.1, 0.1])
    Q = G.resample_closed(np.array(P), 0.3)
    draw(Q + 0 * Q, [1, 0.1, 0.1])
tp_img.save(WORK + "/petals_traced_x10.png", big)
