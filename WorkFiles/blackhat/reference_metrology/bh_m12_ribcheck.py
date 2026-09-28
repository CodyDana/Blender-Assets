"""Debug: 2x image with candidate heavy ribs (red), thin lines (cyan), lashings (yellow) drawn from the apex."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_draw import *
im = load_srgb(); k = 2
img = upscale(stretch(im, 0, 0.5), k).copy()
xa, ya = 334.03, 139.93
heavy = [-56.3, -35.3, 12.0, 39.6]
thin = [-63.0, -59.75, -51.5, -46.3, -40.5, -31.0, -25.25, -14.5, -0.25, 27.5, 33.5, 56.0, 59.0, 62.5]
for lst, col in ((heavy, (1, 0, 0)), (thin, (0, 0.9, 1))):
    for p in lst:
        a = np.radians(p)
        line(img, xa + 30 * np.sin(a), ya + 30 * np.cos(a), xa + 70 * np.sin(a), ya + 70 * np.cos(a), col, k, 2)
        line(img, xa + 330 * np.sin(a), ya + 330 * np.cos(a), xa + 360 * np.sin(a), ya + 360 * np.cos(a), col, k, 2)
save_png(os.path.join(DBG, 'dbg_ribcandidates_2x.png'), img)
