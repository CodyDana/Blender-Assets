import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib
a = jlib.load_image()
name = sys.argv[sys.argv.index("--") + 1]
m = np.load(os.path.join(jlib.OUT, name + ".npy"))
ov = a.copy()
ov[jlib.boundary(m)] = [0, 1, 0]
def crop(tag, x0, x1, y0, y1, z=3):
    c = ov[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, z, 0), z, 1)
    jlib.save_png(os.path.join(jlib.OUT, "z_%s_%s.png" % (name, tag)), c)
crop("rneck", 760, 1000, 540, 720)
crop("lup", 150, 450, 540, 720)
crop("botR", 700, 860, 900, 1120)
crop("topL", 560, 720, 150, 400)
crop("toptip", 600, 760, 0, 120, 4)
