#!/usr/bin/env python
"""props_lib.smokebomb_strips - the smoke bomb's tape strips as functions on the sphere.

numpy only (no bpy): the layout tool, the mesh builder, the texture generator and the
measurement code all evaluate the SAME functions, so a strip is described once.

FRAMES
------
The reference (References/SmokeBomb/smokebomb.png) is an orthographic product shot, and
REFERENCE_SPEC.md gives every position in its CAMERA frame:

    camera   Xc right, Yc up, Zc toward the camera; the image centre is (0, 0, 1)
    Blender  the reference view is Blender's Front view (camera on -Y looking +Y,
             image-right = +X, image-up = +Z), so  X = Xc,  Y = -Zc,  Z = Yc

Everything in this module works on UNIT VECTORS in the camera frame; ``cam_to_blender``
is applied once, when a vertex is written.

A STRIP
-------
A cloth tape on a ball lies along a geodesic (a great circle) as long as nothing bends it.
The reference is a still image, not a physical winding, and several of its edges are not
circles (REFERENCE_SPEC 4.2), so a strip here is a *deviated great circle*:

    pole n, zero meridian e1, e2 = n x e1        (the strip's own great circle)
    lam = atan2(p.e2, p.e1)                     (position ALONG the strip)
    phi = asin(p.n)                             (angular offset ACROSS it)

and the strip is the set  phi_lo(lam) <= phi <= phi_hi(lam),  two periodic splines through
knots.  Where the knots are constant the strip IS a great-circle band of constant width;
where the reference bends an edge the knots bend it.  Every strip that is visible on the
front closes into a loop on the back (REFERENCE_SPEC section 9: "continue every visible
strip along its own path"), unless it is declared open with both ends tucked under other
strips.

Evaluation of N points against a strip is O(N): two ``np.interp`` lookups into tables
tabulated at 0.125 deg, no nearest-point search.

ORDER (over / under)
--------------------
The reference's over/under is WOVEN - R_in over A over C over R_in's own lower end
(REFERENCE_SPEC 4.4) - so no single layer index can hold it.  Each strip carries a RANK
that is piecewise constant ALONG it (``rank_knots``): a strip dives under another by
dropping its rank between two crossings.  At a point, the visible strip is the covering
strip with the highest rank there.

HEIGHT
------
A strip's sheet stands one tape thickness above everything it lies on:

    h_S(p) = R0(p) + t * g(1 + sum_U c_U(p))       over strips U under S at p

``c_U`` is U's coverage, ramped over ``DRAPE_MM`` across U's own edge (a tape bridging a
buried edge drapes, it does not step), and ``g`` softens deep stacks (only the top layers
of a real ball carry height - SMOKEBOMB_STUDY 4).  S's OWN edge is not ramped: that is the
step the viewer sees, and it reaches the silhouette (the kunai lesson).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# --------------------------------------------------------------------------- reference frame

#: REFERENCE_SPEC section 1 / 2: the fitted silhouette circle of the reference, in px.
REF_SIZE_PX = 1254
REF_CENTRE_PX = (627.38, 628.92)
REF_RADIUS_PX = 464.11
#: frame width over ball diameter (REFERENCE_SPEC 2, "Ortho scale")
ORTHO_D_PER_FRAME = 1254.0 / 928.2

DEG = math.pi / 180.0


def latlon(lat_deg, lon_deg) -> np.ndarray:
    """Camera-frame unit vector(s) from REFERENCE_SPEC lat / lon (degrees)."""
    lat = np.asarray(lat_deg, np.float64) * DEG
    lon = np.asarray(lon_deg, np.float64) * DEG
    return np.stack([np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)], axis=-1)


def img_to_cam(x, y, back: bool = False) -> np.ndarray:
    """Orthographic back-projection of reference pixels onto the unit sphere (front half)."""
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    xc = (x - REF_CENTRE_PX[0]) / REF_RADIUS_PX
    yc = -(y - REF_CENTRE_PX[1]) / REF_RADIUS_PX
    r2 = xc * xc + yc * yc
    z = np.sqrt(np.clip(1.0 - r2, 0.0, None))
    if back:
        z = -z
    out = np.stack([xc, yc, z], axis=-1)
    n = np.linalg.norm(out, axis=-1, keepdims=True)
    return out / np.maximum(n, 1e-12)


def cam_to_img(p) -> np.ndarray:
    p = np.asarray(p, np.float64)
    return np.stack([REF_CENTRE_PX[0] + REF_RADIUS_PX * p[..., 0],
                     REF_CENTRE_PX[1] - REF_RADIUS_PX * p[..., 1]], axis=-1)


def image_angle_deg(p) -> np.ndarray:
    """REFERENCE_SPEC image angle: CCW from 3 o'clock, y up."""
    p = np.asarray(p, np.float64)
    return np.degrees(np.arctan2(p[..., 1], p[..., 0])) % 360.0


