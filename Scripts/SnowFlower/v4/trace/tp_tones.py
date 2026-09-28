"""Trace pilot: SAMPLE the material colours from the reference (display sRGB -> linear albedo).
    silver  = traced plate outlines minus insets minus the blossom (the rims)
    enamel  = traced insets
    pearl   = fitted petal interiors (1.5 px in)
    lacquer = the body below the throat (rows 185-280, central 60 % of the width)
Metals are not seen as their albedo (they reflect the studio), so the silver albedo is the sampled p80 tone times
CAL (calibration factor from the first front compare, argv[1], default 1.0).  Output work/tones.json."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_geom2d as G
W = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CAL = {k: float(v) for k, v in (a.split("=") for a in argv)} if argv else {}
a = np.load(W + "/ref_full.npy")[..., :3]
TP = json.load(open(W + "/trace_plates.json"))["plates"]
BF = json.load(open(W + "/blossom_fit.json"))
Hh, Ww = a.shape[:2]
X, Y = G.grid(0, Hh, 0, Ww)
r0, r1, c0, c1 = 25, 175, 425, 590
sub = (slice(r0, r1), slice(c0, c1))
Xs, Ys = X[sub], Y[sub]
silver = np.zeros(Xs.shape, bool); enamel = np.zeros(Xs.shape, bool)
for nm, e in TP.items():
    if nm.startswith("crest") or nm.startswith("sleeve"):
        continue
    o = G.pip(Xs, Ys, np.array(e["outer"]))
    i = G.pip(Xs, Ys, np.array(e["inset"])) if "inset" in e else np.zeros_like(o)
    silver |= o & ~i; enamel |= i
cx, cy = BF["centre"]
blos = np.hypot(Xs - cx, Ys - cy) < 34
silver &= ~blos; enamel &= ~blos
# erode 1 px so edges (anti-aliasing / neighbours) do not leak in
silver = G.erode(silver, 1); enamel = G.erode(enamel, 1)
def petal_poly(phi, d0, d1, w, q, e, n=96, shrink=0.0):
    s = np.linspace(0, 1, n)
    hw = w / 2 * (2 * np.sqrt(np.clip(s * (1 - s), 0, None))) ** q * (1 + e * (s - 0.5))
    hw = np.maximum(hw - shrink, 0); u = d0 + shrink + s * (d1 - d0 - 2 * shrink)
    Q = np.vstack([np.c_[u, hw], np.c_[u[::-1], -hw[::-1]][1:-1]])
    cu, su = np.cos(phi), np.sin(phi)
    return np.c_[cx + Q[:, 0] * cu - Q[:, 1] * su, cy + Q[:, 0] * su + Q[:, 1] * cu]
pearl = np.zeros(Xs.shape, bool)
for pp in BF["petals"]:
    pearl |= G.pip(Xs, Ys, petal_poly(pp["phi"], pp["d0"], pp["d1"], pp["w"], pp["q"], pp["e"], shrink=2.5))
lac = np.zeros(a.shape[:2], bool); lac[185:280, 476:536] = True
A = a[sub]
def stats(m, arr=A):
    v = arr[m] if arr is A else a[m]
    lum = v @ [0.2126, 0.7152, 0.0722]
    return {"n": int(m.sum()), "median": np.median(v, 0).round(4).tolist(), "p80_by_lum": v[(lum >= np.percentile(lum, 70)) & (lum <= np.percentile(lum, 90))].mean(0).round(4).tolist(),
            "lum_p10_p50_p90": np.percentile(lum, [10, 50, 90]).round(4).tolist()}
S = {"silver": stats(silver), "enamel": stats(enamel), "pearl": stats(pearl), "lacquer": stats(lac, a)}
def lin(c): return [float((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c]
alb = {
    "silver": [min(v * CAL.get("silver", 1.0), 0.95) for v in lin(S["silver"]["p80_by_lum"])],
    "enamel": [v * CAL.get("enamel", 1.0) for v in lin(S["enamel"]["median"])],
    "pearl": [min(v * CAL.get("pearl", 1.0), 0.95) for v in lin(S["pearl"]["median"])],
    "lacquer": [v * CAL.get("lacquer", 1.0) for v in lin(S["lacquer"]["median"])],
}
out = {"sampled_display_srgb": S, "albedo_linear": alb, "calibration": CAL}
json.dump(out, open(W + "/tones.json", "w"), indent=1)
for k in S: print(k, S[k]["n"], "median", S[k]["median"], "p80", S[k]["p80_by_lum"], "lum", S[k]["lum_p10_p50_p90"], "-> albedo", np.round(alb[k], 4).tolist())
