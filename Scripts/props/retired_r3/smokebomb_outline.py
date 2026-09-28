#!/usr/bin/env python
"""props_lib.smokebomb_outline - the reference view's OUTLINE, matched by construction (round 3).

numpy only.  Round 2 kept the outline round with a degree-8 fit of the layer count and a
12-sector core profile.  The adversary measured what that left: outline harmonics n9 / n10
3-4x the reference's, no whorl bump at 88 deg, and the biggest bulge in the wrong place.

Round 3 matches the outline's low-order shape directly.  The silhouette in the reference view
is the tape surface along the LIMB (the camera-frame great circle z = 0), seen edge-on, so
its radius at image angle theta is (to within the cos of a few degrees) the height of the
strip on top at the limb point, max'ed over a few degrees either side of the limb.  That is
evaluated from the height model BEFORE meshing (``limb_radius``), and the core gets a smooth
correction so that the outline's Fourier series up to ``N_MATCH`` equals the reference's:

    core(P) = core_mm + c0 + sum_{n=1..N} (A_n cos n theta + B_n sin n theta) * (1 - z^2)

(theta = the image angle of P, z = its component along the view axis).  The (1 - z^2)
weight is 1 on the limb and 0 at the view axis, so the correction never pinches the front
or the back pole.  Above ``N_MATCH`` the outline is left to the geometry: the tape's own
steps where each edge crosses the limb (REFERENCE_SPEC 5).

REF_OUTLINE_PX is a MEASUREMENT, typed in: the reference outline's Fourier coefficients
(cos, sin) in px, n = 0..24, measured by WorkFiles/smokebomb/build_r3/r3_outline_measure.py
with the round-2 adversary's own outline instrument (half-maximum edge, 1440 rays, circle
fit: centre (627.33, 628.85), R 464.07 px).  The build never reads the reference image.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_strips as SS

#: MEASURED (see the module docstring): (cos, sin) px per harmonic n = 0..24
REF_OUTLINE_PX: Tuple[Tuple[float, float], ...] = (
    (-0.036, 0.0), (0.034, -0.081), (-1.501, -4.322), (3.077, 0.639), (-0.606, -1.378),
    (1.142, 2.154), (-1.354, 1.564), (-1.204, -1.556), (0.43, -0.516), (-0.465, 0.215),
    (-0.725, -0.279), (-1.992, -0.27), (0.325, -1.014), (-0.468, 0.167), (-0.68, 0.313),
    (-0.29, -0.113), (0.624, -0.943), (0.039, 0.939), (-0.842, 0.146), (-1.123, -0.11),
    (0.28, -0.398), (0.713, -0.023), (-0.275, 0.272), (-0.138, -0.756), (-0.084, 0.156),
)
REF_OUTLINE_R_PX = 464.07

#: harmonics matched by the core correction; above this the tape's own steps make the outline
N_MATCH = 24
#: limb sampling
LIMB_N = 1440
LIMB_ALPHA_DEG = tuple(np.arange(-6.0, 6.01, 0.5).tolist())


def target_radius_mm(theta: np.ndarray, radius_mm: float, n_max: int = N_MATCH) -> np.ndarray:
    """The reference outline scaled to a mean radius of ``radius_mm``, harmonics 2..n_max
    (n = 1, the centre offset, is zero: the ball is centred on its pivot)."""
    k = radius_mm / REF_OUTLINE_R_PX
    r = np.full_like(theta, radius_mm, dtype=np.float64)
    for n in range(2, min(n_max, len(REF_OUTLINE_PX) - 1) + 1):
        a, b = REF_OUTLINE_PX[n]
        r = r + k * (a * np.cos(n * theta) + b * np.sin(n * theta))
    return r


def fourier(r: np.ndarray, n_max: int) -> np.ndarray:
    """(n_max + 1, 2) cos / sin coefficients of r sampled uniformly on [0, 2 pi)."""
    F = np.fft.rfft(r) / len(r)
    out = np.zeros((n_max + 1, 2))
    out[0, 0] = F[0].real
    for n in range(1, n_max + 1):
        out[n, 0] = 2 * F[n].real
        out[n, 1] = -2 * F[n].imag
    return out


def limb_radius(strips, hm, n: int = LIMB_N, alphas: Sequence[float] = LIMB_ALPHA_DEG,
                chart_r: float = 35.0) -> Tuple[np.ndarray, np.ndarray]:
    """Projected outline radius (mm) at ``n`` image angles: the height of the strip on top,
    times cos(alpha), max'ed over points ``alpha`` degrees in front of / behind the limb."""
    th = np.arange(n) * 2.0 * math.pi / n
    best = np.full(n, -np.inf)
    for a in alphas:
        ar = math.radians(a)
        P = np.stack([np.cos(th) * math.cos(ar), np.sin(th) * math.cos(ar),
                      np.full(n, math.sin(ar))], axis=1)
        f = SS.evaluate_field(strips, P, chart_r)
        top = f.top
        ok = top >= 0
        h = np.full(n, -np.inf)
        if ok.any():
            idx = np.nonzero(ok)[0]
            fs = SS.Field(f.names, f.d[:, idx], f.rank[:, idx], f.s[:, idx], f.w[:, idx], f.lift[:, idx],
                          f.top[idx], f.covered[:, idx], f.half_width[:, idx])
            h[idx] = hm.sheet(fs, P[idx], top[idx])
        best = np.maximum(best, h * math.cos(ar))
    bad = ~np.isfinite(best)
    if bad.any():
        best[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], best[~bad], period=n)
    return th, best


