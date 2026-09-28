"""Stage 4: details on top of stage 3 (per tag): per-arc hub fits, flank-to-hole tangency,
root corner residuals, bevel band widths along every flank / hub arc / hole rim.

blender -b --factory-startup --python s4_details.py -- <photo> <outdir> <tag> [plots 0/1]
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
photo, outdir, tag = argv[0], argv[1], argv[2]
plots = len(argv) > 3 and argv[3] == "1"
rgb = imgio.load_rgb(photo).astype(np.float64)
H, W, _ = rgb.shape
lum = rgb.mean(2)
chroma = rgb.max(2) - rgb.min(2)
R = json.load(open(os.path.join(outdir, f"radial_{tag}.json")))
rt = np.load(os.path.join(outdir, f"rtheta_{tag}.npy"))
thetas, r_out, r_in, clipped = rt[:, 0], rt[:, 1], rt[:, 2], rt[:, 3].astype(bool)
cx, cy = R["centres"]["hole_fit_all"]
hole_r = R["hole_px"]["r_fit_all"]
hole_r_crisp = R["hole_px"]["r_fit_crisp_half"]
hcx2, hcy2 = R["centres"]["hole_fit_crisp_half"]
out = {}


def bil(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def fit_circle(x, y, iters=30):
    A = np.stack([x, y, np.ones_like(x)], 1)
    c, *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    ccx, ccy = c[0] / 2, c[1] / 2
    r = math.sqrt(c[2] + ccx * ccx + ccy * ccy)
    for _ in range(iters):
        dx, dy = x - ccx, y - ccy
        d = np.sqrt(dx * dx + dy * dy)
        J = np.stack([-dx / d, -dy / d, -np.ones_like(d)], 1)
        st, *_ = np.linalg.lstsq(J, -(d - r), rcond=None)
        ccx += st[0]; ccy += st[1]; r += st[2]
    res = np.sqrt((x - ccx) ** 2 + (y - ccy) ** 2) - r
    return ccx, ccy, r, float(np.sqrt((res ** 2).mean()))


def smooth(v, n):
    k = np.ones(n) / n
    return np.convolve(np.concatenate([v[-n:], v, v[:n]]), k, mode="same")[n:-n]


def angdiff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0

N = len(thetas)
tip_th = [p["tip"]["theta"] for p in R["points"]]
tip_idx = [int(round(t / 0.1)) % N for t in tip_th]

# ---------------------------------------------------------------- hub arcs (robust)
drs = np.gradient(smooth(r_out, 21), 0.1)
arcs = []
for k in range(6):
    a, b = tip_idx[k], tip_idx[(k + 1) % 6]
    idx = np.arange(a, b if b > a else b + N) % N
    base = np.percentile(r_out[idx], 20)
    flat = (np.abs(drs[idx]) < 4.0) & (np.abs(r_out[idx] - base) < 8)
    runs, cur = [], []
    for ii, f in zip(idx, flat):
        if f:
            cur.append(ii)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    run = max(runs, key=len)
    th = np.radians(thetas[run])
    x = cx + r_out[run] * np.cos(th); y = cy - r_out[run] * np.sin(th)
    trim = run[15:-15] if len(run) > 60 else run   # 1.5 deg off each end for curvature fit
    tht = np.radians(thetas[trim])
    xt = cx + r_out[trim] * np.cos(tht); yt = cy - r_out[trim] * np.sin(tht)
    acx, acy, ar, arms = fit_circle(xt, yt)
    mid_th = thetas[run[len(run) // 2]]
    nvec = np.array([math.cos(math.radians(mid_th)), math.sin(math.radians(mid_th))])  # y-up
    soft_score = float(np.dot(nvec, np.array([1, 1]) / math.sqrt(2)))
    arcs.append({"gap": k, "theta_start": float(thetas[run[0]]), "theta_end": float(thetas[run[-1]]),
                 "extent_deg": float(len(run) * 0.1), "r_mean_from_hole_centre": float(r_out[run].mean()),
                 "r_std": float(r_out[run].std()), "own_circle_r": ar, "own_circle_c": [acx, acy],
                 "own_circle_rms": arms, "shadow_side_score": soft_score,
                 "x": x.tolist(), "y": y.tolist()})
allx = np.concatenate([a["x"] for a in arcs]); ally = np.concatenate([a["y"] for a in arcs])
ucx, ucy, ur, urms = fit_circle(allx, ally)
crisp_arcs = [a for a in arcs if a["shadow_side_score"] < 0.2]
if len(crisp_arcs) >= 2:
    cxx = np.concatenate([a["x"] for a in crisp_arcs]); cyy = np.concatenate([a["y"] for a in crisp_arcs])
    ucx2, ucy2, ur2, urms2 = fit_circle(cxx, cyy)
else:
    ucx2 = ucy2 = ur2 = urms2 = None
out["hub"] = {"all_arcs_circle": {"c": [ucx, ucy], "r": ur, "rms": urms},
              "crisp_arcs_circle": {"c": [ucx2, ucy2], "r": ur2, "rms": urms2,
                                    "arcs_used": [a["gap"] for a in crisp_arcs]},
              "arcs": [{k: v for k, v in a.items() if k not in ("x", "y")} for a in arcs]}

# ---------------------------------------------------------------- flank lines
flanks = []
for pk in R["points"]:
    for side in ("cw", "ccw"):
        f = pk[side]
        p0 = np.array(f["p0"]); d = np.array(f["dir"])
        n = np.array([-d[1], d[0]])
        dist_hole = abs(np.dot(np.array([cx, cy]) - p0, n))
        dist_hole2 = abs(np.dot(np.array([hcx2, hcy2]) - p0, n))
        dist_hub = abs(np.dot(np.array([ucx, ucy]) - p0, n))
        flanks.append({"k": pk["k"], "side": side, "dist_from_hole_centre": float(dist_hole),
                       "dist_from_crisp_hole_centre": float(dist_hole2),
                       "dist_from_hub_centre": float(dist_hub),
                       "outward_normal": f["outward_normal"]})
dh = np.array([f["dist_from_hole_centre"] for f in flanks])
out["flank_tangency"] = {"per_flank": flanks, "mean": float(dh.mean()), "std": float(dh.std()),
                         "hole_r_all": hole_r, "hole_r_crisp": hole_r_crisp}

# ---------------------------------------------------------------- root corners
# model outline near a root = max(arc radius along ray, flank line radius along ray)
def ray_circle(th, acx, acy, ar):
    ex, ey = np.cos(np.radians(th)), -np.sin(np.radians(th))
    fx, fy = cx - acx, cy - acy
    b = 2 * (fx * ex + fy * ey); c = fx * fx + fy * fy - ar * ar
    disc = b * b - 4 * c
    return np.where(disc >= 0, (-b + np.sqrt(np.maximum(disc, 0))) / 2, np.nan)


def ray_line(th, p0, d):
    e = np.stack([np.cos(np.radians(th)), -np.sin(np.radians(th))], -1)
    n = np.array([-d[1], d[0]])
    num = np.dot(p0 - np.array([cx, cy]), n)
    den = e @ n
    r = num / den
    return np.where(r > 0, r, np.nan)

roots = []
for k, pk in enumerate(R["points"]):
    for side in ("cw", "ccw"):
        f = pk[side]
        p0 = np.array(f["p0"]); d = np.array(f["dir"])
        arc = arcs[(k - 1) % 6] if side == "cw" else arcs[k]
        acx, acy = arc["own_circle_c"]; ar = arc["own_circle_r"]
        # corner: where the flank line meets this arc's circle, the intersection nearer the tip
        # search in theta between arc end and tip
        if side == "cw":
            th_range = np.arange(arc["theta_end"] - 6, arc["theta_end"] + 12, 0.1)
        else:
            th_range = np.arange(arc["theta_start"] - 12, arc["theta_start"] + 6, 0.1)
        th_range = th_range % 360
        ra = ray_circle(th_range, acx, acy, ar)
        rl = ray_line(th_range, p0, d)
        model = np.fmax(ra, np.nan_to_num(rl, nan=-1))
        ii = (np.round(th_range / 0.1).astype(int)) % N
        e = r_out[ii] - model
        # model corner angle = where flank line radius equals arc radius
        diff = rl - ra
        ok = np.isfinite(diff)
        cidx = np.argmin(np.where(ok, np.abs(diff), 1e9))
        th_c = th_range[cidx]
        near = np.abs(angdiff(th_range, th_c)) <= 4
        roots.append({"k": k, "side": side, "corner_theta": float(th_c),
                      "corner_xy": [float(cx + ra[cidx] * math.cos(math.radians(th_c))),
                                    float(cy - ra[cidx] * math.sin(math.radians(th_c)))],
                      "min_resid_px": float(np.nanmin(e[near])), "theta_min": float(th_range[near][np.nanargmin(e[near])]),
                      "max_resid_px": float(np.nanmax(e[near])), "theta_max": float(th_range[near][np.nanargmax(e[near])]),
                      "resid_profile": [[float(t), float(v)] for t, v in zip(th_range[near][::5], e[near][::5])]})
out["roots"] = roots

# ---------------------------------------------------------------- bevel bands
def band_profiles(p0, d, nin, s_vals, depth=32, outside=6, step=0.5):
    """sample lum/chroma along inward normal from points on the fitted line."""
    offs = np.arange(-outside, depth, step)
    P = p0[None, None, :] + s_vals[:, None, None] * d[None, None, :] + offs[None, :, None] * nin[None, None, :]
    L = bil(lum, P[..., 0], P[..., 1]); C = bil(chroma, P[..., 0], P[..., 1])
    return offs, L, C


def band_width(offs, L, C, face_L, face_C):
    """per profile: edge = first offset where L drops below mid(bg, band) ... returns widths."""
    widths = []
    for li, ci in zip(L, C):
        # edge: outermost offset where lum is < 0.5 * (bg + plate) or chroma high
        bgL = np.median(li[:4])
        inside = (li < bgL - 0.5 * (bgL - face_L)) | (ci > face_C + 0.045)
        if not inside.any():
            widths.append(np.nan); continue
        e0 = np.argmax(inside)
        # band: from edge inward while chroma > face_C + 0.035 or |L - face_L| > 0.09
        j = e0
        while j < len(li) and ((ci[j] > face_C + 0.035) or (abs(li[j] - face_L) > 0.09)):
            j += 1
        widths.append((j - e0) * (offs[1] - offs[0]))
    return np.array(widths)

# face reference: deep interior of the plate (eroded solid), exclude the hole rim
solid = np.load(os.path.join(outdir, f"solid_{tag}.npy"))
core = imgio.erode(solid, 25)
face_L = float(np.median(lum[core])); face_C = float(np.median(chroma[core]))
face_C90 = float(np.percentile(chroma[core], 90)); face_L90 = np.percentile(lum[core], [10, 90]).tolist()
bev = []
for pk in R["points"]:
    for side in ("cw", "ccw"):
        f = pk[side]
        p0 = np.array(f["p0"]); d = np.array(f["dir"])
        nout = np.array(f["outward_normal"])
        # start the profile outside the fitted edge line
        L_fit = f["fit_len_px"]
        # parameterise along the flank from the root (s=-L/2) to tip (s=+L/2) roughly
        s_vals = np.linspace(-L_fit / 2, L_fit / 2, 60)
        offs, Lp, Cp = band_profiles(p0 - 0 * nout, d, -nout, s_vals)
        w = band_width(offs, Lp, Cp, face_L, face_C)
        medL = np.median(Lp, 0); medC = np.median(Cp, 0)
        wm = band_width(offs, medL[None], medC[None], face_L, face_C)[0]
        shadow = float(np.dot(np.array([nout[0], -nout[1]]), np.array([1, 1]) / math.sqrt(2)))
        bev.append({"k": pk["k"], "side": side, "shadow_side_score": shadow,
                    "band_width_median_profile_px": float(wm),
                    "band_width_per_profile_median_px": float(np.nanmedian(w)),
                    "band_width_p25_p75": np.nanpercentile(w, [25, 75]).tolist(),
                    "frac_profiles_with_band_ge3px": float(np.mean(w >= 3)),
                    "band_by_position": [float(v) for v in w],
                    "median_profile": [[float(o), float(a), float(b)] for o, a, b in zip(offs[::2], medL[::2], medC[::2])]})
# hub arcs and hole rim, radial profiles
def radial_band(th_list, r_edge_fn, inward_sign):
    ths = np.array(th_list)
    offs = np.arange(-6, 32, 0.5)
    ws = []
    Ls, Cs = [], []
    for th in ths:
        re = r_edge_fn(th)
        rr = re + inward_sign * offs * -1  # inward_sign -1: inward = decreasing r
        x = cx + rr * math.cos(math.radians(th)); y = cy - rr * math.sin(math.radians(th))
        Ls.append(bil(lum, x, y)); Cs.append(bil(chroma, x, y))
    Ls = np.array(Ls); Cs = np.array(Cs)
    w = band_width(offs, Ls, Cs, face_L, face_C)
    return w, offs, np.median(Ls, 0), np.median(Cs, 0)

arc_bev = []
for a in arcs:
    ths = np.arange(a["theta_start"] + 2, a["theta_start"] + a["extent_deg"] - 2, 0.5)
    fn = lambda th: r_out[int(round((th % 360) / 0.1)) % N]
    # edge at r_out; inward = decreasing r; profile starts 6 px outside
    offs = np.arange(-6, 32, 0.5)
    Ls, Cs = [], []
    for th in ths:
        rr = fn(th) - offs
        x = cx + rr * math.cos(math.radians(th)); y = cy - rr * math.sin(math.radians(th))
        Ls.append(bil(lum, x, y)); Cs.append(bil(chroma, x, y))
    Ls = np.array(Ls); Cs = np.array(Cs)
    w = band_width(offs, Ls, Cs, face_L, face_C)
    arc_bev.append({"gap": a["gap"], "shadow_side_score": a["shadow_side_score"],
                    "band_width_per_profile_median_px": float(np.nanmedian(w)),
                    "frac_ge3px": float(np.mean(w >= 3))})
# hole rim: edge at r_in, inward into plate = increasing r
hole_bev = []
for th0 in range(0, 360, 30):
    ths = np.arange(th0, th0 + 30, 0.5)
    offs = np.arange(-6, 32, 0.5)
    Ls, Cs = [], []
    for th in ths:
        re = r_in[int(round(th / 0.1)) % N]
        rr = re + offs
        x = cx + rr * math.cos(math.radians(th)); y = cy - rr * math.sin(math.radians(th))
        Ls.append(bil(lum, x, y)); Cs.append(bil(chroma, x, y))
    w = band_width(offs, np.array(Ls), np.array(Cs), face_L, face_C)
    hole_bev.append({"theta_range": [th0, th0 + 30], "band_width_median_px": float(np.nanmedian(w)),
                     "frac_ge3px": float(np.mean(w >= 3))})
out["bevel"] = {"face_L": face_L, "face_C": face_C, "face_C_p90": face_C90, "face_L_p10_p90": face_L90,
                "flanks": bev, "hub_arcs": arc_bev, "hole_rim": hole_bev}

# hole rim deviation from crisp-half circle, per 15 deg sector
hr_dev = []
for th0 in range(0, 360, 15):
    ths = np.arange(th0, th0 + 15, 0.1)
    ii = (np.round(ths / 0.1).astype(int)) % N
    x = cx + r_in[ii] * np.cos(np.radians(ths)); y = cy - r_in[ii] * np.sin(np.radians(ths))
    dev = np.sqrt((x - hcx2) ** 2 + (y - hcy2) ** 2) - hole_r_crisp
    hr_dev.append([th0, float(np.median(dev))])
out["hole_rim_dev_from_crisp_circle"] = hr_dev

json.dump(out, open(os.path.join(outdir, f"details_{tag}.json"), "w"), indent=1, default=float)

print("TAG", tag)
print("hub all-arcs circle c=(%.1f,%.1f) r=%.2f rms=%.2f" % (ucx, ucy, ur, urms))
print("hub crisp-arcs circle", out["hub"]["crisp_arcs_circle"])
for a in out["hub"]["arcs"]:
    print("  arc", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in a.items() if k != "own_circle_c"},
          "c", np.round(a["own_circle_c"], 1).tolist())
print("flank dist from hole centre: mean %.2f std %.2f | hole r all %.2f crisp %.2f" % (dh.mean(), dh.std(), hole_r, hole_r_crisp))
print("  ", [round(f["dist_from_hole_centre"], 1) for f in flanks])
print("  from crisp hole centre", [round(f["dist_from_crisp_hole_centre"], 1) for f in flanks])
for r_ in roots:
    print("root", r_["k"], r_["side"], "corner th %.1f xy (%.0f,%.0f) min %.1f @%.1f max %.1f @%.1f" % (
        r_["corner_theta"], r_["corner_xy"][0], r_["corner_xy"][1], r_["min_resid_px"], r_["theta_min"],
        r_["max_resid_px"], r_["theta_max"]))
print("face L %.3f C %.3f (C p90 %.3f, L p10/p90 %s)" % (face_L, face_C, face_C90, np.round(face_L90, 3).tolist()))
for b in bev:
    print("bevel pt", b["k"], b["side"], "shadow %.2f" % b["shadow_side_score"], "w_medprof %.1f w_med %.1f iqr %s frac>=3 %.2f" % (
        b["band_width_median_profile_px"], b["band_width_per_profile_median_px"],
        np.round(b["band_width_p25_p75"], 1).tolist(), b["frac_profiles_with_band_ge3px"]))
    print("     by position root->tip:", " ".join("%.0f" % v if np.isfinite(v) else "-" for v in b["band_by_position"]))
for a in arc_bev:
    print("arc bevel", a)
for h in hole_bev:
    print("hole bevel", h)
print("hole rim dev from crisp circle (sector start, median px):", [(a, round(b, 1)) for a, b in hr_dev])
