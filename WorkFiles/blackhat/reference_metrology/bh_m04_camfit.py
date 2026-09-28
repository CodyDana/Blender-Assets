"""Stage 4: fit camera + cone height + rim tube radius to the silhouette, for a ladder of camera distances."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
top = np.load(os.path.join(D, 'bh_top.npy')); bot = np.load(os.path.join(D, 'bh_bot.npy'))
xt = np.array([x for x in list(range(4, 285)) + list(range(390, 436)) + list(range(475, 662)) if not np.isnan(top[x])], float)
xb = np.array([x for x in range(6, 541) if not np.isnan(bot[x])], float)
# median-filter bottom to suppress lashing bumps (window 25)
bm = np.array([np.median(bot[max(0, int(x) - 12):int(x) + 13]) for x in xb])
yt_m = top[xt.astype(int)]; yb_m = bm
slope_t = np.gradient(yt_m, xt); slope_b = np.gradient(yb_m, xb)
wt = 1 / np.sqrt(1 + slope_t ** 2); wb = 1 / np.sqrt(1 + slope_b ** 2)
def huber(r, k=1.5):
    a = np.abs(r); return np.where(a <= k, r, np.sign(r) * np.sqrt(2 * k * a - k * k))
out = {}
ladder = [2.5, 3, 3.5, 4, 5, 6, 8, 10, 14, 20, 40, np.inf]
for d in ladder:
    def fun(p):
        yt, yb, _, _ = outlines(p, d, xt, xb)
        r = np.concatenate([(yt - yt_m) * wt, (yb - yb_m) * wb])
        r = np.nan_to_num(r, nan=20.0)
        return huber(r)
    e0 = np.radians(19)
    f0 = 330 * (d if np.isfinite(d) else 1)
    p0 = [0.62, 0.035, e0, f0, 333, 330, np.radians(0.5)]
    p, r, J = lm(fun, p0, iters=80)
    rr = fun(p)
    H, rt, e, f, u0, v0, roll = p
    out[str(d)] = dict(H=H, rt=rt, e_deg=float(np.degrees(e)), f=f, u0=u0, v0=v0, roll_deg=float(np.degrees(roll)),
                       rms=float(np.sqrt(np.mean(rr ** 2))), n=int(rr.size))
    print('d', d, {k: round(v, 4) for k, v in out[str(d)].items()})
dump('bh_s04_camfit.json', out)
