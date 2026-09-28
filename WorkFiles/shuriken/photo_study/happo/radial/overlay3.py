import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, imglib as L
OUT = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(OUT, "geom.json")))
ej = json.load(open(os.path.join(OUT, "edges_v2.json")))
rgb = np.load(os.path.join(OUT, "rgb.npy")); H, W = rgb.shape[:2]
SS = 2
img = np.repeat(np.repeat(rgb, SS, 0), SS, 1)
def dot(x, y, col, r=0):
    xi, yi = int(round(x*SS)), int(round(y*SS))
    if 0 <= xi < W*SS and 0 <= yi < H*SS: img[max(yi-r,0):yi+r+1, max(xi-r,0):xi+r+1] = col
for e, ge in zip(ej["edges"], G["edges"]):
    c = np.array(ge["c"]); d = np.array(ge["d"]); n = np.array(e["n"])
    for t in np.arange(-0.75*e["len"], 0.75*e["len"], 0.25):
        p = c + t*d; dot(p[0], p[1], [0.1, 1.0, 0.2])
    for r in e["rows"]:
        s = r["s_clean"] if ge["rule"] == "clean" else r["s_dark"]
        if np.isfinite(s):
            p = np.array(r["P"]) + s*n
            dot(p[0], p[1], [1, 0, 0] if 0.15 <= r["t"] <= 0.85 else [1, 0.55, 0])
C = np.array(G["centre"])
for k in range(-14, 15):
    dot(C[0]+k*0.5, C[1], [1,1,0], 1); dot(C[0], C[1]+k*0.5, [1,1,0], 1)
for v in G["vertices"]:
    X = v["X"]
    for k in range(-12, 13):
        dot(X[0]+k*0.5, X[1], [0, 0.9, 1]); dot(X[0], X[1]+k*0.5, [0, 0.9, 1])
    if v.get("P_actual"):
        P = v["P_actual"]
        for k in range(-6, 7):
            dot(P[0]+k*0.5, P[1]+k*0.5, [1,1,0]); dot(P[0]+k*0.5, P[1]-k*0.5, [1,1,0])
L.save_png(os.path.join(OUT, "dbg_final.png"), img)
tiles = []
for v in G["vertices"]:
    X = v["X"]; half, sc = 55, 2
    cx = int(np.clip(round(X[0]*SS), 0, W*SS-1)); cy = int(np.clip(round(X[1]*SS), 0, H*SS-1)); hh = half*SS
    pad = np.pad(img, ((hh,hh),(hh,hh),(0,0)), constant_values=1.0)
    t = pad[cy:cy+2*hh, cx:cx+2*hh]
    t = np.repeat(np.repeat(t, sc, 0), sc, 1)
    t[:, :2] = [0,0.5,0]; t[:2, :] = [0,0.5,0]
    tiles.append(t)
rows = [np.concatenate(tiles[i:i+4], 1) for i in range(0, len(tiles), 4)]
L.save_png(os.path.join(OUT, "dbg_final_vertices.png"), np.concatenate(rows, 0))
