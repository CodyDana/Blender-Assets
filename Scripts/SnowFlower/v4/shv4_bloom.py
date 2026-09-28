"""Snow Flower sheath look-match round 1: the PEARL blossom (real geometry at every LOD that shows it).

The reference's blossoms are five cupped, domed pearl-white petals, each held by a thin polished silver bezel, round
a silver dome ringed with small beads (the stamen dots), with small silver sepal tips between the petals.  The v4
build used flat grey discs with engraved lines.

Petal (local 2D: rho along the petal axis from the flower centre, lam across):
    outline  rho = RC + AR cos a,  lam = AL sin a (1 - TAPER max(0, -cos a))      (obovate, narrow at the centre)
    height   the whole petal rises toward its tip (the cup) and domes over its own centre (the pearl)
Low LOD0: outline ring + one inner ring + the centre, a short wall sunk into the substrate and a flat underside, so
every petal is a closed solid (no floating cards).  High: dense petals + bezel tubes + bead ring + sepals.
Millimetres; C = flower centre on the substrate, N = substrate normal, U = the direction petal 0 points to.
"""
from __future__ import annotations

import math

import numpy as np

from sfv4_mesh import MB, _norm, ellipsoid, tube

H_SILVER, H_INLAY = 1, 2
RC, AR, AL, TAPER = 0.585, 0.415, 0.345, 0.3
CUP = 0.16            # petal tip lift (x r) - the cup
DOME = 0.13           # pearl dome over the petal's own centre (x r)
BASE_H = 0.035        # petal base above the substrate (x r)
CENTRE_R, CENTRE_H = 0.2, 0.15


def _frame(N, U):
    N = _norm(np.asarray(N, float))
    U = np.asarray(U, float)
    U = _norm(U - N * (U @ N))
    V = np.cross(N, U)
    return N, U, V


def petal_outline(n):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rho = RC + AR * np.cos(a)
    lam = AL * np.sin(a) * (1 - TAPER * np.maximum(0.0, -np.cos(a)))
    return rho, lam, a


def petal_height(rho, s):
    """height (x r) at radial rho (x r) and normalised inset s (0 outline .. 1 petal centre)."""
    cup = CUP * max(0.0, (rho - 0.2) / 0.8) ** 1.4
    dome = DOME * math.sin(0.5 * math.pi * s) ** 0.8
    return BASE_H + cup + dome


def _petal_points(C, N, R_, T_, r, rho, lam, s, lift):
    return [C + R_ * (rr * r) + T_ * (ll * r) + N * (r * petal_height(rr, s) + lift) for rr, ll in zip(rho, lam)]


