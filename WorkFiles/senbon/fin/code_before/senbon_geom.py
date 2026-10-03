"""Senbon needles: every LOD as real geometry, generated analytically (numpy only, no bpy).

Each mesh is a list of triangles with per-corner analytic normals and per-corner island-local UVs in millimetres:
U along the profile (arc length of the LOD0 profile, the same function on every LOD), V around it (arc length,
V = -(theta' - 180 deg) * r, seam on -Z, decreasing with theta so the tangent frame is not mirrored).  Facets of the
heavy point are their own islands (planar coordinates).  ``layout`` converts island mm to texture UVs.

Nothing is decimated: LOD0..2 are each generated at their own side count and stations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import senbon_spec as S

D2R = math.pi / 180.0


# =============================================================================================== containers
@dataclass
class PPoint:
    """One profile station: axial position, radius, profile-plane normals (n_axial, n_radial) before / after."""
    s: float
    r: float
    nb: Tuple[float, float]
    na: Tuple[float, float]


def _unit(a, b):
    l = math.hypot(a, b)
    return (a / l, b / l)


def seg_normal(p0, p1):
    """Outward profile normal of the straight segment p0 -> p1 (s increasing, the solid below r)."""
    ds, dr = p1[0] - p0[0], p1[1] - p0[1]
    return _unit(-dr, ds) if (ds > 0 or dr != 0) else (0.0, 1.0)


class MB:
    """Mesh builder: vertices (mm), triangles with per-corner normals / island UVs (mm), slot, part, island."""

    def __init__(self, name):
        self.name = name
        self.V: List[Tuple[float, float, float]] = []
        self.T: List[Tuple[int, int, int]] = []
        self.N: List[np.ndarray] = []
        self.UV: List[np.ndarray] = []
        self.slot: List[int] = []
        self.part: List[str] = []
        self.island: List[str] = []
        self.flipped = 0

    def v(self, p) -> int:
        self.V.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.V) - 1

    def tri(self, idx, normals, uvs, slot, part, island):
        a, b, c = (np.array(self.V[i]) for i in idx)
        gn = np.cross(b - a, c - a)
        if np.linalg.norm(gn) < 1e-14:
            return False                      # zero-area: skipped (never emitted)
        if gn @ np.mean(normals, axis=0) < 0:
            idx = (idx[0], idx[2], idx[1])
            normals = [normals[0], normals[2], normals[1]]
            uvs = [uvs[0], uvs[2], uvs[1]]
            self.flipped += 1
        self.T.append(tuple(int(i) for i in idx))
        self.N.append(np.array([np.asarray(n, float) / np.linalg.norm(n) for n in normals]))
        self.UV.append(np.array(uvs, float))
        self.slot.append(int(slot))
        self.part.append(part)
        self.island.append(island)
        return True

    def arrays(self):
        return (np.array(self.V), np.array(self.T, np.int64), np.array(self.N), np.array(self.UV),
                np.array(self.slot), np.array(self.part), np.array(self.island))


# =============================================================================================== canonical U
class Canon:
    """The LOD0 profile polyline and its arc length: U(s, r) = arc length of the nearest point (every LOD)."""

    def __init__(self, pts: Sequence[Tuple[float, float]], extend_to: Optional[float] = None):
        P = [tuple(p) for p in pts]
        if extend_to is not None and P[-1][0] < extend_to:
            P.append((extend_to, P[-1][1]))
        self.P = np.array(P, float)
        d = np.linalg.norm(np.diff(self.P, axis=0), axis=1)
        self.L = np.concatenate([[0.0], np.cumsum(d)])

    def U(self, s, r) -> float:
        q = np.array([s, r], float)
        best, bu = 1e18, 0.0
        for i in range(len(self.P) - 1):
            a, b = self.P[i], self.P[i + 1]
            ab = b - a
            ll = ab @ ab
            t = 0.0 if ll == 0 else float(np.clip((q - a) @ ab / ll, 0, 1))
            d = np.linalg.norm(a + t * ab - q)
            if d < best - 1e-12:
                best, bu = d, self.L[i] + t * math.sqrt(ll)
        return float(bu)

    def at(self, u):
        """(s, r) on the canonical profile at arc length u (vectorised)."""
        u = np.asarray(u, float)
        i = np.clip(np.searchsorted(self.L, u, side="right") - 1, 0, len(self.L) - 2)
        seg = self.L[i + 1] - self.L[i]
        t = np.where(seg > 0, (u - self.L[i]) / np.where(seg > 0, seg, 1), 0)
        p = self.P[i] + (self.P[i + 1] - self.P[i]) * t[..., None]
        return p[..., 0], p[..., 1]


# =============================================================================================== revolve
def columns(n: int) -> np.ndarray:
    """theta' (deg from the -Z seam) for k = 0..n (n == 0 again at 360)."""
    return np.array([360.0 * k / n for k in range(n + 1)])


