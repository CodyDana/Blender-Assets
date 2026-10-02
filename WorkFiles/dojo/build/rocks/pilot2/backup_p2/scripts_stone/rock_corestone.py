"""Corestone construction for river boulders (pilot 2; STONE_BUILDING_STUDY.md 3.9: joints first, then rounding from
outside in). bpy (bmesh) + numpy; returns closed meshes for stone_sdf.SDFGraph.

A river boulder is a CORESTONE that the river has rolled: a rounded ellipsoidal mass whose old joint planes still
show as broad faces, its edges rounded in proportion to its short axis, its surface lumpy with soft secondary facets,
a domed top, sides that roll under into the bed. Pilot 1 built the boulder from the traced visual hull and got a loaf
(vertical sides, flat top, hard shoulders); here the hull is only a clamp.

    lobe = corestone_lobe(spec, rng)                    # lumpy superellipsoid (V, F), closed
    cuts = joint_cuts(Vpts, joints)                     # 2-4 old joint planes (half-space boxes)
    facets = facet_cuts(Vpts, rng, n, depth, ...)       # shallow soft facets on the upper and side surface
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numpy as np
import bmesh

import stone_sdf as sd
import rock_forms as rf


def _sgnpow(x, e):
    return np.sign(x) * np.abs(x) ** e


def unit_sphere(subdiv=5):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts])
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return V / np.linalg.norm(V, axis=1, keepdims=True), F


def corestone_lobe(spec: Dict, rng, subdiv=5):
    """spec: centre (x, y), a (half length), b (half depth), ze (equator height above grade), c_up (equator to
    crown), c_dn (equator to the bottom, below grade), p_xy / p_z (superellipse exponents: 2 = ellipse, larger =
    fuller), crown (dx, dy) shift of the crown, tilt_deg (lean of the long axis in x-z), yaw_deg, lumps
    [(amplitude share of radius, frequency on the unit sphere)], under (0-1 extra tuck of the lower flank)."""
    U, F = unit_sphere(subdiv)
    pxy = spec.get("p_xy", 2.2)
    pz = spec.get("p_z", 2.1)
    x = spec["a"] * _sgnpow(U[:, 0], 2.0 / pxy)
    y = spec["b"] * _sgnpow(U[:, 1], 2.0 / pxy)
    up = U[:, 2] >= 0
    z = np.where(up, spec["c_up"] * _sgnpow(U[:, 2], 2.0 / pz), spec["c_dn"] * _sgnpow(U[:, 2], 2.0 / pz))
    # flank tuck: below the equator the section shrinks a little more (the rolled-under foot)
    t = np.clip(-U[:, 2], 0, 1)
    k = 1.0 - spec.get("under", 0.12) * t ** 1.5
    x, y = x * k, y * k
    # crown shift: the top of the dome sits off-centre (both sheet boulders crown right of centre)
    cdx, cdy = spec.get("crown", (0.0, 0.0))
    w = np.clip(U[:, 2], 0, 1) ** 2
    x = x + cdx * w
    y = y + cdy * w
    # lumps: low-frequency radial bumps (secondary form, not noise speckle)
    lump = np.zeros(len(U))
    for amp, fr in spec.get("lumps", [(0.035, 1.6), (0.018, 3.4)]):
        lump += amp * sd.vnoise3(U * fr + 7.3 * fr, int(rng.integers(1 << 30)))
    P = np.stack([x, y, z], 1)
    c = np.array([0.0, 0.0, 0.0])
    P = c + P * (1.0 + lump)[:, None]
    # lean / yaw
    tl = math.radians(spec.get("tilt_deg", 0.0))
    ct, st = math.cos(tl), math.sin(tl)
    P = np.column_stack([P[:, 0] * ct - P[:, 2] * st, P[:, 1], P[:, 0] * st + P[:, 2] * ct])
    P = np.array([sd.rotz(p, spec.get("yaw_deg", 0.0)) for p in P]) if spec.get("yaw_deg") else P
    cx, cy = spec.get("centre", (0.0, 0.0))
    P[:, 0] += cx
    P[:, 1] += cy
    P[:, 2] += spec["ze"]
    return P, F


def joint_cuts(Vpts, joints: Sequence):
    """joints: [(normal, depth under the support)] -> half-space cutters (broad old joint faces)."""
    out = []
    for n, depth in joints:
        c = rf.joint_cut(Vpts, np.asarray(n, float), float(depth))
        if c is not None:
            out.append(c)
    return out


def facet_cuts(Vpts, rng, count, depth=(0.015, 0.05), nz_min=-0.15, zmin=0.15, jitter_deg=12.0):
    """Shallow soft facets: plane caps removed from the convex mass at random up / side directions. The cap of a
    convex surface of radius R cut at depth h is ~2 sqrt(2 R h) across: 3 cm on a 0.7 m radius = a 40 cm facet."""
    out = []
    cen = Vpts.mean(0)
    tries = 0
    while len(out) < count and tries < count * 20:
        tries += 1
        d = sd.unit(rng.normal(0, 1, 3))
        if d[2] < nz_min:
            continue
        d = sd.jitter(d, jitter_deg, rng)
        s = Vpts @ d
        cap = Vpts[s > s.max() - 0.01]
        if cap[:, 2].mean() < zmin:
            continue
        h = rng.uniform(*depth)
        c = rf.joint_cut(Vpts, d, h, margin=0.15)
        if c is not None:
            out.append(c)
    return out


def hull_points(V, F, n=40000, rng=None):
    """Area-weighted surface points of a closed mesh (support queries for the cutters)."""
    rng = rng or np.random.default_rng(0)
    _, a = sd.face_normals_areas(V, F)
    idx = rng.choice(len(F), n, p=a / a.sum())
    r1 = np.sqrt(rng.uniform(size=n))
    r2 = rng.uniform(size=n)
    A, B, C = V[F[idx, 0]], V[F[idx, 1]], V[F[idx, 2]]
    return (1 - r1)[:, None] * A + (r1 * (1 - r2))[:, None] * B + (r1 * r2)[:, None] * C
