# Debug overlay: photo + final mask outline + fitted primitives (lines, hook-back circles), corners, tips, axes, span.
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *

px = np.load(BASE + "/manji_pixels.npy"); H, W = px.shape[:2]
m = np.load(BASE + "/mask_final.npy")
st = np.load(BASE + "/fit_state.npy", allow_pickle=True).item()
bev = json.load(open(BASE + "/bevel_samples.json"))
img = px.copy() * 0.75 + 0.25


def put(x, y, col, r=0):
    xi = int(round(x)); yi = int(round(y))
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if 0 <= xi + dx < W and 0 <= yi + dy < H:
                img[yi + dy, xi + dx] = col


def seg(p, q, col, r=0, dash=None):
    n = int(np.hypot(*(np.asarray(q) - np.asarray(p)))) + 1
    for i in range(n + 1):
        t = i / n
        if dash and (i // dash) % 2:
            continue
        put(p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]), col, r)


def arc(c, R, a0, a1, col, r=0):
    n = max(int(abs(a1 - a0) * R), 2)
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        put(c[0] + R * math.cos(a), c[1] + R * math.sin(a), col, r)


RED = [1, 0, 0]; GRN = [0, 1, 0]; CYN = [0, 0.9, 1]; MAG = [1, 0, 1]; YEL = [1, 1, 0]; WHT = [1, 1, 1]; BLU = [0.2, 0.3, 1]
edge = (m ^ np.roll(m, 1, 0)) | (m ^ np.roll(m, 1, 1)); edge[0, :] = edge[:, 0] = False
img[edge] = RED
# fitted primitives
for name, e in st["edges"].items():
    P0, P1 = e["P0"], e["P1"]
    if name.endswith("hook_back"):
        c, R = e["c"], e["R"]
        a0 = math.atan2(P0[1] - c[1], P0[0] - c[0]); a1 = math.atan2(P1[1] - c[1], P1[0] - c[0])
        if a1 - a0 > math.pi: a1 -= 2 * math.pi
        if a0 - a1 > math.pi: a1 += 2 * math.pi
        arc(c, R, a0, a1, CYN, 1)
    else:
        p, d = e["p"], e["d"]
        t0 = (P0 - p) @ d; t1 = (P1 - p) @ d
        seg(p + (t0 - 60) * d, p + (t1 + 60) * d, GRN, 1)
# bevel band inner boundary samples
for name, s in bev.items():
    for q, nin, tb, has in zip(s["q"], s["nin"], s["tb"], s["has"]):
        if has:
            put(q[0] + tb * nin[0], q[1] + tb * nin[1], BLU, 1)
# corners, tips, centre, axes, span
for k, cinfo in st["corners"].items():
    v = cinfo["vertex"]; put(v[0], v[1], MAG, 6)
O = st["O"]
for a, ax in st["axes"].items():
    seg(O, O + 1500 * ax["d"], WHT, 0, dash=14)
for a, T in st["T"].items():
    put(T[0], T[1], YEL, 7)
seg(st["T"]["top"], st["T"]["bottom"], [1, 0.55, 0], 0, dash=22)
seg(st["T"]["right"], st["T"]["left"], [1, 0.55, 0], 0, dash=22)
put(O[0], O[1], WHT, 9)
write_png(BASE + "/manji_overlay.png", img)
sc = 3
h2, w2 = H // sc, W // sc
q = img[:h2 * sc, :w2 * sc].reshape(h2, sc, w2, sc, 3)
small = q.mean((1, 3))
for col in (RED, GRN, CYN, MAG, YEL, WHT, BLU, [1, 0.55, 0]):
    hit = np.all(np.abs(q - np.array(col)) < 0.02, axis=4).any((1, 3))
    small[hit] = col
write_png(BASE + "/manji_overlay_small.png", small)
print("overlay written")
