import numpy as np, json
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/"
OUT = D + "reconcile/"

B = np.load(D + "contour/mask_final.npy").astype(bool)
Ar = np.load(D + "radial/mask.npy")
A = np.unpackbits(Ar)[: B.size].reshape(B.shape).astype(bool)
H, W = B.shape
MASKS = {"A": A, "B": B}

def subpix_edge(M, px, py, dx, dy, lo, hi, step=0.05):
    """walk along (dx,dy) from lo..hi, return last t where inside (nearest-neighbour)."""
    t = np.arange(lo, hi, step)
    xi = np.clip(np.round(px + dx * t).astype(int), 0, W - 1)
    yi = np.clip(np.round(py + dy * t).astype(int), 0, H - 1)
    ins = M[yi, xi]
    if not ins.any():
        return None
    return t[len(t) - 1 - np.argmax(ins[::-1])]

def tls_line(u, v):
    """fit v = a + b u by robust TLS-ish (iterative reweighting on residual)."""
    w = np.ones_like(u)
    for _ in range(8):
        sw = w.sum()
        um = (w * u).sum() / sw; vm = (w * v).sum() / sw
        du = u - um; dv = v - vm
        sxx = (w * du * du).sum(); sxy = (w * du * dv).sum(); syy = (w * dv * dv).sum()
        th = 0.5 * np.arctan2(2 * sxy, sxx - syy)
        nx, ny = -np.sin(th), np.cos(th)
        c = -(nx * um + ny * vm)
        r = nx * u + ny * v + c
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-6
        w = 1.0 / (1.0 + (r / (2.5 * s)) ** 2)
    b = -nx / ny
    a = -c / ny
    rms = float(np.sqrt((r ** 2).mean()))
    return a, b, rms

