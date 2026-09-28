#!/usr/bin/env python
"""props_lib.paperbomb_finefit - sub-pixel knock-outs fitted to the reference.

Some of the user's marks are paper lines INSIDE solid red that are narrower than one
pixel of the reference (3.9 px/mm): the two four-point sparkles in the big seal's panel
and the slots between the bars of the 目 inside 道 on the small seal.  A half-level
contour cannot see a line narrower than half a pixel: it either misses it (the red then
reads as a lighter patch, which the tone sampling turned into a pale scribble) or keeps a
blob where the line crosses itself.

These are fitted by ANALYSIS BY SYNTHESIS instead: a small parametric shape (a star of
tapered rays, or a stack of rounded slots) is erased from the traced red, rendered
through the source's own point spread (pixel box + Gaussian 0.4 px) at the full-strength
density, and its parameters are moved (Nelder-Mead, deterministic) until the rendering
reproduces the observed red in a window round the mark.  The start point is read from
the reference too: the paper deficit (1 - red / density) along rays from the mark's
centre, or across the slots' rows.

The fitted shapes are ERASE polygons (card mm): red coverage = traced red x (1 - erase).
They are stored with the traced group (``knockouts_mm``) and the traced holes they
replace are dropped from the group, so the one JSON carries everything.
"""
from __future__ import annotations

import math

import numpy as np

from . import trace as T

FINEFIT_VERSION = "1.2.0"

#: the marks fitted this way, in card mm.  ``centre_mm`` / ``box_mm`` only say WHERE to
#: look; every shape parameter comes from the fit.
KNOCKOUTS = (
    {"name": "seal_spark_TL", "group": "seal_big", "layer": "red", "kind": "star",
     "centre_mm": (9.6, 126.9), "half_mm": 2.4, "rays": 4},
    {"name": "seal_spark_BR", "group": "seal_big", "layer": "red", "kind": "star",
     "centre_mm": (20.8, 146.3), "half_mm": 2.1, "rays": 4},
    {"name": "dou_slots", "group": "small_seal", "layer": "red", "kind": "slots",
     "box_mm": (59.45, 146.62, 61.05, 149.45), "n": 4},
)

#: weight of the half-level hinge in the fit's loss (see ``_Window.loss``)
HALF_LEVEL_WEIGHT = 0.5

#: a traced hole is replaced by the fit when its centroid is in the fit's window and its
#: area is under this (mm^2): the panel's big flame device is never touched
MAX_REPLACED_HOLE_MM2 = 3.0


# ===========================================================================
# Nelder-Mead (deterministic)
# ===========================================================================

def nelder_mead(f, x0, step, iters=3000, tol=1e-10):
    n = len(x0)
    pts = [np.asarray(x0, np.float64)]
    for i in range(n):
        p = pts[0].copy()
        p[i] += step[i]
        pts.append(p)
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = np.argsort(vals, kind="stable")
        pts = [pts[i] for i in order]
        vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) <= tol * (abs(vals[0]) + 1e-12):
            break
        c = np.mean(pts[:-1], 0)
        xr = c + (c - pts[-1]); fr = f(xr)
        if fr < vals[0]:
            xe = c + 2.0 * (c - pts[-1]); fe = f(xe)
            if fe < fr:
                pts[-1], vals[-1] = xe, fe
            else:
                pts[-1], vals[-1] = xr, fr
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c) if fr >= vals[-1] else c + 0.5 * (xr - c)
            fc = f(xc)
            if fc < min(fr, vals[-1]):
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = pts[0] + 0.5 * (pts[i] - pts[0])
                    vals[i] = f(pts[i])
    i = int(np.argmin(vals))
    return pts[i], float(vals[i])


