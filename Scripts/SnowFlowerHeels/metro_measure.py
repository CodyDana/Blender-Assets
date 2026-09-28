"""Reference metrology for the Snow Flower heels: materials, camera estimate, proportions, registered crops.
Run with Blender's bundled python (numpy, no bpy needed):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/SnowFlowerHeels/metro_measure.py <ref.npy> <maskA.npy> <maskB.npy> <sil.json>
Writes WorkFiles/SnowFlowerHeels/ref/* and WorkFiles/SnowFlowerHeels/heels_spec_measure.json (merged into heels_spec.json by metro_write_spec.py)."""
import sys, json, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metro_png as png, metro_common as cm, metro_traces as mt, metro_overlay as mo, metro_crop as mc

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + "/WorkFiles/SnowFlowerHeels"
REF = OUT + "/ref"
os.makedirs(REF, exist_ok=True)
a = np.load(sys.argv[1]); H, W = a.shape[:2]
mA = np.load(sys.argv[2]); mB = np.load(sys.argv[3]); sil = json.load(open(sys.argv[4]))
T = mt.T
res = {}

# ------------------------------------------------------------------ helpers
def poly_mask(pts, shape=(H, W)):
    pts = np.asarray(pts, float); yy, xx = np.mgrid[:shape[0], :shape[1]]
    x0, y0 = np.floor(pts.min(0)).astype(int); x1, y1 = np.ceil(pts.max(0)).astype(int) + 1
    sub = np.zeros((y1-y0, x1-x0), bool); X = xx[y0:y1, x0:x1] + 0.5; Y = yy[y0:y1, x0:x1] + 0.5
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i+1) % n]
        c = ((ya > Y) != (yb > Y)) & (X < (xb - xa) * (Y - ya) / (yb - ya + 1e-12) + xa)
        sub ^= c
    m = np.zeros(shape, bool); m[y0:y1, x0:x1] = sub; return m

def line_mask(pts, width):
    m = np.zeros((H, W), bool); pts = np.asarray(pts, float)
    ws = width if isinstance(width, list) else [width]*len(pts)
    yy, xx = np.mgrid[:H, :W]
    for i in range(len(pts)-1):
        p, q = pts[i], pts[i+1]; w = (ws[i] + ws[i+1]) / 4.0
        x0, y0 = np.floor(np.minimum(p, q) - w - 1).astype(int); x1, y1 = np.ceil(np.maximum(p, q) + w + 1).astype(int)
        X = xx[y0:y1, x0:x1] + 0.5; Y = yy[y0:y1, x0:x1] + 0.5; d = q - p; L2 = (d**2).sum()
        t = np.clip(((X-p[0])*d[0] + (Y-p[1])*d[1]) / L2, 0, 1)
        dist = np.hypot(X - (p[0]+t*d[0]), Y - (p[1]+t*d[1]))
        m[y0:y1, x0:x1] |= dist <= w
    return m

def disc(c, r, r_in=0):
    yy, xx = np.mgrid[:H, :W]; d = np.hypot(xx + 0.5 - c[0], yy + 0.5 - c[1]); return (d <= r) & (d >= r_in)

def to_lin(c): c = np.asarray(c, float); return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
def lum(rgb): return rgb @ np.array([0.2126, 0.7152, 0.0722])
def hexc(c): c = np.clip(np.round(np.asarray(c)*255), 0, 255).astype(int); return "#%02x%02x%02x" % tuple(c)

def stats(mask, name, note=""):
    px = a[mask]; L = lum(to_lin(px))  # linear luminance
    Ls = px.mean(1)
    med = np.median(px, 0); mean = px.mean(0)
    q = {p: np.percentile(L, p) for p in (5, 10, 50, 90, 98)}
    # colours at the luminance percentiles (median colour of pixels near each percentile)
    def col_at(p):
        lo, hi = np.percentile(L, max(p-3, 0)), np.percentile(L, min(p+3, 100)); sel = (L >= lo) & (L <= hi)
        return np.median(px[sel], 0)
    d = {"n_px": int(mask.sum()), "note": note,
         "srgb_median": hexc(med), "srgb_mean": hexc(mean), "srgb_median_0_255": [int(round(v*255)) for v in med],
         "linear_median": [round(float(v), 4) for v in to_lin(med)],
         "lum_linear_p5_p10_p50_p90_p98": [round(float(q[p]), 4) for p in (5, 10, 50, 90, 98)],
         "srgb_at_p10": hexc(col_at(10)), "srgb_at_p50": hexc(col_at(50)), "srgb_at_p90": hexc(col_at(90)), "srgb_at_p98": hexc(col_at(98)),
         "saturation_median": round(float(np.median((px.max(1)-px.min(1)) / np.maximum(px.max(1), 1e-4))), 3),
         "warmth_R_minus_B_median_0_255": round(float(np.median(px[:, 0]-px[:, 2])*255), 1)}
    res.setdefault("materials", {})[name] = d
    return d

