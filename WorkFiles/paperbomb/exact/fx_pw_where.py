# final pass: where is the paper weight above 1.1 (which texels set the Paper Colour Limit's p99.9)?
import sys, json
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials/maps")
import numpy as np, recolour_common as rc
T = rc.EXPORTS / "PaperBomb" / "Textures" / "Recolour"
P = json.load(open(T / "recolour_maps.json", encoding="utf-8"))["parts"]["Tag"]["params"]
pd8, _, _ = rc.png_read(T / "T_PaperBomb_PaperDetail.png")
iw8, _, _ = rc.png_read(T / "T_PaperBomb_InkWeights.png")
w = rc.s2l(pd8[..., :3] / 255.0) * P["Paper Weight Scale"]
m = w.max(-1)
print("p99.9", np.percentile(m, 99.9), "p99", np.percentile(m, 99), "p99.99", np.percentile(m, 99.99))
hi = m > 1.12
ys, xs = np.nonzero(hi)
print("n>1.12", hi.sum(), "argmax channel counts", np.bincount(w[hi].argmax(-1), minlength=3))
print("ink weights there: red mean %.3f black mean %.3f" % (iw8[hi][:, 2].mean() / 255, iw8[hi][:, 0].mean() / 255))
H = np.histogram2d(ys, xs, bins=[16, 16], range=[[0, 2048], [0, 2048]])[0].astype(int)
print(H)
old = rc.png_read("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/regression/post_paper_bomb/recolour/T_PaperBomb_PaperDetail.png")[0] if False else None
