#!/usr/bin/env python
"""props_lib.fan_fold - the folding fan's mechanism: where every stick and every leaf face is at any
openness, and the instruments that prove the fold (numpy only; runs without bpy).

THE MODEL (FAN_REPORT.md 3 has the derivation and the alternatives that were measured and dropped)

* Openness ``s``: 0 = closed, 1 = the bind pose (fan2's 163.2 deg).  Stick ``i`` turns about the rivet
  axis (Z) only; ``FanSpec.stick_axis_deg`` gives its angle.  The front guard ``stick_00`` never moves.
* The leaf is 50 rigid faces.  Face ``2i`` spans leaf line ``i`` (on stick ``i``) to mid-gap fold ``i``,
  face ``2i+1`` spans mid-gap fold ``i`` to leaf line ``i+1``.  Each face is one bone, weight 1.0.
* Leaf lines are horizontal radial lines at their stick's level ``z_i`` (FanSpec.leaf_line_z), so the
  25 gaps are identical up to a turn about Z and a step down in Z: every gap folds the same way at the
  same moment.  ONE gap is solved per openness and copied to the other 24 by that symmetry.
* Bind (open) pose: a mid-gap fold is the unstacked single-vertex solution (elevation gamma, FanSpec) run
  through the axis point half way between its two leaf lines, BELOW them (``MID_SIGN``): the leaf lines
  on the ribs are the mountains seen from the front and the mid-gap folds the valleys, as fan2 measures.
* Stacked sticks make an exact rigid fold impossible (the leaf lines do not meet in one point; the
  report shows why), so at each openness the two faces of a gap are the rigid placements that best
  keep them on their leaf lines and on each other (least squares, 12 unknowns, continued from the
  open pose so the pleat keeps its valley-away-from-the-viewer side all the way down).  What is left over
  is a crack between a face and its neighbour or its rib: ``crack_mm``; the gate is 0.1 mm.
* Near closed the pleats stop being fins and lie down as pages (the rib points of a gap are then
  separated mostly in Z); with the valleys toward -Z and the leaf stepping DOWN from the front guard,
  every page lies to the -angle side of the leaf lines (under the front guard's side), so the closed leaf
  is one neat stack of pages beside the stick stack.

INSTRUMENTS: triangle-triangle intersection (separating axis), point-to-segment distances, dihedral
angles.  ``verify_pose`` runs them on posed meshes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .fan_spec import D2R, FAN, FanSpec

#: +1: the mid-gap folds rise toward the viewer (round 1); -1: they fall away (round 2, fan2 measured: the
#: ribs carry the mountains, the mid-gap folds are the sharp valleys)
MID_SIGN = -1.0


# =========================================================================== small linear algebra
def rotz(deg: float) -> np.ndarray:
    a = deg * D2R
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4)
    m[:2, :2] = [[c, -s], [s, c]]
    return m


def translate(v) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = v
    return m


def rotvec(w: np.ndarray) -> np.ndarray:
    th = float(np.linalg.norm(w))
    if th < 1e-15:
        return np.eye(3)
    k = w / th
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(th) * K + (1.0 - math.cos(th)) * (K @ K)


def apply(T: np.ndarray, P: np.ndarray) -> np.ndarray:
    P = np.asarray(P, np.float64)
    return P @ T[:3, :3].T + T[:3, 3]


def rigid(R: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    """p -> R (p - c) + c + d as a 4x4."""
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = c + d - R @ c
    return T


# =========================================================================== bind geometry
@dataclass
class LeafTemplate:
    """Bind geometry of the leaf's fold lines (the vertex positions every LOD uses)."""
    rib_pts: np.ndarray    # (26, 2, 3): leaf line i at [inner, outer] (radii r_in, r_out; the scallop is fan_geom's)
    mid_pts: np.ndarray    # (25, 2, 3): mid-gap fold i at [inner, outer] (horizontal radii r_in, r_out)
    lam_deg: np.ndarray    # (26,) bind leaf-line angles
    z: np.ndarray          # (26,) leaf-line levels


