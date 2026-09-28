"""zoom crops: reference (nearest) | ours (BC, bilinear) at the same mm scale.  usage: r2_zoom.py <bc.npy|shipped> <tag>"""
import os, sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
from props_lib import atlas as AT
from props_lib.spec import PAPER_BOMB
import xt_io
plan = AT.plan_for(PAPER_BOMB); ppmm, pad = plan.ppmm, plan.pad_mm
src = sys.argv[1]; tag = sys.argv[2]
if src == "shipped":
    a, _ = xt_io.read(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
    bc = a[:plan.raster[1], :plan.raster[0], :3]
else:
    bc = T.linear_to_srgb(np.load(src))
S = T.read_source(); fit = T.fit_card(S)
def samp(img, u, v):
    H, W = img.shape[:2]
    u = np.clip(u, 0, W - 1.000001); v = np.clip(v, 0, H - 1.000001)
    j = np.floor(u).astype(int); i = np.floor(v).astype(int)
    fu = (u - j)[..., None]; fv = (v - i)[..., None]
    return ((img[i, j] * (1 - fu) + img[i, j + 1] * fu) * (1 - fv) + (img[i + 1, j] * (1 - fu) + img[i + 1, j + 1] * fu) * fv)
CROPS = {"sealTL": (6.8, 123.5, 12.8, 130.5), "sealBR": (17.8, 143.3, 23.8, 149.3), "dou": (57.8, 144.5, 62.4, 150.9),
         "ruleTop": (24.0, 5.0, 48.0, 8.2), "cTL": (0.5, 5.0, 8.5, 12.5), "sealbig": (5.0, 121.8, 24.6, 150.6),
         "emblem": (21.5, 18.5, 48.5, 43.6)}
only = sys.argv[3].split(",") if len(sys.argv) > 3 else list(CROPS)
for name in only:
    x0, y0, x1, y1 = CROPS[name]
    F = 64.0 if (x1 - x0) < 10 else 24.0
    nx = int((x1 - x0) * F); ny = int((y1 - y0) * F)
    xm, ym = np.meshgrid(x0 + (np.arange(nx) + 0.5) / F, y0 + (np.arange(ny) + 0.5) / F)
    px, py = fit.mm_to_px(xm, ym)
    ref = S.rgb[np.clip(py.astype(int), 0, S.H - 1), np.clip(px.astype(int), 0, S.W - 1)]
    ours = samp(bc, (xm + pad) * ppmm - 0.5, (ym + pad) * ppmm - 0.5)
    sep = np.ones((ny, 6, 3)) * 0.5
    xt_io.write("zoom_%s_%s.png" % (tag, name), np.concatenate([ref, sep, ours], 1))
print("ok")
