import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib
a = jlib.load_image()
def crop(name, x0, x1, y0, y1, z=4):
    c = a[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, z, 0), z, 1)
    jlib.save_png(os.path.join(jlib.OUT, "crop_%s.png" % name), c)
crop("right_neck", 760, 1000, 550, 710, 3)
crop("left_upper", 330, 600, 550, 720, 3)
crop("top_arm_mid", 560, 800, 150, 350, 3)
crop("bot_arm_mid", 600, 820, 800, 1000, 3)
