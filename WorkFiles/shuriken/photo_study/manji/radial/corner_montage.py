"""Montage of the 12 corners (rows: junction, hook root, arm end; columns: quarters) and 4 tips, 3x zoom, with final edge."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
rgb, info = C.load_rgb(C.IMG); h, w = rgb.shape[:2]
fm = np.unpackbits(np.load(os.path.join(C.OUT, "mask.npy")))[:h * w].reshape(h, w).astype(bool)
R = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
Q = R["quarters_xy_img"]
S, Z = 70, 3
rows = ["junction", "next_root", "armend", "tip"]
M = np.ones((len(rows) * (S * Z + 6), 4 * 2 * (S * Z) + 4 * 12, 3), np.float32)
for r, key in enumerate(rows):
    for c in range(4):
        x, y = Q[c][key]
        x0 = int(np.clip(x - S // 2, 0, w - S)); y0 = int(np.clip(y - S // 2, 0, h - S))
        crop = rgb[y0:y0 + S, x0:x0 + S].copy()
        mc = fm[y0:y0 + S, x0:x0 + S]
        e = mc & ~C.erode(mc, 1)
        c2 = crop.copy(); c2[e] = [1, 0, 0]
        both = np.concatenate([crop, c2], 1)
        both = np.repeat(np.repeat(both, Z, 0), Z, 1)
        oy = r * (S * Z + 6); ox = c * (2 * S * Z + 12)
        M[oy:oy + S * Z, ox:ox + 2 * S * Z] = both
C.save_png(M, os.path.join(C.OUT, "corners_montage.png"))
print("ok")
