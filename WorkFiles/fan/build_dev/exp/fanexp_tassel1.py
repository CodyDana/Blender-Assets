import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_tassel as T
for lod in range(3):
    mb, info = T.build_tassel(FAN, lod)
    s = T.tassel_uvs(mb)
    uv = np.concatenate(mb.TUV)
    print(info, "px/mm", round(s, 2), uv.min(0).round(3), uv.max(0).round(3), "maxinfl", max(len(w) for w in mb.W))
print(T.bone_table(FAN))
