"""full-res crops of a saved winding's front render beside the reference (edges overlaid)."""
import pickle, sys, os
import numpy as np
sys.path.insert(0, ".")
import wd_run as RR, wd_score as SC
from wd_png import write_png
from props_lib import smokebomb_wind as W
tag = sys.argv[1]
wd = pickle.load(open(SC.OUT + f"/{tag}_wd.pkl", "rb"))
names = wd.names
lab = W.render_labels(wd, "front", 1254)
img = RR.colour_labels(lab, names)
RR.spec_edges_overlay(img, 1.0, (1, 1, 1))
ref = np.clip(RR.REF[:, :, :3], 0, 1) ** 0.55
ov = RR.edges_overlay(ref, lab, names)
cm = SC.cut_map(wd, lab)
img[cm] = [1, 0, 0]
regions = dict(bottom=(170, 780, 1100, 1110), upper=(380, 130, 1010, 600), left=(150, 250, 560, 950), right=(800, 330, 1100, 900))
if len(sys.argv) > 2:
    x0, y0, x1, y1 = map(int, sys.argv[2:6]); regions = {"custom": (x0, y0, x1, y1)}
for rn, (x0, y0, x1, y1) in regions.items():
    write_png(os.path.join(SC.OUT, f"{tag}_crop_{rn}.png"), np.concatenate([ov[y0:y1, x0:x1], img[y0:y1, x0:x1]], 1))
# legend: pass -> colour
leg = np.ones((22 * len(names), 200, 3))
for k, n in enumerate(names):
    leg[22 * k:22 * k + 18, :40] = RR.pass_colour(k, names)
write_png(os.path.join(SC.OUT, f"{tag}_legend.png"), leg)
print({k: n for k, n in enumerate(names)})
