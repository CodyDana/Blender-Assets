"""Independent reconciliation measurement of Senban.jpg.

Edge rules chosen after reading the raw profiles (r01/r02):
  bottom / left : crisp. metal edge = sub-pixel L crossing of 0.55 walking in
                  from the background plateau (bg ~0.66-0.70, bevel top ~0.45).
  top           : the lid shadow (ramp + grey umbra) sits outside the metal.
                  metal edge = the crisp drop into the near-black unlit top
                  bevel facet: sub-pixel crossing of 0.10 at the steepest step.
  right         : no crisp step (a 30-50 px soft halo). Measured two ways and
                  reported as a range; NOT used to drive the C4 fit.
Then a 5-parameter C4 model (cx, cy, theta, half-diagonal, sagitta) is fitted to
the bottom+left+top boundary points, and the right side is a prediction that is
checked against the observed crease/halo.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from rc_common import load_rgb, lum, bilinear, fit_circle, fit_line_tls, line_intersect, OUT

rgb = load_rgb()
L = lum(rgb)
H, W = L.shape
res = {}

# ---------------------------------------------------------------- outer edges
def cross_down(prof, coords, level):
    """First index where prof goes from >=level to <level; sub-pixel."""
    for i in range(1, len(prof)):
        if prof[i - 1] >= level > prof[i]:
            f = (prof[i - 1] - level) / (prof[i - 1] - prof[i])
            return coords[i - 1] + f * (coords[i] - coords[i - 1])
    return None

def steep_drop_to(prof, coords, level):
    """Location of the steepest negative step whose end is below `level`."""
    best, bi = 0.0, None
    for i in range(1, len(prof)):
        d = prof[i - 1] - prof[i]
        if prof[i] < level and d > best:
            best, bi = d, i
    if bi is None:
        return None
    f = (prof[bi - 1] - level) / max(prof[bi - 1] - prof[bi], 1e-6)
    f = min(max(f, 0.0), 1.0)
    return coords[bi - 1] + f * (coords[bi] - coords[bi - 1])

pts = {'bottom': [], 'left': [], 'top': [], 'right_halo': [], 'right_crease': [],
       'crease_bottom': [], 'crease_left': [], 'crease_top': []}

# bottom: columns, walk upward from y=960
for x in range(130, 880, 2):
    col = L[:, x]
    ys = np.arange(960, 700, -1)
    prof = col[ys]
    e = cross_down(prof, ys, 0.55)
    if e is not None:
        pts['bottom'].append((x, e))
        # crease: strongest drop 6..30 px further in (bevel -> body)
        yy = np.arange(int(e) - 3, int(e) - 34, -1)
        p2 = col[yy]
        g = p2[:-1] - p2[1:]
        k = int(np.argmax(g))
        if g[k] > 0.05:
            pts['crease_bottom'].append((x, yy[k] - 0.5))

# left: rows, walk rightward from x=10
for y in range(120, 880, 2):
    row = L[y, :]
    xs = np.arange(10, 400)
    prof = row[xs]
    e = cross_down(prof, xs, 0.55)
    if e is not None:
        pts['left'].append((e, y))
        xx = np.arange(int(e) + 3, int(e) + 34)
        p2 = row[xx]
        g = p2[:-1] - p2[1:]
        k = int(np.argmax(g))
        if g[k] > 0.05:
            pts['crease_left'].append((xx[k] + 0.5, y))

# top: columns, walk downward from y=5
for x in range(130, 880, 2):
    col = L[:, x]
    ys = np.arange(5, 330)
    prof = col[ys]
    e = steep_drop_to(prof, ys, 0.10)
    if e is not None:
        pts['top'].append((x, e))
        yy = np.arange(int(e) + 3, int(e) + 34)
        p2 = col[yy]
        g = p2[1:] - p2[:-1]        # black band -> brighter body
        k = int(np.argmax(g))
        if g[k] > 0.05:
            pts['crease_top'].append((x, yy[k] + 0.5))

# right: two readings
for y in range(120, 880, 2):
    row = L[y, :]
    xs = np.arange(995, 500, -1)
    prof = row[xs]
    e = cross_down(prof, xs, 0.55)
    if e is not None:
        pts['right_halo'].append((e, y))
    # crease = strongest body->bevel rise walking outward from x=820
    xx = np.arange(820, 985)
    p2 = row[xx]
    g = p2[1:] - p2[:-1]
    k = int(np.argmax(g))
    if g[k] > 0.05:
        pts['right_crease'].append((xx[k] + 0.5, y))

for k in pts:
    pts[k] = np.array(pts[k], dtype=np.float64)
    print(f"{k:14s} {len(pts[k]):4d} points")

# ---------------------------------------------------------------- C4 model fit
def c4_outline(p, n=4000):
    """p = (cx, cy, theta, Rd, s). Rd = centre-to-corner. s = sagitta.
    Returns closed polyline, image frame (x right, y down)."""
    cx, cy, th, Rd, s = p
    a = Rd * np.sqrt(2.0)                  # side (apex to apex)
    out = []
    per = max(n // 4, 8)
    for k in range(4):
        a0 = th + k * np.pi / 2 - np.pi / 4
        a1 = th + (k + 1) * np.pi / 2 - np.pi / 4
        P0 = np.array([cx + Rd * np.cos(a0), cy + Rd * np.sin(a0)])
        P1 = np.array([cx + Rd * np.cos(a1), cy + Rd * np.sin(a1)])
        d = (P1 - P0) / a
        nrm = np.array([-d[1], d[0]])
        if np.dot(nrm, np.array([cx, cy]) - P0) < 0:
            nrm = -nrm                     # inward
        R = a * a / (8.0 * s) + s / 2.0
        mid = 0.5 * (P0 + P1) + nrm * s
        ccen = mid - nrm * R
        v0 = P0 - ccen; v1 = P1 - ccen
        t0 = np.arctan2(v0[1], v0[0]); t1 = np.arctan2(v1[1], v1[0])
        while t1 - t0 > np.pi: t1 -= 2 * np.pi
        while t1 - t0 < -np.pi: t1 += 2 * np.pi
        tt = np.linspace(t0, t1, per, endpoint=False)
        out.append(np.stack([ccen[0] + R * np.cos(tt), ccen[1] + R * np.sin(tt)], axis=1))
    return np.concatenate(out, axis=0)

def resid_c4(p, data):
    poly = c4_outline(p, 4000)
    r = []
    for q in data:
        d = poly - q
        r.append(np.sqrt(np.min(d[:, 0] ** 2 + d[:, 1] ** 2)))
    return np.array(r)

def signed_resid(p, data):
    """signed distance: + outside the model"""
    poly = c4_outline(p, 4000)
    cx, cy = p[0], p[1]
    out = []
    for q in data:
        d = poly - q
        i = int(np.argmin(d[:, 0] ** 2 + d[:, 1] ** 2))
        dist = np.hypot(*(poly[i] - q))
        rq = np.hypot(q[0] - cx, q[1] - cy)
        rp = np.hypot(poly[i][0] - cx, poly[i][1] - cy)
        out.append(dist * (1 if rq > rp else -1))
    return np.array(out)

data3 = np.concatenate([pts['bottom'], pts['left'], pts['top']], axis=0)
p0 = np.array([505.0, 476.0, -2.45 * np.pi / 180.0, 603.0, 52.0])

def nelder(f, x0, steps, iters=4000):
    n = len(x0)
    simplex = [np.array(x0, dtype=np.float64)]
    for i in range(n):
        v = np.array(x0, dtype=np.float64); v[i] += steps[i]; simplex.append(v)
    simplex = np.array(simplex)
    fv = np.array([f(s) for s in simplex])
    for _ in range(iters):
        o = np.argsort(fv); simplex = simplex[o]; fv = fv[o]
        if fv[-1] - fv[0] < 1e-10:
            break
        cen = simplex[:-1].mean(axis=0)
        xr = cen + 1.0 * (cen - simplex[-1]); fr = f(xr)
        if fr < fv[0]:
            xe = cen + 2.0 * (cen - simplex[-1]); fe = f(xe)
            simplex[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < fv[-2]:
            simplex[-1], fv[-1] = xr, fr
        else:
            xc = cen + 0.5 * (simplex[-1] - cen); fc = f(xc)
            if fc < fv[-1]:
                simplex[-1], fv[-1] = xc, fc
            else:
                simplex[1:] = simplex[0] + 0.5 * (simplex[1:] - simplex[0])
                fv = np.array([f(s) for s in simplex])
    o = np.argsort(fv)
    return simplex[o][0], fv[o][0]

cost = lambda p: float(np.mean(resid_c4(p, data3) ** 2))
best, c = nelder(cost, p0, [3, 3, 0.01, 6, 3])
best, c = nelder(cost, best, [1, 1, 0.003, 2, 1])
cx, cy, th, Rd, s = best
side = Rd * np.sqrt(2.0)
print("\n=== C4 fit to bottom+left+top ===")
print(f" centre        ({cx:.2f}, {cy:.2f})")
print(f" rotation      {np.degrees(th) % 90 - 90 if (np.degrees(th) % 90) > 45 else np.degrees(th) % 90:.3f} deg")
print(f" half-diagonal {Rd:.2f} px   side {side:.2f} px   diagonal {2*Rd:.2f} px")
print(f" sagitta       {s:.2f} px   s/c = {s/side:.5f}")
print(f" rms           {np.sqrt(c):.3f} px")
for k in ('bottom', 'left', 'top', 'right_halo', 'right_crease'):
    if len(pts[k]):
        r = signed_resid(best, pts[k])
        print(f"   {k:13s} n={len(pts[k]):4d} median signed resid {np.median(r):+7.2f} px  "
              f"p10 {np.percentile(r,10):+6.2f}  p90 {np.percentile(r,90):+6.2f}")

# ---------------------------------------------------------------- per-side arcs
print("\n=== per-side independent circle fits (my own edge points) ===")
corners = {}
sides = {}
for k in ('bottom', 'left', 'top'):
    P = pts[k]
    # trim 12% at each end (corner blur / mitre)
    if k in ('bottom', 'top'):
        o = np.argsort(P[:, 0])
    else:
        o = np.argsort(P[:, 1])
    P = P[o]
    m = len(P)
    core = P[int(0.10 * m):int(0.90 * m)]
    ccx, ccy, R, rms, _ = fit_circle(core)
    sides[k] = (ccx, ccy, R)
    print(f" {k:7s} R = {R:8.1f} px  rms {rms:.3f} px  n={len(core)}")

res['c4_fit'] = dict(centre=[cx, cy], rot_deg=float(np.degrees(th)),
                     half_diag_px=Rd, side_px=side, sagitta_px=s,
                     sag_over_chord=s / side, rms_px=float(np.sqrt(c)))

# ---------------------------------------------------------------- hole
print("\n=== HOLE ===")
# crisp sides: top (bright lit chamfer then dark wall then lid) and right.
# rule: the plan boundary = midpoint of the dark wall line, i.e. the 0.50 L
# crossing walking from the bright lid outward into the metal.
hole_top, hole_right, hole_bottom, hole_left = [], [], [], []
hcx, hcy = 505.0, 470.0
for x in range(400, 610, 1):
    col = L[:, x]
    ys = np.arange(int(hcy) - 40, 320, -1)           # from inside upward
    prof = col[ys]
    e = cross_down(prof, ys, 0.50)
    if e is not None:
        hole_top.append((x, e))
for y in range(375, 565, 1):
    row = L[y, :]
    xs = np.arange(int(hcx) + 40, 700)               # from inside rightward
    prof = row[xs]
    e = cross_down(prof, xs, 0.50)
    if e is not None:
        hole_right.append((e, y))
    xs = np.arange(int(hcx) - 40, 330, -1)           # from inside leftward
    prof = row[xs]
    e = cross_down(prof, xs, 0.50)
    if e is not None:
        hole_left.append((e, y))
for x in range(400, 610, 1):
    col = L[:, x]
    ys = np.arange(int(hcy) + 40, 700)               # from inside downward
    prof = col[ys]
    e = cross_down(prof, ys, 0.50)
    if e is not None:
        hole_bottom.append((x, e))
for nm, arr in (('top', hole_top), ('right', hole_right),
                ('bottom', hole_bottom), ('left', hole_left)):
    A = np.array(arr, dtype=np.float64)
    # drop the outer 15% each end (corner fillets)
    o = np.argsort(A[:, 0] if nm in ('top', 'bottom') else A[:, 1])
    A = A[o]; m = len(A)
    A = A[int(0.15 * m):int(0.85 * m)]
    c0, d0, rms = fit_line_tls(A)
    ang = np.degrees(np.arctan2(d0[1], d0[0])) % 90
    if ang > 45: ang -= 90
    # distance from the plate centre to this line
    n0 = np.array([-d0[1], d0[0]])
    dist = abs(np.dot(np.array([cx, cy]) - c0, n0))
    print(f" hole {nm:7s} n={len(A):4d} rms {rms:5.2f} px  heading {ang:+6.2f} deg  "
          f"dist from plate centre {dist:7.2f} px")
    res.setdefault('hole_lines', {})[nm] = dict(c=list(c0), d=list(d0), rms=rms,
                                                heading=ang, dist_from_plate_centre=dist)

res['pts_counts'] = {k: int(len(v)) for k, v in pts.items()}
np.save(os.path.join(OUT, 'reconcile', 'edge_points.npy'),
        np.array([1]), allow_pickle=False)
np.savez(os.path.join(OUT, 'reconcile', 'edge_points.npz'), **pts)
with open(os.path.join(OUT, 'reconcile', 'rc_measure.json'), 'w') as f:
    json.dump(res, f, indent=1)
print("\nwrote rc_measure.json")
