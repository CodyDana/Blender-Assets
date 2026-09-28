# Method B segmentation: Otsu on luminance + Otsu on saturation, background flood-filled from the image
# border (outside) and hole = largest enclosed background component. Writes mask + npz.
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = np.load(os.path.join(OUT, "roppo_rgb.npy"))
H, W, _ = a.shape
L, S = features(a)
Ls = gauss_blur(L, 0.8); Ss = gauss_blur(S, 0.8)
tL = otsu(Ls)
# saturation threshold: Otsu restricted to pixels that are not clearly dark face / clearly background by L alone
tS = otsu(Ss, rng=(0, 1))
fg = (Ls < tL) | ((Ss > tS) & (Ls < 0.75))
bg = ~fg
lab, n, sizes = label(bg, 4)
border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]).tolist()) - {0}
outside = np.isin(lab, list(border))
inner = [(sizes[i], i) for i in range(1, n + 1) if i not in border]
inner.sort(reverse=True)
hole_id = inner[0][1]
hole = lab == hole_id
piece = ~outside & ~hole
# keep the largest 8-connected foreground component (drops specks outside)
plab, pn, psz = label(piece, 8)
k = int(np.argmax(psz[1:])) + 1
piece = plab == k
# re-derive the hole as enclosed non-piece region connected to the hole seed
info = dict(tL=tL, tS=tS, n_bg_components=n, border_components=len(border),
            hole_px=int(hole.sum()), next_inner_bg_sizes=[s for s, _ in inner[1:8]],
            piece_px=int(piece.sum()), n_piece_components_8=pn, piece_component_sizes_top=sorted(psz[1:], reverse=True)[:5],
            touches_bottom=int(piece[-1].sum()), touches_top=int(piece[0].sum()), touches_left=int(piece[:, 0].sum()), touches_right=int(piece[:, -1].sum()))
print(json.dumps(info, indent=1))
np.savez_compressed(os.path.join(OUT, "seg.npz"), piece=piece, hole=hole, L=L, S=S)
write_png(os.path.join(OUT, "roppo_mask.png"), np.where(piece, 1.0, np.where(hole, 0.5, 0.0)))
json.dump(info, open(os.path.join(OUT, "seg_info.json"), "w"), indent=1)
