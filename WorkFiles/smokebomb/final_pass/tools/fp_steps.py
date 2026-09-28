import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import read_png
from props_lib import smokebomb_metrics as MT
for p in sys.argv[1:]:
    a = np.load(p) if p.endswith(".npy") else read_png(p)[..., :3] / 255.0
    s = MT.silhouette(np.asarray(a, np.float64)[..., :3])
    st = s["steps"]
    print(p.split("/")[-2] if "/" in p else p, st["count_ge_4px"], {k: v for k, v in st.items() if k != "count_ge_4px"})