def cam_to_blender(p) -> np.ndarray:
    p = np.asarray(p, np.float64)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], axis=-1)


def blender_to_cam(p) -> np.ndarray:
    p = np.asarray(p, np.float64)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], axis=-1)


def normalize(v) -> np.ndarray:
    v = np.asarray(v, np.float64)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-15)


def fit_pole(points: np.ndarray) -> np.ndarray:
    """The great circle closest to ``points`` (unit vectors): its pole, sign arbitrary."""
    p = normalize(points)
    w, v = np.linalg.eigh(p.T @ p)
    return v[:, 0]


# --------------------------------------------------------------------------- splines

def _pchip_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Fritsch-Carlson monotone slopes (no overshoot between knots)."""
    h = np.diff(x)
    d = np.diff(y) / h
    m = np.zeros_like(y)
    for i in range(1, len(y) - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0] = d[0]
    m[-1] = d[-1]
    return m


def periodic_spline(knots: Sequence[Tuple[float, float]], samples: np.ndarray,
                    period: float = 360.0, smooth: bool = True) -> np.ndarray:
    """A periodic interpolant through ``(x, y)`` knots, evaluated at ``samples``.

    ``smooth`` uses monotone cubic Hermite segments (no overshoot, C1); otherwise linear.
    With one knot the function is constant.
    """
    k = sorted((float(a) % period, float(b)) for a, b in knots)
    if len(k) == 1:
        return np.full_like(np.asarray(samples, np.float64), k[0][1])
    x = np.array([a for a, _ in k])
    y = np.array([b for _, b in k])
    # unroll one period either side so every sample has two neighbours
    xx = np.concatenate([x - period, x, x + period, x + 2 * period])
    yy = np.concatenate([y, y, y, y])
    s = np.asarray(samples, np.float64) % period
    if not smooth:
        return np.interp(s, xx, yy)
    m = _pchip_slopes(xx, yy)
    i = np.clip(np.searchsorted(xx, s, side="right") - 1, 0, len(xx) - 2)
    h = xx[i + 1] - xx[i]
    t = (s - xx[i]) / h
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * yy[i] + (t3 - 2 * t2 + t) * h * m[i]
            + (-2 * t3 + 3 * t2) * yy[i + 1] + (t3 - t2) * h * m[i + 1])


def step_function(knots: Sequence[Tuple[float, float]], samples: np.ndarray,
                  period: float = 360.0) -> np.ndarray:
    """Piecewise constant, periodic: value k_i from x_i up to the next knot."""
    k = sorted((float(a) % period, float(b)) for a, b in knots)
    x = np.array([a for a, _ in k])
    y = np.array([b for _, b in k])
    s = np.asarray(samples, np.float64) % period
    i = np.searchsorted(x, s, side="right") - 1          # -1 -> wraps to the last knot
    return y[i]


# --------------------------------------------------------------------------- the strip

TABLE_STEP_DEG = 0.125
#: a strip is never narrower than 0.7 mm on a 35 mm chart.  Round 4: was 1.2 mm; the
#: reference's edge-on ridges are ~9 px = 0.68 mm (REFERENCE_SPEC 4.2 W's twisted section;
#: the whorl's knuckled ridge), and the 1.2 mm floor widened both into flat bands
MIN_HALF_WIDTH_DEG = math.degrees(0.35 / 35.0)


@dataclass
class Strip:
    """One tape strip; see the module docstring.  Angles in degrees."""
    name: str
    pole: np.ndarray                         # camera frame, unit
    zero: np.ndarray                         # a direction on (or near) the great circle: lam = 0
    hi: List[Tuple[float, float]]            # knots (lam, phi) of the +phi edge
    lo: List[Tuple[float, float]]            # knots (lam, phi) of the -phi edge
    rank: List[Tuple[float, float]]          # knots (lam, rank), piecewise constant
    family: str = ""
    closed: bool = True
    lam_range: Tuple[float, float] = (-180.0, 180.0)   # open strips only
    #: extra height in tape layers (W's edge-on twist stands proud of the tape it lies on)
    lift: List[Tuple[float, float]] = field(default_factory=lambda: [(0.0, 0.0)])
    #: profile across the strip: "flat", or "roll" for an edge-on / rolled section
    note: str = ""

    def __post_init__(self):
        n = normalize(self.pole)
        z = np.asarray(self.zero, np.float64)
        e1 = normalize(z - np.dot(z, n) * n)
        e2 = np.cross(n, e1)
        self.n, self.e1, self.e2 = n, e1, e2
        lam = np.arange(-180.0, 180.0 + TABLE_STEP_DEG * 0.5, TABLE_STEP_DEG)
        self._lam = lam
        hi_t = periodic_spline(self.hi, lam)
        lo_t = periodic_spline(self.lo, lam)
        # where two independently splined edges would pinch or cross (between the front
        # knots and the far side), hold a minimum width about their mid-line
        mid = 0.5 * (hi_t + lo_t)
        half = np.maximum(0.5 * (hi_t - lo_t), MIN_HALF_WIDTH_DEG)
        self.pinched = int(np.count_nonzero(0.5 * (hi_t - lo_t) < MIN_HALF_WIDTH_DEG))
        self._hi = mid + half
        self._lo = mid - half
        self._c = 0.5 * (self._hi + self._lo)
        self._lift = periodic_spline(self.lift, lam)
        # slopes (deg of phi per deg of lam) for the perpendicular-distance correction
        self._dhi = np.gradient(self._hi, lam)
        self._dlo = np.gradient(self._lo, lam)
        self._dc = np.gradient(self._c, lam)
        # arc length along the centreline, radians of a unit sphere
        cphi = np.cos(self._c * DEG)
        ds = np.sqrt((cphi) ** 2 + (self._dc) ** 2) * TABLE_STEP_DEG * DEG
        s = np.concatenate([[0.0], np.cumsum(0.5 * (ds[1:] + ds[:-1]))])
        s -= np.interp(0.0, lam, s)                  # s = 0 at lam = 0
        self._s = s
        self.length_rad = float(s[-1] - s[0])

    # ---------------------------------------------------------------- tables
    def at(self, lam_deg):
        """(phi_lo, phi_hi, phi_c) in degrees at ``lam_deg``."""
        l = ((np.asarray(lam_deg, np.float64) + 180.0) % 360.0) - 180.0
        return (np.interp(l, self._lam, self._lo), np.interp(l, self._lam, self._hi),
                np.interp(l, self._lam, self._c))

    def width_deg(self, lam_deg):
        lo, hi, _ = self.at(lam_deg)
        return hi - lo

    def in_range(self, lam_deg) -> np.ndarray:
        l = np.asarray(lam_deg, np.float64)
        if self.closed:
            return np.ones(l.shape, bool)
        a, b = self.lam_range
        if a <= b:
            return (l >= a) & (l <= b)
        return (l >= a) | (l <= b)

    # ---------------------------------------------------------------- evaluation
    def coords(self, P: np.ndarray):
        """lam, phi (degrees) of unit vectors ``P`` (..., 3) in this strip's frame."""
        P = np.asarray(P, np.float64)
        lam = np.degrees(np.arctan2(P @ self.e2, P @ self.e1))
        phi = np.degrees(np.arcsin(np.clip(P @ self.n, -1.0, 1.0)))
        return lam, phi

    def evaluate(self, P: np.ndarray, radius_mm: float) -> Dict[str, np.ndarray]:
        """Everything about ``P`` relative to this strip.

        d    signed distance to the nearer edge, mm on a sphere of ``radius_mm``
             (positive inside the strip)
        d_hi, d_lo  the same to each edge separately
        s    mm along the centreline (0 at lam 0)
        w    mm across, from the centreline, positive toward the pole
        rank the strip's rank at this position along it
        """
        lam, phi = self.coords(P)
        l = ((lam + 180.0) % 360.0) - 180.0
        lo = np.interp(l, self._lam, self._lo)
        hi = np.interp(l, self._lam, self._hi)
        c = np.interp(l, self._lam, self._c)
        cphi = np.cos(phi * DEG)
        # perpendicular distance: the edge's local slope tilts the across direction
        shi = np.interp(l, self._lam, self._dhi)
        slo = np.interp(l, self._lam, self._dlo)
        sc = np.interp(l, self._lam, self._dc)
        k_hi = np.cos(np.arctan2(shi, np.maximum(cphi, 1e-6)))
        k_lo = np.cos(np.arctan2(slo, np.maximum(cphi, 1e-6)))
        k_c = np.cos(np.arctan2(sc, np.maximum(np.cos(c * DEG), 1e-6)))   # on the centre line, as chart_to_cam: an exact round trip
        r = radius_mm * DEG
        d_hi = (hi - phi) * k_hi * r
        d_lo = (phi - lo) * k_lo * r
        d = np.minimum(d_hi, d_lo)
        if not self.closed:
            inr = self.in_range(l)
            d = np.where(inr, d, -1e3)
        s = np.interp(l, self._lam, self._s) * radius_mm
        w = (phi - c) * k_c * r
        rank = step_function(self.rank, l)
        lift = np.interp(l, self._lam, self._lift)
        return {"lam": l, "phi": phi, "d": d, "d_hi": d_hi, "d_lo": d_lo, "s": s, "w": w,
                "rank": rank, "lift": lift, "half_width": 0.5 * (hi - lo) * k_c * r}

    # ---------------------------------------------------------------- chart -> sphere
    def lam_of_s(self, s_mm, radius_mm: float) -> np.ndarray:
        s = np.asarray(s_mm, np.float64) / radius_mm
        # every strip's tables cover the whole circle, so s is periodic with the loop's
        # length (an open strip's range may wrap through lam = +-180)
        s = self._s[0] + np.mod(s - self._s[0], self.length_rad)
        return np.interp(s, self._s, self._lam)

    def chart_to_cam(self, s_mm, w_mm, radius_mm: float) -> np.ndarray:
        """Unit vectors at (s along, w across) mm of this strip's chart."""
        lam = self.lam_of_s(s_mm, radius_mm)
        c = np.interp(lam, self._lam, self._c)
        sc = np.interp(lam, self._lam, self._dc)
        cphi = np.cos(c * DEG)
        k_c = np.cos(np.arctan2(sc, np.maximum(cphi, 1e-6)))
        phi = c + np.asarray(w_mm, np.float64) / (radius_mm * DEG) / np.maximum(k_c, 1e-6)
        lr, pr = lam * DEG, phi * DEG
        cp = np.cos(pr)[..., None]
        return (cp * (np.cos(lr)[..., None] * self.e1 + np.sin(lr)[..., None] * self.e2)
                + np.sin(pr)[..., None] * self.n)

    def centreline_cam(self, lam_deg) -> np.ndarray:
        lam = np.asarray(lam_deg, np.float64)
        c = np.interp(((lam + 180) % 360) - 180, self._lam, self._c)
        lr, pr = lam * DEG, c * DEG
        cp = np.cos(pr)[..., None]
        return (cp * (np.cos(lr)[..., None] * self.e1 + np.sin(lr)[..., None] * self.e2)
                + np.sin(pr)[..., None] * self.n)

    def edge_cam(self, lam_deg, which: str) -> np.ndarray:
        lam = np.asarray(lam_deg, np.float64)
        l = ((lam + 180) % 360) - 180
        e = np.interp(l, self._lam, self._hi if which == "hi" else self._lo)
        lr, pr = lam * DEG, e * DEG
        cp = np.cos(pr)[..., None]
        return (cp * (np.cos(lr)[..., None] * self.e1 + np.sin(lr)[..., None] * self.e2)
                + np.sin(pr)[..., None] * self.n)

    def s_range_mm(self, radius_mm: float) -> Tuple[float, float]:
        if self.closed:
            return float(self._s[0] * radius_mm), float(self._s[-1] * radius_mm)
        a, b = self.lam_range
        sa = float(np.interp(a, self._lam, self._s) * radius_mm)
        sb = float(np.interp(b, self._lam, self._s) * radius_mm)
        if sb <= sa:                     # the range wraps through lam = +-180
            sb += self.length_rad * radius_mm
        return sa, sb