def theta_of(tp_deg):
    return (S.SEAM_DEG + np.asarray(tp_deg)) % 360.0


def pos(s, r, th_deg):
    t = th_deg * D2R
    return (s, r * math.cos(t), r * math.sin(t))


def nrm3(n2, th_deg):
    t = th_deg * D2R
    return (n2[0], n2[1] * math.cos(t), n2[1] * math.sin(t))


def vcoord(tp_deg, r):
    """Island-local V (mm): arc length from the island centre line (theta' = 180, i.e. +Z), decreasing with theta."""
    return -(tp_deg - 180.0) * D2R * r


def make_ring(mb: MB, p: PPoint, n: int):
    if p.r <= 1e-12:
        return [mb.v((p.s, 0.0, 0.0))]
    tps = columns(n)[:-1]
    return [mb.v(pos(p.s, p.r, theta_of(tp))) for tp in tps]


def revolve(mb: MB, prof: Sequence[PPoint], n: int, canon: Canon, slot_of, part_of, island_of, rings=None):
    """Revolve ``prof`` with n columns; consecutive points share rings.  Returns the ring list."""
    tps = columns(n)
    if rings is None:
        rings = [None] * len(prof)
    for i, p in enumerate(prof):
        if rings[i] is None:
            rings[i] = make_ring(mb, p, n)
    Us = [canon.U(p.s, p.r) for p in prof]
    for i in range(len(prof) - 1):
        p0, p1 = prof[i], prof[i + 1]
        R0, R1 = rings[i], rings[i + 1]
        slot, part, isl = slot_of(i), part_of(i), island_of(i)
        if len(R0) == 1 and len(R1) == 1:
            continue
        for k in range(n):
            t0, t1 = tps[k], tps[k + 1]
            th0, th1 = theta_of(t0), theta_of(t1)
            thm = theta_of(0.5 * (t0 + t1))
            k1 = (k + 1) % n

            def corner(ring, j, pp, U, nn, th, tp):
                if len(ring) == 1:
                    return ring[0], nrm3(nn, thm), (U, 0.0)
                return ring[j], nrm3(nn, th), (U, vcoord(tp, pp.r))
            a = corner(R0, k, p0, Us[i], p0.na, th0, t0)
            b = corner(R0, k1, p0, Us[i], p0.na, th1, t1)
            c = corner(R1, k1, p1, Us[i + 1], p1.nb, th1, t1)
            d = corner(R1, k, p1, Us[i + 1], p1.nb, th0, t0)
            if len(R0) == 1:
                mb.tri((a[0], c[0], d[0]), [a[1], c[1], d[1]], [a[2], c[2], d[2]], slot, part, isl)
            elif len(R1) == 1:
                mb.tri((a[0], b[0], c[0]), [a[1], b[1], c[1]], [a[2], b[2], c[2]], slot, part, isl)
            else:
                mb.tri((a[0], b[0], c[0]), [a[1], b[1], c[1]], [a[2], b[2], c[2]], slot, part, isl)
                mb.tri((a[0], c[0], d[0]), [a[1], c[1], d[1]], [a[2], c[2], d[2]], slot, part, isl)
    return rings


