# Primitive fitting and measurements on the final contour (Method B).
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
from features import load_features

px = np.load(BASE + "/manji_pixels.npy"); H, W = px.shape[:2]
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
C, dp, feats, tips, ti, turn, sarc = load_features(verbose=False)
N = len(C); P_ = sarc[-1] + np.hypot(*(C[0] - C[-1]))
ARMS = ["top", "right", "bottom", "left"]
NEXT = {a: ARMS[(i + 1) % 4] for i, a in enumerate(ARMS)}
PREV = {a: ARMS[(i - 1) % 4] for i, a in enumerate(ARMS)}


def up(v):
    return np.array([v[0], -v[1]])  # image -> y-up frame


def cross2(a, b):
    return float(a[0] * b[1] - a[1] * b[0])


def ang_up(v):
    return math.degrees(math.atan2(-v[1], v[0]))


def unit(v):
    v = np.asarray(v, float)
    return v / np.hypot(*v)


# ---------------------------------------------------------------- primitives
def fit_line(P):
    mu = P.mean(0)
    U, S, Vt = np.linalg.svd(P - mu, full_matrices=False)
    d = Vt[0]; n = np.array([-d[1], d[0]])
    return mu, d, (P - mu) @ n


def robust_line(P, k=2.5, it=4):
    keep = np.ones(len(P), bool)
    for _ in range(it):
        mu, d, _ = fit_line(P[keep]); r = (P - mu) @ np.array([-d[1], d[0]])
        sd = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep])))
        keep = np.abs(r - np.median(r[keep])) < max(k * sd, 0.75)
    mu, d, r = fit_line(P[keep])
    return dict(p=mu, d=d, rms=float(np.sqrt(np.mean(r ** 2))), maxdev=float(np.abs(r).max()), n=int(keep.sum()), n_all=len(P))


def fit_circle(P):
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]; b = x * x + y * y
    cx, cy, c0 = np.linalg.lstsq(A, b, rcond=None)[0]           # algebraic (Kasa) fit
    R = math.sqrt(max(c0 + cx * cx + cy * cy, 1e-9)); c = np.array([cx, cy])
    for _ in range(30):                                          # geometric refinement (Gauss-Newton)
        d = P - c; r = np.hypot(d[:, 0], d[:, 1])
        J = np.c_[-d[:, 0] / r, -d[:, 1] / r, -np.ones(len(r))]
        res = r - R; step = np.linalg.lstsq(J, -res, rcond=None)[0]
        c = c + step[:2]; R = R + step[2]
        if np.abs(step).max() < 1e-7:
            break
    res = np.hypot(*(P - c).T) - R
    return c, float(R), res


def robust_circle(P, k=2.5, it=4):
    keep = np.ones(len(P), bool)
    for _ in range(it):
        c, R, _ = fit_circle(P[keep]); r = np.hypot(*(P - c).T) - R
        sd = 1.4826 * np.median(np.abs(r[keep])); keep = np.abs(r) < max(k * sd, 0.75)
    c, R, res = fit_circle(P[keep])
    return dict(c=c, R=R, rms=float(np.sqrt(np.mean(res ** 2))), n=int(keep.sum()))


def isect(l1, l2):
    A = np.array([l1["d"], -l2["d"]]).T
    t = np.linalg.solve(A, l2["p"] - l1["p"])
    return l1["p"] + t[0] * l1["d"]


def dist_to_line(q, l):
    return float((np.asarray(q) - l["p"]) @ np.array([-l["d"][1], l["d"][0]]))


def feat_pts(name, trim0, trim1):
    idx = feats[name]["idx"]; s = (sarc[idx] - sarc[idx[0]]) % P_; Ls = s[-1]
    keep = (s >= trim0) & (s <= Ls - trim1)
    return C[idx[keep]], float(Ls)


def local_pts(name, end, dmin, dmax):
    idx = feats[name]["idx"]; s = (sarc[idx] - sarc[idx[0]]) % P_; Ls = s[-1]
    dd = s if end == "start" else Ls - s
    return C[idx[(dd >= dmin) & (dd <= dmax)]]


# ---------------------------------------------------------------- tips and span
T = {a: np.array(tips[a]["apparent_tip"]) for a in ARMS}
Vt = {a: np.array(tips[a]["virtual_tip"]) for a in ARMS}
d_tb = float(np.hypot(*(T["top"] - T["bottom"]))); d_rl = float(np.hypot(*(T["right"] - T["left"])))
SPAN = 0.5 * (d_tb + d_rl)


def hull(P):
    P = sorted(map(tuple, P))

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return np.array(lo[:-1] + hi[:-1])