def strip_from_points(name: str, hi_pts: np.ndarray, lo_pts: np.ndarray,
                      pole: Optional[np.ndarray] = None, **kw) -> Tuple[np.ndarray, np.ndarray,
                                                                    list, list]:
    """Knots for a strip whose two edges pass through camera-frame points."""
    pts = np.concatenate([hi_pts, lo_pts], axis=0)
    n = normalize(pole) if pole is not None else fit_pole(pts)
    zero = normalize(pts.mean(axis=0))
    e1 = normalize(zero - np.dot(zero, n) * n)
    e2 = np.cross(n, e1)

    def knots(P):
        lam = np.degrees(np.arctan2(P @ e2, P @ e1))
        phi = np.degrees(np.arcsin(np.clip(P @ n, -1, 1)))
        return list(zip(lam.tolist(), phi.tolist()))
    return n, zero, knots(hi_pts), knots(lo_pts)


# --------------------------------------------------------------------------- the field

@dataclass
class Field:
    """Every strip evaluated at a set of points: the top label, counts and heights."""
    names: List[str]
    d: np.ndarray            # (S, N) signed distance, mm
    rank: np.ndarray         # (S, N)
    s: np.ndarray            # (S, N)
    w: np.ndarray            # (S, N)
    lift: np.ndarray         # (S, N)
    top: np.ndarray          # (N,) index of the visible strip, -1 where none covers
    covered: np.ndarray      # (S, N) bool
    half_width: Optional[np.ndarray] = None   # (S, N) mm

    def rank_top(self):
        r = np.where(self.covered, self.rank, -np.inf)
        return r