# =============================================================================================== needle
def needle_profile(lod: int) -> List[PPoint]:
    L2, SH, tr = S.NEEDLE_HALF, S.NEEDLE_SH_X, S.NEEDLE_TIP_R
    steps = (S.NEEDLE_LOD0_SWELL_STEPS, S.NEEDLE_LOD1_SWELL_STEPS, S.NEEDLE_LOD2_SWELL_STEPS)[lod]
    xs = np.linspace(-SH, SH, 2 * steps + 1)
    body = []
    for x in xs:
        x = float(x)
        n = _unit(-S.needle_drdx(x), 1.0)
        body.append((x, S.needle_r(x), n))
    r_sh = S.needle_r(SH)
    if lod == 0:
        cone_r = seg_normal((SH, r_sh), (L2, tr))           # +X cone (to the tip flat)
        cone_l = (-cone_r[0], cone_r[1])
        prof = [PPoint(-L2, 0.0, (-1, 0), (-1, 0)), PPoint(-L2, tr, (-1, 0), cone_l)]
    else:
        cone_r = seg_normal((SH, r_sh), (L2, 0.0))
        cone_l = (-cone_r[0], cone_r[1])
        prof = [PPoint(-L2, 0.0, cone_l, cone_l)]
    for j, (x, r, n) in enumerate(body):
        nb = cone_l if j == 0 else n
        na = cone_r if j == len(body) - 1 else n
        if j == 0:
            na = n
        if j == len(body) - 1:
            nb = n
        prof.append(PPoint(x, r, nb, na))
    if lod == 0:
        prof += [PPoint(L2, tr, cone_r, (1, 0)), PPoint(L2, 0.0, (1, 0), (1, 0))]
    else:
        prof.append(PPoint(L2, 0.0, cone_r, cone_r))
    return prof


def needle_canon() -> Canon:
    return Canon([(p.s, p.r) for p in needle_profile(0)])


def build_needle(lod: int) -> MB:
    d = S.NEEDLE_LODS[lod]
    prof = needle_profile(lod)
    canon = needle_canon()
    mb = MB(f"needle_LOD{lod}")
    shoulder = {i for i, p in enumerate(prof) if abs(abs(p.s) - S.NEEDLE_SH_X) < 1e-9}
    i_l, i_r = min(shoulder), max(shoulder)

    def part_of(i):
        if i < i_l:
            return "point_back"
        if i >= i_r:
            return "point_front"
        return "body"
    revolve(mb, prof, d.sides, canon, lambda i: 0, part_of, lambda i: "needle")
    return mb


# =============================================================================================== heavy
def _arc(c, rad, a0, a1, n):
    return [(c[0] + rad * math.cos(a * D2R), c[1] + rad * math.sin(a * D2R), (math.cos(a * D2R), math.sin(a * D2R)))
            for a in np.linspace(a0, a1, n + 1)]


