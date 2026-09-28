"""Reconciler measurement v2: gradient-peak sub-pixel edges (pedestal-immune),
outermost-edge rule on flanks, robust fits, shadow classification.
"""
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
SDIR = np.array([np.cos(np.radians(305.0)), np.sin(np.radians(305.0))])

rgb = rio.load_rgb(IMG)
H, W, _ = rgb.shape
L = rio.lum(rgb)
Lb = rio.blur(L, 0.8)


def edge_on_profile(v, step, rising, min_amp=0.12, bg_check=None):
    """Return sub-sample index of the chosen edge on profile v (sampled every `step`).
    rising: L increases with index across the edge. Picks the OUTERMOST (largest index)
    local derivative peak with amplitude >= min_amp; if bg_check is given, the profile
    after the edge must stay beyond bg_check."""
    d = np.gradient(v, step)
    dd = d if rising else -d
    cand = []
    for i in range(2, len(dd) - 2):
        if dd[i] >= dd[i - 1] and dd[i] >= dd[i + 1] and dd[i] > 0:
            lo = max(0, i - int(3 / step))
            hi = min(len(v), i + int(3 / step) + 1)
            amp = abs(v[hi - 1] - v[lo])
            if amp >= min_amp:
                cand.append((i, dd[i], amp))
    if not cand:
        return None
    if bg_check is not None:
        ok = []
        for i, g, amp in cand:
            tail = v[min(len(v) - 1, i + int(4 / step)):]
            if len(tail) and (tail.min() > bg_check if rising else tail.max() < bg_check):
                ok.append((i, g, amp))
        if ok:
            cand = ok
    i = max(cand, key=lambda c: c[0])[0]
    # keep the strongest peak within 3 px of the outermost accepted one
    near = [c for c in cand if abs(c[0] - i) * step <= 3.0]
    i = max(near, key=lambda c: c[1])[0]
    return rio.peak_refine(dd, i)


def ray_edges(cx, cy, angles, r0, r1, rising, min_amp=0.15, bg_check=None):
    step = 0.2
    rr = np.arange(r0, r1, step)
    out = []
    for a in angles:
        th = np.radians(a)
        ux, uy = np.cos(th), np.sin(th)
        px, py = cx + ux * rr, cy + uy * rr
        if px.min() < 2 or px.max() > W - 3 or py.min() < 2 or py.max() > H - 3:
            continue
        v = rio.sample(Lb, px, py)
        i = edge_on_profile(v, step, rising, min_amp, bg_check)
        if i is None:
            continue
        r = r0 + i * step
        out.append((a % 360.0, r, float(np.array([ux, uy]) @ SDIR)))
    return np.array(out)


def robust_circle(x, y, tol=2.0, iters=5):
    keep = np.ones(len(x), bool)
    for _ in range(iters):
        cx, cy, r, rms = rio.fit_circle(x[keep], y[keep])
        d = np.hypot(x - cx, y - cy) - r
        keep = np.abs(d) < max(tol, 3 * rms)
    cx, cy, r, rms = rio.fit_circle(x[keep], y[keep])
    return cx, cy, r, rms, keep


res = {}

# ---------------------------------------------------------------- HOLE
cx, cy = 630.5, 527.0
for it in range(5):
    angs = np.arange(0, 360, 0.5)
    pts = ray_edges(cx, cy, angs, 100, 175, rising=False, min_amp=0.15)
    sel = pts[:, 2] > -0.15          # exclude the strongly shadowed down-left rim
    x = cx + np.cos(np.radians(pts[sel, 0])) * pts[sel, 1]
    y = cy + np.sin(np.radians(pts[sel, 0])) * pts[sel, 1]
    ncx, ncy, nr, rms, keep = robust_circle(x, y)
    if abs(ncx - cx) < 0.02 and abs(ncy - cy) < 0.02:
        cx, cy = ncx, ncy
        break
    cx, cy = ncx, ncy
hole_pts = pts
xs = cx + np.cos(np.radians(pts[:, 0])) * pts[:, 1]
ys = cy + np.sin(np.radians(pts[:, 0])) * pts[:, 1]
res['hole'] = {}
for tag, m in (("litneutral", pts[:, 2] > -0.15), ("lit", pts[:, 2] > 0.35),
               ("all", np.ones(len(pts), bool))):
    a, b, r, rms, keep = robust_circle(xs[m], ys[m])
    res['hole'][tag] = dict(cx=a, cy=b, r=r, rms=rms, n=int(m.sum()), nkeep=int(keep.sum()))
