"""Look-match round 1 (sword): the CAST blossom - one construction for every fitting blossom (pommel end face, guard
centre, grip sprigs), in the high-poly (bake source) and as real low-poly petals (silhouette-carrying proxies).

Sheet (guard / pommel detail crops): five broad, puffy, polished petals, each with a bright bevelled rim and an
engraved centre line, pointed-oval tips; a raised centre dome ringed by stamen filaments ending in round beads.

Frame: C centre, N out of the flower, U toward petal 0 (rotated by ``phase``), V = N x U.  ``radius`` = petal reach.
``curve`` (mm per mm^2) bends the petals back along -N with the square of the distance from the centre so the
blossom can sit on a dome.
"""
from __future__ import annotations

import math

import numpy as np

from sfv4_mesh import MB, _norm, fan_cap, grid, tube

# petal proportions (fractions of the reach R)
BASE_R = 0.13         # petals start here (under the centre dome)
HALF_W = 0.37         # widest half-width (at WIDEST along the petal)
WIDEST = 0.60
HEIGHT = 0.20         # petal crown above the flower plane
EDGE_H = 0.055        # petal edge (rim) height above the plane
GROOVE = 0.035        # centre-line groove depth
CENTRE_R = 0.15       # centre dome radius
CENTRE_H = 0.19       # centre dome height (the highest point of the blossom)


def _frame(normal, phase, up_hint):
    N = _norm(normal)
    U = np.asarray(up_hint, float)
    U = U - N * np.dot(U, N)
    if np.linalg.norm(U) < 1e-6:
        U = np.array([1.0, 0, 0]) - N * N[0]
    U = _norm(U)
    V = np.cross(N, U)
    c, s = math.cos(phase), math.sin(phase)
    return N, U * c + V * s, np.cross(N, U * c + V * s)


def petal_hw(t):
    """Half-width (fraction of R) at t = 0 (petal base) .. 1 (tip): narrow claw, broad pointed oval."""
    t = np.asarray(t, float)
    up = np.sin(0.5 * math.pi * np.clip(t / WIDEST, 0, 1)) ** 0.75
    dn = np.clip((1 - t) / (1 - WIDEST), 0, 1)
    tipc = np.sqrt(np.clip(1 - (1 - dn) ** 2.2, 0, 1)) * (0.35 + 0.65 * dn ** 0.35)
    base = 0.20 + 0.80 * up
    return HALF_W * np.where(t < WIDEST, base, tipc)


def _petal_point(C, N, A, W, R, t, f, curve, lift, sink=0.0):
    """t along the petal (0 base .. 1 tip), f across (-1 .. 1); returns the TOP surface point."""
    r = (BASE_R + (1 - BASE_R) * t) * R
    hw = float(petal_hw(t)) * R
    crown = HEIGHT * R * math.sin(math.pi * (0.18 + 0.82 * t)) ** 0.8
    prof = (1 - abs(f) ** 2.2) ** 0.55
    h = EDGE_H * R + (crown - EDGE_H * R) * prof
    # engraved centre line (fades out toward the tip) and a slight cup lift of the edges
    h -= GROOVE * R * math.exp(-(f / 0.09) ** 2) * math.sin(math.pi * min(1.0, 0.1 + t * 1.1)) * (1 - t) ** 0.3
    h += 0.03 * R * abs(f) ** 3 * math.sin(math.pi * t)
    h += lift * (1 - t) - curve * r * r - sink
    return C + A * r + W * (f * hw) + N * h


def _petal_base(C, N, A, W, R, t, f, curve, depth=0.35):
    """Point under the petal on the (curved) flower bed, ``depth`` below it."""
    r = (BASE_R + (1 - BASE_R) * t) * R
    hw = float(petal_hw(t)) * R
    return C + A * r + W * (f * hw) - N * (curve * r * r + depth)


