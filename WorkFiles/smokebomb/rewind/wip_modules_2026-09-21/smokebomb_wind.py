#!/usr/bin/env python
"""props_lib.smokebomb_wind - SM_SmokeBomb's ONE continuous tape, wound pass after pass.

numpy only (no bpy).  This module says WHERE the tape runs and WHICH layer it lies on.  It
does not know about the cloth cross-section, materials, UVs or export: the tape builder
(props_lib.smokebomb_tape) sweeps its cross-section along what this module returns.

HOW THE REAL OBJECT IS MADE, AND HOW THIS MODULE MAKES IT
---------------------------------------------------------
A hand-wound ball is ONE tape.  The winder lays a loop round the core, turns the ball a
little and lays the next loop, so every loop (a PASS) is close to a great circle and its
axis precesses from pass to pass.  That is what gives the reference its long, continuous,
sweeping bands, its pinwheel where passes converge, and only one free end.

    pass k    a near-great-circle: axis n_k, zero meridian e1_k (the point of the front
              half nearest the camera), and in the pass's own spherical coordinates
                  phi    = atan2(p.e2, p.e1)        position ALONG the pass
                  lam    = asin(p.n)               offset ACROSS it (toward +n = left of travel)
              the tape centre runs at lam = beta_k(phi) and the tape is w_k(phi) wide.
              beta, w and the roll g are uniform cubic B-splines over the pass's FRONT arc
              [phi_a, phi_b] (a first harmonic in beta is exactly an axis tilt; the higher
              terms are the gentle bends a friction-held cloth tape can take).
    connector the stretch between pass k's front arc and pass k+1's: pass k's own circle
              continued and pass k+1's circle run back, blended with a C2 smootherstep
              (the precession happens on the far side, where the winder turns the ball).
    order     the tape is laid in arc length s, so LATER IS ON TOP: at any point the
              covering stretch with the larger key lies over the smaller.  key = s,
              except on a TUCK - a stretch the winder threaded UNDER an earlier pass -
              whose key drops to just below that pass.  The reference's woven cycle
              (R_in > A > C > R_in's own lower end L5, REFERENCE_SPEC 4.4) is one tuck;
              the finishing end is the other (it is pushed under a pass, so the ball
              shows no free end - REFERENCE_SPEC 1 "Not present").
    lift      where tape lies on tape the upper one is one thickness higher.  layer(p)
              = the number of stretches under the one at p; lift is layer draped over
              buried edges (a tape bridges a buried edge over DRAPE_T thicknesses, it
              does not step - but its OWN edge is a true step, which is the crevice).

The first CORE_PASSES passes are the core (an evenly precessing yarn-ball winding): they
fill every point the outer passes leave open, so nothing anywhere is a void, and they carry
the gentle stack that makes the outline lumpy.  The last passes are FITTED to
REFERENCE_SPEC's 16+ visible bands from the reference camera (the fit and its scores live
in WorkFiles/smokebomb/rewind/wind/; the frozen numbers are in smokebomb_wind_fit).

FRAMES
------
Everything here is in the reference CAMERA frame (REFERENCE_SPEC 0): X right, Y up, Z toward
the camera, unit sphere (radius 1 = D / 2).  The Blender build frame (the reference view is
Blender's Front view: camera on -Y) is  X = Xc, Y = -Zc, Z = Yc  (``cam_to_build``).
Widths are carried in RADIANS of arc on the unit sphere (frac_D x 2).
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

#: the tape: REFERENCE_SPEC 4.2 widths are per band; the roll (a gathered, rolled stretch
#: such as W's twisted end) keeps this visible width (REFERENCE_SPEC 4.2 "W twisted": 0.010 D)
CORD_W = 0.010 * 2.0
#: a tape bridges a buried edge over this many thicknesses (SMOKEBOMB_STUDY 6: 2 mm = 4 t)
DRAPE_T = 4.0


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


# --------------------------------------------------------------------------- B-splines
def bspline_basis(x: np.ndarray, a: float, b: float, k: int) -> np.ndarray:
    """uniform cubic B-spline basis on [a, b] with k >= 4 coefficients -> (len(x), k).
    Outside [a, b] the end segment's cubic is clamped to its end value (flat)."""
    x = np.atleast_1d(np.asarray(x, np.float64))
    nseg = k - 3
    h = (b - a) / nseg
    t = np.clip((x - a) / h, 0.0, nseg)
    i = np.minimum(np.floor(t).astype(int), nseg - 1)
    u = t - i
    B = np.zeros((x.size, k))
    w0 = (1 - u) ** 3 / 6.0
    w1 = (3 * u ** 3 - 6 * u ** 2 + 4) / 6.0
    w2 = (-3 * u ** 3 + 3 * u ** 2 + 3 * u + 1) / 6.0
    w3 = u ** 3 / 6.0
    r = np.arange(x.size)
    B[r, i] = w0
    B[r, i + 1] = w1
    B[r, i + 2] = w2
    B[r, i + 3] = w3
    return B


def smootherstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)


# --------------------------------------------------------------------------- a pass
@dataclass(frozen=True)
class PassSpec:
    """One loop of the tape (see the module docstring).  Angles in DEGREES, widths in frac D."""
    name: str
    #: the REFERENCE_SPEC strips this pass shows (e.g. ("C", "B")); empty for a core pass
    shows: Tuple[str, ...]
    n: Tuple[float, float, float]
    e1: Tuple[float, float, float]
    phi_a: float
    phi_b: float
    beta: Tuple[float, ...]            # deg, B-spline coefficients over [phi_a, phi_b]
    width: Tuple[float, ...]           # frac D, B-spline coefficients
    roll: Tuple[float, ...] = ()       # 0 flat .. 1 rolled into a cord; B-spline coefficients
    role: str = "visible"              # "visible" | "core"
    note: str = ""

    def frame(self):
        n = normalize(np.array(self.n))
        e1 = normalize(np.array(self.e1) - np.dot(self.e1, n) * n)
        e2 = np.cross(n, e1)
        return e1, e2, n

    def _spl(self, coef, phi_deg, default=0.0):
        if not coef:
            return np.full(np.shape(np.atleast_1d(phi_deg)), default, np.float64)
        return bspline_basis(phi_deg, self.phi_a, self.phi_b, len(coef)) @ np.asarray(coef, np.float64)

    def beta_rad(self, phi_deg):
        return self._spl(self.beta, phi_deg) * DEG

    def width_rad(self, phi_deg):
        return self._spl(self.width, phi_deg) * 2.0

    def roll_at(self, phi_deg):
        return np.clip(self._spl(self.roll, phi_deg), 0.0, 1.0)

    def point(self, phi_deg, beta_rad=None) -> np.ndarray:
        e1, e2, n = self.frame()
        ph = np.atleast_1d(np.asarray(phi_deg, np.float64)) * DEG
        be = self.beta_rad(np.degrees(ph)) if beta_rad is None else np.broadcast_to(beta_rad, ph.shape)
        cb = np.cos(be)[:, None]
        return cb * (np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2) + np.sin(be)[:, None] * n

    def coords(self, p) -> Tuple[np.ndarray, np.ndarray]:
        """(phi deg, lam rad) of camera-frame unit vectors p in this pass's own frame."""
        e1, e2, n = self.frame()
        p = np.asarray(p, np.float64)
        return (np.degrees(np.arctan2(p @ e2, p @ e1)),
                np.arcsin(np.clip(p @ n, -1.0, 1.0)))


# --------------------------------------------------------------------------- the winding
@dataclass
class Tuck:
    """A stretch of pass ``pass_name`` (its own phi range, deg) threaded UNDER pass ``under``."""
    pass_name: str
    phi_from: float
    phi_to: float
    under: str
    why: str = ""


