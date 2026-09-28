#!/usr/bin/env python
"""props_lib.smokebomb_wind - SM_SmokeBomb's ONE continuous tape, wound pass after pass.

numpy only (no bpy).  This module says WHERE the tape runs, HOW WIDE it lies there and
WHICH layer it lies on.  It knows nothing about the cloth cross-section, materials, UVs or
export: the tape builder (props_lib.smokebomb_tape) sweeps its section along what
``reference_winding()`` returns (``Winding.to_mm``) and asks ``Winding.layers_below`` how
far each point is lifted.

HOW THE REAL OBJECT IS MADE, AND HOW THIS MODULE MAKES IT
---------------------------------------------------------
A hand-wound ball is ONE tape.  The winder lays a loop round the core, turns the ball a
little and lays the next loop, so every loop (a PASS) is close to a great circle and its
axis precesses from pass to pass.  That gives the reference its long, continuous, sweeping
bands, its pinwheel where passes converge, and only one free end.

    core      the first ~24 loops: one continuous precessing winding (``core_path``) whose
              axis walks a short path through an even (Fibonacci) set of axes, so the loops
              cover every point of the ball at least twice - nothing anywhere is a void -
              and the tape is everywhere a near-great-circle (no joins in the core at all).
    pass k    a fitted near-great-circle: axis n_k and zero meridian e1_k (the point of the
              circle nearest the reference camera).  In the pass's own coordinates
                  phi = atan2(p.e2, p.e1)   position ALONG the pass (e2 = n x e1)
                  lam = asin(p.n)           offset ACROSS it (+n = left of travel)
              the tape centre runs at lam = beta_k(phi) and is w_k(phi) wide; beta, w and
              the gather g are uniform cubic B-splines over the pass's arc [phi_a, phi_b],
              which runs from just behind one limb to just behind the other (the FRONT
              arc).  A first harmonic in beta is an axis tilt; the rest are the bends a
              friction-held cloth tape takes.
    gather    0 = the tape lies flat and open; 1 = it is gathered into a rope of width
              CORD_W (REFERENCE_SPEC 4.2 "W twisted": a raised double rim ~0.010 D, the two
              rolled edges side by side).  footprint width = w (1 - g) + CORD_W g.
    connector the stretch on the FAR side between pass k's front arc and pass k+1's: pass k
              run straight on (a geodesic) and pass k+1 run straight back, blended with a
              C2 smootherstep; lengths chosen to keep it behind the limbs with the least
              in-plane (geodesic) curvature - this is where the winder turns the ball.
    order     the tape is laid in arc length s, so LATER IS ON TOP: key = s.
    weaves    CROSSING-LOCAL layering (REFERENCE_SPEC 4.4: "a single global layer index
              cannot represent this").  A Weave says: where this stretch of pass A lies on
              that stretch of pass B, A lies directly BELOW B (the winder threaded A
              under B there).  At a point, a demoted stretch takes the effective key of the
              stretch above it minus a hair, so the stack stays a stack; everywhere else the
              keys rule.  Because only points inside B's footprint are demoted, the only
              boundary anyone sees is B's own edge.  The reference's woven cycle (R_in > A
              > C > R_in's own lower end L5) is one weave; the free end is another (it is
              pushed under a pass on the far side, REFERENCE_SPEC 1 "Not present", 9.7).

FRAMES AND UNITS
----------------
Everything here is in the reference CAMERA frame (REFERENCE_SPEC 0): X right, Y up, Z
toward the camera, on the unit sphere (radius 1 = D / 2).  The Blender build frame (the
reference view is Blender's Front view: camera on -Y) is  X = Xc, Y = -Zc, Z = Yc
(``cam_to_build``).  Widths are carried in RADIANS of arc on the unit sphere (frac_D x 2).
The fitted numbers live in props_lib.smokebomb_wind_fit; the fit, its previews and scores
in WorkFiles/smokebomb/rewind/wind/.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

DEG = math.pi / 180.0

# --------------------------------------------------------------------------- reference frame
#: REFERENCE_SPEC 1 / 2: the reference's fitted silhouette circle (px) and frame
REF_SIZE_PX = 1254
REF_CENTRE_PX = (627.38, 628.92)
REF_RADIUS_PX = 464.11
#: REFERENCE_SPEC 4.5: the top whorl (the V-gap apex), camera frame
TOP_WHORL = np.array([0.135, 0.812, 0.568]) / np.linalg.norm([0.135, 0.812, 0.568])
#: REFERENCE_SPEC 9.5 (DESIGNED): the bottom convergence, 10 - 20 deg behind the bottom outline
BOTTOM_WHORL = np.array([0.05, -0.97, -0.25]) / np.linalg.norm([0.05, -0.97, -0.25])

#: the gathered rope's footprint (REFERENCE_SPEC 4.2 "W twisted": 0.010 D visible width)
CORD_W = 0.010 * 2.0
#: REFERENCE_SPEC 5: one tape thickness = the outline step 0.0062 D, in unit-sphere radii
STEP_R = 0.0062 * 2.0
#: a woven-under point sits this far (in key = arc length, rad) below the stretch above it:
#: far less than one loop (the gap between stretches), more than the rounding in a cell
WEAVE_HAIR = 1e-4


def cam_to_build(p) -> np.ndarray:
    p = np.asarray(p, np.float64)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)


def build_to_cam(p) -> np.ndarray:
    p = np.asarray(p, np.float64)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


def normalize(v) -> np.ndarray:
    v = np.asarray(v, np.float64)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-300)


def latlon(lat_deg, lon_deg) -> np.ndarray:
    lat = np.asarray(lat_deg, np.float64) * DEG
    lon = np.asarray(lon_deg, np.float64) * DEG
    return np.stack([np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)], -1)


def img_to_cam(x, y, back: bool = False) -> np.ndarray:
    """reference image px -> camera-frame unit vector (orthographic about the silhouette)."""
    cx, cy = REF_CENTRE_PX
    u = (np.asarray(x, np.float64) - cx) / REF_RADIUS_PX
    v = -(np.asarray(y, np.float64) - cy) / REF_RADIUS_PX
    r2 = np.minimum(u * u + v * v, 1.0)
    z = np.sqrt(1.0 - r2) * (-1.0 if back else 1.0)
    return normalize(np.stack([u, v, z], -1))


def cam_to_img(p) -> np.ndarray:
    p = np.asarray(p, np.float64)
    cx, cy = REF_CENTRE_PX
    return np.stack([cx + REF_RADIUS_PX * p[..., 0], cy - REF_RADIUS_PX * p[..., 1]], -1)


def image_angle_deg(p) -> np.ndarray:
    p = np.asarray(p, np.float64)
    return np.degrees(np.arctan2(p[..., 1], p[..., 0])) % 360.0


def rot_about(axis, ang) -> np.ndarray:
    a = normalize(axis)
    x, y, z = a
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def slerp_dir(p, t, ang) -> np.ndarray:
    """points reached from unit p heading along unit tangent t for arc ``ang`` (rad)."""
    ang = np.asarray(ang, np.float64)[..., None]
    return np.cos(ang) * p + np.sin(ang) * t


# --------------------------------------------------------------------------- B-splines
def bspline_basis(x: np.ndarray, a: float, b: float, k: int) -> np.ndarray:
    """uniform cubic B-spline basis on [a, b] with k >= 4 coefficients -> (len(x), k).
    Outside [a, b] the end cubic is evaluated at the end (flat continuation)."""
    x = np.atleast_1d(np.asarray(x, np.float64))
    nseg = k - 3
    h = (b - a) / nseg
    t = np.clip((x - a) / h, 0.0, nseg)
    i = np.minimum(np.floor(t).astype(int), nseg - 1)
    u = t - i
    B = np.zeros((x.size, k))
    r = np.arange(x.size)
    B[r, i] = (1 - u) ** 3 / 6.0
    B[r, i + 1] = (3 * u ** 3 - 6 * u ** 2 + 4) / 6.0
    B[r, i + 2] = (-3 * u ** 3 + 3 * u ** 2 + 3 * u + 1) / 6.0
    B[r, i + 3] = u ** 3 / 6.0
    return B


def smootherstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)


# --------------------------------------------------------------------------- a pass
@dataclass(frozen=True)
class PassSpec:
    """One loop of the tape's FRONT arc (see the module docstring).  Angles in DEGREES,
    widths in frac D.  beta / width / gather are B-spline coefficients over [phi_a, phi_b]."""
    name: str
    #: the REFERENCE_SPEC strips this pass shows (e.g. ("W",)); empty for a hidden pass
    shows: Tuple[str, ...]
    n: Tuple[float, float, float]
    e1: Tuple[float, float, float]
    phi_a: float
    phi_b: float
    beta: Tuple[float, ...]
    width: Tuple[float, ...]
    gather: Tuple[float, ...] = ()
    role: str = "visible"              # "visible" | "core"
    note: str = ""

    def frame(self):
        n = normalize(np.array(self.n, np.float64))
        e1 = np.array(self.e1, np.float64)
        e1 = normalize(e1 - np.dot(e1, n) * n)
        e2 = np.cross(n, e1)
        return e1, e2, n

    def _spl(self, coef, phi_deg, default=0.0):
        phi_deg = np.atleast_1d(np.asarray(phi_deg, np.float64))
        if not coef:
            return np.full(phi_deg.shape, default, np.float64)
        return bspline_basis(phi_deg, self.phi_a, self.phi_b, len(coef)) @ np.asarray(coef, np.float64)

    def beta_rad(self, phi_deg):
        return self._spl(self.beta, phi_deg) * DEG

    def width_rad(self, phi_deg):
        return self._spl(self.width, phi_deg) * 2.0

    def gather_at(self, phi_deg):
        return np.clip(self._spl(self.gather, phi_deg), 0.0, 1.0)

    def point(self, phi_deg, beta_rad=None) -> np.ndarray:
        e1, e2, n = self.frame()
        ph = np.atleast_1d(np.asarray(phi_deg, np.float64))
        be = self.beta_rad(ph) if beta_rad is None else np.broadcast_to(beta_rad, ph.shape)
        ph = ph * DEG
        cb = np.cos(be)[:, None]
        return cb * (np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2) + np.sin(be)[:, None] * n

    def tangent(self, phi_deg) -> np.ndarray:
        """unit direction of laying; one-sided at the ends of the arc (the spline is flat
        outside [phi_a, phi_b], which is not the tape's direction)."""
        ph = np.atleast_1d(np.asarray(phi_deg, np.float64))
        h = 0.02
        a = np.clip(ph - h, self.phi_a, self.phi_b)
        b = np.clip(ph + h, self.phi_a, self.phi_b)
        b = np.where(b - a < 1e-9, a + h, b)
        return normalize(self.point(b) - self.point(a))

    def coords(self, p) -> Tuple[np.ndarray, np.ndarray]:
        """(phi deg, lam rad) of camera-frame unit vectors p in this pass's own frame."""
        e1, e2, n = self.frame()
        p = np.asarray(p, np.float64)
        return (np.degrees(np.arctan2(p @ e2, p @ e1)), np.arcsin(np.clip(p @ n, -1.0, 1.0)))

    def reversed(self) -> "PassSpec":
        """the same tape laid the other way round: n -> -n flips phi and lam, so the spline
        coefficients run backwards and beta changes sign."""
        import dataclasses
        return dataclasses.replace(
            self, n=tuple(float(v) for v in -np.asarray(self.n, float)), phi_a=-self.phi_b, phi_b=-self.phi_a,
            beta=tuple(-v for v in self.beta[::-1]), width=tuple(self.width[::-1]),
            gather=tuple(self.gather[::-1]))

    def covers(self, p) -> np.ndarray:
        """does this pass's front arc cover the unit points p (footprint in the pass frame)?"""
        ph, lam = self.coords(p)
        inside = (ph >= self.phi_a) & (ph <= self.phi_b)
        be = self.beta_rad(ph)
        hw = 0.5 * (self.width_rad(ph) * (1 - self.gather_at(ph)) + CORD_W * self.gather_at(ph))
        return inside & (np.abs(lam - be) <= hw)


@dataclass
class Weave:
    """Where the ``lower`` pass's stretch lies on the ``upper`` pass's stretch, the lower
    lies directly BELOW the upper (crossing-local).  Each stretch is a phi range on the
    pass's front arc (deg), or with *_where="tail" an arc-length range past the end of the
    front arc (deg, the connector after it).  ``upper`` may be a tuple of passes: the lower
    then lies below whichever of them is lowest at each point (one group - the R strips
    diving under the whole U fan keep their own order while they do)."""
    lower: str
    lower_range: Tuple[float, float]
    upper: object
    #: None = the upper pass's front arc; with upper_where="all" and None = the whole pass
    upper_range: Optional[Tuple[float, float]] = None
    lower_where: str = "front"
    upper_where: str = "front"
    why: str = ""
    #: run the lower stretch on (within its pass) while its section still meets the upper
    #: stretch's footprint, so neither end of it lies under the upper (that would show as a
    #: cut across the tape) ...
    extend: bool = True
    #: ... unless a stretch laid later than the lower hides that end completely
    stop_hidden: bool = True

    def uppers(self) -> Tuple[str, ...]:
        return (self.upper,) if isinstance(self.upper, str) else tuple(self.upper)


# --------------------------------------------------------------------------- cube map
def _cube_index(p: np.ndarray, n: int) -> np.ndarray:
    """unit vectors -> flat equi-angular cube-map cell index (6 * n * n cells)."""
    p = np.asarray(p, np.float64)
    ax = np.argmax(np.abs(p), axis=-1)
    comp = np.take_along_axis(p, ax[..., None], -1)[..., 0]
    face = ax * 2 + (comp < 0)
    m = np.abs(comp)
    oa = np.where(ax == 0, 1, 0)
    ob = np.where(ax == 2, 1, 2)
    ua = np.take_along_axis(p, oa[..., None], -1)[..., 0] / m
    ub = np.take_along_axis(p, ob[..., None], -1)[..., 0] / m
    ia = np.clip(((np.arctan(ua) / (math.pi / 4)) * 0.5 + 0.5) * n, 0, n - 1).astype(np.int64)
    ib = np.clip(((np.arctan(ub) / (math.pi / 4)) * 0.5 + 0.5) * n, 0, n - 1).astype(np.int64)
    return (face * n + ia) * n + ib


def _cube_centres(n: int) -> np.ndarray:
    """(6 n n, 3) unit centre of every cube-map cell, in _cube_index order."""
    g = np.tan(((np.arange(n) + 0.5) / n * 2 - 1) * (math.pi / 4))
    A, B = np.meshgrid(g, g, indexing="ij")
    out = np.zeros((6, n, n, 3))
    for ax in range(3):
        oa = 1 if ax == 0 else 0
        ob = 1 if ax == 2 else 2
        for sgn in (0, 1):
            f = ax * 2 + sgn
            v = np.zeros((n, n, 3))
            v[..., ax] = -1.0 if sgn else 1.0
            v[..., oa] = A
            v[..., ob] = B
            out[f] = v
    return normalize(out.reshape(-1, 3))


def _dilate_cells(mask: np.ndarray, nf: int) -> np.ndarray:
    """grow a cube-map cell mask by one cell (neighbours through the cell centres)."""
    out = mask.copy()
    on = np.nonzero(mask)[0]
    if on.size == 0:
        return out
    P = _cube_centres(nf)[on]
    d = (math.pi / 2) / nf
    ref = np.where(np.abs(P[:, :1]) < 0.9, np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 1.0, 0.0]]))
    a = normalize(np.cross(P, ref))
    b = np.cross(P, a)
    for va in (a, -a, b, -b):
        out[_cube_index(normalize(P + d * va), nf)] = True
    return out


