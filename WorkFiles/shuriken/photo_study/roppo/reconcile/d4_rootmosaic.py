import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
rgb = rio.load_rgb(IMG)
corners = [(912.0, 591.6), (900.3, 442.2), (824.4, 317.7), (710.4, 238.2),
           (545.7, 245.6), (423.6, 328.0), (350.8, 459.0), (355.1, 607.2),
           (434.8, 737.4), (563.5, 803.5), (710.5, 800.6), (834.1, 732.9)]
# reconciled hub circle drawn for reference (my lit-arc fit)
HCX, HCY, HR = 628.43, 529.22, 285.9
R = 34
Z = 6
tiles = []
for (x, y) in corners:
    x0, y0 = int(round(x)) - R, int(round(y)) - R
    crop = np.clip(rgb[y0:y0 + 2 * R, x0:x0 + 2 * R].copy(), 0, 1)
    lo, hi = np.percentile(crop, 2), np.percentile(crop, 98)
    crop = np.clip((crop - lo) / max(hi - lo, 1e-6), 0, 1)
    big = np.repeat(np.repeat(crop, Z, axis=0), Z, axis=1)
    # hub circle in yellow
    for a in np.arange(0, 360, 0.02):
        th = np.radians(a)
        px = (HCX + np.cos(th) * HR - x0) * Z
        py = (HCY + np.sin(th) * HR - y0) * Z
        i, j = int(round(py)), int(round(px))
        if 0 <= i < big.shape[0] and 0 <= j < big.shape[1]:
            big[i, j] = (1, 1, 0)
    tiles.append(big)
rows = []
for r in range(3):
    row = np.concatenate([np.pad(t, ((2, 2), (2, 2), (0, 0)), constant_values=1)
                          for t in tiles[r * 4:(r + 1) * 4]], axis=1)
    rows.append(row)
mos = np.concatenate(rows, axis=0)
rio.save_rgb(os.path.join(HERE, "roots_mosaic_recon.png"), mos)
print("saved", mos.shape)
