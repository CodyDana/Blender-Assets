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


# ----------------------------------------------------------------------------------------------- pilot 2 fix 1
# Judge (pilot 2, 4/10): the corestones read as potato / soap-bar blobs (solidity 0.998 vs the sheet's 0.976 /
# 0.945, 2 corners over 35 deg where the sheet has 5 / 12) and the cracks as knife slots. Method change: a
# FACETED WATER-WORN BLOCK - the dome mass cut by 10-16 broad, designed joint / wear planes (cap depths 6-22 cm, so
# each facet is 40-90 cm across), rounded by one large opening so the planes stay readable and meet at soft
# ridges; joints SPLIT the mass into lobes (each lobe stepped down by its own amount and rounded on its own, so the
# joint has a step and rounded lips on both sides) instead of being cut as slots.
def az_el(az_deg, el_deg):
    """Unit normal from azimuth (0 = facing the sheet's main view, i.e. -y; +90 = the +x end; 180 = back) and
    elevation (+90 = up)."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])


def broad_facet_cuts(Vpts, facets, rng, jitter_deg=4.0):
    """facets: [(az, el, depth m)] -> half-space cutters removing the cap beyond ``depth`` under the support."""
    out = []
    for az, el, depth in facets:
        n = sd.jitter(az_el(az, el), jitter_deg, rng)
        c = rf.joint_cut(Vpts, n, float(depth), margin=0.4)
        if c is not None:
            out.append(c)
    return out


def wavy_halfspace(p0, n, amp=0.04, freq=1.2, seed=0, size=6.0, res=72, depth=6.0, meander=None):
    """Closed mesh of the solid {x : n.(x - p0) >= w(u, v)} clipped to a size x size x depth slab, where w is a
    smooth low-frequency wave (amplitude ``amp`` m, ``freq`` per m) so a joint surface meanders instead of running
    as a straight plane. ``meander`` = (amp, freq) of an extra wave along the in-plane horizontal axis only."""
    n = sd.unit(n)
    t = sd.unit(np.cross(n, [0.0, 0.0, 1.0]) if abs(n[2]) < 0.95 else np.cross(n, [1.0, 0.0, 0.0]))
    b = np.cross(n, t)
    us = np.linspace(-size / 2, size / 2, res + 1)
    U, Vv = np.meshgrid(us, us, indexing="ij")
    P2 = np.stack([U.ravel(), Vv.ravel(), np.zeros(U.size)], 1)
    w = amp * sd.fbm(P2, [(0.7, freq), (0.3, freq * 2.3)], seed) / 0.7
    if meander:
        ma, mf = meander
        w = w + ma * np.sin(P2[:, 1] * mf * 2 * math.pi + 0.7 * seed)
    p0 = np.asarray(p0, float)
    front = p0 + U.ravel()[:, None] * t + Vv.ravel()[:, None] * b + w[:, None] * n
    back = p0 + U.ravel()[:, None] * t + Vv.ravel()[:, None] * b + depth * n
    V = np.vstack([front, back])
    m = res + 1
    off = m * m
    F = []
    for i in range(res):
        for j in range(res):
            a0, a1, a2, a3 = i * m + j, (i + 1) * m + j, (i + 1) * m + j + 1, i * m + j + 1
            F += [(a0, a2, a1), (a0, a3, a2), (a0 + off, a1 + off, a2 + off), (a0 + off, a2 + off, a3 + off)]
    ring = [i * m for i in range(m)] + [res * m + j for j in range(1, m)] + \
        [i * m + res for i in range(res - 1, -1, -1)] + [j for j in range(res - 1, 0, -1)]
    for k in range(len(ring)):
        a, c = ring[k], ring[(k + 1) % len(ring)]
        F += [(a, c, c + off), (a, c + off, a + off)]
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(map(float, p))) for p in V]
    for f in F:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.index_update()
    Vo = np.array([v.co[:] for v in bm.verts])
    Fo = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return Vo, Fo