# --------------------------------------------------------------------------- the winding
@dataclass
class Winding:
    """The sampled tape.  Arrays are indexed by sample i along the tape (uniform in s)."""
    s: np.ndarray            # arc length on the unit sphere (rad), 0 at the inner end
    c: np.ndarray            # (N,3) centre, camera frame, unit
    t: np.ndarray            # (N,3) unit tangent (direction of laying)
    b: np.ndarray            # (N,3) unit across = c x t (left of travel)
    w: np.ndarray            # full open width, rad of arc
    gather: np.ndarray       # 0 open .. 1 gathered into a rope (CORD_W)
    pass_idx: np.ndarray     # index into ``passes`` (a connector belongs to the pass before it)
    phi: np.ndarray          # the pass's own phi (deg) on front arcs, NaN elsewhere
    tail: np.ndarray         # arc length (deg) past the end of the front arc on a connector, NaN elsewhere
    key: np.ndarray          # layer order key (= s: later is on top)
    passes: List[PassSpec]
    weaves: List[Weave]
    notes: Dict[str, object] = field(default_factory=dict)
    #: resolved weaves: sample ranges and, per weave, the cube-map key of the top-most
    #: upper-stretch sample at each cell (-inf where the upper stretch is absent)
    weave_lo: np.ndarray = None
    weave_hi: np.ndarray = None
    weave_upkey: List[np.ndarray] = None
    weave_face: int = 512

    @property
    def ds(self) -> float:
        return float(self.s[1] - self.s[0])

    @property
    def names(self) -> List[str]:
        return [p.name for p in self.passes]

    def w_eff(self) -> np.ndarray:
        """the footprint width: a gathered stretch keeps only the rope's width."""
        return self.w * (1.0 - self.gather) + CORD_W * self.gather

    def edge(self, side: int, idx=None) -> np.ndarray:
        """(N,3) edge line: side +1 = left of travel (+b), -1 = right."""
        idx = np.arange(self.s.size) if idx is None else np.asarray(idx)
        hw = 0.5 * self.w_eff()[idx]
        return normalize(np.cos(hw)[:, None] * self.c[idx] + side * np.sin(hw)[:, None] * self.b[idx])

    def points(self, v: np.ndarray, idx=None) -> np.ndarray:
        """(len(idx), len(v), 3) points across the tape; v in [-1, 1] (-1 right edge, +1 left)."""
        idx = np.arange(self.s.size) if idx is None else np.asarray(idx)
        hw = 0.5 * self.w_eff()[idx]
        a = hw[:, None] * np.asarray(v, np.float64)[None, :]
        return normalize(np.cos(a)[..., None] * self.c[idx, None, :] + np.sin(a)[..., None] * self.b[idx, None, :])

    def samples_of(self, name: str, rng=None, where: str = "front") -> np.ndarray:
        """sample indices of pass ``name``: its whole run (rng None), a phi range of its front
        arc (where="front"), or an arc-length range past the front arc (where="tail")."""
        k = self.names.index(name)
        m = self.pass_idx == k
        if rng is not None and where != "all":
            if where == "tail":
                m &= ~np.isnan(self.tail) & (self.tail >= rng[0]) & (self.tail <= rng[1])
            else:
                m &= (self.phi >= rng[0]) & (self.phi <= rng[1])
        return np.nonzero(m)[0]

    def geodesic_curvature(self) -> np.ndarray:
        """kappa_g = (dt/ds) . b  (0 on a great circle), per unit-sphere radian."""
        dt = np.gradient(self.t, self.s, axis=0)
        return np.einsum("ij,ij->i", dt, self.b)

    def edge_strain(self) -> np.ndarray:
        """|kappa_g| x half the footprint width: the in-plane strain the tape's edges take to
        follow the path flat (0.01 = 1 %)."""
        return np.abs(self.geodesic_curvature()) * 0.5 * self.w_eff()

    # ---------------------------------------------------------------- layering
    def effective_key(self, P: np.ndarray, sid: np.ndarray) -> np.ndarray:
        """the key of the tape at points P lying on samples sid: its own key, or - where a
        weave puts that stretch under another at that point - the key of the stretch above
        it minus a hair (weaves resolved upper-first, so chains stay a stack)."""
        sid = np.asarray(sid)
        k = self.key[sid].copy()
        if not self.weaves or self.weave_lo is None:
            return k
        cells = None
        for w in range(len(self.weaves)):
            if self.weave_upkey is None or self.weave_upkey[w] is None:
                continue
            a, b = self.weave_lo[w]
            m = (sid >= a) & (sid <= b)
            if not np.any(m):
                continue
            if cells is None:
                cells = _cube_index(np.asarray(P), self.weave_face)
            up = self.weave_upkey[w][cells[m]]
            dem = np.isfinite(up)
            if np.any(dem):
                kk = k[m]
                cand = up[dem] - WEAVE_HAIR + 1e-12 * self.key[sid[m][dem]]
                kk[dem] = np.minimum(kk[dem], cand)
                k[m] = kk
        return k

    def layers_below(self, P: np.ndarray, sid: np.ndarray, grid: "StackGrid" = None) -> np.ndarray:
        """how many tape stretches lie under the tape at points P (on samples sid), with the
        weaves applied - the tape builder lifts each point by this many thicknesses (or a
        capped/draped function of it)."""
        g = grid if grid is not None else self.stack_grid()
        P = np.asarray(P, np.float64)
        sid = np.asarray(sid)
        ek = self.effective_key(P, sid)
        ci = _cube_index(P, g.n_face)
        K = g.keys[ci]
        S = g.samples[ci]
        other = (S >= 0) & (np.abs(S - sid[:, None]) > 3 * g.run_len)
        return np.sum(other & (K < ek[:, None]), axis=1)

    def stack_grid(self, n_face: int = 256) -> "StackGrid":
        if self.notes.get("_grid_face") != n_face:
            self.notes["_grid"] = StackGrid.build(self, n_face=n_face)
            self.notes["_grid_face"] = n_face
        return self.notes["_grid"]

    def to_mm(self, radius_mm: float = 35.0) -> Dict[str, np.ndarray]:
        """The tape for the builder, in the BUILD frame (Blender: X right, Y back, Z up), mm:
        base centre points on the core sphere, outward normals, tangent, across (left), open
        width and footprint width (mm of arc), gather, key, pass index, phi, tail, s (mm)."""
        return dict(points_mm=cam_to_build(self.c) * radius_mm, normals=cam_to_build(self.c),
                    tangent=cam_to_build(self.t), across=cam_to_build(self.b),
                    width_mm=self.w * radius_mm, width_eff_mm=self.w_eff() * radius_mm,
                    gather=self.gather.copy(), key=self.key.copy(), pass_idx=self.pass_idx.copy(),
                    phi=self.phi.copy(), tail=self.tail.copy(), s_mm=self.s * radius_mm)


