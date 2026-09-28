r"""Snow Flower sheath look-match round 1 (2026-09-27): CAST PLATES as real geometry.

The reference's throat, band and chape are raised, bevelled, overlapping cast plates: a thick rounded silver frame
around a cupped dark inset (or a solid silver field), stacked in tiers.  The v4 build baked their OUTLINES onto flat
blocks; this module models them.

A plate is a LEAF: a spine (base -> tip) in the reference front view plus two half-width profiles (side a = the
spine tangent rotated +90 deg in the (x, z) plane, side b = the other side).  Its cross-section across the spine is
a closed slab:

        crest                 dish / keel (dark inset) or flat field (silver)
       _/^^\_______________________/^^\_
      |                                 |      <- outer wall (bevel)
      |_________________________________|      <- underside (on the envelope, hidden on the body)

Front-view (x, z) points are mapped onto an ENVELOPE (a smooth surface around the sheath) and lifted along its
normal by the tier lift + the profile height + an optional tip curl.  Because only y is assigned, the front view of
every plate is exactly its designed outline.  One function builds LOD0 / LOD1 / LOD2 (column and row subsets of the
same parameterisation, so every LOD samples the same UV islands) and the high-poly (denser, rounded crest).

Millimetres, sheath frame (shv4_spec): +Z toward the chape point, +X the image LEFT in the reference front view,
-Y the front face.
"""
from __future__ import annotations

import math

import numpy as np

import shv4_spec as S
from sfv4_mesh import MB, _norm, arclen, catmull, resample

# high-poly material indices (shv4_parts H_*: H_LACQ, H_SILVER, H_INLAY, H_RECESS, H_INSET, H_BRANCH, H_CAVITY,
# H_ANTIQUE)
H_SILVER, H_INSET, H_ANTIQUE = 1, 4, 7


# ====================================================================== envelopes

def _se(q, m):
    q = min(abs(q), 0.999)
    return (1.0 - q ** m) ** (1.0 / m)


class Envelope:
    """Front/back surface y = side * Y(x, z) with an outward normal.  Subclasses define Y."""
    name = "env"

    def Y(self, x, z):
        raise NotImplementedError

    def body_factor(self, x, z):
        """1 where the envelope is a real surface under the plate (the plate's wall reaches down to it), 0 where the
        plate floats free (beyond the bulb's sides); a 2 mm ramp between."""
        return 1.0

    def point(self, x, z, side):
        return np.array([x, side * self.Y(x, z), z])

    def normal(self, x, z, side, h=0.05):
        dydx = (self.Y(x + h, z) - self.Y(x - h, z)) / (2 * h)
        dydz = (self.Y(x, z + h) - self.Y(x, z - h)) / (2 * h)
        # surface (x, s*Y, z): tangents (1, s*Yx, 0), (0, s*Yz, 1); outward normal has y of sign s
        n = np.array([-dydx, side * 1.0, -dydz])
        return _norm(n)


class CrownEnv(Envelope):
    """The throat crown: a superellipse bulb |y| = Yb(row) * se(|x| / AX, M) (virtual beyond the bulb's sides)."""
    name = "crown"

    def Y(self, x, z):
        row = float(S.row_of(z))
        return S.crown_Yb(row) * _se(x / S.CROWN_AX, S.CROWN_M)

    def body_factor(self, x, z):
        """1 where the bulb is under the plate (its wall reaches down to it); 0 where the bulb has curved away."""
        row = float(S.row_of(z))
        a, yb = S.crown_half(row), S.crown_Yb(row)
        if abs(x) >= a:
            return 0.0
        y_sq = yb * (1.0 - (abs(x) / a) ** S.CROWN_SIDE_M) ** (1.0 / S.CROWN_SIDE_M)
        gap = self.Y(x, z) - y_sq
        return float(np.clip(1.0 - gap / 4.0, 0.0, 1.0))


class ChapeEnv(Envelope):
    name = "chape"

    def Y(self, x, z):
        row = float(S.row_of(z))
        return S.chape_Yb(row) * _se(x / S.chape_ax(row), S.chape_m(row))

    def body_factor(self, x, z):
        a = S.chape_body_half(float(S.row_of(z)))
        return float(np.clip((a - abs(x)) / 2.0, 0.0, 1.0))


