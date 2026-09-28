"""Stage 6: consolidated numbers per tag + final debug overlay (for the nominal tag).
blender -b --factory-startup --python s6_summary.py -- <photo> <outdir> <tag> [overlay 0/1]
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
photo, outdir, tag = argv[0], argv[1], argv[2]
do_ov = len(argv) > 3 and argv[3] == "1"
R = json.load(open(os.path.join(outdir, f"radial_{tag}.json")))
D = json.load(open(os.path.join(outdir, f"details_{tag}.json")))
rt = np.load(os.path.join(outdir, f"rtheta_{tag}.npy"))
thetas, r_out = rt[:, 0], rt[:, 1]
cx, cy = R["centres"]["hole_fit_all"]
N = len(thetas)


def fit_circle(x, y, iters=40):
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

out = {"tag": tag}
# hub arcs points again from r(theta) and arc theta ranges
arcs = D["hub"]["arcs"]
pts = {}
for a in arcs:
    ths = np.arange(a["theta_start"] + 1.5, a["theta_start"] + a["extent_deg"] - 1.5, 0.1)
    ii = (np.round((ths % 360) / 0.1).astype(int)) % N
    pts[a["gap"]] = (cx + r_out[ii] * np.cos(np.radians(ths)), cy - r_out[ii] * np.sin(np.radians(ths)))
five = [g for g in range(6) if g != 1]
hx = np.concatenate([pts[g][0] for g in five]); hy = np.concatenate([pts[g][1] for g in five])
h5 = fit_circle(hx, hy)
per_arc_r = {}
for g in range(6):
    x, y = pts[g]
    per_arc_r[g] = float(np.mean(np.hypot(x - h5[0], y - h5[1])))
out["hub_5arc_circle"] = {"c": [h5[0], h5[1]], "r": h5[2], "rms": h5[3],
                          "per_arc_mean_r_about_this_centre": per_arc_r}
# hole crisp
hc = R["centres"]["hole_fit_crisp_half"]; hr = R["hole_px"]["r_fit_crisp_half"]
out["hole_crisp"] = {"c": hc, "r": hr, "rms": R["hole_px"]["rms_crisp"]}

# circle tangent to the 12 flank lines (point equidistant from all lines)
lines = []
for p in R["points"]:
    for side in ("cw", "ccw"):
        f = p[side]
        p0 = np.array(f["p0"]); d = np.array(f["dir"]); n = np.array([-d[1], d[0]])
        lines.append((p0, n))
def tan_fit(ls, c0):
    c = np.array(c0, float); rr = 130.0
    for _ in range(50):
        res, J = [], []
        for p0, n in ls:
            s = np.dot(c - p0, n)
            sg = np.sign(s) if s != 0 else 1.0
            res.append(abs(s) - rr); J.append([sg * n[0], sg * n[1], -1.0])
        st, *_ = np.linalg.lstsq(np.array(J), -np.array(res), rcond=None)
        c += st[:2]; rr += st[2]
    res = np.array(res)
    return c, rr, float(np.sqrt((res ** 2).mean())), res
tc, trr, trms, tres = tan_fit(lines, [cx, cy])
l11 = [l for i, l in enumerate(lines) if i != 11]  # drop point-5 ccw flank (bent tip)
tc11, trr11, trms11, _ = tan_fit(l11, [cx, cy])
out["flank_tangent_circle"] = {"all12": {"c": tc.tolist(), "r": trr, "rms": trms, "resid": tres.tolist()},
                               "drop_p5ccw": {"c": tc11.tolist(), "r": trr11, "rms": trms11}}

# tips
tips = R["tips_raw"]
unc = [t for t in tips if not t["clipped_by_frame"]]
tip_r_hole = [math.hypot(t["x"] - hc[0], t["y"] - hc[1]) for t in unc]
gt = [p["geom"]["geometric_tip"] for p in R["points"]]
spans_unclipped = [s["dist_px"] for s in R["spans_raw_tips"] if not s["clipped"]]
span = float(np.mean(spans_unclipped))
out["span_px"] = span
out["spans_unclipped"] = spans_unclipped
out["tip_r_about_crisp_hole_centre"] = tip_r_hole
tip_th = np.array([p["geom"]["geometric_tip_theta"] for p in R["points"]])
dev = (tip_th - np.arange(6) * 60.0 + 180) % 360 - 180
dev -= dev.mean()
out["tip_angular_spacing_dev_deg"] = dev.tolist()
inc = np.array([p["geom"]["included_angle_deg"] for p in R["points"]])
base = np.array([p["geom"]["base_chord_px"] for p in R["points"]])
base_ang = np.array([p["geom"]["base_angular_deg"] for p in R["points"]])
short = np.array([p["geom"]["geometric_tip_r"] - p["tip"]["r"] for p in R["points"]])
clip = np.array([p["tip"]["clipped_by_frame"] for p in R["points"]])
wid = {f: np.array([R["widths"][k][f]["chord_px"] for k in range(6)]) for f in ("0.1", "0.25", "0.5", "0.75")}
widR = {f: np.array([R["widths"][k][f]["R_px"] for k in range(6)]) for f in ("0.1", "0.25", "0.5", "0.75")}
out["ratios_to_span"] = {
    "tip_radius_mean": float(np.mean(tip_r_hole) / span), "tip_radius_std": float(np.std(tip_r_hole) / span),
    "hub_diam_5arc": float(2 * h5[2] / span),
    "hub_diam_all6_mean_r": float(2 * np.mean([a["r_mean_from_hole_centre"] for a in arcs]) / span),
    "hole_diam_crisp": float(2 * hr / span), "hole_diam_allrim": float(2 * R["hole_px"]["r_fit_all"] / span),
    "hole_equiv_diam": float(R["hole_px"]["equiv_diam"] / span),
    "base_chord_mean": float(base.mean() / span), "base_chord_std": float(base.std() / span),
    "tip_shortfall_mean_unclipped": float(short[~clip].mean() / span),
    "flank_tangent_circle_diam": float(2 * trr11 / span),
    "point_length_hub_to_tip": float((np.mean(tip_r_hole) - h5[2]) / span),
    **{f"width_at_f{f}": float(wid[f].mean() / span) for f in wid},
    **{f"width_at_f{f}_R": float(widR[f].mean() / span) for f in widR},
    **{f"width_at_f{f}_std": float(wid[f].std() / span) for f in wid},
}
out["angles"] = {"tip_included_mean": float(inc.mean()), "tip_included_std": float(inc.std()),
                 "tip_included_min": float(inc.min()), "tip_included_max": float(inc.max()),
                 "tip_included_outer_half": [p["geom"]["included_angle_outer_half_deg"] for p in R["points"]],
                 "base_angular_mean": float(base_ang.mean()), "base_angular_std": float(base_ang.std()),
                 "exposed_hub_arc_mean": float(np.mean([a["extent_deg"] for a in arcs])),
                 "exposed_hub_arc_std": float(np.std([a["extent_deg"] for a in arcs])),
                 "bisector_lean": [p["geom"]["bisector_lean_from_radial_deg"] for p in R["points"]],
                 "flank_to_radial": [[p["geom"]["flank_cw_to_radial_deg"], p["geom"]["flank_ccw_to_radial_deg"]] for p in R["points"]]}
cents = {"hole_crisp": hc, "hub_5arc": [h5[0], h5[1]], "tip_circle": R["centres"]["tip_circle_unclipped"],
         "flank_tangent": tc11.tolist(), "silhouette_centroid": list(R["centres"]["silhouette_centroid"])}
out["centres"] = cents
json.dump(out, open(os.path.join(outdir, f"summary_{tag}.json"), "w"), indent=1, default=float)

print("TAG", tag, "span %.1f (%s)" % (span, [round(s, 1) for s in spans_unclipped]))
print("hub 5-arc circle c=(%.1f,%.1f) r=%.2f rms=%.2f per-arc r:" % h5, {g: round(v, 1) for g, v in per_arc_r.items()})
print("hole crisp c=(%.1f,%.1f) r=%.2f" % (hc[0], hc[1], hr))
print("flank tangent circle 12: c=(%.1f,%.1f) r=%.2f rms=%.2f | 11: c=(%.1f,%.1f) r=%.2f rms=%.2f" % (
    tc[0], tc[1], trr, trms, tc11[0], tc11[1], trr11, trms11))
print("tip r about crisp hole centre", [round(v, 1) for v in tip_r_hole])
print("tip spacing dev deg", np.round(dev, 2).tolist(), "std %.2f" % dev.std())
print("ratios", {k: round(v, 4) for k, v in out["ratios_to_span"].items()})
print("angles", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in out["angles"].items() if not isinstance(v, list)})
print("centres", {k: [round(v[0], 1), round(v[1], 1)] for k, v in cents.items()})

if do_ov:
    rgb = imgio.load_rgb(photo)
    H, W, _ = rgb.shape
    ov = rgb * 0.75
    def put(x, y, col, rad=0):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < W and 0 <= yi < H:
            ov[max(0, yi - rad):yi + rad + 1, max(0, xi - rad):xi + rad + 1] = col
    sil = np.load(os.path.join(outdir, f"solid_{tag}.npy")) | np.load(os.path.join(outdir, f"holes_{tag}.npy"))
    p = np.pad(sil, 1)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    ov[sil & ~inner] = [0, 1, 1]
    for a in np.arange(0, 360, 0.05):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        put(h5[0] + h5[2] * ca, h5[1] - h5[2] * sa, [1, 0, 1])
        put(hc[0] + hr * ca, hc[1] - hr * sa, [1, 1, 0])
        put(tc11[0] + trr11 * ca, tc11[1] - trr11 * sa, [1, 0.5, 0])
        tcx, tcy = R["centres"]["tip_circle_unclipped"]; trad = R["tip_circle_px"]["r"]
        put(tcx + trad * ca, tcy - trad * sa, [0.3, 0.6, 1])
    for pk in R["points"]:
        for side in ("cw", "ccw"):
            f = pk[side]
            p0 = np.array(f["p0"]); d = np.array(f["dir"])
            for s in np.arange(-700, 700, 0.5):
                q = p0 + s * d
                put(q[0], q[1], [1, 0.15, 0.15] if side == "cw" else [0.2, 1, 0.2])
        g = pk["geom"]["geometric_tip"]; put(g[0], g[1], [0, 0, 1], 3)
        put(pk["tip"]["x"], pk["tip"]["y"], [1, 1, 1], 3)
    for c in cents.values():
        put(c[0], c[1], [1, 1, 1], 2)
    imgio.save_rgb(os.path.join(outdir, "overlay_final.png"), ov)
    print("overlay saved")
