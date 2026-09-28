"""Editor pass on the synthesis (run AFTER s2_synthesis.py, BEFORE s6_contact.py).
Run: blender -b --factory-startup --python s5_fix.py
 1. Rebuilds the juji outline cleanly: smoothed station profile, exact R 5.5 mm crotch fillet tangent to both arms with
    its nearest point at 7.57 mm (0.078 of the 97 mm span), a 67 deg straight tip over the last 4.85 mm to a sharp apex,
    exact C4 + mirror symmetry, even arc-length resampling (no decimation). Re-runs area, mass, IoU.
 2. Rotates the senban outline and both holes 45 deg so a corner sits on +X (study section 4 pivot rule).
 3. IoU for the variants actually recommended (happo with its kept 9.5 mm hole, senban with the kept 12.7 mm hole).
 4. Senban bevel volume under a stated chamfer assumption.
 5. Roppo spec overlay re-placed at 98 mm apex to apex (same convention as the photo-matched panel).
 6. QA on every outline: turning angles, reversals, self-intersection, symmetry.
Reads only photo_study/* and References/Shuriken/images/*; writes only photo_study/synthesis/*.
Idempotent: the s2 originals are kept as fix/*_before_s5.json and read from there; delete them after re-running s2."""
import bpy, numpy as np, json, math, os, sys

P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
OUT = P + "synthesis/"
FIX = OUT + "fix/"
IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/"
RHO_STEEL = 7.85e-3
os.makedirs(FIX, exist_ok=True)
# shared helpers (load_rgb, save_png, densify, stamp, raster, shoelace, place, rot, circle, fillet, rounded_square, iou)
exec(open(OUT + "s2_synthesis.py").read().split("R = {}   # results")[0].split("# ------------------------------------------------------------------ io helpers")[1])

_bn, _bo = FIX + "synthesis_numbers_before_s5.json", FIX + "photo_matched_outlines_mm_before_s5.json"
if not os.path.exists(_bn):   # first run: keep s2 originals so this script stays idempotent
    import shutil; shutil.copy(OUT + "synthesis_numbers.json", _bn); shutil.copy(OUT + "photo_matched_outlines_mm.json", _bo)
N = json.load(open(_bn))
OL = json.load(open(_bo))
DRY = "--dry" in sys.argv

# ------------------------------------------------------------------ QA helpers
def turn_angles(p):
    """signed turning angle (deg) at each vertex of a closed loop; + = left turn (convex for a CCW loop)"""
    a = np.roll(p, 1, 0); b = p; c = np.roll(p, -1, 0)
    d1 = b - a; d2 = c - b
    cr = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]; dt = (d1 * d2).sum(1)
    return np.degrees(np.arctan2(cr, dt))

def self_intersections(p):
    q = np.vstack([p, p[:1]]); A = q[:-1]; B = q[1:]; n = len(A); hits = 0
    for i in range(n):
        a, b = A[i], B[i]
        j = np.arange(n); m = (j != i) & (j != (i + 1) % n) & (j != (i - 1) % n)
        c, d = A[m], B[m]
        def orient(p1, p2, p3):
            return (p2[..., 0] - p1[..., 0]) * (p3[..., 1] - p1[..., 1]) - (p2[..., 1] - p1[..., 1]) * (p3[..., 0] - p1[..., 0])
        o1 = orient(a, b, c); o2 = orient(a, b, d); o3 = orient(c, d, a); o4 = orient(c, d, b)
        hits += int(((o1 * o2 < 0) & (o3 * o4 < 0)).sum())
    return hits // 2

def qa(name, p, sharp_expected):
    t = turn_angles(p)
    L = np.hypot(*np.diff(np.vstack([p, p[:1]]), axis=0).T)
    big = np.where(np.abs(t) > 30)[0]
    rev = int((np.abs(t) > 120).sum())
    return dict(name=name, n=int(len(p)), seg_min_mm=float(L.min()), seg_max_mm=float(L.max()),
                turns_over_30deg=int(len(big)), turns_over_120deg=rev, sharp_corners_expected=sharp_expected,
                max_abs_turn_deg=float(np.abs(t).max()), concave_turns_over_30deg=int((t[big] < 0).sum()),
                self_intersections=self_intersections(p), signed_area_mm2=float(shoelace(p)))

