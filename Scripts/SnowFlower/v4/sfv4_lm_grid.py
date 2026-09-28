"""Look-match: sheet crop with a model-frame mm grid (x across, z down) for reading design coordinates.
python sfv4_lm_grid.py <view front|side|back> <z0> <z1> <xhalf> <zoom> <out.png> [step_mm]"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_lm_img as I
import sfv4_spec as S
AX = {"front": 287.5, "side": 489.0, "back": 681.0}
view, z0, z1, xh, k, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
step = float(sys.argv[7]) if len(sys.argv) > 7 else 5.0
ref = I.read_png(HERE.parents[2] / "References/SnowFlower/SnowFlower_user_reference.png")[..., :3]
row = lambda z: (z - S.Z_POMMEL_TOP) / S.MM_PER_PX + 10.0
r0, r1 = row(z0), row(z1)
c0, c1 = AX[view] - xh / S.MM_PER_PX, AX[view] + xh / S.MM_PER_PX
H, W = int((r1 - r0) * k), int((c1 - c0) * k)
ys = r0 + (np.arange(H) + 0.5) / k - 0.5
xs = c0 + (np.arange(W) + 0.5) / k - 0.5
yi = np.clip(ys.astype(int), 0, ref.shape[0] - 2); fy = (ys - yi)[:, None, None]
xi = np.clip(xs.astype(int), 0, ref.shape[1] - 2); fx = (xs - xi)[None, :, None]
a = ref[yi][:, xi] * (1 - fy) * (1 - fx) + ref[yi + 1][:, xi] * fy * (1 - fx) + ref[yi][:, xi + 1] * (1 - fy) * fx + ref[yi + 1][:, xi + 1] * fy * fx
a = a.copy()
# image column -> model x (front: image-left = +X; back: image-left = -X; side: image-left = +Y)
sgn = -1 if view == "front" or view == "side" else 1
for v in np.arange(-200, 200 + step, step):
    c = (AX[view] + sgn * v / S.MM_PER_PX - c0) * k
    if 0 <= c < W:
        col = (1, 0, 0) if v == 0 else ((0, 0.6, 1) if v % (4 * step) == 0 else (0, 0.9, 0.3))
        a[:, int(c)] = a[:, int(c)] * 0.4 + np.array(col) * 0.6
for z in np.arange(-300, 1100, step):
    r = (row(z) - r0) * k
    if 0 <= r < H:
        col = (0, 0.6, 1) if z % (4 * step) == 0 else (0, 0.9, 0.3)
        a[int(r)] = a[int(r)] * 0.4 + np.array(col) * 0.6
I.write_png(out, a)
print(H, W)
