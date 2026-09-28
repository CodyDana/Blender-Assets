"""Stage 2: inspection tiles (contrast-stretched, 2x, with a coordinate grid) for reading the strip layout by eye.
Grid: every 50 px image coords (dim blue), every 100 px (red). Tile origins in the file name."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

rgb = L.load_srgb()
Y = L.lum(rgb)
g = L.stretch(Y, 0.0, 0.33) ** 0.8
# local-normalised variant
mu = L.gauss_blur(Y, 25)
sd = np.sqrt(L.gauss_blur((Y - mu) ** 2, 25)) + 0.01
ln = np.clip(0.5 + 0.18 * (Y - mu) / sd, 0, 1)
bgm = Y > 0.6
ln[bgm] = 0.85
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
T = int(args[0]) if args else 360
K = int(args[1]) if len(args) > 1 else 2
origins = [int(a) for a in args[2:]] if len(args) > 2 else None
if origins is None:
    xs = [150, 450, 750]; ys = [150, 450, 750]
    pairs = [(x, y) for y in ys for x in xs]
else:
    pairs = list(zip(origins[0::2], origins[1::2]))
for variant, img in (("st", g), ("ln", ln)):
    for (x0, y0) in pairs:
        c = img[y0:y0 + T, x0:x0 + T]
        c = np.repeat(c[..., None], 3, 2).astype(np.float32)
        c = L.upscale(c, K)
        for v in range(((x0 + 49) // 50) * 50, x0 + T, 50):
            col = (v - x0) * K
            clr = np.array((1, 0.2, 0.2) if v % 100 == 0 else (0.3, 0.5, 1.0), np.float32)
            c[:, col] = 0.5 * c[:, col] + 0.5 * clr
        for v in range(((y0 + 49) // 50) * 50, y0 + T, 50):
            row = (v - y0) * K
            clr = np.array((1, 0.2, 0.2) if v % 100 == 0 else (0.3, 0.5, 1.0), np.float32)
            c[row, :] = 0.5 * c[row, :] + 0.5 * clr
        L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_tile_{variant}_{x0}_{y0}_T{T}_K{K}.png"), c)
# whole-ball local-normalised at 1x
L.save_png(os.path.join(L.DBG, "DEBUG_NEVER_SHIP_sb_localnorm_full.png"), ln)
print("done")