def pattern_search(f, x0, step, min_step, sweeps=400):
    """Hooke-Jeeves-style coordinate pattern search (deterministic, derivative free).
    Every parameter is tried at +-step; an improving move is kept and repeated along the
    same direction while it keeps improving; steps halve when a sweep finds nothing."""
    x = np.asarray(x0, np.float64).copy()
    st = np.asarray(step, np.float64).copy()
    mn = np.asarray(min_step, np.float64)
    fx = f(x)
    for _ in range(sweeps):
        moved = False
        for i in range(len(x)):
            if st[i] < mn[i]:
                continue
            for sgn in (1.0, -1.0):
                y = x.copy(); y[i] += sgn * st[i]
                fy = f(y)
                if fy < fx:
                    x, fx, moved = y, fy, True
                    while True:
                        y = x.copy(); y[i] += sgn * st[i]
                        fy = f(y)
                        if fy < fx:
                            x, fx = y, fy
                        else:
                            break
                    break
        if not moved:
            st *= 0.5
            if np.all(st < mn):
                break
    return x, float(fx)


def adam_fd(f, x0, lr, h, iters=300):
    """Adam on central-difference gradients (deterministic); keeps the best point seen.
    ``lr`` and ``h`` are per-parameter scales."""
    x = np.asarray(x0, np.float64).copy()
    lr = np.asarray(lr, np.float64); h = np.asarray(h, np.float64)
    m = np.zeros_like(x); v = np.zeros_like(x)
    best, fbest = x.copy(), f(x)
    for it in range(1, iters + 1):
        g = np.empty_like(x)
        for i in range(len(x)):
            a = x.copy(); a[i] += h[i]
            b = x.copy(); b[i] -= h[i]
            g[i] = (f(a) - f(b)) / (2 * h[i])
        m = 0.9 * m + 0.1 * g
        v = 0.999 * v + 0.001 * g * g
        mh = m / (1 - 0.9 ** it); vh = v / (1 - 0.999 ** it)
        x = x - lr * mh / (np.sqrt(vh) + 1e-12)
        fx = f(x)
        if fx < fbest:
            best, fbest = x.copy(), fx
    return best, float(fbest)


# ===========================================================================
# Shapes (source px)
# ===========================================================================

RAY_KNOTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def star_polys(p, rays: int = 4) -> list:
    """p = [cx, cy, phi, a0, a1, a2, a3, (theta, length, h0, taper) per ray]: a sparkle.

    The HEART is a kite round the centre: four vertices at distances a0..a3 along phi,
    phi + 90, phi + 180, phi + 270 deg, joined by concave edges (each edge's midpoint is
    pulled a third of the way in).  The POINTS are ``rays`` tapered rays from the same
    centre, each at its own angle and length (a brush sparkle's opposite rays are rarely
    collinear), half width h0 (1 - t)^taper.  One polygon per part; they overlap (union)."""
    c = np.array([p[0], p[1]])
    out = []
    phi = p[2]
    a = [max(0.0, v) for v in p[3:7]]
    if sum(a) > 0.2:
        verts = [c + a[k] * np.array([math.cos(phi + k * math.pi / 2),
                                      math.sin(phi + k * math.pi / 2)]) for k in range(4)]
        pts = []
        for k in range(4):
            v0, v1 = verts[k], verts[(k + 1) % 4]
            mid = 0.5 * (v0 + v1)
            ctrl = mid + (c - mid) * 0.33
            for t in np.linspace(0.0, 1.0, 9)[:-1]:
                pts.append((1 - t) ** 2 * v0 + 2 * (1 - t) * t * ctrl + t * t * v1)
        poly = np.array(pts)
        if abs(T.signed_area(poly)) > 1e-6:
            out.append(poly if T.signed_area(poly) > 0 else poly[::-1])
    s = np.linspace(0.0, 1.0, 33)
    for k in range(rays):
        th, L, h0, tp = p[7 + 4 * k: 11 + 4 * k]
        L = max(0.0, L); h0 = max(0.0, h0); tp = min(8.0, max(0.3, tp))
        if L < 0.05 or h0 < 0.005:
            continue
        half = h0 * (1.0 - s) ** tp
        u = np.array([math.cos(th), math.sin(th)]); n = np.array([-u[1], u[0]])
        left = c + (s * L)[:, None] * u + half[:, None] * n
        right = c + (s * L)[:, None] * u - half[:, None] * n
        poly = np.vstack([(c - h0 * u)[None], left, right[::-1][1:]])
        if T.signed_area(poly) < 0:
            poly = poly[::-1]
        out.append(poly)
    return out


