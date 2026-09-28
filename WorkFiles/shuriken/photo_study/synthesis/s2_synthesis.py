"""NOTE (editor pass): s5_fix.py supersedes this script for the juji outline, the senban orientation and the IoU variants;
run s5_fix.py after this one, then s6_contact.py.
Synthesis: photo-matched parametric outlines at the study's sourced sizes, exact areas and masses,
IoU against the reconciled photo masks, photo-matched overlays, and the contact sheet.
Run: blender -b --factory-startup --python s2_synthesis.py
Reads only photo_study/* and References/Shuriken/images/* ; writes only photo_study/synthesis/* and
photo_study/contact_sheet.png."""
import bpy, numpy as np, json, math, os, sys

P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
OUT = P + "synthesis/"
IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/"
RHO_STEEL = 7.85e-3   # g per mm^3

# ------------------------------------------------------------------ io helpers
def load_rgb(path):
    img = bpy.data.images.load(path)
    W, H = img.size
    buf = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(buf)
    a = buf.reshape(H, W, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    return a

def save_png(a, path):
    h, w, _ = a.shape
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=False)
    buf = np.ones((h, w, 4), np.float32); buf[..., :3] = np.clip(a, 0, 1)
    img.pixels.foreach_set(buf[::-1].ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img); print("wrote", path)

def densify(p, step=0.5, closed=True):
    q = np.vstack([p, p[:1]]) if closed else p
    out = []
    for a, b in zip(q[:-1], q[1:]):
        n = max(int(np.ceil(np.hypot(*(b - a)) / step)), 1)
        t = np.arange(n)[:, None] / n
        out.append(a + (b - a) * t)
    out.append(q[-1:])
    return np.vstack(out)

