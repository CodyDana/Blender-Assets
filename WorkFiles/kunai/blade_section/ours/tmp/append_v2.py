

# =========================================================================== v2: de-blurred matcap (forward model)
# Validation (run_validate.py) showed the kernel-smoothed matcap OVER-reads the face slope: blurring the probe in normal
# space flattens M, so a steeper facet is needed to reproduce the facets' contrast (ours: 0.096 read as 0.185 with a
# 0.10 kernel - measurer A used 0.12, B 4-degree bins).  The fix: fit an UNBLURRED matcap on a grid so that the probe
# pixels are reproduced as the pixel footprint (1 px box) convolved with the image PSF, with a smoothness prior.
from math import erf as _erf


def _footprint(sig_psf, n=9):
    """Sub-pixel offsets and weights of box(1 px) (x) Gaussian(sig_psf)."""
    half = 0.5 + 2.5 * sig_psf
    o = np.linspace(-half, half, n)
    s2 = math.sqrt(2) * max(sig_psf, 1e-3)
    w1 = np.array([0.5 * (_erf((t + 0.5) / s2) - _erf((t - 0.5) / s2)) for t in o])
    W = np.outer(w1, w1)
    W /= W.sum()
    ox, oy = np.meshgrid(o, o)
    return ox.ravel(), oy.ravel(), W.ravel()


class DeblurMatcap:
    """M(n) on a grid over the unit disk, fitted to probe pixels through the pixel footprint + PSF."""

    def __init__(self, lum, d_of_xy, pixels, sig_psf=0.35, step=0.05, lam=0.02, persp=None):
        """d_of_xy(x, y) -> (nx, ny, inside): image-plane normal of the probe at sub-pixel points.  pixels: (x, y)
        pixel centres to use.  persp: (f_px, cx, cy) -> index by the reflection-equivalent normal n - v/2 (v = the
        view vector's image-plane part), or None (orthographic)."""
        self.step = step
        g = np.arange(-1.0, 1.0 + 1e-9, step)
        N = len(g)
        self.N = N
        ox, oy, ow = _footprint(sig_psf)
        rows, vals = [], []
        for (x, y) in pixels:
            nx, ny, inside = d_of_xy(x + ox, y + oy)
            if not np.all(inside):
                continue
            if persp is not None:
                vx, vy = -(x - persp[1]) / persp[0], -(y - persp[2]) / persp[0]
                nx, ny = nx - 0.5 * vx, ny - 0.5 * vy
            fx = (nx + 1.0) / step
            fy = (ny + 1.0) / step
            i0 = np.clip(np.floor(fx).astype(int), 0, N - 2)
            j0 = np.clip(np.floor(fy).astype(int), 0, N - 2)
            ax, ay = fx - i0, fy - j0
            row = np.zeros(N * N)
            for di, dj, w in ((0, 0, (1 - ax) * (1 - ay)), (1, 0, ax * (1 - ay)), (0, 1, (1 - ax) * ay),
                              (1, 1, ax * ay)):
                np.add.at(row, (j0 + dj) * N + (i0 + di), w * ow)
            rows.append(row)
            vals.append(lum[int(round(y)), int(round(x))])
        A = np.array(rows)
        b = np.array(vals)
        used = np.where(A.sum(0) > 1e-9)[0]
        act = set(used.tolist())
        for k in used:
            j, i = divmod(int(k), N)
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    if 0 <= j + dj < N and 0 <= i + di < N:
                        act.add((j + dj) * N + i + di)
        act = np.array(sorted(act))
        idx = {int(k): t for t, k in enumerate(act)}
        As = A[:, act]
        reg = []
        for k in act:
            j, i = divmod(int(k), N)
            for (dj, di) in ((0, 1), (1, 0)):
                k2 = (j + dj) * N + i + di
                k3 = (j - dj) * N + i - di
                if 0 <= j + dj < N and 0 <= i + di < N and 0 <= j - dj < N and 0 <= i - di < N \
                        and k2 in idx and k3 in idx:
                    r = np.zeros(len(act))
                    r[idx[k2]] += 1
                    r[idx[k3]] += 1
                    r[idx[int(k)]] -= 2
                    reg.append(r)
        R = np.array(reg)
        scale = np.sqrt(len(b) / max(len(R), 1)) * lam
        sol, *_ = np.linalg.lstsq(np.vstack([As, scale * R]), np.r_[b, np.zeros(len(R))], rcond=None)
        m = np.full(N * N, np.nan)
        m[act] = sol
        self.m = m.reshape(N, N)
        self.n_rows = len(b)
        self.fit_rms = float(np.sqrt(np.mean((As @ sol - b) ** 2)))
        self.persp = persp

    def __call__(self, n2, at_xy=None):
        nx, ny = n2[0], n2[1]
        if self.persp is not None and at_xy is not None:
            vx = -(at_xy[0] - self.persp[1]) / self.persp[0]
            vy = -(at_xy[1] - self.persp[2]) / self.persp[0]
            nx, ny = nx - 0.5 * vx, ny - 0.5 * vy
        fx = (nx + 1.0) / self.step
        fy = (ny + 1.0) / self.step
        i0 = int(min(max(math.floor(fx), 0), self.N - 2))
        j0 = int(min(max(math.floor(fy), 0), self.N - 2))
        ax, ay = fx - i0, fy - j0
        m = self.m
        v = (m[j0, i0] * (1 - ax) * (1 - ay) + m[j0, i0 + 1] * ax * (1 - ay) + m[j0 + 1, i0] * (1 - ax) * ay
             + m[j0 + 1, i0 + 1] * ax * ay)
        if not np.isfinite(v):
            return float("nan")
        return float(max(v, 1e-5))


