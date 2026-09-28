#!/usr/bin/env python
"""props_lib.smokebomb_threads - the one loose thread that leaves the silhouette: T4.

numpy only.  REFERENCE_SPEC 6: "T4 - hook on the left outline, image angle ~155 deg, 6 px
past the outline" (about 0.45 mm at the ball's 70 mm), the only fibre that breaks the
outline by more than fuzz ("thread_tips_past_outline": max reach 7.4 px, one 6 px hook at
155 deg; no loose thread hangs off the ball).  Round 2 drew it in the texture, so nothing
crossed the outline; the adversary found it missing.  Here it is a tiny closed tube:

    root   0.3 mm inside the tape surface at the limb (so no open end ever shows)
    hook   out past the outline by 0.45 mm and curling back, in the plane of the outline
    tube   0.16 mm across (about 2 px in the reference view), 4 sides, capped ends

It carries its own small island in the atlas, painted as the tape's own yarn (the colour of
the fibres, props_lib.smokebomb_cloth).  LOD0 only: at LOD1's switch distance (0.89 m) the
hook is a twentieth of a pixel.  T1, T2, T3 and T5 lie ON the tape and stay in the texture.
"""
from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Dict, Tuple

import numpy as np

#: REFERENCE_SPEC 6 (T4): image angle of the hook, and how far past the outline it reaches
T4_ANGLE_DEG = 155.0
T4_REACH_MM = 0.45
TUBE_R_MM = 0.115
#: 4 sides and 6 rings: every triangle stays above Unreal's 0.005 mm2 drop threshold (the
#: build drops anything under 0.008 mm2)
SIDES = 4
RINGS = 6
#: the hook's path in the outline's local frame: (radial mm from the outline, along-outline
#: mm toward increasing image angle, toward-camera mm).  DESIGNED from the reference's hook
#: shape (out, up and over, curling back toward the ball); the root is buried.
HOOK_PATH = ((-0.30, 0.05, 0.25), (-0.05, 0.08, 0.12), (0.18, 0.10, 0.04), (0.38, 0.02, 0.0),
             (T4_REACH_MM, -0.12, 0.0), (0.40, -0.28, 0.0), (0.26, -0.36, -0.02), (0.12, -0.33, -0.03))
#: the island's chart size (mm): u along the tube, v round it
ISLAND_KEY_SUB = 99999


