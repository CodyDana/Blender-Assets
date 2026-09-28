"""Stage 4 (final): outline with a per-edge rule chosen from the data, line fits,
vertices, r(theta) at 0.1 deg, notch/tip shape, bevel bands, star-polygon match.

Per-edge rule (documented choice, see cmprule.py output):
  the gap between the 'dark core' crossing (lum 0.30) and the 'clearly darker than the
  modelled lid' crossing (bg_lum - 0.08) is measured along each edge.
    * gap roughly CONSTANT along the edge  -> the gap is the soft lid shadow ramp
      (edges that face the lamp-shadow side); outline = dark-core crossing.
    * gap GROWS toward the tip (> 4 px)    -> the gap is a lit ground bevel that widens
      toward the tip; outline = bg_lum-0.08 crossing (bevel included, knife edge).
Both candidates are kept per station so the systematic spread can be reported.
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(OUT, "measure2.py")).read()
exec(compile(src[:src.index("compass = [")], "m2head", "exec"))
tex = np.load(os.path.join(OUT, "tex.npy"))
ej = json.load(open(os.path.join(OUT, "edges_v2.json")))
E = ej["edges"]
nE = len(E)

# ---------- per-edge rule ----------
for e in E:
    rows = [r for r in e["rows"] if 0.15 <= r["t"] <= 0.85]
    t = np.array([r["t"] for r in rows])
    gap = np.array([r["s_clean"] - r["s_dark"] for r in rows])
    g_lo = float(np.nanmedian(gap[t < 0.35])); g_hi = float(np.nanmedian(gap[t > 0.65]))
    e["gap_lo"], e["gap_hi"] = g_lo, g_hi
    e["rule"] = "clean" if (g_hi - g_lo) > 4.0 else "dark"


def s_of(e, r):
    return r["s_clean"] if e["rule"] == "clean" else r["s_dark"]


def pt(e, r, rule=None):
    s = (r["s_clean"] if (rule or e["rule"]) == "clean" else r["s_dark"])
    if not np.isfinite(s):
        return np.array([np.nan, np.nan])
    return np.array(r["P"]) + s * np.array(e["n"])


fits = []
for e in E:
    pts = np.array([pt(e, r) for r in e["rows"] if 0.15 <= r["t"] <= 0.85])
    f = robust_line(pts)
    if np.dot(f["d"], np.array(e["u"])) < 0:
        f["d"] = -f["d"]
    f["alt"] = robust_line(np.array([pt(e, r, "clean" if e["rule"] == "dark" else "dark")
                                     for r in e["rows"] if 0.15 <= r["t"] <= 0.85]))
    fits.append(f)

# ---------- vertices ----------
names = [v["name"] for v in ej["variants"]["outer"]["vertices"]]
kinds = [v["kind"] for v in ej["variants"]["outer"]["vertices"]]
nV = len(names)
VX = []
for i in range(nV):
    f1, f2 = fits[(i - 1) % nE], fits[i]
    X = intersect(f1["c"], f1["d"], f2["c"], f2["d"])
    r1 = f1["d"] if np.dot(f1["d"], f1["c"] - X) > 0 else -f1["d"]
    r2 = f2["d"] if np.dot(f2["d"], f2["c"] - X) > 0 else -f2["d"]
    Xa = intersect(f1["alt"]["c"], f1["alt"]["d"], f2["alt"]["c"], f2["alt"]["d"])
    VX.append(dict(name=names[i], kind=kinds[i], X=X, angle=ang(r1, r2), bis=(r1 / np.linalg.norm(r1) + r2 / np.linalg.norm(r2)),
                   X_alt=Xa, angle_alt=ang(f1["alt"]["d"] if np.dot(f1["alt"]["d"], f1["alt"]["c"] - Xa) > 0 else -f1["alt"]["d"],
                                           f2["alt"]["d"] if np.dot(f2["alt"]["d"], f2["alt"]["c"] - Xa) > 0 else -f2["alt"]["d"]),
                   edges=[E[(i - 1) % nE]["name"], E[i]["name"]]))
for v in VX:
    v["bis"] = v["bis"] / np.linalg.norm(v["bis"])   # points from the vertex INTO the piece side

# ---------- centre estimates ----------
tipX = np.array([v["X"] for v in VX if v["kind"] == "tip"])
notX = np.array([v["X"] for v in VX if v["kind"] == "notch"])


def fit_circle(P):
    A = np.c_[2 * P, np.ones(len(P))]
    b = (P ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:2]
    r = math.sqrt(sol[2] + c @ c)
    return c, r, np.linalg.norm(P - c, axis=1)


c_tip, r_tip_fit, rr_tip = fit_circle(tipX)
c_not, r_not_fit, rr_not = fit_circle(notX)
C = 0.5 * (c_tip + c_not)
print("circle centre through 8 tips  : (%.1f, %.1f) R %.1f  spread %.1f" % (c_tip[0], c_tip[1], r_tip_fit, rr_tip.std()))
print("circle centre through 8 notches: (%.1f, %.1f) R %.1f  spread %.1f" % (c_not[0], c_not[1], r_not_fit, rr_not.std()))
print("centre used (mean of the two): (%.1f, %.1f)" % (C[0], C[1]))

# ---------- vertex-region actual boundary along the bisector ----------
def material(x, y):
    if not (0 <= x < W - 1 and 0 <= y < H - 1):
        return False
    lu = L.bilinear(lum, np.array([x]), np.array([y]))[0]
    bl = L.bilinear(bg_lum, np.array([x]), np.array([y]))[0]
    tx = L.bilinear(tex, np.array([x]), np.array([y]))[0]
    return bool(lu < bl - 0.10 and tx > 0.012)


for v in VX:
    X = v["X"]; b = v["bis"]        # bis points into the metal for BOTH kinds? check by sampling
    inward = b if material(*(X + 12 * b)) else -b
    v["inward"] = inward
    # walk outward (-inward) from a point well inside, find the last material sample
    last = None
    for d in np.arange(-40.0, 60.0, 0.25):
        p = X - d * inward
        if material(p[0], p[1]):
            last = d
    v["delta"] = float(last) if last is not None else float("nan")   # >0 : boundary beyond X
    v["P_actual"] = (X - v["delta"] * inward).tolist() if last is not None else None
    v["clipped"] = bool(last is not None and not (0 <= (X - (last + 1) * inward)[0] < W - 1 and 0 <= (X - (last + 1) * inward)[1] < H - 1))

# ---------- radii / span ----------
print()
rows = []
for v in VX:
    r = float(np.linalg.norm(v["X"] - C))
    ract = float(np.linalg.norm(np.array(v["P_actual"]) - C)) if v["P_actual"] else float("nan")
    th = math.degrees(math.atan2(-(v["X"][1] - C[1]), v["X"][0] - C[0])) % 360
    v["r"], v["r_actual"], v["theta"] = r, ract, th
    rows.append((v["name"], v["kind"], th, r, ract, v["angle"], v["delta"], v["clipped"]))
    print("%-7s %-5s th %6.2f  r_virtual %7.2f  r_actual %7.2f  angle %6.2f  delta %+6.2f %s" %
          (v["name"], v["kind"], th, r, ract, v["angle"], v["delta"], "CLIPPED-BY-IMAGE-EDGE" if v["clipped"] else ""))

tips = [v for v in VX if v["kind"] == "tip"]
nots = [v for v in VX if v["kind"] == "notch"]
tips.sort(key=lambda v: v["theta"]); nots.sort(key=lambda v: v["theta"])
opp = [float(np.linalg.norm(tips[i]["X"] - tips[i + 4]["X"])) for i in range(4)]
span = float(np.mean(opp))
print("\nopposite-tip spans (virtual apexes): %s  mean %.1f px  sd %.1f" % (["%.1f" % o for o in opp], span, np.std(opp)))
print("tip radii: %s" % ["%.1f" % v["r"] for v in tips])
print("notch radii: %s" % ["%.1f" % v["r"] for v in nots])
print("tip angular spacing: %s" % ["%.2f" % ((tips[(i + 1) % 8]["theta"] - tips[i]["theta"]) % 360) for i in range(8)])
print("notch angular spacing: %s" % ["%.2f" % ((nots[(i + 1) % 8]["theta"] - nots[i]["theta"]) % 360) for i in range(8)])

out = dict(centre=C.tolist(), centre_tips=c_tip.tolist(), centre_notches=c_not.tolist(),
           span_px=span, opp_spans=opp,
           edges=[dict(name=e["name"], rule=e["rule"], gap_lo=e["gap_lo"], gap_hi=e["gap_hi"],
                       rms=f["rms"], maxdev=f["maxdev"], sagitta=f["sagitta"], fit_len=f["fit_len"],
                       n_used=f["n_used"], n_total=f["n_total"],
                       dir_deg=math.degrees(math.atan2(-f["d"][1], f["d"][0])),
                       dir_alt_deg=math.degrees(math.atan2(-f["alt"]["d"][1], f["alt"]["d"][0])),
                       c=f["c"].tolist(), d=f["d"].tolist())
                  for e, f in zip(E, fits)],
           vertices=[dict(name=v["name"], kind=v["kind"], X=v["X"].tolist(), X_alt=v["X_alt"].tolist(),
                          angle=v["angle"], angle_alt=v["angle_alt"], theta=v["theta"], r=v["r"],
                          r_actual=v["r_actual"], delta=v["delta"], clipped=v["clipped"],
                          P_actual=v["P_actual"], edges=v["edges"]) for v in VX])
json.dump(out, open(os.path.join(OUT, "geom.json"), "w"), indent=1)
print("\nwrote geom.json")
