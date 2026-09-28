"""crops of a BC preview vs reference at the same card-mm window, both magnified to the same px/mm.
usage: r1_crops.py bc.npy tag x0 y0 x1 y1 [out_ppmm]"""
import os, sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T
import xt_io
bc = np.load(sys.argv[1]); tag = sys.argv[2]
x0, y0, x1, y1 = [float(v) for v in sys.argv[3:7]]
op = float(sys.argv[7]) if len(sys.argv) > 7 else 31.3
src = T.read_source(); fit = T.fit_card(src)
Ht, Wt = bc.shape[:2]; tp = Wt / (70.0 + 3.2)
nx = int((x1 - x0) * op); ny = int((y1 - y0) * op)
xs = x0 + (np.arange(nx) + 0.5) / op; ys = y0 + (np.arange(ny) + 0.5) / op
xm, ym = np.meshgrid(xs, ys)
# reference: catmull-rom of stored
px, py = fit.mm_to_px(xm, ym)
def samp(img, u, v):
    H, W = img.shape[:2]
    u = np.clip(u, 0, W - 1.000001); v = np.clip(v, 0, H - 1.000001)
    j = np.floor(u).astype(int); i = np.floor(v).astype(int); fu = (u - j)[..., None]; fv = (v - i)[..., None]
    return (img[i, j] * (1 - fu) + img[i, j + 1] * fu) * (1 - fv) + (img[i + 1, j] * (1 - fu) + img[i + 1, j + 1] * fu) * fv
ref = samp(src.rgb, px - 0.5, py - 0.5)
ours = samp(T.linear_to_srgb(bc), (xm + 1.6) * tp - 0.5, (ym + 1.6) * tp - 0.5)
sep = np.ones((ny, 6, 3))
xt_io.write(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crop_%s.png" % tag), np.concatenate([ref, sep, ours], 1))
