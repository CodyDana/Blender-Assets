import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
R = load(REFP)[..., :3]
H = 745
top = R[:H]
lum = top @ np.array([0.2126, 0.7152, 0.0722])
# background model: per-row robust estimate from known empty columns, interpolated along x
gapcols = [(0, 45), (330, 360), (600, 625), (935, 960), (1225, 1254)]
xs_c, bg_c = [], []
for a, b in gapcols:
    xs_c.append((a + b) / 2); bg_c.append(np.median(lum[:, a:b], 1))
xs_c = np.array(xs_c); bg_c = np.array(bg_c).T  # H x 5
bg = np.stack([np.interp(np.arange(1254), xs_c, bg_c[y]) for y in range(H)])
# smooth local std
def boxf(a, r):
    c = np.cumsum(np.cumsum(np.pad(a, ((r + 1, r), (r + 1, r)), mode="edge"), 0), 1)
    return (c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]) / (2 * r + 1) ** 2
d = lum - bg
sat = top.max(2) - top.min(2)
m1 = boxf(lum, 2); m2 = boxf(lum ** 2, 2); sd = np.sqrt(np.maximum(m2 - m1 ** 2, 0))
obj = (np.abs(d) > 9) | (sat > 12) | (sd > 5.5)
np.save("m2_refmask_raw.npy", obj)
ov = top.copy(); ov[obj] = ov[obj] * 0.5 + np.array([255, 0, 0]) * 0.5
save(ROOT + "WorkFiles/flashbang/measure_r2/m2_refmask_raw.png", ov)
print("M2 done")