def bind_template(spec: FanSpec = FAN, mid_offsets: Optional[np.ndarray] = None) -> LeafTemplate:
    """``mid_offsets`` (2, 2): the optimised (radial, z) shift of every gap's inner and outer mid-gap
    fold points (``optimise_bind``); the fold's angle is always re-solved for equal face widths."""
    n = spec.n_sticks
    lam = np.array([spec.leaf_line_deg(i, 1.0) for i in range(n)])
    z = np.array([spec.leaf_line_z(i) for i in range(n)])
    # the fold lines end at r_in and r_out: the scallop (bumps at the mountains, notches at the valleys) is
    # fan_geom's, as vertices ALONG these lines, so tuning it never changes the mechanism
    rib = np.zeros((n, 2, 3))
    for i in range(n):
        u = np.array([math.cos(lam[i] * D2R), math.sin(lam[i] * D2R), 0.0])
        rib[i, 0] = spec.r_in * u + [0, 0, z[i]]
        rib[i, 1] = spec.r_out * u + [0, 0, z[i]]
    g = MID_SIGN * spec.gamma_deg * D2R                              # the mid-gap folds are valleys (-Z)
    mid = np.zeros((n - 1, 2, 3))
    for i in range(n - 1):
        mu = 0.5 * (lam[i] + lam[i + 1]) * D2R
        v = np.array([math.cos(g) * math.cos(mu), math.cos(g) * math.sin(mu), math.sin(g)])
        c = np.array([0.0, 0.0, 0.5 * (z[i] + z[i + 1])])
        for k, rr in enumerate((spec.r_in, spec.r_out)):
            p = c + v * (rr / math.cos(g))
            if mid_offsets is not None:
                # (radial, z) shift of gap 0's fold point, turned with the gap; the equidistance below
                # then fixes its angle, so the two faces of every gap stay the same width
                d_r, d_z = np.asarray(mid_offsets, np.float64)[k]
                p = p + np.array([math.cos(mu) * d_r, math.sin(mu) * d_r, d_z])
            mid[i, k] = _equidistant(p, rib[i, 0], rib[i, 1], rib[i + 1, 0], rib[i + 1, 1])
    return LeafTemplate(rib, mid, lam, z)


def _line_dist(p, a, b):
    u = (b - a) / np.linalg.norm(b - a)
    w = p - a
    return float(np.linalg.norm(w - (w @ u) * u))


def _equidistant(p, a0, a1, b0, b1):
    """Turn p about Z (a few hundredths of a degree) until it is equally far from both leaf lines.

    The two faces of a gap then have the same width at every radius, so when the gap closes (its
    leaf lines parallel, one pitch apart in Z) the fold can lie on the plane half way between them:
    the closed leaf is a flat stack of pages, not a leaning one.  Without it the lower face is the
    wider (its leaf line is one pitch further below the fold) and the closed pages stand at 22 deg."""
    def f(e):
        q = apply(rotz(e), p[None])[0]
        return _line_dist(q, a0, a1) - _line_dist(q, b0, b1)
    lo, hi = -1.0, 1.0
    flo = f(lo)
    for _ in range(80):
        m = 0.5 * (lo + hi)
        fm = f(m)
        if (fm < 0) == (flo < 0):
            lo, flo = m, fm
        else:
            hi = m
    return apply(rotz(0.5 * (lo + hi)), p[None])[0]


# =========================================================================== the solver
@dataclass
class GapSolution:
    s: float
    TA: np.ndarray         # face 0 (leaf line 0 -> mid 0), bind -> posed, 4x4
    TB: np.ndarray         # face 1 (mid 0 -> leaf line 1)
    x: np.ndarray          # the 12 unknowns
    crack_mm: Dict[str, float]