def sym_err(p, k_fold, mirror=True):
    """max distance from each point of the rotated / mirrored loop to the nearest original point"""
    from_ = []
    for k in range(1, k_fold):
        q = rot(p, 360.0 * k / k_fold)
        d = np.sqrt(((q[:, None, :] - p[None, :, :]) ** 2).sum(-1)).min(1); from_.append(d.max())
    if mirror:
        q = p * np.array([1, -1]); d = np.sqrt(((q[:, None, :] - p[None, :, :]) ** 2).sum(-1)).min(1); from_.append(d.max())
    return float(max(from_))

# ================================================================== 1. JUJI rebuild
Rm = 48.5                       # model apex radius, mm (SOURCED 97 mm span, taken apex to apex)
TIP_INCL = 67.0                 # deg, reconciled 66.5 +- 2.5 over the last 5 % of span
TIP_LEN = 0.05 * 97.0           # 4.85 mm straight tip
R_FIL = 5.5                     # mm, reconciled 0.057 +- 0.007 span
D_NEAR = 0.078 * 97.0           # 7.566 mm, reconciled 0.078 +- 0.002 span
raw = np.load(OUT + "juji_profile_raw.npy")       # u/R_phys, h/R_phys (median of 8 sides)
g, h8 = raw[:, 0], raw[:, 1]
ok = np.isfinite(h8)
sig = 12                                          # 0.012 R gaussian
k = np.arange(-4 * sig, 4 * sig + 1); w = np.exp(-k ** 2 / (2.0 * sig ** 2))
hs = np.convolve(np.where(ok, h8, 0.0), w, 'same') / np.maximum(np.convolve(ok.astype(float), w, 'same'), 1e-9)
hs[~ok] = np.nan
# straight tip line of fixed 67 deg fitted to the raw median over 0.90-0.97 R (the last 3 % is scan blur)
tq = math.tan(math.radians(TIP_INCL / 2))
sel = (g >= 0.90) & (g <= 0.97) & ok
c0 = float(np.mean(h8[sel] + tq * g[sel]))
u_apex = c0 / tq                                   # virtual apex, R_phys units
KS = Rm / u_apex                                   # model mm per R_phys
# The gaussian-smoothed median still wiggles (13 curvature sign changes between 0.19 and 0.91 R). A degree-8
# Chebyshev least-squares fit over that range keeps one inflection (0.528 R, reconciled 0.53 +- 0.04), rms 0.03 mm,
# max 0.08 mm from the smoothed median: that is the "smoothed station profile" the outline is built from.
FIT_LO, FIT_HI, FIT_DEG = 0.19, 0.91, 8
CH = np.polynomial.chebyshev
fm = (g >= FIT_LO) & (g <= FIT_HI) & ok
cheb = CH.chebfit(g[fm], hs[fm], FIT_DEG)
cheb_rms = float(np.sqrt(np.mean((CH.chebval(g[fm], cheb) - hs[fm]) ** 2)))
cheb_maxdev = float(np.abs(CH.chebval(g[fm], cheb) - hs[fm]).max())
def f_meas(x):                                     # fitted measured half-width, model mm
    return KS * CH.chebval(np.asarray(x) / KS, cheb)
def f_smooth(x):                                   # gaussian-smoothed median (for deviation checks only)
    return KS * np.interp(np.asarray(x) / KS, g[ok], hs[ok])
def df_meas(x, e=0.05):
    return (f_meas(x + e) - f_meas(x - e)) / (2 * e)
def hermite(x, x0, y0, m0, x1, y1, m1):
    t = (x - x0) / (x1 - x0); hh = x1 - x0
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * y0 + (t ** 3 - 2 * t ** 2 + t) * hh * m0 +
            (-2 * t ** 3 + 3 * t ** 2) * y1 + (t ** 3 - t ** 2) * hh * m1)