def splat_tape(wd: Winding, step: float, idx: Optional[np.ndarray] = None, facing=None, chunk: int = 3000):
    """Yield (points (M,3), sample index (M,), v in [-1,1] (M,)) covering the tape's footprint
    with spacing <= ``step`` (rad).  ``facing`` = unit view direction: skip samples whose
    whole section faces away from it."""
    N = wd.s.size
    idx_all = np.arange(N - 1) if idx is None else np.asarray(idx)
    idx_all = idx_all[idx_all < N - 1]
    w_eff = wd.w_eff()
    ds = wd.ds
    sub_s = max(1, int(math.ceil(ds / step)))
    if facing is not None:
        f = np.asarray(facing, np.float64)
        keep = (wd.c[idx_all] @ f) > -np.sin(0.5 * w_eff[idx_all] + 2 * ds) - 0.02
        idx_all = idx_all[keep]
    for i0 in range(0, idx_all.size, chunk):
        idx = idx_all[i0:i0 + chunk]
        for js in range(sub_s):
            fr = (js + 0.5) / sub_s
            c = normalize(wd.c[idx] * (1 - fr) + wd.c[idx + 1] * fr)
            bb = normalize(wd.b[idx] * (1 - fr) + wd.b[idx + 1] * fr)
            hw = 0.5 * (w_eff[idx] * (1 - fr) + w_eff[idx + 1] * fr)
            nv = np.maximum(2, np.ceil(2 * hw / step).astype(int) + 1)
            nvm = int(nv.max())
            vv = (np.arange(nvm)[None, :] + 0.5) / nv[:, None] * 2 - 1
            ok = np.arange(nvm)[None, :] < nv[:, None]
            a = hw[:, None] * vv
            P = np.cos(a)[..., None] * c[:, None, :] + np.sin(a)[..., None] * bb[:, None, :]
            sid = np.broadcast_to(np.where(fr < 0.5, idx, idx + 1)[:, None], ok.shape)
            yield P[ok], sid[ok], vv[ok]