def stamp(im, pts, col, rad=1.6, dashed=0):
    H, W, _ = im.shape
    d = densify(pts, 0.5)
    if dashed:
        L = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(d, axis=0).T))])
        d = d[(L // dashed) % 2 == 0]
    k = int(np.ceil(rad))
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            if dx * dx + dy * dy > rad * rad + 0.3: continue
            x = np.round(d[:, 0]).astype(int) + dx; y = np.round(d[:, 1]).astype(int) + dy
            ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
            im[y[ok], x[ok]] = col

def raster(loops, W, H):
    """even-odd fill at pixel centres"""
    E = []
    for p in loops:
        q = np.vstack([p, p[:1]])
        E.append(np.stack([q[:-1], q[1:]], 1))
    E = np.vstack(E)                      # (n,2,2)
    x0, y0, x1, y1 = E[:, 0, 0], E[:, 0, 1], E[:, 1, 0], E[:, 1, 1]
    M = np.zeros((H, W), bool)
    xs = np.arange(W) + 0.5
    for r in range(H):
        yc = r + 0.5
        s = ((y0 <= yc) & (y1 > yc)) | ((y1 <= yc) & (y0 > yc))
        if not s.any(): continue
        xc = x0[s] + (yc - y0[s]) * (x1[s] - x0[s]) / (y1[s] - y0[s])
        xc = np.sort(xc)
        cnt = np.searchsorted(xc, xs)
        M[r] = (cnt % 2) == 1
    return M

def shoelace(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

def place(p, cen, scale, rot_deg):
    a = math.radians(rot_deg); c, s = math.cos(a), math.sin(a)
    x = scale * (c * p[:, 0] - s * p[:, 1]); y = scale * (s * p[:, 0] + c * p[:, 1])
    return np.stack([cen[0] + x, cen[1] - y], 1)

def rot(p, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return p @ np.array([[c, -s], [s, c]]).T

def circle(cx, cy, r, n=720):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(t), cy + r * np.sin(t)], 1)

def fillet(pPrev, pV, pNext, r, n=24):
    pPrev, pV, pNext = map(np.asarray, (pPrev, pV, pNext))
    d1 = pPrev - pV; d2 = pNext - pV
    d1 = d1 / np.linalg.norm(d1); d2 = d2 / np.linalg.norm(d2)
    ang = math.acos(np.clip(d1 @ d2, -1, 1))
    t = r / math.tan(ang / 2)
    bis = d1 + d2; bis /= np.linalg.norm(bis)
    cen = pV + bis * (r / math.sin(ang / 2))
    q1, q2 = pV + d1 * t, pV + d2 * t
    a1 = math.atan2(q1[1] - cen[1], q1[0] - cen[0]); a2 = math.atan2(q2[1] - cen[1], q2[0] - cen[0])
    while a2 - a1 > math.pi: a2 -= 2 * math.pi
    while a1 - a2 > math.pi: a2 += 2 * math.pi
    return np.array([cen + r * np.array([math.cos(a), math.sin(a)]) for a in np.linspace(a1, a2, n)])

def rounded_square(side, rf, n=24):
    h = side / 2; pts = []
    for cx, cy, a0 in ((h - rf, h - rf, 0), (-h + rf, h - rf, 90), (-h + rf, -h + rf, 180), (h - rf, -h + rf, 270)):
        for a in np.linspace(math.radians(a0), math.radians(a0 + 90), n):
            pts.append((cx + rf * math.cos(a), cy + rf * math.sin(a)))
    return np.array(pts)

def iou(A, B):
    return float((A & B).sum() / max((A | B).sum(), 1))

R = {}   # results

# ================================================================== JUJI (study 2.1)
raw = np.load(OUT + "juji_profile_raw.npy")       # u/R, h/R (median 8 sides), h/R (excl top)
g, h8 = raw[:, 0], raw[:, 1]
fin = np.isfinite(h8)
# diagonal crossing h(u) = u
i0 = np.argmax(fin)
dd = h8 - g
idx = [i for i in range(i0, 400) if np.isfinite(dd[i]) and np.isfinite(dd[i + 1]) and dd[i] >= 0 > dd[i + 1]]
if not idx:
    idx = [i0]
iD = idx[0]
uD = g[iD] + (g[iD + 1] - g[iD]) * dd[iD] / (dd[iD] - dd[iD + 1]) if dd[iD] != dd[iD + 1] else g[iD]
# smooth interior with a +-0.012 R moving average, keep the tip raw
h = h8.copy()
seg = slice(iD, 971)
v = h[seg]; ok = np.isfinite(v); v2 = np.where(ok, v, 0)
k = np.ones(25)
num = np.convolve(v2, k, 'same'); den = np.convolve(ok.astype(float), k, 'same')
h[seg] = num / np.maximum(den, 1)
h[1000] = 0.0
for i in range(971, 1000):
    if not np.isfinite(h[i]): h[i] = np.nan
tipzone = np.arange(960, 1001)
good = np.isfinite(h[tipzone])
h[tipzone] = np.interp(g[tipzone], g[tipzone][good], h[tipzone][good])
iMax = 500 + int(np.nanargmax(h[500:900]))
h[iMax:] = np.minimum.accumulate(h[iMax:])
uu = np.concatenate([[uD], g[iD + 1:]]); hh = np.concatenate([[uD], h[iD + 1:]])
# key features of the profile
nk = 150 + int(np.nanargmin(h[150:500]))
d1 = np.gradient(np.convolve(np.nan_to_num(h), np.ones(41) / 41, 'same'))
infl = nk + int(np.argmax(d1[nk:iMax]))      # steepest point = concave-to-convex inflection
tipsel = (g >= 0.90) & (g <= 0.99)
sl = np.polyfit(g[tipsel], h[tipsel], 1)[0]
tip_incl_5 = 2 * math.degrees(math.atan(abs(sl)))
tipsel10 = (g >= 0.80) & (g <= 0.99)
sl10 = np.polyfit(g[tipsel10], h[tipsel10], 1)[0]
tip_incl_10 = 2 * math.degrees(math.atan(abs(sl10)))
Rj = 48.5   # mm, sourced 97 mm span
arm_lo = np.stack([uu, -hh], 1)[:-1]       # u ascending, lower side, drop tip duplicate
arm_hi = np.stack([uu[::-1], hh[::-1]], 1)
arm = np.vstack([arm_lo, arm_hi])            # from diagonal at -45 deg, CCW round the tip, to +45 deg
juji_R = np.vstack([rot(arm, 90 * k)[:-1] for k in range(4)])   # units of R
juji_mm = juji_R * Rj
A_juji = abs(shoelace(juji_mm))
stations = {}
for s in (0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.98, 1.0):
    stations["%.2f" % s] = dict(u_mm=round(s * Rj, 2), width_mm=round(2 * float(np.interp(s, uu, hh)) * Rj, 2),
                                width_over_span=round(float(np.interp(s, uu, hh)), 4))
R["juji"] = dict(
    span_mm=97.0, thickness_mm=3.0, R_mm=Rj,
    diagonal_crossing_uR=float(uD), crotch_nearest_mm=float(math.sqrt(2) * uD * Rj),
    crotch_nearest_over_span=float(math.sqrt(2) * uD / 2),
    neck_min_uR=float(g[nk]), neck_min_width_mm=float(2 * h[nk] * Rj), neck_min_over_span=float(h[nk]),
    blade_max_uR=float(g[iMax]), blade_max_width_mm=float(2 * h[iMax] * Rj), blade_max_over_span=float(h[iMax]),
    inflection_uR=float(g[infl]) if infl > 0 else None,
    tip_included_last5pct_deg=tip_incl_5, tip_included_last10pct_deg=tip_incl_10,
    stations=stations, area_mm2=A_juji, area_over_span2=A_juji / 97.0 ** 2,
    mass_g_at_3mm=A_juji * 3.0 * RHO_STEEL,
    thickness_for_39g_mm=39.0 / (A_juji * RHO_STEEL),
)

# ================================================================== HAPPO (study 2.2)
Rh, rho = 50.0, 0.4576
rn = rho * Rh
fil = 0.0124 * 100.0
V = []
for k in range(8):
    a = math.radians(45 * k); V.append((Rh * math.cos(a), Rh * math.sin(a)))
    b = math.radians(45 * k + 22.5); V.append((rn * math.cos(b), rn * math.sin(b)))
V = np.array(V)
star = []
for i in range(16):
    if i % 2 == 0: star.append(V[i:i + 1])
    else: star.append(fillet(V[i - 1], V[i], V[(i + 1) % 16], fil, 40))
star = np.vstack(star)
A_star_sharp = 8 * Rh * rn * math.sin(math.radians(22.5))
A_star = abs(shoelace(densify(star, 0.01)))
hole_h = 9.5
A_hole_h = math.pi * (hole_h / 2) ** 2
tan_half = rn * math.sin(math.radians(22.5)) / (Rh - rn * math.cos(math.radians(22.5)))
tip_implied = 2 * math.degrees(math.atan(tan_half))
notch_open = tip_implied + 45.0
R["happo"] = dict(
    span_mm=100.0, thickness_mm=2.5, R_tip_mm=Rh, rho=rho, notch_vertex_r_mm=rn, notch_fillet_mm=fil,
    notch_floor_r_mm=rn + fil * (1 / math.sin(math.radians(notch_open / 2)) - 1),
    tip_included_implied_deg=tip_implied, notch_opening_implied_deg=notch_open,
    point_root_chord_mm=2 * rn * math.sin(math.radians(22.5)),
    area_sharp_analytic_mm2=A_star_sharp, area_with_fillets_mm2=A_star,
    hole_mm=hole_h, hole_area_mm2=A_hole_h,
    area_net_with_sourced_hole_mm2=A_star - A_hole_h,
    mass_g_with_hole=(A_star - A_hole_h) * 2.5 * RHO_STEEL,
    mass_g_no_hole=A_star * 2.5 * RHO_STEEL,
    t_for_60g_with_hole=60 / ((A_star - A_hole_h) * RHO_STEEL),
    t_for_57p5g_with_hole=57.5 / ((A_star - A_hole_h) * RHO_STEEL),
    t_for_60g_no_hole=60 / (A_star * RHO_STEEL),
    area_over_span2_no_hole=A_star / 100.0 ** 2,
)

# ================================================================== ROPPO (study 2.4)
Ra = 49.0                      # sharp apex radius = sourced 98 mm / 2
Sref = Ra / 0.514              # mm per reconciled observed span unit S
Rhub = 0.2440 * Sref; Rbore = 0.1140 * Sref
alpha = 25.1; ha = math.radians(alpha / 2)
tt = Ra * math.cos(ha) - math.sqrt(Rhub ** 2 - (Ra * math.sin(ha)) ** 2)
xr, yr = Ra - tt * math.cos(ha), tt * math.sin(ha)
beta = math.degrees(math.atan2(yr, xr))
ro = []
for k in range(6):
    ph = 60 * k
    ro.append(rot(np.array([[xr, -yr], [Ra, 0.0], [xr, yr]]), ph))
    arc_a = np.radians(np.linspace(ph + beta, ph + 60 - beta, 90))[1:-1]
    ro.append(np.stack([Rhub * np.cos(arc_a), Rhub * np.sin(arc_a)], 1))
ro = np.vstack(ro)
tri = 0.5 * (2 * yr) * (Ra - xr)
th2 = math.radians(beta)
segm = Rhub ** 2 / 2 * (2 * th2 - math.sin(2 * th2))
A_point = tri - segm
A_ro = math.pi * Rhub ** 2 + 6 * A_point - math.pi * Rbore ** 2
A_ro_poly = abs(shoelace(ro)) - math.pi * Rbore ** 2
# generator equivalent: arm width whose taper starts exactly at the hub root, and one with a 0.5 mm parallel run
def run_len(hw):
    return (Ra - hw / math.tan(ha)) - math.sqrt(Rhub ** 2 - hw ** 2)
lo_, hi_ = 3.0, 9.0
for _ in range(80):
    m = (lo_ + hi_) / 2
    lo_, hi_ = (m, hi_) if run_len(m) > 0.5 else (lo_, m)
hw05 = lo_
R["roppo"] = dict(
    span_mm=98.0, thickness_mm=2.0, R_apex_mm=Ra, mm_per_S=Sref,
    hub_r_mm=Rhub, hub_d_mm=2 * Rhub, bore_d_mm=2 * Rbore, rim_round_mm=0.0035 * Sref,
    tip_included_deg=alpha, root_chord_mm=2 * yr, root_axial_mm=xr, root_half_angle_deg=beta,
    exposed_hub_arc_deg=60 - 2 * beta, taper_start_mm=Ra - yr / math.tan(ha),
    arm_width_zero_run_mm=2 * yr, arm_width_05mm_run=2 * hw05,
    point_area_each_mm2=A_point, area_mm2=A_ro, area_poly_check_mm2=A_ro_poly,
    mass_g_at_2mm=A_ro * 2.0 * RHO_STEEL, t_for_40g=40 / (A_ro * RHO_STEEL),
    flank_tangent_bore_rule_deg=2 * math.degrees(math.asin(Rbore / Ra)),
)
# alt: if the sourced 98 mm were the blunt observed span, everything scales by 98/Sref
k_alt = 98.0 / Sref
R["roppo"]["alt_if_98mm_is_observed_span"] = dict(scale=k_alt, area_mm2=A_ro * k_alt ** 2,
                                                  mass_g_at_2mm=A_ro * k_alt ** 2 * 2 * RHO_STEEL,
                                                  t_for_40g=40 / (A_ro * k_alt ** 2 * RHO_STEEL))

# ================================================================== SENBAN (study 2.3)
c = 76.2; s_ph = 0.0616 * c
def senban_outline(c, s, n=400):
    Rarc = (c * c / 4 + s * s) / (2 * s)
    pts = []
    corners = [(c / 2, -c / 2), (c / 2, c / 2), (-c / 2, c / 2), (-c / 2, -c / 2)]
    for i in range(4):
        a = np.array(corners[i]); b = np.array(corners[(i + 1) % 4])
        mid = (a + b) / 2; out = mid / np.linalg.norm(mid)
        cen = mid - out * (s - Rarc)            # centre outside the plate
        a1 = math.atan2(a[1] - cen[1], a[0] - cen[0]); a2 = math.atan2(b[1] - cen[1], b[0] - cen[0])
        while a2 - a1 > math.pi: a2 -= 2 * math.pi
        while a1 - a2 > math.pi: a2 += 2 * math.pi
        for t in np.linspace(a1, a2, n)[:-1]:
            pts.append(cen + Rarc * np.array([math.cos(t), math.sin(t)]))
    return np.array(pts), Rarc
def seg_area(c, s):
    Rarc = (c * c / 4 + s * s) / (2 * s); th = math.asin(c / 2 / Rarc)
    return Rarc ** 2 / 2 * (2 * th - math.sin(2 * th))
sen, Rarc = senban_outline(c, s_ph)
A_sq = c * c - 4 * seg_area(c, s_ph)
A_sq_spec = c * c - 4 * seg_area(c, 6.0)
hf = 0.0117 * c
hole_src = 12.7; hole_ph = 0.264 * c
A_hole_src = hole_src ** 2 - (4 - math.pi) * hf ** 2
A_hole_ph = hole_ph ** 2 - (4 - math.pi) * hf ** 2
corner_tip = 90 - 4 * math.degrees(math.atan(2 * s_ph / c))
R["senban"] = dict(
    side_mm=c, diagonal_mm=c * math.sqrt(2), thickness_mm=1.9, sagitta_mm=s_ph, arc_R_mm=Rarc,
    corner_tip_deg=corner_tip, spec_corner_tip_deg=90 - 4 * math.degrees(math.atan(12.0 / c)),
    hole_fillet_mm=hf, bevel_plan_mm=0.0166 * c,
    outline_area_mm2=A_sq, outline_poly_check_mm2=abs(shoelace(sen)),
    A_with_sourced_hole=A_sq - A_hole_src, mass_g_sourced_hole=(A_sq - A_hole_src) * 1.9 * RHO_STEEL,
    t_for_66g_sourced_hole=66 / ((A_sq - A_hole_src) * RHO_STEEL),
    hole_photo_mm=hole_ph, A_with_photo_hole=A_sq - A_hole_ph,
    mass_g_photo_hole=(A_sq - A_hole_ph) * 1.9 * RHO_STEEL,
    spec_area_mm2=A_sq_spec - hole_src ** 2, spec_mass_g=(A_sq_spec - hole_src ** 2) * 1.9 * RHO_STEEL,
)

# ================================================================== MANJI (study 2.6)
sys.path.insert(0, P + "manji/reconcile")
import outline as mo
mp = mo.full_polygon("reconciled")
mp = mp / (2.0 * np.hypot(mp[:, 0], mp[:, 1]).max())     # tip-to-tip = 1
A_man = abs(shoelace(mp)) * 100.0 ** 2
# denser check: rebuild with finer arc sampling
R["manji"] = dict(
    span_mm=100.0, thickness_mm=2.5, area_mm2=A_man, area_over_span2=A_man / 1e4,
    mass_g_at_2p5=A_man * 2.5 * RHO_STEEL, t_for_60g=60 / (A_man * RHO_STEEL),
    mass_g_at_3p4=A_man * 3.4 * RHO_STEEL,
    arm_w_centre_mm=2 * mo.P["half_w0"] * 100, arm_w_hook_mm=2 * mo.v_hook * 100,
    central_square_mm=2 * abs(mo.J_IN[1]) * 100, across_arms_mm=2 * mo.P["u_axis_back"] * 100,
    hook_corner_u_mm=mo.P["u_hook"] * 100, tip_off_deg=mo.P["tip_off_deg"],
    back_arc_R_mm=mo.P["arc_R"] * 100, inner_edge_deg=75.05,
)

# ================================================================== overlays + IoU
cyan = (0.0, 1.0, 1.0); yellow = (1.0, 0.85, 0.0)
panels = {}

def dim(a): return a * 0.72 + 0.14

# juji
im = load_rgb(IMG + "Juji.JPG"); H, W, _ = im.shape
cenJ = np.array([694.10, 651.11]); scJ = 662.45 / Rj
pj = place(juji_mm, cenJ, scJ, 1.70)
cont = np.load(P + "juji/contour/contour_refined.npy").astype(float)
mJ = raster([cont], W, H); mP = raster([pj], W, H)
R["juji"]["iou_vs_reconciled_mask"] = iou(mJ, mP)
R["juji"]["measured_area_over_span2"] = abs(shoelace(cont)) / (2 * 662.45) ** 2
o = dim(im); stamp(o, pj, cyan, 2.6)
save_png(o, OUT + "juji_photo_matched.png"); panels["juji"] = o

# happo
im = load_rgb(IMG + "Happo.JPG"); H, W, _ = im.shape
cenH = np.array([610.95, 638.76]); scH = 632.15 / Rh
ph_ = place(star, cenH, scH, 27.67); phh = place(circle(0, 0, hole_h / 2), cenH, scH, 0)
mk = load_rgb(P + "happo/happo_reconciled_mask.png")[..., 0] > 0.75
R["happo"]["iou_vs_reconciled_mask_no_hole"] = iou(mk, raster([ph_], W, H))
R["happo"]["measured_area_over_span2"] = None
o = dim(im); stamp(o, ph_, cyan, 2.6); stamp(o, phh, yellow, 2.6, dashed=10)
save_png(o, OUT + "happo_photo_matched.png"); panels["happo"] = o

# roppo
im = load_rgb(IMG + "Roppo.JPG"); H, W, _ = im.shape
cenR = np.array([629.0, 528.3]); scR = 604.978 / Ra
pr = place(ro, cenR, scR, 1.595); pb = place(circle(0, 0, Rbore), cenR, scR, 0)
mk = load_rgb(P + "roppo/contour/roppo_mask.png")[..., 0] > 0.75
MR = raster([pr, pb], W, H)
R["roppo"]["iou_vs_contour_mask_B_includes_shadow_band"] = iou(mk, MR)
R["roppo"]["iou_vs_radial_mask_A_T65"] = iou(load_rgb(P + "roppo/radial/mask_T65.png")[..., 0] > 0.75, MR)
o = dim(im); stamp(o, pr, cyan, 2.6); stamp(o, pb, cyan, 2.6)
save_png(o, OUT + "roppo_photo_matched.png"); panels["roppo"] = o

# senban
im = load_rgb(IMG + "Senban.jpg"); H, W, _ = im.shape
cenS = np.array([505.3, 476.8]); scS = 852.3 / c
ps = place(sen, cenS, scS, 2.45)
phs = place(rounded_square(hole_src, hf), cenS, scS, 2.45)
php = place(rounded_square(hole_ph, hf), cenS, scS, 2.45)
mk = load_rgb(P + "senban/contour/senban_mask.png")[..., 0] > 0.75
R["senban"]["iou_vs_contour_mask_photo_hole"] = iou(mk, raster([ps, php], W, H))
o = dim(im); stamp(o, ps, cyan, 2.4); stamp(o, php, cyan, 2.0, dashed=10); stamp(o, phs, yellow, 2.4)
save_png(o, OUT + "senban_photo_matched.png"); panels["senban"] = o

# manji
im = load_rgb(IMG + "Manjiken.JPG"); H, W, _ = im.shape
pm = place(mp, np.array([1305.2, 1317.9]), 2842.8, -0.47)
mk = np.load(P + "manji/contour/mask_final.npy").astype(bool)
R["manji"]["iou_vs_contour_mask"] = iou(mk, raster([pm], W, H))
o = dim(im); stamp(o, pm, cyan, 5.0)
o2 = o.reshape(H // 2, 2, W // 2, 2, 3).mean((1, 3)) if (H % 2 == 0 and W % 2 == 0) else o[::2, ::2]
save_png(o2, OUT + "manji_photo_matched_half.png"); panels["manji"] = o2

json.dump(R, open(OUT + "synthesis_numbers.json", "w"), indent=1, default=float)
print(json.dumps(R, indent=1, default=float))

# ================================================================== model-ready outlines (mm, +X = first tip, CCW, Blender top view)
def dec(p, step):
    d = densify(p, step)
    return [[round(float(x), 4), round(float(y), 4)] for x, y in d[:-1]]
outl = dict(
    note="Photo-matched plan outlines in mm at the study's sourced sizes. Blender top view: +Z to the viewer, X right, Y up. "
         "Outer loops CCW. Holes listed separately. Un-bevelled plan outline only.",
    juji=dict(outer=[[round(float(x), 4), round(float(y), 4)] for x, y in juji_mm[::3]],
              half_profile_uR_hR=[[round(float(a), 4), round(float(b), 5)] for a, b in zip(uu[::5], hh[::5])], R_mm=Rj, holes=[]),
    happo=dict(outer=dec(star, 0.5), holes=[dict(kind="circle", d_mm=hole_h, status="SOURCED, kept; absent in photo")]),
    roppo=dict(outer=dec(ro, 0.5), holes=[dict(kind="circle", d_mm=2 * Rbore, rim_fillet_mm=0.0035 * Sref)]),
    senban=dict(outer=dec(sen, 0.5), holes=[dict(kind="rounded_square", side_mm=hole_src, fillet_mm=hf, status="SOURCED, kept"),
                                         dict(kind="rounded_square", side_mm=hole_ph, fillet_mm=hf, status="photo value, option")]),
    manji=dict(outer=dec(mp * 100.0, 0.5), holes=[], handedness="left-facing manji: hook on the +X arm lies at +Y"),
)
json.dump(outl, open(OUT + "photo_matched_outlines_mm.json", "w"))
print("wrote outlines json")
