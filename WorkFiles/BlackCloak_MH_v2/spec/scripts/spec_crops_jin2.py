import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from spec_imgutil import *
O = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out"
a = load(os.path.join(O, "spec_jin_full.png"))
c = a[450:850, 900:1400].copy()   # face: eyes .. collar rim, 20 px grid, blue every 100
c[::20, :, :3] = (1, 0, 0); c[:, ::20, :3] = (1, 0, 0)
c[::100, :, :3] = (0, 0, 1); c[:, ::100, :3] = (0, 0, 1)
save(c, os.path.join(O, "spec_jin_face_grid20.png"))
# whole figure at 1/4 with a 100 px (full-res) grid for silhouette / fold reading
d = a[::4, ::4].copy()
d[::25, :, :3] = (1, 0, 0); d[:, ::25, :3] = (1, 0, 0)
save(d, os.path.join(O, "spec_jin_quarter_grid100.png"))
