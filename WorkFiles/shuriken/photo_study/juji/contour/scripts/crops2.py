import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)
# contrast stretch for visibility
def st(a):
    lo, hi = np.percentile(a, 1), np.percentile(a, 99)
    return np.clip((a - lo) / (hi - lo), 0, 1)
write_png(ROOT + "crop_top_arm.png", st(up(rgb[0:600, 560:820], 2)))
write_png(ROOT + "crop_left_arm.png", st(up(rgb[540:790, 20:640], 2)))
