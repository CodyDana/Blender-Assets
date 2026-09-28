import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib
a = jlib.load_image()
lum = a.mean(2)
np.set_printoptions(linewidth=300)
print("upper edges of horizontal arms: lum*100 at y=548..660 step 2 (3px wide avg)")
for x in [120, 200, 280, 360, 440, 520, 580, 800, 860, 920, 980, 1060, 1140, 1220, 1300]:
    col = lum[548:662:2, x-1:x+2].mean(1)
    print("x%4d" % x, " ".join("%2d" % v for v in (col*100).astype(int)))
print("lower edges: y=640..760")
for x in [120, 200, 280, 360, 440, 520, 580, 800, 860, 920, 980, 1060, 1140, 1220, 1300]:
    col = lum[640:762:2, x-1:x+2].mean(1)
    print("x%4d" % x, " ".join("%2d" % v for v in (col*100).astype(int)))
print("left edges of vertical arms: x=560..700")
for y in [60, 120, 200, 300, 400, 480, 850, 950, 1050, 1150, 1250]:
    row = lum[y-1:y+2, 560:702:2].mean(0)
    print("y%4d" % y, " ".join("%2d" % v for v in (row*100).astype(int)))
print("right edges of vertical arms: x=700..840")
for y in [60, 120, 200, 300, 400, 480, 850, 950, 1050, 1150, 1250]:
    row = lum[y-1:y+2, 700:842:2].mean(0)
    print("y%4d" % y, " ".join("%2d" % v for v in (row*100).astype(int)))