def build_low(mb: MB, C, N, U, r, level, island, mat, phase=0.0, lift=0.0, sink=0.6):
    """LOD 0/1/2 pearl blossom.  Islands: <island>_p (petal tops), <island>_w (walls), <island>_under, <island>_c."""
    N, U, V = _frame(N, U)
    C = np.asarray(C, float)
    n_o = {0: 12 if r > 12.0 else (9 if r > 7.5 else 8), 1: 8 if r > 12.0 else 6, 2: 6}[level]
    rings = {0: [1.0, 0.55], 1: [1.0], 2: [1.0]}[level]
    for k in range(5):
        ang = phase + 2 * math.pi * k / 5
        R_ = U * math.cos(ang) + V * math.sin(ang)
        T_ = np.cross(N, R_)
        rho, lam, a = petal_outline(n_o)
        loops = []
        for f in rings:
            rr = RC + (rho - RC) * f
            ll = lam * f
            pts = _petal_points(C, N, R_, T_, r, rr, ll, 1.0 - f, lift)
            loops.append((mb.vs(pts), rr, ll))
        cen = mb.v(C + R_ * (RC * r) + N * (r * petal_height(RC, 1.0) + lift))
        # local planar UV (mm) in the flower frame, petal k offset so petals never share texels
        def uv(rr, ll):
            x = rr * r * math.cos(ang) - ll * r * math.sin(ang)
            y = rr * r * math.sin(ang) + ll * r * math.cos(ang)
            return (float(x), float(y))
        for li in range(len(loops) - 1):
            (ia, ra, la), (ib, rb, lb) = loops[li], loops[li + 1]
            for j in range(n_o):
                j2 = (j + 1) % n_o
                mb.f([ia[j], ia[j2], ib[j2], ib[j]], [uv(ra[j], la[j]), uv(ra[j2], la[j2]), uv(rb[j2], lb[j2]),
                                                      uv(rb[j], lb[j])], island + "_p", mat)
        il, rl, ll_ = loops[-1]
        for j in range(n_o):
            j2 = (j + 1) % n_o
            mb.f([il[j], il[j2], cen], [uv(rl[j], ll_[j]), uv(rl[j2], ll_[j2]), uv(RC, 0.0)], island + "_p", mat)
        # wall down into the substrate + underside
        i0, r0_, l0_ = loops[0]
        bot = mb.vs([C + R_ * (rr * r) + T_ * (ll * r) - N * sink for rr, ll in zip(r0_, l0_)])
        per = np.cumsum([0.0] + [np.linalg.norm(np.subtract(mb.verts[i0[(j + 1) % n_o]], mb.verts[i0[j]]))
                                 for j in range(n_o)])
        hgt = r * 0.2 + sink
        for j in range(n_o):
            j2 = (j + 1) % n_o
            mb.f([i0[j2], i0[j], bot[j], bot[j2]], [(per[j + 1] + k * 60.0, hgt), (per[j] + k * 60.0, hgt),
                                                     (per[j] + k * 60.0, 0.0), (per[j + 1] + k * 60.0, 0.0)],
                 island + "_w", mat)
        cb = mb.v(C + R_ * (RC * r) - N * sink)
        for j in range(n_o):
            j2 = (j + 1) % n_o
            mb.f([bot[j2], bot[j], cb], [uv(r0_[j2], l0_[j2]), uv(r0_[j], l0_[j]), uv(RC, 0.0)], island + "_under", mat)
    # the silver centre dome
    nc = {0: 8, 1: 6, 2: 5}[level]
    ring = []
    for j in range(nc):
        a = 2 * math.pi * j / nc
        d = U * math.cos(a) + V * math.sin(a)
        ring.append(C + d * (CENTRE_R * r) + N * (r * (BASE_H + 0.06) + lift))
    ri = mb.vs(ring)
    top = mb.v(C + N * (r * (BASE_H + 0.06 + CENTRE_H) + lift))
    for j in range(nc):
        j2 = (j + 1) % nc
        a0, a1 = 2 * math.pi * j / nc, 2 * math.pi * j2 / nc
        mb.f([ri[j], ri[j2], top], [(CENTRE_R * r * math.cos(a0), CENTRE_R * r * math.sin(a0)),
                                    (CENTRE_R * r * math.cos(a1), CENTRE_R * r * math.sin(a1)), (0.0, 0.0)],
             island + "_c", mat)
    cb = mb.v(C - N * sink)
    for j in range(nc):
        j2 = (j + 1) % nc
        a0, a1 = 2 * math.pi * j / nc, 2 * math.pi * j2 / nc
        k0 = 0.8 * CENTRE_R * r
        mb.f([ri[j2], ri[j], cb], [(k0 * math.cos(a1), k0 * math.sin(a1)), (k0 * math.cos(a0), k0 * math.sin(a0)),
                                   (0.0, 0.0)], island + "_cu", mat)


