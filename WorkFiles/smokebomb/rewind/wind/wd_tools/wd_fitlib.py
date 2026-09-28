"""wd_fitlib - fit the smoke bomb's visible passes to REFERENCE_SPEC (numbers only).

Reads WorkFiles/smokebomb/reference_metrology/reference_spec.json (the spec's machine twin:
control points of every traced edge).  Never reads the reference pixels.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
from props_lib import smokebomb_wind as W  # noqa: E402

SPEC_PATH = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology/reference_spec.json"
SPEC = json.load(open(SPEC_PATH))
CX, CY = W.REF_CENTRE_PX
RPX = W.REF_RADIUS_PX
DEG = W.DEG

EDGES_PX: Dict[str, np.ndarray] = {}
for _s in SPEC["strips"]:
    for _e, _v in _s.get("edge_control_points", {}).items():
        EDGES_PX.setdefault(_e, np.array(_v["control_img"], float))


def px2cam(p) -> np.ndarray:
    p = np.asarray(p, float).reshape(-1, 2)
    x = (p[:, 0] - CX) / RPX
    y = -(p[:, 1] - CY) / RPX
    r2 = np.clip(x * x + y * y, 0, 0.99995)
    return np.stack([x, y, np.sqrt(1 - r2)], 1)


def cam2px(v) -> np.ndarray:
    v = np.asarray(v, float)
    return np.stack([CX + RPX * v[..., 0], CY - RPX * v[..., 1]], -1)


def resample_poly(P: np.ndarray, step: float = 6.0) -> np.ndarray:
    """polyline (image px) resampled every ``step`` px (a smooth Catmull-Rom through the
    control points, so the fit sees the traced curve, not its chords)."""
    P = np.asarray(P, float)
    if len(P) < 2:
        return P
    # Catmull-Rom
    ext = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(2, int(np.ceil(np.linalg.norm(p2 - p1) / step)))
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1:])
    return np.vstack(out)


def edge_px(name: str, xr=None, yr=None, step: float = 6.0, frac=None) -> np.ndarray:
    P = resample_poly(EDGES_PX[name], step)
    if frac is not None:
        n = len(P)
        P = P[int(frac[0] * (n - 1)):int(math.ceil(frac[1] * (n - 1))) + 1]
    if xr is not None:
        P = P[(P[:, 0] >= xr[0]) & (P[:, 0] <= xr[1])]
    if yr is not None:
        P = P[(P[:, 1] >= yr[0]) & (P[:, 1] <= yr[1])]
    return P


def to_limb_px(P: np.ndarray, r_frac: float = 0.992) -> np.ndarray:
    d = np.asarray(P, float) - [CX, CY]
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    return np.array([CX, CY]) + d * RPX * r_frac


# --------------------------------------------------------------------------- the fit
@dataclass
class EdgeTerm:
    """points (image px) the pass's edge on ``side`` (+1 left of travel, -1 right, 0 the
    centre line) must pass through, with a weight.  kind 'own' = a visible edge of this pass;
    'hide' = a hidden edge that must lie under the covering band (soft)."""
    pts: np.ndarray
    side: int
    weight: float = 1.0
    kind: str = "own"
    label: str = ""
    cam: Optional[np.ndarray] = None       # camera-frame unit points (overrides pts; may lie behind a limb)

    def P(self) -> np.ndarray:
        return np.asarray(self.cam, float) if self.cam is not None else px2cam(self.pts)


@dataclass
class PassFit:
    name: str
    shows: Tuple[str, ...]
    start_px: Tuple[float, float]          # travel direction hint: from ...
    end_px: Tuple[float, float]            # ... to
    terms: List[EdgeTerm]
    width: float                           # prior, frac D
    width_w: float = 0.15                  # prior weight
    knot_deg: float = 8.0
    smooth: float = 0.5
    beta_prior: float = 0.02
    phi_pad: float = 7.0                   # arc beyond each limb crossing (deg)
    gather: Optional[Tuple[Tuple[float, float], ...]] = None   # (px along -> g) as (phi from px pts)
    gather_px: Optional[List[Tuple[Tuple[float, float], float]]] = None
    axis: Optional[Tuple[float, float, float]] = None          # force the frame's axis
    phi_range: Optional[Tuple[float, float]] = None
    note: str = ""
    role: str = "visible"
    max_strain: float = 0.03               # edge strain budget on the front arc (1 = 100 %)
    strain_w: float = 150.0                # weight of the strain hinge in the refinement
    visible_strain: float = 1.0            # budget where the reference shows the band (its edges rule)
    width_d1: float = 0.3                  # penalty on width change per knot


def pass_strain(ps: W.PassSpec, front_only: bool = True):
    """max |kappa_g| x half footprint width along the pass's arc (front part by default)."""
    ph = np.linspace(ps.phi_a, ps.phi_b, 800)
    P = ps.point(ph)
    d = np.radians(ph[1] - ph[0])
    T = np.gradient(P, d, axis=0)
    sp = np.linalg.norm(T, axis=1)
    T = T / sp[:, None]
    dT = np.gradient(T, d, axis=0) / sp[:, None]
    kg = np.einsum("ij,ij->i", dT, np.cross(P, T))
    hw = 0.5 * (ps.width_rad(ph) * (1 - ps.gather_at(ph)) + W.CORD_W * ps.gather_at(ph))
    st = np.abs(kg) * hw
    m = P[:, 2] > -0.05 if front_only else np.ones(len(P), bool)
    m[:3] = m[-3:] = False
    return float(st[m].max()) if m.any() else 0.0, kg, ph