def fit_core_correction(strips, hm, radius_mm: float, n_max: int = N_MATCH, rounds: int = 3,
                        log=None) -> dict:
    """Set ``hm.outline_coef`` / ``hm.core_mm`` so that the limb outline's harmonics 0..n_max
    equal the reference's (scaled to ``radius_mm``).  Returns a report."""
    th = np.arange(LIMB_N) * 2.0 * math.pi / LIMB_N
    tgt = fourier(target_radius_mm(th, radius_mm, n_max), n_max)
    hm.outline_coef = np.zeros((n_max + 1, 2)) if getattr(hm, "outline_coef", None) is None else hm.outline_coef
    hist = []
    for it in range(rounds):
        _, r = limb_radius(strips, hm)
        cur = fourier(r, n_max)
        err = tgt - cur
        hm.core_mm = float(hm.core_mm + err[0, 0])
        coef = hm.outline_coef.copy()
        coef[1:] += err[1:]
        hm.outline_coef = coef
        rms = float(np.sqrt(0.5 * (err[1:] ** 2).sum()))
        hist.append({"round": it, "mean_mm": round(float(cur[0, 0]), 4), "lowpass_rms_err_mm": round(rms, 4)})
        if log:
            log(f"  outline fit round {it}: mean {cur[0, 0]:.3f} mm, harmonic error rms {rms:.4f} mm")
    _, r = limb_radius(strips, hm)
    cur = fourier(r, n_max)
    res = r - target_radius_mm(th, radius_mm, n_max)
    return {"rounds": hist, "core_mm": round(hm.core_mm, 4),
            "final_lowpass_err_mm": round(float(np.sqrt(0.5 * ((tgt - cur)[1:] ** 2).sum())), 5),
            "residual_rms_mm": round(float(res.std()), 4),
            "correction_amp_mm": [round(float(math.hypot(*c)), 3) for c in hm.outline_coef]}


def correction(P: np.ndarray, coef: Optional[np.ndarray]) -> np.ndarray:
    """sum (A_n cos n th + B_n sin n th) (1 - z^2) at camera-frame unit vectors P."""
    if coef is None:
        return np.zeros(P.shape[:-1])
    th = np.arctan2(P[..., 1], P[..., 0])
    out = np.zeros(P.shape[:-1])
    for n in range(1, len(coef)):
        out = out + coef[n, 0] * np.cos(n * th) + coef[n, 1] * np.sin(n * th)
    return out * (1.0 - P[..., 2] ** 2)


