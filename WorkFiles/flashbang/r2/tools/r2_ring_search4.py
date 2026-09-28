import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
import r2_ring_fit as RF
from r2_ring_fit import *
import math
def frame(top, alpha, tau, roll):
    u = np.array([math.cos(math.radians(alpha)), math.sin(math.radians(alpha)), 0.0])
    zz = np.array([0, 0, 1.0]); out = np.cross(u, zz)
    zdir = math.cos(math.radians(tau)) * zz - math.sin(math.radians(tau)) * out      # centre -> top (unrolled)
    # roll: rotate the ring in its plane about the eye: centre -> eye direction turns by roll toward +u
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    d = cr * zdir + sr * u                                   # centre -> eye
    e = -sr * zdir + cr * u
    c = np.array(top) - 21.9 * d
    return c, d, e
def ring(top, alpha, tau, roll, r=1.2):
    c, d, e = frame(top, alpha, tau, roll)
    n = np.cross(e, d)
    a = np.linspace(0, 2 * math.pi, 720)[:, None]
    b = np.linspace(0, 2 * math.pi, 12)[None, :]
    dd = np.cos(a) * d + np.sin(a) * e
    P = c + (21.9 + r * np.cos(b))[..., None] * dd[:, None, :] + (r * np.sin(b))[..., None] * n
    return P.reshape(-1, 3), c, d, e
def score2(top, alpha, tau, roll):
    rp, c, d, e = ring(top, alpha, tau, roll)
    tot = 0; per = {}
    for v in VIEW_X_PX:
        m = bodym[v] | mask(rp, v)
        ex = extents(m, v, Hs)
        er = [abs(a[SIDE[v]] - b[SIDE[v]]) for a, b in zip(ex, refx[v]) if a[0] is not None and b[0] is not None]
        per[v] = round(float(np.mean(er)), 2); tot += per[v]
    asp = {}
    for v in ("v1", "v2", "v3"):
        cc = c + 21.9 * (np.cos(np.linspace(0, 6.3, 360))[:, None] * d + np.sin(np.linspace(0, 6.3, 360))[:, None] * e)
        xy, _ = project(cc, v)
        asp[v] = (xy[:, 0].max() - xy[:, 0].min()) / (xy[:, 1].max() - xy[:, 1].min())
    pen = 10 * max(0, 0.95 - asp["v1"]) + 10 * max(0, 0.9 - asp["v3"]) + 10 * max(0, asp["v2"] - 0.35)
    # v1 ring centre lateral: the reference's ring spans x 160-330 -> centre x 245 ref px, y ~200
    xy, _ = project(c[None, :], "v1")
    cen = abs(xy[0, 0] - 245.0) / 3.984 + abs(xy[0, 1] - 200.0) / 3.984
    return tot + pen + 0.5 * cen, tot, per, {k: round(v, 2) for k, v in asp.items()}, round(cen, 1)
res = []
for px in (11.0, 12.5, 14.0):
    for py in (-17.5, -19.0, -20.5):
        for alpha in (-35, -25, -15, -5):
            for tau in (10, 20):
                for roll in (0, 15, 30):
                    s = score2((px, py, 156.5), alpha, tau, roll)
                    res.append((round(s[0], 2), round(s[1], 2), px, py, alpha, tau, roll, s[2], s[3], s[4]))
res.sort(key=lambda t: t[0])
for r in res[:12]:
    print(r)
