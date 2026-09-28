# Method B step 7 (final): silhouette primitives, tips, notch fillet fits, centre, ratios, bevel taper,
# star-polygon comparison, hole check. Inputs: b5_edges.json (station points), b1_segment.json, L.npy, rgb.npy
import sys, os, json, numpy as np
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour")
from common import *
rgb = np.load(os.path.join(OUT, "rgb.npy")).astype(np.float64)
L = np.load(os.path.join(OUT, "L.npy")).astype(np.float64)
Yc = (rgb[..., 0] + rgb[..., 1]) / 2 - rgb[..., 2]
H, W = L.shape
R = json.load(open(os.path.join(OUT, "b5_edges.json")))
seg = json.load(open(os.path.join(OUT, "b1_segment.json")))
names = list(R.keys())
out = dict(edges={}, tips={}, notches={}, notes=[])

def arr(key, e):
    return np.array(e[key], float)

# ------------------------------------------------------------------ yellowness boundary (for T5-N4)
def yellow_outer(e, step=2.0):
    m = np.array(e["outer_pt"]); dv = np.array(e["outer_dir"]); n = np.array(e["outer_n"])
    P = arr("pts_outer", e); P = P[~np.isnan(P[:, 0])]; s = (P - m) @ dv
    TS = np.arange(-12, 22.01, 0.25); SS = np.arange(-4, 4.01, 1.0); pts = []
    for s0 in np.arange(s.min(), s.max(), step):
        base = m + dv * s0
        xs = base[0] + TS[None, :] * n[0] + SS[:, None] * dv[0]; ys = base[1] + TS[None, :] * n[1] + SS[:, None] * dv[1]
        py = smooth1d(bil(Yc, xs, ys).mean(0), 1.0, 0.25)
        ybg = np.median(py[TS >= 14]); win = (TS >= -6) & (TS <= 8)
        i0 = np.nonzero(win)[0][np.argmax(py[win])]; ymax = py[i0]
        if ymax - ybg < 0.03: continue
        half = (ymax + ybg) / 2; j = i0
        while j < len(TS) - 1 and py[j] > half: j += 1
        if j >= len(TS) - 1: continue
        t = TS[j - 1] + (py[j - 1] - half) / (py[j - 1] - py[j]) * 0.25
        pts.append(base + n * t)
    return np.array(pts)

# ------------------------------------------------------------------ silhouette + crease lines per edge
SIL = {}; CREASE = {}; SILPTS = {}
for name in names:
    e = R[name]; u = np.array(e["outer_dir"]); n = np.array(e["outer_n"])
    Po = arr("pts_outer", e); Pf = arr("pts_face", e)
    f = np.array([s["f"] for s in e["stations"]]); band = np.array([s["band"] for s in e["stations"]])
    okO = ~np.isnan(Po[:, 0]); okF = ~np.isnan(Pf[:, 0])
    kind = "outer"
    if name == "T5-N4":
        P = yellow_outer(e); kind = "yellow_channel"
    elif name == "T0-N0":
        # dark bevel stripe visible (crisp outer boundary) only near the tip; shadow swallows it toward the notch.
        # taper model: outer points near the tip + face points where the bevel has run out (near the notch)
        P = np.vstack([Po[okO & (f < 0.35)], Pf[okF & (f > 0.75)]]); kind = "outer_near_tip+face_near_notch"
    elif name == "T3-N2":
        P = Pf[okF]; kind = "face_only(shadowed)"
    else:
        P = Po[okO]
    m, d, keep, res = robust_line(P)
    if np.dot(d, u) < 0: d = -d
    nn = np.array([-d[1], d[0]]);
    if np.dot(nn, n) < 0: nn = -nn
    SIL[name] = (m, d, nn); SILPTS[name] = P[keep]
    # crease line: face points only where a separate band was detected
    sel = okF & okO & (band > 1.5)
    crease = None
    if sel.sum() >= 12:
        mc, dc, kc, rc = robust_line(Pf[sel])
        if np.dot(dc, u) < 0: dc = -dc
        crease = (mc, dc, float(np.sqrt(np.mean(rc ** 2))), int(kc.sum()))
    CREASE[name] = crease
    # straightness
    s = (P[keep] - m) @ d; r = (P[keep] - m) @ nn
    c2 = np.polyfit(s, r, 2); sp = s.max() - s.min()
    out["edges"][name] = dict(normal=nn.tolist(), sil_kind=kind, sil_line=[m.tolist(), d.tolist()], n_pts=int(keep.sum()),
                              rms_px=float(np.sqrt(np.mean(res ** 2))), max_abs_res_px=float(np.max(np.abs(res))),
                              fitted_len_px=float(sp), sagitta_px=float(c2[0] * (sp / 2) ** 2 * -1),  # + = bulges outward
                              crease_line=([crease[0].tolist(), crease[1].tolist()] if crease else None),
                              crease_rms_px=(crease[2] if crease else None), crease_pts=(crease[3] if crease else 0))

