import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib
a = jlib.load_image()
def crop(tag, x0, x1, y0, y1, z=6):
    c = a[y0:y1, x0:x1].copy()
    lo = np.percentile(c, 1); hi = np.percentile(c, 99)
    c = (c - lo) / (hi - lo)
    c = np.repeat(np.repeat(c, z, 0), z, 1)
    jlib.save_png(os.path.join(jlib.OUT, "enh_%s.png" % tag), c)
crop("topR_y300", 720, 800, 270, 330)
crop("topL_y300", 590, 690, 270, 330)
crop("rneck_upper", 870, 930, 570, 630)
crop("rneck_lower", 870, 930, 660, 710)
crop("botL_y1100", 600, 680, 1070, 1130)
