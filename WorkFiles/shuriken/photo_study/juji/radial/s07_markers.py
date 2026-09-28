"""Calibrate marker thresholds: background statistics of evidence features in the four quadrants between arms."""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
seg = np.load(os.path.join(jlib.OUT, "seg.npz"))
feat = np.load(os.path.join(jlib.OUT, "feat.npz"))
warm = feat["warm"]; grad = feat["grad"]
bg = seg["bg"]


def box(img, r):
    k = 2 * r + 1
    p = np.pad(img, r, mode='edge').astype(np.float64)
    c = np.cumsum(p, 0); c = np.concatenate([np.zeros_like(c[:1]), c], 0); v = (c[k:] - c[:-k]) / k
    c = np.cumsum(v, 1); c = np.concatenate([np.zeros_like(c[:, :1]), c], 1)
    return ((c[:, k:] - c[:, :-k]) / k).astype(np.float32)


lum = a.mean(2)
warm_s = box(warm, 2)
dark = box(bg.mean(2) - lum, 1)
quads = {"UL": (slice(60, 500), slice(60, 540)), "UR": (slice(60, 480), slice(840, 1330)),
         "LL": (slice(800, 1330), slice(60, 560)), "LR": (slice(780, 1330), slice(860, 1330))}
for k, (ys, xs) in quads.items():
    print(k, "warm_s p50/99/99.9/max", np.round(np.percentile(warm_s[ys, xs], [50, 99, 99.9, 100]), 3),
          "dark p99.9/max", np.round(np.percentile(dark[ys, xs], [99.9, 100]), 3),
          "grad p99/99.9/max", np.round(np.percentile(grad[ys, xs], [99, 99.9, 100]), 4),
          "lum p0.1/p50", np.round(np.percentile(lum[ys, xs], [0.1, 50]), 3))