def _smooth_path(P: np.ndarray, n: int = 20) -> np.ndarray:
    """Catmull-Rom through the path points, ``n`` samples."""
    P = np.asarray(P, float)
    Q = np.concatenate([P[:1] * 2 - P[1:2], P, P[-1:] * 2 - P[-2:-1]], axis=0)
    out = []
    segs = len(P) - 1
    for i in range(segs):
        p0, p1, p2, p3 = Q[i], Q[i + 1], Q[i + 2], Q[i + 3]
        for t in np.linspace(0, 1, max(2, n // segs), endpoint=(i == segs - 1)):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def hook_geometry(outline_r_mm: float, angle_deg: float = T4_ANGLE_DEG) -> Dict[str, np.ndarray]:
    """The T4 tube in the CAMERA frame (mm): vertices, triangles (outward), and per-corner
    chart coordinates (u along the tube, v round it, mm)."""
    th = math.radians(angle_deg)
    er = np.array([math.cos(th), math.sin(th), 0.0])        # radial (image plane)
    et = np.array([-math.sin(th), math.cos(th), 0.0])       # along the outline (increasing angle)
    ez = np.array([0.0, 0.0, 1.0])                          # toward the camera
    base = er * outline_r_mm
    ctrl = np.array([base + a * er + b * et + c * ez for a, b, c in HOOK_PATH])
    C = _smooth_path(ctrl, 60)
    # resample to RINGS points evenly along the length
    Lc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
    tq = np.linspace(0.0, Lc[-1], RINGS)
    C = np.stack([np.interp(tq, Lc, C[:, i]) for i in range(3)], axis=1)
    # parallel-transport frames along the path
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    n0 = np.cross(T[0], ez)
    if np.linalg.norm(n0) < 1e-6:
        n0 = np.cross(T[0], er)
    n0 /= np.linalg.norm(n0)
    N = [n0]
    for i in range(1, len(C)):
        n = N[-1] - np.dot(N[-1], T[i]) * T[i]
        N.append(n / np.linalg.norm(n))
    N = np.array(N)
    Bn = np.cross(T, N)
    # taper the radius to 60 % at the free tip
    rr = TUBE_R_MM * np.linspace(1.0, 0.85, len(C))
    ang = np.arange(SIDES) * 2 * math.pi / SIDES
    ring = (C[:, None, :] + rr[:, None, None] * (np.cos(ang)[None, :, None] * N[:, None, :]
                                                  + np.sin(ang)[None, :, None] * Bn[:, None, :]))
    V = ring.reshape(-1, 3)
    L = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
    circ = 2 * math.pi * TUBE_R_MM
    tris, charts = [], []
    for i in range(len(C) - 1):
        for j in range(SIDES):
            a, b = i * SIDES + j, i * SIDES + (j + 1) % SIDES
            c, d = (i + 1) * SIDES + j, (i + 1) * SIDES + (j + 1) % SIDES
            va, vb = circ * j / SIDES, circ * (j + 1) / SIDES
            tris += [(a, c, b), (b, c, d)]
            charts += [[(L[i], va), (L[i + 1], va), (L[i], vb)], [(L[i], vb), (L[i + 1], va), (L[i + 1], vb)]]
    # caps: the end ring closed by two triangles (a quad)
    for end, i in ((0, 0), (1, len(C) - 1)):
        r0 = i * SIDES
        a, b, c, d = r0, r0 + 1, r0 + 2, r0 + 3
        q = [(a, b, c), (a, c, d)] if end == 0 else [(c, b, a), (d, c, a)]
        tris += q
        u = L[i]
        for _ in q:
            charts.append([(u, 0.0), (u + 0.08, 0.5 * circ), (u, circ)])
    T3 = np.array(tris, np.int64)
    ch = np.array(charts, float)
    # make every triangle face away from the tube's axis (outward)
    X = V[T3]
    nrm = np.cross(X[:, 1] - X[:, 0], X[:, 2] - X[:, 0])
    cen = X.mean(axis=1)
    k = np.argmin(np.linalg.norm(cen[:, None, :] - C[None, :, :], axis=2), axis=1)
    out = cen - C[k]
    nside = 2 * SIDES * (len(C) - 1)
    caps = np.arange(len(T3)) >= nside
    ends = np.where(np.arange(len(T3))[caps] < nside + 2, 0, len(C) - 1)
    out[caps] = T[ends] * np.where(ends == 0, -1.0, 1.0)[:, None]
    flip = (nrm * out).sum(axis=1) < 0
    T3 = np.where(flip[:, None], T3[:, ::-1], T3)
    ch = np.where(flip[:, None, None], ch[:, ::-1], ch)
    X = V[T3]
    nrm = np.cross(X[:, 1] - X[:, 0], X[:, 2] - X[:, 0])

    def hand(Xt, Ct):
        e1, e2 = Xt[:, 1] - Xt[:, 0], Xt[:, 2] - Xt[:, 0]
        d1, d2 = Ct[:, 1] - Ct[:, 0], Ct[:, 2] - Ct[:, 0]
        det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
        dpu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
        dpv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
        return (np.cross(dpu, dpv) * np.cross(e1, e2)).sum(axis=1)
    # the sides: one continuous (u along, v round) strip; mirror it as a whole if needed
    if (hand(X[~caps], ch[~caps]) < 0).mean() > 0.5:
        ch[~caps, :, 1] = circ - ch[~caps, :, 1]
    # the caps: each its own planar chart, beside the strip (never overlapping it)
    for ci, where in ((0, -0.45), (1, L[-1] + 0.15)):
        sel = np.nonzero(caps & (np.where(caps, np.arange(len(T3)), 0) >= nside + 2 * ci)
                         & (np.arange(len(T3)) < nside + 2 * ci + 2))[0]
        n_ = nrm[sel[0]] / np.linalg.norm(nrm[sel[0]])
        o = X[sel[0], 0]
        e1 = X[sel[0], 1] - o
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(n_, e1)
        for t_ in sel:
            q = X[t_] - o
            ch[t_] = np.stack([q @ e1, q @ e2], axis=1)
        m = ch[sel].reshape(-1, 2).min(axis=0)
        ch[sel] = ch[sel] - m + np.array([where, 0.0])
    assert (hand(X, ch) > 0).all(), "T4 hook: a mirrored UV triangle"
    Xa = V[T3]
    area = 0.5 * np.linalg.norm(np.cross(Xa[:, 1] - Xa[:, 0], Xa[:, 2] - Xa[:, 0]), axis=1)
    return {"verts": V, "tris": T3, "chart": ch, "min_area_mm2": float(area.min()), "length_mm": float(L[-1]), "circ_mm": circ,
            "reach_mm": T4_REACH_MM, "angle_deg": angle_deg, "outline_r_mm": outline_r_mm}


def atlas_item(hook: Dict[str, np.ndarray], strip_index: int):
    """The hook's island for props_lib.smokebomb_atlas.plan (strip index past the real strips)."""
    ch = hook["chart"].reshape(-1, 2)
    box = (float(ch[:, 0].min()), float(ch[:, 0].max()), float(ch[:, 1].min()), float(ch[:, 1].max()))
    return SimpleNamespace(strip=strip_index, sub=ISLAND_KEY_SUB, comp=0, bbox_mm=box, is_thread=True)


def append_hook(A, hook: Dict[str, np.ndarray], atlas, strip_index: int):
    """Append the hook to an Assembled LOD (smokebomb_geometry.Assembled) as its own vertices
    (never welded to the shell), with its island's UVs."""
    from . import smokebomb_strips as SS
    from .smokebomb_geometry import Assembled, MM
    key = (int(strip_index), ISLAND_KEY_SUB, 0)
    Vb = SS.cam_to_blender(hook["verts"] * MM)
    n0 = len(A.verts)
    T = hook["tris"] + n0
    uv = atlas.uv(key, hook["chart"].reshape(-1, 2)).reshape(-1, 3, 2)
    out = Assembled(np.concatenate([A.verts, Vb]), np.concatenate([A.tris, T]),
                    np.concatenate([A.loop_uv, uv]), np.concatenate([A.tri_strip, np.full(len(T), -1)]),
                    np.concatenate([A.tri_wall, np.zeros(len(T), bool)]),
                    np.concatenate([A.tri_island, np.full(len(T), -1)]), list(A.sharp),
                    np.concatenate([A.vert_strip, np.full(len(Vb), -1)]),
                    np.concatenate([A.vert_chart, np.zeros((len(Vb), 2))]))
    out.report = dict(A.report)
    out.report["T4_hook"] = {"triangles": int(len(T)), "vertices": int(len(Vb)),
                             "reach_past_outline_mm": hook["reach_mm"], "angle_deg": hook["angle_deg"],
                             "tube_radius_mm": TUBE_R_MM}
    out.report["triangles"] = int(len(out.tris))
    out.report["vertices"] = int(len(out.verts))
    return out


__all__ = ["T4_ANGLE_DEG", "T4_REACH_MM", "hook_geometry", "atlas_item", "append_hook", "ISLAND_KEY_SUB"]
