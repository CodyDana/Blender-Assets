"""Stage 4: robust corner fillet radii (area method), bevel-band widths along the two lit outer edges,
hook root width by linear extrapolation, and the final ratio summary."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
mask = np.unpackbits(np.load(os.path.join(C.OUT, "mask.npy")))[:h * w].reshape(h, w).astype(bool)
R1 = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
R2 = json.load(open(os.path.join(C.OUT, "measure2.json")))
G = json.load(open(os.path.join(C.OUT, "geometry_internal.json")))
cont = np.load(os.path.join(C.OUT, "contour_final.npy"))
cx, cy = G["centre"]
CX = cont[:, 0] - cx; CY = -(cont[:, 1] - cy)
seg = np.hypot(np.diff(cont[:, 0], append=cont[0, 0]), np.diff(cont[:, 1], append=cont[0, 1]))
arc = np.concatenate([[0], np.cumsum(seg)[:-1]]); L_total = float(seg.sum())
SPAN = R1["SPAN_px"]
lumw = np.array([0.2126, 0.7152, 0.0722])
OUT = {}


def mathpts(idx):
    return np.column_stack([CX[idx], CY[idx]])


def local_line(i, direction, a0=60, a1=250):
    ds = ((arc - arc[i]) * direction) % L_total
    sel = np.nonzero((ds >= a0) & (ds <= a1))[0]
    P = mathpts(sel)
    c = P.mean(0)
    U, S, Vt = np.linalg.svd(P - c, full_matrices=False)
    d = Vt[0]
    if (P.mean(0) - np.array([CX[i], CY[i]])) @ d < 0:
        d = -d
    return c, d


# ---------- corner fillet radius by missing/extra area inside a disc ----------
RD = 60.0
gy, gx = np.mgrid[-int(RD):int(RD) + 1, -int(RD):int(RD) + 1]
disc = (gx ** 2 + gy ** 2) <= RD * RD
fillets = []
for cinfo in R1["corners"]:
    i = cinfo["contour_i"]
    X = np.array(cinfo["ideal_vertex_math"])
    c1, d1 = local_line(i, -1)
    c2, d2 = local_line(i, +1)
    concave = 'concave' in cinfo["kind"]
    # grid of math coords around the ideal vertex
    PX = X[0] + gx; PY = X[1] - gy      # gy increases downward in image rows
    ix = np.round(cx + PX).astype(int); iy = np.round(cy - PY).astype(int)
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    m = np.zeros(gx.shape, bool); m[ok] = mask[iy[ok], ix[ok]]
    # half planes: metal side of each edge line. Determine the sign using the mask far from the corner
    def halfplane(c, d):
        n = np.array([-d[1], d[0]])
        s = (PX - c[0]) * n[0] + (PY - c[1]) * n[1]
        probe = np.array([CX[i], CY[i]]) + 30 * d  # a point along the edge
        # test both sides 12 px off the edge
        p_in = probe + 12 * n; p_out = probe - 12 * n
        vin = mask[int(round(cy - p_in[1])), int(round(cx + p_in[0]))]
        return s > 0 if vin else s < 0
    H1 = halfplane(c1, d1); H2 = halfplane(c2, d2)
    ideal = (H1 | H2) if concave else (H1 & H2)
    diff = (m.astype(int) - ideal.astype(int))[disc]
    A = float(diff.sum()) * (1 if concave else -1)   # concave: extra metal; convex: missing metal
    alpha = math.radians(cinfo["angle_between_edges_deg"])
    k = 1 / math.tan(alpha / 2) - (math.pi - alpha) / 2
    r = math.sqrt(max(A, 0) / k) if k > 0 else float('nan')
    fillets.append(dict(kind=cinfo["kind"], area_px=A, angle_deg=cinfo["angle_between_edges_deg"],
                        fillet_radius_px=r, fillet_ratio_span=r / SPAN, vertex_gap_px=cinfo["gap_px"]))
OUT["corner_fillets_area_method"] = fillets

# ---------- bevel band along the outer edges ----------
depths = np.arange(0, 60, 0.5)


def fwd(i0, i1):
    L = (arc[i1] - arc[i0]) % L_total
    ds = (arc - arc[i0]) % L_total
    idx = np.nonzero((ds > 0) & (ds < L))[0]
    return idx[np.argsort(ds[idx])], L


def band_along(i0, i1, n=24):
    idx, L = fwd(i0, i1)
    dsl = (arc[idx] - arc[i0]) % L_total
    out = []
    for s0 in np.linspace(0.03 * L, 0.95 * L, n):
        k = idx[np.argmin(np.abs(dsl - s0))]
        ka = idx[np.argmin(np.abs(dsl - (s0 - 10)))]; kb = idx[np.argmin(np.abs(dsl - (s0 + 10)))]
        t = np.array([CX[kb] - CX[ka], CY[kb] - CY[ka]], float); t /= np.linalg.norm(t) + 1e-9
        nn = np.array([-t[1], t[0]])
        base = np.array([CX[k], CY[k]])
        p = base + 8 * nn
        if not mask[int(round(cy - p[1])) % h, int(round(cx + p[0])) % w]:
            nn = -nn
        acc = np.zeros((len(depths), 3))
        offs = np.arange(-6, 7, 2.0)
        for o in offs:
            P = base[None, :] + depths[:, None] * nn[None, :] + o * t[None, :]
            acc += C.bilinear(rgb, cx + P[:, 0], cy - P[:, 1])
        prof = (acc / len(offs)) @ lumw
        # thickness available: stop where the profile leaves the mask
        insid = np.array([mask[int(round(cy - (base[1] + d * nn[1]))) % h, int(round(cx + (base[0] + d * nn[0]))) % w]
                          for d in depths])
        lastin = np.nonzero(~insid)[0]
        dmax = depths[lastin[0]] if len(lastin) else depths[-1]
        band = float(prof[(depths >= 2) & (depths <= 6)].mean())
        far_sel = (depths >= min(dmax - 12, 45)) & (depths <= min(dmax - 2, 58))
        far = float(prof[far_sel].mean()) if far_sel.sum() > 3 else float('nan')
        wdt = None
        if not math.isnan(far) and band - far > 0.05:
            half = (band + far) / 2
            kk = np.nonzero((depths > 3) & (depths < dmax) & (prof < half))[0]
            if len(kk):
                wdt = float(depths[kk[0]])
        out.append(dict(s=float(s0), s_frac=float(s0 / L), band_lum=band, face_lum=far,
                        thickness_px=float(dmax), band_width_px=wdt))
    return out, L


bands = {}
for q in range(4):
    Q = R1["quarters_contour_idx"][q]
    b, L = band_along(Q["tip"], Q["armend"])
    bands["q%d_outer" % q] = dict(edge_len=L, stations=b)
    # inner edge of the same hook for comparison
    Qp = R1["quarters_contour_idx"][(q - 1) % 4]
    b2, L2 = band_along(Qp["next_root"], Q["tip"])
    bands["q%d_hookinner" % q] = dict(edge_len=L2, stations=b2)
OUT["bevel_bands"] = bands

# ---------- hook width: linear fit vs fraction of hook length ----------
hooks = []
for a in R1["arms"]:
    f = np.array([p["f"] for p in a["hook_profile"]])
    wd = np.array([p["width"] for p in a["hook_profile"]])
    sel = (f >= 0.05) & (f <= 0.9)
    A = np.polyfit(f[sel], wd[sel], 1)
    hooks.append(dict(k=a["k"], root_width_extrapolated_px=float(A[1]), slope=float(A[0]),
                      width_at_5pct=float(wd[f == 0.05][0]), width_at_50pct=float(wd[f == 0.5][0]),
                      hook_len_px=a["hook_len_beyond_arm"]))
OUT["hook_width_fits"] = hooks

# ---------- ratio summary ----------
def stat(vals):
    v = np.array([x for x in vals if x is not None and not (isinstance(x, float) and math.isnan(x))], float)
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                min=float(v.min()), max=float(v.max()), n=int(len(v)), values=[float(x) for x in v])


arms = R1["arms"]
S = {}
S["span_px"] = SPAN
S["tip_radius_px"] = stat(R1["tips_radius_px"])
S["tip_angle_spacing_deg"] = stat(R1["tips_angle_spacing_deg"])
S["arm_width_at_root_ratio"] = stat([a["width_root"] / SPAN for a in arms])
S["arm_width_at_hookroot_ratio"] = stat([a["width_end"] / SPAN for a in arms])
S["arm_width_taper_total_deg"] = stat([a["taper_deg"] for a in arms])
S["hook_len_beyond_arm_ratio"] = stat([a["hook_len_beyond_arm"] / SPAN for a in arms])
S["hook_len_from_centreline_ratio"] = stat([a["hook_len_from_centreline"] / SPAN for a in arms])
S["hook_len_from_trailing_edge_ratio"] = stat([a["hook_len_from_trailing_edge"] / SPAN for a in arms])
S["hook_root_width_ratio"] = stat([hk["root_width_extrapolated_px"] / SPAN for hk in hooks])
S["hook_root_u_ratio"] = stat([a["u_root"] / SPAN for a in arms])
S["arm_outer_end_u_ratio"] = stat([a["u_end_centre"] / SPAN for a in arms])
S["tip_u_ratio"] = stat([a["u_tip"] / SPAN for a in arms])
S["tip_v_ratio"] = stat([a["v_tip"] / SPAN for a in arms])
S["hook_inner_edge_angle_to_arm_axis_deg"] = stat(
    [(e["idx_hookinner"]["angle_deg"] - a["axis_deg"]) % 180 for e, a in zip(R1["edge_fits"], arms)])
S["tip_angle_deg_window20_300"] = stat([t["20-300"] for t in R1["tip_angles"]])
S["tip_angle_deg_window15_150"] = stat([t["15-150"] for t in R1["tip_angles"]])
S["tip_angle_deg_window10_80"] = stat([t["10-80"] for t in R1["tip_angles"]])
S["tip_chord_angle_deg"] = stat([t["chord_root_armend"] for t in R1["tip_angles"]])
S["tip_width_10px_back"] = stat([t["width_behind_tip_px"]["10"] for t in R1["tip_angles"]])
S["tip_width_3px_back"] = stat([t["width_behind_tip_px"]["3"] for t in R1["tip_angles"]])
S["outer_edge_arc_radius_ratio"] = stat([f["radius_ratio_span"] for f in R2["outer_edge_arc_fits"]])
S["junction_radius_ratio"] = stat([m[1] / SPAN for m in R1["r_theta_local_minima_deg_px"]])
for kind in ("junction(concave)", "hook_root(concave)", "arm_end(convex)"):
    S["fillet_%s_ratio" % kind.split('(')[0]] = stat([f["fillet_ratio_span"] for f in fillets if f["kind"] == kind])
    S["fillet_%s_px" % kind.split('(')[0]] = stat([f["fillet_radius_px"] for f in fillets if f["kind"] == kind])
S["corner_angle_junction_deg"] = stat([f["angle_deg"] for f in fillets if f["kind"] == "junction(concave)"])
S["corner_angle_hookroot_deg"] = stat([f["angle_deg"] for f in fillets if f["kind"] == "hook_root(concave)"])
S["corner_angle_armend_deg"] = stat([f["angle_deg"] for f in fillets if f["kind"] == "arm_end(convex)"])
S["bbox_in_arm_frame_ratio"] = [R1["extent_along_mean_axes_px"]["width_u"] / SPAN,
                                R1["extent_along_mean_axes_px"]["width_v"] / SPAN]
S["across_arms_centreline_ratio"] = [v / SPAN for v in R1["across_arms_centreline_px"]]
S["area_ratio_span2"] = R1["area_px"] / SPAN ** 2
S["perimeter_ratio"] = R1["perimeter_px"] / SPAN
OUT["summary_ratios"] = S
json.dump(OUT, open(os.path.join(C.OUT, "measure3.json"), "w"), indent=1, default=float)

print("FILLETS")
for f in fillets:
    print("  %-20s angle %5.1f area %7.0f r=%5.1f px (%.4f span) gap %.1f" % (
        f["kind"], f["angle_deg"], f["area_px"], f["fillet_radius_px"], f["fillet_ratio_span"], f["vertex_gap_px"]))
print("BANDS (outer edges; s_frac from tip -> arm end; width in px)")
for k, v in bands.items():
    print("  ", k, "len %.0f" % v["edge_len"], [(round(s["s_frac"], 2), s["band_width_px"]) for s in v["stations"]])
print("HOOK width fits", [(hk["k"], round(hk["root_width_extrapolated_px"], 1), round(hk["slope"], 1)) for hk in hooks])
for k, v in S.items():
    if isinstance(v, dict):
        print("  %-42s mean %9.4f sd %7.4f  min %9.4f max %9.4f n %d" % (k, v["mean"], v["sd"], v["min"], v["max"], v["n"]))
    else:
        print("  %-42s %s" % (k, v))
