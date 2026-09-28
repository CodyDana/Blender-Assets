import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m1")
from m1_lib import *
r = load(REF); print(r.shape)
L = lab(r)
# card box: non-white
nonwhite = (L[..., 0] < 97) | (np.abs(L[..., 2]) > 6)
ys, xs = np.nonzero(nonwhite); print("nonwhite bbox", xs.min(), xs.max(), ys.min(), ys.max())
row = nonwhite.mean(1); col = nonwhite.mean(0)
print("rows>0.5", np.nonzero(row > 0.5)[0][[0, -1]], "cols>0.5", np.nonzero(col > 0.5)[0][[0, -1]])
up = upscale_nn(r, 3)
for g in range(0, 300, 10):
    up[:, g*3, :] = [0, 0.6, 1] if g % 50 else [0, 0, 1]
for g in range(0, 653, 10):
    up[g*3, :, :] = [0, 0.6, 1] if g % 50 else [0, 0, 1]
save(up[:990], OUT+"m1_refgrid_top.png"); save(up[960:], OUT+"m1_refgrid_bot.png")