# ------------------------------------------------------------------ tips
def profile_along(P0, dvec, t0, t1, half=0.5, dt=0.25, A=None):
    A = L if A is None else A
    TS = np.arange(t0, t1 + 1e-9, dt); nvec = np.array([-dvec[1], dvec[0]])
    SS = np.arange(-half, half + 1e-9, 0.5)
    xs = P0[0] + TS[None, :] * dvec[0] + SS[:, None] * nvec[0]; ys = P0[1] + TS[None, :] * dvec[1] + SS[:, None] * nvec[1]
    return TS, bil(A, xs, ys).mean(0)

TV = {}
for k in range(8):
    ea = "T%d-N%d" % (k, k); eb = "T%d-N%d" % (k, (k - 1) % 8)
    ma, da, na = SIL[ea]; mb, db, nb = SIL[eb]
    V = intersect(ma, da, mb, db)
    ua = da; ub = db   # both oriented tip -> notch
    alpha = angle_between(ua, ub)
    bis = -(ua + ub); bis /= np.linalg.norm(bis)
    TS, p = profile_along(V, bis, -45, 25, half=0.5)
    ps = smooth1d(p, 0.5, 0.25)
    inside = np.median(ps[(TS > -40) & (TS < -25)]); outside = np.median(ps[TS > 12])
    half = (inside + outside) / 2
    idx = np.nonzero(np.diff(np.sign(ps - half)) != 0)[0]
    tend = float(TS[idx[-1]] + 0.125) if len(idx) else float('nan')
    inimg = bool((0 <= V[0] < W) and (0 <= V[1] < H))
    # crease-based (flat face) tip angle where both creases exist
    ca, cb = CREASE[ea], CREASE[eb]
    alpha_face = angle_between(ca[1], cb[1]) if (ca and cb) else None
    TV[k] = V
    out["tips"][k] = dict(vertex=V.tolist(), included_angle_deg=alpha, face_crease_angle_deg=alpha_face, bisector=bis.tolist(),
                          end_offset_px=tend, end_pt=(V + bis * tend).tolist() if tend == tend else None,
                          vertex_in_image=inimg, edges=[ea, eb],
                          edge_kinds=[out["edges"][ea]["sil_kind"], out["edges"][eb]["sil_kind"]])

# ------------------------------------------------------------------ PSF estimate (erf fit on high-contrast lit steps near notches)
from math import erf
def erf_fit(TS, p):
    best = None
    for sg in np.arange(0.5, 4.01, 0.05):
        for t0 in np.arange(-4, 4.01, 0.1):
            model_shape = np.array([0.5 * (1 + erf((t - t0) / (sg * np.sqrt(2)))) for t in TS])
            A = np.c_[model_shape, np.ones(len(TS))]
            c, *_ = np.linalg.lstsq(A, p, rcond=None)
            r = np.sum((A @ c - p) ** 2)
            if best is None or r < best[0]: best = (r, sg, t0)
    return best[1], best[2]
psf = []
for name in ("T7-N6", "T4-N4", "T3-N3", "T6-N5"):
    m, d, nn = SIL[name]
    P = SILPTS[name]; s = (P - m) @ d
    for q in (0.80, 0.85, 0.9):
        base = m + d * np.quantile(s, q)
        TS, p = profile_along(base, nn, -8, 8, half=0.0, dt=0.25)
        # average along the edge +-6 px without smoothing
        acc = []
        for sh in np.arange(-6, 6.01, 1):
            TS, pp = profile_along(base + d * sh, nn, -8, 8, half=0.0, dt=0.25); acc.append(pp)
        psf.append(erf_fit(TS, np.mean(acc, 0))[0])
