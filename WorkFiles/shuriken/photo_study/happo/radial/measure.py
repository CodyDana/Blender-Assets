"""Stage 3: edge-normal profile outline extraction, line fits, vertices, r(theta).

Outline rule along each profile (s = signed distance along the OUTWARD edge normal):
  profs  : lum sampled bilinearly, Gaussian smoothed (sigma 0.75 px)
  s_lid  : first s (from inside) where profs >= bg_lum - 0.05  (lid reached)
  s_dark : last s < s_lid with profs < 0.30 (face, dark shaded facet or black umbra)
  outline: the OUTERMOST sharp rise in (s_dark, s_lid] (slope >= 0.06/px and total
           rise >= 0.08 over ~4 px) -> half-level crossing of that rise; if none,
           the 0.30 crossing just outside s_dark.  Soft lid shadows have no sharp
           rise, so they are excluded; bright bevels end in a sharp rise to the lid,
           so they are included. Dark bands (<0.30) on up-facing edges are INCLUDED
           ('outer' reading).  The 'inner' alternative (dark band excluded) is
           computed separately as outline minus the very-dark band width.
Angles in the image frame with y down: theta = atan2(-(y-cy), x-cx) (CCW as viewed).
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
warm = (rgb[..., 0] - rgb[..., 2]).astype(np.float32)
co = json.load(open(os.path.join(OUT, "coarse_mask_filled.json")))
C0 = np.array(co["centroid"])

DS = 0.25
S = np.arange(-30, 40 + 1e-9, DS)
g = np.exp(-0.5 * (np.arange(-6, 7) * DS / 0.75) ** 2); g /= g.sum()
g2 = np.exp(-0.5 * (np.arange(-12, 13) * DS / 1.5) ** 2); g2 /= g2.sum()


def sample(P, n):
    x = P[0] + S * n[0]
    y = P[1] + S * n[1]
    ok = (x >= 0) & (x <= W - 1.001) & (y >= 0) & (y <= H - 1.001)
    v = np.full(len(S), np.nan)
    v[ok] = L.bilinear(lum, x[ok], y[ok])
    # outside the image: treat as lid
    b = L.bilinear(bg_lum, np.clip(x, 0, W - 1.001), np.clip(y, 0, H - 1.001))
    v[~ok] = b[~ok]
    wv = np.full(len(S), 0.015)
    wv[ok] = L.bilinear(warm, x[ok], y[ok])
    return v, b, wv


def conv(v, k):
    p = len(k) // 2
    vv = np.concatenate([np.full(p, v[0]), v, np.full(p, v[-1])])
    return np.convolve(vv, k, mode="valid")


def outline_on_profile(P, n):
    v, b, wv = sample(P, n)
    ws = conv(wv, g)
    ps = conv(v, g)
    ps2 = conv(v, g2)
    bgref = b[-1]
    i0 = np.searchsorted(S, -20)
    lidi = np.flatnonzero((ps >= bgref - 0.05) & (np.arange(len(S)) > i0))
    i_lid = lidi[0] if len(lidi) else len(S) - 1
    dk = np.flatnonzero(ps[:i_lid] < 0.30)
    i_dark = dk[-1] if len(dk) else 0
    no_dark = len(dk) == 0
    d = np.gradient(ps, DS)
    w4 = int(4 / DS)
    cand = []
    for i in range(i_dark + 1, i_lid + 1):
        if d[i] >= 0.06 and d[i] >= d[max(i - 1, 0)] and d[i] >= d[min(i + 1, len(S) - 1)]:
            lo = ps[max(i - int(1.5 / DS), 0)]
            hi = ps[min(i + int(2.5 / DS), len(S) - 1)]
            if hi - lo >= 0.08:
                cand.append(i)
    kind = "dark030"
    if cand:
        i = cand[-1]
        lo = ps[max(i - int(1.5 / DS), 0)]
        hi = ps[min(i + int(3 / DS), len(S) - 1)]
        mid = 0.5 * (lo + hi)
        j0, j1 = max(i - int(2.5 / DS), 0), min(i + int(3 / DS), len(S) - 1)
        seg = ps[j0:j1 + 1]
        k = np.flatnonzero((seg[:-1] < mid) & (seg[1:] >= mid))
        if len(k):
            k = k[-1] + j0
            s_edge = S[k] + DS * (mid - ps[k]) / (ps[k + 1] - ps[k] + 1e-9)
        else:
            s_edge = S[i]
        kind = "rise"
        rise = hi - lo
    else:
        k = i_dark
        if k + 1 < len(S) and ps[k + 1] != ps[k]:
            s_edge = S[k] + DS * (0.30 - ps[k]) / (ps[k + 1] - ps[k])
        else:
            s_edge = S[k]
        rise = 0.0
    # warmth candidate: outermost place where warmth falls (going outward) from
    # metal-warm (>= 0.035) to lid-neutral (<= 0.03 for the next 3 px)
    s_warm = np.nan
    n3 = int(3 / DS)
    for i in range(len(S) - n3 - 1, i0, -1):
        if ws[i] >= 0.035 and ws[i + 1] < 0.035 and np.all(ws[i + 1:i + 1 + n3] <= 0.03):
            if ws[max(i - n3, 0)] - ws[min(i + n3, len(S) - 1)] >= 0.025:
                s_warm = S[i] + DS * (ws[i] - 0.035) / (ws[i] - ws[i + 1] + 1e-9)
                break
    s_lumedge = s_edge
    if np.isfinite(s_warm) and s_warm > s_edge + 0.75 and s_warm < s_edge + 25:
        # accept only if the lum profile between is material-like (not lid): below bg - 0.015 on average
        m = (S > s_edge) & (S < s_warm)
        if m.sum() == 0 or np.mean(ps[m]) < bgref - 0.015:
            s_edge = s_warm
            kind = "warm"
    s_dark = S[i_dark] if not no_dark else np.nan
    # bright bevel: between s_dark and s_edge, profile mostly in [0.30, bgref-0.06]
    bevel_w = 0.0
    if kind in ("rise", "warm") and not no_dark:
        m = (S > s_dark) & (S < s_edge)
        if m.sum() > 0:
            bevel_w = max(0.0, s_edge - s_dark)
    elif kind in ("rise", "warm") and no_dark:
        bevel_w = np.nan  # all-bevel (tip region)
    # very dark band just inside the outline (shaded facet OR umbra): skip <= 2.5 px of
    # transition, then count contiguous ps2 < 0.15 going inward
    i_e = min(int(np.searchsorted(S, s_edge)), len(S) - 1)
    j = i_e
    lim = max(i_e - int(2.5 / DS), 0)
    while j > lim and ps2[j] >= 0.15:
        j -= 1
    dark_band = 0.0
    if ps2[j] < 0.15:
        k2 = j
        while k2 > 0 and ps2[k2] < 0.15:
            k2 -= 1
        dark_band = float(s_edge - S[k2])
    return dict(s_edge=float(s_edge), s_dark=float(s_dark), kind=kind, rise=float(rise),
                bevel_w=float(bevel_w), dark_band=float(dark_band), no_dark=bool(no_dark),
                s_lid=float(S[i_lid]), s_warm=float(s_warm), s_lumedge=float(s_lumedge))


# ---------------- vertices & edges ----------------
tips = co["tips"]; notches = co["notches"]
verts = []
for t in tips:
    verts.append(("tip", t["theta"] % 360, np.array([t["x"], t["y"]])))
for t in notches:
    verts.append(("notch", t["theta"] % 360, np.array([t["x"], t["y"]])))
verts.sort(key=lambda v: v[1])
# rotate so the list starts with a notch
while verts[0][0] != "notch":
    verts = verts[1:] + verts[:1]
names = {}
ti = 0
compass = ["E", "ENE", "NE", "NNE", "N", "NNW", "NW", "WNW", "W", "WSW", "SW", "SSW", "S", "SSE", "SE", "ESE"]
def comp(th):
    return compass[int(((th % 360) + 11.25) // 22.5) % 16]
V = []
for kind, th, P in verts:
    V.append(dict(kind=kind, theta=th, P=P, name=("T" if kind == "tip" else "N") + "_" + comp(th)))
nV = len(V)
edges = []
for i in range(nV):
    a, b = V[i], V[(i + 1) % nV]
    notch, tip = (a, b) if a["kind"] == "notch" else (b, a)
    edges.append(dict(notch=notch, tip=tip, name=notch["name"] + "-" + tip["name"]))

results = []
all_pts = []
for e in edges:
    A = e["notch"]["P"]; B = e["tip"]["P"]
    u = (B - A) / np.linalg.norm(B - A)
    n = np.array([u[1], -u[0]])
    if np.dot(n, C0 - A) > 0:
        n = -n
    Lg = np.linalg.norm(B - A)
    ts = np.arange(0.03, 0.97 + 1e-9, 1.5 / Lg)
    rows = []
    for t in ts:
        P = A + t * (B - A)
        r = outline_on_profile(P, n)
        q = P + r["s_edge"] * n
        r.update(t=float(t), x=float(q[0]), y=float(q[1]))
        rows.append(r)
    e["u"], e["n"], e["len"] = u, n, Lg
    e["rows"] = rows
    results.append(e)

# ---- line fits (t in [0.15, 0.85]) ----
def tls(pts):
    c = pts.mean(0)
    U, s_, Vt = np.linalg.svd(pts - c)
    d = Vt[0]
    nn = np.array([-d[1], d[0]])
    res = (pts - c) @ nn
    return c, d, res


def fit_edge(e, key_shift=None, lo=0.15, hi=0.85):
    rows = [r for r in e["rows"] if lo <= r["t"] <= hi]
    pts = np.array([[r["x"], r["y"]] for r in rows])
    if key_shift is not None:
        sh = np.array([r[key_shift] for r in rows])
        pts = pts - sh[:, None] * e["n"][None, :]
    keep = np.ones(len(pts), bool)
    for _ in range(4):
        c, d, res = tls(pts[keep])
        _, _, res_all = (c, d, (pts - c) @ np.array([-d[1], d[0]]))
        sd = 1.4826 * np.median(np.abs(res_all[keep] - np.median(res_all[keep]))) + 0.05
        keep = np.abs(res_all) < max(3 * sd, 1.0)
    c, d, res = tls(pts[keep])
    if np.dot(d, e["u"]) < 0:
        d = -d
    # curvature: quadratic of normal offset vs along-edge coordinate
    al = (pts[keep] - c) @ d
    nn = np.array([-d[1], d[0]])
    off = (pts[keep] - c) @ nn
    q = np.polyfit(al, off, 2)
    half = 0.5 * (al.max() - al.min())
    sag = q[0] * half ** 2
    return dict(c=c, d=d, rms=float(np.sqrt(np.mean(res ** 2))), maxdev=float(np.abs(res).max()),
                n_used=int(keep.sum()), n_total=len(pts), sagitta=float(sag), fit_len=float(2 * half))


def intersect(c1, d1, c2, d2):
    M = np.array([d1, -d2]).T
    ab = np.linalg.solve(M, c2 - c1)
    return c1 + ab[0] * d1


def angle_between(v1, v2):
    return math.degrees(math.acos(np.clip(np.dot(v1, v2) / np.linalg.norm(v1) / np.linalg.norm(v2), -1, 1)))


for e in results:
    e["fit"] = fit_edge(e)

nE = len(results)
# vertex order: edge i joins V[i] and V[i+1]
vert_out = []
for i in range(nV):
    e_prev = results[(i - 1) % nE]  # joins V[i-1], V[i]
    e_next = results[i]             # joins V[i], V[i+1]
    f1, f2 = e_prev["fit"], e_next["fit"]
    X = intersect(f1["c"], f1["d"], f2["c"], f2["d"])
    kind = V[i]["kind"]
    # rays away from the vertex along each edge
    if kind == "tip":
        r1 = -f1["d"] if np.dot(f1["d"], X - f1["c"]) > 0 else f1["d"]
        r2 = -f2["d"] if np.dot(f2["d"], X - f2["c"]) > 0 else f2["d"]
    else:
        r1 = -f1["d"] if np.dot(f1["d"], X - f1["c"]) > 0 else f1["d"]
        r2 = -f2["d"] if np.dot(f2["d"], X - f2["c"]) > 0 else f2["d"]
    ang = angle_between(r1, r2)
    vert_out.append(dict(name=V[i]["name"], kind=kind, X=X, angle=ang, r1=r1, r2=r2,
                         e_prev=e_prev["name"], e_next=e_next["name"]))

# ---------------- save intermediate ----------------
dump = dict(centroid_coarse=C0.tolist(), edges=[], vertices=[])
for e in results:
    f = e["fit"]
    dump["edges"].append(dict(name=e["name"], len=e["len"], n=e["n"].tolist(), u=e["u"].tolist(),
                              fit=dict(c=f["c"].tolist(), d=f["d"].tolist(), rms=f["rms"], maxdev=f["maxdev"],
                                       sagitta=f["sagitta"], n_used=f["n_used"], n_total=f["n_total"],
                                       fit_len=f["fit_len"]),
                              rows=e["rows"]))
for v in vert_out:
    dump["vertices"].append(dict(name=v["name"], kind=v["kind"], X=v["X"].tolist(), angle=v["angle"],
                                 r1=v["r1"].tolist(), r2=v["r2"].tolist()))
json.dump(dump, open(os.path.join(OUT, "edges_outer.json"), "w"), indent=0)

for e in results:
    f = e["fit"]
    rows = e["rows"]
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print("%-14s len %6.1f  n=(%+.2f,%+.2f) rms %.2f max %.2f sag %+.2f used %d/%d kinds %s darkband_med %.1f bevel_med %.1f" % (
        e["name"], e["len"], e["n"][0], e["n"][1], f["rms"], f["maxdev"], f["sagitta"], f["n_used"], f["n_total"], kinds,
        np.nanmedian([r["dark_band"] for r in rows]), np.nanmedian([r["bevel_w"] for r in rows])))
for v in vert_out:
    print("%-8s %-5s X=(%.1f, %.1f) angle %.2f" % (v["name"], v["kind"], v["X"][0], v["X"][1], v["angle"]))