def blossom_high(sink, center, radius, normal, phase=0.0, up_hint=(0, 0, 1), curve=0.0, mats=None, n_l=22, n_w=15,
                 stamens=10, lift=0.0):
    """High-poly cast blossom into ``sink`` (sfv4_rev3.Sink).  mats: dict petal / rim / groove / centre / stamen."""
    import sfv4_rev3 as R3
    M = {"petal": R3.INLAY, "rim": R3.SILVER, "groove": R3.RECESS, "centre": R3.INLAY, "stamen": R3.SILVER}
    M.update(mats or {})
    C = np.asarray(center, float)
    N, U0, V0 = _frame(normal, phase, up_hint)
    R = float(radius)
    ts = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, n_l))
    fs = np.sin(np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_w))
    for k in range(5):
        a = 2 * math.pi * k / 5
        A = U0 * math.cos(a) + V0 * math.sin(a)
        W = np.cross(N, A)
        mb = sink.mb(M["petal"])
        # ONE closed shell per petal (top sheet + tip + walls + hidden bottom sharing vertices), so the normal
        # recalculation can never flip a petal (an open top sheet flipped one guard petal: black in the normal bake)
        tsh = ts[:-1]
        top = np.array([[_petal_point(C, N, A, W, R, t, f, curve, lift) for f in fs] for t in tsh])
        nt = len(tsh)
        idx = np.array(mb.vs(top.reshape(-1, 3))).reshape(nt, n_w)
        pm = M["petal"]
        for a_ in range(nt - 1):
            for b_ in range(n_w - 1):
                mb.f([idx[a_, b_], idx[a_ + 1, b_], idx[a_ + 1, b_ + 1], idx[a_, b_ + 1]], None, "HIGH", pm)
        tip = mb.v(_petal_point(C, N, A, W, R, 1.0, 0.0, curve, lift))
        for b_ in range(n_w - 1):
            mb.f([idx[nt - 1, b_], tip, idx[nt - 1, b_ + 1]], None, "HIGH", pm)
        ring = [(idx[a_, n_w - 1], tsh[a_], fs[n_w - 1]) for a_ in range(nt)] + [(tip, 1.0, 0.0)] +                [(idx[a_, 0], tsh[a_], fs[0]) for a_ in range(nt - 1, -1, -1)] +                [(idx[0, b_], tsh[0], fs[b_]) for b_ in range(1, n_w - 1)]
        bot = mb.vs([_petal_base(C, N, A, W, R, t, f, curve, 0.45) for _, t, f in ring])
        L = len(ring)
        for m_ in range(L):
            n2 = (m_ + 1) % L
            mb.f([ring[m_][0], bot[m_], bot[n2], ring[n2][0]], None, "HIGH", pm)
        cb = np.mean([mb.verts[b] for b in bot], axis=0)
        fan_cap(mb, bot, cb, "HIGH", pm, flip=True)
        # bright bevelled rim bead along the petal outline (slightly inside the edge)
        rim_pts = []
        for t in np.linspace(0.04, 1.0, 40):
            rim_pts.append(_petal_point(C, N, A, W, R, t, 0.93, curve, lift))
        for t in np.linspace(1.0, 0.04, 40)[1:]:
            rim_pts.append(_petal_point(C, N, A, W, R, t, -0.93, curve, lift))
        tube(sink.mb(M["rim"]), np.array(rim_pts), 0.026 * R, sides=6, island="HIGH", mat=M["rim"])
        # engraved centre line (dark, sunk in the groove)
        line = [_petal_point(C, N, A, W, R, t, 0.0, curve, lift) - N * 0.004 * R for t in np.linspace(0.08, 0.72, 14)]
        tube(sink.mb(M["groove"]), np.array(line), lambda x: 0.011 * R * (1 - 0.6 * x), sides=5, island="HIGH",
             mat=M["groove"])
    # centre dome
    _dome(sink.mb(M["centre"]), C + N * (lift * 0.9), N, U0, V0, CENTRE_R * R, CENTRE_H * R, M["centre"])
    # stamens: filaments arching out from the dome, round anther beads
    for i in range(stamens):
        a = 2 * math.pi * (i + 0.5) / stamens + (0.18 if i % 2 else -0.05)
        D = U0 * math.cos(a) + V0 * math.sin(a)
        reach = R * (0.27 + 0.035 * math.sin(i * 2.3))
        p0 = C + D * CENTRE_R * R * 0.7 + N * (lift + 0.14 * R)
        p1 = C + D * reach * 0.65 + N * (lift + 0.19 * R - curve * (reach * 0.65) ** 2)
        p2 = C + D * reach + N * (lift + 0.17 * R - curve * reach * reach)
        tube(sink.mb(M["stamen"]), np.array([p0, p1, p2]), 0.022 * R, sides=5, island="HIGH", mat=M["stamen"])
        _bead(sink.mb(M["stamen"]), p2 + N * 0.015 * R, 0.055 * R, M["stamen"])


