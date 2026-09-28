"""r3 zoom probe: reference (nearest) | traced outline on reference | our BC at the same mm.
usage: r3_zoom.py <bc: shipped|path.npy(linear)> <tag> [names]"""
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
OUT = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1]; tag = sys.argv[2]
traced = sys.argv[4] if len(sys.argv) > 4 else PT.TRACED_JSON
if src == "shipped":
    a, _ = xt_io.read(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
    bc = a[:plan.raster[1], :plan.raster[0], :3]
else:
    bc = T.linear_to_srgb(np.load(src))
S = T.read_source(); fit = T.fit_card(S)
data = PT.load_traced(traced)
CROPS = {"sealTL16": (40, 64, 494, 520, 16), "sealBR16": (86, 108, 580, 598, 16),
         "cTL": (20, 60, 24, 62, 12), "cBL": (20, 60, 592, 636, 12), "cBR": (244, 284, 592, 636, 12),
         "cTR": (244, 284, 24, 62, 12), "knob": (22, 42, 36, 52, 24)}


def samp(img, u, v):
    H, W = img.shape[:2]
    u = np.clip(u, 0, W - 1.000001); v = np.clip(v, 0, H - 1.000001)
    j = np.floor(u).astype(int); i = np.floor(v).astype(int)
    fu = (u - j)[..., None]; fv = (v - i)[..., None]
    return ((img[i, j] * (1 - fu) + img[i, j + 1] * fu) * (1 - fv) + (img[i + 1, j] * (1 - fu) + img[i + 1, j + 1] * fu) * fv)


only = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else list(CROPS)
for name in only:
    x0, x1, y0, y1, F = CROPS[name]
    nx, ny = (x1 - x0) * F, (y1 - y0) * F
    px, py = np.meshgrid(x0 + (np.arange(nx) + 0.5) / F, y0 + (np.arange(ny) + 0.5) / F)
    ref = S.rgb[np.clip(py.astype(int), 0, S.H - 1), np.clip(px.astype(int), 0, S.W - 1)]
    xm, ym = fit.px_to_mm(px, py)
    ours = samp(bc, (xm + pad) * ppmm - 0.5, (ym + pad) * ppmm - 0.5)
    # traced outline: rasterise each layer's polygons at the zoom grid, draw its edge
    ov = ref.copy()
    for layer, col in (("red", (0.0, 0.8, 1.0)), ("black", (0.1, 1.0, 0.2))):
        polys, er, soft, ink = [], [], [], []
        for g in data["groups"]:
            if g["layer"] != layer:
                continue
            polys += PT.group_polys_mm(g, 0.01)
            er += PT.knockout_polys_mm(g)
            soft += PT.soft_knockouts_mm(g) if hasattr(PT, "soft_knockouts_mm") else []
            ink += PT.ink_polys_mm(g) if hasattr(PT, "ink_polys_mm") else []
        def topx(p):
            u, v = fit.mm_to_px(p[:, 0], p[:, 1])
            return np.stack([(u - x0) * F, (v - y0) * F], 1)
        m = PT.compose_coverage(lambda ps: T.fill_polys([topx(p) for p in ps], ny, nx, ss=2),
                                polys, er, soft, ink, blur_scale=F)
        b = m > 0.5
        e = b ^ T.erode(b, 1)
        ov[e] = col
        if layer == "red":
            fillp = np.repeat((1 - m)[..., None], 3, -1)
    sep = np.ones((ny, 6, 3)) * 0.5
    xt_io.write(os.path.join(OUT, "z_%s_%s.png" % (tag, name)), np.concatenate([ref, sep, ov, sep, fillp, sep, ours], 1))
print("ok")
