import sys, os, json
sys.argv = [sys.argv[0]] + ["--"]  # silence
OUT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(OUT, "measure.py")).read()
src = src[:src.index("# ---------------- vertices & edges")]
exec(compile(src, "measure_head", "exec"))
ej = json.load(open(os.path.join(OUT, "edges_outer.json")))
want = [("N_NW-T_NNW", 0.5), ("N_NW-T_NNW", 0.8), ("N_NW-T_WNW", 0.5), ("N_S-T_SSE", 0.7)]
for name, t in want:
    e = [e for e in ej["edges"] if e["name"] == name][0]
    r = min(e["rows"], key=lambda r: abs(r["t"] - t))
    n = np.array(e["n"])
    P = np.array([r["x"], r["y"]]) - r["s_edge"] * n
    v, b, wv = sample(P, n)
    ps = conv(v, g); ws = conv(wv, g); ps2 = conv(v, g2)
    print(name, "t=%.3f" % r["t"], {k: (round(val, 2) if isinstance(val, float) else val) for k, val in r.items() if k not in ("x", "y", "t")}, "bgref %.3f" % b[-1])
    for i in range(0, len(S), 4):
        print("   s %6.1f  ps %.3f  ps2 %.3f  warm %+.3f" % (S[i], ps[i], ps2[i], ws[i]))
