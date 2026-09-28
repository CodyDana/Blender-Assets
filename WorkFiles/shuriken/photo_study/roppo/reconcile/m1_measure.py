"""Reconciler's own sub-pixel edge measurement of Roppo.JPG.

Method: no binary mask. Sub-pixel edge localisation by (a) steepest-gradient
peak and (b) 50% level crossing, on a lightly blurred luminance image, sampled
along rays (hole rim, hub arcs) and along perpendicular stations (point flanks).
Edges are classified lit / neutral / shadowed from the cast-shadow direction so
that primary fits use only shadow-free edges.
"""
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
OUT = HERE

# cast-shadow direction in image coords (x right, y down); from method B: 305 deg
SDIR = np.array([np.cos(np.radians(305.0)), np.sin(np.radians(305.0))])

rgb = rio.load_rgb(IMG)
H, W, _ = rgb.shape
L = rio.lum(rgb)
Lb = rio.blur(L, 0.8)
print("image", W, H, "lum bg/plate percentiles",
      float(np.percentile(L, 5)), float(np.percentile(L, 95)))


def ray_edge(cx, cy, ang_deg, r_lo, r_hi, rising, r_in_lo, r_in_hi, r_out_lo, r_out_hi):
    """Edge along a ray. rising=True means L increases outward across the edge.
    Returns (r_grad, r_half, contrast) or None."""
    th = np.radians(ang_deg)
    ux, uy = np.cos(th), np.sin(th)
    rr = np.arange(min(r_in_lo, r_lo) - 2, max(r_out_hi, r_hi) + 2, 0.2)
    v = rio.sample(Lb, cx + ux * rr, cy + uy * rr)
    inside = np.median(v[(rr >= r_in_lo) & (rr <= r_in_hi)])
    outside = np.median(v[(rr >= r_out_lo) & (rr <= r_out_hi)])
    if rising and outside - inside < 0.15:
        return None
    if (not rising) and inside - outside < 0.15:
        return None
    d = np.gradient(v, rr)
    sel = (rr >= r_lo) & (rr <= r_hi)
    idx = np.flatnonzero(sel)
    dd = d[idx] if rising else -d[idx]
    i = idx[int(np.argmax(dd))]
    ref = rio.peak_refine(d if rising else -d, i)
    r_grad = rr[0] + ref * 0.2
    mid = 0.5 * (inside + outside)
    seg = np.flatnonzero(sel & ((v > mid) if rising else (v < mid)))
    r_half = None
    if len(seg):
        j = seg[0]
        if j > 0:
            v0, v1 = v[j - 1], v[j]
            f = (mid - v0) / (v1 - v0) if v1 != v0 else 0.0
            r_half = rr[j - 1] + f * 0.2
    return r_grad, r_half, float(abs(outside - inside))


# ---------------------------------------------------------------- hole rim
cx, cy = 630.5, 527.0
hole_pts = []
for it in range(4):
    angs = np.arange(0, 360, 0.5)
    pts = []
    for a in angs:
        e = ray_edge(cx, cy, a, 115, 158, False, 100, 112, 158, 172)
        if e is None:
            continue
        rg, rh, c = e
        th = np.radians(a)
        u = np.array([np.cos(th), np.sin(th)])
        pts.append((a, rg, rh if rh is not None else rg, float(u @ SDIR)))
    pts = np.array(pts)
    lit = pts[pts[:, 3] > 0.35]
    x = cx + np.cos(np.radians(lit[:, 0])) * lit[:, 1]
    y = cy + np.sin(np.radians(lit[:, 0])) * lit[:, 1]
    cx, cy, rhole, rms = rio.fit_circle(x, y)
    hole_pts = pts
print("hole lit-grad fit", cx, cy, rhole, rms, "n", int((hole_pts[:, 3] > 0.35).sum()))

hole = {}
for tag, col in (("grad", 1), ("half", 2)):
    for sel_tag, mask in (("lit", hole_pts[:, 3] > 0.35),
                          ("neutral", np.abs(hole_pts[:, 3]) <= 0.35),
                          ("shadow", hole_pts[:, 3] < -0.35),
                          ("all", np.ones(len(hole_pts), bool))):
        p = hole_pts[mask]
        if len(p) < 20:
            continue
        x = cx + np.cos(np.radians(p[:, 0])) * p[:, col]
        y = cy + np.sin(np.radians(p[:, 0])) * p[:, col]
        fx, fy, fr, frms = rio.fit_circle(x, y)
        hole["%s_%s" % (tag, sel_tag)] = dict(cx=fx, cy=fy, r=fr, rms=frms, n=int(len(p)))
