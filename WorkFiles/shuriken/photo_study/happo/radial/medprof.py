import sys, os, json
OUT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(OUT, "measure.py")).read()
src = src[:src.index("# ---------------- vertices & edges")]
exec(compile(src, "measure_head", "exec"))
ej = json.load(open(os.path.join(OUT, "edges_outer.json")))
sel = np.arange(-14, 21, 2)
print("median lum profile across stations t in [0.3,0.7], profiles positioned on the FITTED line (s=0 on line)")
print("%-12s %5s %5s " % ("edge", "nx", "ny") + " ".join("%5d" % s_ for s_ in sel))
for e in ej["edges"]:
    c = np.array(e["fit"]["c"]); d = np.array(e["fit"]["d"]); n = np.array(e["n"])
    nn = np.array([-d[1], d[0]]); nn = nn if np.dot(nn, n) > 0 else -nn
    A = np.array(e["rows"][0]["x"]), np.array(e["rows"][0]["y"])
    profs = []; warms = []
    for t in np.linspace(0.3, 0.7, 40):
        # point on the fitted line at fraction t along the edge (project station)
        r = min(e["rows"], key=lambda r: abs(r["t"] - t))
        p = np.array([r["x"], r["y"]]); p = c + np.dot(p - c, d) * d
        v, b, wv = sample(p, nn)
        profs.append(conv(v, g)); warms.append(conv(wv, g))
    mp = np.median(profs, 0); mw = np.median(warms, 0)
    idx = [np.argmin(np.abs(S - s_)) for s_ in sel]
    print("%-12s %+5.2f %+5.2f " % (e["name"][:12], nn[0], nn[1]) + " ".join("%5.2f" % mp[i] for i in idx))
    print("%-12s %5s %5s " % ("   warm", "", "") + " ".join("%5.2f" % mw[i] for i in idx))