class CoreEnv(Envelope):
    """The faceted lacquer core, smoothed (the band's leaf plates sit on its front face and chamfers)."""
    name = "core"

    def Y(self, x, z):
        row = float(S.row_of(z))
        c = float(S.core_w(row)) / 2
        b = float(S.body_d(row)) / 2
        # smooth superellipse that hugs the octagon's front face and chamfers from outside
        return (b + 0.05) * _se(x / (c * 1.02), 4.2)


class BandEnv(Envelope):
    name = "band"

    def Y(self, x, z):
        row = float(S.row_of(z))
        c = float(S.core_w(row)) / 2 + S.T_BAND
        b = float(S.body_d(row)) / 2 + S.T_BAND
        return b * _se(x / (c * 1.05), 4.0)


ENVS = {"crown": CrownEnv(), "chape": ChapeEnv(), "core": CoreEnv(), "band": BandEnv()}


# ====================================================================== leaf definition

class Leaf:
    """spine: [(dx_px, row)] base -> tip in the reference front view (dx = x_px - 505.5, image-right +).
    wa / wb: [(t, half-width px)] for the two sides (a = +90 deg of the tangent in the IMAGE (dx, row) plane;
    for a spine pointing down the image, a is the image-LEFT side... see _frame).  fill: 'dish' | 'keel' (dark inset)
    or 'silver' (solid field).  T: crest height; F: frame width (mm); tier: stacking level; curl: extra lift (mm) at the
    tip (t -> 1) along the envelope normal, ramping in from t = curl_t0."""

    def __init__(self, name, spine, wa, wb=None, tier=0, env="crown", fill="dish", T=1.9, F=2.2, curl=0.0,
                 curl_t0=0.55, pair=True, sides=(-1, 1), lift0=0.15, dish=0.45, keel=0.35, tier_step=1.25,
                 rows0=None, base_curl=0.0, cup=0.8, lobes=0, lobe_depth=0.22, hmat=None):
        self.name, self.spine, self.wa = name, spine, wa
        self.wb = wb if wb is not None else wa
        self.tier, self.env, self.fill = tier, env, fill
        self.T, self.F, self.curl, self.curl_t0 = T, F, curl, curl_t0
        self.pair, self.sides, self.lift0 = pair, sides, lift0
        self.dish, self.keel, self.tier_step = dish, keel, tier_step
        self.rows0 = rows0
        self.base_curl = base_curl
        self.cup = cup
        self.lobes, self.lobe_depth, self.hmat = lobes, lobe_depth, hmat

    @property
    def lift(self):
        return self.lift0 + self.tier * self.tier_step

    def mirrored(self):
        sp = [(-dx, r) for dx, r in self.spine]
        m = Leaf(self.name, sp, self.wb, self.wa, self.tier, self.env, self.fill, self.T, self.F, self.curl,
                 self.curl_t0, False, self.sides, self.lift0, self.dish, self.keel, self.tier_step, self.rows0,
                 self.base_curl, self.cup, self.lobes, self.lobe_depth, self.hmat)
        return m


def expand(leaves):
    """-> [(tag, Leaf)] with the mirrored partners of paired leaves (tag R = as designed, L = mirrored)."""
    out = []
    for lf in leaves:
        if lf.pair:
            out.append((lf.name + "R", lf))
            out.append((lf.name + "L", lf.mirrored()))
        else:
            out.append((lf.name, lf))
    return out


# ====================================================================== geometry

def _pchip(xk, yk, x):
    """Monotone cubic (Fritsch-Carlson) interpolation."""
    xk, yk = np.asarray(xk, float), np.asarray(yk, float)
    x = np.asarray(x, float)
    n = len(xk)
    if n == 1:
        return np.full_like(x, yk[0])
    h = np.diff(xk)
    d = np.diff(yk) / h
    m = np.zeros(n)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    i = np.clip(np.searchsorted(xk, x) - 1, 0, n - 2)
    t = (x - xk[i]) / h[i]
    h00 = (2 * t ** 3 - 3 * t ** 2 + 1)
    h10 = (t ** 3 - 2 * t ** 2 + t)
    h01 = (-2 * t ** 3 + 3 * t ** 2)
    h11 = (t ** 3 - t ** 2)
    return h00 * yk[i] + h10 * h[i] * m[i] + h01 * yk[i + 1] + h11 * h[i] * m[i + 1]


