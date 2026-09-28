import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
lum = a.mean(2)
rb = a[:, :, 0] - a[:, :, 2]


def vprof(x, y0, y1):
    print("--- vertical profile x=%d" % x)
    for y in range(y0, y1):
        r, g, b = a[y, x - 1:x + 2].mean(0)
        print("y%4d lum %.3f rb %.3f  rgb %.2f %.2f %.2f" % (y, lum[y, x - 1:x + 2].mean(), rb[y, x - 1:x + 2].mean(), r, g, b))


def hprof(y, x0, x1):
    print("--- horizontal profile y=%d" % y)
    for x in range(x0, x1):
        r, g, b = a[y - 1:y + 2, x].mean(0)
        print("x%4d lum %.3f rb %.3f  rgb %.2f %.2f %.2f" % (x, lum[y - 1:y + 2, x].mean(), rb[y - 1:y + 2, x].mean(), r, g, b))


vprof(900, 570, 700)
hprof(300, 600, 780)
