"""Tracing aid: a labelled zoom of the reference (grid every 2 px, labels every 10 px, 3x5 pixel digits) with
optional traced curves drawn over it.  args: r0 r1 c0 c1 scale name [curves.json]"""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
FONT = {"0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"], "2": ["111", "001", "111", "100", "111"],
        "3": ["111", "001", "111", "001", "111"], "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
        "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"], "8": ["111", "101", "111", "101", "111"],
        "9": ["111", "101", "111", "001", "111"]}


def text(img, x, y, s, col, k=3):
    for ch in s:
        g = FONT[ch]
        for j, row in enumerate(g):
            for i, c in enumerate(row):
                if c == "1":
                    img[y + j * k:y + (j + 1) * k, x + i * k:x + (i + 1) * k, :3] = col
        x += 4 * k


a = np.load(OUT + "/ref_full.npy")
argv = sys.argv[sys.argv.index("--") + 1:]
r0, r1, c0, c1, s = map(int, argv[:5]); name = argv[5]
curves = json.load(open(argv[6])) if len(argv) > 6 else {}
c = a[r0:r1, c0:c1].copy()
big = tp_img.resize(c, s, kind='linear')
pad = 40
can = np.ones((big.shape[0] + pad, big.shape[1] + pad, 4), np.float32)
can[pad:, pad:] = big
for r in range(r0, r1 + 1):
    y = pad + (r - r0) * s
    if y >= can.shape[0]: break
    if r % 2 == 0:
        a_ = 0.35 if r % 10 == 0 else 0.12
        can[y, pad:, :3] = can[y, pad:, :3] * (1 - a_) + a_ * np.array([1, 0, 0])
    if r % 10 == 0:
        text(can, 2, y - 7, str(r), [0.8, 0, 0])
for q in range(c0, c1 + 1):
    x = pad + (q - c0) * s
    if x >= can.shape[1]: break
    if q % 2 == 0:
        a_ = 0.35 if q % 10 == 0 else 0.12
        can[pad:, x, :3] = can[pad:, x, :3] * (1 - a_) + a_ * np.array([0, 0, 1])
    if q % 10 == 0:
        text(can, x - 17, 12, str(q), [0, 0, 0.8])
cols = [[0, 0.9, 0], [1, 0, 1], [0, 0.8, 0.9], [1, 0.6, 0], [0.5, 0, 1], [1, 1, 0]]
for i, (nm, pts) in enumerate(curves.items()):
    P = np.asarray(pts, float)
    if len(P) < 2: continue
    seg = np.vstack([P, P[:1]]) if nm.endswith("*") is False else P
    for k in range(len(seg) - 1):
        for t in np.linspace(0, 1, 60):
            x, y = seg[k] + t * (seg[k + 1] - seg[k])
            xi, yi = int(pad + (x - c0) * s), int(pad + (y - r0) * s)
            if 0 <= xi < can.shape[1] - 1 and 0 <= yi < can.shape[0] - 1:
                can[yi:yi + 2, xi:xi + 2, :3] = cols[i % len(cols)]
    for x, y in P:
        xi, yi = int(pad + (x - c0) * s), int(pad + (y - r0) * s)
        can[max(yi - 3, 0):yi + 4, max(xi - 3, 0):xi + 4, :3] = [0, 0, 0]
tp_img.save(OUT + f"/z3_{name}.png", can)
print("saved", name)
