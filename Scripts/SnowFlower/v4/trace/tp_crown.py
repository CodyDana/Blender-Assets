"""Trace pilot - the crown surface the traced plates are wrapped onto (numpy only).

Sheath frame (same as round 1, mm): origin = mid-band centre on the axis, +Z toward the chape point, +X = viewer's LEFT
in the reference front view, -Y = the front face.  Reference px -> mm:  z = (row - 304) K,  x = (505.5 - col) K.

The crown section at a row is the smooth outer envelope of
    * the round-1 lacquer core (flattened octagon, core_w / body_d copied from the r1 shv4_spec) + a shell standoff
    * a super-ellipse whose half-width is the reference SILHOUETTE half-width of that row (traced per side) and whose
      half-depth is the core's half-depth + standoff.
so the front view of the crown is exactly the traced silhouette, and plates that reach the silhouette turn back to the
side plane (y = 0) the way the reference's foreshortened flare panels read.  The back is the mirror (y -> -y).
Offsetting a plate by h along the surface normal is solved so that its FRONT-VIEW x stays the traced x."""
import numpy as np

K = 0.687
AXIS = 505.5
P_SE = 2.5

def zr(row): return (np.asarray(row, float) - 304.0) * K
def row_of(z): return np.asarray(z, float) / K + 304.0
def xc(col): return (AXIS - np.asarray(col, float)) * K

# ---- round-1 core (copied from Scripts_v4/shv4_spec.py of the r1 snapshot; read-only reference)
BODY_PX = [(31, 97.0), (169, 97.0), (250, 97.0), (286, 97.0), (322, 96.0), (340, 96.0), (400, 95.0), (500, 92.0)]
DEPTH_ROWS = [(31, 22.0), (169, 22.0), (1292, 17.0), (1400, 16.4)]
THROAT_EXTRA = 2.0
THROAT_DEPTH_EXTRA = 9.0
THROAT_DEPTH_ROWS = (62.0, 100.0)
def body_w(row):
    r, w = zip(*BODY_PX); return np.interp(np.asarray(row, float), r, w) * K
def core_w(row):
    row = np.asarray(row, float)
    e = THROAT_EXTRA * np.clip((140.0 - row) / (140.0 - 60.0), 0.0, 1.0)
    return body_w(row) + 2 * e
def body_d(row):
    r, d = zip(*DEPTH_ROWS); row = np.asarray(row, float)
    a, b = THROAT_DEPTH_ROWS
    e = THROAT_DEPTH_EXTRA * np.clip((b - row) / (b - a), 0.0, 1.0)
    return np.interp(row, r, d) + 2 * e

def standoff(row):
    """shell standoff over the core (mm): 2.2 under the plates, 1.2 on the sleeve (spec: sleeve 2.5 px proud)."""
    t = np.clip((np.asarray(row, float) - 138.0) / 12.0, 0, 1)
    return 2.2 - 1.0 * t * t * (3 - 2 * t)

OCT_U = np.array([0.0, 0.51, 0.93, 1.0])
OCT_V = np.array([1.0, 1.0, 0.40, 0.13])