def heavy_profile(lod: int) -> Tuple[List[PPoint], Dict[str, Tuple[int, int]]]:
    """Profile from the butt centre to s = 148 and the index ranges of [butt, wrap, body] segments."""
    rt, ch, rb, rw, rr = S.H_R_TAIL, S.H_CH, S.H_R_BIND, S.H_R_WRAP, S.H_BIND_ROUND
    (b0, b1), (f0, f1) = S.H_RB, S.H_FB
    up, out, dn = (0.0, 1.0), (-1.0, 0.0), (1.0, 0.0)
    taper = seg_normal((S.H_TAIL_END, rt), (S.H_PT0, S.H_R_FRONT))
    P: List[PPoint] = [PPoint(0.0, 0.0, out, out)]
    if lod == 0:
        cham = seg_normal((0.0, rt - ch), (ch, rt))
        P += [PPoint(0.0, rt - ch, out, cham), PPoint(ch, rt, cham, up)]
    else:
        P += [PPoint(0.0, rt, out, up)]
    i_butt_end = len(P)                     # next point (s = 6, r_tail) closes the butt island
    P.append(PPoint(b0, rt, up, out))
    if lod == 0:
        for (s0, s1) in ((b0, b1), (f0, f1)):
            # rear corner (180 -> 90 deg) and front corner (90 -> 0 deg) of each binding, 0.15 mm rounds
            for (sx, rx, n) in _arc((s0 + rr, rb - rr), rr, 180.0, 90.0, 2) + _arc((s1 - rr, rb - rr), rr, 90.0, 0.0, 2):
                P.append(PPoint(sx, rx, n, n))
            if s0 == b0:
                P += [PPoint(b1, rw, dn, up), PPoint(f0, rw, up, out)]
    elif lod == 1:
        P += [PPoint(b0, rb, out, up), PPoint(b1, rb, up, dn), PPoint(b1, rw, dn, up), PPoint(f0, rw, up, out),
              PPoint(f0, rb, out, up), PPoint(f1, rb, up, dn)]
    else:
        P += [PPoint(b0, rw, out, up), PPoint(f1, rw, up, dn)]
    P.append(PPoint(f1, rt, dn, taper))
    i_wrap_end = len(P) - 1
    P.append(PPoint(S.H_PT0, S.H_R_FRONT, taper, taper))
    ranges = {"butt": (0, i_butt_end), "wrap": (i_butt_end, i_wrap_end), "body": (i_wrap_end, len(P) - 1)}
    return P, ranges


def heavy_canon() -> Canon:
    P, _ = heavy_profile(0)
    return Canon([(p.s, p.r) for p in P], extend_to=S.HEAVY_L)


def facet_normal(phi_deg):
    k = S.H_FACET_H0 / S.H_PT_L
    t = phi_deg * D2R
    n = np.array([k, math.cos(t), math.sin(t)])
    return n / np.linalg.norm(n)


def build_heavy(lod: int) -> MB:
    d = S.HEAVY_LODS[lod]
    n = d.sides
    prof, rng = heavy_profile(lod)
    canon = heavy_canon()
    mb = MB(f"heavy_LOD{lod}")

    def seg_info(i):
        if i < rng["butt"][1]:
            return 0, "butt", "heavy_butt"
        if i < rng["wrap"][1]:
            seg = (prof[i].s, prof[i].r, prof[i + 1].s, prof[i + 1].r)
            part = "wrap" if (abs(seg[1] - S.H_R_WRAP) < 1e-9 and abs(seg[3] - S.H_R_WRAP) < 1e-9
                              and seg[2] - seg[0] > 10) else "binding"
            return 1, part, "wrap"
        return 0, "body", "heavy_body"
    body_end = len(prof) - 1                        # the s = 148 ring
    np_col = S.HEAVY_POINT_COLUMNS_LOD0 if lod == 0 else n
    # revolve everything except the last segment (taper -> 148) when the point ring is denser
    if np_col == n:
        rings = revolve(mb, prof, n, canon, lambda i: seg_info(i)[0], lambda i: seg_info(i)[1],
                        lambda i: seg_info(i)[2])
        ring148 = rings[-1]
    else:
        rings = revolve(mb, prof[:-1], n, canon, lambda i: seg_info(i)[0], lambda i: seg_info(i)[1],
                        lambda i: seg_info(i)[2])
        ring148 = _transition(mb, prof[-2], prof[-1], rings[-1], n, np_col, canon)
    _point(mb, ring148, np_col, canon, prof[-1])
    return mb


