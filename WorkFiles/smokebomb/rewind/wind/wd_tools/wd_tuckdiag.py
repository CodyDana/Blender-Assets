import pickle, sys
import numpy as np
sys.path.insert(0, ".")
import wd_fitlib as FL, wd_passes as TP, wd_score as SC
from props_lib import smokebomb_wind as W
wd = pickle.load(open(SC.OUT + "/" + sys.argv[1] + "_wd.pkl", "rb"))
probes = TP.band_probes()
names = wd.names
for t, (tk, (i0, i1)) in enumerate(zip(wd.tucks, wd.tuck_range)):
    k = names.index(tk.pass_name)
    ps = wd.passes[k]
    bad = tot = 0
    own = np.nonzero(wd.pass_idx == k)[0]
    for band in ps.shows:
        if band not in probes:
            continue
        Pc = FL.px2cam(probes[band])
        j = own[np.argmax(Pc @ wd.c[own].T, axis=1)]
        bad += int(((j >= i0) & (j <= i1)).sum()); tot += len(Pc)
    print(f"{tk.pass_name:5s} under {','.join(tk.under)[:30]:30s} phi {wd.phi[i0]:7.1f}..{wd.phi[i1]:7.1f} tail {wd.tail[i0]:5.0f}..{wd.tail[i1]:5.0f} len {(i1-i0)*0.2:6.1f}deg own-visible {bad}/{tot}" + ("  <--" if bad else ""))