def footprint_mask(wd: Winding, idx: np.ndarray, n_face: int = 512, dilate: bool = True) -> np.ndarray:
    """cube-map cells the samples ``idx`` cover."""
    m = np.zeros(6 * n_face * n_face, bool)
    cell = (math.pi / 2) / n_face
    for P, _sid, _v in splat_tape(wd, 0.45 * cell, idx=idx):
        m[_cube_index(P, n_face)] = True
    return _dilate_cells(m, n_face) if dilate else m


@dataclass
class StackGrid:
    """Per cube-map cell, every tape STRETCH covering it (a stretch = one contiguous run of
    samples through the cell): its effective key (weaves applied) and one of its samples."""
    n_face: int
    keys: np.ndarray        # (cells, M) float64 sorted ascending, +inf padded
    count: np.ndarray       # (cells,) int
    top_sample: np.ndarray  # (cells,) sample of the top stretch (-1 = bare)
    samples: np.ndarray = None
    run_len: int = 3

    @staticmethod
    def build(wd: Winding, n_face: int = 256) -> "StackGrid":
        cell = (math.pi / 2) / n_face
        step = 0.45 * cell
        ds = wd.ds
        cells_all, sid_all, ek_all = [], [], []
        for P, sid, _v in splat_tape(wd, step):
            cells_all.append(_cube_index(P, n_face))
            sid_all.append(sid)
            ek_all.append(wd.effective_key(P, sid))
        cells = np.concatenate(cells_all)
        sid = np.concatenate(sid_all)
        ek = np.concatenate(ek_all)
        o = np.lexsort((ek, sid, cells))
        cells, sid, ek = cells[o], sid[o], ek[o]
        first = np.ones(len(cells), bool)
        first[1:] = (cells[1:] != cells[:-1]) | (sid[1:] != sid[:-1])
        cells, sid, ek = cells[first], sid[first], ek[first]
        gap = max(3, int(3 * cell / ds) + 2)
        newrun = np.ones(len(cells), bool)
        newrun[1:] = ~((cells[1:] == cells[:-1]) & ((sid[1:] - sid[:-1]) <= gap))
        run_id = np.cumsum(newrun) - 1
        run_key = np.full(run_id[-1] + 1, np.inf)
        np.minimum.at(run_key, run_id, ek)
        run_cell = cells[newrun]
        run_sample = sid[newrun]
        ncell = 6 * n_face * n_face
        order = np.lexsort((run_key, run_cell))
        run_cell, run_key, run_sample = run_cell[order], run_key[order], run_sample[order]
        cnt = np.bincount(run_cell, minlength=ncell)
        M = int(cnt.max())
        start = np.zeros(ncell + 1, np.int64)
        start[1:] = np.cumsum(cnt)
        rank = np.arange(len(run_cell)) - start[run_cell]
        K = np.full((ncell, M), np.inf)
        K[run_cell, rank] = run_key
        S = np.full((ncell, M), -1, np.int64)
        S[run_cell, rank] = run_sample
        top = np.full(ncell, -1, np.int64)
        last = start[1:] - 1
        has = cnt > 0
        top[has] = run_sample[last[has]]
        return StackGrid(n_face, K, cnt, top, S, gap)

    def depth(self, p) -> np.ndarray:
        return self.count[_cube_index(p, self.n_face)]


