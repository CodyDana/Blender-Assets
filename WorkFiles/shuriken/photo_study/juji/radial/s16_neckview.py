"""Zoomed straightened views (neck and blade) with ridge line and edge estimates drawn, for visual audit."""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
names = ["right", "top", "left", "bottom"]
s0, s1 = int(sys.argv[sys.argv.index("--") + 1]), int(sys.argv[sys.argv.index("--") + 2])
z = 3
strips = []
for nme in names:
    d = np.load(os.path.join(jlib.OUT, "arm_ws_%s.npz" % nme))
    u, n, origin = d["u"], d["n"], d["origin"]
    r = np.load(os.path.join(jlib.OUT, "refine_%s.npz" % nme))
    S = np.arange(s0, s1, 1.0 / z)
    T = np.arange(110, -110, -1.0 / z)
    X = origin[0] + S[None, :] * u[0] + T[:, None] * n[0]
    Y = origin[1] + S[None, :] * u[1] + T[:, None] * n[1]
    img = jlib.bilinear(a, X, Y).astype(np.float32)
    # contrast stretch
    lo, hi = np.percentile(img, 0.5), np.percentile(img, 99.5)
    img = np.clip((img - lo) / (hi - lo), 0, 1)
    def draw(tvals, col):
        for ci, s in enumerate(S):
            i = int(np.argmin(np.abs(r["S"] - s)))
            t = tvals[i]
            if np.isfinite(t):
                ri = int(round((110 - t) * z))
                if 0 <= ri < len(T):
                    img[ri, ci] = col
    draw(r["ridge"], [1, 0, 1])
    draw(r["ws_L"], [0, 1, 0]); draw(r["ws_R"], [0, 1, 0])
    draw(r["t90_L"], [0, 0.6, 1]); draw(r["t90_R"], [0, 0.6, 1])
    draw(r["ridge_raw"], [1, 1, 0])
    strips.append(img)
    strips.append(np.ones((4, img.shape[1], 3), np.float32))
jlib.save_png(os.path.join(jlib.OUT, "dbg_neckview_%d_%d.png" % (s0, s1)), np.concatenate(strips, 0))