res['hole']['ellipse_litneutral'] = rio.fit_ellipse(xs[pts[:, 2] > -0.15], ys[pts[:, 2] > -0.15])
HOLE = res['hole']['litneutral']
hc = np.array([HOLE['cx'], HOLE['cy']])
# residual by direction sector (about the litneutral fit)
sect = {}
for a0 in range(0, 360, 30):
    m = (pts[:, 0] >= a0) & (pts[:, 0] < a0 + 30)
    if m.sum() < 5:
        continue
    d = np.hypot(xs[m] - hc[0], ys[m] - hc[1]) - HOLE['r']
    sect[a0] = [float(np.median(d)), float(np.median(pts[m, 2])), int(m.sum())]
res['hole']['sector_resid'] = sect

# ---------------------------------------------------------------- HUB
axes_img = np.array([-61.6561, -1.3513, 58.8581, 118.1469, 177.9719, -121.5356])
axes_img = np.sort(np.mod(axes_img, 360.0))
cxh, cyh = hc[0], hc[1]
for it in range(4):
    allp = []
    for k in range(6):
        a0 = axes_img[k]
        a1 = axes_img[(k + 1) % 6] + (360.0 if k == 5 else 0.0)
        mid = 0.5 * (a0 + a1)
        p = ray_edges(cxh, cyh, np.arange(mid - 11, mid + 11.001, 0.25), 250, 340,
                      rising=True, min_amp=0.15)
        if len(p):
            p = np.column_stack([p, np.full(len(p), k)])
            allp.append(p)
    hub_pts = np.vstack(allp)
    top = np.argmax([np.mean(hub_pts[hub_pts[:, 3] == k][:, 2]) for k in range(6)])
    m = hub_pts[:, 3] != top
    x = cxh + np.cos(np.radians(hub_pts[m, 0])) * hub_pts[m, 1]
    y = cyh + np.sin(np.radians(hub_pts[m, 0])) * hub_pts[m, 1]
    ncx, ncy, nr, rms, keep = robust_circle(x, y)
    if abs(ncx - cxh) < 0.02 and abs(ncy - cyh) < 0.02:
        cxh, cyh = ncx, ncy
        break
    cxh, cyh = ncx, ncy
xs2 = cxh + np.cos(np.radians(hub_pts[:, 0])) * hub_pts[:, 1]
ys2 = cyh + np.sin(np.radians(hub_pts[:, 0])) * hub_pts[:, 1]
res['hub'] = {}
for tag, m in (("no_top", hub_pts[:, 3] != top), ("all", np.ones(len(hub_pts), bool)),
               ("lit", hub_pts[:, 2] < -0.35)):
    a, b, r, rms, keep = robust_circle(xs2[m], ys2[m])
    res['hub'][tag] = dict(cx=a, cy=b, r=r, rms=rms, n=int(m.sum()), nkeep=int(keep.sum()))
res['hub']['ellipse_no_top'] = rio.fit_ellipse(xs2[hub_pts[:, 3] != top], ys2[hub_pts[:, 3] != top])
HUB = res['hub']['no_top']
HC = np.array([HUB['cx'], HUB['cy']])
RH = HUB['r']
per_arc = {}
for k in range(6):
    m = hub_pts[:, 3] == k
    d = np.hypot(xs2[m] - HC[0], ys2[m] - HC[1])
    per_arc[int(k)] = dict(mean=float(d.mean()), sd=float(d.std()), n=int(m.sum()),
                           shadow=float(np.mean(hub_pts[m, 2])))
res['hub']['per_arc'] = per_arc
res['hub']['top_arc_index'] = int(top)
print("HOLE", HOLE)
print("HUB", HUB)
print("per arc", {k: (round(v['mean'], 2), round(v['sd'], 2), round(v['shadow'], 2)) for k, v in per_arc.items()})

# ---------------------------------------------------------------- FLANKS
ALPHA = np.radians(25.1)
RAPEX = 605.0


def flank_points(axis_deg, sgn, hw_model, window=25.0):
    a = np.array([np.cos(np.radians(axis_deg)), np.sin(np.radians(axis_deg))])
    q = np.array([-a[1], a[0]]) * sgn
    pts = []
    step = 0.2
    for t in np.arange(RH + 22, RAPEX - 50, 1.0):
        base = HC + a * t + q * hw_model(t)
        ss = np.arange(-window, window + step, step)
        px, py = base[0] + q[0] * ss, base[1] + q[1] * ss
        if px.min() < 2 or px.max() > W - 3 or py.min() < 2 or py.max() > H - 3:
            continue
        v = rio.sample(Lb, px, py)
        if np.median(v[-15:]) - np.median(v[:15]) < 0.2:
            continue
        i = edge_on_profile(v, step, True, 0.15, bg_check=0.55)
        if i is None:
            continue
        s = -window + i * step
        p = base + q * s
        pts.append((t, p[0], p[1], s))
    return np.array(pts), a, q