# --------------------------------------------------------------------------- weaves
def resolve_weaves(wd: Winding) -> None:
    """Turn every Weave into sample ranges and the upper stretch's per-cell key.  Weaves are
    resolved upper-first (a weave whose upper stretch is itself woven under a third waits
    for that one), so a chain A < B < C stays a stack."""
    wd.weave_lo = np.zeros((len(wd.weaves), 2), np.int64)
    wd.weave_hi = np.zeros((len(wd.weaves), 2), np.int64)
    wd.weave_upkey = [None] * len(wd.weaves)
    if not wd.weaves:
        return
    nf = wd.weave_face
    cell = (math.pi / 2) / nf
    lo_idx, hi_idx = [], []
    for w in wd.weaves:
        lo = wd.samples_of(w.lower, w.lower_range, w.lower_where)
        his = []
        for un in w.uppers():
            if w.upper_range is None and w.upper_where == "front":
                # by default the upper stretch is the upper pass's FRONT arc (a crossing the
                # viewer sees); its far-side connector is not part of it
                up = wd.passes[wd.names.index(un)]
                his.append(wd.samples_of(un, (up.phi_a, up.phi_b), "front"))
            elif w.upper_where.startswith("front+"):
                # the front arc and the first N deg of its far-side connector
                up = wd.passes[wd.names.index(un)]
                his.append(wd.samples_of(un, (up.phi_a, up.phi_b), "front"))
                his.append(wd.samples_of(un, (0.0, float(w.upper_where[6:])), "tail"))
            else:
                his.append(wd.samples_of(un, w.upper_range, w.upper_where))
        hi = np.unique(np.concatenate(his)) if his else np.zeros(0, np.int64)
        if lo.size == 0 or hi.size == 0:
            raise ValueError(f"weave {w} selects no samples")
        lo_idx.append(lo)
        hi_idx.append(hi)
    v = np.linspace(-1.0, 1.0, 11)
    fp_cache = {}
    grid = None
    for i, w in enumerate(wd.weaves):
        a, b = int(lo_idx[i][0]), int(lo_idx[i][-1])
        if w.extend:
            key = (w.uppers(), None if w.upper_range is None else tuple(w.upper_range), w.upper_where)
            if key not in fp_cache:
                fp_cache[key] = footprint_mask(wd, hi_idx[i], nf)
            fp = fp_cache[key]
            own = np.nonzero(wd.pass_idx == wd.pass_idx[a])[0]
            if w.lower_where == "tail":
                own = own[~np.isnan(wd.tail[own])]          # a stretch of the connector stays on it
            lo_lim, hi_lim = int(own[0]), int(own[-1])
            if grid is None:
                grid = StackGrid.build(wd, n_face=256)      # base keys (no weave yet)

            def needs_more(q):
                """the stretch's end must not lie under the upper where anyone could see
                it: run on while the section still meets the upper's footprint, unless every
                point of it there is covered by a stretch laid later (the change is hidden)."""
                P = wd.points(v, idx=[q])[0]
                inside = fp[_cube_index(P, nf)]
                if not inside.any():
                    return False
                if not w.stop_hidden:
                    return True
                ci = _cube_index(P[inside], grid.n_face)
                K, S = grid.keys[ci], grid.samples[ci]
                above = (S >= 0) & (np.abs(S - q) > 3 * grid.run_len) & (K > wd.key[q])
                return not bool(above.any(axis=1).all())
            while a > lo_lim and needs_more(a - 1):
                a -= 1
            while b < hi_lim and needs_more(b + 1):
                b += 1
        wd.weave_lo[i] = (a, b)
        wd.weave_hi[i] = (hi_idx[i][0], hi_idx[i][-1]) if len(hi_idx[i]) else (0, -1)
    # order: a weave whose upper samples are the lower of another weave comes after it
    done = [False] * len(wd.weaves)
    active = []                                   # weaves already usable in effective_key
    saved = (wd.weave_lo, wd.weave_upkey)
    for _round in range(len(wd.weaves) + 1):
        progressed = False
        for i, w in enumerate(wd.weaves):
            if done[i]:
                continue
            deps = [j for j in range(len(wd.weaves)) if j != i and not done[j]
                    and wd.weave_lo[j][0] <= wd.weave_hi[i][1] and wd.weave_lo[j][1] >= wd.weave_hi[i][0]]
            if deps and _round < len(wd.weaves):
                continue
            # the upper stretch's LOWEST effective key per cell, so a point demoted under it
            # lies under every point of it there (a stretch's keys vary along it)
            up = np.full(6 * nf * nf, np.inf)
            wd.weave_upkey = [u if done[j] else None for j, u in enumerate(wd.weave_upkey)]
            for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=hi_idx[i]):
                ek = _effective_key_partial(wd, P, sid, done)
                np.minimum.at(up, _cube_index(P, nf), ek)
            # dilate one cell so the upper's own edge covers the lower there
            up = _dilate_min(up, nf)
            wd.weave_upkey[i] = up
            done[i] = True
            progressed = True
        if all(done):
            break
        if not progressed:
            break
    wd.weave_upkey = [u if u is not None else np.full(6 * nf * nf, np.inf) for u in wd.weave_upkey]


def _effective_key_partial(wd: Winding, P, sid, done) -> np.ndarray:
    k = wd.key[sid].copy()
    cells = None
    for w, ok in enumerate(done):
        if not ok or wd.weave_upkey[w] is None:
            continue
        a, b = wd.weave_lo[w]
        m = (sid >= a) & (sid <= b)
        if not np.any(m):
            continue
        if cells is None:
            cells = _cube_index(P, wd.weave_face)
        up = wd.weave_upkey[w][cells[m]]
        dem = np.isfinite(up)
        if np.any(dem):
            kk = k[m]
            kk[dem] = np.minimum(kk[dem], up[dem] - WEAVE_HAIR + 1e-12 * wd.key[sid[m][dem]])
            k[m] = kk
    return k


def _dilate_min(up: np.ndarray, nf: int) -> np.ndarray:
    """grow a per-cell key map by one cell (min with the four neighbours)."""
    on = np.nonzero(np.isfinite(up))[0]
    if on.size == 0:
        return up
    out = up.copy()
    P = _cube_centres(nf)[on]
    d = (math.pi / 2) / nf
    ref = np.where(np.abs(P[:, :1]) < 0.9, np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 1.0, 0.0]]))
    a = normalize(np.cross(P, ref))
    b = np.cross(P, a)
    for va in (a, -a, b, -b):
        np.minimum.at(out, _cube_index(normalize(P + d * va), nf), up[on])
    return out


# --------------------------------------------------------------------------- connectors
def _geodesic_run(p, t, L_deg, u):
    """points from p heading t (unit tangent) along a great circle, arc u * L (deg)."""
    return slerp_dir(p[None, :], t[None, :], np.asarray(u) * L_deg * DEG)


