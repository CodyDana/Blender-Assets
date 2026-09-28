import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_lm1")
from mlm1_lib import *
a = sys.argv[sys.argv.index('--')+1:]
view, r0, r1, k = a[0], int(a[1]), int(a[2]), int(a[3])
im = load(D+"mlm1_cmp_"+view+".png")[..., :3]
c = im[r0:r1]
savepng(D+"mlm1_zoom_%s_%d_%d.png" % (view, r0, r1), resize(c, c.shape[0]*k, c.shape[1]*k))
