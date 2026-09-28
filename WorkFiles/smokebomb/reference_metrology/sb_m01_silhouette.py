"""Stage 1: silhouette of the ball. Sub-pixel radial edge at several thresholds, circle + ellipse fits,
harmonics, bumpiness, thread-tip protrusions.  Angles: theta measured CCW from image +x (right), up = 90."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

rgb = L.load_srgb()
Y = L.lum(rgb)
H, W = Y.shape
bg = float(np.median(Y[:40, :40]))
m = Y < 0.5
ys, xs = np.nonzero(m)
cx0, cy0 = xs.mean(), ys.mean()
R0 = np.sqrt(m.sum() / np.pi)
print("coarse", cx0, cy0, R0, "mask px", m.sum())

# rim cloth level: median of lum in annulus 0.93..0.97 R0
yy, xx = np.mgrid[0:H, 0:W]
rr = np.hypot(xx - cx0, yy - cy0)
rim = float(np.median(Y[(rr > 0.93 * R0) & (rr < 0.97 * R0)]))
inner = float(np.median(Y[rr < 0.9 * R0]))
print("bg", bg, "rim", rim, "inner", inner)

NA = 3600
th = np.arange(NA) * (2 * np.pi / NA)
rs = np.arange(0.80 * R0, 1.20 * R0, 0.05)
X = cx0 + np.cos(th)[:, None] * rs[None, :]
Yc = cy0 - np.sin(th)[:, None] * rs[None, :]
prof = L.bilinear(Y, X, Yc)          # NA x NR


def outer_cross(prof, level):
    """outermost radius where the profile is below level (object) -> crossing to above, sub-pixel."""
    below = prof < level
    out = np.full(prof.shape[0], np.nan)
    for i in range(prof.shape[0]):
        idx = np.nonzero(below[i])[0]
        if len(idx) == 0:
            continue
        j = idx[-1]
        if j + 1 >= prof.shape[1]:
            out[i] = rs[-1]; continue
        a, b = prof[i, j], prof[i, j + 1]
        t = (level - a) / (b - a) if b != a else 0.5
        out[i] = rs[j] + t * (rs[j + 1] - rs[j])
    return out


res = {}
levels = {}
for f in (0.25, 0.5, 0.75, 0.9, 0.97):
    lev = rim + f * (bg - rim)
    levels[f] = lev
    res[f] = outer_cross(prof, lev)

r50 = res[0.5]
ex = cx0 + np.cos(th) * r50
ey = cy0 - np.sin(th) * r50


def fit_circle(x, y):
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    xc, yc = c[0], c[1]
    r = np.sqrt(c[2] + xc * xc + yc * yc)
    for _ in range(20):   # geometric refinement
        d = np.hypot(x - xc, y - yc)
        J = np.c_[-(x - xc) / d, -(y - yc) / d, -np.ones_like(x)]
        rres = d - r
        step, *_ = np.linalg.lstsq(J, -rres, rcond=None)
        xc += step[0]; yc += step[1]; r += step[2]
    d = np.hypot(x - xc, y - yc) - r
    return xc, yc, r, d


xc, yc, rc, dres = fit_circle(ex, ey)
print("circle", xc, yc, rc, "rms", dres.std(), "min", dres.min(), "max", dres.max())


def fit_ellipse(x, y):
    # Fitzgibbon direct LSQ, on normalised coords
    mx, my, s = x.mean(), y.mean(), (x.std() + y.std()) / 2
    u, v = (x - mx) / s, (y - my) / s
    D1 = np.c_[u * u, u * v, v * v]
    D2 = np.c_[u, v, np.ones_like(u)]
    S1, S2, S3 = D1.T @ D1, D1.T @ D2, D2.T @ D2
    T = -np.linalg.solve(S3, S2.T)
    M = S1 + S2 @ T
    C1 = np.array([[0, 0, 2], [0, -1, 0], [2, 0, 0]], float)
    M = np.linalg.solve(C1, M)
    ev, evec = np.linalg.eig(M)
    cond = 4 * evec[0] * evec[2] - evec[1] ** 2
    a1 = np.real(evec[:, np.nonzero(cond > 0)[0][0]])
    a = np.r_[a1, T @ a1]
    A, B, C, Dd, E, F = a
    # centre
    den = B * B - 4 * A * C
    u0 = (2 * C * Dd - B * E) / den
    v0 = (2 * A * E - B * Dd) / den
    # axes
    num = 2 * (A * E * E + C * Dd * Dd - B * Dd * E + den * F)
    root = np.sqrt((A - C) ** 2 + B * B)
    ax1 = -np.sqrt(num * (A + C + root)) / den
    ax2 = -np.sqrt(num * (A + C - root)) / den
    ang = 0.5 * np.arctan2(-B, C - A)
    return mx + u0 * s, my + v0 * s, abs(ax1) * s, abs(ax2) * s, np.degrees(ang)


ell = fit_ellipse(ex, ey)
print("ellipse", ell)

# radius function about fitted circle centre, harmonics
thc = np.arctan2(-(ey - yc), ex - xc)
rcen = np.hypot(ex - xc, ey - yc)
order = np.argsort(thc)
thc_s, r_s = thc[order], rcen[order]
# resample uniformly
tu = np.linspace(-np.pi, np.pi, 3600, endpoint=False)
ru = np.interp(tu, thc_s, r_s, period=2 * np.pi)
Fq = np.fft.rfft(ru - ru.mean()) / len(ru) * 2
harm = {n: dict(amp_px=float(abs(Fq[n])), phase_deg=float(np.degrees(np.angle(Fq[n])))) for n in range(1, 13)}
# low-order shape: n<=6
Fl = np.fft.rfft(ru)
Fl[7:] = 0
rlow = np.fft.irfft(Fl, n=len(ru))
hp = ru - rlow
print("low-order p-p", rlow.max() - rlow.min(), "hp rms", hp.std(), "hp min/max", hp.min(), hp.max())

# directional extents (flattening / bulge): width vs height from mask at 0.5
wid_h = r50[0] + r50[1800]   # right + left
hei_v = r50[900] + r50[2700]  # up + down
# diameters at every angle
diam = r50[:1800] + r50[1800:]
print("diam min/max", diam.min(), diam.max(), "at deg", np.argmin(diam) / 10, np.argmax(diam) / 10)

# thread / wisp protrusions: where the faint threshold reaches well past the main edge
wisp = res[0.9] - res[0.5]
wisp97 = res[0.97] - res[0.5]
# cluster angles where wisp97 > 1.5 px
flag = wisp97 > 1.5
runs = []
i = 0
while i < NA:
    if flag[i]:
        j = i
        while j + 1 < NA and flag[j + 1]:
            j += 1
        k = np.argmax(wisp97[i:j + 1]) + i
        runs.append(dict(theta_deg=float(th[k] * 180 / np.pi), width_deg=float((j - i + 1) / 10),
                         reach_px_97=float(wisp97[k]), reach_px_90=float(wisp[k]),
                         min_lum_beyond=None))
        i = j + 1
    else:
        i += 1
print("wisp runs", len(runs))
for r_ in sorted(runs, key=lambda d: -d['reach_px_97'])[:30]:
    print("  wisp", r_)

# local steps in hp (strip edges breaking the outline)
dhp = np.diff(np.r_[hp, hp[0]])
steps = []
for k in np.nonzero(np.abs(dhp) > 0.8)[0]:
    steps.append(dict(theta_deg=float(np.degrees(tu[k])), jump_px=float(dhp[k])))
print("steps >0.8px/0.1deg:", len(steps))

out = dict(bg_lum=bg, rim_lum=rim, inner_lum=inner, levels={str(k): float(v) for k, v in levels.items()},
           coarse=dict(cx=cx0, cy=cy0, R=R0),
           circle=dict(cx=float(xc), cy=float(yc), r=float(rc), rms=float(dres.std()), min=float(dres.min()),
                       max=float(dres.max())),
           ellipse=dict(cx=float(ell[0]), cy=float(ell[1]), a=float(ell[2]), b=float(ell[3]), angle_deg=float(ell[4])),
           harmonics=harm, lowpass_pp=float(rlow.max() - rlow.min()), hp_rms=float(hp.std()),
           hp_min=float(hp.min()), hp_max=float(hp.max()),
           diam_min=float(diam.min()), diam_max=float(diam.max()),
           diam_min_deg=float(np.argmin(diam) / 10), diam_max_deg=float(np.argmax(diam) / 10),
           width_h=float(wid_h), height_v=float(hei_v),
           wisps=runs, steps=steps)
L.dump("sb_s1_silhouette.json", out)
np.save(os.path.join(L.D, "sb_s1_radial.npy"), np.c_[th, res[0.25], res[0.5], res[0.75], res[0.9], res[0.97]])
np.save(os.path.join(L.D, "sb_s1_ru.npy"), np.c_[tu, ru, rlow, hp])

# debug image: stretched ball, fitted circle in cyan, 0.5 edge in yellow, wisps in red
vis = L.stretch(rgb, 0.0, 0.35)
vis = np.repeat(L.lum(vis)[..., None], 3, 2) * 0.8
for t_ in np.linspace(0, 2 * np.pi, 8000):
    x = int(round(xc + rc * np.cos(t_))); y = int(round(yc - rc * np.sin(t_)))
    vis[y, x] = (0, 1, 1)
for i in range(NA):
    x = int(round(ex[i])); y = int(round(ey[i]))
    vis[y, x] = (1, 1, 0)
    if wisp97[i] > 1.5:
        x2 = int(round(cx0 + np.cos(th[i]) * res[0.97][i])); y2 = int(round(cy0 - np.sin(th[i]) * res[0.97][i]))
        vis[y2, x2] = (1, 0, 0)
L.save_png(os.path.join(L.DBG, "DEBUG_NEVER_SHIP_sb_s1_silhouette.png"), vis)
print("done")
