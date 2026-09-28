"""ruler crop: args groups of: out x0 y0 x1 y1 scale. Adds margin rulers on all 4 sides: ticks every 5 ref px; 10 = longer; 50 = red long. Thin faint guide lines every 50 px."""
import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
a = sys.argv[sys.argv.index('--')+1:]
ref = load_srgb()
M = 24
for i in range(0, len(a), 6):
    out, x0, y0, x1, y1, k = a[i], *map(int, a[i+1:i+6])
    c = upscale(ref[y0:y1, x0:x1].copy(), k)
    h, w = c.shape[:2]
    can = np.full((h + 2*M, w + 2*M, 3), 0.95, np.float32)
    can[M:M+h, M:M+w] = c
    for gx in range(x0, x1+1):
        if gx % 5: continue
        col = M + (gx - x0)*k
        if col >= w + 2*M: continue
        ln = 6 if gx % 10 else (12 if gx % 50 else M)
        colr = [1, 0, 0] if gx % 50 == 0 else ([0, 0, 0.9] if gx % 10 == 0 else [0.3, 0.3, 0.3])
        can[M-ln:M, col] = colr; can[M+h:M+h+ln, col] = colr
        if gx % 50 == 0: can[M:M+h:3, col] = [1, 0.2, 0.2]
    for gy in range(y0, y1+1):
        if gy % 5: continue
        row = M + (gy - y0)*k
        if row >= h + 2*M: continue
        ln = 6 if gy % 10 else (12 if gy % 50 else M)
        colr = [1, 0, 0] if gy % 50 == 0 else ([0, 0, 0.9] if gy % 10 == 0 else [0.3, 0.3, 0.3])
        can[row, M-ln:M] = colr; can[row, M+w:M+w+ln] = colr
        if gy % 50 == 0: can[row, M:M+w:3] = [1, 0.2, 0.2]
    save_png(out, can)
