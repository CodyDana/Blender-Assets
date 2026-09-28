import bpy, numpy as np, sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
img = bpy.data.images.load(DBG + "/DEBUG_NEVER_SHIP_fan2_layout_LABELLED.png"); w, h = img.size
a = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
save_png(a[380:560, 520:760], "DEBUG_NEVER_SHIP_fan2_layout_zoom_rightend_x4", 4)
save_png(a[380:560, 40:280], "DEBUG_NEVER_SHIP_fan2_layout_zoom_leftend_x4", 4)
print("done")
