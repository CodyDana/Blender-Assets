"""Hilt close comparison at 4x: sheet front/side/back vs the shipped-asset refviews (same scale)."""
import sys
from pathlib import Path
import bpy
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_png as P
ROOT = HERE.parents[2]
argv = sys.argv[sys.argv.index("--") + 1:]
rd = Path(argv[0]); outp = Path(argv[1]); prefix = argv[2] if len(argv) > 2 else "ref"
r0, r1 = (int(argv[3]), int(argv[4])) if len(argv) > 4 else (0, 380)
def load(p):
    im = bpy.data.images.load(str(p)); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1].copy(); bpy.data.images.remove(im)
    if a.shape[2] == 4:
        a = a[..., :3] * a[..., 3:] + (1 - a[..., 3:])
    return a[..., :3]
ref = load(ROOT / "References/SnowFlower/SnowFlower_user_reference.png")
AX = {"front": 287.5, "side": 489.0, "back": 681.0}
cols = []
for v, ax in AX.items():
    o = load(rd / f"{prefix}_{v}.png")
    x0 = int(ax - 75)
    cols += [ref[r0:r1, x0:x0 + 150], o[r0:r1, 75:225], np.full((r1 - r0, 3, 3), 0.7)]
img = np.concatenate(cols[:-1], 1)
P.write_png(outp, np.repeat(np.repeat(img, 3, 0), 3, 1))
print("SF4_HILT_DONE")