@dataclass
class Winding:
    """The sampled tape.  Arrays are indexed by sample i along the tape (uniform in s)."""
    s: np.ndarray            # arc length on the unit sphere (rad), 0 at the core end
    c: np.ndarray            # (N,3) centre, camera frame, unit
    t: np.ndarray            # (N,3) unit tangent (direction of laying)
    b: np.ndarray            # (N,3) unit across = c x t (left of travel)
    w: np.ndarray            # full width, rad of arc
    roll: np.ndarray         # 0 flat .. 1 rolled into a cord
    pass_idx: np.ndarray     # index into ``passes``
    phi: np.ndarray          # the pass's own phi (deg) on front arcs, NaN on connectors
    key: np.ndarray          # layer order key (s, dropped on a tuck)
    passes: List[PassSpec]
    tucks: List[Tuck]
    notes: Dict[str, object] = field(default_factory=dict)

    # ---------------------------------------------------------------- basic geometry
    @property
    def ds(self) -> float:
        return float(self.s[1] - self.s[0])

    def w_eff(self) -> np.ndarray:
        """the footprint width: a rolled stretch keeps only the cord's width."""
        return self.w * (1.0 - self.roll) + CORD_W * self.roll

    def edge(self, side: int, eff: bool = True) -> np.ndarray:
        """(N,3) edge line: side +1 = left of travel (+b), -1 = right."""
        hw = 0.5 * (self.w_eff() if eff else self.w)
        return normalize(np.cos(hw)[:, None] * self.c + side * np.sin(hw)[:, None] * self.b)

    def points(self, v: np.ndarray, eff: bool = True, idx=None) -> np.ndarray:
        """(len(idx), len(v), 3) points across the tape; v in [-1, 1] (-1 right edge, +1 left)."""
        idx = np.arange(self.s.size) if idx is None else np.asarray(idx)
        hw = 0.5 * (self.w_eff() if eff else self.w)[idx]
        a = hw[:, None] * np.asarray(v, np.float64)[None, :]
        return normalize(np.cos(a)[..., None] * self.c[idx, None, :] + np.sin(a)[..., None] * self.b[idx, None, :])

    def pass_slice(self, name: str) -> np.ndarray:
        k = [p.name for p in self.passes].index(name)
        return np.nonzero(self.pass_idx == k)[0]

    def geodesic_curvature(self) -> np.ndarray:
        """kappa_g = (dt/ds) . b  (0 on a great circle)."""
        dt = np.gradient(self.t, self.s, axis=0)
        return np.einsum("ij,ij->i", dt, self.b)

    # ---------------------------------------------------------------- layers
    def stack_grid(self, n_face: int = 512, dv: float = None, drop_roll: bool = False) -> "StackGrid":
        return StackGrid.build(self, n_face=n_face, dv=dv)


# --------------------------------------------------------------------------- cube-map stack
def _cube_index(p: np.ndarray, n: int) -> np.ndarray:
    """unit vectors -> flat cube-map cell index (6 * n * n cells)."""
    p = np.asarray(p, np.float64)
    ax = np.argmax(np.abs(p), axis=-1)
    sgn = np.take_along_axis(p, ax[..., None], -1)[..., 0] >= 0
    face = ax * 2 + (~sgn)
    m = np.abs(np.take_along_axis(p, ax[..., None], -1)[..., 0])
    # the two other coordinates, in a fixed order per axis
    oa = np.where(ax == 0, 1, 0)
    ob = np.where(ax == 2, 1, 2)
    ua = np.take_along_axis(p, oa[..., None], -1)[..., 0] / m
    ub = np.take_along_axis(p, ob[..., None], -1)[..., 0] / m
    # equi-angular cube map (cells ~ equal angle)
    ia = np.clip(((np.arctan(ua) / (math.pi / 4)) * 0.5 + 0.5) * n, 0, n - 1).astype(np.int64)
    ib = np.clip(((np.arctan(ub) / (math.pi / 4)) * 0.5 + 0.5) * n, 0, n - 1).astype(np.int64)
    return (face * n + ia) * n + ib


