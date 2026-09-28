import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)
write_png(ROOT + "crop_top_tip.png", up(rgb[0:80, 620:760], 5))
write_png(ROOT + "crop_bottom_tip.png", up(rgb[1240:1330, 660:780], 5))
write_png(ROOT + "crop_left_tip.png", up(rgb[600:720, 20:160], 5))
write_png(ROOT + "crop_right_tip.png", up(rgb[580:700, 1230:1370], 5))
write_png(ROOT + "crop_centre.png", up(rgb[520:800, 560:820], 3))