def _transition(mb, p0: PPoint, p1: PPoint, lo_ring, n_lo, n_hi, canon):
    """Taper strip from an n_lo ring to an n_hi ring (n_hi = m * n_lo): each low face fans to m + 1 triangles.
    The surface morphs from the 12-gon to the 48-gon over the 94 mm taper (0.077 mm at most)."""
    m = n_hi // n_lo
    assert m * n_lo == n_hi and m % 2 == 0
    hi_ring = make_ring(mb, p1, n_hi)
    tl, th = columns(n_lo), columns(n_hi)
    U0, U1 = canon.U(p0.s, p0.r), canon.U(p1.s, p1.r)
    for k in range(n_lo):
        L0, L1 = lo_ring[k], lo_ring[(k + 1) % n_lo]
        lc = [(L0, tl[k]), (L1, tl[k + 1])]
        hc = [(hi_ring[(m * k + j) % n_hi], th[m * k + j]) for j in range(m + 1)]

        def C(vtx, tp, p, U, nn):
            return vtx, nrm3(nn, theta_of(tp)), (U, vcoord(tp, p.r))
        for j in range(m):
            lo = lc[0] if j < m // 2 else lc[1]
            a = C(lo[0], lo[1], p0, U0, p0.na)
            b = C(hc[j][0], hc[j][1], p1, U1, p1.nb)
            c = C(hc[j + 1][0], hc[j + 1][1], p1, U1, p1.nb)
            mb.tri((a[0], b[0], c[0]), [a[1], b[1], c[1]], [a[2], b[2], c[2]], 0, "body", "heavy_body")
        a = C(lc[0][0], lc[0][1], p0, U0, p0.na)
        b = C(lc[1][0], lc[1][1], p0, U0, p0.na)
        c = C(hc[m // 2][0], hc[m // 2][1], p1, U1, p1.nb)
        mb.tri((a[0], b[0], c[0]), [a[1], b[1], c[1]], [a[2], b[2], c[2]], 0, "body", "heavy_body")
    return hi_ring


def _nearest_facet(th_deg):
    best = None
    for phi in S.H_FACET_PHI:
        c = math.cos((th_deg - phi) * D2R)
        if best is None or c > best[0] + 1e-12:
            best = (c, phi)
    return best


def _point(mb: MB, ring148, n, canon, p148: PPoint):
    """Lands (the round 4.5 mm stock between the facets, up to the grind lines) + three planar facets."""
    R = S.H_R_FRONT
    tps = columns(n)
    U148 = canon.U(S.H_PT0, R)
    cut_v, cut_s = [], []
    for k in range(n):
        th = theta_of(tps[k])
        c, _phi = _nearest_facet(th)
        s_cut = S.HEAVY_L - S.H_PT_L * c * R / S.H_FACET_H0
        s_cut = max(S.H_PT0, s_cut)
        cut_s.append(s_cut)
        cut_v.append(ring148[k] if s_cut - S.H_PT0 < 1e-9 else mb.v(pos(s_cut, R, th)))
    tip = mb.v((S.HEAVY_L, 0.0, 0.0))
    # lands: radial normals, the body island continued along U
    for k in range(n):
        k1 = (k + 1) % n
        t0, t1 = tps[k], tps[k + 1]

        def C(vtx, s, tp):
            th = theta_of(tp)
            return vtx, nrm3((0.0, 1.0), th), (U148 + (s - S.H_PT0), vcoord(tp, R))
        A, B = C(ring148[k], S.H_PT0, t0), C(ring148[k1], S.H_PT0, t1)
        Cc, D = C(cut_v[k1], cut_s[k1], t1), C(cut_v[k], cut_s[k], t0)
        if cut_v[k] != ring148[k] and cut_v[k1] != ring148[k1]:
            mb.tri((A[0], B[0], Cc[0]), [A[1], B[1], Cc[1]], [A[2], B[2], Cc[2]], 0, "land", "heavy_body")
            mb.tri((A[0], Cc[0], D[0]), [A[1], Cc[1], D[1]], [A[2], Cc[2], D[2]], 0, "land", "heavy_body")
        elif cut_v[k] == ring148[k] and cut_v[k1] != ring148[k1]:
            mb.tri((A[0], B[0], Cc[0]), [A[1], B[1], Cc[1]], [A[2], B[2], Cc[2]], 0, "land", "heavy_body")
        elif cut_v[k1] == ring148[k1] and cut_v[k] != ring148[k]:
            mb.tri((A[0], B[0], D[0]), [A[1], B[1], D[1]], [A[2], B[2], D[2]], 0, "land", "heavy_body")
    # facets: fan from the tip over the cut vertices between the two ridge columns around each facet
    for phi in S.H_FACET_PHI:
        nf = facet_normal(phi)
        e2 = np.array([0.0, -math.sin(phi * D2R), math.cos(phi * D2R)])
        ks = [k for k in range(n + 1) if _in_range(theta_of(tps[k]), phi)]
        # order by theta' around the facet (handle the seam: use unwrapped angle relative to phi)
        ks = sorted(set(k % n for k in ks), key=lambda k: _rel(theta_of(tps[k]), phi))
        isl = f"heavy_facet_{int(phi)}"

        def F(vtx):
            p = np.array(mb.V[vtx])
            return vtx, nf, (p[0], -float(p @ e2))
        Tt = F(tip)
        for a, b in zip(ks[:-1], ks[1:]):
            A, B = F(cut_v[a]), F(cut_v[b])
            mb.tri((Tt[0], A[0], B[0]), [Tt[1], A[1], B[1]], [Tt[2], A[2], B[2]], 0, "facet", isl)


def _rel(th, phi):
    return ((th - phi + 180.0) % 360.0) - 180.0


def _in_range(th, phi):
    return abs(_rel(th, phi)) <= 60.0 + 1e-6


# =============================================================================================== hulls
def octagon(s, r_in, phase=22.5):
    R = r_in / math.cos(math.pi / 8)
    return [(s, R * math.cos((phase + 45 * k) * D2R), R * math.sin((phase + 45 * k) * D2R)) for k in range(8)]


def needle_hull_points(eps=1e-4):
    r = S.NEEDLE_D_BELLY / 2 + eps
    h = S.NEEDLE_TIP_R + eps
    pts = octagon(-S.NEEDLE_SH_X, r) + octagon(S.NEEDLE_SH_X, r)
    for x in (-S.NEEDLE_HALF - eps, S.NEEDLE_HALF + eps):
        pts += [(x, sy * h, sz * h) for sy, sz in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
    return np.array(pts)


def heavy_hull_points(eps=1e-4):
    r = S.H_R_BIND + eps
    return np.array(octagon(-eps, r) + octagon(S.H_RIDGE_S0, r) + [(S.HEAVY_L + eps, 0.0, 0.0)])


# =============================================================================================== mass
def needle_round_mass():
    """Volume / COM of the as-built LOD0 profile with a ROUND section (frustum sums)."""
    P = [(p.s, p.r) for p in needle_profile(0)]
    return _frustum_volume(P)


def _frustum_volume(P):
    V, M = 0.0, 0.0
    for (s0, r0), (s1, r1) in zip(P[:-1], P[1:]):
        h = s1 - s0
        if h <= 0:
            continue
        v = math.pi * h / 3 * (r0 * r0 + r0 * r1 + r1 * r1)
        # centroid of a frustum from s0
        c = h * (r0 * r0 + 2 * r0 * r1 + 3 * r1 * r1) / (4 * (r0 * r0 + r0 * r1 + r1 * r1)) if v > 0 else 0
        V += v
        M += v * (s0 + c)
    return V, M / V


def heavy_round_mass(n_int=170001):
    """Steel (round section, three facets, design area law) + wrap (the as-built rounded binding profile)."""
    ss = np.linspace(0.0, S.HEAVY_L, n_int)
    a = np.array([S.heavy_steel_area(s) for s in ss])
    vs = float(np.trapezoid(a, ss))
    cs = float(np.trapezoid(a * ss, ss) / vs)
    P, rng = heavy_profile(0)
    pts = [(p.s, p.r) for p in P[rng["wrap"][0]:rng["wrap"][1] + 1]]
    # wrap volume = revolve of the outer profile minus the steel core (r_tail) between s 6 and 54
    vw, mw = 0.0, 0.0
    sw = np.linspace(S.H_RB[0], S.H_FB[1], 48001)
    ro = np.interp(sw, *_monotone(pts))
    aw = math.pi * (ro ** 2 - S.H_R_TAIL ** 2)
    vw = float(np.trapezoid(aw, sw))
    cw = float(np.trapezoid(aw * sw, sw) / vw)
    ms = vs * S.STEEL_DENSITY_G_MM3
    mw_g = vw * S.COTTON_DENSITY_G_MM3
    com = (ms * cs + mw_g * cw) / (ms + mw_g)
    return {"steel_volume_mm3": vs, "steel_com_mm": cs, "wrap_volume_mm3": vw, "wrap_com_mm": cw,
            "steel_mass_g": ms, "wrap_mass_g": mw_g, "mass_g": ms + mw_g, "com_from_butt_mm": com}


def _monotone(pts):
    """Outer radius as a function of s for the wrap profile (a step at equal s becomes a 1e-6 mm ramp)."""
    xs, ys = [], []
    for s, r in pts:
        if xs and s <= xs[-1] + 1e-9:
            s = xs[-1] + 1e-6
        xs.append(s)
        ys.append(r)
    return np.array(xs), np.array(ys)


def mesh_volume_com(V, T):
    """Closed-mesh volume (mm3) and centroid (mm) by signed tetrahedra."""
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    v6 = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    vol = v6.sum()
    com = (v6[:, None] * (a + b + c) / 4.0).sum(axis=0) / vol
    return float(vol), com


def closed_manifold(T) -> bool:
    from collections import Counter
    e = Counter()
    for t in T:
        for i in range(3):
            a, b = int(t[i]), int(t[(i + 1) % 3])
            e[(min(a, b), max(a, b))] += 1
    return all(v == 2 for v in e.values())


# =============================================================================================== design sections
def design_section_extents(item: str, s: float, n_circle: int = 3600):
    """Design (round, sharp-cornered) silhouette half-extents at a station: {+Y, -Y, +Z, -Z} in mm."""
    if item == "needle":
        r = S.needle_r(s)
        return {"+Y": r, "-Y": r, "+Z": r, "-Z": r}
    r = max(S.heavy_round_r(s), S.heavy_wrap_outer_r(s))
    th = np.linspace(0, 2 * math.pi, n_circle, endpoint=False)
    poly = np.stack([r * np.cos(th), r * np.sin(th)], 1)
    if s > S.H_PT0:
        h = S.heavy_facet_h(s)
        for phi in S.H_FACET_PHI:
            nrm = np.array([math.cos(phi * D2R), math.sin(phi * D2R)])
            poly = _clip(poly, nrm, h)
    if len(poly) == 0:
        return {"+Y": 0, "-Y": 0, "+Z": 0, "-Z": 0}
    return {"+Y": float(poly[:, 0].max()), "-Y": float(-poly[:, 0].min()), "+Z": float(poly[:, 1].max()),
            "-Z": float(-poly[:, 1].min())}


def _clip(poly, n, h):
    out = []
    m = len(poly)
    for i in range(m):
        p, q = poly[i], poly[(i + 1) % m]
        dp, dq = p @ n - h, q @ n - h
        if dp <= 0:
            out.append(p)
        if (dp < 0) != (dq < 0) and dp != dq:
            t = dp / (dp - dq)
            out.append(p + t * (q - p))
    return np.array(out)


def mesh_section_extents(V, T, s):
    """Silhouette half-extents of a triangle mesh cut by the plane x = s (mm)."""
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    pts = []
    for p, q in ((a, b), (b, c), (c, a)):
        dp, dq = p[:, 0] - s, q[:, 0] - s
        m = (dp * dq < 0) | (np.abs(dp) < 1e-12)
        t = np.where(np.abs(dp - dq) > 1e-15, dp / np.where(np.abs(dp - dq) > 1e-15, dp - dq, 1), 0)
        x = p + (q - p) * t[:, None]
        pts.append(x[m])
    P = np.concatenate(pts) if pts else np.zeros((0, 3))
    if len(P) == 0:
        return None
    return {"+Y": float(P[:, 1].max()), "-Y": float(-P[:, 1].min()), "+Z": float(P[:, 2].max()),
            "-Z": float(-P[:, 2].min())}