def d2hermite(x, x0, y0, m0, x1, y1, m1):
    t = (x - x0) / (x1 - x0); hh = x1 - x0
    return ((12 * t - 6) * y0 + (6 * t - 4) * hh * m0 + (-12 * t + 6) * y1 + (6 * t - 2) * hh * m1) / hh ** 2
# crotch fillet: centre on the 45 deg diagonal, nearest point to the centre at D_NEAR
cc = (D_NEAR + R_FIL) / math.sqrt(2)
def arc_pt(phi):
    return np.array([cc + R_FIL * math.cos(phi), cc + R_FIL * math.sin(phi)])
best = None
for phT in np.radians(np.arange(228.0, 268.01, 0.25)):
    T = arc_pt(phT); mT = -1.0 / math.tan(phT)
    for xB in np.arange(round(FIT_LO * KS + 0.1, 1), 15.01, 0.1):
        xs = np.linspace(T[0], xB, 200)
        yh = hermite(xs, T[0], T[1], mT, xB, f_meas(xB), df_meas(xB))
        d2 = d2hermite(xs, T[0], T[1], mT, xB, f_meas(xB), df_meas(xB))
        if d2.min() < 0: continue                  # must stay concave (curving away from the metal) through the flank
        dev = np.abs(yh - f_smooth(xs)).max()
        if best is None or dev < best[0]: best = (dev, phT, xB)
dev_crotch, phT, xB = best
T = arc_pt(phT); mT = -1.0 / math.tan(phT)
# tip blend
x2 = Rm - TIP_LEN; y2 = TIP_LEN * tq
best = None
for x1 in np.arange(36.0, FIT_HI * KS - 0.1, 0.1):
    xs = np.linspace(x1, x2, 200)
    yh = hermite(xs, x1, f_meas(x1), df_meas(x1), x2, y2, -tq)
    d2 = d2hermite(xs, x1, f_meas(x1), df_meas(x1), x2, y2, -tq)
    if d2.max() > 0: continue                      # convex leaf edge only
    dev = np.abs(yh - f_smooth(xs)).max()
    if best is None or dev < best[0]: best = (dev, x1)
dev_tip, x1 = best
xD = D_NEAR / math.sqrt(2)
def h_final(x):
    x = np.atleast_1d(np.asarray(x, float)); y = np.empty_like(x)
    a = x <= T[0]
    # arc: x = cc + R cos(phi) with phi in [225, phT] -> lower branch
    y[a] = cc - np.sqrt(np.maximum(R_FIL ** 2 - (x[a] - cc) ** 2, 0))
    b = (x > T[0]) & (x <= xB); y[b] = hermite(x[b], T[0], T[1], mT, xB, f_meas(xB), df_meas(xB))
    c = (x > xB) & (x <= x1); y[c] = f_meas(x[c])
    d = (x > x1) & (x <= x2); y[d] = hermite(x[d], x1, f_meas(x1), df_meas(x1), x2, y2, -tq)
    e = x > x2; y[e] = (Rm - x[e]) * tq
    return y
