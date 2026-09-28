import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
print("size", W, H)
B = 12
border = np.concatenate([a[:B].reshape(-1, 3), a[-B:].reshape(-1, 3), a[:, :B].reshape(-1, 3), a[:, -B:].reshape(-1, 3)])
print("border median", np.median(border, 0), "p5", np.percentile(border, 5, 0), "p95", np.percentile(border, 95, 0))
for name, sl in [("top", a[:B]), ("bottom", a[-B:]), ("left", a[:, :B]), ("right", a[:, -B:])]:
    s = sl.reshape(-1, 3)
    print(name, np.median(s, 0), np.percentile(s, 2, 0), np.percentile(s, 98, 0))
# profile along the right border columns (scanner artefact?)
for x in [W - 1, W - 3, W - 6, W - 10, W - 20]:
    print("col", x, np.median(a[:, x], 0))
for y in [0, 2, 5, H - 1, H - 3, H - 6]:
    print("row", y, np.median(a[y], 0))
lum = a.mean(2)
chroma = a.max(2) - a.min(2)
rb = a[:, :, 0] - a[:, :, 2]
print("chroma border median", np.median(chroma[:B]), np.percentile(np.concatenate([chroma[:B].ravel(), chroma[-B:].ravel()]), 99))
jlib.save_png(os.path.join(jlib.OUT, "dbg_chroma.png"), np.clip(chroma * 4, 0, 1))
jlib.save_png(os.path.join(jlib.OUT, "dbg_rb.png"), np.clip(rb * 4 + 0.2, 0, 1))
jlib.save_png(os.path.join(jlib.OUT, "dbg_lum.png"), lum)
# coarse background map: block medians
bs = 40
gy, gx = H // bs, W // bs
blk = a[:gy * bs, :gx * bs].reshape(gy, bs, gx, bs, 3).transpose(0, 2, 1, 3, 4).reshape(gy, gx, -1, 3)
med = np.median(blk, 2)
np.set_printoptions(linewidth=250, precision=2)
print("block median lum (x40 px)")
print((med.mean(2) * 100).astype(int))
print("block median chroma")
print(((med.max(2) - med.min(2)) * 100).astype(int))
