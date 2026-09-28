import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, imglib as L
OUT = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(OUT, "results.json")))
G = json.load(open(os.path.join(OUT, "geom.json")))
EJ = json.load(open(os.path.join(OUT, "edges_v3.json")))["edges"]
rgb = np.load(os.path.join(OUT, "rgb.npy")); H, W = rgb.shape[:2]
C = np.array(res["centre_px"])
SS = 3
img = np.repeat(np.repeat(rgb, SS, 0), SS, 1)
def dot(x, y, col, rr=0):
    xi, yi = int(round(x*SS)), int(round(y*SS))
    if 0 <= xi < W*SS and 0 <= yi < H*SS: img[max(yi-rr,0):yi+rr+1, max(xi-rr,0):xi+rr+1] = col
for e, ge in zip(EJ, G["edges"]):
    c = np.array(ge["c"]); d = np.array(ge["d"]); n = np.array(e["n"])
    for t in np.arange(-0.8*e["len"], 0.8*e["len"], 0.2):
        p = c + t*d; dot(p[0], p[1], [0.1, 1.0, 0.2])
    for r in e["rows"]:
        s = r.get("s_edge", float("nan"))
        if np.isfinite(s):
            p = np.array(r["P"]) + s*n; dot(p[0], p[1], [1, 0, 0])
which = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "notches"
items = res["notches"] if which == "notches" else res["tips"]
for v in items:
    X = np.array(v["X"])
    for k in range(-12, 13):
        dot(X[0]+k*0.4, X[1], [0, 0.9, 1]); dot(X[0], X[1]+k*0.4, [0, 0.9, 1])
    if v.get("P_actual"):
        P = np.array(v["P_actual"])
        for k in range(-7, 8):
            dot(P[0]+k*0.4, P[1]+k*0.4, [1, 1, 0]); dot(P[0]+k*0.4, P[1]-k*0.4, [1, 1, 0])
    # fillet circle: centre on the bisector at distance rho/sin(beta/2) from X, toward the metal
    rho = v.get("fillet_radius_px") or v.get("blunt_radius_px")
    if rho and np.isfinite(rho) and v.get("P_actual"):
        u = (X - C)/np.linalg.norm(X - C)
        inward = -u if which == "notches" else u
        b2 = math.radians(v["angle"]/2)
        Ccirc = X + inward * (rho/math.sin(b2)) * (1 if which == "notches" else -1)
        for a in np.arange(0, 2*math.pi, 0.01):
            dot(Ccirc[0] + rho*math.cos(a), Ccirc[1] + rho*math.sin(a), [1, 0, 1])
tiles = []
for v in items:
    X = v["X"]; half, sc = 60, 2
    cx = int(np.clip(round(X[0]*SS), 0, W*SS-1)); cy = int(np.clip(round(X[1]*SS), 0, H*SS-1)); hh = half*SS
    pad = np.pad(img, ((hh,hh),(hh,hh),(0,0)), constant_values=1.0)
    t = pad[cy:cy+2*hh, cx:cx+2*hh]
    t = np.repeat(np.repeat(t, sc, 0), sc, 1)
    t[:, :2] = [0,0.5,0]; t[:2, :] = [0,0.5,0]
    tiles.append(t)
rows = [np.concatenate(tiles[i:i+4], 1) for i in range(0, len(tiles), 4)]
L.save_png(os.path.join(OUT, "qa_%s.png" % which), np.concatenate(rows, 0))
