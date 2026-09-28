"""Draw outline points + fitted lines + vertices on the photo; also residual strips.
usage: -- edges_json out_png [crop_half scale]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[sys.argv.index("--") + 1:]
ej = json.load(open(os.path.join(OUT, a[0])))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
H, W = rgb.shape[:2]
S = 2  # supersample for drawing
img = np.repeat(np.repeat(rgb, S, 0), S, 1)


def dot(x, y, col, r=0):
    xi, yi = int(round(x * S)), int(round(y * S))
    if 0 <= xi < W * S and 0 <= yi < H * S:
        img[max(yi - r, 0):yi + r + 1, max(xi - r, 0):xi + r + 1] = col


for e in ej["edges"]:
    f = e["fit"]
    c = np.array(f["c"]); d = np.array(f["d"])
    for t in np.arange(-0.62 * e["len"], 0.62 * e["len"], 0.25):
        p = c + t * d
        dot(p[0], p[1], [0.1, 1.0, 0.2])
    for r in e["rows"]:
        col = [1, 0, 0] if r["kind"] == "rise" else [1, 0, 1]
        dot(r["x"], r["y"], col)
        if "x_inner" in r:
            dot(r["x_inner"], r["y_inner"], [1, 0.6, 0])
for v in ej["vertices"]:
    X = v["X"]
    for k in range(-8, 9):
        dot(X[0] + k * 0.5, X[1], [0, 0.9, 1]); dot(X[0], X[1] + k * 0.5, [0, 0.9, 1])
for extra in ej.get("extra_points", []):
    dot(extra[0], extra[1], [1, 1, 0], 1)
L.save_png(os.path.join(OUT, a[1]), img[::S, ::S] if False else img)
if len(a) > 2:
    half, sc = int(a[2]), int(a[3])
    tiles = []
    for v in ej["vertices"]:
        X = v["X"]
        cx, cy = int(np.clip(round(X[0] * S), 0, W * S - 1)), int(np.clip(round(X[1] * S), 0, H * S - 1))
        hh = half * S
        pad = np.pad(img, ((hh, hh), (hh, hh), (0, 0)), constant_values=1.0)
        t = pad[cy:cy + 2 * hh, cx:cx + 2 * hh]
        t = np.repeat(np.repeat(t, sc, 0), sc, 1)
        t[:, :2] = [0, 0.5, 0]; t[:2, :] = [0, 0.5, 0]
        tiles.append(t)
    rows = [np.concatenate(tiles[i:i + 4], 1) for i in range(0, len(tiles), 4)]
    L.save_png(os.path.join(OUT, a[1].replace(".png", "_vertices.png")), np.concatenate(rows, 0))