def _connector_pts(A0, tA, B0, tB, La_max=175.0, Lb_max=175.0, wall=True, step_deg=0.25, fixed=None):
    """the far-side join from (A0, heading tA) to (B0, heading tB): A run straight on and B
    run straight back, blended with smootherstep; (La, Lb) searched for the least squared
    geodesic curvature behind a hard wall at the limbs (z <= -0.03) unless wall=False."""
    tA = normalize(tA - np.dot(tA, A0) * A0)
    tB = normalize(tB - np.dot(tB, B0) * B0)

    def build(La, Lb, m):
        u = np.linspace(0.0, 1.0, m)
        h = smootherstep(u)
        A = _geodesic_run(A0, tA, La, u)
        B = _geodesic_run(B0, -tB, Lb, 1 - u)
        return normalize((1 - h)[:, None] * A + h[:, None] * B), u, h

    def cost(La, Lb):
        P, u, h = build(La, Lb, 121)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        L = seg.sum()
        if not np.all(seg > 1e-9):
            return np.inf
        s = np.concatenate([[0], np.cumsum(seg)])
        T = np.gradient(P, s, axis=0)
        T = normalize(T - np.einsum("ij,ij->i", T, P)[:, None] * P)
        dT = np.gradient(T, s, axis=0)
        kg = np.einsum("ij,ij->i", dT, np.cross(P, T))
        z = P[:, 2]
        inner = (s > 4 * DEG) & (s < L - 4 * DEG)
        front = np.clip(z[inner] + 0.03, 0.0, None) if wall else np.zeros(1)
        # no cusp: the tape must never double back on itself
        dseg = np.diff(P, axis=0)
        dseg /= np.maximum(np.linalg.norm(dseg, axis=1, keepdims=True), 1e-12)
        if np.min(np.einsum("ij,ij->i", dseg[1:], dseg[:-1])) < 0.9:
            return np.inf
        return float(np.mean(kg ** 2) * L + 1e5 * np.sum(front ** 2) + 0.02 * L)

    if fixed is not None:
        La, Lb = fixed
        c = None
    else:
        best = None
        lo = 5.0 if not wall else 30.0
        for La in np.arange(lo, La_max + 0.1, 7.5):
            for Lb in np.arange(lo, Lb_max + 0.1, 7.5):
                c = cost(La, Lb)
                if best is None or c < best[0]:
                    best = (c, La, Lb)
        _, La, Lb = best
        for stp in (2.5, 0.8):
            for dLa in (-2 * stp, -stp, 0, stp, 2 * stp):
                for dLb in (-2 * stp, -stp, 0, stp, 2 * stp):
                    a, b = min(La_max, max(5.0, La + dLa)), min(Lb_max, max(5.0, Lb + dLb))
                    cc = cost(a, b)
                    if cc < best[0]:
                        best = (cc, a, b)
            _, La, Lb = best
        c = best[0]
    m = max(24, int(math.ceil(max(La, Lb) / step_deg)))
    P, u, h = build(La, Lb, m + 2)
    return P[1:-1], h[1:-1], dict(La=float(La), Lb=float(Lb), cost=c)


def _tail_pts(A0, tA, L_deg, step_deg: float = 0.25):
    tA = normalize(tA - np.dot(tA, A0) * A0)
    m = max(8, int(math.ceil(L_deg / step_deg)))
    u = np.linspace(0, 1, m + 1)[1:]
    return _geodesic_run(A0, tA, L_deg, u), u * L_deg


