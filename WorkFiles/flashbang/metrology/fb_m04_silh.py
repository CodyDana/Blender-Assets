import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
fg = np.load(DBG + "/fb_fg_raw.npy")
H, W = fg.shape
fg[721:] = False
def dil(m, r): return box_blur(m.astype(np.float32), r) > 1e-3
def ero(m, r): return box_blur(m.astype(np.float32), r) > 1 - 1e-3
m = dil(ero(fg, 1), 1)          # open: remove specks
m = ero(dil(m, 2), 2)           # close
m[721:] = False
# outside flood from border
bgm = ~m
out = np.zeros_like(m); out[0, :] = bgm[0, :]; out[:, 0] = bgm[:, 0]; out[:, -1] = bgm[:, -1]; out[-1, :] = bgm[-1, :]
for it in range(3000):
    n = out.copy()
    n[1:] |= out[:-1]; n[:-1] |= out[1:]; n[:, 1:] |= out[:, :-1]; n[:, :-1] |= out[:, 1:]
    n &= bgm
    if (n == out).all(): break
    out = n
sil = ~out
# enclosed background holes: classify (ring interior vs hole in body)
holes = sil & ~m
np.save(DBG + "/fb_sil.npy", sil); np.save(DBG + "/fb_m.npy", m)
ref = load_srgb()[:H]
vis = ref.copy()*0.6
vis[sil & m] = vis[sil & m]*0.5 + np.array([0.5, 0, 0])
vis[holes] = [0, 0.6, 0]
save_png(DBG + "/sil.png", vis)
print("iters", it)
