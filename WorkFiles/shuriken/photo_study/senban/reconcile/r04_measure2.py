"""Reconciliation measurement, v2. Fixed top-edge detector + hole from the two
crisp hole sides only."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from rc_common import load_rgb, lum, fit_circle, fit_line_tls, OUT

rgb = load_rgb(); L = lum(rgb); H, W = L.shape
res = {}

def smooth(a, k=3):
    ker = np.ones(k) / k
    return np.convolve(a, ker, mode='same')

def cross_down(prof, coords, level):
    for i in range(1, len(prof)):
        if prof[i - 1] >= level > prof[i]:
            f = (prof[i - 1] - level) / (prof[i - 1] - prof[i])
            return coords[i - 1] + f * (coords[i] - coords[i - 1])
    return None

def top_edge(prof, coords):
    """First entry into the near-black unlit top bevel: steepest smoothed drop
    within 28 samples after L first falls below 0.30."""
    ia = None
    for i in range(len(prof)):
        if prof[i] < 0.30:
            ia = i; break
    if ia is None or ia + 4 >= len(prof):
        return None
    ib = min(ia + 28, len(prof) - 1)
    sp = smooth(prof[max(ia - 2, 0):ib + 2])
    seg = sp[2:-2] if len(sp) > 4 else sp
    base = max(ia - 2, 0) + 2
    g = seg[:-1] - seg[1:]
    if len(g) < 3:
        return None
    k = int(np.argmax(g))
    if g[k] < 0.03:
        return None
    # parabolic sub-sample on the gradient peak
    d = 0.0
    if 0 < k < len(g) - 1:
        den = g[k - 1] - 2 * g[k] + g[k + 1]
        if abs(den) > 1e-9:
            d = 0.5 * (g[k - 1] - g[k + 1]) / den
    i0 = base + k
    return coords[i0] + (d + 0.5) * (coords[min(i0 + 1, len(coords) - 1)] - coords[i0])

pts = {k: [] for k in ('bottom', 'left', 'top', 'right_halo', 'right_crease',
                       'crease_bottom', 'crease_left', 'crease_top', 'crease_right')}

for x in range(150, 860, 2):
    col = L[:, x]
    ys = np.arange(960, 700, -1)
    e = cross_down(col[ys], ys, 0.55)
    if e is not None:
        pts['bottom'].append((x, e))
        yy = np.arange(int(e) - 3, int(e) - 34, -1); p2 = col[yy]
        g = p2[:-1] - p2[1:]; k = int(np.argmax(g))
        if g[k] > 0.05: pts['crease_bottom'].append((x, yy[k] - 0.5))
    ys = np.arange(5, 340)
    e = top_edge(col[ys], ys)
    if e is not None:
        pts['top'].append((x, e))
        yy = np.arange(int(e) + 4, int(e) + 34); p2 = col[yy]
        g = p2[1:] - p2[:-1]; k = int(np.argmax(g))
        if g[k] > 0.05: pts['crease_top'].append((x, yy[k] + 0.5))

for y in range(140, 860, 2):
    row = L[y, :]
    xs = np.arange(10, 420)
    e = cross_down(row[xs], xs, 0.55)
    if e is not None:
        pts['left'].append((e, y))
        xx = np.arange(int(e) + 3, int(e) + 34); p2 = row[xx]
        g = p2[:-1] - p2[1:]; k = int(np.argmax(g))
        if g[k] > 0.05: pts['crease_left'].append((xx[k] + 0.5, y))
    xs = np.arange(995, 560, -1)
    e = cross_down(row[xs], xs, 0.55)
    if e is not None: pts['right_halo'].append((e, y))
    xx = np.arange(830, 985); p2 = row[xx]
    g = p2[1:] - p2[:-1]; k = int(np.argmax(g))
    if g[k] > 0.05: pts['crease_right'].append((xx[k] + 0.5, y))

for k in pts:
    pts[k] = np.array(pts[k], dtype=np.float64)

# ------------------------------------------------ per-side independent circles
print("=== per-side circle fits, my own edge points (middle 80% of each side) ===")
side_fit = {}
for k in ('bottom', 'left', 'top'):
    P = pts[k]
    o = np.argsort(P[:, 0] if k in ('bottom', 'top') else P[:, 1])
    P = P[o]; m = len(P); core = P[int(0.10 * m):int(0.90 * m)]
    for _ in range(3):            # robust: drop >3 sigma
        ccx, ccy, R, rms, r = fit_circle(core)
        keep = np.abs(r) < max(3 * rms, 1.0)
        if keep.all(): break
        core = core[keep]
    side_fit[k] = (ccx, ccy, R)
    print(f" {k:7s} n={len(core):4d} R={R:8.1f}px  rms={rms:.3f}px")

# ------------------------------------------------------------------- C4 fit
def c4_poly(p, n=4800):
    cx, cy, th, Rd, s = p
    a = Rd * np.sqrt(2.0); out = []
    per = n // 4
    for k in range(4):
        a0 = th + k * np.pi / 2 - np.pi / 4
        a1 = th + (k + 1) * np.pi / 2 - np.pi / 4
        P0 = np.array([cx + Rd * np.cos(a0), cy + Rd * np.sin(a0)])
        P1 = np.array([cx + Rd * np.cos(a1), cy + Rd * np.sin(a1)])
        d = (P1 - P0) / a; nrm = np.array([-d[1], d[0]])
        if np.dot(nrm, np.array([cx, cy]) - P0) < 0: nrm = -nrm
        R = a * a / (8.0 * s) + s / 2.0
        ccen = 0.5 * (P0 + P1) + nrm * s - nrm * R
        v0 = P0 - ccen; v1 = P1 - ccen
        t0 = np.arctan2(v0[1], v0[0]); t1 = np.arctan2(v1[1], v1[0])
        while t1 - t0 > np.pi: t1 -= 2 * np.pi
        while t1 - t0 < -np.pi: t1 += 2 * np.pi
        tt = np.linspace(t0, t1, per, endpoint=False)
        out.append(np.stack([ccen[0] + R * np.cos(tt), ccen[1] + R * np.sin(tt)], 1))
    return np.concatenate(out, 0)

def resid(p, data):
    poly = c4_poly(p)
    out = np.empty(len(data))
    for i, q in enumerate(data):
        d = poly - q
        out[i] = np.sqrt(np.min(d[:, 0] ** 2 + d[:, 1] ** 2))
    return out

def signed(p, data):
    poly = c4_poly(p); cx, cy = p[0], p[1]
    out = np.empty(len(data))
    for i, q in enumerate(data):
        d = poly - q; j = int(np.argmin(d[:, 0] ** 2 + d[:, 1] ** 2))
        out[i] = np.hypot(*(poly[j] - q)) * (1 if np.hypot(q[0] - cx, q[1] - cy) >
                                             np.hypot(poly[j][0] - cx, poly[j][1] - cy) else -1)
    return out

def nelder(f, x0, steps, iters=3000):
    n = len(x0); S = [np.array(x0, float)]
    for i in range(n):
        v = np.array(x0, float); v[i] += steps[i]; S.append(v)
    S = np.array(S); fv = np.array([f(s) for s in S])
    for _ in range(iters):
        o = np.argsort(fv); S = S[o]; fv = fv[o]
        if fv[-1] - fv[0] < 1e-11: break
        cen = S[:-1].mean(0)
        xr = cen + (cen - S[-1]); fr = f(xr)
        if fr < fv[0]:
            xe = cen + 2 * (cen - S[-1]); fe = f(xe)
            S[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < fv[-2]: S[-1], fv[-1] = xr, fr
        else:
            xc = cen + 0.5 * (S[-1] - cen); fc = f(xc)
            if fc < fv[-1]: S[-1], fv[-1] = xc, fc
            else:
                S[1:] = S[0] + 0.5 * (S[1:] - S[0]); fv = np.array([f(s) for s in S])
    o = np.argsort(fv); return S[o][0], fv[o][0]

def trim(P, key, lo=0.08, hi=0.92):
    o = np.argsort(P[:, key]); P = P[o]; m = len(P)
    return P[int(lo * m):int(hi * m)]

data3 = np.concatenate([trim(pts['bottom'], 0), trim(pts['left'], 1),
                        trim(pts['top'], 0)], 0)
cost = lambda p: float(np.mean(resid(p, data3) ** 2))
best, c = nelder(cost, [505., 477., np.radians(-2.45), 603., 52.], [4, 4, .01, 8, 4])
best, c = nelder(cost, best, [1, 1, .003, 2, 1])
best, c = nelder(cost, best, [.3, .3, .001, .6, .3])
cx, cy, th, Rd, s = best; side = Rd * np.sqrt(2.0)
rot = np.degrees(th) % 90
if rot > 45: rot -= 90
print(f"\n=== C4 fit (bottom+left+top, right excluded) ===")
print(f" centre ({cx:.2f}, {cy:.2f})  rot {rot:+.3f} deg")
print(f" side {side:.2f} px  diagonal {2*Rd:.2f} px  diag/side {2*Rd/side:.4f}")
print(f" sagitta {s:.2f} px   s/c {s/side:.5f}   rms {np.sqrt(c):.3f} px")
tip = 90.0 - 4 * np.degrees(np.arctan(2 * s / side))
print(f" implied corner tip angle (arc tangents) {tip:.2f} deg")
for k in ('bottom', 'left', 'top', 'right_halo', 'right_crease',
          'crease_bottom', 'crease_left', 'crease_top', 'crease_right'):
    if len(pts[k]):
        r = signed(best, trim(pts[k], 0 if k.endswith(('bottom', 'top')) else 1))
        print(f"   {k:14s} median {np.median(r):+7.2f}  p10 {np.percentile(r,10):+7.2f}"
              f"  p90 {np.percentile(r,90):+7.2f}")

res['c4'] = dict(centre=[cx, cy], rot_deg=rot, side_px=side, diag_px=2 * Rd,
                 sagitta_px=s, sag_over_chord=s / side, rms_px=float(np.sqrt(c)),
                 tip_angle_deg=tip)

# --------------------------------------------------------------------- hole
print("\n=== HOLE (0.50 L crossing walking outward from inside) ===")
hl = {'top': [], 'right': [], 'bottom': [], 'left': []}
for x in range(400, 612, 1):
    col = L[:, x]
    ys = np.arange(int(cy) - 40, 320, -1)
    e = cross_down(col[ys], ys, 0.50)
    if e is not None: hl['top'].append((x, e))
    ys = np.arange(int(cy) + 40, 700)
    e = cross_down(col[ys], ys, 0.50)
    if e is not None: hl['bottom'].append((x, e))
for y in range(372, 568, 1):
    row = L[y, :]
    xs = np.arange(int(cx) + 40, 720)
    e = cross_down(row[xs], xs, 0.50)
    if e is not None: hl['right'].append((e, y))
    xs = np.arange(int(cx) - 40, 320, -1)
    e = cross_down(row[xs], xs, 0.50)
    if e is not None: hl['left'].append((e, y))
hole = {}
for nm in ('top', 'right', 'bottom', 'left'):
    A = np.array(hl[nm], float)
    A = trim(A, 0 if nm in ('top', 'bottom') else 1, 0.15, 0.85)
    c0, d0, rms = fit_line_tls(A)
    ang = np.degrees(np.arctan2(d0[1], d0[0])) % 90
    if ang > 45: ang -= 90
    n0 = np.array([-d0[1], d0[0]])
    dist = abs(np.dot(np.array([cx, cy]) - c0, n0))
    hole[nm] = dict(dist=dist, heading=ang, rms=rms, n=len(A))
    print(f" {nm:7s} n={len(A):4d} rms {rms:5.2f}px  heading {ang:+6.2f}deg  "
          f"centre->line {dist:7.2f}px   implied side {2*dist:7.2f}px")
print(f" top+bottom separation {hole['top']['dist']+hole['bottom']['dist']:.2f} px")
print(f" left+right separation {hole['left']['dist']+hole['right']['dist']:.2f} px")
crisp = 2 * 0.5 * (hole['top']['dist'] + hole['right']['dist'])
print(f" CRISP-ONLY hole side (2 x mean of top,right distances) = {crisp:.2f} px")
print(f"   -> hole side / plate side = {crisp/side:.4f}")
outer_head = rot
print(f" hole headings vs plate rotation {outer_head:+.3f}: "
      + ", ".join(f"{nm} {hole[nm]['heading']-outer_head:+.2f}" for nm in hole))
res['hole'] = hole
res['hole_crisp_side_px'] = crisp
res['hole_over_side'] = crisp / side

# bevel widths: metal edge -> crease
print("\n=== bevel band widths (metal edge to crease) ===")
bw = {}
for nm, a, b, key in (('bottom', 'bottom', 'crease_bottom', 0),
                      ('left', 'left', 'crease_left', 1),
                      ('top', 'top', 'crease_top', 0),
                      ('right', 'right_halo', 'crease_right', 1)):
    A = trim(pts[a], key, 0.12, 0.88); B = trim(pts[b], key, 0.12, 0.88)
    m = min(len(A), len(B))
    d = np.hypot(A[:m, 0] - B[:m, 0], A[:m, 1] - B[:m, 1])
    bw[nm] = dict(median=float(np.median(d)), p10=float(np.percentile(d, 10)),
                  p90=float(np.percentile(d, 90)))
    print(f" {nm:7s} median {np.median(d):6.2f} px  p10 {np.percentile(d,10):6.2f}"
          f"  p90 {np.percentile(d,90):6.2f}"
          + ("   (right: metal edge is the halo crossing = upper bound)" if nm == 'right' else ""))
res['bevel_px'] = bw
np.savez(os.path.join(OUT, 'reconcile', 'edge_points.npz'), **pts,
         **{f'hole_{k}': np.array(v, float) for k, v in hl.items()})
with open(os.path.join(OUT, 'reconcile', 'rc_measure2.json'), 'w') as f:
    json.dump(res, f, indent=1)
print("\nwrote rc_measure2.json")