# dense edge from D (on the diagonal) to the apex; the arc part is sampled in angle
phis = np.linspace(math.radians(225.0), phT, 400)
arcp = np.array([arc_pt(p) for p in phis])
xs = np.concatenate([np.linspace(T[0], Rm, 40000)[1:]])
dense = np.vstack([arcp, np.stack([xs, h_final(xs)], 1)])
dense[0] = [xD, xD]; dense[-1] = [Rm, 0.0]
sL = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(dense, axis=0).T))])
L_edge = sL[-1]
n_seg = int(round(L_edge / 0.2))
st = np.linspace(0, L_edge, n_seg + 1)
edge = np.stack([np.interp(st, sL, dense[:, 0]), np.interp(st, sL, dense[:, 1])], 1)   # D -> apex, evenly spaced
edge[0] = [xD, xD]; edge[-1] = [Rm, 0.0]
up = edge[::-1]                                    # apex(+X) -> D   (CCW)
mir = edge[:, ::-1]                                # D -> apex(+Y)   (mirror across the diagonal)
quad = np.vstack([up, mir[1:-1]])                  # apex_X ... D ... (apex_Y excluded)
juji_mm = np.vstack([rot(quad, 90 * k) for k in range(4)])
A_juji = abs(shoelace(juji_mm))
r_all = np.hypot(juji_mm[:, 0], juji_mm[:, 1])
# chord angle at the crotch over +-1 mm of arc
i_d = len(up) - 1
nb = int(round(1.0 / (L_edge / n_seg)))
v1 = juji_mm[i_d - nb] - juji_mm[i_d]; v2 = juji_mm[i_d + nb] - juji_mm[i_d]
chord_ang = math.degrees(math.acos(v1 @ v2 / np.linalg.norm(v1) / np.linalg.norm(v2)))
# station table from the final profile
fine = np.linspace(xD, Rm, 20001); hf = h_final(fine)
iN = np.argmin(np.where((fine > 10) & (fine < 25), hf, 1e9)); iX = np.argmax(np.where((fine > 25) & (fine < 45), hf, -1e9))
curv = np.gradient(np.gradient(hf, fine), fine)
sm = np.convolve(curv, np.ones(201) / 201, 'same')
iI = iN + int(np.argmax(np.gradient(hf, fine)[iN:iX]))      # steepest point between neck and blade = inflection
# curvature sign changes along the edge (expect exactly one: concave flank -> convex leaf)
d2f = np.gradient(np.gradient(hf, fine), fine)
kb = int(round(0.5 / (fine[1] - fine[0])))
d2s = np.convolve(d2f, np.ones(2 * kb + 1) / (2 * kb + 1), 'same')
segm_ = (fine > xD + 0.6) & (fine < x2 - 0.6)
sg = np.sign(d2s[segm_]); xg = fine[segm_]; nz = sg != 0
chg = np.where(np.diff(sg[nz]) != 0)[0]
curv_sign_changes = [float(xg[nz][i]) for i in chg]
stations = {}
for uR in (0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.98, 1.0):
    x = uR * Rm; stations["%.2f" % uR] = dict(u_mm=round(x, 2), width_mm=round(2 * float(h_final(x)[0]), 2),
                                             width_over_span=round(2 * float(h_final(x)[0]) / 97.0, 4))