# lit+neutral ellipse and full ellipse on grad edges
for tag, mask in (("litneutral", hole_pts[:, 3] > -0.35), ("all", np.ones(len(hole_pts), bool))):
    p = hole_pts[mask]
    x = cx + np.cos(np.radians(p[:, 0])) * p[:, 1]
    y = cy + np.sin(np.radians(p[:, 0])) * p[:, 1]
    hole["ellipse_" + tag] = rio.fit_ellipse(x, y)

# diameters along shadow-neutral directions (both ends unshadowed)
neut = []
for a in np.arange(0, 180, 0.5):
    th1, th2 = np.radians(a), np.radians(a + 180)
    u = np.array([np.cos(th1), np.sin(th1)])
    if abs(u @ SDIR) > 0.20:
        continue
    e1 = ray_edge(cx, cy, a, 115, 158, False, 100, 112, 158, 172)
    e2 = ray_edge(cx, cy, a + 180, 115, 158, False, 100, 112, 158, 172)
    if e1 and e2:
        neut.append((a, e1[0] + e2[0]))
hole["neutral_diameters"] = [[float(a), float(d)] for a, d in neut]

# ---------------------------------------------------------------- hub arcs
# axis angles (image coords, y down) from method B, refined later
axes_img = np.array([-61.6561, -1.3513, 58.8581, 118.1469, 177.9719, -121.5356])
axes_img = np.sort(np.mod(axes_img, 360.0))
hub_pts = []
for k in range(6):
    a0 = axes_img[k]
    a1 = axes_img[(k + 1) % 6] + (360.0 if k == 5 else 0.0)
    mid = 0.5 * (a0 + a1)
    for a in np.arange(mid - 11, mid + 11.001, 0.25):
        e = ray_edge(cx, cy, a, 265, 315, True, 250, 265, 320, 335)
        if e is None:
            continue
        rg, rh, c = e
        th = np.radians(a)
        u = np.array([np.cos(th), np.sin(th)])
        hub_pts.append((a % 360.0, rg, rh if rh is not None else rg, float(u @ SDIR), k))
hub_pts = np.array(hub_pts)
hub = {}
for tag, col in (("grad", 1), ("half", 2)):
    for sel_tag, mask in (("lit", hub_pts[:, 3] < -0.35),
                          ("litneutral", hub_pts[:, 3] < 0.2),
                          ("all", np.ones(len(hub_pts), bool)),
                          ("no_top_arc", hub_pts[:, 3] < 0.85)):
        p = hub_pts[mask]
        if len(p) < 20:
            continue
        x = cx + np.cos(np.radians(p[:, 0])) * p[:, col]
        y = cy + np.sin(np.radians(p[:, 0])) * p[:, col]
        fx, fy, fr, frms = rio.fit_circle(x, y)
        hub["%s_%s" % (tag, sel_tag)] = dict(cx=fx, cy=fy, r=fr, rms=frms, n=int(len(p)))
p = hub_pts[hub_pts[:, 3] < -0.35]
x = cx + np.cos(np.radians(p[:, 0])) * p[:, 1]
y = cy + np.sin(np.radians(p[:, 0])) * p[:, 1]
hub["ellipse_lit"] = rio.fit_ellipse(x, y)
p = hub_pts[hub_pts[:, 3] < 0.2]
x = cx + np.cos(np.radians(p[:, 0])) * p[:, 1]
y = cy + np.sin(np.radians(p[:, 0])) * p[:, 1]
hub["ellipse_litneutral"] = rio.fit_ellipse(x, y)
hubc = hub["grad_lit"]
# per-arc radius about the lit-fit centre
per_arc = {}
for k in range(6):
    p = hub_pts[hub_pts[:, 4] == k]
    d = np.hypot(cx + np.cos(np.radians(p[:, 0])) * p[:, 1] - hubc['cx'],
                 cy + np.sin(np.radians(p[:, 0])) * p[:, 1] - hubc['cy'])
    per_arc[k] = dict(mean=float(d.mean()), sd=float(d.std()), n=int(len(p)),
                      shadow=float(p[:, 3].mean()))
hub["per_arc_about_lit_centre"] = per_arc

