"""Tone sampler: mean colour of the bright (>70th pct) and mid (30-70th pct) pixels of a rect, per image.
blender -b --factory-startup --python sample.py -- img x0 y0 x1 y1 [img x0 y0 x1 y1 ...] (y from the top)"""
import sys
import bpy
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
for i in range(0, len(a), 5):
    im = bpy.data.images.load(a[i])
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    x0, y0, x1, y1 = map(int, a[i + 1:i + 5])
    r = px[y0:y1, x0:x1].reshape(-1, 3)
    lum = r @ np.array([0.2126, 0.7152, 0.0722])
    p30, p70, p95 = np.percentile(lum, [30, 70, 95])
    print("SAMPLE", a[i].split("\\")[-1].split("/")[-1], (x0, y0, x1, y1),
          "bright", np.round(r[lum > p70].mean(0), 3), "mid", np.round(r[(lum > p30) & (lum <= p70)].mean(0), 3),
          "top5", np.round(r[lum > p95].mean(0), 3))