sig_psf = float(np.median(psf))
out["psf_sigma_px"] = dict(median=sig_psf, values=[float(v) for v in psf])

# simulate where the half level falls for a sharp blurred wedge (tip) and V notch, for the measured PSF
def sim_wedge(alpha_deg, sigma, notch=False):
    ss = 8; Nn = 120
    yy, xx = np.mgrid[0:Nn * ss, 0:Nn * ss] / ss - Nn / 2
    a = np.radians(alpha_deg / 2)
    wedge = (xx <= 0) & (np.abs(yy) <= -xx * np.tan(a))       # vertex at origin, opening toward -x
    img = wedge.astype(float) if not notch else (~wedge).astype(float)
    # gaussian blur via FFT at supersampled resolution
    s2 = sigma * ss
    ky = np.fft.fftfreq(img.shape[0]); kx = np.fft.fftfreq(img.shape[1])
    G = np.exp(-2 * np.pi ** 2 * s2 ** 2 * (ky[:, None] ** 2 + kx[None, :] ** 2))
    b = np.real(np.fft.ifft2(np.fft.fft2(img) * G))
    row = b[img.shape[0] // 2]; x = np.arange(img.shape[1]) / ss - Nn / 2
    lo, hi = row[x < -40].mean(), row[x > 40].mean()
    hlf = (lo + hi) / 2
    i = np.nonzero(np.diff(np.sign(row - hlf)) != 0)[0]
    i = i[np.argmin(np.abs(x[i]))]
    return float(x[i])
out["blur_sim"] = dict(tip_half_level_offset_px=sim_wedge(33.5, sig_psf), notch_half_level_offset_px=sim_wedge(78.5, sig_psf, notch=True))

# ------------------------------------------------------------------ notches: fillet model fit
def boundary_near(P0, nvec, half=2.0, span=(-14, 14), thr=0.035):
    TS, p = profile_along(P0, nvec, span[0], span[1], half=half)
    ps = smooth1d(p, 1.0, 0.25); d = np.gradient(ps, 0.25)
    cand = [dict(q, s=+1) for q in peaks(d, TS, thr, +1) if q["fwhm"] <= 6] + \
           [dict(q, s=-1) for q in peaks(d, TS, thr, -1) if q["fwhm"] <= 6]
    if not cand: return None
    return min(cand, key=lambda c: c["t"])          # innermost crisp step from the material side

def fillet_model_dist(P, V, ua, ub, beta, rho):
    # distance of points to (ray V+ua*s) U (ray V+ub*s) U fillet arc of radius rho (arc inside the empty wedge)
    bis = (ua + ub) / np.linalg.norm(ua + ub)
    if rho <= 0:
        da = np.abs((P - V) @ np.array([-ua[1], ua[0]])); db = np.abs((P - V) @ np.array([-ub[1], ub[0]]))
        return np.minimum(da, db)
    half = np.radians(beta / 2)
    C = V + bis * rho / np.sin(half); st = rho / np.tan(half)
    Ta = V + ua * st; Tb = V + ub * st
    dist = []
    for q in P:
        cands = []
        for Tt, uu in ((Ta, ua), (Tb, ub)):
            s = np.dot(q - Tt, uu)
            if s >= 0: cands.append(abs(np.dot(q - Tt, np.array([-uu[1], uu[0]]))))
        # arc part: the short arc Ta..Tb seen from C, i.e. the sector that contains the direction C->V
        v = q - C; ang = np.arctan2(v[1], v[0])
        a1 = np.arctan2(*(Ta - C)[::-1]); a2 = np.arctan2(*(Tb - C)[::-1]); am = np.arctan2(*(V - C)[::-1])
        def within(x, a, b):
            return ((x - a) % (2 * np.pi)) <= ((b - a) % (2 * np.pi))
        lo, hi = (a1, a2) if within(am, a1, a2) else (a2, a1)
        if within(ang, lo, hi):
            cands.append(abs(np.hypot(*v) - rho))
        cands.append(np.hypot(*(q - Ta))); cands.append(np.hypot(*(q - Tb)))
        dist.append(min(cands))
    return np.array(dist)

NV = {}
for k in range(8):
    ea = "T%d-N%d" % (k, k); eb = "T%d-N%d" % ((k + 1) % 8, k)
    ma, da, na = SIL[ea]; mb, db, nb = SIL[eb]
    V = intersect(ma, da, mb, db)
    ua = -da; ub = -db                          # from notch vertex toward the tips
    beta = angle_between(ua, ub)
    bis = (ua + ub) / np.linalg.norm(ua + ub)   # out of the notch (away from centre)
    pts = []; offs = {ea: [], eb: []}
    for name, uu, nrm in ((ea, ua, na), (eb, ub, nb)):
        for s in np.arange(1.0, 60.01, 1.0):
            P0 = V + uu * s
            c = boundary_near(P0, nrm)
            if c is not None and abs(c["t"]) < 13:
                pts.append(P0 + nrm * c["t"]); offs[name].append((float(s), float(c["t"]), c["s"]))
    # along the bisector
    cb = boundary_near(V, bis, half=1.0, span=(-10, 25))
    gap = cb["t"] if cb else float('nan')
    if cb: pts.append(V + bis * gap)
    pts = np.array(pts)
    # 1-D search for the fillet radius using points within 40 px of the vertex
    near = np.hypot(*(pts - V).T) <= 40
    Pn = pts[near]
    grid = np.arange(0, 40.01, 0.5)
    cost = [np.median(fillet_model_dist(Pn, V, ua, ub, beta, r)) for r in grid]
    ibest = int(np.argmin(cost)); rho = float(grid[ibest])
    # also a free circle fit to boundary points within the fillet zone (distance to vertex <= 1.6*rho+4)
    cf = None
    if rho > 0:
        zone = np.hypot(*(pts - V).T) <= 1.3 * rho / np.tan(np.radians(beta / 2)) + 3
        if zone.sum() >= 6:
            Cc, rr, cres = circle_fit(pts[zone]); cf = dict(radius_px=rr, rms_px=float(np.sqrt(np.mean(cres ** 2))), n=int(zone.sum()),
                                                           centre_along_bisector_px=float(np.dot(Cc - V, bis)))
    # mean offset of the boundary from the lines far from the vertex (checks line fidelity near the notch)
    far = {nm: float(np.median([o[1] for o in offs[nm] if 25 <= o[0] <= 60])) if any(25 <= o[0] <= 60 for o in offs[nm]) else None for nm in offs}
    NV[k] = V
    out["notches"][k] = dict(vertex=V.tolist(), opening_deg=beta, bisector=bis.tolist(), bottom_gap_px=gap,
                             bottom_pt=(V + bis * gap).tolist() if gap == gap else None,
                             bottom_step_sign=(cb["s"] if cb else None),
                             fillet_radius_px=rho, cost_sharp_px=float(cost[0]), cost_best_px=float(cost[ibest]),
                             fillet_from_gap_px=float(gap / (1 / np.sin(np.radians(beta / 2)) - 1)) if gap == gap else None,
                             free_circle=cf, far_offset_px=far, boundary_pts=pts.tolist(), edges=[ea, eb],
                             edge_kinds=[out["edges"][ea]["sil_kind"], out["edges"][eb]["sil_kind"]])

# ------------------------------------------------------------------ centre, span, ratios
tipsIn = [k for k in range(8) if out["tips"][k]["vertex_in_image"]]
TVa = np.array([TV[k] for k in range(8)]); NVa = np.array([NV[k] for k in range(8)])
Ct, Rt, rt = circle_fit(TVa[tipsIn]); Cn, Rn, rn = circle_fit(NVa)
C0 = Ct
span = 2 * Rt
opp = {"T%d-T%d" % (k, k + 4): float(np.hypot(*(TVa[k] - TVa[k + 4]))) for k in range(4)}
end_pts = {k: np.array(out["tips"][k]["end_pt"]) for k in tipsIn if out["tips"][k]["end_pt"]}
r_end = {k: float(np.hypot(*(p - C0))) for k, p in end_pts.items()}
out["centre"] = dict(tip_circle_centre=Ct.tolist(), tip_circle_R_px=Rt, tip_circle_rms_px=float(np.sqrt(np.mean(rt ** 2))),
                     tips_used=tipsIn, notch_circle_centre=Cn.tolist(), notch_circle_R_px=Rn,
                     notch_circle_rms_px=float(np.sqrt(np.mean(rn ** 2))), centre_offset_px=float(np.hypot(*(Ct - Cn))),
                     span_px=span, opposite_tip_vertex_dist_px=opp, r_tip_end_px=r_end)
for k in range(8):
    v = TVa[k] - C0
    t = out["tips"][k]; t["r_vertex_px"] = float(np.hypot(*v)); t["polar_deg"] = float(np.degrees(np.arctan2(-v[1], v[0])) % 360)
    bis = np.array(t["bisector"]); radu = v / np.linalg.norm(v)
    t["axis_skew_deg"] = float(np.degrees(np.arctan2(radu[0] * bis[1] - radu[1] * bis[0], np.dot(radu, bis))))
    t["r_vertex_ratio"] = t["r_vertex_px"] / span
    if k in r_end: t["r_end_ratio"] = r_end[k] / span
for k in range(8):
    v = NVa[k] - C0
    t = out["notches"][k]; t["r_vertex_px"] = float(np.hypot(*v)); t["polar_deg"] = float(np.degrees(np.arctan2(-v[1], v[0])) % 360)
    t["r_vertex_ratio"] = t["r_vertex_px"] / span
    if t["bottom_pt"]: t["r_bottom_ratio"] = float(np.hypot(*(np.array(t["bottom_pt"]) - C0))) / span
    t["fillet_ratio"] = t["fillet_radius_px"] / span

# ------------------------------------------------------------------ bevel taper per edge (silhouette vs crease)
for name in names:
    cr = CREASE[name]
    if not cr: continue
    m, d, nn = SIL[name]; mc, dc = cr[0], cr[1]
    k = R[name]["tip"]; V = TV[k]
    # distance along silhouette from tip vertex to the notch vertex
    nk = R[name]["notch"]; Vn = NV[nk]; Ledge = float(np.hypot(*(Vn - V)))
    taper = float(np.degrees(np.arcsin(abs(d[0] * dc[1] - d[1] * dc[0]))))
    # band width (perpendicular) as function of s from the tip vertex, from the two lines
    def band_at(s):
        P = V + d * s; # point on silhouette
        return float(np.dot(P - mc, np.array([-dc[1], dc[0]])) * np.sign(np.dot(np.array([-dc[1], dc[0]]), nn)))
    # measured band values (station-wise)
    e = R[name]; Po = arr("pts_outer", e); Pf = arr("pts_face", e)
    b = np.array([s["band"] for s in e["stations"]]); ok = (b > 1.5) & ~np.isnan(Po[:, 0]) & ~np.isnan(Pf[:, 0])
    ss = ((Po[ok] - V) @ d) / Ledge; bb = b[ok]
    try:
        run_out = (np.dot(intersect(m, d, mc, dc) - V, d)) / Ledge
    except Exception:
        run_out = None
    out["edges"][name].update(bevel=dict(taper_deg=taper, edge_len_px=Ledge,
        band_at_frac={("%.1f" % f): band_at(f * Ledge) for f in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)},
        run_out_frac_from_tip=(float(run_out) if run_out is not None else None),
        measured_band_px=dict(n=int(ok.sum()), frac_min=float(ss.min()) if ok.any() else None, frac_max=float(ss.max()) if ok.any() else None,
                              max=float(bb.max()) if ok.any() else None, median=float(np.median(bb)) if ok.any() else None)))

