"""Stage 3 (v2): per-edge consistent outline rule, line fits, vertices.

Lighting finding (probed): the lid shows a soft shadow outside every edge whose outward
normal points up and/or right (shadow direction ~ (+x,-y) in the image); edges facing
down/left have a sharp step from metal or bright ground bevel to the lid.

Per-edge rule (chosen from the edge's median cross-profile, not per station, so every
edge is traced with ONE consistent definition):
  CLEAN edge    : outline = first place (from inside) where lum rises above bg_lum-0.08
                  and stays there 3 px  -> bright bevels are inside the outline.
  SHADOWED edge : outline = first place where lum rises above 0.30 and stays 3 px
                  (dark core: face + shaded dark facet/umbra)  -> 'OUTER' reading.
                  'INNER' alternative: the inner boundary of the band darker than the
                  face (face level - 0.04) that sits just inside the OUTER outline;
                  equals OUTER when no such band exists.
Coordinates: image px, y down. Angles theta = atan2(-(y-cy), x-cx), CCW as viewed.
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
lum = np.load(os.path.join(OUT, "lum.npy"))
bg_lum = np.load(os.path.join(OUT, "bg_lum.npy"))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
H, W = lum.shape
co = json.load(open(os.path.join(OUT, "coarse_mask_filled.json")))
C0 = np.array(co["centroid"])

DS = 0.25
S = np.arange(-30, 40 + 1e-9, DS)
g = np.exp(-0.5 * (np.arange(-6, 7) * DS / 0.75) ** 2); g /= g.sum()
g2 = np.exp(-0.5 * (np.arange(-12, 13) * DS / 1.5) ** 2); g2 /= g2.sum()
STAY = int(3 / DS)


def conv(v, k):
    p = len(k) // 2
    vv = np.concatenate([np.full(p, v[0]), v, np.full(p, v[-1])])
    return np.convolve(vv, k, mode="valid")


def sample(P, n, Sg=S):
    x = P[0] + Sg * n[0]
    y = P[1] + Sg * n[1]
    ok = (x >= 0) & (x <= W - 1.001) & (y >= 0) & (y <= H - 1.001)
    b = L.bilinear(bg_lum, np.clip(x, 0, W - 1.001), np.clip(y, 0, H - 1.001))
    v = b.copy()
    v[ok] = L.bilinear(lum, x[ok], y[ok])
    return v, b


def first_stay_above(ps, level, start=0):
    """first index i>=start with ps[i:i+STAY] all >= level[...]; returns subpixel s."""
    lv = np.broadcast_to(level, ps.shape)
    above = ps >= lv
    n = len(ps)
    for i in range(max(start, 1), n - STAY):
        if above[i] and above[i:i + STAY].all():
            # interpolate crossing between i-1 and i
            a0 = ps[i - 1] - lv[i - 1]; a1 = ps[i] - lv[i]
            f = -a0 / (a1 - a0) if a1 != a0 else 0.0
            return S[i - 1] + f * DS, i
    return np.nan, None


def profile_candidates(P, n):
    v, b = sample(P, n)
    ps = conv(v, g); ps2 = conv(v, g2)
    i_start = int(np.searchsorted(S, -20))
    # require the start region to be material (dark) -> search from the last dark sample
    s_clean, ic = first_stay_above(ps, b - 0.08, i_start)
    s_dark, idk = first_stay_above(ps, np.full_like(ps, 0.30), i_start)
    face = float(np.median(ps2[:int(np.searchsorted(S, -15))]))
    s_inner = s_dark
    band_w = 0.0
    if idk is not None:
        j = idk - 1
        # skip the transition (<= 2 px) to reach the dark band
        lim = max(idk - int(2 / DS), 0)
        while j > lim and ps2[j] >= face - 0.04:
            j -= 1
        if ps2[j] < face - 0.04:
            k = j
            while k > 0 and ps2[k] < face - 0.04:
                k -= 1
            s_inner = S[k]
            band_w = s_dark - s_inner
    return dict(s_clean=float(s_clean), s_dark=float(s_dark), s_inner=float(s_inner),
                band_w=float(band_w), face=face,
                bevel_w=float(s_clean - s_dark) if np.isfinite(s_clean) and np.isfinite(s_dark) else np.nan)


def tls(pts):
    c = pts.mean(0)
    _, _, Vt = np.linalg.svd(pts - c)
    d = Vt[0]
    return c, d


def robust_line(pts):
    keep = np.isfinite(pts).all(1)
    for _ in range(5):
        c, d = tls(pts[keep])
        nn = np.array([-d[1], d[0]])
        res = (pts - c) @ nn
        r = res[keep]
        sd = 1.4826 * np.median(np.abs(r - np.median(r))) + 0.05
        keep = np.isfinite(res) & (np.abs(res - np.median(r)) < max(3 * sd, 0.75))
    c, d = tls(pts[keep])
    nn = np.array([-d[1], d[0]])
    res = (pts[keep] - c) @ nn
    al = (pts[keep] - c) @ d
    q = np.polyfit(al, res, 2)
    half = 0.5 * (al.max() - al.min())
    return dict(c=c, d=d, rms=float(np.sqrt(np.mean(res ** 2))), maxdev=float(np.abs(res).max()),
                sagitta=float(q[0] * half ** 2), n_used=int(keep.sum()), n_total=int(np.isfinite(pts).all(1).sum()),
                fit_len=float(2 * half))


def intersect(c1, d1, c2, d2):
    M = np.array([d1, -d2]).T
    ab = np.linalg.solve(M, c2 - c1)
    return c1 + ab[0] * d1


def ang(v1, v2):
    return math.degrees(math.acos(np.clip(np.dot(v1, v2) / np.linalg.norm(v1) / np.linalg.norm(v2), -1, 1)))


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

edges = []
for i in range(nV):
    a, b = V[i], V[(i + 1) % nV]
    notch, tip = (a, b) if a["kind"] == "notch" else (b, a)
    A = notch["P"]; B = tip["P"]
    u = (B - A) / np.linalg.norm(B - A)
    n = np.array([u[1], -u[0]])
    if np.dot(n, C0 - A) > 0:
        n = -n
    Lg = float(np.linalg.norm(B - A))
    rows = []
    for t in np.arange(0.0, 1.12 + 1e-9, 1.0 / Lg):
        P = A + t * (B - A)
        r = profile_candidates(P, n)
        r["t"] = float(t)
        r["P"] = P.tolist()
        rows.append(r)
    edges.append(dict(name=notch["name"] + "-" + tip["name"], notch=notch["name"], tip=tip["name"],
                      A=A, B=B, u=u, n=n, len=Lg, rows=rows, vi=(i, (i + 1) % nV)))

# ---- classify each edge from its median profile around the dark-core outline ----
for e in edges:
    mids = [r for r in e["rows"] if 0.3 <= r["t"] <= 0.7 and np.isfinite(r["s_clean"])]
    prof = []
    for r in mids[::3]:
        P = np.array(r["P"]) + r["s_clean"] * e["n"]
        v, b = sample(P, e["n"], np.arange(0, 12.01, 1.0))
        prof.append(v - b)
    mp = np.median(np.array(prof), 0)   # lum - lid, from the 0.30 crossing outward, 0..12 px
    e["lid_deficit_profile"] = mp.tolist()
    # shadowed if, 6 px outside the (bg-0.08) crossing, the lid is still >= 0.05 darker
    # than the modelled unshadowed lid -> the outer transition is a shadow ramp, not a step
    e["shadowed"] = bool(mp[6] < -0.05)


def outline_xy(e, r, variant):
    s = r["s_dark"] if e["shadowed"] else r["s_clean"]
    if variant == "inner" and e["shadowed"]:
        s = r["s_inner"]
    if not np.isfinite(s):
        return np.array([np.nan, np.nan])
    return np.array(r["P"]) + s * e["n"]


results = {}
for variant in ("outer", "inner"):
    fits = []
    for e in edges:
        pts = np.array([outline_xy(e, r, variant) for r in e["rows"] if 0.15 <= r["t"] <= 0.85])
        f = robust_line(pts)
        if np.dot(f["d"], e["u"]) < 0:
            f["d"] = -f["d"]
        fits.append(f)
    vx = []
    for i in range(nV):
        # edges adjacent to vertex i: edge i-1 (V[i-1],V[i]) and edge i (V[i],V[i+1])
        f1, f2 = fits[(i - 1) % nV], fits[i]
        X = intersect(f1["c"], f1["d"], f2["c"], f2["d"])
        r1 = f1["d"] if np.dot(f1["d"], f1["c"] - X) > 0 else -f1["d"]
        r2 = f2["d"] if np.dot(f2["d"], f2["c"] - X) > 0 else -f2["d"]
        vx.append(dict(name=V[i]["name"], kind=V[i]["kind"], X=X.tolist(), angle=ang(r1, r2),
                       ray1=r1.tolist(), ray2=r2.tolist(),
                       edges=[edges[(i - 1) % nV]["name"], edges[i]["name"]]))
    results[variant] = dict(fits=fits, vertices=vx)

# ---- save ----
def fjson(f):
    return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in f.items()}

dump = dict(centroid_coarse=C0.tolist(), edges=[], variants={})
for k, e in enumerate(edges):
    dump["edges"].append(dict(name=e["name"], notch=e["notch"], tip=e["tip"], len=e["len"], n=e["n"].tolist(),
                              u=e["u"].tolist(), A=e["A"].tolist(), B=e["B"].tolist(), shadowed=e["shadowed"],
                              lid_deficit_profile=e["lid_deficit_profile"], rows=e["rows"]))
for variant, R in results.items():
    dump["variants"][variant] = dict(fits=[fjson(f) for f in R["fits"]], vertices=R["vertices"])
json.dump(dump, open(os.path.join(OUT, "edges_v2.json"), "w"), indent=0)

for variant, R in results.items():
    print("==== variant", variant)
    for e, f in zip(edges, R["fits"]):
        print("%-14s %-8s rms %.2f max %.2f sag %+.2f used %d/%d dir %.2f deg" % (
            e["name"], "SHADOW" if e["shadowed"] else "clean", f["rms"], f["maxdev"], f["sagitta"], f["n_used"],
            f["n_total"], math.degrees(math.atan2(-f["d"][1], f["d"][0]))))
    for v in R["vertices"]:
        print("  %-7s %-5s X=(%7.1f, %7.1f) angle %.2f" % (v["name"], v["kind"], v["X"][0], v["X"][1], v["angle"]))
for e in edges:
    print("%-14s deficit(0..12px) %s" % (e["name"], " ".join("%+.2f" % x for x in e["lid_deficit_profile"])))