CACHE_DIR = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_cache"


def _pf_key(pf: PassFit) -> str:
    import hashlib
    h = hashlib.sha1()
    import dataclasses as _dc
    h.update(repr([(f.name, getattr(pf, f.name)) for f in _dc.fields(pf) if f.name != "terms"]).encode())
    for t in pf.terms:
        h.update(np.round(np.asarray(t.pts, float), 3).tobytes())
        if getattr(t, 'cam', None) is not None:
            h.update(np.round(np.asarray(t.cam, float), 9).tobytes())
        h.update(repr((t.side, t.weight, t.kind)).encode())
    import inspect
    h.update(inspect.getsource(refine_pass).encode())
    h.update(inspect.getsource(_fit_pass).encode())
    h.update(inspect.getsource(true_offsets).encode())
    h.update(inspect.getsource(_fit_pass_nocache).encode())
    h.update(inspect.getsource(W.PassSpec).encode())
    h.update(inspect.getsource(_centre_and_normal).encode())
    return h.hexdigest()[:20]


def fit_pass(pf: PassFit, verbose: bool = False) -> W.PassSpec:
    """linear least squares, then the true-normal LM refinement (cached on disk)."""
    import os, pickle
    os.makedirs(CACHE_DIR, exist_ok=True)
    fn = os.path.join(CACHE_DIR, f"{pf.name}_{_pf_key(pf)}.pkl")
    if os.path.exists(fn):
        return pickle.load(open(fn, "rb"))
    ps = _fit_pass_nocache(pf, verbose)
    pickle.dump(ps, open(fn, "wb"))
    return ps


def _fit_pass_nocache(pf: PassFit, verbose: bool = False) -> W.PassSpec:
    """fit; if either end of the arc is not safely behind a limb (z <= -0.08), extend the
    arc there (the extension is hidden, so the regulariser runs it straight) and refit."""
    import dataclasses
    rng = pf.phi_range or (-90.0 - pf.phi_pad, 90.0 + pf.phi_pad)
    for it in range(8):
        cur = dataclasses.replace(pf, phi_range=rng)
        ps = _fit_pass(cur, verbose)
        za = float(ps.point(ps.phi_a)[0, 2])
        zb = float(ps.point(ps.phi_b)[0, 2])
        a, b = rng
        if za > -0.08:
            a = max(a - 12.0, -178.0)
        if zb > -0.08:
            b = min(b + 12.0, 178.0)
        if (a, b) == rng:
            break
        rng = (a, b)
    pf = cur
    ps = refine_pass(pf, ps)
    st, _, _ = pass_strain(ps)
    object.__setattr__(ps, "note", (ps.note + f" [strain {st*100:.1f}%]").strip())
    return ps


def frame_from(points: np.ndarray, start: np.ndarray, end: np.ndarray, axis=None):
    if axis is None:
        u, s, vt = np.linalg.svd(points)
        n = vt[2]
    else:
        n = W.normalize(np.asarray(axis, float))
    # travel: increasing phi = n x p
    mid = W.normalize(start + end)
    if np.dot(np.cross(n, start), end - start) < 0:
        n = -n
    z = np.array([0.0, 0.0, 1.0])
    e1 = W.normalize(z - np.dot(z, n) * n) if abs(n[2]) < 0.9999 else np.array([1.0, 0, 0])
    return n, e1