# --------------------------------------------------------------------------- the core
def core_axes(n: int, first_axis, last_axis) -> np.ndarray:
    """n loop axes spread evenly over the hemisphere (a Fibonacci set: a circle's axis and
    its antipode are one circle), walked as a short path (nearest neighbour + 2-opt) that
    starts at ``first_axis``; the walk is reversed if that brings its end nearer
    ``last_axis``, and signs are aligned so the sense of travel never flips."""
    fa = normalize(first_axis)
    la = normalize(last_axis)
    ga = math.pi * (3 - math.sqrt(5))
    pts = []
    for k in range(n):
        z = 1 - (k + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        pts.append([r * math.cos(k * ga), r * math.sin(k * ga), z])
    pts = normalize(np.array(pts))
    zc = np.array([0.0, 0.0, 1.0])
    v = np.cross(zc, fa)
    if np.linalg.norm(v) > 1e-9:
        pts = pts @ rot_about(v, math.acos(np.clip(fa[2], -1, 1))).T

    def dist(a, b):
        return math.acos(min(1.0, abs(float(np.dot(a, b)))))
    left = list(range(1, n))
    path = [0]
    while left:
        j = min(left, key=lambda q: dist(pts[path[-1]], pts[q]))
        path.append(j)
        left.remove(j)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a0, a1, b0, b1 = pts[path[i - 1]], pts[path[i]], pts[path[j]], pts[path[j + 1]]
                if dist(a0, b0) + dist(a1, b1) < dist(a0, a1) + dist(b0, b1) - 1e-9:
                    path[i:j + 1] = path[i:j + 1][::-1]
                    improved = True
    axes = [pts[i] for i in path]
    if dist(axes[0], la) < dist(axes[-1], la):
        axes = axes[::-1]
    out = [normalize(axes[0])]
    for ax in axes[1:]:
        ax = normalize(ax)
        out.append(ax if np.dot(ax, out[-1]) >= 0 else -ax)
    return np.array(out)


def core_path(axes: np.ndarray, width_frac_d: float = 0.20, ds_deg: float = 0.2):
    """The CORE as one continuous precessing winding: loop k runs round axis n_k, and the
    axis turns smoothly (an eased slerp) from n_k to n_{k+1} WHILE the loop is laid, so the
    tape is everywhere a near-great-circle (its in-plane curvature is the axis's turning
    rate, about (step angle) / (2 pi)) and there is no join anywhere.  Returns (points (M,3),
    width rad (M,))."""
    m = len(axes)
    per = int(round(360.0 / ds_deg))
    t = np.arange(m * per) / per
    k = np.minimum(np.floor(t).astype(int), m - 1)
    f = smootherstep(t - k)
    k1 = np.minimum(k + 1, m - 1)
    A, B = axes[k], axes[k1]
    om = np.arccos(np.clip(np.einsum("ij,ij->i", A, B), -1, 1))
    so = np.where(om < 1e-9, 1.0, np.sin(np.maximum(om, 1e-9)))
    wa = np.where(om < 1e-9, 1 - f, np.sin((1 - f) * om) / so)
    wb = np.where(om < 1e-9, f, np.sin(f * om) / so)
    N = normalize(wa[:, None] * A + wb[:, None] * B)
    U = np.zeros_like(N)
    ref = np.array([0.31, 0.47, 0.83])
    u = normalize(ref - np.dot(ref, N[0]) * N[0])
    for i in range(len(N)):
        u = u - np.dot(u, N[i]) * N[i]
        u = u / np.linalg.norm(u)
        U[i] = u
    V = np.cross(N, U)
    th = 2 * math.pi * t
    P = np.cos(th)[:, None] * U + np.sin(th)[:, None] * V
    return normalize(P), np.full(len(P), width_frac_d * 2.0)


def core_start_trim(CP: np.ndarray, CW: np.ndarray, per: int = 1800, nf: int = 256) -> int:
    """the first core sample whose cap lies under the core laid one loop later (so the
    tape's inner end is buried)."""
    later_cache = {}
    for k in range(0, per, 20):
        Pl = CP[k + per:]
        tl = normalize(np.gradient(Pl, axis=0))
        bl = normalize(np.cross(Pl, tl))
        later = np.zeros(6 * nf * nf, bool)
        for vv in np.linspace(-0.95, 0.95, 41):
            a = 0.5 * CW[k + per:] * vv
            later[_cube_index(normalize(np.cos(a)[:, None] * Pl + np.sin(a)[:, None] * bl), nf)] = True
        t0 = normalize(CP[k + 1] - CP[k])
        b0 = normalize(np.cross(CP[k], t0))
        cap = normalize(np.array([np.cos(0.5 * CW[k] * vv) * CP[k] + np.sin(0.5 * CW[k] * vv) * b0
                                  for vv in np.linspace(-1, 1, 11)]))
        if later[_cube_index(cap, nf)].all():
            return k
    return 0


# --------------------------------------------------------------------------- assembly
def assemble(passes: Sequence[PassSpec], weaves: Sequence[Weave] = (), tail_deg: float = 60.0,
             core: Optional[Tuple[np.ndarray, np.ndarray]] = None, connectors: Optional[Sequence[dict]] = None,
             ds_deg: float = 0.2, dphi_deg: float = 0.2, tail_fold: float = 0.85,
             tail_fold_deg: float = 30.0) -> Winding:
    """Chain the core path (pass 0, "core"), the passes' front arcs and the far-side
    connectors, ending in the finishing tail, into one tape sampled uniformly in s.
    ``connectors`` (one dict per join, core->first pass first) freezes the (La, Lb) of each
    join; otherwise they are searched."""
    pts, wid, gat, pid, phis, tails = [], [], [], [], [], []
    conn_info = []
    passes = list(passes)
    allp = []
    ci = 0

    def conn(A0, tA, wa, ga, B0, tB, wb, gb, wall, lim):
        nonlocal ci
        fx = None
        if connectors is not None and ci < len(connectors) and connectors[ci] is not None:
            fx = (connectors[ci]["La"], connectors[ci]["Lb"])
        P, h, info = _connector_pts(A0, tA, B0, tB, La_max=lim, Lb_max=lim, wall=wall, fixed=fx)
        ci += 1
        seg = np.linalg.norm(np.diff(np.vstack([A0, P]), axis=0), axis=1)
        return P, (1 - h) * wa + h * wb, (1 - h) * ga + h * gb, np.degrees(np.cumsum(seg)), info

    if core is not None:
        CP, CW = core
        pts.append(CP)
        wid.append(CW)
        gat.append(np.zeros(len(CP)))
        pid.append(np.zeros(len(CP), int))
        phis.append(np.full(len(CP), np.nan))
        tails.append(np.full(len(CP), np.nan))
        p0 = passes[0]
        P, Wd, G, T, info = conn(CP[-1], normalize(CP[-1] - CP[-2]), float(CW[-1]), 0.0,
                                 p0.point(p0.phi_a)[0], p0.tangent(p0.phi_a)[0], float(p0.width_rad(p0.phi_a)[0]),
                                 float(p0.gather_at(p0.phi_a)[0]), False, 175.0)
        pts.append(P)
        wid.append(Wd)
        gat.append(G)
        pid.append(np.zeros(len(P), int))
        phis.append(np.full(len(P), np.nan))
        tails.append(T)
        conn_info.append(dict(frm="core", to=p0.name, **info))
        allp.append(PassSpec(name="core", shows=(), n=(0.0, 0.0, 1.0), e1=(1.0, 0.0, 0.0), phi_a=0.0,
                             phi_b=1.0, beta=(0.0,) * 4, width=(float(CW[0]) / 2,) * 4, role="core",
                             note="continuous precessing core winding"))
    off = len(allp)
    allp += passes
    for k in range(off, len(allp)):
        ps = allp[k]
        nph = max(8, int(math.ceil((ps.phi_b - ps.phi_a) / dphi_deg)))
        ph = np.linspace(ps.phi_a, ps.phi_b, nph + 1)
        pts.append(ps.point(ph))
        wid.append(ps.width_rad(ph))
        gat.append(ps.gather_at(ph))
        pid.append(np.full(ph.size, k))
        phis.append(ph)
        tails.append(np.full(ph.size, np.nan))
        A0 = ps.point(ps.phi_b)[0]
        tA = ps.tangent(ps.phi_b)[0]
        if k + 1 < len(allp):
            pb = allp[k + 1]
            P, Wd, G, T, info = conn(A0, tA, float(ps.width_rad(ps.phi_b)[0]), float(ps.gather_at(ps.phi_b)[0]),
                                     pb.point(pb.phi_a)[0], pb.tangent(pb.phi_a)[0], float(pb.width_rad(pb.phi_a)[0]),
                                     float(pb.gather_at(pb.phi_a)[0]), True, 175.0)
            conn_info.append(dict(frm=ps.name, to=pb.name, **info))
        else:
            # the free end: run straight on, the last ``tail_fold_deg`` folded/gathered narrow
            # (a winder folds the end before pushing it under a wrap)
            P, T = _tail_pts(A0, tA, tail_deg)
            Wd = np.full(len(P), float(ps.width_rad(ps.phi_b)[0]))
            G = tail_fold * smootherstep((T - (tail_deg - tail_fold_deg)) / max(tail_fold_deg, 1e-6))
        pts.append(P)
        wid.append(Wd)
        gat.append(G)
        pid.append(np.full(len(P), k))
        phis.append(np.full(len(P), np.nan))
        tails.append(T)
    P = np.concatenate(pts)
    Wd = np.concatenate(wid)
    Ga = np.concatenate(gat)
    Pi = np.concatenate(pid)
    Ph = np.concatenate(phis)
    Tl = np.concatenate(tails)
    seg = np.arccos(np.clip(np.einsum("ij,ij->i", P[1:], P[:-1]), -1, 1))
    keep = np.concatenate([[True], seg > 1e-9])
    P, Wd, Ga, Pi, Ph, Tl = P[keep], Wd[keep], Ga[keep], Pi[keep], Ph[keep], Tl[keep]
    seg = np.arccos(np.clip(np.einsum("ij,ij->i", P[1:], P[:-1]), -1, 1))
    s0 = np.concatenate([[0.0], np.cumsum(seg)])
    ds = ds_deg * DEG
    s = np.arange(0.0, s0[-1], ds)
    j = np.clip(np.searchsorted(s0, s, side="right") - 1, 0, len(s0) - 2)
    f = (s - s0[j]) / np.maximum(s0[j + 1] - s0[j], 1e-12)
    c = normalize(P[j] * (1 - f)[:, None] + P[j + 1] * f[:, None])
    w = Wd[j] * (1 - f) + Wd[j + 1] * f
    ga = Ga[j] * (1 - f) + Ga[j + 1] * f
    pi = np.where(f < 0.5, Pi[j], Pi[j + 1])
    ph = np.where(np.isnan(Ph[j]) | np.isnan(Ph[j + 1]), np.nan, Ph[j] * (1 - f) + Ph[j + 1] * f)
    tl = np.where(np.isnan(Tl[j]) | np.isnan(Tl[j + 1]), np.nan, Tl[j] * (1 - f) + Tl[j + 1] * f)
    t = np.gradient(c, axis=0)
    t = normalize(t - np.einsum("ij,ij->i", t, c)[:, None] * c)
    b = normalize(np.cross(c, t))
    wd = Winding(s=s, c=c, t=t, b=b, w=w, gather=ga, pass_idx=pi, phi=ph, tail=tl, key=s.copy(),
                 passes=allp, weaves=list(weaves), notes={"connectors": conn_info})
    resolve_weaves(wd)
    return wd


# --------------------------------------------------------------------------- the frozen design
def reference_winding(fit=None) -> Winding:
    """SM_SmokeBomb's tape, assembled from the frozen numbers in props_lib.smokebomb_wind_fit:
    the core path, the fitted passes in winding order, the far-side joins, the folded free
    end and the weaves.  Deterministic; numpy only."""
    if fit is None:
        from . import smokebomb_wind_fit as fit
    axes = np.array(fit.CORE_AXES, np.float64)
    CP, CW = core_path(axes, fit.CORE_WIDTH)
    CP, CW = CP[:fit.CORE_END + 1], CW[:fit.CORE_END + 1]
    CP, CW = CP[fit.CORE_TRIM:], CW[fit.CORE_TRIM:]
    passes = [PassSpec(name=p["name"], shows=tuple(p["shows"]), n=tuple(p["n"]), e1=tuple(p["e1"]),
                       phi_a=p["phi_a"], phi_b=p["phi_b"], beta=tuple(p["beta"]), width=tuple(p["width"]),
                       gather=tuple(p["gather"]), role=p["role"], note=p["note"]) for p in fit.PASSES]
    weaves = [Weave(**w) for w in fit.WEAVES]
    conns = [dict(La=a, Lb=b) for a, b in fit.CONNECTORS]
    wd = assemble(passes, weaves, tail_deg=fit.TAIL_DEG, core=(CP, CW), connectors=conns,
                  tail_fold=fit.TAIL_FOLD)
    wd.notes["design"] = fit.DESIGN
    return wd


# --------------------------------------------------------------------------- views + raster
VIEWS = {
    # name: (toward-camera d, image right r, image up u), camera frame
    "front": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "back": ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
    "left": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "right": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    "top": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    "bottom": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
}


def view_axes(view) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if isinstance(view, str):
        d, r, u = VIEWS[view]
    else:
        d, r, u = view
    return (normalize(np.array(d, np.float64)), normalize(np.array(r, np.float64)),
            normalize(np.array(u, np.float64)))


def render_labels(wd: Winding, view="front", size: int = 627, scale: float = None, centre=None,
                  lift: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
    """Orthographic label render: per pixel the TOP point of the tape (largest effective
    key, weaves applied).  Framing defaults to the reference's (REFERENCE_SPEC 2: ortho,
    ball D = 0.7402 of the frame).  Returns sample (-1 = background), v (across, -1..1),
    pass_ (-1 = background)."""
    d, r, u = view_axes(view)
    sc = size / REF_SIZE_PX
    R = REF_RADIUS_PX * sc if scale is None else scale
    cx, cy = (REF_CENTRE_PX[0] * sc, REF_CENTRE_PX[1] * sc) if centre is None else centre
    step = 0.6 / R
    N = wd.key.size
    # every key a point can take is a sample key or (woven) a hair below one: rank on floats
    VQ = 1024
    bufk = np.full(size * size, -np.inf)
    bufs = np.full(size * size, -1, np.int64)
    bufv = np.zeros(size * size)
    for P, sid, vv in splat_tape(wd, step, facing=d):
        f = P @ d
        m = f > 0
        P, sid, vv = P[m], sid[m], vv[m]
        rad = 1.0 if lift is None else (1.0 + lift[sid])[:, None]
        Q = P * rad
        x = np.floor(cx + R * (Q @ r)).astype(np.int64)
        y = np.floor(cy - R * (Q @ u)).astype(np.int64)
        ok = (x >= 0) & (x < size) & (y >= 0) & (y < size)
        P, sid, vv, x, y = P[ok], sid[ok], vv[ok], x[ok], y[ok]
        pix = y * size + x
        ek = wd.effective_key(P, sid)
        # per pixel keep the largest key: sort this chunk, take the last per pixel, merge
        o = np.lexsort((ek, pix))
        pix, ek, sid, vv = pix[o], ek[o], sid[o], vv[o]
        last = np.ones(len(pix), bool)
        last[:-1] = pix[1:] != pix[:-1]
        pix, ek, sid, vv = pix[last], ek[last], sid[last], vv[last]
        better = ek > bufk[pix]
        bufk[pix[better]] = ek[better]
        bufs[pix[better]] = sid[better]
        bufv[pix[better]] = vv[better]
    has = bufs >= 0
    v = np.full(size * size, np.nan)
    v[has] = bufv[has]
    pas = np.full(size * size, -1, np.int64)
    pas[has] = wd.pass_idx[bufs[has]]
    return dict(sample=bufs.reshape(size, size), v=v.reshape(size, size), pass_=pas.reshape(size, size),
                key=bufk.reshape(size, size), size=size, R=R, cx=cx, cy=cy, view=view)


# --------------------------------------------------------------------------- checks
def coverage(wd: Winding, n_face: int = 128) -> Dict[str, object]:
    """how many stretches cover each cube-map cell; voids = cells nothing covers."""
    sg = StackGrid.build(wd, n_face=n_face)
    cnt = sg.count
    cen = _cube_centres(n_face)
    void = cnt == 0
    return dict(min=int(cnt.min()), mean=float(cnt.mean()), p05=float(np.percentile(cnt, 5)),
                max=int(cnt.max()), void_cells=int(void.sum()), void_frac=float(void.mean()),
                void_dirs=cen[void][:50].tolist())


def end_cap_cover(wd: Winding, idx: np.ndarray, n_face: int = 512) -> Dict[int, List[int]]:
    """for each candidate end sample: the passes whose footprint holds the tape's whole
    section there (the free end can be woven under any of them)."""
    v = np.linspace(-1.0, 1.0, 11)
    masks = {j: footprint_mask(wd, np.nonzero(wd.pass_idx == j)[0], n_face, dilate=False)
             for j in range(len(wd.passes) - 1)}
    out = {}
    for i in idx:
        cells = _cube_index(wd.points(v, idx=[i])[0], n_face)
        out[int(i)] = [j for j, m in masks.items() if m[cells].all()]
    return out


def end_hidden(wd: Winding, which: str = "end", n_face: int = 512) -> Dict[str, object]:
    """is the tape's inner (start) or free (end) cap covered at every point by a stretch
    with a higher effective key?  (The end cap is what a viewer could see as a cut end.)"""
    i = 0 if which == "start" else wd.s.size - 1
    v = np.linspace(-0.98, 0.98, 21)
    cap = wd.points(v, idx=[i])[0]
    ek = wd.effective_key(cap, np.full(len(cap), i))
    g = wd.stack_grid(256)
    ci = _cube_index(cap, g.n_face)
    K, S = g.keys[ci], g.samples[ci]
    far = (S >= 0) & (np.abs(S - i) > 3 * g.run_len)
    covered = np.any(far & (K > ek[:, None]), axis=1)
    return dict(which=which, sample=i, covered_frac=float(covered.mean()), all_covered=bool(covered.all()))


__all__ = ["DEG", "REF_SIZE_PX", "REF_CENTRE_PX", "REF_RADIUS_PX", "TOP_WHORL", "BOTTOM_WHORL", "CORD_W",
           "STEP_R", "cam_to_build", "build_to_cam", "normalize", "latlon", "img_to_cam", "cam_to_img",
           "image_angle_deg", "rot_about", "bspline_basis", "smootherstep", "PassSpec", "Weave", "Winding",
           "StackGrid", "splat_tape", "footprint_mask", "resolve_weaves", "core_axes", "core_path",
           "core_start_trim", "assemble", "reference_winding", "VIEWS", "view_axes", "render_labels", "coverage", "end_cap_cover",
           "end_hidden"]
