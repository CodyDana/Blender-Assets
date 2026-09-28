"""Save enlarged crops of the photo (or an overlay png) for visual inspection.
blender -b --factory-startup --python crops.py -- <img> <outdir> name:x0:y0:x1:y1:scale [...]
(coords top-origin)
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
src, outdir = argv[0], argv[1]
rgb = imgio.load_rgb(src)
for spec in argv[2:]:
    name, x0, y0, x1, y1, s = spec.split(":")
    x0, y0, x1, y1, s = int(x0), int(y0), int(x1), int(y1), int(s)
    c = rgb[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, s, axis=0), s, axis=1)
    imgio.save_rgb(os.path.join(outdir, name + ".png"), c)
    print("saved", name, c.shape)