def _fit_pass(pf: PassFit, verbose: bool = False) -> W.PassSpec:
    allp = np.vstack([t.P() for t in pf.terms if len(t.pts) and t.kind not in ("keepout", "inside")])
    start, end = px2cam(pf.start_px)[0], px2cam(pf.end_px)[0]
    n, e1 = frame_from(allp, start, end, pf.axis)
    e2 = np.cross(n, e1)

    def coords(P):
        return np.degrees(np.arctan2(P @ e2, P @ e1)), np.degrees(np.arcsin(np.clip(P @ n, -1, 1)))

    if pf.phi_range is not None:
        pa, pb = pf.phi_range
    else:
        # the circle's limb crossings are at phi = +-90 (e1 is the point nearest the camera)
        pa, pb = -90.0 - pf.phi_pad, 90.0 + pf.phi_pad
    K = max(6, int(math.ceil((pb - pa) / pf.knot_deg)) + 3)
    rows, rhs = [], []

    def add(Bb, Bh, val, w):
        rows.append(np.concatenate([Bb, Bh]) * w)
        rhs.append(val * w)

    for t in pf.terms:
        if not len(t.pts) or t.kind in ("keepout", "inside"):
            continue
        P = t.P()
        ph, lam = coords(P)
        B = W.bspline_basis(ph, pa, pb, K)
        # weight: foreshortening - a px error near the limb is a large angle; weight by
        # the image-space leverage (cos of the angle from the view axis, floored)
        lev = np.clip(P[:, 2], 0.25, 1.0)
        for i in range(len(P)):
            if t.side == 0:
                add(B[i], np.zeros(K), lam[i], t.weight * lev[i])
            else:
                add(B[i], t.side * B[i], lam[i], t.weight * lev[i])
    # priors
    phs = np.linspace(pa, pb, 60)
    Bp = W.bspline_basis(phs, pa, pb, K)
    hw0 = pf.width / DEG
    for i in range(len(phs)):
        add(np.zeros(K), Bp[i], hw0, pf.width_w)
        add(Bp[i], np.zeros(K), 0.0, pf.beta_prior)
    # geodesic-curvature regulariser: kappa_g ~ beta'' + beta (small beta), so its null space
    # is the family of tilted great circles - a hidden stretch continues STRAIGHT on
    h = math.radians((pb - pa) / (K - 3))
    D2 = np.zeros((K - 2, K))
    for i in range(K - 2):
        D2[i, i:i + 3] = [1, -2, 1]
        D2[i, i + 1] += h * h
    D1 = np.zeros((K - 1, K))
    for i in range(K - 1):
        D1[i, i:i + 2] = [-1, 1]
    for i in range(K - 2):
        add(D2[i], np.zeros(K), 0.0, pf.smooth)
        add(np.zeros(K), D2[i], 0.0, pf.smooth * 1.5)
    for i in range(K - 1):
        add(np.zeros(K), D1[i], 0.0, pf.width_d1)
    A = np.array(rows)
    y = np.array(rhs)
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    beta = sol[:K]
    hw = np.maximum(sol[K:], 0.25)
    width = hw * DEG                        # frac D (= half width in rad)
    gather = ()
    if pf.gather_px:
        # gather given at image points along the pass -> spline samples
        gp = [(coords(px2cam(p))[0][0], g) for p, g in pf.gather_px]
        gp.sort()
        gph = np.array([a for a, _ in gp])
        gg = np.array([b for _, b in gp])
        g_s = np.interp(phs, gph, gg)
        gc, *_ = np.linalg.lstsq(Bp, g_s, rcond=None)
        gather = tuple(float(x) for x in gc)
    ps = W.PassSpec(name=pf.name, shows=pf.shows, n=tuple(float(x) for x in n), e1=tuple(float(x) for x in e1),
                    phi_a=float(pa), phi_b=float(pb), beta=tuple(float(x) for x in beta),
                    width=tuple(float(x) for x in width), gather=gather, role=pf.role, note=pf.note)
    if verbose:
        print(pf.name, "K", K, "n", np.round(n, 3))
    return ps


def edge_residual_px(ps: W.PassSpec, t: EdgeTerm) -> np.ndarray:
    """image-space distance (px) from each term point to the pass's edge on t.side
    (the edge as the pass draws it: offset across the pass frame's meridian)."""
    ph = np.linspace(ps.phi_a, ps.phi_b, 2000)
    e1, e2, n = ps.frame()
    be = ps.beta_rad(ph)
    hw = 0.5 * (ps.width_rad(ph) * (1 - ps.gather_at(ph)) + W.CORD_W * ps.gather_at(ph))
    lam = be + t.side * hw
    phr = ph * DEG
    C = np.cos(lam)[:, None] * (np.cos(phr)[:, None] * e1 + np.sin(phr)[:, None] * e2) + np.sin(lam)[:, None] * n
    C = C[C[:, 2] > -0.05]
    E = cam2px(C)
    d = np.linalg.norm(t.pts[:, None, :] - E[None, :, :], axis=2).min(1)
    return d


