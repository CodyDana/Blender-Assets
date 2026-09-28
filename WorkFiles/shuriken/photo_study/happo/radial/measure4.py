"""Stage 5: final numbers - vertex boundaries, outline polygon, mask, r(theta), widths,
bevel bands, star-polygon match. Writes results.json, happo_mask.png, overlay PNGs.
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
lum = np.load(os.path.join(OUT, "lum.npy"))
bg_lum = np.load(os.path.join(OUT, "bg_lum.npy"))
tex = np.load(os.path.join(OUT, "tex.npy"))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
H, W = lum.shape
G = json.load(open(os.path.join(OUT, "geom.json")))
EJ = json.load(open(os.path.join(OUT, "edges_v3.json")))["edges"]
C = np.array(G["centre"])
VS = G["vertices"]
ES = G["edges"]
nE = len(ES)


def bil(a, p):
    return float(L.bilinear(a, np.array([p[0]]), np.array([p[1]]))[0])


def is_metal(p):
    """metal face / bevel: clearly darker than the modelled lid, but not the black lid
    umbra (which is very dark AND smooth)."""
    if not (1 <= p[0] < W - 2 and 1 <= p[1] < H - 2):
        return False
    lu = bil(lum, p); b = bil(bg_lum, p); tx = bil(tex, p)
    if lu > b - 0.11:
        return False
    if tx < 0.008:               # perfectly smooth -> lid shadow, not metal
        return False
    if lu > 0.30 and tx < 0.012:  # mid-grey and smooth -> lid shadow, not a lit bevel
        return False
    return True


# ---------- actual boundary at each vertex, along the radial direction ----------
for v in VS:
    X = np.array(v["X"])
    u = (X - C) / np.linalg.norm(X - C)
    run = 0
    last = None
    for d in np.arange(-45.0, 40.0, 0.25):
        p = X + d * u
        if is_metal(p):
            last = d
            run = 0
        else:
            run += 0.25
            if last is not None and run >= 4.0:
                break
    v["delta_px"] = float(last) if last is not None else float("nan")
    P = X + v["delta_px"] * u if last is not None else None
    v["P_actual"] = P.tolist() if P is not None else None
    v["r_actual"] = float(np.linalg.norm(P - C)) if P is not None else float("nan")
    v["at_image_edge"] = bool(P is not None and (P[0] < 3 or P[1] < 3 or P[0] > W - 4 or P[1] > H - 4))

# ---------- outline polygon ----------
poly = []
for i, (e, ge) in enumerate(zip(EJ, ES)):
    # vertices adjacent: VS[i] (start, the vertex shared with edge i-1) and VS[i+1]
    Va = np.array(VS[i]["X"]); Vb = np.array(VS[(i + 1) % nE]["X"])
    d = np.array(ge["d"]); c = np.array(ge["c"])
    n = np.array(e["n"])
    ta = (Va - c) @ d; tb = (Vb - c) @ d
    lo, hi = min(ta, tb), max(ta, tb)
    pts = []
    for r in e["rows"]:
        s = r.get("s_edge", float("nan"))
        if not np.isfinite(s):
            continue
        p = np.array(r["P"]) + s * n
        proj = (p - c) @ d
        if lo + 12 <= proj <= hi - 12:
            pts.append((proj, p))
    pts.sort(key=lambda z: z[0])
    if ta > tb:
        pts = pts[::-1]
    if VS[i]["P_actual"]:
        poly.append(np.array(VS[i]["P_actual"]))
    poly.extend([p for _, p in pts])
poly = np.array(poly)   # natural outline order (edges are in angular order)
np.save(os.path.join(OUT, "polygon.npy"), poly)

# ---------- r(theta) at 0.1 deg: ray from C vs every polygon segment ----------
grid = np.arange(0, 360, 0.1)
A = poly - C
B = np.roll(poly, -1, axis=0) - C
r_theta = np.zeros(len(grid))
for i, tdeg in enumerate(grid):
    dvec = np.array([math.cos(math.radians(tdeg)), -math.sin(math.radians(tdeg))])
    nvec = np.array([-dvec[1], dvec[0]])
    da = A @ nvec; db = B @ nvec
    cross = (da > 0) != (db > 0)
    if not cross.any():
        r_theta[i] = np.nan
        continue
    a = A[cross]; b = B[cross]
    f = da[cross] / (da[cross] - db[cross])
    P = a + f[:, None] * (b - a)
    rr = P @ dvec
    rr = rr[rr > 0]
    rr = rr[(rr > 150) & (rr < 800)]
    r_theta[i] = rr.max() if len(rr) else np.nan
bad = ~np.isfinite(r_theta)
if bad.any():
    r_theta[bad] = np.interp(grid[bad], grid[~bad], r_theta[~bad])
np.save(os.path.join(OUT, "r_theta.npy"), np.stack([grid, r_theta]))

F = np.abs(np.fft.rfft(r_theta - r_theta.mean()))
harm = {int(k): float(F[k] / len(r_theta) * 2) for k in range(1, 33)}
dom = int(np.argmax(F[1:40]) + 1)
# 8-fold symmetry: rms of r(theta) - r(theta+45)
sh = int(45 / 0.1)
sym_rms = float(np.sqrt(np.mean((r_theta - np.roll(r_theta, sh)) ** 2)))

# ---------- mask raster from the polygon ----------
mask = np.zeros((H, W), bool)
P1 = poly
P2 = np.roll(poly, -1, axis=0)
for y in range(H):
    y0 = y + 0.5
    cond = ((P1[:, 1] > y0) != (P2[:, 1] > y0))
    if not cond.any():
        continue
    a = P1[cond]; b = P2[cond]
    xs = a[:, 0] + (y0 - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1])
    xs = np.sort(xs)
    for i in range(0, len(xs) - 1, 2):
        x0 = int(math.ceil(xs[i] - 0.5)); x1 = int(math.floor(xs[i + 1] - 0.5))
        if x1 >= x0:
            mask[y, max(x0, 0):min(x1 + 1, W)] = True
L.save_png(os.path.join(OUT, "happo_mask.png"), mask.astype(np.float32))
np.save(os.path.join(OUT, "mask_final.npy"), mask)

# ---------- span, radii, angles ----------
tips = [v for v in VS if v["kind"] == "tip"]
nots = [v for v in VS if v["kind"] == "notch"]
tips.sort(key=lambda v: v["theta"]); nots.sort(key=lambda v: v["theta"])
opp = [float(np.linalg.norm(np.array(tips[i]["X"]) - np.array(tips[i + 4]["X"]))) for i in range(4)]
span = float(np.mean(opp))
opp_act = []
for i in range(4):
    if tips[i]["P_actual"] and tips[i + 4]["P_actual"]:
        opp_act.append(float(np.linalg.norm(np.array(tips[i]["P_actual"]) - np.array(tips[i + 4]["P_actual"]))))

# ---------- widths of each point at radius fractions (from the two fitted lines) ----------
def line_of(name):
    for ge in ES:
        if ge["name"] == name:
            return np.array(ge["c"]), np.array(ge["d"])
    raise KeyError(name)


widths = {}
for v in tips:
    X = np.array(v["X"])
    ax = (X - C) / np.linalg.norm(X - C)
    per = np.array([-ax[1], ax[0]])
    l1 = line_of(v["edges"][0]); l2 = line_of(v["edges"][1])
    w = {}
    for f in (0.5, 0.6, 0.7, 0.8, 0.9):
        r = f * v["r"]
        Q = C + r * ax
        ds = []
        for (c0, d0) in (l1, l2):
            # intersect the line through Q along 'per' with the edge line
            M = np.array([per, -d0]).T
            sol = np.linalg.solve(M, c0 - Q)
            ds.append(abs(sol[0]))
        w[f] = float(sum(ds))
    widths[v["name"]] = w

# ---------- bevel / dark band widths per edge ----------
bands = []
for e, ge in zip(EJ, ES):
    rows = e["rows"]
    t = np.array([r["t"] for r in rows])
    lit = np.array([r.get("s_edge", np.nan) - r["s_dark"] for r in rows])
    dark = np.array([r["band_w"] for r in rows])
    band = np.where(np.isfinite(lit) & (lit > dark), lit, dark)
    seg = lambda a, b: float(np.nanmedian(band[(t >= a) & (t <= b)]))
    segl = lambda a, b: float(np.nanmedian(lit[(t >= a) & (t <= b)]))
    segd = lambda a, b: float(np.nanmedian(dark[(t >= a) & (t <= b)]))
    ok = (t >= 0.05) & (t <= 0.95) & np.isfinite(band)
    bands.append(dict(edge=ge["name"], kind="edge band",
                      near_notch=seg(0.05, 0.3), mid=seg(0.4, 0.6), near_tip=seg(0.7, 0.95),
                      lit_notch=segl(0.05, 0.3), lit_mid=segl(0.4, 0.6), lit_tip=segl(0.7, 0.95),
                      dark_notch=segd(0.05, 0.3), dark_mid=segd(0.4, 0.6), dark_tip=segd(0.7, 0.95),
                      frac_gt3px=float(np.mean(band[ok] > 3)), frac_gt6px=float(np.mean(band[ok] > 6))))

# ---------- notch fillet / tip bluntness ----------
for v in VS:
    a = math.radians(v["angle"] / 2)
    v["fillet_r_px"] = float(abs(v["delta_px"]) * math.sin(a) / (1 - math.sin(a))) if np.isfinite(v["delta_px"]) else float("nan")

res = dict(
    image=dict(file="Happo.JPG", w=W, h=H),
    centre_px=C.tolist(), centre_from_tips=G["centre_tips"], centre_from_notches=G["centre_notches"],
    span_px=span, opposite_tip_spans_px=opp, opposite_tip_spans_actual_px=opp_act,
    point_count=dict(dominant_harmonic=dom, harmonic_amplitudes_px={k: harm[k] for k in (6, 7, 8, 9, 16, 24, 32)},
                     sym45_rms_px=sym_rms),
    tips=[dict(name=v["name"], theta=v["theta"], r_virtual=v["r"], r_actual=v["r_actual"],
               blunt_px=-v["delta_px"], blunt_radius_px=v["fillet_r_px"], angle=v["angle"], angle_alt=v["angle_alt"],
               at_image_edge=v["at_image_edge"], X=v["X"], P_actual=v["P_actual"]) for v in tips],
    notches=[dict(name=v["name"], theta=v["theta"], r_virtual=v["r"], r_actual=v["r_actual"],
                  fill_px=v["delta_px"], fillet_radius_px=v["fillet_r_px"], angle=v["angle"], angle_alt=v["angle_alt"],
                  X=v["X"], P_actual=v["P_actual"]) for v in nots],
    edges=[dict(name=ge["name"], rule=ge["rule"], rms_px=ge["rms"], maxdev_px=ge["maxdev"], sagitta_px=ge["sagitta"],
                fit_len_px=ge["fit_len"], dir_deg=ge["dir_deg"], dir_alt_deg=ge["dir_alt_deg"],
                gap_lo=ge["gap_lo"], gap_hi=ge["gap_hi"]) for ge in ES],
    widths_by_radius_fraction=widths, bands=bands,
)
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)

tv = np.array([v["r"] for v in tips]); nv = np.array([v["r"] for v in nots])
ta = np.array([v["angle"] for v in tips]); na = np.array([v["angle"] for v in nots])
print("centre (%.1f, %.1f)  span %.1f px  (opposite-tip: %s)" % (C[0], C[1], span, ["%.0f" % o for o in opp]))
print("tip r virtual  mean %.1f sd %.1f  min %.1f max %.1f" % (tv.mean(), tv.std(), tv.min(), tv.max()))
print("notch r virtual mean %.1f sd %.1f  min %.1f max %.1f" % (nv.mean(), nv.std(), nv.min(), nv.max()))
print("ratio notch/tip %.4f   (regular {8/2}=0.7654  {8/3}=0.5412)" % (nv.mean() / tv.mean()))
print("tip angle mean %.2f sd %.2f  [%s]" % (ta.mean(), ta.std(), " ".join("%.1f" % a for a in ta)))
print("notch angle mean %.2f sd %.2f  [%s]" % (na.mean(), na.std(), " ".join("%.1f" % a for a in na)))
print("notch - tip angle = %.2f (a regular straight-edged 8-point star gives exactly 45)" % (na.mean() - ta.mean()))
print("predicted notch/tip radius ratio from mean tip angle: %.4f" %
      (math.sin(math.radians(ta.mean() / 2)) / math.sin(math.radians(ta.mean() / 2 + 22.5))))
print("dominant harmonic %d  amp8 %.1f px  sym45 rms %.2f px" % (dom, harm[8], sym_rms))
print("tip bluntness (virtual - actual, px): %s" % ["%.0f" % (-v["delta_px"]) for v in tips])
print("notch fill (actual - virtual, px): %s" % ["%.0f" % v["delta_px"] for v in nots])
print("notch fillet radius est (px): %s" % ["%.0f" % v["fillet_r_px"] for v in nots])
for b in bands:
    print("band %-14s notch %5.1f mid %5.1f tip %5.1f  (lit %4.1f/%4.1f/%4.1f dark %4.1f/%4.1f/%4.1f) frac>3px %.2f" %
          (b["edge"], b["near_notch"], b["mid"], b["near_tip"], b["lit_notch"], b["lit_mid"], b["lit_tip"],
           b["dark_notch"], b["dark_mid"], b["dark_tip"], b["frac_gt3px"]))
for k, w in widths.items():
    print("width %-8s " % k + "  ".join("r%.1f: %.1f px (%.3f span)" % (f, v, v / span) for f, v in w.items()))
print("\nr(theta): min %.1f max %.1f" % (r_theta.min(), r_theta.max()))