@dataclass
class StackGrid:
    """Per cube-map cell, the sorted keys of every tape stretch covering it."""
    n_face: int
    keys: np.ndarray        # (cells, M) float64 sorted ascending, +inf padded
    count: np.ndarray       # (cells,) int
    top_pass: np.ndarray    # (cells,) pass index of the top stretch (-1 = bare)
    key_to_pass: Tuple[np.ndarray, np.ndarray]   # (sorted keys, pass idx) lookup

    @staticmethod
    def build(wd: Winding, n_face: int = 512, dv: float = None) -> "StackGrid":
        cell = (math.pi / 2) / n_face
        step = 0.45 * cell if dv is None else dv
        ds = wd.ds
        # along-tape supersampling so sub-points are <= step apart
        sub_s = max(1, int(math.ceil(ds / step)))
        w_eff = wd.w_eff()
        cells_all, keys_all = [], []
        N = wd.s.size
        chunk = 4000
        for i0 in range(0, N - 1, chunk):
            i1 = min(N - 1, i0 + chunk)
            idx = np.arange(i0, i1)
            for js in range(sub_s):
                f = (js + 0.5) / sub_s
                c = normalize(wd.c[idx] * (1 - f) + wd.c[idx + 1] * f)
                bb = normalize(wd.b[idx] * (1 - f) + wd.b[idx + 1] * f)
                hw = 0.5 * (w_eff[idx] * (1 - f) + w_eff[idx + 1] * f)
                nv = np.maximum(2, np.ceil(2 * hw / step).astype(int) + 1)
                nvm = int(nv.max())
                vv = (np.arange(nvm)[None, :] + 0.5) / nv[:, None] * 2 - 1        # (n, nvm)
                ok = np.arange(nvm)[None, :] < nv[:, None]
                a = hw[:, None] * vv
                P = np.cos(a)[..., None] * c[:, None, :] + np.sin(a)[..., None] * bb[:, None, :]
                P = P[ok]
                K = np.broadcast_to(wd.key[idx][:, None], ok.shape)[ok]
                cells_all.append(_cube_index(P, n_face))
                keys_all.append(K)
        cells = np.concatenate(cells_all)
        keys = np.concatenate(keys_all)
        # one entry per (cell, stretch): a stretch = the key rounded to its sample
        kq = np.round(keys / ds).astype(np.int64)
        pair = np.unique(np.stack([cells, kq], 1), axis=0)
        # merge entries of the same stretch in a cell (neighbouring samples): keep one per
        # contiguous key run (a tape crossing a cell covers a few consecutive samples)
        order = np.lexsort((pair[:, 1], pair[:, 0]))
        pair = pair[order]
        newrun = np.ones(len(pair), bool)
        same_cell = pair[1:, 0] == pair[:-1, 0]
        close_key = (pair[1:, 1] - pair[:-1, 1]) <= max(3, int(3 * cell / ds) + 2)
        newrun[1:] = ~(same_cell & close_key)
        pair = pair[newrun]
        ncell = 6 * n_face * n_face
        cnt = np.bincount(pair[:, 0], minlength=ncell)
        M = int(cnt.max())
        start = np.zeros(ncell + 1, np.int64)
        start[1:] = np.cumsum(cnt)
        rank = np.arange(len(pair)) - start[pair[:, 0]]
        K = np.full((ncell, M), np.inf)
        K[pair[:, 0], rank] = pair[:, 1] * ds
        top = np.full(ncell, -1, np.int64)
        has = cnt > 0
        topkey = K[np.arange(ncell), np.maximum(cnt - 1, 0)]
        sk = np.argsort(wd.key)
        kp = (wd.key[sk], wd.pass_idx[sk])
        j = np.clip(np.searchsorted(kp[0], topkey[has] - 0.5 * ds), 0, len(sk) - 1)
        top[has] = kp[1][j]
        return StackGrid(n_face, K, cnt, top, kp)

    def cells(self, p) -> np.ndarray:
        return _cube_index(p, self.n_face)

    def below(self, p, key) -> np.ndarray:
        """number of tape stretches under a stretch with ``key`` at points p."""
        ci = self.cells(p)
        key = np.asarray(key, np.float64)
        tol = 3.0 * (math.pi / 2) / self.n_face
        return np.sum(self.keys[ci] < (key[..., None] - tol), axis=-1)

    def top_key(self, p) -> np.ndarray:
        ci = self.cells(p)
        c = self.count[ci]
        return np.where(c > 0, self.keys[ci, np.maximum(c - 1, 0)], -np.inf)

    def top(self, p) -> np.ndarray:
        return self.top_pass[self.cells(p)]


