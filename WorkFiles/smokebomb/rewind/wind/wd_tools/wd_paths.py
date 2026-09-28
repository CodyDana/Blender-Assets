"""draw chosen passes' centre lines and edges (front arc + connector) over the front render."""
import pickle, sys, os
import numpy as np
sys.path.insert(0, ".")
import wd_run as RR, wd_score as SC
from wd_png import write_png
from props_lib import smokebomb_wind as W
tag = sys.argv[1]; which = sys.argv[2].split(",")
wd = pickle.load(open(SC.OUT + f"/{tag}_wd.pkl", "rb"))
names = wd.names
size = 1254
lab = W.render_labels(wd, "front", size)
img = RR.colour_labels(lab, names) * 0.55 + 0.45
RR.spec_edges_overlay(img, 1.0, (0, 0, 0))
for nm in which:
    k = names.index(nm)
    col = RR.pass_colour(k, names)
    idx = np.nonzero(wd.pass_idx == k)[0]
    for side, rad in ((0, 1), (1, 0), (-1, 0)):
        P = wd.c[idx] if side == 0 else wd.edge(side, idx)
        front = P[:, 2] > 0
        xy = W.cam_to_img(P[front])
        for x, y in xy[::2]:
            xi, yi = int(x), int(y)
            if 0 <= xi < size and 0 <= yi < size:
                img[max(0, yi - rad):yi + rad + 1, max(0, xi - rad):xi + rad + 1] = col * 0.6 if side else [0, 0, 0]
x0, y0, x1, y1 = (0, 0, size, size) if len(sys.argv) < 7 else tuple(map(int, sys.argv[3:7]))
write_png(os.path.join(SC.OUT, f"{tag}_paths_{'_'.join(which)}.png"), img[y0:y1, x0:x1])