def slot_polys(p, n: int) -> list:
    """p = [x0, x1, (yc, h) * n] -> n rounded slots (stadium ends) sharing one run
    x0..x1: the paper between the bars of a box character runs wall to wall."""
    out = []
    a = np.linspace(-math.pi / 2, math.pi / 2, 9)
    x0, x1 = p[0], p[1]
    for k in range(n):
        yc, h = p[2 + 2 * k], max(0.0, p[3 + 2 * k])
        if h < 0.01 or x1 - x0 < 0.05:
            continue
        r = 0.5 * h
        xa = min(x0 + r, 0.5 * (x0 + x1)); xb = max(x1 - r, 0.5 * (x0 + x1))
        right = np.stack([xb + r * np.cos(a), yc + r * np.sin(a)], 1)
        left = np.stack([xa - r * np.cos(a), yc - r * np.sin(a)], 1)
        poly = np.vstack([right, left])
        if T.signed_area(poly) < 0:
            poly = poly[::-1]
        out.append(poly)
    return out


# ===========================================================================
# The fit
# ===========================================================================

class _Window:
    def __init__(self, base_polys_px, obs, dens, x0, y0, x1, y1, pad=3):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.pad = pad
        H, W = obs.shape
        self.gx0, self.gy0 = max(0, x0 - pad), max(0, y0 - pad)
        self.gx1, self.gy1 = min(W, x1 + pad), min(H, y1 + pad)
        self.h, self.w = self.gy1 - self.gy0, self.gx1 - self.gx0
        off = np.array([self.gx0, self.gy0], np.float64)
        self.off = off
        self.base = T.fill_polys([q - off for q in base_polys_px], self.h, self.w,
                                 ss=16).astype(np.float64)
        self.obs = obs[self.gy0:self.gy1, self.gx0:self.gx1]
        # FULL STRENGTH IN THE WINDOW.  The tracer's density field is a local mean of
        # the ink's eroded cores; among bars one or two pixels wide (the 目 of 道) there
        # are almost no cores and it falls towards its 0.6 floor, which made the fit
        # thin the slots to compensate.  In a knock-out window the ink is one pigment
        # at one load: its full strength is the median of the window's solid ink.
        solid = (self.base > 0.99) & (self.obs > 0.85)
        dc = float(np.median(self.obs[solid])) if solid.sum() >= 4 else 0.97
        self.dens = np.full_like(self.obs, min(1.0, max(0.9, dc)))
        iy0, ix0 = y0 - self.gy0, x0 - self.gx0
        self.inner = np.zeros((self.h, self.w), bool)
        self.inner[iy0:iy0 + (y1 - y0), ix0:ix0 + (x1 - x0)] = True

    def render(self, erase_px):
        e = T.fill_polys([q - self.off for q in erase_px], self.h, self.w, ss=16) \
            if erase_px else np.zeros((self.h, self.w))
        cov = self.base * (1.0 - e)
        return T.gauss_blur(cov, T.SOURCE_PSF_SIGMA_PX) * self.dens

    def loss(self, erase_px):
        """Squared error of the re-rendered red, plus a hinge on every pixel that lands
        on the wrong side of HALF strength (a knock-out's slots and rays sit near 0.5 at
        the source's grid, and the element scores are half-level overlaps)."""
        pred = self.render(erase_px)
        d = pred - self.obs
        o = self.obs / self.dens
        p = pred / self.dens
        hinge = np.where(o > 0.5, np.clip(0.5 - p, 0, None), np.clip(p - 0.5, 0, None))
        hinge = np.where(np.abs(o - 0.5) > 0.03, hinge, 0.0)
        return float((d[self.inner] ** 2).sum() + HALF_LEVEL_WEIGHT * hinge[self.inner].sum())


