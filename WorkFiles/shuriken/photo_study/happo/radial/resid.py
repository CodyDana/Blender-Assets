import os, json, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
import sys
fn = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "edges_outer.json"
ej = json.load(open(os.path.join(OUT, fn)))
bins = np.arange(0.0, 1.0001, 0.05)
print("residual (px, + = outward/toward lid) vs t (0 = notch, 1 = tip); columns are t-bin centres")
print("%-14s" % "edge" + "".join("%6.2f" % (b + 0.025) for b in bins[:-1]))
for e in ej["edges"]:
    c = np.array(e["fit"]["c"]); d = np.array(e["fit"]["d"]); n = np.array(e["n"])
    nn = np.array([-d[1], d[0]])
    if np.dot(nn, n) < 0: nn = -nn
    t = np.array([r["t"] for r in e["rows"]]); P = np.array([[r["x"], r["y"]] for r in e["rows"]])
    res = (P - c) @ nn
    line = "%-14s" % e["name"]
    for b0, b1 in zip(bins[:-1], bins[1:]):
        m = (t >= b0) & (t < b1)
        line += "%6.1f" % np.median(res[m]) if m.any() else "   nan"
    print(line)
print()
print("dark-band width (px) median per t-bin")
for e in ej["edges"]:
    t = np.array([r["t"] for r in e["rows"]]); v = np.array([r["dark_band"] for r in e["rows"]])
    line = "%-14s" % e["name"]
    for b0, b1 in zip(bins[:-1], bins[1:]):
        m = (t >= b0) & (t < b1)
        line += "%6.1f" % np.median(v[m]) if m.any() else "   nan"
    print(line)
print()
print("bright bevel width (px) median per t-bin (nan = no dark face in profile)")
for e in ej["edges"]:
    t = np.array([r["t"] for r in e["rows"]]); v = np.array([r["bevel_w"] for r in e["rows"]])
    line = "%-14s" % e["name"]
    for b0, b1 in zip(bins[:-1], bins[1:]):
        m = (t >= b0) & (t < b1)
        line += "%6.1f" % np.nanmedian(v[m]) if m.any() and np.isfinite(v[m]).any() else "   nan"
    print(line)
