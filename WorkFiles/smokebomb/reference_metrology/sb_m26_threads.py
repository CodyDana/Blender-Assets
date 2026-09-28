"""Stage 26: loose-thread candidate detector: thin bright ridges (sigma 1.2) whose direction departs from the local
strip (warp) direction by > 35 deg, grouped into components >= 12 px long. Prints candidates for visual review."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
from sb_m08_segments import components

rgb = L.load_srgb(); Y = L.lum(rgb).astype(np.float32)
ball = Y < 0.6
er = L.box_blur(ball.astype(np.float32), 5) > 0.999
Yl = np.log(np.clip(Y, 0.02, 1))
G = L.gauss_blur(Yl, 1.2)
gy, gx = np.gradient(G); gyy, gyx = np.gradient(gy); gxy, gxx = np.gradient(gx)
# Hessian eigen: bright ridge -> strongly negative eigenvalue across
tr_ = gxx + gyy; det = gxx * gyy - gxy * gxy
disc = np.sqrt(np.maximum(0, tr_ * tr_ / 4 - det))
l1 = tr_ / 2 - disc      # most negative
ridge = np.maximum(0, -l1)
# eigenvector for l1: (gxy, l1 - gxx) -> normal direction; ridge direction perpendicular
nx, ny = gxy, l1 - gxx
ang_n = np.arctan2(-ny, nx)                     # y-up
ridge_dir = (np.degrees(ang_n) + 90) % 180
ori = np.load(os.path.join(L.D, "sb_s4_orient_s12.npy"))
strip_dir = ori[0]
dd = np.abs(((ridge_dir - strip_dir) + 90) % 180 - 90)
# also against the perpendicular (weft) direction
dw = np.abs(((ridge_dir - strip_dir - 90) + 90) % 180 - 90)
p = np.percentile(ridge[er], 98.5)
bright = Y > L.gauss_blur(Y, 6) * 1.15
cand = er & (ridge > p) & (dd > 30) & bright
ys, xs, roots = components(cand)
res = []
for rt in np.unique(roots):
    m = roots == rt
    if m.sum() < 8:
        continue
    c = np.c_[xs[m], ys[m]].astype(float)
    u, s, vt = np.linalg.svd(c - c.mean(0), full_matrices=False)
    t = (c - c.mean(0)) @ vt[0]
    length = t.max() - t.min()
    if length < 10:
        continue
    res.append(dict(cx=round(float(c[:, 0].mean())), cy=round(float(c[:, 1].mean())), length_px=round(float(length), 1),
                    n=int(m.sum()), bbox=[int(c[:, 0].min()), int(c[:, 1].min()), int(c[:, 0].max()), int(c[:, 1].max())]))
res.sort(key=lambda r: -r['length_px'])
print("CANDIDATES", len(res))
for r in res[:40]:
    print("  ", r)
L.dump("sb_s26_thread_candidates.json", res)