def _dome(mb, base, N, U, V, r, h, mat, seg=20, rings=6, island="HIGH"):
    pts = []
    for j in range(rings):
        phi = 0.5 * math.pi * j / rings
        pts.append([base + (U * math.cos(t) + V * math.sin(t)) * r * math.cos(phi) + N * h * math.sin(phi)
                    for t in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
    idx = grid(mb, np.array(pts), True, island, mat)
    fan_cap(mb, list(idx[-1]), base + N * h, island, mat)
    fan_cap(mb, list(idx[0]), base - N * 0.3, island, mat, flip=True)


def _bead(mb, c, r, mat):
    from sfv4_mesh import ellipsoid
    ellipsoid(mb, c, np.array([r, 0, 0]), np.array([0, r, 0]), np.array([0, 0, r]), "HIGH", mat, seg=8, rings=5)


# ====================================================================== low-poly proxy (real petals)

def blossom_low(mb: MB, center, radius, normal, phase, island, mat=0, level=0, up_hint=(0, 0, 1), curve=0.0, lift=0.0):
    """Five real petals + the centre dome; the same surface law as the high blossom (at low resolution) so the bake
    cage stays small.  UV islands (no overlap inside any of them): <island> = the five petal tops laid side by side in
    petal-local (along, across) mm, <island>_c = the dome (planar), <island>_side = every wall strip stacked,
    <island>_under = the hidden undersides (packed at low density)."""
    C = np.asarray(center, float)
    N, U0, V0 = _frame(normal, phase, up_hint)
    R = float(radius)
    if level == 0:
        ts = np.array([0.0, 0.2, 0.45, 0.7, 0.88])
        fs = np.array([-1.0, -0.6, 0.0, 0.6, 1.0])
    elif level == 1:
        ts = np.array([0.0, 0.4, 0.75])
        fs = np.array([-1.0, 0.0, 1.0])
    else:
        ts = np.array([0.0, 0.55])
        fs = np.array([-1.0, 0.0, 1.0])
    step = 1.25 * R          # petal k's UV block offset (u)
    side_v = 0.0
    for k in range(5):
        a = 2 * math.pi * k / 5
        A = U0 * math.cos(a) + V0 * math.sin(a)
        W = np.cross(N, A)

        def luv(t, f, k=k):
            r = (BASE_R + (1 - BASE_R) * t) * R
            return (float(r + k * step), float(f * float(petal_hw(t)) * R))

        top = np.array([[_petal_point(C, N, A, W, R, t, f, curve, lift) for f in fs] for t in ts])
        nt, nf = top.shape[:2]
        idx = np.array(mb.vs(top.reshape(-1, 3))).reshape(nt, nf)
        for i in range(nt - 1):
            for j in range(nf - 1):
                q = [idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]]
                mb.f(q, [luv(ts[i], fs[j]), luv(ts[i + 1], fs[j]), luv(ts[i + 1], fs[j + 1]), luv(ts[i], fs[j + 1])],
                     island, mat)
        tip_p = _petal_point(C, N, A, W, R, 1.0, 0.0, curve, lift)
        tip = mb.v(tip_p)
        for j in range(nf - 1):
            mb.f([idx[nt - 1, j], tip, idx[nt - 1, j + 1]], [luv(ts[-1], fs[j]), luv(1.0, 0.0), luv(ts[-1], fs[j + 1])],
                 island, mat)
        # outline ring (CCW seen from +N): +f edge from base to tip, the tip, -f edge back, base row
        ring = [("v", idx[i, nf - 1], ts[i], fs[nf - 1]) for i in range(nt)] + [("v", tip, 1.0, 0.0)] + \
               [("v", idx[i, 0], ts[i], fs[0]) for i in range(nt - 1, -1, -1)] + \
               [("v", idx[0, j], ts[0], fs[j]) for j in range(1, nf - 1)]
        ring_i = [r[1] for r in ring]
        ring_p = [np.asarray(mb.verts[r[1]]) for r in ring]
        bot_p = [_petal_base(C, N, A, W, R, r[2], r[3], curve, 0.35) for r in ring]
        bot_i = mb.vs(bot_p)
        L = len(ring_i)
        s = 0.0
        hmax = max(float(np.linalg.norm(ring_p[m] - bot_p[m])) for m in range(L))
        for m in range(L):
            n2 = (m + 1) % L
            seg = float(np.linalg.norm(ring_p[n2] - ring_p[m]))
            h0 = float(np.linalg.norm(ring_p[m] - bot_p[m]))
            h1 = float(np.linalg.norm(ring_p[n2] - bot_p[n2]))
            mb.f([ring_i[m], bot_i[m], bot_i[n2], ring_i[n2]],
                 [(s, side_v + h0), (s, side_v), (s + seg, side_v), (s + seg, side_v + h1)], f"{island}_side", mat)
            s += seg
        side_v += hmax + 0.6
        buv = [luv(r[2], r[3]) for r in ring]
        cb = np.mean(bot_p, axis=0)
        fan_cap(mb, bot_i, cb, f"{island}_under", mat, uv_ring=buv,
                uv_center=(float(np.mean([b[0] for b in buv])), float(np.mean([b[1] for b in buv]))), flip=True)
    # centre dome (its own planar island)
    seg = {0: 10, 1: 8, 2: 6}[level]
    rings = {0: 3, 1: 2, 2: 1}[level]
    base = C + N * (lift * 0.9)
    r, h = CENTRE_R * R * 1.3, CENTRE_H * R     # low dome ~ the high dome (the stamens bake onto the petal bases)

    def puv(p):
        d = p - C
        return (float(np.dot(d, U0)), float(np.dot(d, V0)))
    rows = []
    for j in range(rings):
        phi = 0.5 * math.pi * j / rings
        rows.append([base + (U0 * math.cos(t) + V0 * math.sin(t)) * r * math.cos(phi)
                     + N * (0.08 * R + (h - 0.08 * R) * math.sin(phi))
                     for t in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
    rows = np.array(rows)
    idx = np.array(mb.vs(rows.reshape(-1, 3))).reshape(len(rows), seg)
    for j in range(len(rows) - 1):
        for i in range(seg):
            i2 = (i + 1) % seg
            q = [idx[j, i], idx[j, i2], idx[j + 1, i2], idx[j + 1, i]]
            mb.f(q, [puv(rows[j, i]), puv(rows[j, i2]), puv(rows[j + 1, i2]), puv(rows[j + 1, i])], island + "_c", mat)
    top_c = base + N * h
    fan_cap(mb, list(idx[-1]), top_c, island + "_c", mat, uv_ring=[puv(p) for p in rows[-1]], uv_center=puv(top_c))
    off = 5 * step + r + 1.0
    fan_cap(mb, list(idx[0]), base - N * 0.3, island + "_under", mat,
            uv_ring=[(puv(p)[0] + off, puv(p)[1]) for p in rows[0]], uv_center=(off, 0.0), flip=True)