# alternative reading: 97 mm is the blunt physical tip to tip
k_alt = u_apex
# IoU against the reconciled photo contour (method B edge)
im = load_rgb(IMG + "Juji.JPG"); H, W, _ = im.shape
cenJ = np.array([694.10, 651.11]); R_phys_px = 662.45
scJ = R_phys_px / KS                              # px per model mm
pj = place(juji_mm, cenJ, scJ, 1.70)
cont = np.load(P + "juji/contour/contour_refined.npy").astype(float)
mJ = raster([cont], W, H); mP = raster([pj], W, H)
iou_j = iou(mJ, mP)
# the photographed piece's individual crotches and tips, in model mm (photo contour mapped through the same placement)
qq = cont - cenJ; qq[:, 1] = -qq[:, 1]
ca_, sa_ = math.cos(math.radians(-1.70)), math.sin(math.radians(-1.70))
cm_ = np.stack([ca_ * qq[:, 0] - sa_ * qq[:, 1], sa_ * qq[:, 0] + ca_ * qq[:, 1]], 1) / scJ
rr_ = np.hypot(cm_[:, 0], cm_[:, 1]); tt_ = np.degrees(np.arctan2(cm_[:, 1], cm_[:, 0])) % 360
def _near(d, win): return np.abs(((tt_ - d + 180) % 360) - 180) < win
photo_crotch_each = {str(d): float(rr_[_near(d, 20)].min()) for d in (45, 135, 225, 315)}
photo_tip_each = {str(d): float(rr_[_near(d, 3)].max()) for d in (0, 90, 180, 270)}
old = N["juji"]
J = dict(
    span_mm=97.0, span_convention="apex to apex; the 67 deg flanks extended meet %.3f R beyond the scan's blurred physical tip" % (u_apex - 1),
    thickness_mm=3.0, R_mm=Rm, photo_R_phys_over_model_R=float(1 / u_apex), model_mm_per_photo_R=KS,
    crotch_nearest_mm=float(r_all.min()), crotch_nearest_over_span=float(r_all.min() / 97.0),
    crotch_fillet_R_mm=R_FIL, crotch_fillet_centre_mm=[cc, cc], crotch_fillet_tangent_point_mm=[float(T[0]), float(T[1])],
    crotch_fillet_end_angle_deg=float(math.degrees(phT)), crotch_blend_to_measured_at_mm=float(xB),
    crotch_blend_max_dev_from_measured_mm=float(dev_crotch), crotch_chord_angle_at_pm1mm_deg=chord_ang,
    neck_min_u_mm=float(fine[iN]), neck_min_uR=float(fine[iN] / Rm), neck_min_width_mm=float(2 * hf[iN]),
    neck_min_over_span=float(2 * hf[iN] / 97.0),
    blade_max_u_mm=float(fine[iX]), blade_max_uR=float(fine[iX] / Rm), blade_max_width_mm=float(2 * hf[iX]),
    blade_max_over_span=float(2 * hf[iX] / 97.0),
    inflection_u_mm=float(fine[iI]), inflection_uR=float(fine[iI] / Rm),
    curvature_sign_changes_at_mm=curv_sign_changes,
    tip_included_deg=TIP_INCL, tip_straight_from_mm=x2, tip_straight_length_mm=TIP_LEN,
    tip_blend_from_mm=float(x1), tip_blend_max_dev_from_measured_mm=float(dev_tip),
    stations=stations, area_mm2=A_juji, area_over_span2=A_juji / 97.0 ** 2,
    mass_g_at_3mm=A_juji * 3.0 * RHO_STEEL,
    sourced_object_mass_g=39.0, mass_gap_g=A_juji * 3.0 * RHO_STEEL - 39.0,
    thickness_that_would_give_39g_mm=39.0 / (A_juji * RHO_STEEL),
    alt_if_97mm_is_blunt_physical_span=dict(scale=k_alt, area_mm2=A_juji * k_alt ** 2,
                                            mass_g_at_3mm=A_juji * k_alt ** 2 * 3.0 * RHO_STEEL),
    iou_vs_reconciled_mask=iou_j,
    photo_crotch_nearest_mm_each_deg=photo_crotch_each, photo_blurred_tip_radius_mm_each_deg=photo_tip_each,
    measured_area_over_physical_span2=old.get("measured_area_over_span2"),
    model_area_over_physical_span2=A_juji / (2 * KS) ** 2,
    edge_points_per_quadrant=int(len(quad)), resample_step_mm=float(L_edge / n_seg),
    symmetry_max_err_mm=None, previous_outline=dict(area_mm2=old["area_mm2"], mass_g_at_3mm=old["mass_g_at_3mm"],
                                                     iou=old["iou_vs_reconciled_mask"], crotch_nearest_mm=old["crotch_nearest_mm"]),
)
J["symmetry_max_err_mm"] = sym_err(juji_mm, 4, True)
xx = np.linspace(T[0], x2, 4000)
J["profile_fit"] = dict(method="degree-%d Chebyshev least squares of the gaussian (0.012 R) smoothed 8-side median, %.2f-%.2f R_phys"
                        % (FIT_DEG, FIT_LO, FIT_HI), fit_rms_mm=cheb_rms * KS, fit_max_dev_mm=cheb_maxdev * KS,
                        final_vs_smoothed_max_dev_mm_tangent_to_tip=float(np.abs(h_final(xx) - f_smooth(xx)).max()),
                        final_vs_smoothed_max_dev_mm_in_crotch_arc=float(np.abs(h_final(np.linspace(xD, T[0], 400)) - f_smooth(np.linspace(xD, T[0], 400))).max()))
print(json.dumps({k: v for k, v in J.items() if k != "stations"}, indent=1, default=float))
for kk, vv in stations.items(): print(kk, vv)
if DRY: raise SystemExit