def spine_mm(leaf, n):
    """(n, 2) spine points in model mm (x, z), evenly by arclength, + unit tangents and the side-a normals."""
    P = np.array([[float(S.xp(S.X_AXIS_PX + dx)), float(S.zr(r))] for dx, r in leaf.spine])
    if len(P) > 2:
        C = catmull(P, steps=10)
    else:
        C = np.vstack([P[0] + (P[1] - P[0]) * t for t in np.linspace(0, 1, 11)])
    R = resample(C, n)
    T = np.gradient(R, axis=0)
    T = T / np.linalg.norm(T, axis=1)[:, None]
    # side a: tangent rotated +90 deg in the IMAGE plane (image x = -model x, image down = +z): in model (x, z) that
    # is (tx, tz) -> (tz, -tx)... define it once here and keep it (mirrored leaves swap wa / wb)
    Na = np.stack([T[:, 1], -T[:, 0]], 1)
    return R, T, Na


def widths(leaf, t):
    """half-widths (mm) on side a / b at spine parameters t."""
    ta, wa = zip(*leaf.wa)
    tb, wb = zip(*leaf.wb)
    a = np.maximum(_pchip(ta, np.asarray(wa) * S.K, t), 0.0)
    b = np.maximum(_pchip(tb, np.asarray(wb) * S.K, t), 0.0)
    if leaf.lobes:
        # acanthus lobes: a scalloped edge (sharp notches between rounded lobes)
        ph = np.asarray(t) * leaf.lobes * math.pi
        k = 1.0 - leaf.lobe_depth * (1.0 - np.abs(np.sin(ph)) ** 0.5)
        a, b = a * k, b * np.roll(k, 0)
    return a, b


def frame_profile(leaf, d, w):
    """Profile height (mm above the tier lift) at inward distance d from the edge, for a half-width w.
    The frame is a flat-topped cast band with rounded shoulders (the reference's thick bevelled frames)."""
    T, F = leaf.T, leaf.F
    d = min(d, w)
    wall = 0.3
    if d <= wall:
        return -0.25 + (T - 0.5 + 0.25) * (d / wall)
    if leaf.fill == "silver":
        # bevel up to the crest by 0.6 F, then a flat raised field a hair below the crest
        if d <= 0.6 * F:
            s = (d - wall) / max(0.6 * F - wall, 1e-6)
            return T - 0.5 + 0.5 * math.sin(0.5 * math.pi * s)
        if d <= 0.6 * F + 0.35:                 # a fine groove that separates the rim from the field
            return T - 0.3
        return T - 0.12
    sh = min(0.3, 0.2 * F)                      # rounded outer / inner shoulders (narrow: a broad flat crest)
    if d <= wall + sh:
        s = (d - wall) / sh
        return T - 0.5 + 0.5 * math.sin(0.5 * math.pi * s)
    if d <= F - 0.1 - sh:                       # plateau, faintly convex
        s = (d - wall - sh) / max(F - 0.1 - 2 * sh - wall, 1e-6)
        return T + 0.06 * math.sin(math.pi * s)
    if d <= F - 0.1:
        s = (d - (F - 0.1 - sh)) / sh
        return T - 0.5 * (1 - math.cos(0.5 * math.pi * s))
    if d <= F + 0.3:                            # inner wall down to the inset floor
        s = (d - (F - 0.1)) / 0.4
        if leaf.fill == "open":
            return T - 0.5 - (T - 0.5 + leaf.lift + 2.5) * s
        return T - 0.5 - 0.55 * s
    if leaf.fill == "open":                     # an open frame: the interior drops below the surface it sits on
        return -leaf.lift - 2.5
    floor = T - 1.05
    span = max(w - (F + 0.3), 1e-6)
    s = min(1.0, (d - (F + 0.3)) / span)
    if leaf.fill == "keel":
        return floor + leaf.keel * s ** 1.5
    depth = leaf.dish * min(1.0, span / 2.5)
    return floor - depth * math.sin(0.5 * math.pi * s)


