"""wd_cutdiag - where the cuts are and what makes them (build from a design json)."""
import json
import sys

import numpy as np

sys.path.insert(0, ".")
import wd_score as SC  # noqa: E402
from props_lib import smokebomb_wind as W  # noqa: E402


def load(tag):
    rec = json.load(open(SC.OUT + f"/{tag}_design.json"))
    return rec


def diag(wd, views=("front", "back", "left", "right", "top", "bottom"), size=627, rmax=0.93):
    names = wd.names
    out = []
    for vw in views:
        lab = W.render_labels(wd, vw, size)
        cm = SC.cut_map(wd, lab)
        yy, xx = np.mgrid[0:size, 0:size]
        r = np.hypot(xx + 0.5 - lab["cx"], yy + 0.5 - lab["cy"]) / lab["R"]
        cm &= r < rmax
        s = lab["sample"]
        ys, xs = np.nonzero(cm)
        groups = {}
        for y, x in zip(ys, xs):
            a = s[y, x]
            nb = [s[yy_, xx_] for yy_, xx_ in ((y, x + 1), (y + 1, x), (y, x - 1), (y - 1, x))
                  if 0 <= yy_ < size and 0 <= xx_ < size and s[yy_, xx_] >= 0 and abs(int(s[yy_, xx_]) - int(a)) > 30]
            for b in nb:
                pa, pb = names[wd.pass_idx[a]], names[wd.pass_idx[b]]
                ta = int(any(i0 <= a <= i1 for i0, i1 in wd.weave_lo))
                tb = int(any(i0 <= b <= i1 for i0, i1 in wd.weave_lo))
                key = (pa, "arc" if not np.isnan(wd.phi[a]) else "conn", ta, pb, "arc" if not np.isnan(wd.phi[b]) else "conn", tb)
                groups.setdefault(key, []).append((x, y))
        for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if len(v) < 3:
                continue
            v = np.array(v)
            out.append((vw, len(v), k, tuple(np.round(v.mean(0)).astype(int))))
    return out
