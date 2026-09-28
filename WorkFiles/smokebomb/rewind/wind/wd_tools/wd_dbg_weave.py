import pickle, sys, json
import numpy as np
sys.path.insert(0, ".")
import wd_fitlib as FL, wd_passes as TP, wd_score as SC
from props_lib import smokebomb_wind as W
wd = pickle.load(open(SC.OUT + "/" + sys.argv[1] + "_wd.pkl", "rb"))
rec = json.load(open(SC.OUT + "/" + sys.argv[1] + "_design.json"))
print("order", rec["order"])
names = wd.names
probes = TP.band_probes()
for wi, w in enumerate(wd.weaves):
    lo = wd.weave_lo[wi]; hi = wd.weave_hi[wi]
    up = wd.weave_upkey[wi]
    print(wi, w.lower, w.lower_range, "->", w.upper, "lo samples", lo, "phi", wd.phi[lo[0]], wd.phi[lo[1]], "hi", hi, "upkey finite cells", int(np.isfinite(up).sum()))
    if wi > 40: break
# at U2 probes: which stretches cover, keys, effective keys
P = FL.px2cam(probes["U2"][:5])
g = wd.stack_grid(256)
ci = W._cube_index(P, 256)
for n, c in enumerate(ci):
    S = g.samples[c]; K = g.keys[c]
    ok = S >= 0
    print("probe", n, [(names[wd.pass_idx[s]], round(k, 2)) for s, k in zip(S[ok], K[ok])])
