"""Crop + upscale + optional contrast stretch for visual inspection. args: name x0 y0 x1 y1 k lo hi"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
a = sys.argv[sys.argv.index('--') + 1:]
name = a[0]; x0, y0, x1, y1, k = map(int, a[1:6]); lo, hi = float(a[6]), float(a[7])
im = load_srgb()[y0:y1, x0:x1]
im = stretch(im, lo, hi)
save_png(os.path.join(DBG, name + '.png'), upscale(im, k))
