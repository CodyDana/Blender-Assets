"""Stage 7: joint fit of camera (incl. distance d) + cone height + crown-cap edge circle, using
silhouette lines, rim bottom outline and the crown-cap lower-edge front arc (top of its black shadow line)."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
Lm = lum(load_srgb())
top = np.load(os.path.join(D, 'bh_top.npy')); bot = np.load(os.path.join(D, 'bh_bot.npy'))
# --- crown cap edge trace: first crossing of 0.075 going down from row 155, cols 300..368
cap = []
for x in range(300, 369):
    col = Lm[:, x]
    for y in range(155, 168):
        if col[y] < 0.075 and col[y - 1] >= 0.075:
            cap.append((x, y - 1 + (col[y - 1] - 0.075) / (col[y - 1] - col[y]))); break
cap = np.array(cap); print('cap trace n', len(cap), 'y range', cap[:, 1].min(), cap[:, 1].max())
print('cap trace', [(int(a), round(b, 1)) for a, b in cap[::4]])
np.save(os.path.join(D, 'bh_cap_trace.npy'), cap)
xt = np.array([x for x in list(range(40, 285)) + list(range(390, 436)) + list(range(475, 590)) if not np.isnan(top[x])], float)
xb = np.array([x for x in range(20, 541) if not np.isnan(bot[x])], float)
bm = np.array([np.median(bot[max(0, int(x) - 12):int(x) + 13]) for x in xb])
yt_m = top[xt.astype(int)]
wt = 1 / np.sqrt(1 + np.gradient(yt_m, xt) ** 2); wb = 1 / np.sqrt(1 + np.gradient(bm, xb) ** 2)
th = np.linspace(0, 2 * np.pi, 1440, endpoint=False)
def model(p, d):
    H, e, f, u0, v0, roll, rc = p
    P = np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], -1)
    P = np.vstack([P, [[0, 0, H]]])
    uv = project(P, e, d, f, u0, v0, roll)
    bt, tp = hull(uv)
    yt = np.interp(xt, tp[:, 0], tp[:, 1]); yb = np.interp(xb, bt[:, 0], bt[:, 1])
    # cap circle on the cone: radius rc at z = H(1-rc); front arc = max-v of its projection per column
    Pc = np.stack([rc * np.cos(th), rc * np.sin(th), np.full_like(th, H * (1 - rc))], -1)
    uc = project(Pc, e, d, f, u0, v0, roll)
    cb, ct = hull(uc)
    yc = np.interp(cap[:, 0], cb[:, 0], cb[:, 1], left=np.nan, right=np.nan)
    return yt, yb, yc, uc
def resid(p, d, wcap):
    yt, yb, yc, _ = model(p, d)
    r = np.concatenate([(yt - yt_m) * wt, (yb - bm) * wb, wcap * np.nan_to_num(yc - cap[:, 1], nan=10.0)])
    return r
out = {}
prev = None
for d in [1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.5, 4.0, 5.0, 7.0, 10.0, np.inf]:
    p0 = prev if prev is not None else [0.47, np.radians(16), 330 * 1.8, 334, 290, np.radians(-0.5), 0.12]
    if prev is not None:
        p0 = list(prev); p0[2] = prev[2] * (d / prevd if np.isfinite(d) and np.isfinite(prevd) else 1)
        if not np.isfinite(d): p0[2] = 332
    p, r, J = lm(lambda q: resid(q, d, 2.0), p0, iters=60)
    yt, yb, yc, _ = model(p, d)
    rs_sil = np.sqrt(np.mean(np.concatenate([(yt - yt_m) * wt, (yb - bm) * wb]) ** 2))
    rs_cap = np.sqrt(np.nanmean((yc - cap[:, 1]) ** 2))
    H, e, f, u0, v0, roll, rc = p
    out[str(d)] = dict(H=H, e_deg=float(np.degrees(e)), f=f, u0=u0, v0=v0, roll_deg=float(np.degrees(roll)), rc=rc,
                       rms_sil=float(rs_sil), rms_cap=float(rs_cap), cap_bias=float(np.nanmean(yc - cap[:, 1])))
    print('d', d, {k: round(float(v), 4) for k, v in out[str(d)].items()})
    prev = p; prevd = d
dump('bh_s07_joint.json', out)