def fit_circle(x, y):
    Amat = np.stack([x, y, np.ones_like(x)], 1)
    bvec = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(Amat, bvec, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(sol[2] + cx ** 2 + cy ** 2)
    rms = float(np.sqrt(((np.hypot(x - cx, y - cy) - r) ** 2).mean()))
    return cx, cy, r, rms

results = {}
for name, M in MASKS.items():
    ys, xs = np.nonzero(M)
    cx, cy = xs.mean(), ys.mean()
    # --- tips (fine radial search) ---
    th = np.arange(0, 360, 0.02)
    rad = np.deg2rad(th)
    rr = np.arange(1200, 1500, 0.1)
    X = cx + np.outer(np.cos(rad), rr); Y = cy - np.outer(np.sin(rad), rr)
    ins = M[np.clip(np.round(Y).astype(int), 0, H - 1), np.clip(np.round(X).astype(int), 0, W - 1)]
    idx = ins.shape[1] - 1 - np.argmax(ins[:, ::-1], axis=1)
    rprof = np.where(ins.any(1), rr[idx], 0)
    tips = []
    for k in range(4):
        m = (th >= k * 90 - 45) & (th < k * 90 + 45) if k else ((th < 45) | (th >= 315))
        st, sr = th[m], rprof[m]
        j = np.argmax(sr)
        # centroid of near-max points for stability
        sel = sr > sr[j] - 1.0
        tt = st[sel]
        if tt.max() - tt.min() > 180:
            tt = np.where(tt > 180, tt - 360, tt)
        ta = tt.mean() % 360
        tips.append((ta, sr[j]))
    tips.sort()
    span = 0.5 * (np.hypot(*(np.array([np.cos(np.deg2rad(tips[0][0])) * tips[0][1], -np.sin(np.deg2rad(tips[0][0])) * tips[0][1]]) -
                            np.array([np.cos(np.deg2rad(tips[2][0])) * tips[2][1], -np.sin(np.deg2rad(tips[2][0])) * tips[2][1]]))) +
                 np.hypot(*(np.array([np.cos(np.deg2rad(tips[1][0])) * tips[1][1], -np.sin(np.deg2rad(tips[1][0])) * tips[1][1]]) -
                            np.array([np.cos(np.deg2rad(tips[3][0])) * tips[3][1], -np.sin(np.deg2rad(tips[3][0])) * tips[3][1]]))))
    per_arm = []
    for k in range(4):
        tip_th, tip_r = tips[k]
        phi = np.deg2rad(tip_th - 35.0)   # initial arm axis guess
        for it in range(6):
            ux, uy = np.cos(phi), -np.sin(phi)          # image-space unit along axis
            vx, vy = -np.sin(phi), -np.cos(phi)         # +v = CCW side in y-up terms
            us = np.arange(0.10, 0.325, 0.002) * span
            vp, vm_ = [], []
            for u in us:
                px, py = cx + ux * u, cy + uy * u
                tp = subpix_edge(M, px, py, vx, vy, 0, 0.12 * span)
                tm = subpix_edge(M, px, py, -vx, -vy, 0, 0.12 * span)
                vp.append(tp if tp is not None else np.nan)
                vm_.append(-tm if tm is not None else np.nan)
            vp = np.array(vp); vm_ = np.array(vm_)
            ok = ~np.isnan(vp) & ~np.isnan(vm_)
            a1, b1, r1 = tls_line(us[ok], vp[ok])   # leading (hook side, +v)
            a2, b2, r2 = tls_line(us[ok], vm_[ok])  # trailing (-v)
            phi += 0.5 * (b1 + b2)                  # rotate so bisector is the axis
        ux, uy = np.cos(phi), -np.sin(phi)
        vx, vy = -np.sin(phi), -np.cos(phi)
        tipx = cx + np.cos(np.deg2rad(tip_th)) * tip_r
        tipy = cy - np.sin(np.deg2rad(tip_th)) * tip_r
        du = (tipx - cx) * ux + (tipy - cy) * uy
        dv = (tipx - cx) * vx + (tipy - cy) * vy

        # hook inner corner: where the leading boundary leaves the fitted line
        uu = np.arange(0.25, 0.42, 0.001) * span
        vhi = []
        for u in uu:
            px, py = cx + ux * u, cy + uy * u
            tp = subpix_edge(M, px, py, vx, vy, 0, 0.35 * span)
            vhi.append(tp if tp is not None else np.nan)
        vhi = np.array(vhi)
        dev = vhi - (a1 + b1 * uu)
        j = np.argmax(dev > 3.0)
        u_hook = uu[j]; v_hook = a1 + b1 * u_hook
        # outer elbow: where trailing boundary leaves its line
        vlo = []
        for u in uu:
            px, py = cx + ux * u, cy + uy * u
            tm = subpix_edge(M, px, py, -vx, -vy, 0, 0.35 * span)
            vlo.append(-tm if tm is not None else np.nan)
        vlo = np.array(vlo)
        ok2 = ~np.isnan(vlo)
        dev2 = np.where(ok2, vlo - (a2 + b2 * uu), np.nan)
        bad = ok2 & (np.abs(uu - uu[0]) > 0)
        j2 = np.argmax(~ok2 | (np.abs(dev2) > 3.0))
        u_elbow = uu[j2]

        # back arc: u_max(v) for v from just above trailing edge to near the tip
        vs = np.arange(a2 + b2 * u_elbow + 8, dv - 60, 2.0)
        uarc = []
        for v in vs:
            px, py = cx + vx * v, cy + vy * v
            tt = subpix_edge(M, px, py, ux, uy, 0.20 * span, 0.50 * span)
            uarc.append(tt if tt is not None else np.nan)
        uarc = np.array(uarc); okA = ~np.isnan(uarc)
        ccx, ccy, crad, crms = fit_circle(uarc[okA], vs[okA])
        # on-axis back-arc radius
        u_axis_back = ccx + np.sqrt(max(crad ** 2 - ccy ** 2, 0))
        # sagitta over the fitted chord
        chord = np.hypot(uarc[okA][0] - uarc[okA][-1], vs[okA][0] - vs[okA][-1])
        sag = crad - np.sqrt(max(crad ** 2 - (chord / 2) ** 2, 0))
        # B-style hook root width: along-arm run at the hook corner's v
        px, py = cx + vx * v_hook, cy + vy * v_hook
        u_back_at_hook = subpix_edge(M, px, py, ux, uy, 0.20 * span, 0.50 * span)
        hook_root_B = u_back_at_hook - u_hook
        # A-style: width of the hook parallel to the arm axis, linear fit of w(f) extrapolated to the arm edge
        fr = np.linspace(0.12, 0.75, 22)
        ws, vvs = [], []
        for f in fr:
            v = v_hook + f * (dv - v_hook)
            px, py = cx + vx * v, cy + vy * v
            t_far = subpix_edge(M, px, py, ux, uy, 0.20 * span, 0.50 * span)
            t_near = subpix_edge(M, px, py, -ux, -uy, -0.50 * span, -0.15 * span)
            # inner boundary: march inward from the far edge until leaving the mask
            tt = np.arange(t_far, 0.15 * span, -0.05)
            xi = np.clip(np.round(px + ux * tt).astype(int), 0, W - 1)
            yi = np.clip(np.round(py + uy * tt).astype(int), 0, H - 1)
            insl = M[yi, xi]
            k2 = np.argmax(~insl)
            t_in = tt[k2]
            ws.append(t_far - t_in); vvs.append(f)
        ws = np.array(ws); vvs = np.array(vvs)
        pf = np.polyfit(vvs, ws, 1)
        hook_root_A = float(np.polyval(pf, 0.0))

        # hook inner (straight) edge angle to arm axis
        pts_u, pts_v = [], []
        for f in np.linspace(0.10, 0.85, 40):
            v = v_hook + f * (dv - v_hook)
            px, py = cx + vx * v, cy + vy * v
            t_far = subpix_edge(M, px, py, ux, uy, 0.20 * span, 0.50 * span)
            tt = np.arange(t_far, 0.15 * span, -0.05)
            xi = np.clip(np.round(px + ux * tt).astype(int), 0, W - 1)
            yi = np.clip(np.round(py + uy * tt).astype(int), 0, H - 1)
            k2 = np.argmax(~M[yi, xi])
            pts_u.append(tt[k2]); pts_v.append(v)
        pts_u = np.array(pts_u); pts_v = np.array(pts_v)
        ai, bi, rmsi = tls_line(pts_v, pts_u)   # u = ai + bi v
        inner_ang = 90.0 - np.degrees(np.arctan(abs(bi)))

        # tip included angle at several window lengths
        tipang = {}
        for wlo, whi in ((10, 80), (20, 150), (20, 300), (110, 420), (30, 600)):
            # flank points: walk back from the tip along the bisector, measure both flanks
            bis = np.arctan2(dv - (a1 + b1 * du), 0)  # unused
            f1u, f1v, f2u, f2v = [], [], [], []
            for s in np.linspace(wlo, whi, 60):
                # cut perpendicular to the tip->centre-ish direction: use the line v = dv - s*sin, simple: cut along v
                v = dv - s * np.cos(np.deg2rad(15.0))
                px, py = cx + vx * v, cy + vy * v
                t_far = subpix_edge(M, px, py, ux, uy, 0.20 * span, 0.50 * span)
                if t_far is None: continue
                tt = np.arange(t_far, 0.15 * span, -0.05)
                xi = np.clip(np.round(px + ux * tt).astype(int), 0, W - 1)
                yi = np.clip(np.round(py + uy * tt).astype(int), 0, H - 1)
                k2 = np.argmax(~M[yi, xi])
                f1u.append(t_far); f1v.append(v)          # back (outer) edge
                f2u.append(tt[k2]); f2v.append(v)         # inner edge
            if len(f1u) < 6: continue
            a_b, b_b, _ = tls_line(np.array(f1v), np.array(f1u))
            a_i, b_i, _ = tls_line(np.array(f2v), np.array(f2u))
            tipang["%d-%d" % (wlo, whi)] = float(abs(np.degrees(np.arctan(b_b) - np.arctan(b_i))))

        per_arm.append(dict(
            tip_th=float(tip_th), tip_r=float(tip_r), phi_deg=float(np.degrees(phi)),
            tip_off_axis_deg=float(np.degrees(np.arctan2(dv, du))),
            tip_u=float(du), tip_v=float(dv),
            w_centre=float(a1 - a2), w_at_hookcorner=float((a1 - a2) + (b1 - b2) * u_hook),
            taper_deg=float(np.degrees(np.arctan(b1) - np.arctan(b2))),
            edge_rms=[r1, r2],
            u_hook=float(u_hook), v_hook=float(v_hook), u_elbow=float(u_elbow),
            hook_root_B=float(hook_root_B), hook_root_A=float(hook_root_A),
            overhang_perp=float((dv - (a1 + b1 * du)) * np.cos(np.arctan(b1))),
            overhang_from_trailing=float((dv - (a2 + b2 * du)) * np.cos(np.arctan(b2))),
            arc_radius=float(crad), arc_rms=float(crms), arc_sagitta=float(sag),
            u_axis_back=float(u_axis_back),
            inner_edge_angle=float(inner_ang), inner_edge_rms=float(rmsi),
            tip_angles=tipang))
    results[name] = dict(centre=[float(cx), float(cy)], span=float(span), tips=tips, arms=per_arm)

json.dump(results, open(OUT + "remeasure.json", "w"), indent=1, default=float)

def agg(name, key, scale=None):
    out = {}
    for m in ("A", "B"):
        sp = results[m]["span"]
        v = np.array([a[key] for a in results[m]["arms"]], float)
        if scale == "span": v = v / sp
        out[m] = (v.mean(), v.std(), v)
    print("%-26s A %9.5f +-%.5f   B %9.5f +-%.5f   diff %+.5f"
          % (name, out["A"][0], out["A"][1], out["B"][0], out["B"][1], out["A"][0] - out["B"][0]))
    return out

print("\nspan  A %.2f  B %.2f" % (results["A"]["span"], results["B"]["span"]))
agg("tip_off_axis_deg", "tip_off_axis_deg")
agg("w_centre/span", "w_centre", "span")
agg("w_at_hookcorner/span", "w_at_hookcorner", "span")
agg("taper_deg", "taper_deg")
agg("u_hook/span", "u_hook", "span")
agg("u_elbow/span", "u_elbow", "span")
agg("u_axis_back/span", "u_axis_back", "span")
agg("hook_root_B/span", "hook_root_B", "span")
agg("hook_root_A/span", "hook_root_A", "span")
agg("overhang_perp/span", "overhang_perp", "span")
agg("overhang_trailing/span", "overhang_from_trailing", "span")
agg("tip_v/span", "tip_v", "span")
agg("tip_u/span", "tip_u", "span")
agg("arc_radius/span", "arc_radius", "span")
agg("arc_sagitta/span", "arc_sagitta", "span")
agg("inner_edge_angle", "inner_edge_angle")
print("\ntip included angle vs window:")
for k in results["A"]["arms"][0]["tip_angles"]:
    for m in ("A", "B"):
        v = np.array([a["tip_angles"][k] for a in results[m]["arms"]])
        print("  %-9s %s  %6.2f +- %.2f" % (k, m, v.mean(), v.std()))