def evaluate_field(strips: Sequence[Strip], P: np.ndarray, radius_mm: float) -> Field:
    P = np.asarray(P, np.float64).reshape(-1, 3)
    S = len(strips)
    N = len(P)
    d = np.empty((S, N))
    rank = np.empty((S, N))
    s = np.empty((S, N))
    w = np.empty((S, N))
    lift = np.empty((S, N))
    hw = np.empty((S, N))
    for i, st in enumerate(strips):
        e = st.evaluate(P, radius_mm)
        d[i], rank[i], s[i], w[i], lift[i], hw[i] = e["d"], e["rank"], e["s"], e["w"], e["lift"], e["half_width"]
    covered = d >= 0.0
    r = np.where(covered, rank, -np.inf)
    top = np.argmax(r, axis=0)
    top = np.where(np.isfinite(r.max(axis=0)), top, -1)
    return Field([st.name for st in strips], d, rank, s, w, lift, top, covered, hw)


def smooth_cover(d: np.ndarray, ramp_mm: float) -> np.ndarray:
    """0 outside, 1 inside, a smoothstep over ``ramp_mm`` centred on the edge."""
    t = np.clip(d / ramp_mm + 0.5, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def soften_stack(x: np.ndarray, knee: float, above: float) -> np.ndarray:
    """g(x): layers count fully up to ``knee``, then at ``above`` per extra layer."""
    return np.where(x <= knee, x, knee + (x - knee) * above)


def sheet_layers(field: Field, which: np.ndarray, drape_mm: float, knee: float,
                 above: float) -> np.ndarray:
    """Layer height (in tape thicknesses) of strip ``which[j]``'s sheet at point j.

    ``which`` is an index per point (usually ``field.top``, or the strip whose piece the
    point belongs to).  Everything that covers the point with a LOWER rank than that
    strip lies under it and lifts it, each by its ramped coverage.
    """
    N = field.d.shape[1]
    j = np.arange(N)
    wr = field.rank[which, j]
    under = field.rank < wr[None, :]
    cov = smooth_cover(field.d, drape_mm) * under
    cov[which, j] = 0.0
    n = 1.0 + cov.sum(axis=0) + field.lift[which, j]
    return soften_stack(n, knee, above)


__all__ = ["REF_SIZE_PX", "REF_CENTRE_PX", "REF_RADIUS_PX", "ORTHO_D_PER_FRAME", "DEG",
           "latlon", "img_to_cam", "cam_to_img", "image_angle_deg", "cam_to_blender",
           "blender_to_cam", "normalize", "fit_pole", "periodic_spline", "step_function",
           "Strip", "strip_from_points", "Field", "evaluate_field", "smooth_cover",
           "soften_stack", "sheet_layers", "TABLE_STEP_DEG"]