def _columns(leaf, level):
    """Inward distances (mm) of the columns on ONE side, edge -> centre ('C' = the spine)."""
    F = leaf.F
    if level == "high":
        sh = min(0.3, 0.2 * F)
        cols = [0.0, 0.1, 0.3] + list(0.3 + sh * np.array([0.25, 0.5, 0.75, 1.0])) +             list(np.linspace(0.3 + sh, F - 0.1 - sh, 5)[1:-1]) + list(F - 0.1 - sh * np.array([1.0, 0.75, 0.5, 0.25, 0.0])) +             [F + 0.1, F + 0.3]
        cols += [F + 0.3 + k for k in (0.6, 1.3, 2.2, 3.4, 5.0, 7.0, 10.0)]
    elif level == 0:
        cols = [0.0, 0.3, 0.3 + min(0.3, 0.2 * F), F - 0.1 - min(0.3, 0.2 * F), F + 0.3, F + 1.8]
    elif level == 1:
        cols = [0.0, 0.5 * F, F + 0.3]
    else:
        cols = [0.0, 0.5 * F]
    if leaf.fill == "silver":
        if level == "high":
            cols = [0.0, 0.1, 0.25] + list(np.linspace(0.25, 0.6 * F, 6)[1:]) + [0.6 * F + 0.1, 0.6 * F + 0.25,
                                                                                 0.6 * F + 0.4, 0.6 * F + 1.0]
            cols += [0.6 * F + 0.4 + k for k in (1.5, 3.0, 5.0, 8.0)]
        elif level == 0:
            cols = [0.0, 0.25, 0.6 * F, 0.6 * F + 0.4, 0.6 * F + 2.0]
        elif level == 1:
            cols = [0.0, 0.6 * F, 0.6 * F + 0.4]
    return cols