# overlays + 4x crops at the critic's windows
o = im * 0.72 + 0.14
stamp(o, pj, (0.0, 1.0, 1.0), 2.6)
save_png(o, OUT + "juji_photo_matched.png")
for (x0, y0, x1_, y1_), nm in (((680, 480, 860, 660), "juji_crotch_TR"), ((540, 640, 720, 820), "juji_crotch_BL"),
                               ((1180, 560, 1370, 720), "juji_tip_R"), ((600, 0, 800, 160), "juji_tip_T")):
    o2 = im[y0:y1_, x0:x1_] * 0.72 + 0.14
    o2 = np.repeat(np.repeat(o2, 4, 0), 4, 1).copy()
    q = (pj - np.array([x0, y0])) * 4 + 1.5
    stamp(o2, q, (0.0, 1.0, 1.0), 2.2)
    save_png(o2, FIX + nm + "_rebuilt_4x.png")

# ================================================================== 2-4. HAPPO / SENBAN variants
Rh, rho = 50.0, 0.4576; rn = rho * Rh; fil = 0.0124 * 100.0
V = []
for kk in range(8):
    a = math.radians(45 * kk); V.append((Rh * math.cos(a), Rh * math.sin(a)))
    b = math.radians(45 * kk + 22.5); V.append((rn * math.cos(b), rn * math.sin(b)))
V = np.array(V); star = []
for i in range(16):
    star.append(V[i:i + 1] if i % 2 == 0 else fillet(V[i - 1], V[i], V[(i + 1) % 16], fil, 40))
star = np.vstack(star)
imH = load_rgb(IMG + "Happo.JPG"); Hh, Wh, _ = imH.shape
cenH = np.array([610.95, 638.76]); scH = 632.15 / Rh
ph_ = place(star, cenH, scH, 27.67); phh = place(circle(0, 0, 9.5 / 2), cenH, scH, 0)
mk = load_rgb(P + "happo/happo_reconciled_mask.png")[..., 0] > 0.75
iou_h_hole = iou(mk, raster([ph_, phh], Wh, Hh)); iou_h_nohole = iou(mk, raster([ph_], Wh, Hh))

c = 76.2; s_ph = 0.0616 * c
def senban_outline(c, s, n=400):
    Rarc = (c * c / 4 + s * s) / (2 * s); pts = []
    corners = [(c / 2, -c / 2), (c / 2, c / 2), (-c / 2, c / 2), (-c / 2, -c / 2)]
    for i in range(4):
        a = np.array(corners[i]); b = np.array(corners[(i + 1) % 4])
        mid = (a + b) / 2; out = mid / np.linalg.norm(mid); cen = mid - out * (s - Rarc)
        a1 = math.atan2(a[1] - cen[1], a[0] - cen[0]); a2 = math.atan2(b[1] - cen[1], b[0] - cen[0])
        while a2 - a1 > math.pi: a2 -= 2 * math.pi
        while a1 - a2 > math.pi: a2 += 2 * math.pi
        for t in np.linspace(a1, a2, n)[:-1]: pts.append(cen + Rarc * np.array([math.cos(t), math.sin(t)]))
    return np.array(pts), Rarc
sen, Rarc = senban_outline(c, s_ph)
sen45 = rot(sen, 45.0)                              # corner on +X
hf_ = N["senban"]["hole_fillet_mm"]; hole_src = 12.7; hole_ph = N["senban"]["hole_photo_mm"]
hs_src = rot(rounded_square(hole_src, hf_), 45.0); hs_ph = rot(rounded_square(hole_ph, hf_), 45.0)
imS = load_rgb(IMG + "Senban.jpg"); Hs, Ws, _ = imS.shape
cenS = np.array([505.3, 476.8]); scS = 852.3 / c; rS = 2.45 - 45.0
ps = place(sen45, cenS, scS, rS); phs = place(hs_src, cenS, scS, rS); php = place(hs_ph, cenS, scS, rS)
mk = load_rgb(P + "senban/contour/senban_mask.png")[..., 0] > 0.75
iou_s_src = iou(mk, raster([ps, phs], Ws, Hs)); iou_s_ph = iou(mk, raster([ps, php], Ws, Hs))
o = imS * 0.72 + 0.14; stamp(o, ps, (0.0, 1.0, 1.0), 2.4); stamp(o, php, (0.0, 1.0, 1.0), 2.0, dashed=10); stamp(o, phs, (1.0, 0.85, 0.0), 2.4)
save_png(o, OUT + "senban_photo_matched.png")
per = float(np.hypot(*np.diff(np.vstack([sen, sen[:1]]), axis=0).T).sum())
bev_w = N["senban"]["bevel_plan_mm"]
def bevel_g(depth, faces): return 0.5 * bev_w * depth * per * faces * RHO_STEEL
bevel = dict(assumption="plain chamfer of right-triangle section, %.2f mm wide in plan (measured) by an ASSUMED depth, "
                        "run along the outer perimeter only; a plan scan gives neither the depth, the profile nor the far face" % bev_w,
             perimeter_mm=per, plan_width_mm=bev_w,
             g_half_depth_one_face=bevel_g(0.95, 1), g_full_depth_one_face=bevel_g(1.9, 1), g_half_depth_both_faces=bevel_g(0.95, 2))