# ------------------------------------------------------------------ materials
objA = mA; mn = a.mean(-1)
silver_lines = np.zeros((H, W), bool)
for k in ("A.front_branch_band", "A.topline_piping", "A.toe_frame_far_rail"):
    t = T[k]; silver_lines |= line_mask(t["pts"], t["width_px"])
spike = poly_mask(T["A.crest_spike"]["pts"]) & ~poly_mask(T["A.crest_spike_inset"]["pts"])
silver = (silver_lines | spike) & objA
# the traced band envelopes include a little leather at the edges: keep pixels that are not dark leather
silver_core = silver & (mn > 0.18)
stats(silver_core, "silver_antiqued", "front branch band + crest spike rim + topline piping + toe far rail, leather-edge pixels (<0.18) dropped")
stats(poly_mask(T["A.crest_spike_inset"]["pts"]) & objA, "silver_recess_inset", "dark recessed lens inside the crest spike (antiqued recess colour)")
pearl = np.zeros((H, W), bool)
for k in ("A.buckle_blossom", "A.toe_blossom", "A.vamp_blossom", "A.counter_blossom"):
    t = T[k]; r = t["d_px"]/2; pearl |= disc(t["pts"][0], 0.62*r, 0.22*r)
stats(pearl & (mn > 0.35), "pearl_blossom_petals", "petal ring (0.22-0.62 R) of the buckle, toe, vamp and counter blossoms; pixels darker than 0.35 (petal gaps) dropped")
stats(disc(T["A.vamp_blossom"]["pts"][0], 0.14*T["A.vamp_blossom"]["d_px"]/2), "blossom_centre_boss", "stamen boss at the centre of the vamp blossom")
cap = poly_mask(T["A.toe_cap"]["pts"]) & objA
stats(cap, "toe_cap_gloss", "glossy black toe cap, includes the specular streaks (see p90/p98)")
vamp = np.zeros((H, W), bool)
for b in [(305, 985, 350, 1025), (360, 1000, 420, 1040), (560, 935, 615, 970), (400, 1060, 480, 1090)]:
    vamp[b[1]:b[3], b[0]:b[2]] = True
vamp &= objA & ~line_mask(T["A.vine_frame_lower"]["pts"], 12) & ~line_mask(T["A.vine_lower_run"]["pts"], 12) & (mn < 0.30)
stats(vamp, "leather_vamp", "black vamp leather with fine grain + tone-on-tone floral emboss; bright silver excluded")
lining = np.zeros((H, W), bool); lining[70:170, 180:265] = True; lining &= objA & (mn < 0.3)
stats(lining, "leather_far_panel", "inside of the closed side / high back (lining side seen through the opening)")
med = poly_mask(T["A.medallion_leather"]["pts"]) & objA & ~line_mask(T["A.rear_c_band"]["pts"], 12) & (mn < 0.45)
stats(med, "leather_counter_medallion", "crackle-grain leather oval on the counter back")
strap = poly_mask(T["A.strap_near_run"]["pts"]) & objA & ~poly_mask(T["A.strap_stud"]["pts"]); strap[:, :335] = False
stats(strap, "strap_leather", "smooth black strap leather with edge stitching")
stil = np.zeros((H, W), bool); stil[650:870, 112:136] = True; stil &= objA
stats(stil, "stiletto_black", "black part of the stiletto (front/right face), semi-gloss")
tl = np.zeros((H, W), bool); tl[897:912, 90:136] = True; tl &= objA
stats(tl, "toplift_black", "top-lift block")
ins = np.zeros((H, W), bool); ins[560:700, 180:240] = True
ins &= objA & ~line_mask(T["A.insole_branch_stem"]["pts"], 14) & (mn < 0.5)
for p in T["A.insole_buds"]["pts"]: ins &= ~disc(p, 10)
stats(ins, "insole_ground", "insole sock-lining ground between prints (shows a lighter centre band)")
insp = np.zeros((H, W), bool)
for k in ("A.insole_blossom_1", "A.insole_blossom_2"):
    t = T[k]; r = t["d_px"]/2; insp |= disc(t["pts"][0], 0.6*r, 0.22*r)