# --------------------------------------------------------------------------- assembly
def _connector(pa: PassSpec, pb: PassSpec, n_min: int = 64):
    """pass pa's circle continued past phi_b, blended into pass pb's circle run back from its
    phi_a.  Returns (points (m,3), width rad (m,), roll (m,)) excluding both end points."""
    ba = float(pa.beta_rad(pa.phi_b)[0])
    bb = float(pb.beta_rad(pb.phi_a)[0])
    wa = float(pa.width_rad(pa.phi_b)[0])
    wb = float(pb.width_rad(pb.phi_a)[0])
    ra = float(pa.roll_at(pa.phi_b)[0])
    rb = float(pb.roll_at(pb.phi_a)[0])
    u = np.linspace(0.0, 1.0, 97)
    h = smootherstep(u)
    best = None
    for La in np.arange(40.0, 330.0, 5.0):
        A = pa.point(pa.phi_b + u * La, ba)
        for Lb in np.arange(40.0, 330.0, 5.0):
            B = pb.point(pb.phi_a - (1 - u) * Lb, bb)
            d = np.sum((A - B) ** 2, axis=1)
            cost = float(np.mean(d * (h * (1 - h) * 4 + 0.05))) + 1e-4 * ((La - Lb) / 90.0) ** 2
            if best is None or cost < best[0]:
                best = (cost, La, Lb)
    _, La, Lb = best
    # refine
    for step in (2.0, 0.5):
        for dLa in np.arange(-4 * step, 4.01 * step, step):
            for dLb in np.arange(-4 * step, 4.01 * step, step):
                A = pa.point(pa.phi_b + u * (La + dLa), ba)
                B = pb.point(pb.phi_a - (1 - u) * (Lb + dLb), bb)
                d = np.sum((A - B) ** 2, axis=1)
                cost = float(np.mean(d * (h * (1 - h) * 4 + 0.05))) + 1e-4 * (((La + dLa) - (Lb + dLb)) / 90.0) ** 2
                if cost < best[0]:
                    best = (cost, La + dLa, Lb + dLb)
        _, La, Lb = best
    m = max(n_min, int(math.ceil(max(La, Lb) / 0.25)))
    u = np.linspace(0.0, 1.0, m + 2)[1:-1]
    h = smootherstep(u)
    A = pa.point(pa.phi_b + u * La, ba)
    B = pb.point(pb.phi_a - (1 - u) * Lb, bb)
    P = normalize((1 - h)[:, None] * A + h[:, None] * B)
    return P, (1 - h) * wa + h * wb, (1 - h) * ra + h * rb, dict(La=La, Lb=Lb, cost=best[0])


