"""Stage 11: clean contrast-stretched view of the ball, box-downsampled by an integer factor, optional grid."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
from sb_m08_segments import text

a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
f = int(a[0]) if a else 2
gamma = float(a[1]) if len(a) > 1 else 0.7
grid = int(a[2]) if len(a) > 2 else 0
rgb = L.load_srgb()
lin = L.srgb_to_lin(rgb)
x0, y0, T = 150, 150, 960
c = lin[y0:y0 + T, x0:x0 + T]
c = c.reshape(T // f, f, T // f, f, 3).mean((1, 3))
v = L.lum(c.astype(np.float32))
lo, hi = np.percentile(v[v < 0.5], [1, 99.5])
g = np.clip((v - lo) / (hi - lo), 0, 1) ** gamma
g[v > 0.5] = 1
out = np.repeat(g[..., None], 3, 2).astype(np.float32)
if grid:
    for vv in range(200, 1110, grid):
        k = (vv - x0) // f
        clr = np.array((1, 0.25, 0.25) if vv % 100 == 0 else (0.3, 0.6, 1), np.float32)
        out[:, k] = 0.6 * out[:, k] + 0.4 * clr
        out[k, :] = 0.6 * out[k, :] + 0.4 * clr
L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_small_f{f}_g{gamma}_grid{grid}.png"), out)
print("done")