stats(insp & (mn > 0.30), "insole_print_blossom", "printed blossoms on the insole (grey-pearl, flatter than the metal-set ones)")
emb = poly_mask(T["A.insole_emblem"]["pts"]) & objA
stats(emb & (mn > 0.30), "insole_emblem_print_lines", "light lines of the diamond emblem")
stats(emb & (mn <= 0.30), "insole_emblem_ground", "dark ground inside the diamond emblem")

# leather grain scale: autocorrelation of the high-passed vamp patch
patch = mn[985:1040, 305:420].astype(float); hp = patch - cm.boxmean(patch, 3)
f = np.fft.fft2(hp - hp.mean()); ac = np.real(np.fft.ifft2(f * np.conj(f))); ac = np.fft.fftshift(ac) / ac.max()
cy, cx = np.array(ac.shape)//2; yy, xx = np.mgrid[:ac.shape[0], :ac.shape[1]]; rr = np.hypot(yy-cy, xx-cx).astype(int)
prof = np.bincount(rr.ravel(), ac.ravel()) / np.bincount(rr.ravel())
zc = int(np.argmax(prof < 0.0)) if (prof < 0).any() else -1
res["leather_grain"] = {"autocorr_first_zero_px": zc, "highpass_std_mean_units": round(float(hp.std()), 4),
                        "note": "grain cell radius ~ first zero of the autocorrelation of the 3-px high-passed vamp leather (view A px)"}

# ------------------------------------------------------------------ camera estimate from the top-lift footprint
def cam_from_toplift(front, left, right):
    e1 = np.subtract(left, front); e2 = np.subtract(right, front)
    # weak perspective, square-cornered footprint on the ground: tan(a) sin(e) = |e1v|/|e1u| ; sin(e)/tan(a) = |e2v|/|e2u|
    k1 = abs(e1[1]/e1[0]); k2 = abs(e2[1]/e2[0]); se = np.sqrt(k1*k2); ta = k1/se
    return float(np.degrees(np.arcsin(se))), float(np.degrees(np.arctan(ta))), float(np.hypot(*e1)), float(np.hypot(*e2)), e1.tolist(), e2.tolist()
cams = {}
for v in "AB":
    fr, le, ri = (T[v + ".toplift_%s_corner" % s]["pts"][0] for s in ("front", "left", "right"))
    e, al, l1, l2, e1, e2 = cam_from_toplift(fr, le, ri)
    toe = T[v + ".toe_tip"]["pts"][0]
    du, dv = toe[0]-fr[0], toe[1]-fr[1]
    cams[v] = {"toplift_elev_deg": round(e, 1), "toplift_edge_yaw_deg": round(al, 1), "toplift_edges_px": [e1, e2]}
e_deg = float(np.mean([cams[v]["toplift_elev_deg"] for v in "AB"]))
res["camera"] = {"model": "weak perspective (orthographic + scale); no measurable perspective convergence (stiletto sides and strap edges stay parallel)",
                 "elevation_deg": round(e_deg, 1), "elevation_range_deg": [18, 26], "per_view": cams}
def axis_params(v, e):
    fr = T[v + ".toplift_front_corner"]["pts"][0]; toe = T[v + ".toe_tip"]["pts"][0]
    du, dv = toe[0]-fr[0], toe[1]-fr[1]; se = np.sin(np.radians(e))
    al = np.arctan2(dv/se, du); sL = du/np.cos(al)
    return al, sL, fr