def _nrows(leaf, level, L):
    if level == "high":
        return max(int(L / 0.7), 24)
    base = leaf.rows0 or max(int(L / 5.0), 7)
    return {0: base, 1: max(base // 2 + 1, 5), 2: max(base // 3 + 1, 4)}[level]


def _row_params(leaf, level, L):
    n0 = _nrows(leaf, 0, L)
    t0 = np.linspace(0, 1, n0)
    if level == "high":
        return np.linspace(0, 1, _nrows(leaf, "high", L))
    if level == 0:
        return t0
    step = 2 if level == 1 else 3
    keep = list(range(0, n0, step))
    if keep[-1] != n0 - 1:
        keep.append(n0 - 1)
    return t0[keep]


def _u_of(leaf, d, w, fine=48):
    """Distance from the plate's mid-line to the column at inward distance d, measured ALONG the profile (mm): the
    across UV coordinate.  Evaluated on a fine profile so every LOD's column gets the same u."""
    if w <= 1e-6:
        return 0.0
    ds = np.linspace(min(d, w), w, fine)
    hs = np.array([frame_profile(leaf, x, w) for x in ds])
    return float(np.sum(np.hypot(np.diff(ds), np.diff(hs))))


def _face(mb, q, uv, island, mat):
    """Add a face with repeated (collapsed) corners removed; skip it if fewer than 3 corners remain."""
    qq, uu = [], []
    n = len(q)
    for i in range(n):
        if q[i] != q[(i + 1) % n]:
            qq.append(q[i])
            uu.append(uv[i] if uv is not None else None)
    if len(set(qq)) < 3 or len(qq) != len(set(qq)):
        if len(set(qq)) >= 3:
            seen, q2, u2 = set(), [], []
            for a, b in zip(qq, uu):
                if a not in seen:
                    seen.add(a)
                    q2.append(a)
                    u2.append(b)
            qq, uu = q2, u2
        else:
            return 0
    mb.f(qq, uu if uv is not None else None, island, mat)
    return 1


def build_leaf(mb: MB, leaf: Leaf, side, level, island, mat_low=1, high=False):
    """Append the closed plate slab to ``mb`` (LOD ``level`` 0/1/2 or "high").  Returns the number of faces."""
    env = ENVS[leaf.env]
    nfine = 240
    R, Tn, Na = spine_mm(leaf, nfine)
    L = float(arclen(R)[-1])
    tt = _row_params(leaf, level, L)
    cols_one = _columns(leaf, level)
    wa, wb = widths(leaf, tt)
    rows_idx, rows_uv, rows_d, rows_und = [], [], [], []
    for i, t in enumerate(tt):
        k = int(round(t * (nfine - 1)))
        na = Na[k]
        w = 0.5 * (wa[i] + wb[i])
        mid = R[k] + na * 0.5 * (wa[i] - wb[i])
        curl = 0.0
        if leaf.curl and t > leaf.curl_t0:
            curl = leaf.curl * ((t - leaf.curl_t0) / (1 - leaf.curl_t0)) ** 2
        if leaf.base_curl and t < 0.3:
            curl += leaf.base_curl * ((0.3 - t) / 0.3) ** 2
        if w < 1e-4:
            x, z = mid
            bf = env.body_factor(x, z)
            p = env.point(x, z, side) + env.normal(x, z, side) * (leaf.lift + curl - 0.3 - leaf.lift * bf)
            vi = mb.v(p)
            n = 2 * len(cols_one) + 1
            rows_idx.append([vi] * n)
            rows_uv.append([(0.0, float(t * L))] * n)
            rows_d.append([0.0] * n)
            rows_und.append(([vi] * 3, [0.0] * 3))
            continue
        ds = [min(d, w) for d in cols_one]
        cols = [(-(w - d), d) for d in ds] + [(0.0, w)] + [((w - d), d) for d in ds[::-1]]
        pts, uvs, dl = [], [], []
        for u, d in cols:
            x, z = mid + na * u
            nrm = env.normal(x, z, side)
            if d <= 1e-9:
                h = -0.3 - leaf.lift * env.body_factor(x, z)
            else:
                h = frame_profile(leaf, d, w)
            cupv = leaf.cup * (abs(u) / w) ** 2 if w > 1e-6 else 0.0      # the leaf is cupped: edges raised
            pts.append(env.point(x, z, side) + nrm * (leaf.lift + h + curl + cupv))
            uu = _u_of(leaf, d, w) if not high else 0.0
            uvs.append((float(np.sign(u) * uu), float(t * L)))
            dl.append(d)
        ids = []
        prev_key = None
        for kk, (u, d) in enumerate(cols):
            key = (round(u, 6), round(d, 6))
            if key == prev_key:
                ids.append(ids[-1])
            else:
                ids.append(mb.v(pts[kk]))
            prev_key = key
        rows_idx.append(ids)
        rows_uv.append(uvs)
        rows_d.append(dl)
        # the underside follows the envelope (a straight chord across a cupped, curling leaf can poke through its top)
        und, uu_ = [ids[0]], [-w]
        for u in (0.0,):
            x, z = mid + na * u
            nrm = env.normal(x, z, side)
            cupv = leaf.cup * (abs(u) / w) ** 2
            h = -0.3 - leaf.lift * env.body_factor(x, z)
            und.append(mb.v(env.point(x, z, side) + nrm * (leaf.lift + h + curl + cupv)))
            uu_.append(u)
        und.append(ids[-1])
        uu_.append(w)
        rows_und.append((und, uu_))    # [edge b, centre, edge a]
    ncol = len(rows_idx[0])
    nf = 0
    for i in range(len(tt) - 1):
        for c in range(ncol - 1):
            q = [rows_idx[i][c], rows_idx[i][c + 1], rows_idx[i + 1][c + 1], rows_idx[i + 1][c]]
            uv = [rows_uv[i][c], rows_uv[i][c + 1], rows_uv[i + 1][c + 1], rows_uv[i + 1][c]]
            if high:
                dm = 0.25 * (rows_d[i][c] + rows_d[i][c + 1] + rows_d[i + 1][c + 1] + rows_d[i + 1][c])
                m = H_SILVER if (leaf.fill == "silver" or dm < leaf.F + 0.05) else H_INSET
                if leaf.hmat is not None and m == H_SILVER:
                    m = leaf.hmat
                nf += _face(mb, q, None, "HIGH", m)
            else:
                nf += _face(mb, q, uv, island + "_top", mat_low)
    # underside: edge b -> edge a through three interior points on the envelope, every row
    for i in range(len(tt) - 1):
        (u0i, u0u), (u1i, u1u) = rows_und[i], rows_und[i + 1]
        for c in range(2):
            q = [u0i[c + 1], u0i[c], u1i[c], u1i[c + 1]]
            uv = [(u0u[c + 1], tt[i] * L), (u0u[c], tt[i] * L), (u1u[c], tt[i + 1] * L), (u1u[c + 1], tt[i + 1] * L)]
            if high:
                nf += _face(mb, q, None, "HIGH", H_SILVER)
            else:
                nf += _face(mb, q, uv, island + "_under", mat_low)
    return nf


def leaf_outline_px(leaf, n=120):
    """Closed front-view outline in reference px (x_px, row) - for overlays."""
    R, Tn, Na = spine_mm(leaf, 200)
    t = np.linspace(0, 1, n)
    wa, wb = widths(leaf, t)
    k = np.round(t * 199).astype(int)
    A = R[k] + Na[k] * wa[:, None]
    B = R[k] - Na[k] * wb[:, None]
    P = np.vstack([A, B[::-1]])
    return np.stack([S.X_AXIS_PX - P[:, 0] / S.K, P[:, 1] / S.K + S.ROW_BAND], 1)


def leaves_from(table, env):
    out = []
    for d in table:
        d = dict(d)
        out.append(Leaf(d.pop("name"), d.pop("spine"), d.pop("wa"), d.pop("wb", None), env=d.pop("env", env), **d))
    return out
