# Preview sheet of a fabric map set: full tile (BC stretched, N, ORM rough), a 1:1 crop, and a 2x2 tiling (seams).
# args: <maps_dir> <out_png>
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import sv2_imgmetrics as M

d, out = sys.argv[sys.argv.index("--") + 1:][:2]
bc = M.load(d + "/T_BlackCloakV2_Cloth_BC.png")
nm = M.load(d + "/T_BlackCloakV2_Cloth_N.png")
orm = M.load(d + "/T_BlackCloakV2_Cloth_ORM.png")
L = M.lum(bc)
lo, hi = np.percentile(L, [0.5, 99.5])
st = np.clip((L - lo) / (hi - lo), 0, 1) * 255


def down(a, f):
    h, w = a.shape[:2]
    return a[:h // f * f, :w // f * f].reshape(h // f, f, w // f, f, *a.shape[2:]).mean((1, 3))


row1 = [down(st, 4), down(nm, 4), down(orm[..., 1] * 1.0, 4)]
row1 = [np.stack([r] * 3, -1) if r.ndim == 2 else r for r in row1]
crop = st[0:512, 0:512]
tile2 = down(np.tile(st, (2, 2)), 8)
row2 = [np.stack([crop] * 3, -1), np.stack([tile2] * 3, -1), nm[0:512, 0:512]]
sheet = np.concatenate([np.concatenate(row1, 1), np.concatenate(row2, 1)], 0)
M.save(out, sheet)
# also an unstretched 'true value' swatch at display gamma (what the texture looks like as stored)
M.save(out.replace(".png", "_asstored_x4gain.png"), np.clip(down(bc, 2) * 4, 0, 255))
print("wrote", out)