__all__ = ["REF_OUTLINE_PX", "REF_OUTLINE_R_PX", "N_MATCH", "target_radius_mm", "fourier",
           "limb_radius", "fit_core_correction", "correction"]


# =========================================================================== the mesh's outline
def mesh_outline(verts_mm: np.ndarray, tris: np.ndarray, n: int = LIMB_N, step_mm: float = 0.02,
                 view: Tuple[float, float, float] = (0.0, 0.0, 1.0)) -> Tuple[np.ndarray, np.ndarray]:
    """The ORTHOGRAPHIC outline of a triangle mesh seen along ``view`` (camera frame; the
    reference view is +z): radius (mm) about the origin at ``n`` image angles.  The farthest
    point of a union of triangles along a ray lies on a triangle edge, so every edge near the
    rim is sampled every ``step_mm`` and the farthest sample per angle bin is kept."""
    V = np.asarray(verts_mm, np.float64)
    vz = np.asarray(view, np.float64)
    vz = vz / np.linalg.norm(vz)
    ex = np.cross([0.0, 1.0, 0.0], vz) if abs(vz[1]) < 0.9 else np.cross([1.0, 0.0, 0.0], vz)
    ex /= np.linalg.norm(ex)
    ey = np.cross(vz, ex)
    Q = np.stack([V @ ex, V @ ey], axis=1)
    rq = np.hypot(Q[:, 0], Q[:, 1])
    T = np.asarray(tris, np.int64)
    near = rq[T].max(axis=1) > 0.9 * rq.max()
    E = np.concatenate([T[near][:, [0, 1]], T[near][:, [1, 2]], T[near][:, [2, 0]]], axis=0)
    E = np.unique(np.sort(E, axis=1), axis=0)
    a, b = Q[E[:, 0]], Q[E[:, 1]]
    L = np.linalg.norm(b - a, axis=1)
    m = np.maximum(2, np.ceil(L / step_mm).astype(int) + 1)
    idx = np.repeat(np.arange(len(E)), m)
    t = np.concatenate([np.linspace(0.0, 1.0, k) for k in m])
    pts = a[idx] + (b - a)[idx] * t[:, None]
    th = np.arctan2(pts[:, 1], pts[:, 0]) % (2 * math.pi)
    r = np.hypot(pts[:, 0], pts[:, 1])
    bins = np.floor(th / (2 * math.pi) * n).astype(int) % n
    out = np.full(n, -np.inf)
    np.maximum.at(out, bins, r)
    bad = ~np.isfinite(out)
    if bad.any():
        out[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], out[~bad], period=n)
    return (np.arange(n) + 0.5) * 2 * math.pi / n, out


def refine_from_mesh(hm, verts_mm: np.ndarray, tris: np.ndarray, radius_mm: float,
                     n_max: int = N_MATCH, gain: float = 1.0) -> dict:
    """One correction round measured on the MESH's own outline (walls, steps and all)."""
    th, r = mesh_outline(verts_mm, tris)
    # the bin centres are offset by half a bin: resample onto the uniform grid first
    grid = np.arange(LIMB_N) * 2.0 * math.pi / LIMB_N
    rg = np.interp(grid, th, r, period=2 * math.pi)
    tgt = fourier(target_radius_mm(grid, radius_mm, n_max), n_max)
    cur = fourier(rg, n_max)
    err = tgt - cur
    hm.core_mm = float(hm.core_mm + gain * err[0, 0])
    coef = hm.outline_coef.copy()
    coef[1:] += gain * err[1:]
    hm.outline_coef = coef
    return {"mean_mm": round(float(cur[0, 0]), 4),
            "lowpass_rms_err_mm": round(float(np.sqrt(0.5 * (err[1:] ** 2).sum())), 4),
            "residual_rms_mm": round(float((rg - target_radius_mm(grid, radius_mm, n_max)).std()), 4)}


__all__ += ["mesh_outline", "refine_from_mesh"]