# ================================================================== 5. ROPPO spec at 98 mm apex to apex
imR = load_rgb(IMG + "Roppo.JPG"); HR, WR, _ = imR.shape
S_obs = 1177.0; C_R = np.array([629.0, 528.3]); ROT_R = 1.595
R_APEX = 0.514 * S_obs
K = 2 * R_APEX / 98.0                              # px per mm, apex to apex = 98 mm (as the photo-matched panel)
hub_r, half, tipR, tip_deg, hole_r = 18.0, 5.5, 49.0, 38.0, 4.0
taper = half / math.tan(math.radians(tip_deg / 2)); t_start = tipR - taper; t_root = math.sqrt(hub_r ** 2 - half ** 2)
spec = []
be = math.degrees(math.asin(half / hub_r))
for kk in range(6):
    ph = 60 * kk
    spec.append(rot(np.array([[t_root, -half], [t_start, -half], [tipR, 0.0], [t_start, half], [t_root, half]]), ph))
    aa = np.radians(np.linspace(ph + be, ph + 60 - be, 60))[1:-1]
    spec.append(np.stack([hub_r * np.cos(aa), hub_r * np.sin(aa)], 1))
spec = np.vstack(spec)
o = np.clip(imR, 0, 1) * 0.92
RED = (1.0, 0.15, 0.15); ORA = (1.0, 0.6, 0.0)
stamp(o, place(spec, C_R, K, ROT_R), RED, 2.6)
stamp(o, place(circle(0, 0, hole_r), C_R, K, 0), ORA, 2.6)
for kk in range(6):
    seg_ = rot(np.array([[t_start, -half], [t_start, half]]), 60 * kk)
    stamp(o, place(np.vstack([seg_, seg_[::-1]]), C_R, K, ROT_R), (1.0, 0.8, 0.4), 1.2)
save_png(o, OUT + "roppo_spec_at_apex_span.png")
A_spec_ro = abs(shoelace(spec)) - math.pi * hole_r ** 2

# ================================================================== 6. QA on every delivered outline + JSON
outl = dict(OL)
outl["note"] = ("Photo-matched plan outlines in mm at the study's sourced sizes. Blender top view: +Z to the viewer, X right, Y up. "
                "Outer loops CCW, evenly resampled. Holes listed separately. Un-bevelled plan outline only. "
                "Orientation per study section 4 (+X at one tip): juji, happo and roppo have a tip on +X; the senban has a corner "
                "on +X; the manji has an ARM AXIS on +X (its tips sit 35.0 deg counter-clockwise of each arm axis), which keeps "
                "its handedness gate readable (hook on the +X arm at +Y). Rebuilt by synthesis/s5_fix.py.")
