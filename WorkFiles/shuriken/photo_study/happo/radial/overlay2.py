"""Overlay for edges_v2.json. usage: -- variant out.png [half scale]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[sys.argv.index("--") + 1:]
variant, outname = a[0], a[1]
ej = json.load(open(os.path.join(OUT, "edges_v2.json")))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
H, W = rgb.shape[:2]
SS = 2
img = np.repeat(np.repeat(rgb, SS, 0), SS, 1)


def dot(x, y, col, r=0):
    xi, yi = int(round(x * SS)), int(round(y * SS))
    if 0 <= xi < W * SS and 0 <= yi < H * SS:
        img[max(yi - r, 0):yi + r + 1, max(xi - r, 0):xi + r + 1] = col


R = ej["variants"][variant]
for e, f in zip(ej["edges"], R["fits"]):
    c = np.array(f["c"]); d = np.array(f["d"]); n = np.array(e["n"])
    for t in np.arange(-0.62 * e["len"], 0.62 * e["len"], 0.25):
        p = c + t * d
        dot(p[0], p[1], [0.1, 1.0, 0.2])
    for r in e["rows"]:
        s = r["s_dark"] if e["shadowed"] else r["s_clean"]
        if variant == "inner" and e["shadowed"]:
            s = r["s_inner"]
        if not np.isfinite(s):
            continue
        p = np.array(r["P"]) + s * n
        dot(p[0], p[1], [1, 0, 0] if 0.15 <= r["t"] <= 0.85 else [1, 0.5, 0])
        # the other candidate in magenta
        s2 = r["s_clean"] if e["shadowed"] else r["s_dark"]
        if np.isfinite(s2):
            p2 = np.array(r["P"]) + s2 * n
            dot(p2[0], p2[1], [1, 0, 1])
for v in R["vertices"]:
    X = v["X"]
    for k in range(-10, 11):
        dot(X[0] + k * 0.5, X[1], [0, 0.9, 1]); dot(X[0], X[1] + k * 0.5, [0, 0.9, 1])
L.save_png(os.path.join(OUT, outname), img)
if len(a) > 2:
    half, sc = int(a[2]), int(a[3])
    tiles = []
    for v in R["vertices"]:
        X = v["X"]
        cx = int(np.clip(round(X[0] * SS), 0, W * SS - 1)); cy = int(np.clip(round(X[1] * SS), 0, H * SS - 1))
        hh = half * SS
        pad = np.pad(img, ((hh, hh), (hh, hh), (0, 0)), constant_values=1.0)
        t = pad[cy:cy + 2 * hh, cx:cx + 2 * hh]
        t = np.repeat(np.repeat(t, sc, 0), sc, 1)
        t[:, :2] = [0, 0.5, 0]; t[:2, :] = [0, 0.5, 0]
        tiles.append(t)
    rows = [np.concatenate(tiles[i:i + 4], 1) for i in range(0, len(tiles), 4)]
    L.save_png(os.path.join(OUT, outname.replace(".png", "_vertices.png")), np.concatenate(rows, 0))
