import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape


def crop(name, x0, x1, y0, y1, z=4):
    c = a[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, z, 0), z, 1)
    jlib.save_png(os.path.join(jlib.OUT, "crop_%s.png" % name), c)


crop("top_tip", 620, 780, 0, 110)
crop("left_tip", 20, 200, 580, 720)
crop("right_tip", 1200, 1370, 570, 700)
crop("bot_tip", 640, 800, 1220, 1340)
crop("junction", 560, 820, 520, 800, 3)
crop("top_neck", 580, 780, 380, 540, 3)
# print raw values around top tip rows 0..10
np.set_printoptions(linewidth=250, precision=2)
for y in range(0, 12):
    row = a[y, 660:740].mean(1)
    print(y, (row * 100).astype(int))
