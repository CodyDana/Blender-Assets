import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib
a = jlib.load_image()
def crop(name, x0, x1, y0, y1, z=4, stretch=True):
    c = a[y0:y1, x0:x1].copy()
    if stretch:
        lo, hi = np.percentile(c, 0.5), np.percentile(c, 99.5)
        c = np.clip((c - lo) / (hi - lo), 0, 1)
    c = np.repeat(np.repeat(c, z, 0), z, 1)
    jlib.save_png(os.path.join(jlib.OUT, "crop_%s.png" % name), c)
crop("topneck", 600, 790, 400, 520)
crop("botneck", 610, 790, 800, 900)
crop("leftneck", 440, 600, 560, 730)
crop("rightneck2", 790, 950, 560, 710)