class Crown:
    def __init__(self, sil_rows, sub=None, sigma_rows=3.0):
        """sub = trace.json['silhouette_sub'] (sub-pixel iso crossings on every 1/6 row) - preferred; the integer
        per-row extents are the fallback.  A light Gaussian (sigma_rows) removes the pixel staircase that otherwise
        prints as horizontal banding in the silver reflections; an upper envelope keeps every traced point inside."""
        if sub is not None:
            rows = np.asarray(sub["rows"], float); L = np.asarray(sub["left"], float); R = np.asarray(sub["right"], float)
            step = rows[1] - rows[0]
        else:
            rows = np.array(sorted(int(k) for k in sil_rows), float)
            L = np.array([sil_rows[str(int(r))][0] for r in rows], float); R = np.array([sil_rows[str(int(r))][1] for r in rows], float)
            step = 1.0
        aL = (AXIS - L) * K; aR = (R - AXIS) * K
        n = max(int(round(sigma_rows / step * 3)), 1)
        k = np.exp(-0.5 * (np.arange(-n, n + 1) * step / sigma_rows) ** 2); k /= k.sum()
        def sm(a):
            g = np.convolve(np.pad(a, n, mode='edge'), k, 'valid')
            return np.maximum(g, a - 0.6)           # never more than 0.6 mm inside the traced silhouette
        self.rows, self.aL, self.aR = rows, sm(aL), sm(aR)

    def params(self, row, side):
        """side = +1 (+X, viewer's left) or -1; returns A, B, c, b arrays."""
        row = np.asarray(row, float)
        A = np.where(side > 0, np.interp(row, self.rows, self.aL), np.interp(row, self.rows, self.aR))
        s = standoff(row)
        # smoothstep versions of the r1 core's linear fades (a linear fade prints a crease across the crown at the row
        # where it ends; the smoothstep stays within 0.9 mm of it, well inside the 2.2 mm standoff)
        def sstep(t):
            t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
        e_w = THROAT_EXTRA * sstep((140.0 - row) / 80.0)
        a_, b_ = THROAT_DEPTH_ROWS
        e_d = THROAT_DEPTH_EXTRA * sstep((b_ - row) / (b_ - a_))
        r_, d_ = zip(*DEPTH_ROWS)
        c = body_w(row) / 2 + e_w + s
        b = np.interp(row, r_, d_) / 2 + e_d + s
        A = np.maximum(A, 1.0)
        return A, b, c, b

    @staticmethod
    def f(xa, A, B, c, b, k=1.2):
        """front y (negative) of the crown at |x| = xa."""
        u = xa / c
        f_oct = np.where(u <= 1.0, b * np.interp(np.clip(u, 0, 1), OCT_U, OCT_V), 0.0)
        t = np.clip(xa / A, 0.0, 1.0)
        f_se = B * np.clip(1.0 - t ** P_SE, 0.0, 1.0) ** (1.0 / P_SE)
        f_se = np.where(xa <= A, f_se, 0.0)
        g = 0.5 * (f_oct + f_se + np.sqrt((f_oct - f_se) ** 2 + k * k)) - 0.5 * k   # smooth max of the two depths
        return -np.maximum(g, 0.0)

    def xmax(self, A, c):
        return np.maximum(A, c)

    def map(self, x_front, row, off, back=False):
        """front-view (x mm, row) + outward offset (mm) -> 3D (x, y, z) mm; x of the result == x_front."""
        x_front = np.asarray(x_front, float); row = np.asarray(row, float); off = np.asarray(off, float) * np.ones_like(x_front)
        side = np.where(x_front >= 0, 1, -1)
        xa = np.abs(x_front)
        A, B, c, b = self.params(row, side)
        xm = self.xmax(A, c) - 0.02
        h = 0.04
        def fx(x):
            y = self.f(x, A, B, c, b)
            d = (self.f(np.minimum(x + h, xm + 0.02), A, B, c, b) - self.f(np.maximum(x - h, 0), A, B, c, b)) / (np.minimum(x + h, xm + 0.02) - np.maximum(x - h, 0))
            nrm = np.sqrt(1 + d * d)
            return y, d / nrm, -1.0 / nrm        # y, n_x, n_y (outward, front)
        lo = np.zeros_like(xa); hi = xm.copy()
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            y, nx, ny = fx(mid)
            g = mid + off * nx - xa
            lo = np.where(g < 0, mid, lo); hi = np.where(g >= 0, mid, hi)
        xp = 0.5 * (lo + hi)
        y, nx, ny = fx(xp)
        X = side * (xp + off * nx)
        Y = y + off * ny
        if back: Y = -Y
        return np.c_[X, Y, zr(row)]