HC = np.array([hubc['cx'], hubc['cy']])
RH = hubc['r']
print("hub lit fit", hubc, "hole", hole["grad_lit"])

# ---------------------------------------------------------------- flanks
ALPHA = np.radians(25.1)
RAPEX = 605.0
flanks = {}
for it in range(2):
    new_axes = []
    flanks = {}
    for k in range(6):
        aimg = axes_img[k]
        a = np.array([np.cos(np.radians(aimg)), np.sin(np.radians(aimg))])
        q = np.array([-a[1], a[0]])
        for sgn in (+1, -1):
            n = q * sgn
            pts = []
            for t in np.arange(RH + 25, RAPEX - 55, 1.5):
                hw = max(3.0, (RAPEX - t) * np.tan(ALPHA / 2))
                base = HC + a * t + n * hw
                ss = np.arange(-16, 16.001, 0.2)
                px = base[0] + n[0] * ss
                py = base[1] + n[1] * ss
                if px.min() < 2 or px.max() > W - 3 or py.min() < 2 or py.max() > H - 3:
                    continue
                v = rio.sample(Lb, px, py)
                ins = np.median(v[:20])
                out = np.median(v[-20:])
                if out - ins < 0.2:
                    continue
                d = np.gradient(v, 0.2)
                i = int(np.argmax(d))
                if i < 3 or i > len(d) - 4:
                    continue
                ref = rio.peak_refine(d, i)
                sgrad = ss[0] + ref * 0.2
                mid = 0.5 * (ins + out)
                j = np.flatnonzero(v > mid)
                shalf = None
                if len(j) and j[0] > 0:
                    v0, v1 = v[j[0] - 1], v[j[0]]
                    shalf = ss[j[0] - 1] + (mid - v0) / (v1 - v0) * 0.2
                pg = base + n * sgrad
                ph = base + n * (shalf if shalf is not None else sgrad)
                pts.append((t, pg[0], pg[1], ph[0], ph[1]))
            pts = np.array(pts)
            if len(pts) < 20:
                continue
            for col in (1, 3):
                pass
            # robust TLS on gradient edges
            xs, ys = pts[:, 1], pts[:, 2]
            keep = np.ones(len(xs), bool)
            for _ in range(4):
                p0, u0, rms, res = rio.fit_line_tls(xs[keep], ys[keep])
                allres = (np.stack([xs - p0[0], ys - p0[1]], 1) @ np.array([-u0[1], u0[0]]))
                keep = np.abs(allres) < max(1.2, 3 * rms)
            p0, u0, rms, res = rio.fit_line_tls(xs[keep], ys[keep])
            ph0, uh0, rmsh, _ = rio.fit_line_tls(pts[:, 3], pts[:, 4])
            # inner / outer half fits
            half = len(pts) // 2
            pin, uin, _, _ = rio.fit_line_tls(xs[:half], ys[:half])
            pout, uout, _, _ = rio.fit_line_tls(xs[half:], ys[half:])
            # sagitta
            tt = (np.stack([xs - p0[0], ys - p0[1]], 1) @ u0)
            nn = (np.stack([xs - p0[0], ys - p0[1]], 1) @ np.array([-u0[1], u0[0]]))
            cf = np.polyfit(tt, nn, 2)
            sag = cf[0] * ((tt.max() - tt.min()) / 2) ** 2
            flanks["p%d%s" % (k, "A" if sgn > 0 else "B")] = dict(
                k=k, sgn=int(sgn), n=int(len(pts)), nkeep=int(keep.sum()),
                p=[float(p0[0]), float(p0[1])], u=[float(u0[0]), float(u0[1])],
                rms=float(rms), rms_half=float(rmsh),
                p_half=[float(ph0[0]), float(ph0[1])], u_half=[float(uh0[0]), float(uh0[1])],
                shadow=float(n @ SDIR), sagitta=float(sag),
                u_in=[float(uin[0]), float(uin[1])], u_out=[float(uout[0]), float(uout[1])],
                dist_from_centre=float(abs((HC - p0) @ np.array([-u0[1], u0[0]]))),
                t_range=[float(pts[0, 0]), float(pts[-1, 0])])
        # refine axis from the two flank directions
        fa = flanks.get("p%dA" % k)
        fb = flanks.get("p%dB" % k)
        if fa and fb:
            pa, ua = np.array(fa['p']), np.array(fa['u'])
            pb, ub = np.array(fb['p']), np.array(fb['u'])
            if ua @ (HC - pa) > 0:
                ua = -ua
            if ub @ (HC - pb) > 0:
                ub = -ub
            apex = rio.line_intersect(pa, ua, pb, ub)
            bis = apex - HC
            new_axes.append(np.degrees(np.arctan2(bis[1], bis[0])) % 360.0)
        else:
            new_axes.append(axes_img[k])
    axes_img = np.array(new_axes)