def ring_d_ellipses(inner, outer, excl_deg=None):
    """d_of_xy for a ring from its inner/outer ellipses (photo)."""
    cx = 0.5 * (inner["cx"] + outer["cx"])
    cy = 0.5 * (inner["cy"] + outer["cy"])

    def ell_r(f, psi):
        u = psi - math.radians(f["major_angle_deg"])
        return 1 / np.sqrt((np.cos(u) / f["a"]) ** 2 + (np.sin(u) / f["b"]) ** 2)

    def fn(x, y):
        dx, dy = np.asarray(x, float) - cx, np.asarray(y, float) - cy
        psi = np.arctan2(dy, dx)
        ri, ro = ell_r(inner, psi), ell_r(outer, psi)
        d = (np.hypot(dx, dy) - 0.5 * (ri + ro)) / (0.5 * (ro - ri))
        inside = np.abs(d) < 1.0
        if excl_deg:
            deg = np.degrees(psi)
            inside &= ~((deg >= excl_deg[0]) & (deg <= excl_deg[1]))
        dd = np.clip(d, -1, 1)
        return dd * np.cos(psi), dd * np.sin(psi), inside
    R = max(outer["a"], outer["b"]) + 1
    return fn, (cx, cy, R)


def ring_d_centreline(centre, centreline, tube_r):
    """d_of_xy for a probe torus from its projected centreline and tube radius (renders)."""
    cx, cy = centre
    cl = np.array(centreline)
    ang = np.arctan2(cl[:, 1] - cy, cl[:, 0] - cx)
    rad = np.hypot(cl[:, 0] - cx, cl[:, 1] - cy)
    o = np.argsort(ang)
    ang, rad = ang[o], rad[o]
    ang = np.r_[ang - 2 * np.pi, ang, ang + 2 * np.pi]
    rad = np.r_[rad, rad, rad]

    def fn(x, y):
        dx, dy = np.asarray(x, float) - cx, np.asarray(y, float) - cy
        psi = np.arctan2(dy, dx)
        d = (np.hypot(dx, dy) - np.interp(psi, ang, rad)) / tube_r
        dd = np.clip(d, -1, 1)
        return dd * np.cos(psi), dd * np.sin(psi), np.abs(d) < 1.0
    return fn, (cx, cy, rad.max() + tube_r + 1)


def probe_pixels(fn, box, dmax):
    cx, cy, R = box
    px = []
    for y in range(int(cy - R), int(cy + R) + 1):
        for x in range(int(cx - R), int(cx + R) + 1):
            nx, ny, ins = fn(np.array([x]), np.array([y]))
            if ins[0] and math.hypot(nx[0], ny[0]) <= dmax:
                px.append((x, y))
    return px


def run2(lum, blade, mc, stations_s, q_by_s, alpha=None, pitch=0.0, gain1=True):
    """RATIO (albedo-free, roll from q) and GAIN1 (albedo = probe) with a matcap taking the facet's image position."""
    rows = []
    for s in stations_s:
        Lt, _ = facet_L(lum, blade, s, "top", alpha=alpha)
        Lb, _ = facet_L(lum, blade, s, "bot", alpha=alpha)
        q = q_by_s(s)
        ut, ub, ur = blade.top(s), blade.bot(s), blade.ridge(s)
        pt = blade.P(s, ur + 0.5 * (ut - ur))
        pb = blade.P(s, ur + 0.5 * (ub - ur))
        mt, ct, mb, cb = station_models(blade, s)
        obs = math.log(Lt / Lb)
        best, curve = None, []
        for r in R_GRID:
            roll = math.degrees(math.atan2(q, r))
            nt = facet_normal(mt, r / ct, blade, roll, pitch)
            nb = facet_normal(mb, r / cb, blade, roll, pitch)
            Mt, Mb = mc(nt[:2], pt), mc(nb[:2], pb)
            if not (np.isfinite(Mt) and np.isfinite(Mb)):
                continue
            pred = math.log(Mt / Mb)
            curve.append((float(r), pred, Mt, Mb))
            if best is None or abs(pred - obs) < best[1]:
                best = (float(r), abs(pred - obs), roll, Mt, Mb)
        ok = [c[0] for c in curve if abs(c[1] - obs) <= 0.10]
        gain = math.exp(0.5 * (math.log(Lt / best[3]) + math.log(Lb / best[4])))
        row = {"s_px": float(s), "L_top_lin": Lt, "L_bot_lin": Lb, "L_top_srgb": float(lin_to_srgb8(Lt)),
               "L_bot_srgb": float(lin_to_srgb8(Lb)), "q": q, "ratio_r": best[0], "ratio_roll": best[2],
               "ratio_resid_log": best[1], "ratio_band10": [min(ok), max(ok)] if ok else None,
               "gain_fitted": gain, "ratio_curve": [(c[0], round(c[1], 4)) for c in curve[::4]]}
        if gain1:
            g1 = None
            for r in R_GRID[::2]:
                for roll in np.arange(-12, 12.01, 0.5):
                    nt = facet_normal(mt, r / ct, blade, roll, pitch)
                    nb = facet_normal(mb, r / cb, blade, roll, pitch)
                    Mt, Mb = mc(nt[:2], pt), mc(nb[:2], pb)
                    if not (np.isfinite(Mt) and np.isfinite(Mb)):
                        continue
                    e = math.log(Mt / Lt) ** 2 + math.log(Mb / Lb) ** 2
                    if g1 is None or e < g1[1]:
                        g1 = (float(r), e, float(roll))
            row.update({"gain1_r": g1[0], "gain1_roll": g1[2], "gain1_rms_log": math.sqrt(g1[1] / 2)})
        rows.append(row)
    return rows