def build_high(sink_obj, C, N, U, r, phase=0.0, lift=0.0, sepals=True):
    """Bake source: dense pearl petals, silver bezels, a beaded silver centre and sepal tips."""
    N, U, V = _frame(N, U)
    C = np.asarray(C, float)
    mbp = sink_obj.mb(H_INLAY)
    mbs = sink_obj.mb(H_SILVER)
    n_o = 56
    rings = [1.0, 0.96, 0.9, 0.8, 0.66, 0.5, 0.33, 0.16]
    for k in range(5):
        ang = phase + 2 * math.pi * k / 5
        R_ = U * math.cos(ang) + V * math.sin(ang)
        T_ = np.cross(N, R_)
        rho, lam, a = petal_outline(n_o)
        loops = []
        for f in rings:
            rr = RC + (rho - RC) * f
            ll = lam * f
            loops.append(mbp.vs(_petal_points(C, N, R_, T_, r, rr, ll, 1.0 - f, lift)))
        cen = mbp.v(C + R_ * (RC * r) + N * (r * petal_height(RC, 1.0) + lift))
        for li in range(len(loops) - 1):
            for j in range(n_o):
                j2 = (j + 1) % n_o
                mbp.f([loops[li][j], loops[li][j2], loops[li + 1][j2], loops[li + 1][j]], None, "HIGH", H_INLAY)
        for j in range(n_o):
            mbp.f([loops[-1][j], loops[-1][(j + 1) % n_o], cen], None, "HIGH", H_INLAY)
        bot = mbp.vs([C + R_ * (rr * r) + T_ * (ll * r) - N * 0.6 for rr, ll in zip(rho, lam)])
        for j in range(n_o):
            j2 = (j + 1) % n_o
            mbp.f([loops[0][j2], loops[0][j], bot[j], bot[j2]], None, "HIGH", H_INLAY)
        cb = mbp.v(C + R_ * (RC * r) - N * 0.6)
        for j in range(n_o):
            mbp.f([bot[(j + 1) % n_o], bot[j], cb], None, "HIGH", H_INLAY)
        # bezel: a thin polished tube on the petal rim
        rim = _petal_points(C, N, R_, T_, r, rho, lam, 0.0, lift)
        rim = np.array(rim)
        pts = np.vstack([rim, rim[:2]])
        ups = np.array([N] * len(pts))
        tube(mbs, pts, max(0.028 * r, 0.3), sides=8, island="HIGH", mat=H_SILVER, cap=(None, None), squash=0.8,
             up=ups)
        if sepals:
            # a small pointed silver sepal in the gap after this petal
            ga = ang + math.pi / 5
            D = U * math.cos(ga) + V * math.sin(ga)
            p0 = C + D * (0.42 * r) + N * (r * 0.05 + lift)
            p1 = C + D * (0.78 * r) + N * (r * 0.02 + lift)
            path = np.array([p0 + (p1 - p0) * t + N * (0.05 * r * math.sin(math.pi * t)) for t in np.linspace(0, 1, 8)])
            tube(mbs, path, lambda t: 0.07 * r * math.sin(math.pi * min(max(t, 0.05), 0.95)) ** 0.7, sides=8,
                 island="HIGH", mat=H_SILVER, cap=("point", "point"), squash=0.45, up=np.array([N] * len(path)))
    # centre: silver dome + a ring of beads (the stamen dots)
    ellipsoid(mbp, C + N * (r * (BASE_H + 0.06) + lift), U * (CENTRE_R * r * 0.72), V * (CENTRE_R * r * 0.72),
              N * (CENTRE_H * r), island="HIGH", mat=H_INLAY, seg=24, rings=10)
    # the silver collar round the pearl centre
    ring = np.array([C + (U * math.cos(a) + V * math.sin(a)) * (CENTRE_R * r * 0.8) + N * (r * (BASE_H + 0.07) + lift)
                     for a in np.linspace(0, 2 * math.pi, 40)])
    tube(mbs, ring, 0.035 * r, sides=8, island="HIGH", mat=H_SILVER, cap=(None, None), squash=0.8,
         up=np.array([N] * len(ring)))
    nb = 10
    for j in range(nb):
        a = 2 * math.pi * (j + 0.5) / nb + phase
        d = U * math.cos(a) + V * math.sin(a)
        c = C + d * (CENTRE_R * r * 1.1) + N * (r * (BASE_H + 0.15) + lift)
        rb = 0.05 * r
        ellipsoid(mbs, c, U * rb, V * rb, N * rb, island="HIGH", mat=H_SILVER, seg=10, rings=6)