# ------------------------------------------------------------------ star polygon comparison
alphas = np.array([out["tips"][k]["included_angle_deg"] for k in range(8)])
betas = np.array([out["notches"][k]["opening_deg"] for k in range(8)])
rho_ratio = Rn / Rt
def tip_angle_from_rho(r):
    return 2 * np.degrees(np.arctan(r * np.sin(np.pi / 8) / (1 - r * np.cos(np.pi / 8))))
def rho_from_k(k):
    return np.cos(np.pi * k / 8) / np.cos(np.pi * (k - 1) / 8)
kk = np.linspace(2, 3.9, 20000); rk = rho_from_k(kk)
k_from_rho = float(kk[np.argmin(np.abs(rk - rho_ratio))])
out["star"] = dict(rho_notch_over_tip=rho_ratio, tip_angle_regular_for_rho=tip_angle_from_rho(rho_ratio),
                   k_equiv_from_rho=k_from_rho, k_equiv_from_tip_angle=float((180 - np.median(alphas)) / 45),
                   ref={"8/2": dict(rho=rho_from_k(2), tip=90.0, notch=135.0), "8/3": dict(rho=rho_from_k(3), tip=45.0, notch=90.0)},
                   tip_angle_median=float(np.median(alphas)), notch_opening_median=float(np.median(betas)),
                   check_beta_minus_alpha=float(np.median(betas) - np.median(alphas)))

