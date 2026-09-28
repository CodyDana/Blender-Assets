import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_indep")
from ms_lib import *
args = sys.argv[sys.argv.index('--')+1:]
name, r0, r1, k = args[0], int(args[1]), int(args[2]), int(args[3])
img = load(D+"cmp_"+name+".png")[..., :3]
w = img.shape[1]//3
c = img[r0:r1, :2*w]
savepng(D+"zoom_"+name+"_%d_%d.png" % (r0, r1), np.repeat(np.repeat(c, k, 0), k, 1))
