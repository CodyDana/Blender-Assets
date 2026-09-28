import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
seg = np.load(OUT + "/seg.npz"); R0, C0 = int(seg["R0"]), int(seg["C0"]); rgb = seg["rgb"]
T = json.load(open(OUT + "/trace.json"))
S = 6
H, W = rgb.shape[:2]
X, Y = G.grid(R0, R0 + H, C0, C0 + W, S)
def fill(loops):
    m = np.zeros(X.shape, bool)
    for l in loops:
        P = np.array(l["pts"]); x0, y0 = P.min(0); x1, y1 = P.max(0)
        bb = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
        m[bb] ^= G.pip(X[bb], Y[bb], P)
    return m
sv = np.zeros(X.shape, bool); dk = np.zeros(X.shape, bool)
for e in T["elements"]:
    sv |= fill(e["silver"]); dk |= fill(e["dark"])
ref = tp_img.resize(rgb, S, kind='linear')
out = ref.copy()
out[sv] = 0.5 * ref[sv] + 0.5 * np.array([1.0, 0.35, 0.2])
out[dk] = 0.5 * ref[dk] + 0.5 * np.array([0.1, 0.4, 1.0])
side = np.concatenate([ref, out], 1)
tp_img.save(OUT + "/trace_fill_x6.png", side)
