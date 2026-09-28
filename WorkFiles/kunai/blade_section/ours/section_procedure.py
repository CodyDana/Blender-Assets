"""The blade-section measurement procedure, applied identically to the photo and to our renders.

Why shading: both blind measurers found the photo's blade is seen almost FACE-ON (the ridge sits on the edge midline to
~0.01 of the half-width), so line geometry cannot read ridge height.  The number comes from shape-from-shading with a
round-tube LIGHT PROBE (the photo's ring; a round-section probe torus in our validation renders):

  1. probe -> matcap: every pixel across the tube gives (image-plane normal = d * radial dir, d = position across the
     tube in -1..1) and its LINEAR luminance (sRGB decoded; an albedo is a gain in linear light, not in sRGB).
  2. facets: at each station along the axis the upper and lower facet luminance (median of the 30-70 % band between the
     ridge line and the edge line, +-2 px along the axis).
  3. model: a planar facet through its edge line rising to the ridge; its normal tilts toward its edge by G (gradient,
     perpendicular to the edge line in the image); face_slope = G * cos(edge-vs-axis angle) (measured square to the
     axis).  Roll (about the axis) and pitch rotate both normals.
  4. estimators
       RATIO   (albedo-free): roll from the measured ridge offset q = r tan(roll); solve r from L_top / L_bot.
       GAIN1   (albedo = probe): solve r and roll from L_top and L_bot with gain 1.
       GAINFIT (albedo free, roll from q): r and the gain from both facets (least squares in log).
     RATIO is the primary one: the blade/probe albedo ratio is the photo's biggest unknown (measurers A vs B).

Coordinates: image x right, y down, z toward the camera.  Roll + = the camera-facing normals tilt image-UP (the top
edge turns away from the camera; the ridge's image moves toward the top edge).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

PHOTO_PATH = "C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg"
BS = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/kunai/blade_section"


# =========================================================================== image
def srgb_to_lin(a):
    a = np.asarray(a, float) / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def load_lum(path, bg=None):
    """Linear Rec.709 luminance (0..1) and alpha (1 for a JPEG)."""
    im = Image.open(path)
    if im.mode == "RGBA":
        arr = np.asarray(im).astype(float)
        alpha = arr[..., 3] / 255.0
        rgb = arr[..., :3]
    else:
        rgb = np.asarray(im.convert("RGB")).astype(float)
        alpha = np.ones(rgb.shape[:2])
    lin = srgb_to_lin(rgb)
    lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    return lum, alpha


def lin_to_srgb8(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055) * 255.0


def bilin(a, x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    x0 = np.clip(np.floor(x).astype(int), 0, a.shape[1] - 2)
    y0 = np.clip(np.floor(y).astype(int), 0, a.shape[0] - 2)
    fx, fy = x - x0, y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) + a[y0 + 1, x0] * (1 - fx) * fy
            + a[y0 + 1, x0 + 1] * fx * fy)


# =========================================================================== geometry
class Blade:
    """Axial frame: s along the axis from the shoulder (px), u along the cross direction (toward the TOP edge)."""

    def __init__(self, origin, axis_d, top_fn, bot_fn, ridge_fn, L_crease, L_visible, L_tip):
        self.o = np.asarray(origin, float)
        self.a = np.asarray(axis_d, float) / np.linalg.norm(axis_d)
        # cross direction: perpendicular to the axis, pointing to the top edge (image up-left for an up-right axis)
        c = np.array([self.a[1], -self.a[0]])
        self.c = c
        self.top, self.bot, self.ridge = top_fn, bot_fn, ridge_fn
        self.L_crease, self.L_visible, self.L_tip = L_crease, L_visible, L_tip

    def P(self, s, u):
        return self.o + s * self.a + u * self.c

    def edge_normal(self, which, s, ds=2.0):
        """Outward unit normal (image plane) of the top / bottom edge at s, and the edge-vs-axis angle cosine."""
        fn = self.top if which == "top" else self.bot
        du = (fn(s + ds) - fn(s - ds)) / (2 * ds)
        t = self.a + du * self.c
        t = t / np.linalg.norm(t)
        n = np.array([t[1], -t[0]])               # rotate -90: for the axis itself this is +c (top side)
        if which == "bot":
            n = -n
        cos_edge = 1.0 / math.sqrt(1.0 + du * du)
        return n, cos_edge


def blade_from_lines(M):
    """Photo geometry from measurer A's line fits (measure_raw.json; B's agree to ~0.5 px)."""
    ln = M["lines"]
    o = np.array(M["shoulder_axis"], float)
    ad = np.array([math.cos(math.radians(M["axis_angle_deg"])), math.sin(math.radians(M["axis_angle_deg"]))])
    c = np.array([ad[1], -ad[0]])
    crease_s = M["L_crease_px"]

    def hit(line, s):
        P = o + s * ad
        L0 = np.array(ln[line]["c"], float)
        d = np.array(ln[line]["d"], float)
        A = np.column_stack([c, -d])
        t = np.linalg.solve(A, L0 - P)
        return float(t[0])

    def top(s):
        return hit("top_front" if s >= crease_s else "top_rear", s)

    def bot(s):
        return hit("bot_front" if s >= crease_s else "bot_rear", s)

    def ridge(s):
        return hit("ridge_front" if s >= crease_s else "ridge_rear", s)
    return Blade(o, ad, top, bot, ridge, crease_s, M["L_visible_px"], M["L_tip_px"])


def blade_from_meta(meta, scale=1.0, visible_x=None):
    """Render geometry from the render sidecar (projected design points), scaled to the analysed image."""
    P = meta["points_px"]
    o = np.array(P["shoulder_axis"]) * scale
    tip = np.array(P["tip"]) * scale
    ad = (tip - o) / np.linalg.norm(tip - o)
    c = np.array([ad[1], -ad[0]])

    def su(poly):
        arr = np.array([[p[1] * scale, p[2] * scale] for p in poly])
        rel = arr - o
        return rel @ ad, rel @ c
    st, ut = su(meta["edge_top_px"])
    sb, ub = su(meta["edge_bot_px"])
    sr, ur = su(meta["ridge_top_px"])
    J = (np.array(P["J"]) * scale - o) @ ad
    L_tip = float(np.linalg.norm(tip - o))
    xs = np.array([p[0] for p in meta["edge_top_px"]], float)
    b = Blade(o, ad, lambda s: float(np.interp(s, st, ut)), lambda s: float(np.interp(s, sb, ub)),
              lambda s: float(np.interp(s, sr, ur)), float(J), None, L_tip)
    # design x <-> s (px) mapping for this render (for the analytic comparison)
    b.x_of_s = lambda s: float(np.interp(s, st, xs))
    b.s_of_x = lambda x: float(np.interp(x, xs, st))
    if visible_x is not None:
        b.L_visible = b.s_of_x(visible_x)
    return b


# =========================================================================== probe / matcap
def probe_samples_ellipses(lum, inner, outer, dcut=0.9, excl_deg=None, bbox=None):
    """(nx, ny, L) from a ring given its inner and outer ellipses (cx, cy, a, b, major_angle_deg)."""
    def ell_r(f, psi):
        th = math.radians(f["major_angle_deg"])
        u = psi - th
        return 1 / math.sqrt((math.cos(u) / f["a"]) ** 2 + (math.sin(u) / f["b"]) ** 2)
    cx = 0.5 * (inner["cx"] + outer["cx"])
    cy = 0.5 * (inner["cy"] + outer["cy"])
    R = max(outer["a"], outer["b"]) + 2
    S = []
    for y in range(int(cy - R), int(cy + R) + 1):
        for x in range(int(cx - R), int(cx + R) + 1):
            dx, dy = x - cx, y - cy
            rr = math.hypot(dx, dy)
            psi = math.atan2(dy, dx)
            if excl_deg and excl_deg[0] <= math.degrees(psi) <= excl_deg[1]:
                continue
            ri, ro = ell_r(inner, psi), ell_r(outer, psi)
            d = (rr - 0.5 * (ri + ro)) / (0.5 * (ro - ri))
            if abs(d) > dcut:
                continue
            S.append((d * math.cos(psi), d * math.sin(psi), lum[y, x]))
    return np.array(S)


def probe_samples_centreline(lum, centre, centreline, tube_r, dcut=0.9):
    """(nx, ny, L) from a probe torus given its projected centreline polyline and tube radius (px)."""
    cx, cy = centre
    cl = np.array(centreline)
    ang = np.arctan2(cl[:, 1] - cy, cl[:, 0] - cx)
    rad = np.hypot(cl[:, 0] - cx, cl[:, 1] - cy)
    order = np.argsort(ang)
    ang, rad = ang[order], rad[order]
    ang = np.r_[ang - 2 * np.pi, ang, ang + 2 * np.pi]
    rad = np.r_[rad, rad, rad]
    R = rad.max() + tube_r + 2
    S = []
    for y in range(int(cy - R), int(cy + R) + 1):
        for x in range(int(cx - R), int(cx + R) + 1):
            dx, dy = x - cx, y - cy
            psi = math.atan2(dy, dx)
            rc = float(np.interp(psi, ang, rad))
            d = (math.hypot(dx, dy) - rc) / tube_r
            if abs(d) > dcut:
                continue
            S.append((d * math.cos(psi), d * math.sin(psi), lum[y, x]))
    return np.array(S)


class Matcap:
    def __init__(self, S, sigma=0.10):
        self.S = S
        self.sig = sigma

    def __call__(self, n2):
        d2 = (self.S[:, 0] - n2[0]) ** 2 + (self.S[:, 1] - n2[1]) ** 2
        w = np.exp(-d2 / (2 * self.sig ** 2))
        return float((w * self.S[:, 2]).sum() / w.sum())


# =========================================================================== model
def rot(axis3, deg):
    k = np.asarray(axis3, float)
    k = k / np.linalg.norm(k)
    t = math.radians(deg)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def facet_normal(m2, G, blade, roll=0.0, pitch=0.0):
    """m2: outward unit edge normal (image plane).  The facet rises toward the ridge (away from its edge), so its
    normal leans toward the edge: n ~ (G m2, 1)."""
    n = np.array([G * m2[0], G * m2[1], 1.0])
    n /= np.linalg.norm(n)
    a3 = np.r_[blade.a, 0.0]
    c3 = np.r_[blade.c, 0.0]
    # roll +: normals tilt toward image-up.  Rotation about the axis a3 by +roll moves z toward ... (sign fixed below)
    Rr = rot(a3, roll * ROLL_SIGN)
    Rp = rot(c3, pitch)
    return Rp @ Rr @ n


ROLL_SIGN = 1.0


def _fix_roll_sign():
    """Make + roll tilt the camera-facing normal toward image-up (-y) for any axis direction."""
    global ROLL_SIGN
    b = Blade((0, 0), (math.cos(-0.4), math.sin(-0.4)), None, None, None, 0, 0, 0)
    n = facet_normal(np.array([0.0, 0.0]), 0.0, b, roll=10.0)
    ROLL_SIGN = 1.0 if n[1] < 0 else -1.0


_fix_roll_sign()


def facet_L(lum, blade, s, which, t0=0.3, t1=0.7, ds=2.0, alpha=None):
    ur = blade.ridge(s)
    ue = blade.top(s) if which == "top" else blade.bot(s)
    vals = []
    for dss in np.arange(-ds, ds + 1e-9, 0.5):
        for f in np.linspace(t0, t1, 9):
            p = blade.P(s + dss, ur + f * (ue - ur))
            vals.append(bilin(lum, p[0], p[1]))
            if alpha is not None and bilin(alpha, p[0], p[1]) < 0.99:
                vals.pop()
    return float(np.median(vals)) if vals else float("nan"), len(vals)


def ridge_offset(lum, blade, s, alpha=None, ds=1.0):
    """Measured q = (ridge - midline) / half-width at station s: edges from the geometry (alpha 0.5 crossings for a
    render when ``alpha`` is given), ridge = the steepest luminance step between them (sub-pixel)."""
    def prof(img, u):
        return np.mean([bilin(img, *blade.P(s + d, u)) for d in np.arange(-ds, ds + 1e-9, 0.5)], axis=0)
    ut, ub = blade.top(s), blade.bot(s)
    if alpha is not None:
        us = np.arange(ub - 6, ut + 6, 0.1)
        al = np.array([prof(alpha, u) for u in us])
        inside = np.where(al >= 0.5)[0]
        ub_m, ut_m = us[inside[0]], us[inside[-1]]
    else:
        ub_m, ut_m = ub, ut
    hw = 0.5 * (ut_m - ub_m)
    mid = 0.5 * (ut_m + ub_m)
    us = np.arange(mid - 0.6 * hw, mid + 0.6 * hw, 0.25)
    L = np.array([prof(lum, u) for u in us])
    g = np.gradient(L)                          # bright (top side, +u) - dark: dL/du > 0 across the ridge
    k = int(np.argmax(g))
    if 0 < k < len(g) - 1:
        den = g[k - 1] - 2 * g[k] + g[k + 1]
        off = 0.5 * (g[k - 1] - g[k + 1]) / den if den != 0 else 0.0
    else:
        off = 0.0
    ur = us[k] + off * 0.25
    return float((ur - mid) / hw), float(hw), float(ur), float(mid)


# =========================================================================== estimators
R_GRID = np.round(np.arange(0.01, 0.801, 0.005), 3)


def station_models(blade, s):
    mt, ct = blade.edge_normal("top", s)
    mb, cb = blade.edge_normal("bot", s)
    return mt, ct, mb, cb


def est_ratio(mc, blade, s, Lt, Lb, q, pitch=0.0, roll_override=None):
    """Albedo-free: roll = atan(q / r); pick r where M(top)/M(bot) = Lt/Lb (log space)."""
    mt, ct, mb, cb = station_models(blade, s)
    obs = math.log(Lt / Lb)
    best, curve = None, []
    for r in R_GRID:
        roll = roll_override if roll_override is not None else math.degrees(math.atan2(q, r))
        nt = facet_normal(mt, r / ct, blade, roll, pitch)
        nb = facet_normal(mb, r / cb, blade, roll, pitch)
        pred = math.log(mc(nt[:2]) / mc(nb[:2]))
        curve.append((float(r), pred))
        e = abs(pred - obs)
        if best is None or e < best[1]:
            best = (float(r), e, roll)
    # monotonic bracket: all r whose predicted log-ratio is within the observation +- 0.10 (10 %)
    ok = [r for r, p in curve if abs(p - obs) <= 0.10]
    return {"r": best[0], "roll": best[2], "resid_log": best[1], "r_band10": [min(ok), max(ok)] if ok else None,
            "curve": curve}


def est_gain1(mc, blade, s, Lt, Lb, pitch=0.0, rolls=np.arange(-12, 12.01, 0.5)):
    mt, ct, mb, cb = station_models(blade, s)
    best = None
    for r in R_GRID:
        for roll in rolls:
            nt = facet_normal(mt, r / ct, blade, roll, pitch)
            nb = facet_normal(mb, r / cb, blade, roll, pitch)
            e = (math.log(mc(nt[:2]) / Lt)) ** 2 + (math.log(mc(nb[:2]) / Lb)) ** 2
            if best is None or e < best[1]:
                best = (float(r), e, float(roll))
    return {"r": best[0], "roll": best[2], "rms_log": math.sqrt(best[1] / 2)}


def est_gainfit(mc, blade, s, Lt, Lb, q, pitch=0.0):
    """Roll from q, gain free: identical to RATIO for two facets (the gain drops out); reported with its gain."""
    res = est_ratio(mc, blade, s, Lt, Lb, q, pitch)
    mt, ct, mb, cb = station_models(blade, s)
    r, roll = res["r"], res["roll"]
    nt = facet_normal(mt, r / ct, blade, roll, pitch)
    nb = facet_normal(mb, r / cb, blade, roll, pitch)
    g = math.exp(0.5 * (math.log(Lt / mc(nt[:2])) + math.log(Lb / mc(nb[:2]))))
    return {"r": r, "roll": roll, "gain": g}


def run(lum, blade, mc, stations_s, q_by_s, alpha=None, pitch=0.0):
    rows = []
    for s in stations_s:
        Lt, nt = facet_L(lum, blade, s, "top", alpha=alpha)
        Lb, nb = facet_L(lum, blade, s, "bot", alpha=alpha)
        q = q_by_s(s)
        er = est_ratio(mc, blade, s, Lt, Lb, q, pitch)
        eg = est_gain1(mc, blade, s, Lt, Lb, pitch)
        ef = est_gainfit(mc, blade, s, Lt, Lb, q, pitch)
        rows.append({"s_px": float(s), "L_top_lin": Lt, "L_bot_lin": Lb, "L_top_srgb": float(lin_to_srgb8(Lt)),
                     "L_bot_srgb": float(lin_to_srgb8(Lb)), "q": q,
                     "ratio": {k: v for k, v in er.items() if k != "curve"}, "gain1": eg, "gainfit_gain": ef["gain"]})
    return rows


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
        return float(max(self._M(self.p, np.array([n2[0]]), np.array([n2[1]]), vx, vy)[0], 1e-5))

    def describe(self):
        return {k: float(v) for k, v in zip(self.NAMES, self.p)} | {"fit_rms_log": self.rms, "n_px": len(self.obs)}