class FoldSolver:
    """Solves gap 0 at any openness, copies it to the 25 gaps, and re-fits the two end faces onto the
    glued flaps.

    Objective per openness (least squares over the two rigid faces of gap 0):
      rib fold  face A's copy of leaf line 0 against the PREVIOUS gap's face B copy of the same line
                (the symmetry maps gap 0's face B onto gap -1's), weight 1
      mid fold  face A's copy of the mid-gap fold against face B's, weight 1
      anchor    each face's leaf-line copy against the stick's leaf line, weight ``w_anchor`` (the leaf
                stays glued to its ribs; the cracks between faces are what the eye would see)"""

    def __init__(self, spec: FanSpec = FAN, mid_offsets: Optional[np.ndarray] = None, w_anchor: float = 0.15):
        self.spec = spec
        self.mid_offsets = None if mid_offsets is None else np.asarray(mid_offsets, np.float64).reshape(2, 2)
        self.tpl = bind_template(spec, self.mid_offsets)
        self.w_anchor = float(w_anchor)
        t = self.tpl
        self.A_rib = t.rib_pts[0].copy()
        self.A_mid = t.mid_pts[0].copy()
        self.B_mid = t.mid_pts[0].copy()
        self.B_rib = t.rib_pts[1].copy()
        self.cA = np.vstack([self.A_rib, self.A_mid]).mean(0)
        self.cB = np.vstack([self.B_mid, self.B_rib]).mean(0)
        self._cache: Dict[float, GapSolution] = {}
        self._s = 1.0

    # -- the stick / leaf line placements
    def stick_T(self, i: int, s: float) -> np.ndarray:
        sp = self.spec
        return rotz(sp.stick_axis_deg(i, s) - sp.stick_axis_deg(i, 1.0))

    def line_T(self, i: int, s: float) -> np.ndarray:
        """bind -> posed for leaf line i (equal to stick i's placement)."""
        return self.stick_T(i, s)

    def _targets(self, s: float):
        return apply(self.line_T(0, s), self.A_rib), apply(self.line_T(1, s), self.B_rib)

    def _faces(self, x):
        TA = rigid(rotvec(x[0:3]), self.cA, x[3:6])
        TB = rigid(rotvec(x[6:9]), self.cB, x[9:12])
        return TA, TB

    def _residual(self, x, tA, tB):
        TA, TB = self._faces(x)
        G = self.symmetry(1, self._s)
        a_rib = apply(TA, self.A_rib)
        b_rib = apply(TB, self.B_rib)
        b_prev = apply(np.linalg.inv(G), b_rib)
        w = self.w_anchor
        return np.concatenate([(a_rib - b_prev).ravel(), (apply(TA, self.A_mid) - apply(TB, self.B_mid)).ravel(),
                               w * (a_rib - tA).ravel(), w * (b_rib - tB).ravel()])

    @staticmethod
    def _lm(fun, x0, n, iters=200):
        x = np.array(x0, np.float64)
        lam = 1e-6
        r = fun(x)
        f = float(r @ r)
        for _ in range(iters):
            J = np.empty((r.size, n))
            for k in range(n):
                d = np.zeros(n)
                h = 1e-7 if k % 6 < 3 else 1e-6
                d[k] = h
                J[:, k] = (fun(x + d) - r) / h
            A = J.T @ J
            g = J.T @ r
            step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), -g)
            xn = x + step
            rn = fun(xn)
            fn = float(rn @ rn)
            if fn < f:
                x, r, f = xn, rn, fn
                lam = max(lam * 0.3, 1e-12)
                if np.abs(step).max() < 1e-12:
                    break
            else:
                lam *= 10.0
                if lam > 1e8:
                    break
        return x, r

    def _solve(self, s: float, x0: np.ndarray) -> GapSolution:
        self._s = s
        tA, tB = self._targets(s)
        x, r = self._lm(lambda v: self._residual(v, tA, tB), x0, 12)
        rr = r.reshape(-1, 3)
        d = np.linalg.norm(rr, axis=1)
        crack = {"rib_fold_mm": float(d[0:2].max()), "mid_fold_mm": float(d[2:4].max()),
                 "off_rib_mm": float(d[4:8].max() / max(self.w_anchor, 1e-12))}
        TA, TB = self._faces(x)
        return GapSolution(s, TA, TB, x, crack)

    def solve(self, s: float) -> GapSolution:
        """Continuation from the open pose: never jumps to the other (mirror) branch."""
        s = float(min(1.0, max(0.0, s)))
        key = round(s, 9)
        if key in self._cache:
            return self._cache[key]
        if not self._cache:
            self._cache[1.0] = self._solve(1.0, np.zeros(12))
        best = min(self._cache.values(), key=lambda g: abs(g.s - s))
        cur = best
        span = s - best.s
        steps = max(1, int(math.ceil(abs(span) / self._step_limit(min(s, best.s)))))
        for k in range(1, steps + 1):
            sk = best.s + span * k / steps
            cur = self._solve(sk, cur.x)
            self._cache[round(sk, 9)] = cur
        return cur

    @staticmethod
    def _step_limit(s_lo: float) -> float:
        # the pleats swing fastest in the last few per cent (fins -> pages): walk finely there
        if s_lo < 0.02:
            return 0.001
        if s_lo < 0.1:
            return 0.005
        return 0.02

    # -- every face
    def symmetry(self, i: int, s: float) -> np.ndarray:
        """gap 0 -> gap i at openness s."""
        sp = self.spec
        return translate([0, 0, self.tpl.z[i] - self.tpl.z[0]]) @ rotz(sp.leaf_line_deg(i, s) - sp.leaf_line_deg(0, s))

    def _end_fit(self, T0, rib_bind, rib_target, mid_bind, mid_target):
        """Re-fit one end face: its leaf-line copy onto the glued flap's edge (the guard's line), its
        mid copy onto the neighbour's; both weight 1.  A small rigid correction of the symmetric
        solution about the face's posed centroid."""
        c = apply(T0, np.vstack([rib_bind, mid_bind])).mean(0)

        def fun(v):
            T = rigid(rotvec(v[0:3]), c, v[3:6]) @ T0
            return np.concatenate([(apply(T, rib_bind) - rib_target).ravel(), (apply(T, mid_bind) - mid_target).ravel()])
        v, _ = self._lm(fun, np.zeros(6), 6, iters=60)
        return rigid(rotvec(v[0:3]), c, v[3:6]) @ T0

    def face_T(self, s: float) -> List[np.ndarray]:
        g = self.solve(s)
        n = self.spec.n_sticks
        out = []
        for i in range(n - 1):
            Si, Si1 = self.symmetry(i, s), self.symmetry(i, 1.0)
            Sinv = np.linalg.inv(Si1)
            out.append(Si @ g.TA @ Sinv)
            out.append(Si @ g.TB @ Sinv)
        t = self.tpl
        # face 0 onto the front flap's edge (leaf line 0, fixed with the front guard)
        out[0] = self._end_fit(out[0], t.rib_pts[0], apply(self.line_T(0, s), t.rib_pts[0]),
                               t.mid_pts[0], apply(out[1], t.mid_pts[0]))
        # face 49 onto the rear flap's edge (leaf line 25, on the rear guard)
        out[-1] = self._end_fit(out[-1], t.rib_pts[n - 1], apply(self.line_T(n - 1, s), t.rib_pts[n - 1]),
                                t.mid_pts[n - 2], apply(out[-2], t.mid_pts[n - 2]))
        return out

    def page_tilt_deg(self, s: float = 0.0) -> float:
        """How far the closed pleats lean out of the fan plane: the angle of gap 0's mid-gap fold (outer
        and inner point) above the horizontal, seen from its two leaf lines' midpoint."""
        g = self.solve(s)
        worst = 0.0
        for k in range(2):
            m = apply(g.TA, self.A_mid[k:k + 1])[0]
            a = apply(self.line_T(0, s), self.A_rib[k:k + 1])[0]
            b = apply(self.line_T(1, s), self.B_rib[k:k + 1])[0]
            c = 0.5 * (a + b)
            v = m - c
            worst = max(worst, abs(math.degrees(math.atan2(v[2], math.hypot(v[0], v[1]) if False else
                                                          np.linalg.norm(v[:2] - (v[:2] @ (a[:2] / np.linalg.norm(a[:2])))
                                                                         * (a[:2] / np.linalg.norm(a[:2])))))))
        return worst

    def sticks_T(self, s: float) -> List[np.ndarray]:
        return [self.stick_T(i, s) for i in range(self.spec.n_sticks)]

    def cracks(self, s: float, faces: Optional[List[np.ndarray]] = None) -> Dict[str, float]:
        """Every fold line's copies, posed: the worst distance between two copies of one vertex (rib fold =
        a leaf line incl. the flap's edge, mid fold = a mid-gap fold), and the leaf's worst distance from
        its ribs' lines."""
        F = faces if faces is not None else self.face_T(s)
        t = self.tpl
        n = self.spec.n_sticks
        rib_f = mid_f = off = 0.0
        for k in range(n):
            copies = []
            if k > 0:
                copies.append(apply(F[2 * k - 1], t.rib_pts[k]))
            if k < n - 1:
                copies.append(apply(F[2 * k], t.rib_pts[k]))
            line = apply(self.line_T(k, s), t.rib_pts[k])
            if k in (0, n - 1):
                copies.append(line)                      # the glued flap's edge IS the line
            for a in range(len(copies)):
                off = max(off, float(np.linalg.norm(copies[a] - line, axis=1).max()))
                for b in range(a + 1, len(copies)):
                    rib_f = max(rib_f, float(np.linalg.norm(copies[a] - copies[b], axis=1).max()))
        for i in range(n - 1):
            a = apply(F[2 * i], t.mid_pts[i])
            b = apply(F[2 * i + 1], t.mid_pts[i])
            mid_f = max(mid_f, float(np.linalg.norm(a - b, axis=1).max()))
        return {"rib_fold_mm": rib_f, "mid_fold_mm": mid_f, "leaf_off_rib_mm": off,
                "worst_mm": max(rib_f, mid_f)}