# --------------------------------------------------------------------------- probes
def probes_between(e1: np.ndarray, e2: np.ndarray, fr=(0.3, 0.5, 0.7), max_d: float = 300.0) -> np.ndarray:
    """points between two boundary polylines (image px): for each point of e1 the nearest
    point of e2, and points at fractions ``fr`` between."""
    out = []
    for p in e1:
        d = np.linalg.norm(e2 - p, axis=1)
        j = int(np.argmin(d))
        if d[j] > max_d or d[j] < 6:
            continue
        # skip end-clamped pairs (nearest = an end point of e2 while far off its end)
        if j in (0, len(e2) - 1) and len(e2) > 2:
            seg = e2[1] - e2[0] if j == 0 else e2[-1] - e2[-2]
            if np.dot(p - e2[j], seg * (1 if j == len(e2) - 1 else -1)) > 8.0 * np.linalg.norm(seg):
                continue
        for f in fr:
            out.append(p + f * (e2[j] - p))
    return np.array(out) if out else np.zeros((0, 2))


def inside_disc(P, r=0.975):
    d = np.linalg.norm(np.asarray(P) - [CX, CY], axis=1)
    return np.asarray(P)[d < r * RPX]


# --------------------------------------------------------------------------- true-normal refinement
def _centre_and_normal(ps: W.PassSpec, beta_c, hw_c, B, ph):
    e1, e2, n = ps.frame()
    be = (B @ beta_c) * DEG
    phr = ph * DEG
    cb = np.cos(be)[:, None]
    C = cb * (np.cos(phr)[:, None] * e1 + np.sin(phr)[:, None] * e2) + np.sin(be)[:, None] * n
    T = np.gradient(C, axis=0)
    T = T - np.einsum("ij,ij->i", T, C)[:, None] * C
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Nb = np.cross(C, T)
    hw = (B @ hw_c) * DEG                   # half width, rad
    return C, T, Nb, hw