# per point geometry
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
    ang = np.degrees(np.arccos(np.clip(ua @ ub, -1, 1)))
    axis = apex - HC
    axis_deg = np.degrees(np.arctan2(axis[1], axis[0])) % 360.0
    # base chord: where each flank line crosses the hub circle
    def circ_hit(p, u):
        f = p - HC
        b = 2 * (f @ u)
        c = f @ f - RH ** 2
        disc = b * b - 4 * c
        if disc < 0:
            return None
        t1 = (-b + np.sqrt(disc)) / 2
        t2 = (-b - np.sqrt(disc)) / 2
        cands = [p + t * u for t in (t1, t2)]
        return min(cands, key=lambda z: np.linalg.norm(z - apex + axis * 0))
    ha = circ_hit(pa, ua)
    hb = circ_hit(pb, ub)
    base = float(np.linalg.norm(ha - hb)) if ha is not None and hb is not None else None
    base_ang = float(np.degrees(np.arccos(np.clip(((ha - HC) / RH) @ ((hb - HC) / RH), -1, 1))))
    points[k] = dict(apex=[float(apex[0]), float(apex[1])],
                     apex_r=float(np.linalg.norm(apex - HC)),
                     tip_angle=float(ang), axis_deg=float(axis_deg),
                     base_chord=base, base_angle=base_ang,
                     flank_dist=[fa['dist_from_centre'], fb['dist_from_centre']],
                     shadow=[fa['shadow'], fb['shadow']],
                     rms=[fa['rms'], fb['rms']], sagitta=[fa['sagitta'], fb['sagitta']])

# ---------------------------------------------------------------- tips
tips = {}
for k in range(6):
    aimg = points[k]['axis_deg']
    a = np.array([np.cos(np.radians(aimg)), np.sin(np.radians(aimg))])
    q = np.array([-a[1], a[0]])
    tt = np.arange(points[k]['apex_r'] - 90, points[k]['apex_r'] + 40, 0.2)
    prof = np.zeros_like(tt)
    okmask = np.ones_like(tt, bool)
    for off in (-0.6, 0.0, 0.6):
        px = HC[0] + a[0] * tt + q[0] * off
        py = HC[1] + a[1] * tt + q[1] * off
        okmask &= (px > 1) & (px < W - 2) & (py > 1) & (py < H - 2)
        prof += rio.sample(Lb, px, py) / 3.0
    if not okmask.all():
        tips[k] = dict(clipped=True)
        continue
    ins = np.median(prof[:60])
    out = np.median(prof[-60:])
    mid = 0.5 * (ins + out)
    j = np.flatnonzero(prof > mid)
    r50 = None
    if len(j) and j[0] > 0:
        v0, v1 = prof[j[0] - 1], prof[j[0]]
        r50 = tt[j[0] - 1] + (mid - v0) / (v1 - v0) * 0.2
    tips[k] = dict(clipped=False, r50=float(r50), plate=float(ins), bg=float(out),
                   apex_r=points[k]['apex_r'], gap=float(points[k]['apex_r'] - r50))

out = dict(image=[W, H], shadow_dir_deg=305.0,
           hole=hole, hub=hub, hub_centre=[float(HC[0]), float(HC[1])], hub_r=float(RH),
           flanks=flanks, points={str(k): v for k, v in points.items()},
           tips={str(k): v for k, v in tips.items()},
           axes_deg=[float(v) for v in axes_img])
with open(os.path.join(OUT, "recon_measure.json"), "w") as f:
    json.dump(out, f, indent=1)
np.save(os.path.join(OUT, "hole_pts.npy"), hole_pts)
np.save(os.path.join(OUT, "hub_pts.npy"), hub_pts)
print("tip angles", [round(points[k]['tip_angle'], 3) for k in range(6)])
print("apex r", [round(points[k]['apex_r'], 1) for k in range(6)])
print("tips r50", [tips[k].get('r50') for k in range(6)])
print("base chord", [round(points[k]['base_chord'], 1) for k in range(6)])
print("axes", [round(v, 3) for v in axes_img])
print("done")
