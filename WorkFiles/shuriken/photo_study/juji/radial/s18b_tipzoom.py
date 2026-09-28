import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib
a = jlib.load_image()
m = np.load(os.path.join(jlib.OUT, "mask_final_ws.npy"))
ov = a.copy()
ov[jlib.boundary(m)] = [0, 1, 0]
def crop(tag, x0, x1, y0, y1, z=5):
    c = ov[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, z, 0), z, 1)
    jlib.save_png(os.path.join(jlib.OUT, "z_tip_%s.png" % tag), c)
crop("bottom", 650, 770, 1220, 1330)
crop("top", 610, 740, 0, 100)
crop("right", 1250, 1370, 580, 690)
crop("left", 20, 140, 610, 720)
