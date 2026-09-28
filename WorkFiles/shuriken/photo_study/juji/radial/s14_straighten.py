"""Resample each arm into a straightened strip: columns = station s along the (watershed) axis, rows = t
(perpendicular, arm's LEFT side on top). Stacks the four arms into one image for visual comparison."""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
tag = "ws"
names = ["right", "top", "left", "bottom"]
m = np.load(os.path.join(jlib.OUT, "mask_final_ws.npy")).astype(np.float32)
strips = []
S = np.arange(0, 680, 1.0)
T = np.arange(120, -120.5, -1.0)   # top row = +t (arm's left)
for nme in names:
    d = np.load(os.path.join(jlib.OUT, "arm_%s_%s.npz" % (tag, nme)))
    u, n, origin = d["u"], d["n"], d["origin"]
    X = origin[0] + S[None, :] * u[0] + T[:, None] * n[0]
    Y = origin[1] + S[None, :] * u[1] + T[:, None] * n[1]
    ok = (X >= 0) & (X <= W - 1) & (Y >= 0) & (Y <= H - 1)
    img = jlib.bilinear(a, X, Y)
    img[~ok] = [1, 0, 1]
    mm = jlib.bilinear(m, X, Y) > 0.5
    edge = mm ^ np.roll(mm, 1, 0)
    img2 = img.copy()
    img2[edge] = [0, 1, 0]
    strips.append(np.concatenate([img, img2], 0))
    strips.append(np.ones((6, len(S), 3), np.float32))
out = np.concatenate(strips, 0)
jlib.save_png(os.path.join(jlib.OUT, "dbg_straightened_arms.png"), out)
print(out.shape)
