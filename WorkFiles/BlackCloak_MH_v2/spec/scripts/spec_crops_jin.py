import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from spec_imgutil import *
O = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out"
a = load(os.path.join(O, "spec_jin_full.png"))
print(a.shape)
# head/collar region with a 50px grid (full-res coords)
c = a[300:1500, 600:1700].copy()
c = draw_grid(c, 50, (1, 0, 0))
c[::100, :, :3] = (0, 0, 1); c[:, ::100, :3] = (0, 0, 1)
save(c[::2, ::2], os.path.join(O, "spec_jin_head_grid.png"))   # 550x600, grid every 25 px displayed = 50 px full, blue every 100 full
c = a[1100:1600, 350:850].copy(); c = draw_grid(c, 50); save(c, os.path.join(O, "spec_jin_clasp_grid.png"))