for v in "AB":
    al, sL, fr = axis_params(v, e_deg)
    res["camera"]["per_view"][v].update({"shoe_axis_yaw_from_image_plane_deg": round(float(np.degrees(al)), 1),
        "px_per_unit_len_toplift_to_toe": round(float(sL), 1),
        "camera_azimuth_from_toe_deg": round(90 - float(np.degrees(al)), 1),
        "visible_side": "wearer's RIGHT side (toe points toward camera-right, heel away-left)"})
res["camera"]["scale_B_over_A"] = round(res["camera"]["per_view"]["B"]["px_per_unit_len_toplift_to_toe"] / res["camera"]["per_view"]["A"]["px_per_unit_len_toplift_to_toe"], 3)

# ------------------------------------------------------------------ 3D estimates (A) with the camera, for the few points that carry proportions
def to_ground_frame(v, uv, e, y_lat=0.0, dz_from_depth=True):
    """Solve shoe-frame (x forward from the top-lift front corner, z up) for an image point assumed at lateral offset y_lat (units of L_tl, + = visible side)."""
    al, sL, fr = axis_params(v, e); se, ce = np.sin(np.radians(e)), np.cos(np.radians(e))
    du, dv = uv[0]-fr[0], uv[1]-fr[1]
    # u = s(x cos a - y sin a) ; v = s((x sin a + y cos a) se - z ce)   with y = + visible side (toward camera-left)
    x = (du/sL + y_lat*np.sin(al)) / np.cos(al)
    z = ((x*np.sin(al) + y_lat*np.cos(al))*se - dv/sL) / ce
    return float(x), float(z)
est = {}
for e in (18.0, e_deg, 26.0):
    d = {}
    # heel seat (stiletto meets the counter at the back): silhouette rear at y=600 in view A
    ys = 600; xs_row = np.nonzero(mA[ys, :200])[0]; seat_back = (float(xs_row.min()), float(ys))
    d["seat_back_xz"] = to_ground_frame("A", seat_back, e)
    d["heel_breast_top_xz"] = to_ground_frame("A", (163, 610), e)
    d["toplift_top_xz"] = to_ground_frame("A", (107.4, 894), e)
    d["toe_apex_tip_xz"] = to_ground_frame("A", T["A.toe_apex_spike"]["pts"][0], e)
    d["strap_fold_xz"] = to_ground_frame("A", T["A.strap_fold"]["pts"][0], e)
    d["crest_spike_tip_xz_if_on_side_y0.12"] = to_ground_frame("A", T["A.crest_spike"]["pts"][0], e, y_lat=0.12)
    d["buckle_xz_if_on_side_y0.12"] = to_ground_frame("A", T["A.buckle_blossom"]["pts"][0], e, y_lat=0.12)
    rear = (10.0, 371.0)
    d["counter_rearmost_xz_if_y0"] = to_ground_frame("A", rear, e)
    al, sL, fr = axis_params("A", e)
    d["toplift_side_len_units"] = [round(res["camera"]["per_view"]["A"]["toplift_edges_px"][0][0] / np.cos(al) / sL, 4)]
    est["elev_%.1f" % e] = {k: ([round(v[0], 4), round(v[1], 4)] if isinstance(v, tuple) else v) for k, v in d.items()}
res["estimates_3d_units_of_toplift_to_toe"] = est

# ------------------------------------------------------------------ image-space proportions (per view)
def along(v, p):
    fr = np.array(T[v + ".toplift_front_corner"]["pts"][0]); toe = np.array(T[v + ".toe_tip"]["pts"][0]); ax = toe - fr; L = np.hypot(*ax)
    q = np.asarray(p) - fr; return float(q @ ax / L**2), float(np.cross(ax, q) / L**2)
