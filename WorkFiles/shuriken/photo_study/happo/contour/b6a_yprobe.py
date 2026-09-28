# probe the yellowness channel Y=(R+G)/2-B across a few edges (outer line frame from b5)
import sys, os, json, numpy as np
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour")
from common import *
rgb = np.load(os.path.join(OUT, "rgb.npy")).astype(np.float64)
Y = (rgb[..., 0] + rgb[..., 1]) / 2 - rgb[..., 2]
L = np.load(os.path.join(OUT, "L.npy")).astype(np.float64)
R = json.load(open(os.path.join(OUT, "b5_edges.json")))
TS = np.arange(-25, 20.01, 1.0); SS = np.arange(-5, 5.01, 1.0)
for name in sys.argv[sys.argv.index("--") + 1:]:
    e = R[name]; m = np.array(e["outer_pt"]); dv = np.array(e["outer_dir"]); n = np.array(e["outer_n"])
    P = np.array([p for p in e["pts_outer"] if p[0] == p[0]])
    s = (P - m) @ dv
    for q in (0.25, 0.5, 0.75):
        s0 = np.quantile(s, q); base = m + dv * s0
        xs = base[0] + TS[None, :] * n[0] + SS[:, None] * dv[0]; ys = base[1] + TS[None, :] * n[1] + SS[:, None] * dv[1]
        py = bil(Y, xs, ys).mean(0); pl = bil(L, xs, ys).mean(0)
        print(name, "q%.2f" % q, " ".join("%+d:%.3f/%.2f" % (t, a, b) for t, a, b in zip(TS, py, pl) if int(t) % 2 == 0))
