"""Stage 9: annotated region viewer. Renders a region (x0,y0,T) at K x with a labelled coordinate grid
(image pixel coordinates printed on the margins), and overlays any traced polylines from
sb_trace.json (edges) with their ids. args: x0 y0 T K [sigma] [base: st|ln|raw] [grid]"""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
from sb_m08_segments import text

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
x0, y0, T, K = (int(a) for a in args[:4])
sigma = float(args[4]) if len(args) > 4 else 1.2
base = args[5] if len(args) > 5 else 'st'
grid = int(args[6]) if len(args) > 6 else 25
show_trace = (args[7] != '0') if len(args) > 7 else True
rgb = L.load_srgb()
Y = L.lum(rgb)
Yb = L.gauss_blur(Y, sigma) if sigma > 0 else Y
if base == 'st':
    img = L.stretch(Yb, 0.02, 0.30)
    img = np.repeat(img[..., None], 3, 2)
elif base == 'ln':
    mu = L.gauss_blur(Y, 40)
    sd = np.sqrt(L.gauss_blur((Yb - mu) ** 2, 40)) + 0.005
    img = np.clip(0.5 + 0.2 * (Yb - mu) / sd, 0, 1)
    img[Y > 0.6] = 0.9
    img = np.repeat(img[..., None], 3, 2)
else:
    img = np.clip(L.gauss_blur(rgb, sigma) if sigma > 0 else rgb, 0, 1)
M = 40  # margin (output px)
H, W = Y.shape
xa, ya = max(0, x0), max(0, y0)
crop = img[ya:y0 + T, xa:x0 + T].astype(np.float32)
crop = L.upscale(crop, K).copy()
out = np.ones((crop.shape[0] + M, crop.shape[1] + M, 3), np.float32)
out[M:, M:] = crop
for v in range(((x0 + grid - 1) // grid) * grid, x0 + T, grid):
    col = M + (v - x0) * K
    major = v % 100 == 0
    clr = np.array((1, 0.2, 0.2) if major else (0.25, 0.55, 1.0), np.float32)
    a = 0.55 if major else 0.35
    out[M:, col] = (1 - a) * out[M:, col] + a * clr
    if v % 50 == 0:
        text(out, str(v), col - 8, 4 if (v // 50) % 2 == 0 else 20, clr * 0.8, 2)
for v in range(((y0 + grid - 1) // grid) * grid, y0 + T, grid):
    row = M + (v - y0) * K
    major = v % 100 == 0
    clr = np.array((1, 0.2, 0.2) if major else (0.25, 0.55, 1.0), np.float32)
    a = 0.55 if major else 0.35
    out[row, M:] = (1 - a) * out[row, M:] + a * clr
    if v % 50 == 0:
        text(out, str(v), 2, row - 5, clr * 0.8, 2)
tp = os.path.join(L.D, "sb_trace.json")
if show_trace and os.path.exists(tp):
    tr = json.load(open(tp))
    pal = [(1, 0.9, 0), (0, 1, 1), (1, 0.3, 1), (0.3, 1, 0.3), (1, 0.55, 0.1), (0.5, 0.6, 1), (1, 0.3, 0.3)]
    for i, (eid, e) in enumerate(sorted(tr.get('edges', {}).items())):
        col = np.array(pal[i % len(pal)], np.float32)
        P = np.array(e['pts'], float)
        for a_, b_ in zip(P[:-1], P[1:]):
            n = int(max(abs(b_ - a_)) * K) + 2
            for f in np.linspace(0, 1, n):
                x = M + int(round((a_[0] + f * (b_[0] - a_[0]) - x0) * K))
                y = M + int(round((a_[1] + f * (b_[1] - a_[1]) - y0) * K))
                if M <= x < out.shape[1] - 1 and M <= y < out.shape[0] - 1:
                    out[y:y + 2, x:x + 1] = col
        # label at the point nearest the region centre
        cc = np.array([x0 + T / 2, y0 + T / 2])
        inside = [(p, np.hypot(*(np.array(p) - cc))) for p in e['pts'] if x0 <= p[0] < x0 + T and y0 <= p[1] < y0 + T]
        if inside:
            p = min(inside, key=lambda q: q[1])[0]
            tx, ty = M + int((p[0] - x0) * K) + 4, M + int((p[1] - y0) * K) + 4
            text(out, eid, tx + 1, ty + 1, np.zeros(3, np.float32), 2)
            text(out, eid, tx, ty, col, 2)
name = f"DEBUG_NEVER_SHIP_sb_view_{x0}_{y0}_T{T}_K{K}_{base}{'_tr' if show_trace else ''}.png"
L.save_png(os.path.join(L.DBG, name), out)
print("saved", name)