def _deficit(win):
    return np.clip(1.0 - win.obs / np.maximum(win.dens, 0.6), 0.0, 1.0) * (win.base > 0.99)


def _star_centre_and_angles(win, cx, cy, n_cand=6):
    d = _deficit(win)
    yy, xx = np.mgrid[0:win.h, 0:win.w] + 0.5
    xx = xx + win.gx0; yy = yy + win.gy0
    near = (np.hypot(xx - cx, yy - cy) < 2.5) & (d > 0.5)
    if near.any():
        wgt = d * near
        cx = float((xx * wgt).sum() / wgt.sum()); cy = float((yy * wgt).sum() / wgt.sum())
    angs = np.radians(np.arange(0, 360, 3))
    r = np.arange(1.5, 9.0, 0.25)

    def arm(a):
        pts = np.stack([cx + r * math.cos(a) - win.gx0, cy + r * math.sin(a) - win.gy0], 1)
        return T._bilinear(d, pts - 0.5)
    prof = np.array([float(arm(a).sum() * 0.25) for a in angs])
    prof = np.convolve(np.concatenate([prof[-2:], prof, prof[:2]]), np.ones(5) / 5, "same")[2:-2]
    chosen = []
    for i in np.argsort(-prof, kind="stable"):
        if all(min(abs(i - j), len(angs) - abs(i - j)) * 3 >= 20 for j in chosen):
            chosen.append(int(i))
        if len(chosen) == n_cand:
            break
    return cx, cy, [float(angs[i]) for i in chosen]


def _ray_profile(win, cx, cy, th):
    """Integrated paper deficit across a ray, every 0.5 px along it: the ray's WIDTH
    (source px), unbiased by the blur - the same measurement as a rule stroke's."""
    d = _deficit(win)
    u = np.array([math.cos(th), math.sin(th)]); n = np.array([-u[1], u[0]])
    s = np.arange(0.5, 10.01, 0.5)
    q = np.arange(-1.5, 1.51, 0.1)
    P = (np.array([cx, cy])[None, None] + s[:, None, None] * u + q[None, :, None] * n
         - np.array([win.gx0 + 0.5, win.gy0 + 0.5]))
    v = T._bilinear(d, P.reshape(-1, 2)).reshape(len(s), len(q))
    return s, v.sum(1) * 0.1


def _star_init(win, cx, cy, thetas):
    """The heart from the second moments of the solid paper round the centre; the
    points' lengths from each ray's integrated-deficit profile."""
    d = _deficit(win)
    yy, xx = np.mgrid[0:win.h, 0:win.w] + 0.5
    xx = xx + win.gx0; yy = yy + win.gy0
    core = (d > 0.6) & (np.hypot(xx - cx, yy - cy) < 3.0)
    phi, a = 0.0, [0.8] * 4
    if core.sum() >= 2:
        dx = xx[core] - cx; dy = yy[core] - cy
        cxx, cyy, cxy = (dx * dx).mean(), (dy * dy).mean(), (dx * dy).mean()
        phi = 0.5 * math.atan2(2 * cxy, cxx - cyy)
        ex = math.sqrt(max(1e-6, 0.5 * (cxx + cyy) + math.hypot(0.5 * (cxx - cyy), cxy)))
        ey = math.sqrt(max(1e-6, 0.5 * (cxx + cyy) - math.hypot(0.5 * (cxx - cyy), cxy)))
        a = [2.0 * ex, 2.0 * ey, 2.0 * ex, 2.0 * ey]
    p = [cx, cy, phi] + a
    for th in thetas:
        s, wid = _ray_profile(win, cx, cy, th)
        on = np.flatnonzero(wid > 0.10)
        L = min(10.0, float(s[on.max()]) + 0.5 if len(on) else 1.0)
        p += [th, L, 0.35, 1.2]
    return np.array(p)


