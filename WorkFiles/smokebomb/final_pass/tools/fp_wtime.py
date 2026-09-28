import sys, time, types
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import smokebomb_wind as W
from props_lib import smokebomb_wind_fit as F
t = time.time()
wd = W.reference_winding(F)
print("assemble", time.time() - t); t = time.time()
lab = W.render_labels(wd, "front", size=627)
print("labels", time.time() - t)
np.save(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/final_pass/lab_orig.npy", lab["pass_"])
print(np.unique(lab["pass_"], return_counts=True))