flanks = {}
axes = axes_img.copy()
for it in range(3):
    new_axes = []
    flanks = {}
    for k in range(6):
        aimg = axes[k]
        got = {}
        for sgn in (+1, -1):
            key = "p%d%s" % (k, "A" if sgn > 0 else "B")
            if it == 0:
                hw = lambda t: max(3.0, (RAPEX - t) * np.tan(ALPHA / 2))
            else:
                prev = flanks_prev.get(key)
                if prev is None:
                    hw = lambda t: max(3.0, (RAPEX - t) * np.tan(ALPHA / 2))
                else:
                    p0 = np.array(prev['p']); u0 = np.array(prev['u'])
                    a_ = np.array([np.cos(np.radians(aimg)), np.sin(np.radians(aimg))])
                    q_ = np.array([-a_[1], a_[0]]) * sgn
                    def hw(t, p0=p0, u0=u0, a_=a_, q_=q_):
                        # distance along q_ from axis point to the previous fitted line
                        n_ = np.array([-u0[1], u0[0]])
                        denom = q_ @ n_
                        if abs(denom) < 1e-6:
                            return 3.0
                        return float(((p0 - (HC + a_ * t)) @ n_) / denom)
            win = 25.0 if it == 0 else 8.0
            pts, a, q = flank_points(aimg, sgn, hw, win)
            if len(pts) < 20:
                continue
            xs3, ys3 = pts[:, 1], pts[:, 2]
            keep = np.ones(len(xs3), bool)
            for _ in range(5):
                p0, u0, rms, _ = rio.fit_line_tls(xs3[keep], ys3[keep])
                nres = np.stack([xs3 - p0[0], ys3 - p0[1]], 1) @ np.array([-u0[1], u0[0]])
                keep = np.abs(nres) < 2.0
                if keep.sum() < 10:
                    keep = np.abs(nres) < 4.0
                    break
            p0, u0, rms, _ = rio.fit_line_tls(xs3[keep], ys3[keep])
            half = len(pts) // 2
            pin, uin, _, _ = rio.fit_line_tls(xs3[:half], ys3[:half])
            pout, uout, _, _ = rio.fit_line_tls(xs3[half:], ys3[half:])
            tt = np.stack([xs3[keep] - p0[0], ys3[keep] - p0[1]], 1) @ u0
            nn = np.stack([xs3[keep] - p0[0], ys3[keep] - p0[1]], 1) @ np.array([-u0[1], u0[0]])
            cf = np.polyfit(tt, nn, 2)
            got[key] = dict(k=k, sgn=int(sgn), n=int(len(pts)), nkeep=int(keep.sum()),
                            p=[float(p0[0]), float(p0[1])], u=[float(u0[0]), float(u0[1])],
                            rms=float(rms), shadow=float(q @ SDIR),
                            sagitta=float(cf[0] * ((tt.max() - tt.min()) / 2) ** 2),
                            u_in=[float(uin[0]), float(uin[1])], u_out=[float(uout[0]), float(uout[1])],
                            dist_from_centre=float(abs((HC - p0) @ np.array([-u0[1], u0[0]]))),
                            t_range=[float(pts[0, 0]), float(pts[-1, 0])])
        flanks.update(got)
        ka, kb = "p%dA" % k, "p%dB" % k
        if ka in got and kb in got:
            pa, ua = np.array(got[ka]['p']), np.array(got[ka]['u'])
            pb, ub = np.array(got[kb]['p']), np.array(got[kb]['u'])
            if ua @ (HC - pa) > 0:
                ua = -ua
            if ub @ (HC - pb) > 0:
                ub = -ub
            apex = rio.line_intersect(pa, ua, pb, ub)
            bis = apex - HC
            new_axes.append(float(np.degrees(np.arctan2(bis[1], bis[0])) % 360.0))
        else:
            new_axes.append(float(axes[k]))
    flanks_prev = flanks
    axes = np.array(new_axes)