Hh = hull(C)
Dm = np.hypot(Hh[:, None, 0] - Hh[None, :, 0], Hh[:, None, 1] - Hh[None, :, 1])
i, j = np.unravel_index(np.argmax(Dm), Dm.shape)
feret_max = float(Dm[i, j]); feret_pts = [Hh[i].tolist(), Hh[j].tolist()]

# ---------------------------------------------------------------- edges: lines and circles
TRIM_C, TRIM_TIP = 30, 170
edges = {}
for a in ARMS:
    spec = {f"{a}_arm_outer": (TRIM_C, TRIM_C), f"{a}_arm_inner": (TRIM_C, TRIM_C),
            f"{a}_hook_back": (TRIM_TIP, TRIM_C), f"{a}_hook_inner": (TRIM_C, TRIM_TIP)}
    for nm, (t0, t1) in spec.items():
        P, Ls = feat_pts(nm, t0, t1)
        ln = robust_line(P); ci = robust_circle(P)
        chord = float(np.hypot(*(P[-1] - P[0])))
        sag = ci["R"] - math.sqrt(max(ci["R"] ** 2 - (chord / 2) ** 2, 0)) if ci["R"] > chord / 2 else float("nan")
        edges[nm] = dict(line=ln, circle=ci, arc_len=Ls, fit_len=chord, sagitta_fit=sag, P=P)

# ---------------------------------------------------------------- arm axes and centre
axes = {}
for a in ARMS:
    lo, li = edges[f"{a}_arm_outer"]["line"], edges[f"{a}_arm_inner"]["line"]
    do, di = lo["d"], li["d"]
    if do @ di < 0:
        di = -di
    axes[a] = dict(p=0.5 * (lo["p"] + li["p"]), d=unit(do + di))
A = np.zeros((2, 2)); b = np.zeros(2)
for a in ARMS:
    n = np.array([-axes[a]["d"][1], axes[a]["d"][0]]); A += np.outer(n, n); b += np.outer(n, n) @ axes[a]["p"]
O = np.linalg.solve(A, b)
axis_miss = {a: abs(dist_to_line(O, axes[a])) for a in ARMS}
for a in ARMS:
    if (axes[a]["p"] - O) @ axes[a]["d"] < 0:
        axes[a]["d"] = -axes[a]["d"]
mfin = np.load(BASE + "/mask_final.npy")
ys, xs = np.nonzero(mfin); centroid = np.array([xs.mean(), ys.mean()])
tip_centre = np.mean([T[a] for a in ARMS], 0)


# ---------------------------------------------------------------- corners (local line fits, fillet radius)
def corner(e_in, e_out, kind):
    P1 = local_pts(e_in, "end", 12, 110); P2 = local_pts(e_out, "start", 12, 110)
    l1 = robust_line(P1); l2 = robust_line(P2); Vc = isect(l1, l2)
    d1 = unit(P1.mean(0) - Vc); d2 = unit(P2.mean(0) - Vc)
    alpha = math.degrees(math.acos(np.clip(d1 @ d2, -1, 1)))
    near = C[np.hypot(*(C - Vc).T) < 60]
    dmin = float(np.hypot(*(near - Vc).T).min())
    sh = math.sin(math.radians(alpha) / 2)
    r_eq = dmin * sh / (1 - sh)
    dev = np.minimum(np.abs([dist_to_line(q, l1) for q in near]), np.abs([dist_to_line(q, l2) for q in near]))
    arc = near[(dev > 1.0) & (np.hypot(*(near - Vc).T) < 45)]
    rc = robust_circle(arc)["R"] if len(arc) >= 8 else None
    return dict(kind=kind, vertex=Vc.tolist(), angle_deg=alpha, setback_px=dmin, fillet_r_equiv_px=r_eq,
                fillet_r_circlefit_px=rc, n_arc_pts=int(len(arc)), line_rms=[l1["rms"], l2["rms"]])


corners = {}
for a in ARMS:
    corners[f"{a}_outer_elbow"] = corner(f"{a}_hook_back", f"{a}_arm_outer", "convex")
    corners[f"centre_{a}_{NEXT[a]}"] = corner(f"{a}_arm_outer", f"{NEXT[a]}_arm_inner", "concave")
    corners[f"{a}_inner_corner"] = corner(f"{a}_arm_inner", f"{a}_hook_inner", "concave")


def ray_circle(p0, d, c, R):
    f = p0 - c; bq = f @ d; cq = f @ f - R * R; disc = bq * bq - cq
    if disc < 0:
        return None
    ts_ = [t for t in (-bq - math.sqrt(disc), -bq + math.sqrt(disc)) if t > 0]
    return float(min(ts_)) if ts_ else None


