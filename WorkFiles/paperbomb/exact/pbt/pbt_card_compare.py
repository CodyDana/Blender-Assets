"""Whole card, traced vs reference at Fx: reference (Catmull-Rom) | traced (black + red over the
reference's own local paper colour) | overlay (traced-only ink magenta, reference-only green).
usage: python pbt_card_compare.py traced.json tag [F] [x0 y0 x1 y1]"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props"); sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
import xt_io

data = json.load(open(sys.argv[1], encoding="utf-8")); tag = sys.argv[2]
F = int(sys.argv[3]) if len(sys.argv) > 3 else 4
L = PT.load_layers(); fit = L.fit
H, W = L.black.shape
x0, y0, x1, y1 = [int(v) for v in sys.argv[4:8]] if len(sys.argv) > 7 else (0, 0, W, H)


def to_px(poly_mm):
    x, y = fit.mm_to_px(poly_mm[:, 0], poly_mm[:, 1])
    return np.stack([x, y], 1)


cov = {}
col = {}
for layer in ("black", "red"):
    polys = []
    for g in data["groups"]:
        if g["layer"] == layer:
            polys += [to_px(p) for p in PT.group_polys_mm(g, step_mm=0.005)]
    cov[layer] = T.fill_polys([(p - [x0, y0]) * F for p in polys], (y1 - y0) * F, (x1 - x0) * F, ss=4).astype(np.float64)
ink_k = np.array([0.0314, 0.0353, 0.0275])
reds = [g["colour"]["median_srgb"] for g in data["groups"] if g["layer"] == "red" and g.get("colour")]
ink_r = np.median(np.array(reds), 0)
ref = np.clip(np.stack([T.upsample_window(L.src.rgb[..., c], x0, y0, x1, y1, F, "catmull")[0] for c in range(3)], -1), 0, 1)
paper = np.stack([T.upsample_window(L.unm_paper[..., c] if hasattr(L, "unm_paper") else L.src.rgb[..., c], x0, y0, x1, y1, F, "linear")[0] for c in range(3)], -1)
# paper colour: local paper estimate from the unmixing
from props_lib.trace import unmix, ink_layers
ak, behind, unm = T.ink_layers(L.src, fit)
paper = np.clip(np.stack([T.upsample_window(unm.paper[..., c], x0, y0, x1, y1, F, "linear")[0] for c in range(3)], -1), 0, 1)
lin = T.srgb_to_linear
img = lin(paper)
img = img * (1 - cov["red"][..., None]) + lin(ink_r)[None, None] * cov["red"][..., None]
img = img * (1 - cov["black"][..., None]) + lin(ink_k)[None, None] * cov["black"][..., None]
traced = T.linear_to_srgb(img)
ob = {}
for layer, fld in (("black", L.black), ("red", L.red)):
    ob[layer] = T.upsample_window(np.where(L.inside, fld / L.density[layer], 0), x0, y0, x1, y1, F, "bspline")[0] > 0.5
grey = np.repeat(ref.mean(-1, keepdims=True) * 0.5 + 0.5, 3, -1)
tb = (cov["black"] > 0.5) | (cov["red"] > 0.5)
obb = ob["black"] | ob["red"]
grey[tb & ~obb] = [0.85, 0.1, 0.85]
grey[obb & ~tb] = [0.1, 0.7, 0.2]
sep = np.ones((ref.shape[0], 6, 3))
out = os.path.join(os.path.dirname(HERE), "pb_card_compare_%s_x%d.png" % (tag, F))
xt_io.write(out, np.concatenate([ref, sep, traced, sep, grey], 1))
print("wrote", out)