# ------------------------------------------------------------------ hole check
holes = seg["holes"]
hd = [dict(area=h["area"], r_ratio=float(np.hypot(h["cx"] - C0[0], h["cy"] - C0[1]) / span)) for h in holes]
yy, xx = np.mgrid[0:H, 0:W]
rr = np.hypot(xx - C0[0], yy - C0[1])
central = L[rr < 0.2 * span]
out["holes"] = dict(enclosed_background_specks=len(holes), largest_area_px=max(h["area"] for h in holes) if holes else 0,
                    min_r_ratio=min(h["r_ratio"] for h in hd) if hd else None,
                    central_disc_r_ratio=0.2, central_L_p99=float(np.percentile(central, 99)), central_frac_L_gt_0p5=float((central > 0.5).mean()))
json.dump(out, open(os.path.join(OUT, "b7_results.json"), "w"), indent=1, default=float)

# ------------------------------------------------------------------ print
print("PSF sigma", out["psf_sigma_px"], "blur sim", out["blur_sim"])
print("centre", {k: v for k, v in out["centre"].items()})
for name in names:
    e = out["edges"][name]
    bv = e.get("bevel")
    print("%-6s %-32s n=%3d rms %.2f max %.2f sag %+.2f len %.0f | crease %s | %s" % (
        name, e["sil_kind"], e["n_pts"], e["rms_px"], e["max_abs_res_px"], e["sagitta_px"], e["fitted_len_px"],
        ("%.2f/%d" % (e["crease_rms_px"], e["crease_pts"])) if e["crease_line"] else "-",
        ("taper %.2f runout %.2f band@0.1 %.1f @0.3 %.1f @0.5 %.1f meas max %.1f med %.1f f[%.2f..%.2f]" % (
            bv["taper_deg"], bv["run_out_frac_from_tip"], bv["band_at_frac"]["0.1"], bv["band_at_frac"]["0.3"], bv["band_at_frac"]["0.5"],
            bv["measured_band_px"]["max"], bv["measured_band_px"]["median"], bv["measured_band_px"]["frac_min"], bv["measured_band_px"]["frac_max"])) if bv else "-"))