points = {}
for k in range(6):
    fa, fb = flanks["p%dA" % k], flanks["p%dB" % k]
    pa, ua = np.array(fa['p']), np.array(fa['u'])
    pb, ub = np.array(fb['p']), np.array(fb['u'])
    if ua @ (HC - pa) > 0:
        ua = -ua
    if ub @ (HC - pb) > 0:
        ub = -ub
    apex = rio.line_intersect(pa, ua, pb, ub)
    ang = float(np.degrees(np.arccos(np.clip(ua @ ub, -1, 1))))
    axis = apex - HC

    def circ_hit(p, u):
        f = p - HC
        b = 2 * (f @ u)
        c = f @ f - RH ** 2
        disc = b * b - 4 * c
        if disc < 0:
            return None
        ts = [(-b + np.sqrt(disc)) / 2, (-b - np.sqrt(disc)) / 2]
        cands = [p + t * u for t in ts]
        return max(cands, key=lambda z: (z - HC) @ (axis / np.linalg.norm(axis)))
    ha, hb = circ_hit(pa, ua), circ_hit(pb, ub)
    base = float(np.linalg.norm(ha - hb))
    base_ang = float(np.degrees(np.arccos(np.clip(((ha - HC) / RH) @ ((hb - HC) / RH), -1, 1))))
    points[k] = dict(apex=[float(apex[0]), float(apex[1])], apex_r=float(np.linalg.norm(axis)),
                     tip_angle=ang, axis_deg=float(np.degrees(np.arctan2(axis[1], axis[0])) % 360.0),
                     base_chord=base, base_angle=base_ang,
                     root=[[float(ha[0]), float(ha[1])], [float(hb[0]), float(hb[1])]],
                     flank_dist=[fa['dist_from_centre'], fb['dist_from_centre']],
                     shadow=[fa['shadow'], fb['shadow']], rms=[fa['rms'], fb['rms']],
                     nkeep=[fa['nkeep'], fb['nkeep']], n=[fa['n'], fb['n']],
                     sagitta=[fa['sagitta'], fb['sagitta']])

# ---------------------------------------------------------------- TIPS (50% along axis)
tips = {}
for k in range(6):
    aimg = points[k]['axis_deg']
    a = np.array([np.cos(np.radians(aimg)), np.sin(np.radians(aimg))])
    q = np.array([-a[1], a[0]])
    tt = np.arange(points[k]['apex_r'] - 90, points[k]['apex_r'] + 35, 0.2)
    px, py = HC[0] + a[0] * tt, HC[1] + a[1] * tt
    ok = (px > 2) & (px < W - 3) & (py > 2) & (py < H - 3)
    clipped = not ok.all()
    tt = tt[ok]
    prof = np.zeros_like(tt)
    for off in (-0.6, 0.0, 0.6):
        prof += rio.sample(Lb, HC[0] + a[0] * tt + q[0] * off, HC[1] + a[1] * tt + q[1] * off) / 3
    ins = float(np.median(prof[:60]))
    out = float(np.median(prof[-40:])) if not clipped else None
    r50 = None
    if out is not None:
        mid = 0.5 * (ins + out)
        j = np.flatnonzero(prof > mid)
        if len(j) and j[0] > 0:
            v0, v1 = prof[j[0] - 1], prof[j[0]]
            r50 = float(tt[j[0] - 1] + (mid - v0) / (v1 - v0) * 0.2)
    tips[k] = dict(clipped=bool(clipped), r50=r50, plate=ins, bg=out,
                   apex_r=points[k]['apex_r'],
                   gap=(points[k]['apex_r'] - r50) if r50 else None)

res['flanks'] = flanks
res['points'] = {str(k): v for k, v in points.items()}
res['tips'] = {str(k): v for k, v in tips.items()}
res['axes_deg'] = [float(v) for v in axes]
with open(os.path.join(HERE, "recon2.json"), "w") as f:
    json.dump(res, f, indent=1)
np.save(os.path.join(HERE, "hole_pts2.npy"), hole_pts)
np.save(os.path.join(HERE, "hub_pts2.npy"), hub_pts)

print("tip angles", [round(points[k]['tip_angle'], 2) for k in range(6)])
print("apex r    ", [round(points[k]['apex_r'], 1) for k in range(6)])
print("base chord", [round(points[k]['base_chord'], 1) for k in range(6)])
print("flank rms ", [(round(flanks["p%dA" % k]['rms'], 2), round(flanks["p%dB" % k]['rms'], 2)) for k in range(6)])
print("tips r50  ", [None if tips[k]['r50'] is None else round(tips[k]['r50'], 1) for k in range(6)])
print("axes      ", [round(v, 2) for v in axes])
print("done")
