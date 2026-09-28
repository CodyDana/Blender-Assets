import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, sv2_imgmetrics as M
im = M.load("C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")
O = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/crops/"
def mag(a, f): return np.repeat(np.repeat(a, f, 0), f, 1)
# three fabric crops 96x96 px (~26 cm) magnified x4, displayed with gain (x3 linear) and stretched
tiles = []
for (x, y) in [(240, 420), (160, 250), (300, 520)]:
    c = im[y:y+96, x:x+96]
    lin = M.s2l(c/255.0)
    g = M.l2s(np.clip(lin*3, 0, 1))*255
    L = M.lum(c); lo, hi = np.percentile(L, [1, 99])
    st = np.clip((L-lo)/(hi-lo), 0, 1)*255
    tiles.append(np.concatenate([mag(g, 4), np.stack([mag(st, 4)]*3, -1)], 0))
M.save(O + "sv2_photo_fabric_crops_x4.png", np.concatenate(tiles, 1))
print("ok")