# ---------------------------------------------------------------- per-arm measurements
arms = {}
for a in ARMS:
    u = axes[a]["d"]; nperp = np.array([-u[1], u[0]])
    lo, li = edges[f"{a}_arm_outer"]["line"], edges[f"{a}_arm_inner"]["line"]
    back, hin = edges[f"{a}_hook_back"], edges[f"{a}_hook_inner"]
    E = np.array(corners[f"{a}_outer_elbow"]["vertex"]); F = np.array(corners[f"{a}_inner_corner"]["vertex"])
    cprev = np.array(corners[f"centre_{PREV[a]}_{a}"]["vertex"]); cnext = np.array(corners[f"centre_{a}_{NEXT[a]}"]["vertex"])
    r_root = float(max((cprev - O) @ u, (cnext - O) @ u))
    r_F = float((F - O) @ u); r_E = float((E - O) @ u)

    def width_at(r):
        lp = dict(p=O + r * u, d=nperp)
        return float(np.hypot(*(isect(lp, lo) - isect(lp, li))))
    w_root = width_at(r_root); w_mid = width_at(0.5 * (r_root + r_F)); w_F = width_at(r_F)
    taper = math.degrees(math.acos(np.clip(abs(lo["d"] @ li["d"]), -1, 1)))
    side_inner = np.sign(cross2(up(u), up(li["p"] - O)))
    v = T[a] - O
    phi = math.degrees(math.atan2(cross2(up(u), up(v)), up(u) @ up(v)))
    reach_outer = abs(dist_to_line(T[a], lo)); reach_inner = abs(dist_to_line(T[a], li))
    bc = back["circle"]; bl = back["line"]
    r_back_axis_circle = ray_circle(O, u, bc["c"], bc["R"])
    r_back_axis_line = float((isect(dict(p=O, d=u), bl) - O) @ u)
    root_w_line = abs(dist_to_line(F, bl))
    root_w_circle = abs(float(np.hypot(*(F - bc["c"])) - bc["R"]))
    dhin = hin["line"]["d"]; dbl = bl["d"]
    arms[a] = dict(
        axis_dir_deg_yup=ang_up(u), r_root=r_root, r_inner_corner=r_F, r_outer_elbow=r_E,
        r_back_edge_on_axis_circle=r_back_axis_circle, r_back_edge_on_axis_line=r_back_axis_line,
        width_root=w_root, width_mid=w_mid, width_at_inner_corner=w_F, taper_deg=taper,
        inner_edge_side="left(CCW)" if side_inner > 0 else "right(CW)",
        tip=T[a].tolist(), tip_radius=float(np.hypot(*v)), tip_angle_from_axis_deg=phi, tip_lateral=cross2(up(u), up(v)),
        tip_reach_from_outer_edge=reach_outer, tip_reach_beyond_inner_edge=reach_inner,
        hook_root_width_line=root_w_line, hook_root_width_circle=root_w_circle,
        hook_inner_edge_vs_axis_deg=math.degrees(math.acos(np.clip(abs(dhin @ u), -1, 1))),
        hook_back_edge_vs_axis_deg=math.degrees(math.acos(np.clip(abs(dbl @ u), -1, 1))),
        tip_angle_between_fitted_lines_deg=math.degrees(math.acos(np.clip(abs(dhin @ dbl), -1, 1))),
        tip_angle_local_deg=tips[a]["tip_angle_deg"],
        tip_setback_from_flank_intersection_px=-tips[a]["apparent_minus_virtual_px"],
        back_edge_contour_len=float(feats[f"{a}_hook_back"]["s1"] - feats[f"{a}_hook_back"]["s0"]),
        inner_edge_contour_len=float(feats[f"{a}_hook_inner"]["s1"] - feats[f"{a}_hook_inner"]["s0"]),
        back_circle_R=bc["R"], back_circle_rms=bc["rms"], back_line_rms=bl["rms"], back_line_maxdev=bl["maxdev"],
        back_sagitta_over_fit=back["sagitta_fit"], back_fit_len=back["fit_len"],
        inner_circle_R=hin["circle"]["R"], inner_circle_rms=hin["circle"]["rms"], inner_line_rms=hin["line"]["rms"],
        inner_line_maxdev=hin["line"]["maxdev"], inner_sagitta_over_fit=hin["sagitta_fit"], inner_fit_len=hin["fit_len"],
        outer_line_rms=lo["rms"], inner_arm_line_rms=li["rms"])
    for key, e in (("back", back), ("inner", hin)):
        mid = e["P"][len(e["P"]) // 2]; c = e["circle"]["c"]; probe = mid + 6 * unit(c - mid)
        inside = bool(mfin[int(round(np.clip(probe[1], 0, H - 1))), int(round(np.clip(probe[0], 0, W - 1)))])
        arms[a][f"{key}_edge_shape"] = "convex (bulges outward)" if inside else "concave (hollowed)"

axis_angles = {f"{a}-{NEXT[a]}": math.degrees(math.acos(np.clip(axes[a]["d"] @ axes[NEXT[a]]["d"], -1, 1))) for a in ARMS}
opp = {"top-bottom": 180 - math.degrees(math.acos(np.clip(axes["top"]["d"] @ axes["bottom"]["d"], -1, 1))),
       "right-left": 180 - math.degrees(math.acos(np.clip(axes["right"]["d"] @ axes["left"]["d"], -1, 1)))}
hand = {a: float(np.sign(cross2(up(axes[a]["d"]), up(T[a] - O)))) for a in ARMS}
b2b_v = (arms["top"]["r_back_edge_on_axis_circle"] or 0) + (arms["bottom"]["r_back_edge_on_axis_circle"] or 0)
b2b_h = (arms["right"]["r_back_edge_on_axis_circle"] or 0) + (arms["left"]["r_back_edge_on_axis_circle"] or 0)
angs = [math.atan2(axes["right"]["d"][1], axes["right"]["d"][0]),
        math.atan2(-axes["left"]["d"][1], -axes["left"]["d"][0]),
        math.atan2(axes["bottom"]["d"][1], axes["bottom"]["d"][0]) - math.pi / 2,
        math.atan2(-axes["top"]["d"][1], -axes["top"]["d"][0]) - math.pi / 2]
th = float(np.angle(np.mean(np.exp(1j * np.array(angs)))))
ex = np.array([math.cos(th), math.sin(th)]); ey = np.array([-math.sin(th), math.cos(th)])
ext_x = float((C @ ex).max() - (C @ ex).min()); ext_y = float((C @ ey).max() - (C @ ey).min())
rr = 0.5 * min(arms[a]["width_root"] for a in ARMS)
YY, XX = np.mgrid[0:H, 0:W]; disc = np.hypot(XX - O[0], YY - O[1]) < rr
seg_info = json.load(open(BASE + "/segment_info.json"))
out = dict(
    image=dict(width=W, height=H),
    contour=dict(points=int(N), dp_eps_px=1.5, dp_vertices=len(dp), perimeter_px=float(P_)),
    span=dict(tip_top_to_tip_bottom_px=d_tb, tip_right_to_tip_left_px=d_rl, span_ref_px=SPAN,
              feret_max_px=feret_max, feret_pts=feret_pts, extent_along_arm_frame_px=[ext_x, ext_y],
              back_to_back_through_centre_px=dict(vertical=b2b_v, horizontal=b2b_h), frame_rotation_deg_img=math.degrees(th)),
    centre=dict(axes_intersection=O.tolist(), axis_miss_px=axis_miss, mask_centroid=centroid.tolist(), tip_centroid=tip_centre.tolist(),
                centre_disc_radius_px=float(rr), centre_disc_L_max=float(L[disc].max()), centre_disc_L_p99=float(np.percentile(L[disc], 99)),
                centre_disc_bglike_px=int((L[disc] > 0.6).sum()), coarse_enclosed_regions=seg_info["holes"]),
    axis_angles_adjacent_deg=axis_angles, axis_opposite_deviation_from_straight_deg=opp, handedness_sign=hand,
    arms=arms, corners=corners,
    edges={k: dict(line=dict(dir_deg_yup=ang_up(v["line"]["d"]), rms=v["line"]["rms"], maxdev=v["line"]["maxdev"], n=v["line"]["n"], n_all=v["line"]["n_all"]),
                   circle=dict(centre=v["circle"]["c"].tolist(), R=v["circle"]["R"], rms=v["circle"]["rms"]),
                   fit_len=v["fit_len"], contour_len=v["arc_len"], sagitta_over_fit=v["sagitta_fit"]) for k, v in edges.items()},
)


def conv(o):
    if isinstance(o, dict):
        return {k: conv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [conv(v) for v in o]
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.ndarray):
        return conv(o.tolist())
    return o


json.dump(conv(out), open(BASE + "/measurements_raw.json", "w"), indent=1)
np.save(BASE + "/fit_state.npy", np.array(dict(
    O=O, axes=axes, T=T, Vt=Vt, SPAN=SPAN,
    edges={k: dict(p=v["line"]["p"], d=v["line"]["d"], c=v["circle"]["c"], R=v["circle"]["R"], P0=v["P"][0], P1=v["P"][-1]) for k, v in edges.items()},
    corners=corners), dtype=object), allow_pickle=True)
print(json.dumps(conv({k: out[k] for k in ("contour", "span", "centre", "axis_angles_adjacent_deg", "axis_opposite_deviation_from_straight_deg", "handedness_sign")}), indent=1))
for a in ARMS:
    print("ARM", a, json.dumps(conv(arms[a])))
for k, v in corners.items():
    print("CORNER", k, json.dumps(conv(v)))
for k, v in out["edges"].items():
    print("EDGE", k, json.dumps(conv(v)))
