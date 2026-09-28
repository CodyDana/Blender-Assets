import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import fan_look as LK, fan_refview as RV
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/dev1/"
ref = LK.load_png(r"C:/Users/Cody/Desktop/Blender_Projects/References/Fan/fan2.png")[..., :3].astype(np.float64)
ren = LK.load_png(D + "Renders/Fan/fan_reference_view.png")[..., :3].astype(np.float64)
mr = RV.photo_mask(ref); mn = RV.photo_mask(ren)
out = np.ones(ref.shape) * 0.9
out[mr & mn] = (0.3, 0.3, 0.3)
out[mr & ~mn] = (1, 0, 0)       # in photo only
out[~mr & mn] = (0, 0.4, 1)     # in render only
LK.write_png(D + "diff_mask.png", out)
print("photo only", int((mr & ~mn).sum()), "render only", int((~mr & mn).sum()))