def assemble(passes: Sequence[PassSpec], tucks: Sequence[Tuck] = (), ds_deg: float = 0.2,
             dphi_deg: float = 0.25) -> Winding:
    """Chain the passes (front arcs + connectors) into one tape sampled uniformly in s."""
    pts, wid, rol, pid, phis = [], [], [], [], []
    conn_info = []
    for k, ps in enumerate(passes):
        nph = max(8, int(math.ceil((ps.phi_b - ps.phi_a) / dphi_deg)))
        ph = np.linspace(ps.phi_a, ps.phi_b, nph + 1)
        pts.append(ps.point(ph))
        wid.append(ps.width_rad(ph))
        rol.append(ps.roll_at(ph))
        pid.append(np.full(ph.size, k))
        phis.append(ph)
        if k + 1 < len(passes):
            P, W, Rr, info = _connector(ps, passes[k + 1])
            pts.append(P)
            wid.append(W)
            rol.append(Rr)
            pid.append(np.full(len(P), k))
            phis.append(np.full(len(P), np.nan))
            conn_info.append(dict(frm=ps.name, to=passes[k + 1].name, **info))
    P = np.concatenate(pts)
    Wd = np.concatenate(wid)
    Ro = np.concatenate(rol)
    Pi = np.concatenate(pid)
    Ph = np.concatenate(phis)
    # arc length, then uniform resampling
    seg = np.arccos(np.clip(np.einsum("ij,ij->i", P[1:], P[:-1]), -1, 1))
    keep = np.concatenate([[True], seg > 1e-9])
    P, Wd, Ro, Pi, Ph = P[keep], Wd[keep], Ro[keep], Pi[keep], Ph[keep]
    seg = np.arccos(np.clip(np.einsum("ij,ij->i", P[1:], P[:-1]), -1, 1))
    s0 = np.concatenate([[0.0], np.cumsum(seg)])
    ds = ds_deg * DEG
    s = np.arange(0.0, s0[-1], ds)
    j = np.clip(np.searchsorted(s0, s, side="right") - 1, 0, len(s0) - 2)
    f = ((s - s0[j]) / np.maximum(s0[j + 1] - s0[j], 1e-12))
    c = normalize(P[j] * (1 - f)[:, None] + P[j + 1] * f[:, None])
    w = Wd[j] * (1 - f) + Wd[j + 1] * f
    ro = Ro[j] * (1 - f) + Ro[j + 1] * f
    pi = np.where(f < 0.5, Pi[j], Pi[j + 1])
    ph = np.where(np.isnan(Ph[j]) | np.isnan(Ph[j + 1]), np.nan, Ph[j] * (1 - f) + Ph[j + 1] * f)
    # tangent by central differences, projected to the tangent plane
    t = np.gradient(c, axis=0)
    t = normalize(t - np.einsum("ij,ij->i", t, c)[:, None] * c)
    b = normalize(np.cross(c, t))
    key = s.copy()
    wd = Winding(s=s, c=c, t=t, b=b, w=w, roll=ro, pass_idx=pi, phi=ph, key=key,
                 passes=list(passes), tucks=list(tucks), notes={"connectors": conn_info})
    apply_tucks(wd)
    return wd


def apply_tucks(wd: Winding) -> None:
    names = [p.name for p in wd.passes]
    for tk in wd.tucks:
        k = names.index(tk.pass_name)
        ku = names.index(tk.under)
        sel = (wd.pass_idx == k) & (wd.phi >= tk.phi_from) & (wd.phi <= tk.phi_to)
        if not np.any(sel):
            raise ValueError(f"tuck {tk} selects no samples")
        s_under = wd.s[wd.pass_idx == ku].min()
        # just below the pass it is threaded under, above everything laid before that pass
        wd.key[sel] = s_under - 0.5 * wd.ds * (1.0 + np.linspace(0, 1, int(sel.sum())) * 1e-3)


# --------------------------------------------------------------------------- core passes
def core_passes(n: int, first_axis: np.ndarray, seed_turn_deg: float = 137.508,
                tilt_deg: float = 62.0, width_frac_d: float = 0.16) -> List[PassSpec]:
    """An evenly precessing yarn-ball core: axis k is ``first_axis`` tilted by tilt_deg and
    turned seed_turn_deg * k about it; plain great circles of constant width."""
    fa = normalize(first_axis)
    ref = normalize(np.cross(fa, [0.3, 0.2, 0.93]))
    out = []
    for k in range(n):
        ax = rot_about(fa, k * seed_turn_deg * DEG) @ (rot_about(ref, tilt_deg * DEG) @ fa)
        e1 = normalize(np.cross(ax, [0.0, 0.0, 1.0]) if abs(ax[2]) < 0.99 else np.array([1.0, 0, 0]))
        e1 = normalize(np.cross(e1, ax))     # a point on the circle
        out.append(PassSpec(name=f"core{k:02d}", shows=(), n=tuple(ax), e1=tuple(e1),
                            phi_a=-90.0, phi_b=90.0, beta=(0.0,) * 4, width=(width_frac_d,) * 4,
                            role="core", note="core winding (hidden by the outer passes)"))
    return out


__all__ = ["DEG", "REF_SIZE_PX", "REF_CENTRE_PX", "REF_RADIUS_PX", "TOP_WHORL", "BOTTOM_WHORL",
           "CORD_W", "DRAPE_T", "cam_to_build", "build_to_cam", "normalize", "latlon", "img_to_cam",
           "cam_to_img", "image_angle_deg", "rot_about", "bspline_basis", "smootherstep", "PassSpec",
           "Tuck", "Winding", "StackGrid", "assemble", "apply_tucks", "core_passes"]
