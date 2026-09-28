import pickle, sys, numpy as np
sys.path.insert(0, ".")
import wd_build as B, wd_score as SC
from props_lib import smokebomb_wind as W
wd = pickle.load(open(SC.OUT + "/c7_wd.pkl", "rb"))
k_last = len(wd.passes) - 1
print("last pass", wd.names[k_last], "tail max", np.nanmax(wd.tail[wd.pass_idx == k_last]))
tail = np.nonzero((wd.pass_idx == k_last) & ~np.isnan(wd.tail))[0]
zc = wd.c[tail, 2] + np.sin(0.5 * wd.w_eff()[tail])
print("tail samples", len(tail), "z of centre along tail:", np.round(wd.c[tail[::40], 2], 2))
print("zc>-0.02 first:", np.nonzero(zc > -0.02)[0][:5])
