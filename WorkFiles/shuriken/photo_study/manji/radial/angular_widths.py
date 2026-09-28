"""Angular extent of each point (hook) at several radii, from r(theta)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
rth = np.load(os.path.join(C.OUT, "r_theta.npy"))
R1 = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
TH, r_out = rth[:, 0], rth[:, 1]
SPAN = R1["SPAN_px"]
res = {}
for frac in (0.25, 0.30, 0.35, 0.40, 0.45, 0.48):
    lvl = frac * SPAN
    m = r_out >= lvl
    d = np.diff(np.concatenate([[m[-1]], m]).astype(np.int8))
    starts = np.nonzero(d == 1)[0]; ends = np.nonzero(d == -1)[0]
    if len(starts) and len(ends):
        if ends[0] < starts[0]:
            ends = np.roll(ends, -1)
        widths = [(TH[e - 1] - TH[s]) % 360 + 0.1 for s, e in zip(starts, ends)]
    else:
        widths = []
    res["%.2f" % frac] = dict(level_px=lvl, n_lobes=len(widths), widths_deg=[round(x, 2) for x in widths],
                              mean=round(float(np.mean(widths)), 2) if widths else None,
                              sd=round(float(np.std(widths, ddof=1)), 3) if len(widths) > 1 else None)
    print("r/span %.2f (%.0f px): %d lobes, angular widths %s deg" % (frac, lvl, len(widths), [round(x, 2) for x in widths]))
json.dump(res, open(os.path.join(C.OUT, "angular_widths.json"), "w"), indent=1)
