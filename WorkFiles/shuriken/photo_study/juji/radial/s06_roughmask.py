"""Rough mask from warm chromaticity + strong darkness, used as the starting contour for edge refinement."""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
seg = np.load(os.path.join(jlib.OUT, "seg.npz"))
feat = np.load(os.path.join(jlib.OUT, "feat.npz"))
bg = seg["bg"]
warm = feat["warm"]


def box(img, r):
    k = 2 * r + 1
    p = np.pad(img, r, mode='edge').astype(np.float64)
    c = np.cumsum(p, 0); c = np.concatenate([np.zeros_like(c[:1]), c], 0); v = (c[k:] - c[:-k]) / k
    c = np.cumsum(v, 1); c = np.concatenate([np.zeros_like(c[:, :1]), c], 1)
    return ((c[:, k:] - c[:, :-k]) / k).astype(np.float32)


lum = a.mean(2)
bl = bg.mean(2)
warm_s = box(warm, 2)
dark = bl - box(lum, 1)
bgw = warm_s[:30].ravel()
print("warm_s top-border stats p50 p99 p99.9", np.percentile(bgw, [50, 99, 99.9]))
for thr in (0.05, 0.06, 0.07):
    m = (warm_s > thr) | (dark > 0.12)
    m = jlib.opening(m, 2)
    m = jlib.largest_component(m)
    f, h = jlib.fill_holes(m)
    print("thr", thr, "px", f.sum(), "holes", h.sum())
m = (warm_s > 0.06) | (dark > 0.12)
m = jlib.opening(m, 2)
m = jlib.largest_component(m)
f, h = jlib.fill_holes(m)
f = jlib.closing(f, 2)
np.save(os.path.join(jlib.OUT, "rough_mask.npy"), f)
jlib.save_png(os.path.join(jlib.OUT, "dbg_roughmask.png"), f)
# overlay
ov = a.copy()
bd = jlib.boundary(f)
ov[bd] = [0, 1, 0]
jlib.save_png(os.path.join(jlib.OUT, "dbg_roughmask_overlay.png"), ov)
