

# =========================================================================== v3: parametric matcap, forward-fitted
# The free-grid de-blur (v2) is ill-conditioned (ripples make the RATIO curve non-monotonic).  v3 fits a physically
# shaped matcap instead: a metal reflecting an environment of SKY above a soft HORIZON plus one soft KEY lobe,
#     r(n) = 2 (n.v) n - v   (v = (0, 0, 1) orthographic; or the per-pixel view vector with a known focal)
#     M = lo + (hi - lo) * logistic((r.U - c) / w) + amp * exp((r.K - 1) / kappa)
# U, K unit vectors (2 angles each).  Roughness and probe blur-free shape are absorbed by w and kappa; the PROBE PIXELS
# are predicted through the pixel footprint (1 px box x Gaussian PSF), so the image blur is modelled, not baked in.


def _unit_from(theta, phi):
    """theta: image-plane direction (rad, x right / y down), phi: tilt toward the camera (+z)."""
    return np.array([math.cos(phi) * math.cos(theta), math.cos(phi) * math.sin(theta), math.sin(phi)])


class ParamMatcap:
    NAMES = ("lo", "hi", "th_u", "ph_u", "c", "w", "amp", "th_k", "ph_k", "kappa")

    def __init__(self, lum, d_of_xy, pixels, sig_psf=0.35, persp=None, starts=None, log=True):
        ox, oy, ow = _footprint(sig_psf, n=7)
        X, Y, V, PX = [], [], [], []
        for (x, y) in pixels:
            nx, ny, inside = d_of_xy(x + ox, y + oy)
            if not np.all(inside):
                continue
            X.append(nx)
            Y.append(ny)
            V.append(lum[int(round(y)), int(round(x))])
            PX.append((x, y))
        self.nx, self.ny = np.array(X), np.array(Y)
        self.w = ow
        self.obs = np.array(V)
        self.px = np.array(PX, float)
        self.persp = persp
        self.log = log
        lo0, hi0 = np.percentile(self.obs, 5), np.percentile(self.obs, 97)
        best = None
        for c0 in (starts or (-0.3, 0.0, 0.3)):
            for thk in (-2.3, -1.57, -0.8):
                p0 = np.array([lo0, hi0 - lo0 + lo0, -math.pi / 2, 0.0, c0, 0.15, 0.0, thk, 0.3, 0.15])
                p, e = self._lm(p0)
                if best is None or e < best[1]:
                    best = (p, e)
        self.p = best[0]
        self.rms = float(math.sqrt(best[1] / len(self.obs)))

    # ---------------------------------------------------------------- model
    def _M(self, p, nx, ny, vx=0.0, vy=0.0):
        lo, hi, thu, phu, c, w, amp, thk, phk, kap = p
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
        vz = np.sqrt(1 - vx * vx - vy * vy)
        ndv = nx * vx + ny * vy + nz * vz
        rx, ry, rz = 2 * ndv * nx - vx, 2 * ndv * ny - vy, 2 * ndv * nz - vz
        U = _unit_from(thu, phu)
        K = _unit_from(thk, phk)
        su = (rx * U[0] + ry * U[1] + rz * U[2] - c) / max(abs(w), 1e-3)
        sky = lo + (hi - lo) / (1 + np.exp(-np.clip(su, -60, 60)))
        key = abs(amp) * np.exp((rx * K[0] + ry * K[1] + rz * K[2] - 1) / max(abs(kap), 1e-3))
        return sky + key

    def _pred(self, p):
        if self.persp is not None:
            f, cx, cy = self.persp
            vx = (-(self.px[:, 0] - cx) / f)[:, None]
            vy = (-(self.px[:, 1] - cy) / f)[:, None]
        else:
            vx = vy = 0.0
        return (self._M(p, self.nx, self.ny, vx, vy) * self.w[None, :]).sum(1)

    def _res(self, p):
        pr = self._pred(p)
        if self.log:
            return np.log(np.maximum(pr, 1e-4)) - np.log(np.maximum(self.obs, 1e-4))
        return pr - self.obs

    def _lm(self, p0, iters=60):
        p = p0.astype(float).copy()
        r = self._res(p)
        e = float(r @ r)
        mu = 1e-2
        for _ in range(iters):
            J = np.empty((len(r), len(p)))
            for k in range(len(p)):
                dp = np.zeros_like(p)
                dp[k] = 1e-4 * max(1.0, abs(p[k]))
                J[:, k] = (self._res(p + dp) - r) / dp[k]
            A = J.T @ J
            g = J.T @ r
            improved = False
            for _t in range(8):
                try:
                    step = -np.linalg.solve(A + mu * np.diag(np.diag(A) + 1e-9), g)
                except np.linalg.LinAlgError:
                    mu *= 10
                    continue
                pn = p + step
                rn = self._res(pn)
                en = float(rn @ rn)
                if en < e:
                    p, r, e = pn, rn, en
                    mu = max(mu / 3, 1e-7)
                    improved = True
                    break
                mu *= 10
            if not improved or np.linalg.norm(step) < 1e-7:
                break
        return p, e

    def __call__(self, n2, at_xy=None):
        vx = vy = 0.0
        if self.persp is not None and at_xy is not None:
            f, cx, cy = self.persp
            vx, vy = -(at_xy[0] - cx) / f, -(at_xy[1] - cy) / f
        return float(self._M(self.p, np.array([n2[0]]), np.array([n2[1]]), vx, vy)[0])

    def describe(self):
        return {k: float(v) for k, v in zip(self.NAMES, self.p)} | {"fit_rms_log": self.rms, "n_px": len(self.obs)}
