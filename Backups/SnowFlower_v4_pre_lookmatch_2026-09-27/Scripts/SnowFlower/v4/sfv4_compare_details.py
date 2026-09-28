"""Sheet detail crops (guard / blade / pommel) beside the shipped-asset detail renders, equal height."""
import sys
from pathlib import Path
import bpy
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_png as P
ROOT = HERE.parents[2]
rd = Path(sys.argv[sys.argv.index("--") + 1])
CROPS = {"guard": (0, 530, 808, 1222), "blade": (572, 858, 800, 1222), "pommel": (878, 1195, 808, 1222)}


def load(p):
    im = bpy.data.images.load(str(p)); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1, :, :3].copy(); bpy.data.images.remove(im)
    return a


def resize(a, h):
    y = (np.arange(h) + 0.5) * a.shape[0] / h
    w = int(round(a.shape[1] * h / a.shape[0]))
    x = (np.arange(w) + 0.5) * a.shape[1] / w
    return a[np.clip(y.astype(int), 0, a.shape[0] - 1)][:, np.clip(x.astype(int), 0, a.shape[1] - 1)]


ref = load(ROOT / "References/SnowFlower/SnowFlower_user_reference.png")
for k, (y0, y1, x0, x1) in CROPS.items():
    c = ref[y0:y1, x0:x1]
    o = load(rd / f"detail_{k}.png")
    H = 900
    img = np.concatenate([resize(c, H), np.full((H, 8, 3), 0.8), resize(o, H)], 1)
    P.write_png(rd / f"compare_detail_{k}.png", img)
print("SF4_DETAILS_DONE")
