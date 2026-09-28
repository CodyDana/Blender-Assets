# final pass: where does the default recomposition of the recolour maps miss the shipped BC by > 1 level?
import sys, json
from pathlib import Path
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials/maps")
import numpy as np
import recolour_common as rc
T = rc.EXPORTS / "PaperBomb" / "Textures"
d = json.load(open(T / "Recolour" / "recolour_maps.json", encoding="utf-8"))
P = d["parts"]["Tag"]["params"]
pd = rc.load_levels8(T / "Recolour" / "T_PaperBomb_PaperDetail.png").astype(np.float64)
iw = rc.load_levels8(T / "Recolour" / "T_PaperBomb_InkWeights.png").astype(np.float64)
bc = rc.load_levels8(T / "T_PaperBomb_BC.png")[..., :3].astype(np.int16)
paper = np.array(P["Paper Colour"][:3]); black = np.array(P["Black Ink Colour"][:3]); red = np.array(P["Red Ink Colour"][:3])
scale = P["Paper Weight Scale"]
w = np.concatenate([iw / 255.0, pd[..., 3:4] / 255.0], -1)
wp = rc.s2l(pd[..., :3] / 255.0) * scale
# dry / pool weights are zero
out = np.minimum(paper * wp + w[..., 0:1] * black + w[..., 2:3] * red, P["Albedo Ceiling"])
q = rc.q8_srgb(out).astype(np.int16)
diff = np.abs(q - bc).max(-1)
ys, xs = np.nonzero(diff > 1)
print("n>1", len(ys), "max", diff.max())
bl = rc.s2l(bc / 255.0)
for y, x in list(zip(ys, xs))[:15]:
    print(y, x, "bc", bc[y, x].tolist(), "rec", q[y, x].tolist(), "Wb %.3f Wr %.3f" % (w[y, x, 0], w[y, x, 2]),
          "pd", pd[y, x, :3].astype(int).tolist(), "bc_lin", np.round(bl[y, x], 5).tolist(),
          "ink", np.round(w[y, x, 0] * black + w[y, x, 2] * red, 5).tolist())
print("rows", ys.min() if len(ys) else None, ys.max() if len(ys) else None, "cols", xs.min() if len(xs) else None, xs.max() if len(xs) else None)