for k in range(8):
    t = out["tips"][k]
    print("T%d r=%.1f (%.4f) polar %.2f alpha %.2f face %s end %.1f skew %+.2f inimg %s %s" % (
        k, t["r_vertex_px"], t["r_vertex_ratio"], t["polar_deg"], t["included_angle_deg"],
        ("%.2f" % t["face_crease_angle_deg"]) if t["face_crease_angle_deg"] else "-", t["end_offset_px"], t["axis_skew_deg"], t["vertex_in_image"], t["edge_kinds"]))
for k in range(8):
    t = out["notches"][k]
    print("N%d r=%.1f (%.4f) polar %.2f beta %.2f gap %.2f(%s) rho %.1f cost0 %.2f costbest %.2f rho_gap %s free %s far %s" % (
        k, t["r_vertex_px"], t["r_vertex_ratio"], t["polar_deg"], t["opening_deg"], t["bottom_gap_px"], t["bottom_step_sign"],
        t["fillet_radius_px"], t["cost_sharp_px"], t["cost_best_px"], ("%.1f" % t["fillet_from_gap_px"]) if t["fillet_from_gap_px"] else "-",
        ("%.1f/%.2f/%+.1f" % (t["free_circle"]["radius_px"], t["free_circle"]["rms_px"], t["free_circle"]["centre_along_bisector_px"])) if t["free_circle"] else "-",
        t["far_offset_px"]))
print("star", out["star"])
print("holes", out["holes"])
