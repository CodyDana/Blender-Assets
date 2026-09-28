"""Stage 12: batch overlay of the traced edges (sb_trace.json) on several region views in one run.
args: K sigma base T x0 y0 [x0 y0 ...]"""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
from sb_m08_segments import text

a = sys.argv[sys.argv.index('--') + 1:]
TRF = os.environ.get("SB_TRACE", "sb_trace.json")
K, sigma, base, T = int(a[0]), float(a[1]), a[2], int(a[3])
origins = [(int(a[i]), int(a[i + 1])) for i in range(4, len(a), 2)]
rgb = L.load_srgb(); Y = L.lum(rgb)
Yb = L.gauss_blur(Y, sigma) if sigma > 0 else Y
if base == 'st':
    img = L.stretch(Yb, 0.02, 0.30)
else:
    mu = L.gauss_blur(Y, 40)
    sd = np.sqrt(L.gauss_blur((Yb - mu) ** 2, 40)) + 0.005
    img = np.clip(0.5 + 0.2 * (Yb - mu) / sd, 0, 1)
    img[Y > 0.6] = 0.9
img = np.repeat(img[..., None], 3, 2).astype(np.float32) * 0.85
tr = json.load(open(os.path.join(L.D, TRF)))
pal = [(1, 0.9, 0), (0, 1, 1), (1, 0.3, 1), (0.3, 1, 0.3), (1, 0.55, 0.1), (0.5, 0.6, 1), (1, 0.3, 0.3),
       (0.6, 1, 0.8), (1, 1, 1)]
M = 40
for (x0, y0) in origins:
    crop = L.upscale(img[max(0, y0):y0 + T, max(0, x0):x0 + T], K).copy()
    out = np.ones((crop.shape[0] + M, crop.shape[1] + M, 3), np.float32)
    out[M:, M:] = crop
    step = 25 if K >= 2 else 50
    for v in range(((x0 + step - 1) // step) * step, x0 + T, step):
        col = M + (v - x0) * K
        clr = np.array((1, 0.2, 0.2) if v % 100 == 0 else (0.25, 0.55, 1.0), np.float32)
        out[M:, col] = 0.7 * out[M:, col] + 0.3 * clr
        if v % 50 == 0:
            text(out, str(v), col - 8, 4 if (v // 50) % 2 == 0 else 20, clr * 0.8, 2)
    for v in range(((y0 + step - 1) // step) * step, y0 + T, step):
        row = M + (v - y0) * K
        clr = np.array((1, 0.2, 0.2) if v % 100 == 0 else (0.25, 0.55, 1.0), np.float32)
        out[row, M:] = 0.7 * out[row, M:] + 0.3 * clr
        if v % 50 == 0:
            text(out, str(v), 2, row - 5, clr * 0.8, 2)
    for i, (eid, e) in enumerate(sorted(tr['edges'].items())):
        col = np.array(pal[i % len(pal)], np.float32)
        P = np.array(e['pts'], float)
        for a_, b_ in zip(P[:-1], P[1:]):
            n = int(max(abs(b_ - a_)) * K) + 2
            for f in np.linspace(0, 1, n):
                x = M + int(round((a_[0] + f * (b_[0] - a_[0]) - x0) * K))
                y = M + int(round((a_[1] + f * (b_[1] - a_[1]) - y0) * K))
                if M <= x < out.shape[1] - 1 and M <= y < out.shape[0] - 1:
                    out[y, x] = col
        for p in P:
            x = M + int(round((p[0] - x0) * K)); y = M + int(round((p[1] - y0) * K))
            if M + 1 <= x < out.shape[1] - 2 and M + 1 <= y < out.shape[0] - 2:
                out[y - 1:y + 2, x - 1:x + 2] = col
        cc = np.array([x0 + T / 2, y0 + T / 2])
        inside = [p for p in e['pts'] if x0 + 10 <= p[0] < x0 + T - 30 and y0 + 10 <= p[1] < y0 + T - 20]
        if inside:
            P2 = np.array(inside, float)
            p = P2[len(P2) // 2]
            tx, ty = M + int((p[0] - x0) * K) + 5, M + int((p[1] - y0) * K) + 5
            text(out, eid, tx + 1, ty + 1, np.zeros(3, np.float32), 2)
            text(out, eid, tx, ty, col, 2)
    L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_ov_{os.path.splitext(TRF)[0]}_{x0}_{y0}_T{T}_K{K}_{base}.png"), out)
    print("saved", x0, y0)