prop = {}
for v, m in (("A", mA), ("B", mB)):
    ys, xs = np.nonzero(m); fr = np.array(T[v + ".toplift_front_corner"]["pts"][0]); toe = np.array(T[v + ".toe_tip"]["pts"][0]); L = float(np.hypot(*(toe - fr)))
    d = {"len_toplift_front_to_toe_px": round(L, 1), "bbox_xyxy": sil[v]["bbox_xyxy"], "area_px": sil[v]["area_px"],
         "height_top_to_ground_px": int(ys.max() - ys.min()), "height_over_len": round(float((ys.max()-ys.min()) / L), 4),
         "width_bbox_over_len": round(float((xs.max()-xs.min()) / L), 4)}
    rows = {}
    for yy in range(int(fr[1]) - 330, int(fr[1]) - 5, 30):
        xr = np.nonzero(m[yy, int(fr[0]) - 70:int(fr[0]) + 70])[0]
        if len(xr):
            runs = np.split(xr, np.nonzero(np.diff(xr) > 1)[0] + 1); r = max(runs, key=len)
            rows[str(yy)] = [int(r[0] + fr[0] - 70), int(r[-1] + fr[0] - 70), int(r[-1] - r[0] + 1)]
    d["stiletto_rows_y_x0_x1_w"] = rows
    pts = {k.split(".", 1)[1]: t["pts"][0] for k, t in T.items() if t["view"] == v and t["kind"] == "point"}
    d["landmarks_along_across"] = {k: [round(c, 4) for c in along(v, p)] for k, p in pts.items()}
    prop[v] = d
res["image_proportions"] = prop

# ------------------------------------------------------------------ element sizes (view A, px and / len)
LA = prop["A"]["len_toplift_front_to_toe_px"]
def plen(p): p = np.asarray(p); return float(np.hypot(*np.diff(p, axis=0).T).sum())
def bbox(p): p = np.asarray(p); return [round(float(v), 1) for v in (*p.min(0), *p.max(0))]
sizes = {}
for k, t in T.items():
    if t["view"] != "A": continue
    n = k.split(".", 1)[1]; p = np.asarray(t["pts"])
    s = {"kind": t["kind"]}
    if t["kind"] == "outline":
        x, y = p[:, 0], p[:, 1]; area = 0.5*abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        dd = np.hypot(*(p[:, None] - p[None]).transpose(2, 0, 1)); i, j = np.unravel_index(dd.argmax(), dd.shape)
        s.update(bbox=bbox(p), area_px=round(float(area), 1), max_extent_px=round(float(dd.max()), 1), max_extent_over_len=round(float(dd.max()/LA), 4))
    elif t["kind"] in ("polyline", "centerline"):
        s.update(bbox=bbox(p), length_px=round(plen(p), 1), length_over_len=round(plen(p)/LA, 4))
        if "width_px" in t: w = t["width_px"]; s["width_px"] = w if not isinstance(w, list) else [min(w), max(w)]
    elif t["kind"] in ("point", "points"):
        if "d_px" in t: s.update(d_px=t["d_px"], d_over_len=round(t["d_px"]/LA, 4))
        s["n"] = len(p)
    sizes[n] = s
res["element_sizes_A"] = sizes

# ------------------------------------------------------------------ registered crops
def save_view(v, m, pad=24):
    ys, xs = np.nonzero(m); x0, y0 = max(xs.min()-pad, 0), max(ys.min()-pad, 0); x1, y1 = min(xs.max()+pad+1, W), min(ys.max()+pad+1, H)
    crop = a[y0:y1, x0:x1]; mm = m[y0:y1, x0:x1]
    png.write(REF + "/view%s_crop.png" % v, crop)
    png.write(REF + "/view%s_mask.png" % v, mm.astype(np.float32))
    png.write(REF + "/view%s_rgba.png" % v, np.concatenate([crop, mm[..., None].astype(np.float32)], -1))
    return [int(x0), int(y0), int(x1), int(y1)]
boxes = {v: save_view(v, m) for v, m in (("A", mA), ("B", mB))}
png.write(REF + "/full_masks.png", np.stack([mA, mB, np.zeros_like(mA)], -1).astype(np.float32))
# similarity B -> A from the shared landmarks
pairs = [("toe_tip", "toe_tip"), ("toplift_front_corner", "toplift_front_corner"), ("crest_spike", "crest_spike_tip"), ("buckle_blossom", "buckle_blossom"),
         ("strap_stud", "strap_stud"), ("strap_fold", "strap_fold"), ("toe_apex_spike", "toe_apex_spike_tip"), ("toe_blossom", "toe_blossom"),
         ("insole_emblem", "insole_emblem_top")]