outl["juji"] = dict(outer=[[round(float(x), 5), round(float(y), 5)] for x, y in juji_mm],
                    orientation="tip on +X, D4 symmetric (C4 + mirror)",
                    fundamental_edge_D_to_apex_mm=[[round(float(x), 5), round(float(y), 5)] for x, y in edge],
                    half_profile_uR_hR=[[round(float(u), 4), round(float(h_final(u * Rm)[0] / Rm), 5)]
                                        for u in np.arange(math.ceil(xD / Rm * 200) / 200, 1.0001, 0.005)],
                    R_mm=Rm, crotch_fillet=dict(R_mm=R_FIL, centre_mm=[round(cc, 4), round(cc, 4)], nearest_mm=round(D_NEAR, 4)),
                    tip=dict(included_deg=TIP_INCL, straight_length_mm=TIP_LEN), holes=[])
outl["senban"] = dict(outer=[[round(float(x), 4), round(float(y), 4)] for x, y in densify(sen45, 0.5)[:-1]],
                      orientation="corner on +X (rotated 45 deg from the photo's framing, which rests on a side)",
                      holes=[dict(kind="rounded_square", side_mm=hole_src, fillet_mm=hf_, status="SOURCED, kept",
                                  rotation_deg=45.0, note="sides parallel to the plate's chords, corners on the X and Y axes",
                                  loop=[[round(float(x), 4), round(float(y), 4)] for x, y in hs_src]),
                             dict(kind="rounded_square", side_mm=hole_ph, fillet_mm=hf_, status="photo value, user option",
                                  rotation_deg=45.0, note="sides parallel to the plate's chords, corners on the X and Y axes",
                                  loop=[[round(float(x), 4), round(float(y), 4)] for x, y in hs_ph])])
outl["happo"]["orientation"] = "tip on +X"
outl["roppo"]["orientation"] = "tip (apex) on +X"
outl["manji"]["orientation"] = "arm axis on +X; tips 35.0 deg CCW of each arm axis"
QA = {}
for key, exp in (("juji", 4), ("happo", 8), ("roppo", 6 + 12), ("senban", 4), ("manji", None)):
    QA[key] = qa(key, np.array(outl[key]["outer"]), exp)
QA["juji"]["symmetry_C4_mirror_max_err_mm"] = J["symmetry_max_err_mm"]
QA["previous_juji_outline"] = qa("juji_prev", np.array(OL["juji"]["outer"]), 4)
print(json.dumps(QA, indent=1))
json.dump(outl, open(OUT + "photo_matched_outlines_mm.json", "w"))

N["juji"] = J
N["happo"]["iou_recommended_with_kept_9p5mm_hole"] = iou_h_hole
N["happo"]["iou_no_hole_variant"] = iou_h_nohole
N["happo"]["mass_status"] = "re-derived from the photo outline; replaces the DERIVED 60 g (study range 53-79 g)"
N["senban"]["iou_recommended_kept_12p7mm_hole"] = iou_s_src
N["senban"]["iou_option_B_photo_20p1mm_hole"] = iou_s_ph
N["senban"]["bevel_estimate"] = bevel
N["senban"]["mass_status"] = ("re-derived from the photo outline with the SOURCED 12.7 mm hole; replaces the DERIVED 66 g, "
                              "which is the spec outline's own 65.92 g (study range 45-82 g)")
N["senban"]["orientation"] = "outline and holes rotated 45 deg: corner on +X"
N["roppo"]["mass_status"] = ("hybrid: photo outline at the retail object's SOURCED 98 mm / 2.0 mm; the SOURCED 40 g belongs to that "
                             "object's own outline, which is unknown")
N["roppo"]["spec_overlay_px_per_mm_apex"] = K
N["roppo"]["spec_area_mm2_check"] = A_spec_ro
N["manji"]["mass_status"] = "re-derived from the photo outline; replaces the placeholder's DERIVED 60.5 g"
N["juji"]["mass_status"] = ("hybrid: photo outline at the replica's SOURCED 97 mm / 3.0 mm; the SOURCED 39 g belongs to that "
                            "replica's own outline")
N["qa"] = QA
json.dump(N, open(OUT + "synthesis_numbers.json", "w"), indent=1, default=float)
print("happo IoU hole/no-hole", iou_h_hole, iou_h_nohole, " senban IoU 12.7/20.1", iou_s_src, iou_s_ph)
print("bevel", json.dumps(bevel, indent=1))
print("roppo spec area check", A_spec_ro)
