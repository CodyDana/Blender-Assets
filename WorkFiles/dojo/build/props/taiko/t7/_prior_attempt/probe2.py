"""probe: the photo's skirt hems (upper: first wood row below the hide; lower: first wood row above it) + zoom crops"""
import sys, math, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import median_filter
T7 = Path(__file__).resolve().parent
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
img = Image.open(ROOT / "References/Dojo/taiko_tacks_ref_user.webp").convert("RGB")
a = np.asarray(img).astype(float)
lum = a.mean(2)
rg = a[..., 0] / np.maximum(a[..., 1], 1)
fg = a.min(2) < 240
hide = (rg < 1.45) & (lum > 60) & fg


def hem_upper(u):
    for v in range(250, 380):
        if not hide[v:v + 6, u].any():
            return v
    return np.nan


def hem_lower(u):
    for v in range(905, 690, -1):
        if not hide[v - 5:v + 1, u].any():
            return v
    return np.nan


U = np.arange(110, 915)
hu = np.array([hem_upper(u) for u in U], float)
hl = np.array([hem_lower(u) for u in U], float)
out = {"u": U.tolist(), "upper_raw": hu.tolist(), "lower_raw": hl.tolist()}
(T7 / "probe2_hems.json").write_text(json.dumps(out), encoding="utf-8")
dbg = img.copy()
d = ImageDraw.Draw(dbg)
for u, v in zip(U, hu):
    if not np.isnan(v):
        d.point((u, v), fill=(0, 255, 0))
for u, v in zip(U, hl):
    if not np.isnan(v):
        d.point((u, v), fill=(0, 255, 255))


def crop(box, name, k=4, grid=10):
    c = dbg.crop(box).resize(((box[2] - box[0]) * k, (box[3] - box[1]) * k), Image.LANCZOS)
    dd = ImageDraw.Draw(c)
    for y in range(box[1] - box[1] % grid + grid, box[3], grid):
        dd.line([(0, (y - box[1]) * k), (8 if y % 50 else 20, (y - box[1]) * k)], fill=(255, 0, 0))
        if y % 20 == 0:
            dd.text((22, (y - box[1]) * k - 6), str(y), fill=(255, 0, 0))
    for x in range(box[0] - box[0] % grid + grid, box[2], grid):
        dd.line([((x - box[0]) * k, 0), ((x - box[0]) * k, 8 if x % 50 else 20)], fill=(0, 0, 255))
        if x % 20 == 0:
            dd.text(((x - box[0]) * k - 8, 22), str(x), fill=(0, 0, 255))
    c.save(T7 / name)


for i, x0 in enumerate(range(100, 920, 205)):
    crop((x0, 230, x0 + 215, 345), "zu_%d.png" % i)
    crop((x0, 700, x0 + 215, 915), "zl_%d.png" % i, k=4)