PA = np.array([T["A." + a_]["pts"][0] for a_, b_ in pairs]); PB = np.array([T["B." + b_]["pts"][0] for a_, b_ in pairs])
def fit_sim(P, Q):  # Q ~ s R P + t
    mp, mq = P.mean(0), Q.mean(0); P0, Q0 = P-mp, Q-mq
    U, S, Vt = np.linalg.svd(Q0.T @ P0); R = U @ Vt
    if np.linalg.det(R) < 0: U[:, -1] *= -1; R = U @ Vt
    s = S.sum() / (P0**2).sum(); t = mq - s * R @ mp; return s, R, t
def fit_aff(P, Q):
    X = np.hstack([P, np.ones((len(P), 1))]); M, *_ = np.linalg.lstsq(X, Q, rcond=None); return M
s, R, t = fit_sim(PB, PA); rs = PA - (s*(R @ PB.T).T + t)
M = fit_aff(PB, PA); ra = PA - np.hstack([PB, np.ones((len(PB), 1))]) @ M
reg = {"pairs_A_B": pairs, "similarity_B_to_A": {"scale": round(float(s), 4), "rot_deg": round(float(np.degrees(np.arctan2(R[1, 0], R[0, 0]))), 2), "t": [round(float(v), 2) for v in t],
       "rms_px": round(float(np.sqrt((rs**2).sum(1).mean())), 2), "residuals_px": {p[0]: [round(float(v), 1) for v in r] for p, r in zip(pairs, rs)}},
       "affine_B_to_A": {"M_3x2": M.round(5).tolist(), "rms_px": round(float(np.sqrt((ra**2).sum(1).mean())), 2)}}
# warp B into A's frame with the similarity (inverse mapping, bilinear)
yy, xx = np.mgrid[:H, :W].astype(float); Ri = R.T / s
src = (np.stack([xx.ravel(), yy.ravel()], 1) - t) @ Ri.T
sx, sy = src[:, 0].reshape(H, W), src[:, 1].reshape(H, W)
def bil(img, sx, sy):
    x0 = np.clip(np.floor(sx).astype(int), 0, W-2); y0 = np.clip(np.floor(sy).astype(int), 0, H-2); fx = np.clip(sx-x0, 0, 1)[..., None]; fy = np.clip(sy-y0, 0, 1)[..., None]
    im = img if img.ndim == 3 else img[..., None]
    o = (im[y0, x0]*(1-fx)*(1-fy) + im[y0, x0+1]*fx*(1-fy) + im[y0+1, x0]*(1-fx)*fy + im[y0+1, x0+1]*fx*fy)
    return o
inside = (sx >= 0) & (sx < W-1) & (sy >= 0) & (sy < H-1)
Bw = bil(a, sx, sy); Bw[~inside] = 1; mBw = bil(mB.astype(np.float32), sx, sy)[..., 0] > 0.5; mBw &= inside
x0, y0, x1, y1 = boxes["A"]
Bw[~mBw] = 1
png.write(REF + "/viewB_registered_to_A_crop.png", Bw[y0:y1, x0:x1])
png.write(REF + "/viewB_registered_to_A_mask.png", mBw[y0:y1, x0:x1].astype(np.float32))
ov = np.ones((H, W, 3), np.float32); ov[mA & ~mBw] = (0.85, 0.2, 0.2); ov[mBw & ~mA] = (0.2, 0.4, 0.9); ov[mA & mBw] = (0.25, 0.25, 0.25)
png.write(REF + "/silhouette_A_vs_B_registered.png", ov[y0:y1, x0:x1])
iou = float((mA & mBw).sum() / (mA | mBw).sum())
reg["silhouette_IoU_A_vs_B_registered_similarity"] = round(iou, 4)
reg["crop_boxes_xyxy"] = boxes
res["registration"] = reg
# traced-outline overlays for the record
for v in "AB":
    bx = boxes[v]; mc.crop(bx[0], bx[1], bx[2], bx[3], 1, 50, REF + "/view%s_traces_overlay.png" % v, a, overlay=mo.overlay_json(v))

json.dump(res, open(OUT + "/heels_spec_measure.json", "w"), indent=1)
print(json.dumps({k: res[k] for k in ("camera", "registration", "leather_grain")}, indent=1))
print(json.dumps(res["estimates_3d_units_of_toplift_to_toe"], indent=1))
