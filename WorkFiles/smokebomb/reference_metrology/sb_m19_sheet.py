"""Stage 19: contact sheet of zoomed crops (for loose threads / fray / silhouette wisps).
args: name half K cols cx cy [cx cy ...]   (stretched luminance, light blur 0.6)"""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
from sb_m08_segments import text

a = sys.argv[sys.argv.index('--') + 1:]
name, half, K, cols = a[0], int(a[1]), int(a[2]), int(a[3])
cs = [(int(a[i]), int(a[i + 1])) for i in range(4, len(a), 2)]
rgb = L.load_srgb(); Y = L.lum(rgb)
g = L.stretch(L.gauss_blur(Y, 0.6), 0.02, 0.45) ** 0.8
H, W = Y.shape
S = 2 * half * K
rows = (len(cs) + cols - 1) // cols
sheet = np.ones((rows * (S + 24), cols * (S + 8), 3), np.float32)
for i, (cx, cy) in enumerate(cs):
    y0, x0 = cy - half, cx - half
    c = np.ones((2 * half, 2 * half), np.float32)
    ys0, xs0 = max(0, y0), max(0, x0)
    ys1, xs1 = min(H, y0 + 2 * half), min(W, x0 + 2 * half)
    c[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0] = g[ys0:ys1, xs0:xs1]
    c = L.upscale(np.repeat(c[..., None], 3, 2), K)
    # 10-px tick marks on the border
    for t in range(0, 2 * half, 10):
        c[:4, t * K] = (1, 0.2, 0.2); c[t * K, :4] = (1, 0.2, 0.2)
    r, q = divmod(i, cols)
    oy, ox = r * (S + 24) + 22, q * (S + 8)
    sheet[oy:oy + S, ox:ox + S] = c
    text(sheet, f"{i} {cx} {cy}", ox + 2, oy - 18, np.array((0.8, 0.1, 0.1), np.float32), 2)
L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_sheet_{name}.png"), sheet)
print("saved")
