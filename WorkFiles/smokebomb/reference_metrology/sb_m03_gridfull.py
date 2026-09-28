"""Stage 3: whole-ball views with a coordinate grid, weave suppressed, for band tracing by eye.
args: x0 y0 T K sigma variant  (variant st|ln)"""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
x0, y0, T, K = (int(a) for a in args[:4]) if args else (150, 150, 960, 1)
sigma = float(args[4]) if len(args) > 4 else 1.5
variant = args[5] if len(args) > 5 else 'st'
grid = int(args[6]) if len(args) > 6 else 50
rgb = L.load_srgb()
Y = L.lum(rgb)
Yb = L.gauss_blur(Y, sigma) if sigma > 0 else Y
if variant == 'st':
    img = L.stretch(Yb, 0.02, 0.30) ** 0.85
else:
    mu = L.gauss_blur(Y, 40)
    sd = np.sqrt(L.gauss_blur((Yb - mu) ** 2, 40)) + 0.005
    img = np.clip(0.5 + 0.2 * (Yb - mu) / sd, 0, 1)
    img[Y > 0.6] = 0.9
c = img[y0:y0 + T, x0:x0 + T]
c = np.repeat(c[..., None], 3, 2).astype(np.float32)
c = L.upscale(c, K)
for v in range(((x0 + grid - 1) // grid) * grid, x0 + T, grid):
    col = (v - x0) * K
    clr = np.array((1, 0.15, 0.15) if v % 100 == 0 else (0.2, 0.5, 1.0), np.float32)
    c[:, col] = 0.4 * c[:, col] + 0.6 * clr
for v in range(((y0 + grid - 1) // grid) * grid, y0 + T, grid):
    row = (v - y0) * K
    clr = np.array((1, 0.15, 0.15) if v % 100 == 0 else (0.2, 0.5, 1.0), np.float32)
    c[row, :] = 0.4 * c[row, :] + 0.6 * clr
# mark every 100-crossing with a green dot cluster for easier counting at 500s
for vx in range(((x0 + 99) // 100) * 100, x0 + T, 100):
    for vy in range(((y0 + 99) // 100) * 100, y0 + T, 100):
        if vx % 500 == 0 or vy % 500 == 0:
            cx, cy = (vx - x0) * K, (vy - y0) * K
            c[max(0, cy - 3):cy + 4, max(0, cx - 3):cx + 4] = (0.1, 1, 0.1)
L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_grid_{variant}_{x0}_{y0}_T{T}_K{K}_s{sigma}.png"), c)
print("done")
