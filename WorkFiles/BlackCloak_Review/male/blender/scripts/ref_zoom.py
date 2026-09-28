import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from imgutil import load, save
from common import REF
import numpy as np
r = load(REF)[..., :3]
c = r[60:120, 85:145]
big = np.repeat(np.repeat(c, 10, 0), 10, 1)
# grid every 10 ref px
for k in range(0, big.shape[0], 100): big[k, :, :] = (1, 0, 0)
for k in range(0, big.shape[1], 100): big[:, k, :] = (1, 0, 0)
save(big, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/blender/compare/_ref_clasp_zoom_x85_y60_grid10.png")