def _slots_init(win, box_px, n):
    """Slot rows from the column-averaged deficit across the box's inner columns."""
    x0, y0, x1, y1 = box_px
    d = np.clip(1.0 - win.obs / np.maximum(win.dens, 0.6), 0.0, 1.0)
    c0 = int(math.floor(x0)) - win.gx0; c1 = int(math.ceil(x1)) - win.gx0
    r0 = int(math.floor(y0)) - win.gy0; r1 = int(math.ceil(y1)) - win.gy0
    # inner columns: those whose deficit over the box's rows is at least half the best
    colsum = d[r0:r1, c0:c1].sum(0)
    ci = np.flatnonzero(colsum >= 0.5 * colsum.max()) + c0
    prof = d[r0:r1, ci.min():ci.max() + 1].mean(1)
    cand = [i for i in range(len(prof))
            if prof[i] > 0.15 and (i == 0 or prof[i] >= prof[i - 1])
            and (i == len(prof) - 1 or prof[i] > prof[i + 1])]
    cand = sorted(sorted(cand, key=lambda i: -prof[i])[:n])
    p = [win.gx0 + float(ci.min()) + 0.2, win.gx0 + float(ci.max()) + 0.8]
    for i in cand:
        lo, hi = max(0, i - 1), min(len(prof), i + 2)
        w = prof[lo:hi].copy()
        # a neighbouring row that is itself a slot's peak is not this slot's
        yc = win.gy0 + r0 + lo + 0.5 + float((w * np.arange(len(w))).sum() / max(w.sum(), 1e-9))
        h = float(min(1.6, max(0.3, w.sum())))
        p += [yc, h]
    return np.array(p), len(cand)


