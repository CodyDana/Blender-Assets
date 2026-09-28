"""Save magnified crops of the original (optionally with mask edge) for visual checks.
usage: blender -b --python crops.py -- name x0 y0 x1 y1 scale [maskfile]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:]
rgb = np.load(os.path.join(OUT, "rgb.npy"))
i = 0
while i < len(argv):
    name = argv[i]; x0, y0, x1, y1, s = map(int, argv[i + 1:i + 6]); maskf = argv[i + 6]
    i += 7
    c = rgb[y0:y1, x0:x1].copy()
    if maskf != "none":
        m = np.load(os.path.join(OUT, maskf))[y0:y1, x0:x1]
        e = m & ~L.erode(m, 1)
        c[e] = c[e] * 0.3 + np.array([1, 0, 0]) * 0.7
    c = np.repeat(np.repeat(c, s, 0), s, 1)
    os.makedirs(os.path.join(OUT, "crops"), exist_ok=True)
    L.save_png(os.path.join(OUT, "crops", name + ".png"), c)
