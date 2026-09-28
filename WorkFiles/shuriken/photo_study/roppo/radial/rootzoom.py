"""Zoomed root-corner sheet: raw photo with local hub-arc circle (magenta), flank line (red),
T50 contour (yellow) and T80 contour (cyan) for each of the 12 roots.
blender -b --factory-startup --python rootzoom.py -- <photo> <outdir> <tag-for-geometry>
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
photo, outdir, tag = argv[0], argv[1], argv[2]
rgb = imgio.load_rgb(photo)
H, W, _ = rgb.shape
R = json.load(open(os.path.join(outdir, f"radial_{tag}.json")))
D = json.load(open(os.path.join(outdir, f"details_{tag}.json")))
S = 5; half = 36


def boundary(m):
    p = np.pad(m, 1, constant_values=False)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner

cont = {}
for t in ("T50", "T80"):
    sil = np.load(os.path.join(outdir, f"solid_{t}.npy")) | np.load(os.path.join(outdir, f"holes_{t}.npy"))
    cont[t] = boundary(sil)
cells = []
for rt in D["roots"]:
    k, side = rt["k"], rt["side"]
    x0c, y0c = [int(round(v)) for v in rt["corner_xy"]]
    xa, ya = x0c - half, y0c - half
    c = np.ones((2 * half, 2 * half, 3), np.float32)
    sx0, sy0, sx1, sy1 = max(0, xa), max(0, ya), min(W, xa + 2 * half), min(H, ya + 2 * half)
    c[sy0 - ya:sy1 - ya, sx0 - xa:sx1 - xa] = rgb[sy0:sy1, sx0:sx1]
    big = np.repeat(np.repeat(c, S, 0), S, 1)

    def put(x, y, col):
        u = int(round((x - xa) * S + S / 2)); v = int(round((y - ya) * S + S / 2))
        if 0 <= u < big.shape[1] and 0 <= v < big.shape[0]:
            big[max(0, v - 1):v + 1, max(0, u - 1):u + 1] = col
    for t, col in (("T50", [1, 1, 0]), ("T80", [0, 1, 1])):
        ys, xs = np.nonzero(cont[t][sy0:sy1, sx0:sx1])
        for x, y in zip(xs + sx0, ys + sy0):
            put(x, y, col)
    arc = D["hub"]["arcs"][(k - 1) % 6 if side == "cw" else k]
    acx, acy = arc["own_circle_c"]; ar = arc["own_circle_r"]
    for a in np.arange(0, 360, 0.02):
        put(acx + ar * math.cos(math.radians(a)), acy - ar * math.sin(math.radians(a)), [1, 0, 1])
    f = R["points"][k][side]
    p0 = np.array(f["p0"]); d = np.array(f["dir"])
    for s in np.arange(-500, 500, 0.2):
        q = p0 + s * d
        put(q[0], q[1], [1, 0, 0])
    big[:2, :] = 0; big[:, :2] = 0
    cells.append(big)
cols = 4
rows = (len(cells) + cols - 1) // cols
cs = 2 * half * S
sheet = np.ones((rows * cs, cols * cs, 3), np.float32)
for i, cimg in enumerate(cells):
    r, q = divmod(i, cols)
    sheet[r * cs:(r + 1) * cs, q * cs:(q + 1) * cs] = cimg
imgio.save_rgb(os.path.join(outdir, "sheet_roots_model.png"), sheet)
print("saved", sheet.shape)