def true_offsets(ps: W.PassSpec, beta_c, hw_c, B, ph, P, gat):
    """for each point P: (signed across-offset from the centre along the true normal, rad,
    half footprint width there, index of the centre sample)."""
    C, T, Nb, hw = _centre_and_normal(ps, beta_c, hw_c, B, ph)
    hwe = hw * (1 - gat) + 0.5 * W.CORD_W * gat
    # nearest centre sample in the tangent direction: minimise |(p - c).t| among samples near p
    d2 = ((P[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    j = np.argmin(d2, axis=1)
    # local refinement: move along the tape by the tangential component
    for _ in range(2):
        tang = np.einsum("ij,ij->i", P - C[j], T[j])
        dj = np.round(tang / np.maximum(np.linalg.norm(C[1] - C[0]), 1e-9)).astype(int)
        j = np.clip(j + dj, 0, len(C) - 1)
    off = np.arcsin(np.clip(np.einsum("ij,ij->i", P, Nb[j]), -1, 1))
    return off, hwe[j], j


def refine_pass(pf: PassFit, ps: W.PassSpec, iters: int = 25, verbose: bool = False) -> W.PassSpec:
    """Levenberg-Marquardt on the B-spline coefficients: every 'own'/'hide' edge point lands
    on the tape's TRUE edge (offset along c x t, as the renderer and the tape builder draw
    it), with the same regularisers as the linear fit."""
    K = len(ps.beta)
    pa, pb = ps.phi_a, ps.phi_b
    ph = np.linspace(pa, pb, 1200)
    B = W.bspline_basis(ph, pa, pb, K)
    gat = ps.gather_at(ph) if ps.gather else np.zeros(len(ph))
    terms = [t for t in pf.terms if len(t.pts)]
    Ps = [t.P() for t in terms]
    ws = [t.weight * np.clip(P[:, 2], 0.25, 1.0) for t, P in zip(terms, Ps)]
    h = math.radians((pb - pa) / (K - 3))
    D2 = np.zeros((K - 2, K))
    for i in range(K - 2):
        D2[i, i:i + 3] = [1, -2, 1]
        D2[i, i + 1] += h * h
    D1 = np.zeros((K - 1, K))
    for i in range(K - 1):
        D1[i, i:i + 2] = [-1, 1]
    phs = np.linspace(pa, pb, 60)
    Bp = W.bspline_basis(phs, pa, pb, K)
    hw0 = pf.width / DEG

    sub = slice(10, len(ph) - 10, 6)
    dph = math.radians(ph[1] - ph[0])
    # the strict budget holds on the HIDDEN parts; where the reference shows the band its
    # edges rule (a loose budget keeps even those bends sane)
    vis = np.zeros(len(ph), bool)
    e1_, e2_, n_ = ps.frame()
    for t in terms:
        if t.kind != "own" or t.cam is not None:
            continue
        P = t.P()
        f = np.degrees(np.arctan2(P @ e2_, P @ e1_))
        vis |= (ph >= f.min() - 10) & (ph <= f.max() + 10)
    # the budget is a CURVATURE limit at the prior width (so the fit cannot buy a bend by
    # pinching the tape narrower)
    budget = np.where(vis, max(pf.max_strain, pf.visible_strain), pf.max_strain)[sub] / max(pf.width, 0.02)
    wmin = 0.7 * pf.width / DEG

    def strain_terms(bc, hc):
        C, T, Nb, hw = _centre_and_normal(ps, bc, hc, B, ph)
        dT = np.gradient(T, dph, axis=0) / np.maximum(np.linalg.norm(np.gradient(C, dph, axis=0), axis=1), 1e-9)[:, None]
        kg = np.einsum("ij,ij->i", dT, Nb)
        st = np.abs(kg)[sub]
        front = (C[:, 2] > -0.15)[sub]
        return np.where(front, np.maximum(st - budget, 0.0), 0.0)

    def width_floor(hc):
        return np.maximum(wmin - Bp @ hc, 0.0)

    def resid(x):
        bc, hc = x[:K], x[K:]
        r = [pf.strain_w * max(pf.width, 0.02) * strain_terms(bc, hc), 2.0 * width_floor(hc)]
        for t, P, w in zip(terms, Ps, ws):
            off, hwe, _ = true_offsets(ps, bc, hc, B, ph, P, gat)
            if t.kind == "own":
                tgt = 0.0 if t.side == 0 else t.side * hwe
                r.append(w * np.degrees(off - tgt))
            elif t.kind == "hide":
                # the point (just inside the covering band) must lie on the tape
                r.append(w * np.degrees(np.maximum(t.side * off - hwe, 0.0)))
            elif t.kind == "keepout":
                r.append(w * np.degrees(np.maximum(hwe - np.abs(off), 0.0)))
            elif t.kind == "inside":
                # the band must cover its own visible region (with a small margin)
                r.append(w * np.degrees(np.maximum(np.abs(off) - (hwe - 0.004), 0.0)))
            else:
                raise ValueError(t.kind)
        r.append(pf.width_w * (Bp @ hc - hw0))
        r.append(pf.beta_prior * (Bp @ bc))
        r.append(pf.smooth * (D2 @ bc))
        r.append(pf.smooth * 1.5 * (D2 @ hc))
        r.append(pf.width_d1 * (D1 @ hc))
        return np.concatenate(r)

    x = np.concatenate([np.array(ps.beta), np.array(ps.width) / DEG])
    r = resid(x)
    lam = 1e-2
    for it in range(iters):
        J = np.zeros((len(r), len(x)))
        eps = 1e-3
        for k in range(len(x)):
            xp = x.copy()
            xp[k] += eps
            J[:, k] = (resid(xp) - r) / eps
        A = J.T @ J
        g = J.T @ r
        improved = False
        for _ in range(8):
            dx = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
            xn = x + dx
            xn[K:] = np.maximum(xn[K:], 0.25)
            rn = resid(xn)
            if rn @ rn < r @ r:
                x, r = xn, rn
                lam = max(lam / 3, 1e-6)
                improved = True
                break
            lam *= 4
        if not improved or np.abs(dx).max() < 1e-4:
            break
    import dataclasses
    return dataclasses.replace(ps, beta=tuple(float(v) for v in x[:K]), width=tuple(float(v) * DEG for v in x[K:]))


def true_edge_residual_px(ps: W.PassSpec, t: EdgeTerm) -> np.ndarray:
    """image px distance from each point to the pass's TRUE edge on t.side."""
    ph = np.linspace(ps.phi_a, ps.phi_b, 3000)
    C = ps.point(ph)
    T = np.gradient(C, axis=0)
    T = T - np.einsum("ij,ij->i", T, C)[:, None] * C
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Nb = np.cross(C, T)
    hw = 0.5 * (ps.width_rad(ph) * (1 - ps.gather_at(ph)) + W.CORD_W * ps.gather_at(ph))
    a = t.side * hw
    Eg = np.cos(a)[:, None] * C + np.sin(a)[:, None] * Nb
    Eg = Eg[Eg[:, 2] > -0.05]
    E = cam2px(Eg)
    return np.linalg.norm(t.pts[:, None, :] - E[None, :, :], axis=2).min(1)
