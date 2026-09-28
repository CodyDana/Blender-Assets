"""Stage 3 (v3, final outline rule): 'outermost sharp step to a plateau', made
consistent along each edge by two line-fit passes.

For each profile along the outward edge normal (0.25 px steps, Gaussian smoothed 0.75 px):
  candidate steps = local maxima of the outward slope with
      slope >= 0.05 /px, rise over +-2 px >= 0.07, and a PLATEAU after it
      (max of profile 3..12 px further out exceeds the post-step value by <= 0.06).
  A lid shadow is a long soft ramp, so it yields no candidate; the outer edge of a lit
  ground bevel (bevel -> lid step) and the outer edge of a dark shaded facet both do.
  Fallback when no candidate: the lum 0.30 crossing (outer edge of the dark core).
Pass 1 uses the outermost candidate, pass 2/3 the candidate nearest the fitted line, so
one definition is used along the whole edge (no flip-flopping between bevel and face).
Outputs geom.json + edges_v3.json in the same shape the later stages expect.
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(OUT, "measure2.py")).read()
exec(compile(src[:src.index("compass = [")], "m2head", "exec"))   # helpers: sample, conv, robust_line, ...

co = json.load(open(os.path.join(OUT, "coarse_mask_filled.json")))
C0 = np.array(co["centroid"])
compass = ["E", "ENE", "NE", "NNE", "N", "NNW", "NW", "WNW", "W", "WSW", "SW", "SSW", "S", "SSE", "SE", "ESE"]
def comp(th):
    return compass[int(((th % 360) + 11.25) // 22.5) % 16]

verts = [("tip", t["theta"] % 360, np.array([t["x"], t["y"]])) for t in co["tips"]] + \
        [("notch", t["theta"] % 360, np.array([t["x"], t["y"]])) for t in co["notches"]]
verts.sort(key=lambda v: v[1])
while verts[0][0] != "notch":
    verts = verts[1:] + verts[:1]
V = [dict(kind=k, theta=th, P=P, name=("T" if k == "tip" else "N") + "_" + comp(th)) for k, th, P in verts]
nV = len(V)


def candidates(P, n):
    v, b = sample(P, n)
    ps = conv(v, g); ps2 = conv(v, g2)
    bgref = float(b[-1])
    i0 = int(np.searchsorted(S, -22))
    d = np.gradient(ps, DS)
    n2 = int(2 / DS); n3 = int(3 / DS); n12 = int(12 / DS)
    cands = []
    for i in range(i0, len(S) - n12):
        if not (d[i] >= 0.05 and d[i] >= d[i - 1] and d[i] > d[i + 1]):
            continue
        lo = ps[max(i - n2, 0)]; hi = ps[i + n2]
        if hi - lo < 0.07:
            continue
        if ps[i + n3:i + n12].max() - hi > 0.06:    # must reach a plateau
            continue
        mid = 0.5 * (lo + hi)
        seg = ps[max(i - n2, 0):i + n2 + 1]
        k = np.flatnonzero((seg[:-1] < mid) & (seg[1:] >= mid))
        s = S[max(i - n2, 0) + k[-1]] + DS * 0 if len(k) else S[i]
        cands.append(float(s))
    s_dark, idk = first_stay_above(ps, np.full_like(ps, 0.30), i0)
    s_clean, _ = first_stay_above(ps, b - 0.08, i0)
    face = float(np.median(ps2[:int(np.searchsorted(S, -15))]))
    band_w = 0.0
    if idk is not None:
        j = idk - 1
        lim = max(idk - int(2 / DS), 0)
        while j > lim and ps2[j] >= face - 0.04:
            j -= 1
        if ps2[j] < face - 0.04:
            k2 = j
            while k2 > 0 and ps2[k2] < face - 0.04:
                k2 -= 1
            band_w = float(s_dark - S[k2])
    return dict(cands=cands, s_dark=float(s_dark), s_clean=float(s_clean), band_w=band_w, face=face)


edges = []
for i in range(nV):
    a, b_ = V[i], V[(i + 1) % nV]
    notch, tip = (a, b_) if a["kind"] == "notch" else (b_, a)
    A = notch["P"]; B = tip["P"]
    u = (B - A) / np.linalg.norm(B - A)
    n = np.array([u[1], -u[0]])
    if np.dot(n, C0 - A) > 0:
        n = -n
    Lg = float(np.linalg.norm(B - A))
    rows = []
    for t in np.arange(0.0, 1.12 + 1e-9, 1.0 / Lg):
        P = A + t * (B - A)
        r = candidates(P, n)
        r["t"] = float(t); r["P"] = P.tolist()
        rows.append(r)
    edges.append(dict(name=notch["name"] + "-" + tip["name"], notch=notch["name"], tip=tip["name"],
                      A=A.tolist(), B=B.tolist(), u=u.tolist(), n=n.tolist(), len=Lg, rows=rows))

fits = []
for e in edges:
    n = np.array(e["n"])
    core = [r for r in e["rows"] if 0.15 <= r["t"] <= 0.85]
    # pass 1: outermost candidate within 40 px of the dark core, else the dark core
    for r in core:
        cc = [c for c in r["cands"] if np.isfinite(r["s_dark"]) and -6 <= c - r["s_dark"] <= 40]
        r["s_edge"] = max(cc) if cc else r["s_dark"]
    for it in range(4):
        pts = np.array([np.array(r["P"]) + r["s_edge"] * n for r in core if np.isfinite(r["s_edge"])])
        f = robust_line(pts)
        c, dvec = f["c"], f["d"]
        nn = np.array([-dvec[1], dvec[0]])
        if np.dot(nn, n) < 0:
            nn = -nn
        for r in core:
            pred = ((c - np.array(r["P"])) @ nn) / (n @ nn)      # s of the line at this station
            opts = [cc for cc in r["cands"] if abs(cc - pred) < 6] or \
                   ([r["s_dark"]] if np.isfinite(r["s_dark"]) and abs(r["s_dark"] - pred) < 6 else [])
            if opts:
                r["s_edge"] = min(opts, key=lambda z: abs(z - pred))
            else:
                r["s_edge"] = float("nan")
    pts = np.array([np.array(r["P"]) + r["s_edge"] * n for r in core if np.isfinite(r["s_edge"])])
    f = robust_line(pts)
    if np.dot(f["d"], np.array(e["u"])) < 0:
        f["d"] = -f["d"]
    f["n_stations"] = len(core)
    f["n_edge_found"] = int(sum(np.isfinite(r["s_edge"]) for r in core))
    fits.append(f)
    # fill s_edge for the rest of the stations (outside 0.15..0.85) using the final line
    c, dvec = f["c"], f["d"]
    nn = np.array([-dvec[1], dvec[0]])
    if np.dot(nn, n) < 0:
        nn = -nn
    for r in e["rows"]:
        if "s_edge" in r and np.isfinite(r.get("s_edge", np.nan)):
            continue
        pred = ((c - np.array(r["P"])) @ nn) / (n @ nn)
        opts = [cc for cc in r["cands"] if abs(cc - pred) < 6] or \
               ([r["s_dark"]] if np.isfinite(r["s_dark"]) and abs(r["s_dark"] - pred) < 6 else [])
        r["s_edge"] = float(min(opts, key=lambda z: abs(z - pred))) if opts else float("nan")

VX = []
for i in range(nV):
    f1, f2 = fits[(i - 1) % nV], fits[i]
    X = intersect(f1["c"], f1["d"], f2["c"], f2["d"])
    r1 = f1["d"] if np.dot(f1["d"], f1["c"] - X) > 0 else -f1["d"]
    r2 = f2["d"] if np.dot(f2["d"], f2["c"] - X) > 0 else -f2["d"]
    VX.append(dict(name=V[i]["name"], kind=V[i]["kind"], X=X, angle=ang(r1, r2),
                   edges=[edges[(i - 1) % nV]["name"], edges[i]["name"]]))

tipX = np.array([v["X"] for v in VX if v["kind"] == "tip"])
notX = np.array([v["X"] for v in VX if v["kind"] == "notch"])


def fit_circle(P):
    A = np.c_[2 * P, np.ones(len(P))]
    sol, *_ = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)
    c = sol[:2]
    return c, math.sqrt(sol[2] + c @ c), np.linalg.norm(P - c, axis=1)


c_tip, R_tip, rr_tip = fit_circle(tipX)
c_not, R_not, rr_not = fit_circle(notX)
C = 0.5 * (c_tip + c_not)
print("tip circle  (%.1f,%.1f) R %.1f sd %.1f | notch circle (%.1f,%.1f) R %.1f sd %.1f | centre (%.1f,%.1f)"
      % (c_tip[0], c_tip[1], R_tip, rr_tip.std(), c_not[0], c_not[1], R_not, rr_not.std(), C[0], C[1]))
for v in VX:
    v["theta"] = math.degrees(math.atan2(-(v["X"][1] - C[1]), v["X"][0] - C[0])) % 360
    v["r"] = float(np.linalg.norm(v["X"] - C))
    v["angle_alt"] = v["angle"]

out = dict(centre=C.tolist(), centre_tips=c_tip.tolist(), centre_notches=c_not.tolist(),
           edges=[dict(name=e["name"], rule="step", gap_lo=0.0, gap_hi=0.0, rms=f["rms"], maxdev=f["maxdev"],
                       sagitta=f["sagitta"], fit_len=f["fit_len"], n_used=f["n_used"], n_total=f["n_total"],
                       dir_deg=math.degrees(math.atan2(-f["d"][1], f["d"][0])),
                       dir_alt_deg=math.degrees(math.atan2(-f["d"][1], f["d"][0])),
                       c=f["c"].tolist(), d=f["d"].tolist(), found=f["n_edge_found"], stations=f["n_stations"])
                  for e, f in zip(edges, fits)],
           vertices=[dict(name=v["name"], kind=v["kind"], X=v["X"].tolist(), X_alt=v["X"].tolist(), angle=v["angle"],
                          angle_alt=v["angle"], theta=v["theta"], r=v["r"], edges=v["edges"]) for v in VX])
json.dump(out, open(os.path.join(OUT, "geom.json"), "w"), indent=1)
json.dump(dict(edges=edges), open(os.path.join(OUT, "edges_v3.json"), "w"), indent=0)

for e, f in zip(edges, fits):
    print("%-14s rms %.2f max %.2f sag %+.2f used %d/%d found %d/%d dir %7.2f" % (
        e["name"], f["rms"], f["maxdev"], f["sagitta"], f["n_used"], f["n_total"], f["n_edge_found"], f["n_stations"],
        math.degrees(math.atan2(-f["d"][1], f["d"][0]))))
for v in VX:
    print("%-7s %-5s X=(%7.1f,%7.1f) r %6.1f th %6.2f angle %6.2f" % (v["name"], v["kind"], v["X"][0], v["X"][1], v["r"], v["theta"], v["angle"]))
ta = np.array([v["angle"] for v in VX if v["kind"] == "tip"]); na = np.array([v["angle"] for v in VX if v["kind"] == "notch"])
tr = np.array([v["r"] for v in VX if v["kind"] == "tip"]); nr = np.array([v["r"] for v in VX if v["kind"] == "notch"])
print("tip angle %.2f +- %.2f | notch angle %.2f +- %.2f | diff %.2f" % (ta.mean(), ta.std(), na.mean(), na.std(), na.mean() - ta.mean()))
print("tip r %.1f +- %.1f | notch r %.1f +- %.1f | ratio %.4f" % (tr.mean(), tr.std(), nr.mean(), nr.std(), nr.mean() / tr.mean()))
