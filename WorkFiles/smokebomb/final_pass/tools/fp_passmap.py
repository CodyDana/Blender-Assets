"""fp_passmap - from a saved stretch-id map + info, paint by pass with a legend strip, plus per-pass stats."""
import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import write_png, read_png
stem = sys.argv[1]
sid = np.load(stem + "_sid.npy"); info = json.load(open(stem + "_info.json"))
kp = {i["k"]: i["pass_"] for i in info}
passes = sorted(set(kp.values()))
pal = np.array([[.9,.1,.1],[.1,.7,.1],[.1,.3,.9],[.9,.8,.1],[.8,.1,.8],[.1,.8,.8],[1,.5,0],[.5,.2,.8],[.4,.9,.5],[.9,.5,.6],
                [.5,.3,.1],[.2,.2,.2],[.7,.7,.7],[0,.4,.4],[.6,.6,0],[.4,0,0],[0,0,.5],[1,.8,.8],[.6,1,1],[.3,.5,.3],[1,1,.6],[.5,.5,1]])
H = sid.shape[0]; img = np.ones((H, H, 3))
pm = -np.ones_like(sid)
for k, p in kp.items(): pm[sid == k] = passes.index(p)
for i, p in enumerate(passes): img[pm == i] = pal[i % len(pal)]
e = np.zeros((H, H), bool)
e[:, 1:] |= sid[:, 1:] != sid[:, :-1]; e[1:, :] |= sid[1:, :] != sid[:-1, :]
img[e] = 0
# legend: blocks at left top
for i, p in enumerate(passes):
    img[10 + i * 22: 28 + i * 22, 5:40] = pal[i % len(pal)]
write_png(stem + "_pass.png", img)
yy, xx = np.mgrid[:H, :H]
for i, p in enumerate(passes):
    m = pm == i
    n = int(m.sum())
    if n:
        print(f"{i:2d} {p:5s} col={pal[i%len(pal)]} px={n:7d} centroid=({xx[m].mean():.0f},{yy[m].mean():.0f})  stretches={sum(1 for k,q in kp.items() if q==p and (sid==k).any())}")