OFFSET_LIMIT_MM = 0.6


def bind_cache_key(spec: FanSpec = FAN) -> str:
    """What the optimised bind depends on: the fold-relevant spec numbers and the solver's source."""
    import hashlib
    import json
    from pathlib import Path
    fields = [spec.n_sticks, spec.opening_deg, spec.leaf_off_front_deg, spec.leaf_off_rear_deg, MID_SIGN,
              round(spec.front_gap_mm, 9), spec.leaf_in_L, spec.leaf_out_L,
              spec.face_tilt_deg, spec.rib_thick_mm, spec.guard_thick_mm, spec.leaf_on_rib_mm,
              spec.L, round(spec.leaf_z_pitch, 9), OFFSET_LIMIT_MM, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    return hashlib.sha256(json.dumps(fields).encode()).hexdigest()[:16]


def optimise_bind(spec: FanSpec = FAN, iters: int = 150, samples=(0.6, 0.3, 0.0), log=None):
    """Nelder-Mead over gap 0's two mid-gap fold points (6 numbers, mm) minimising the worst crack at
    ``samples`` (continued from the open pose each time).  Deterministic.  The shift it finds is a
    few tenths of a millimetre; it removes the first-order part of the stacked leaf's inconsistency
    (the crack drops several times)."""
    def shift(p):
        # bounded: a fold point may move at most OFFSET_LIMIT_MM (radially and in Z) - the shape of the
        # leaf (its radii, its scallop, its pleat depth) must not change; unbounded, the search collapses
        # the mid-gap folds to points
        return OFFSET_LIMIT_MM * np.tanh(np.asarray(p, np.float64))

    def obj(p):
        fs = FoldSolver(spec, shift(p).reshape(2, 2))
        worst = 0.0
        for s in samples:
            g = fs.solve(s)
            worst = max(worst, g.crack_mm["rib_fold_mm"], g.crack_mm["mid_fold_mm"])
        # the closed leaf must be a flat stack of pages: penalise any lean past 6 deg
        return worst + 0.01 * max(0.0, fs.page_tilt_deg(0.0) - 6.0)
    n = 4
    X = [np.zeros(n)] + [np.eye(n)[k] * 0.8 for k in range(n)]
    Fv = [obj(x) for x in X]
    f0 = Fv[0]
    for it in range(iters):
        o = np.argsort(Fv)
        X = [X[k] for k in o]
        Fv = [Fv[k] for k in o]
        c = np.mean(X[:-1], 0)
        xr = c + (c - X[-1])
        fr = obj(xr)
        if fr < Fv[0]:
            xe = c + 2 * (c - X[-1])
            fe = obj(xe)
            X[-1], Fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < Fv[-2]:
            X[-1], Fv[-1] = xr, fr
        else:
            xc = c + 0.5 * (X[-1] - c)
            fc = obj(xc)
            if fc < Fv[-1]:
                X[-1], Fv[-1] = xc, fc
            else:
                X = [X[0]] + [X[0] + 0.5 * (x - X[0]) for x in X[1:]]
                Fv = [Fv[0]] + [obj(x) for x in X[1:]]
        if log and it % 25 == 0:
            log(f"    bind optimisation {it}: worst crack {min(Fv):.5f} mm")
    k = int(np.argmin(Fv))
    off = shift(X[k]).reshape(2, 2)
    return off, {"iterations": iters, "worst_before_mm": float(f0), "worst_after_mm": float(Fv[k]),
                 "samples": list(samples), "offset_limit_mm": OFFSET_LIMIT_MM,
                 "offsets_radial_z_mm": np.round(off, 6).tolist()}


# =========================================================================== instruments
def tri_tri_intersect(A: np.ndarray, B: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    """Vectorised separating-axis test.  A, B: (N, 3, 3) triangle pairs.  True where they intersect
    (touching within eps counts as NOT intersecting)."""
    A = np.asarray(A, np.float64)
    B = np.asarray(B, np.float64)
    n = A.shape[0]
    hit = np.ones(n, bool)
    eA = [A[:, 1] - A[:, 0], A[:, 2] - A[:, 1], A[:, 0] - A[:, 2]]
    eB = [B[:, 1] - B[:, 0], B[:, 2] - B[:, 1], B[:, 0] - B[:, 2]]
    nA = np.cross(eA[0], -eA[2])
    nB = np.cross(eB[0], -eB[2])
    axes = [nA, nB] + [np.cross(a, b) for a in eA for b in eB]
    for ax in axes:
        L = np.linalg.norm(ax, axis=1)
        ok = L > 1e-12
        u = np.where(ok[:, None], ax / np.maximum(L, 1e-300)[:, None], 0.0)
        pa = np.einsum("nij,nj->ni", A, u)
        pb = np.einsum("nij,nj->ni", B, u)
        sep = (pa.max(1) < pb.min(1) + eps) | (pb.max(1) < pa.min(1) + eps)
        hit &= ~(sep & ok)
    return hit


def pairs_by_aabb(TA: np.ndarray, TB: np.ndarray, pad: float = 0.0, same: bool = False):
    """Candidate pairs (ia, ib) whose AABBs overlap."""
    loA, hiA = TA.min(1) - pad, TA.max(1) + pad
    loB, hiB = TB.min(1) - pad, TB.max(1) + pad
    out_a, out_b = [], []
    step = 512
    for s0 in range(0, len(TA), step):
        la, ha = loA[s0:s0 + step, None, :], hiA[s0:s0 + step, None, :]
        ov = np.all((la <= hiB[None]) & (loB[None] <= ha), axis=2)
        ia, ib = np.nonzero(ov)
        ia = ia + s0
        if same:
            k = ia < ib
            ia, ib = ia[k], ib[k]
        out_a.append(ia)
        out_b.append(ib)
    return np.concatenate(out_a), np.concatenate(out_b)


def count_intersections(TA: np.ndarray, TB: np.ndarray, same: bool = False, exclude=None) -> Tuple[int, List]:
    ia, ib = pairs_by_aabb(TA, TB, same=same)
    if exclude is not None and len(ia):
        keep = ~exclude(ia, ib)
        ia, ib = ia[keep], ib[keep]
    if not len(ia):
        return 0, []
    hit = tri_tri_intersect(TA[ia], TB[ib])
    idx = np.nonzero(hit)[0]
    return int(len(idx)), [(int(ia[k]), int(ib[k])) for k in idx[:20]]


def dihedral_deg(p0, p1, qa, qb) -> np.ndarray:
    """Interior angle at edge p0-p1 between the half-planes through qa and qb (0 = folded flat onto
    each other, 180 = flat)."""
    e = p1 - p0
    e = e / np.linalg.norm(e, axis=-1, keepdims=True)
    va = qa - p0
    vb = qb - p0
    va = va - (va * e).sum(-1, keepdims=True) * e
    vb = vb - (vb * e).sum(-1, keepdims=True) * e
    va /= np.linalg.norm(va, axis=-1, keepdims=True)
    vb /= np.linalg.norm(vb, axis=-1, keepdims=True)
    return np.degrees(np.arccos(np.clip((va * vb).sum(-1), -1, 1)))


__all__ = ["FoldSolver", "optimise_bind", "LeafTemplate", "bind_template", "rotz", "translate", "apply", "rotvec", "rigid",
           "tri_tri_intersect", "pairs_by_aabb", "count_intersections", "dihedral_deg"]