def fit_knockout(spec, base_polys_px, obs, dens, fit) -> dict:
    """Fit one knock-out.  Returns the erase polygons (source px), params and losses."""
    if spec["kind"] == "star":
        cx, cy = fit.mm_to_px(*spec["centre_mm"])
        r = spec["half_mm"] * fit.ppmm
        x0, y0 = int(math.floor(cx - r)), int(math.floor(cy - r))
        x1, y1 = int(math.ceil(cx + r)), int(math.ceil(cy + r))
        win = _Window(base_polys_px, obs, dens, x0, y0, x1, y1)
        rays = spec["rays"]
        cx, cy, cands = _star_centre_and_angles(win, float(cx), float(cy))
        import itertools

        def _sep(a, b):
            d = abs(a - b) % (2 * math.pi)
            return min(d, 2 * math.pi - d)
        combos = [sorted(c) for c in itertools.combinations(cands, rays)
                  if all(_sep(a, b) >= math.radians(30) for a, b in itertools.combinations(c, 2))]
        inits = [_star_init(win, cx, cy, c) for c in combos]
        # and each again with a small heart and fuller points: the moment-sized heart
        # can trap the search with the points too short to reach the lines' far ends
        for q in list(inits):
            q2 = q.copy()
            q2[3:7] = 0.6
            for k in range(rays):
                q2[9 + 4 * k] = 0.7; q2[10 + 4 * k] = 1.0
            inits.append(q2)

        def clamp(p):
            """A point never runs out of the red it sits in: its length stops half a
            pixel past the first paper (traced coverage < 0.5) along it, so a sparkle
            can never cut the frame beyond the panel's white gap."""
            q = np.array(p, np.float64)
            for k in range(rays):
                th = q[7 + 4 * k]
                t = np.arange(0.5, 2.6 * r, 0.25)
                pts = np.stack([q[0] + t * math.cos(th) - win.gx0 - 0.5,
                                q[1] + t * math.sin(th) - win.gy0 - 0.5], 1)
                b = T._bilinear(win.base, pts)
                out = np.flatnonzero(b < 0.5)
                if len(out):
                    q[8 + 4 * k] = min(q[8 + 4 * k], float(t[out[0]]) + 0.5)
            return q

        def shapes(p):
            return star_polys(clamp(p), rays)

        def prior(p):
            pen = 10 * max(0.0, math.hypot(p[0] - cx, p[1] - cy) - 1.5)
            pen += 10 * sum(max(0.0, -v) + max(0.0, v - 4.0) for v in p[3:7])
            for k in range(rays):
                th, L, h0, tp = p[7 + 4 * k: 11 + 4 * k]
                pen += 10 * (max(0.0, -L) + max(0.0, L - 2.6 * r))
                pen += 10 * (max(0.0, -h0) + max(0.0, h0 - 1.5))
                pen += 10 * (max(0.0, 0.3 - tp) + max(0.0, tp - 8.0))
            return pen
        step = np.array([0.25, 0.25, 0.1, 0.3, 0.3, 0.3, 0.3] + [0.06, 0.8, 0.1, 0.3] * rays)
        mstep = np.array([0.01, 0.01, 0.004, 0.01, 0.01, 0.01, 0.01] + [0.003, 0.03, 0.004, 0.01] * rays)
        p0 = inits[0]
    else:
        bx0, by0 = fit.mm_to_px(spec["box_mm"][0], spec["box_mm"][1])
        bx1, by1 = fit.mm_to_px(spec["box_mm"][2], spec["box_mm"][3])
        x0, y0 = int(math.floor(bx0)), int(math.floor(by0))
        x1, y1 = int(math.ceil(bx1)), int(math.ceil(by1))
        win = _Window(base_polys_px, obs, dens, x0, y0, x1, y1)
        p0, n = _slots_init(win, (bx0, by0, bx1, by1), spec["n"])

        def shapes(p):
            return slot_polys(p, n)

        def prior(p):
            pen = 0.0
            pen = 10 * max(0.0, p[0] - p[1])
            for k in range(n):
                yc, h = p[2 + 2 * k], p[3 + 2 * k]
                pen += max(0.0, -h) * 10 + max(0.0, h - 2.0) * 10
                pen += 10 * max(0.0, abs(yc - p0[2 + 2 * k]) - 0.8)
            return pen
        step = np.array([0.3, 0.3] + [0.2, 0.2] * n)
        mstep = np.array([0.01, 0.01] + [0.005, 0.005] * n)
    loss0 = win.loss([])
    f = lambda p: win.loss(shapes(p)) + prior(p)
    cand_inits = inits if spec["kind"] == "star" else [p0]
    best, lbest = None, float("inf")
    for q0 in cand_inits:
        b, lb = pattern_search(f, q0, step, mstep)
        if lb < lbest:
            best, lbest, p0 = b, lb, q0
    linit = f(p0)
    # one polish: a fresh pattern at a third of the steps (the first run can end on a
    # ridge where every single-parameter move is uphill)
    best, lbest = pattern_search(f, best, step / 3.0, mstep)
    polys = shapes(best)
    if spec["kind"] == "star":
        best = clamp(best)
    return {"name": spec["name"], "group": spec["group"], "layer": spec["layer"],
            "kind": spec["kind"], "window_px": [x0, y0, x1, y1],
            "params_px": [round(float(v), 5) for v in best],
            "loss_traced_holes_removed": round(loss0, 5), "loss_init": round(linit, 5),
            "loss_fit": round(lbest, 5), "polys_px": polys,
            "density": round(float(win.dens.flat[0]), 5)}


def window_mm(spec) -> tuple:
    if spec["kind"] == "star":
        cx, cy = spec["centre_mm"]; r = spec["half_mm"]
        return (cx - r, cy - r, cx + r, cy + r)
    return tuple(spec["box_mm"])
